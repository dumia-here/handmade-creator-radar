import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dispatch_bridge_radar.approvals import consume_confirmation, create_confirmation, decide_confirmation
from dispatch_bridge_radar.atomic import ArtifactWriteError, atomic_write_new
from dispatch_bridge_radar.errors import ErrorCode
from dispatch_bridge_radar.offline_workflow import OfflineBridgeWorkflow, create_state_dirs, find_stale_tasks


class Step4RuntimeTests(unittest.TestCase):
    def test_confirmation_consumes_once_and_keeps_original_task_link(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "confirm.json"
            record = create_confirmation(path, task_id="t1", original_filename="original.md", allowed_change="track_filter:compound", created_at="2026-07-17T00:00:00Z", expires_at="2026-07-18T00:00:00Z")
            decide_confirmation(path, "approved", "2026-07-17T00:01:00Z")
            first = consume_confirmation(path, task_id="t1", resume_token=record.resume_token, requested_change=record.allowed_change, now="2026-07-17T00:02:00Z")
            second = consume_confirmation(path, task_id="t1", resume_token=record.resume_token, requested_change=record.allowed_change, now="2026-07-17T00:03:00Z")
            self.assertEqual((first, second), ("consumed", "already_consumed"))
            self.assertEqual(record.original_filename, "original.md")

    def test_rejected_and_expired_confirmations_do_not_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            rejected_path = Path(directory) / "rejected.json"
            rejected = create_confirmation(rejected_path, task_id="r", original_filename="r.md", allowed_change="track_filter:minimal", created_at="2026-07-17T00:00:00Z", expires_at="2026-07-18T00:00:00Z")
            decide_confirmation(rejected_path, "rejected", "2026-07-17T00:01:00Z")
            self.assertEqual(consume_confirmation(rejected_path, task_id="r", resume_token=rejected.resume_token, requested_change=rejected.allowed_change, now="2026-07-17T00:02:00Z"), "rejected")
            expired_path = Path(directory) / "expired.json"
            expired = create_confirmation(expired_path, task_id="e", original_filename="e.md", allowed_change="track_filter:minimal", created_at="2026-07-17T00:00:00Z", expires_at="2026-07-17T00:01:00Z")
            decide_confirmation(expired_path, "approved", "2026-07-17T00:00:30Z")
            self.assertEqual(consume_confirmation(expired_path, task_id="e", resume_token=expired.resume_token, requested_change=expired.allowed_change, now="2026-07-17T00:02:00Z"), "expired")

    def test_confirmation_cannot_relax_global_safety(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "unsafe_action_rejected"):
                create_confirmation(Path(directory) / "unsafe.json", task_id="u", original_filename="u.md", allowed_change="disable_allowlist", created_at="2026-07-17T00:00:00Z", expires_at="2026-07-18T00:00:00Z")

    def test_atomic_failure_leaves_no_completed_file(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.md"
            with self.assertRaises(ArtifactWriteError):
                atomic_write_new(output, "partial", validator=lambda _: (_ for _ in ()).throw(ValueError("invalid")))
            self.assertFalse(output.exists())
            self.assertFalse(any(path.name.startswith(".radar-") for path in Path(directory).iterdir()))

    def test_existing_output_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.md"
            output.write_text("original", encoding="utf-8")
            with self.assertRaises(ArtifactWriteError) as caught:
                atomic_write_new(output, "new")
            self.assertEqual(caught.exception.reason_code, ErrorCode.OUTPUT_ALREADY_EXISTS)
            self.assertEqual(output.read_text(), "original")

    def test_move_failure_returns_recoverable_error_and_preserves_task(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_state_dirs(root)
            reports = root / "reports"
            reports.mkdir()
            task = root / "01-执行中/task.md"
            task.write_text("task", encoding="utf-8")
            workflow = OfflineBridgeWorkflow(root, lambda *_: None, mover=lambda *_: (_ for _ in ()).throw(OSError("move failed")))
            result = workflow.complete(task_path=task, task_id="task", report_path=reports / "report.md", report_text="report", receipt_path=root / "02-已完成/receipt.md", receipt_text="receipt", occurred_at="2026-07-17T00:00:00Z")
            self.assertEqual(result.status, "recoverable_error")
            self.assertTrue(task.exists())
            self.assertIn(str(task), result.error.preserved_outputs)

    def test_duplicate_task_does_not_write_or_notify_twice(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_state_dirs(root)
            reports = root / "reports"
            reports.mkdir()
            notifications = []
            workflow = OfflineBridgeWorkflow(root, lambda task_id, status: notifications.append((task_id, status)))
            first = root / "01-执行中/task.md"
            first.write_text("task", encoding="utf-8")
            output = reports / "report.md"
            result = workflow.complete(task_path=first, task_id="task", report_path=output, report_text="report", receipt_path=root / "02-已完成/receipt.md", receipt_text="receipt", occurred_at="2026-07-17T00:00:00Z")
            duplicate = root / "01-执行中/task-duplicate.md"
            duplicate.write_text("task", encoding="utf-8")
            second = workflow.complete(task_path=duplicate, task_id="task", report_path=output, report_text="changed", receipt_path=root / "02-已完成/receipt-2.md", receipt_text="receipt", occurred_at="2026-07-17T00:01:00Z")
            self.assertEqual((result.status, second.status), ("completed", "failed"))
            self.assertEqual(output.read_text(), "report")
            self.assertEqual(notifications, [("task", "completed")])

    def test_stale_tasks_are_identified_but_not_executed(self):
        with tempfile.TemporaryDirectory() as directory:
            running = Path(directory)
            task = running / "stale.md"
            task.write_text("task", encoding="utf-8")
            os.utime(task, (1000, 1000))
            self.assertEqual(find_stale_tasks(running, older_than_seconds=100, now_timestamp=1200), (task,))
            self.assertTrue(task.exists())

    def test_resume_action_failure_routes_original_task_to_failed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_state_dirs(root)
            task = root / "03-需确认/resume-fail.md"
            task.write_text("task", encoding="utf-8")
            confirmation = root / "03-需确认/resume-fail.json"
            record = create_confirmation(confirmation, task_id="resume-fail", original_filename=task.name, allowed_change="track_filter:minimal", created_at="2026-07-17T00:00:00Z", expires_at="2026-07-18T00:00:00Z")
            decide_confirmation(confirmation, "approved", "2026-07-17T00:01:00Z")
            notifications = []
            workflow = OfflineBridgeWorkflow(root, lambda task_id, status: notifications.append((task_id, status)))
            result = workflow.resume(confirmation_path=confirmation, task_path=task, task_id="resume-fail", resume_token=record.resume_token, requested_change=record.allowed_change, now="2026-07-17T00:02:00Z", action=lambda _: (_ for _ in ()).throw(ValueError("boom")))
            self.assertEqual(result.status, "failed")
            self.assertTrue((root / "04-失败/resume-fail.md").exists())
            self.assertTrue((root / "04-失败/resume-fail_error.json").exists())
            self.assertEqual(notifications, [("resume-fail", "failed")])
