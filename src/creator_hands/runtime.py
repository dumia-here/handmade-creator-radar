from __future__ import annotations

import hashlib
from pathlib import Path, PurePosixPath
from typing import Dict, Iterable, List, Protocol

from .handoff import build_frontdesk_handoff
from .models import HandsTask, Receipt, Verification
from .queue import FileQueue


def _safe_relative_path(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError(f"unsafe relative path: {value!r}")
    return path


class Worker(Protocol):
    name: str
    actions: Iterable[str]

    def execute(self, task: HandsTask, workspace: Path) -> List[str]: ...


class Verifier(Protocol):
    name: str

    def verify(self, task: HandsTask, workspace: Path, artifacts: List[str]) -> Verification: ...


class LocalTextWorker:
    """A deliberately small worker used to prove that the action loop moves real bytes."""

    name = "local-text-worker"
    actions = ("write_text",)

    def execute(self, task: HandsTask, workspace: Path) -> List[str]:
        if task.action not in self.actions:
            raise ValueError(f"unsupported action: {task.action}")
        target = _safe_relative_path(str(task.payload.get("target", "")))
        content = task.payload.get("content")
        if not isinstance(content, str):
            raise ValueError("write_text requires string payload.content")

        output = workspace.joinpath(*target.parts)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(content, encoding="utf-8")
        return [target.as_posix()]


class ReadbackVerifier:
    """Read the produced artifact back from disk and verify content + SHA-256."""

    name = "readback-sha256"

    def verify(self, task: HandsTask, workspace: Path, artifacts: List[str]) -> Verification:
        if len(artifacts) != 1:
            return Verification(False, self.name, {"reason": "expected exactly one artifact"})
        relative = _safe_relative_path(artifacts[0])
        path = workspace.joinpath(*relative.parts)
        if not path.is_file():
            return Verification(False, self.name, {"reason": "artifact missing", "path": relative.as_posix()})

        raw = path.read_bytes()
        expected = task.payload.get("content")
        actual = raw.decode("utf-8")
        digest = hashlib.sha256(raw).hexdigest()
        return Verification(
            ok=isinstance(expected, str) and actual == expected,
            verifier=self.name,
            evidence={
                "path": relative.as_posix(),
                "sha256": digest,
                "bytes": len(raw),
                "content_match": isinstance(expected, str) and actual == expected,
            },
        )


class CreatorHandsBridge:
    """Claim one durable task, execute it, verify reality, and return a receipt."""

    def __init__(
        self,
        *,
        queue: FileQueue,
        workspace: Path | str,
        workers: Iterable[Worker],
        verifier: Verifier,
    ):
        self.queue = queue
        self.workspace = Path(workspace)
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.verifier = verifier
        self.workers: Dict[str, Worker] = {}
        for worker in workers:
            for action in worker.actions:
                if action in self.workers:
                    raise ValueError(f"duplicate worker action: {action}")
                self.workers[action] = worker

    def _receipt(
        self,
        task: HandsTask,
        *,
        status: str,
        worker: str,
        artifacts: List[str],
        verification: Verification,
        message: str,
    ) -> Receipt:
        return Receipt(
            task_id=task.task_id,
            status=status,
            worker=worker,
            artifacts=list(artifacts),
            verification=verification,
            message=message,
            frontdesk_handoff=build_frontdesk_handoff(
                task,
                status=status,
                worker=worker,
                artifacts=list(artifacts),
                verification=verification,
                message=message,
            ),
        )

    def run_once(self) -> Receipt | None:
        claimed = self.queue.claim_next()
        if claimed is None:
            return None
        task, running_path = claimed
        worker = self.workers.get(task.action)
        if worker is None:
            verification = Verification(False, self.verifier.name, {"reason": "no registered worker"})
            receipt = self._receipt(
                task,
                status="failed",
                worker="none",
                artifacts=[],
                verification=verification,
                message=f"No worker registered for action {task.action!r}",
            )
            self.queue.finish(running_path, receipt)
            return receipt

        try:
            artifacts = worker.execute(task, self.workspace)
            verification = self.verifier.verify(task, self.workspace, artifacts)
            status = "completed" if verification.ok else "failed"
            message = "Executed and verified" if verification.ok else "Execution finished but verification failed"
        except Exception as exc:  # boundary: convert executor errors into an auditable receipt
            artifacts = []
            verification = Verification(False, self.verifier.name, {"reason": type(exc).__name__, "detail": str(exc)})
            status = "failed"
            message = "Execution failed"

        receipt = self._receipt(
            task,
            status=status,
            worker=worker.name,
            artifacts=artifacts,
            verification=verification,
            message=message,
        )
        self.queue.finish(running_path, receipt)
        return receipt
