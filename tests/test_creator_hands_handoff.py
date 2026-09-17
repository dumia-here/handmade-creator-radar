import json
import tempfile
import unittest
from pathlib import Path

from creator_hands import CreatorHandsBridge, FileQueue, LocalTextWorker, ReadbackVerifier, build_task
from creator_hands.models import Verification


class AlwaysFailVerifier:
    name = "always-fail"

    def verify(self, task, workspace, artifacts):
        return Verification(False, self.name, {"reason": "synthetic verification failure"})


class FrontdeskHandoffTests(unittest.TestCase):
    def make_task(self, task_id="handoff-001"):
        return build_task(
            task_id=task_id,
            request="Create the agreed note and return verified state.",
            project_id="demo",
            action="write_text",
            acceptance=["note exists", "reality is independently checked"],
            payload={
                "target": "output/note.txt",
                "content": "frontdesk can consume this receipt\n",
                "private_runtime_hint": "must-not-be-mirrored",
            },
        )

    def test_verified_receipt_is_frontdesk_consumable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            queue = FileQueue(root / "queue")
            task = self.make_task()
            queue.enqueue(task)
            bridge = CreatorHandsBridge(
                queue=queue,
                workspace=root / "workspace",
                workers=[LocalTextWorker()],
                verifier=ReadbackVerifier(),
            )
            receipt = bridge.run_once()

            handoff = receipt.frontdesk_handoff
            self.assertEqual(handoff["schema_version"], 1)
            self.assertEqual(handoff["task"]["project_id"], "demo")
            self.assertEqual(handoff["task"]["action"], "write_text")
            self.assertEqual(handoff["outcome"]["terminal_status"], "completed")
            self.assertTrue(handoff["verification"]["ok"])
            self.assertTrue(handoff["frontdesk_state"]["may_claim_complete"])
            self.assertFalse(handoff["frontdesk_state"]["requires_frontdesk_review"])

            serialized = json.dumps(handoff, sort_keys=True)
            self.assertNotIn("private_runtime_hint", serialized)
            self.assertNotIn("must-not-be-mirrored", serialized)

    def test_verification_failure_requires_frontdesk_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            queue = FileQueue(root / "queue")
            task = self.make_task("handoff-fail-001")
            queue.enqueue(task)
            bridge = CreatorHandsBridge(
                queue=queue,
                workspace=root / "workspace",
                workers=[LocalTextWorker()],
                verifier=AlwaysFailVerifier(),
            )
            receipt = bridge.run_once()

            self.assertEqual(receipt.status, "failed")
            handoff = receipt.frontdesk_handoff
            self.assertFalse(handoff["frontdesk_state"]["may_claim_complete"])
            self.assertTrue(handoff["frontdesk_state"]["requires_frontdesk_review"])
            self.assertEqual(handoff["verification"]["evidence"]["reason"], "synthetic verification failure")

    def test_unknown_action_still_returns_frontdesk_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            queue = FileQueue(root / "queue")
            task = build_task(
                task_id="handoff-unknown-001",
                request="Use only a registered hand.",
                project_id="demo",
                action="not_registered",
                acceptance=["fail closed"],
            )
            queue.enqueue(task)
            bridge = CreatorHandsBridge(
                queue=queue,
                workspace=root / "workspace",
                workers=[LocalTextWorker()],
                verifier=ReadbackVerifier(),
            )
            receipt = bridge.run_once()

            self.assertEqual(receipt.worker, "none")
            self.assertTrue(receipt.frontdesk_handoff["frontdesk_state"]["requires_frontdesk_review"])
            stored = json.loads((root / "queue/failed/handoff-unknown-001.receipt.json").read_text())
            self.assertIn("frontdesk_handoff", stored)


if __name__ == "__main__":
    unittest.main()
