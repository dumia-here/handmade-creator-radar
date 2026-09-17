import json
import tempfile
import unittest
from pathlib import Path

from creator_hands import (
    CreatorHandsBridge,
    FileQueue,
    LocalTextWorker,
    ReadbackVerifier,
    build_task,
)


class CreatorHandsTests(unittest.TestCase):
    def make_bridge(self, root: Path):
        queue = FileQueue(root / "queue")
        bridge = CreatorHandsBridge(
            queue=queue,
            workspace=root / "workspace",
            workers=[LocalTextWorker()],
            verifier=ReadbackVerifier(),
        )
        return queue, bridge

    def test_end_to_end_task_moves_real_bytes_and_returns_verified_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            queue, bridge = self.make_bridge(root)
            task = build_task(
                task_id="demo-001",
                request="Create the note we agreed on.",
                project_id="demo",
                action="write_text",
                acceptance=["note exists", "content matches"],
                payload={"target": "output/note.txt", "content": "hands can move\n"},
            )
            queue.enqueue(task)

            receipt = bridge.run_once()

            self.assertIsNotNone(receipt)
            self.assertEqual(receipt.status, "completed")
            self.assertTrue(receipt.verification.ok)
            self.assertEqual((root / "workspace/output/note.txt").read_text(), "hands can move\n")
            self.assertEqual(len(receipt.verification.evidence["sha256"]), 64)
            receipt_file = root / "queue/completed/demo-001.receipt.json"
            self.assertTrue(receipt_file.is_file())
            stored = json.loads(receipt_file.read_text())
            self.assertEqual(stored["status"], "completed")

    def test_path_escape_fails_closed_and_returns_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            queue, bridge = self.make_bridge(root)
            task = build_task(
                task_id="escape-001",
                request="Write outside the workspace.",
                project_id="demo",
                action="write_text",
                acceptance=["must not escape workspace"],
                payload={"target": "../secret.txt", "content": "nope"},
            )
            queue.enqueue(task)

            receipt = bridge.run_once()

            self.assertEqual(receipt.status, "failed")
            self.assertFalse(receipt.verification.ok)
            self.assertFalse((root / "secret.txt").exists())
            self.assertEqual(receipt.verification.evidence["reason"], "ValueError")

    def test_unknown_action_is_not_executed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            queue, bridge = self.make_bridge(root)
            task = build_task(
                task_id="unknown-001",
                request="Do an unregistered thing.",
                project_id="demo",
                action="launch_everything",
                acceptance=["do not invent a worker"],
            )
            queue.enqueue(task)

            receipt = bridge.run_once()

            self.assertEqual(receipt.status, "failed")
            self.assertEqual(receipt.worker, "none")
            self.assertEqual(receipt.verification.evidence["reason"], "no registered worker")

    def test_duplicate_task_id_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            queue = FileQueue(Path(tmp) / "queue")
            task = build_task(
                task_id="same-id",
                request="First task.",
                project_id="demo",
                action="write_text",
                acceptance=["accepted once"],
                payload={"target": "a.txt", "content": "a"},
            )
            queue.enqueue(task)
            with self.assertRaises(ValueError):
                queue.enqueue(task)


if __name__ == "__main__":
    unittest.main()
