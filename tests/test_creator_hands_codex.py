import json
import tempfile
import unittest
from pathlib import Path

from creator_hands.codex_worker import (
    CodexCliWorker,
    CodexRunResult,
    ExpectedArtifactsVerifier,
    extract_last_agent_message,
)
from creator_hands.frontdesk import build_task
from creator_hands.queue import FileQueue
from creator_hands.runtime import CreatorHandsBridge


class FakeCodexRunner:
    def __init__(self, *, returncode=0, create=True, jsonl=True):
        self.returncode = returncode
        self.create = create
        self.jsonl = jsonl
        self.calls = []

    def __call__(self, argv, *, cwd, env, timeout):
        self.calls.append({"argv": list(argv), "cwd": Path(cwd), "env": dict(env), "timeout": timeout})
        if self.create:
            target = Path(cwd) / "output" / "codex-note.txt"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("written by codex\n", encoding="utf-8")
        if self.jsonl:
            stdout = json.dumps(
                {"type": "item.completed", "item": {"type": "agent_message", "text": "Done."}}
            ) + "\n"
        else:
            stdout = "not jsonl\n"
        return CodexRunResult(self.returncode, stdout, "")


class CodexWorkerTests(unittest.TestCase):
    def task(self, **payload):
        base = {"expected_artifacts": ["output/codex-note.txt"]}
        base.update(payload)
        return build_task(
            task_id="codex-001",
            request="Create the agreed note.",
            project_id="demo",
            action="codex_task",
            acceptance=["the note exists", "the note is ready for verification"],
            payload=base,
        )

    def test_extract_last_agent_message(self):
        stdout = "\n".join(
            [
                json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "first"}}),
                "not-json",
                json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "last"}}),
            ]
        )
        self.assertEqual(extract_last_agent_message(stdout), "last")

    def test_runtime_authority_is_constructor_owned(self):
        runner = FakeCodexRunner()
        worker = CodexCliWorker(
            executable="/opt/codex",
            model="example-model",
            reasoning_effort="high",
            runner=runner,
            environment_provider=lambda: {"PATH": "/usr/bin"},
        )
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            artifacts = worker.execute(self.task(), workspace)
        self.assertEqual(artifacts, ["output/codex-note.txt"])
        argv = runner.calls[0]["argv"]
        self.assertEqual(argv[0:2], ["/opt/codex", "exec"])
        self.assertIn("--json", argv)
        self.assertIn("--ephemeral", argv)
        self.assertIn("--ignore-user-config", argv)
        self.assertEqual(argv[argv.index("--sandbox") + 1], "workspace-write")
        self.assertEqual(argv[argv.index("--model") + 1], "example-model")
        self.assertEqual(argv[argv.index("--config") + 1], "model_reasoning_effort=high")
        self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", argv)
        self.assertEqual(runner.calls[0]["env"], {"PATH": "/usr/bin"})

    def test_task_cannot_override_runtime(self):
        worker = CodexCliWorker(runner=FakeCodexRunner())
        with tempfile.TemporaryDirectory() as tmp:
            for key in ("command", "argv", "env", "executable", "sandbox", "model", "reasoning_effort", "codex_home", "network"):
                with self.subTest(key=key):
                    with self.assertRaises(ValueError):
                        worker.execute(self.task(**{key: "override"}), Path(tmp))

    def test_missing_expected_artifact_fails_worker(self):
        worker = CodexCliWorker(runner=FakeCodexRunner(create=False))
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(RuntimeError):
                worker.execute(self.task(), Path(tmp))

    def test_nonzero_codex_exit_fails_worker(self):
        worker = CodexCliWorker(runner=FakeCodexRunner(returncode=7, create=False))
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(RuntimeError, "exit code 7"):
                worker.execute(self.task(), Path(tmp))

    def test_invalid_jsonl_fails_worker(self):
        worker = CodexCliWorker(runner=FakeCodexRunner(jsonl=False))
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(RuntimeError, "no completed agent message"):
                worker.execute(self.task(), Path(tmp))

    def test_expected_artifacts_verifier_hashes_real_output(self):
        runner = FakeCodexRunner()
        worker = CodexCliWorker(runner=runner)
        verifier = ExpectedArtifactsVerifier()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifacts = worker.execute(self.task(), root)
            result = verifier.verify(self.task(), root, artifacts)
        self.assertTrue(result.ok)
        evidence = result.evidence["artifacts"][0]
        self.assertEqual(evidence["path"], "output/codex-note.txt")
        self.assertEqual(len(evidence["sha256"]), 64)
        self.assertGreater(evidence["bytes"], 0)

    def test_bridge_returns_failed_receipt_when_codex_output_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            queue = FileQueue(root / "queue")
            task = self.task()
            queue.enqueue(task)
            bridge = CreatorHandsBridge(
                queue=queue,
                workspace=root / "workspace",
                workers=[CodexCliWorker(runner=FakeCodexRunner(create=False))],
                verifier=ExpectedArtifactsVerifier(),
            )
            receipt = bridge.run_once()
        self.assertEqual(receipt.status, "failed")
        self.assertFalse(receipt.verification.ok)

    def test_public_worker_refuses_danger_full_access(self):
        with self.assertRaises(ValueError):
            CodexCliWorker(sandbox="danger-full-access")


if __name__ == "__main__":
    unittest.main()
