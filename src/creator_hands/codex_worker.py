from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Callable, Iterable, Mapping, Protocol, Sequence

from .models import HandsTask, Verification

_SAFE_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z", re.ASCII)
_FORBIDDEN_TASK_KEYS = frozenset(
    {
        "argv",
        "command",
        "env",
        "executable",
        "sandbox",
        "model",
        "reasoning_effort",
        "codex_home",
        "network",
    }
)


def _safe_relative(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or ".." in path.parts:
        raise ValueError(f"unsafe relative path: {value!r}")
    return path


def _expected_artifacts(task: HandsTask) -> list[str]:
    raw = task.payload.get("expected_artifacts")
    if not isinstance(raw, list) or not raw:
        raise ValueError("codex_task requires non-empty payload.expected_artifacts")
    result: list[str] = []
    for item in raw:
        if not isinstance(item, str):
            raise ValueError("expected artifact paths must be strings")
        result.append(_safe_relative(item).as_posix())
    if len(result) != len(set(result)):
        raise ValueError("expected artifact paths must be unique")
    return result


def extract_last_agent_message(stdout: str) -> str | None:
    """Return the last completed Codex agent message from a JSONL stream."""

    messages: list[str] = []
    for line in str(stdout or "").splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict) or event.get("type") != "item.completed":
            continue
        item = event.get("item")
        if not isinstance(item, dict) or item.get("type") != "agent_message":
            continue
        text = item.get("text")
        if isinstance(text, str) and text.strip():
            messages.append(text.strip())
    return messages[-1] if messages else None


@dataclass(frozen=True)
class CodexRunResult:
    returncode: int
    stdout: str
    stderr: str


class CodexRunner(Protocol):
    def __call__(
        self,
        argv: Sequence[str],
        *,
        cwd: Path,
        env: Mapping[str, str],
        timeout: int,
    ) -> CodexRunResult: ...


def subprocess_codex_runner(
    argv: Sequence[str],
    *,
    cwd: Path,
    env: Mapping[str, str],
    timeout: int,
) -> CodexRunResult:
    completed = subprocess.run(
        list(argv),
        cwd=str(cwd),
        env=dict(env),
        capture_output=True,
        text=True,
        timeout=timeout,
        shell=False,
    )
    return CodexRunResult(completed.returncode, completed.stdout, completed.stderr)


class CodexCliWorker:
    """Run one explicit task through ``codex exec`` inside the bridge workspace.

    Runtime authority belongs to the worker constructor, not to the task card. A task may
    describe the work and expected artifacts, but it cannot replace the executable, model,
    sandbox, environment, or argv.
    """

    name = "codex-cli"
    actions = ("codex_task",)

    def __init__(
        self,
        *,
        executable: str = "codex",
        model: str | None = None,
        reasoning_effort: str | None = None,
        sandbox: str = "workspace-write",
        timeout_seconds: int = 900,
        skip_git_repo_check: bool = False,
        runner: CodexRunner = subprocess_codex_runner,
        environment_provider: Callable[[], Mapping[str, str]] | None = None,
    ):
        if not isinstance(executable, str) or not executable or "\x00" in executable:
            raise ValueError("executable must be one argv token")
        if sandbox not in {"read-only", "workspace-write"}:
            raise ValueError("public Codex worker allows only read-only or workspace-write")
        if not isinstance(timeout_seconds, int) or isinstance(timeout_seconds, bool) or not 1 <= timeout_seconds <= 3600:
            raise ValueError("timeout_seconds must be an integer between 1 and 3600")
        if model is not None and not _SAFE_TOKEN.fullmatch(model):
            raise ValueError("model must be one inert argv token")
        if reasoning_effort is not None and not _SAFE_TOKEN.fullmatch(reasoning_effort):
            raise ValueError("reasoning_effort must be one inert argv token")

        self.executable = executable
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.sandbox = sandbox
        self.timeout_seconds = timeout_seconds
        self.skip_git_repo_check = bool(skip_git_repo_check)
        self.runner = runner
        self.environment_provider = environment_provider or (lambda: os.environ.copy())

    def build_argv(self, task: HandsTask, workspace: Path) -> list[str]:
        if task.action not in self.actions:
            raise ValueError(f"unsupported action: {task.action}")
        forbidden = sorted(_FORBIDDEN_TASK_KEYS.intersection(task.payload))
        if forbidden:
            raise ValueError(f"task may not override Codex runtime fields: {', '.join(forbidden)}")
        expected = _expected_artifacts(task)
        criteria = "\n".join(f"- {item}" for item in task.acceptance)
        outputs = "\n".join(f"- {item}" for item in expected)
        prompt = (
            f"Task:\n{task.request.strip()}\n\n"
            f"Acceptance criteria:\n{criteria}\n\n"
            f"Expected artifacts, relative to the workspace:\n{outputs}\n\n"
            "Work only inside the provided workspace. Do not claim completion unless the expected artifacts exist."
        )

        argv = [
            self.executable,
            "exec",
            "--json",
            "--ephemeral",
            "--ignore-user-config",
            "--sandbox",
            self.sandbox,
            "--cd",
            str(workspace),
            "--color",
            "never",
        ]
        if self.skip_git_repo_check:
            argv.append("--skip-git-repo-check")
        if self.model is not None:
            argv.extend(["--model", self.model])
        if self.reasoning_effort is not None:
            argv.extend(["--config", f"model_reasoning_effort={self.reasoning_effort}"])
        argv.append(prompt)
        return argv

    def execute(self, task: HandsTask, workspace: Path) -> list[str]:
        expected = _expected_artifacts(task)
        argv = self.build_argv(task, workspace)
        env = dict(self.environment_provider())
        result = self.runner(argv, cwd=workspace, env=env, timeout=self.timeout_seconds)
        if result.returncode != 0:
            raise RuntimeError(f"codex exec failed with exit code {result.returncode}")
        if extract_last_agent_message(result.stdout) is None:
            raise RuntimeError("codex exec returned no completed agent message")

        for relative in expected:
            path = workspace.joinpath(*PurePosixPath(relative).parts)
            if path.is_symlink() or not path.is_file():
                raise RuntimeError(f"expected artifact missing or unsafe: {relative}")
        return expected


class ExpectedArtifactsVerifier:
    """Re-read the expected files after a worker exits and record SHA-256 evidence."""

    name = "expected-artifacts-sha256"

    def verify(self, task: HandsTask, workspace: Path, artifacts: list[str]) -> Verification:
        try:
            expected = _expected_artifacts(task)
        except ValueError as exc:
            return Verification(False, self.name, {"reason": str(exc)})
        if artifacts != expected:
            return Verification(
                False,
                self.name,
                {"reason": "artifact set mismatch", "expected": expected, "actual": list(artifacts)},
            )

        evidence: list[dict[str, object]] = []
        for relative in expected:
            path = workspace.joinpath(*PurePosixPath(relative).parts)
            if path.is_symlink() or not path.is_file():
                return Verification(False, self.name, {"reason": "artifact missing or unsafe", "path": relative})
            raw = path.read_bytes()
            evidence.append(
                {
                    "path": relative,
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "bytes": len(raw),
                }
            )
        return Verification(True, self.name, {"artifacts": evidence})
