import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dispatch_bridge_radar.errors import ErrorCode, ErrorReceipt, task_route_for_error


class ErrorReceiptTests(unittest.TestCase):
    def test_all_twelve_error_codes_generate_safe_receipts(self):
        self.assertEqual(len(ErrorCode), 12)
        forbidden = ("cookie-value", "device-key", "https://secret.example/device")
        for code in ErrorCode:
            with self.subTest(code=code.value):
                receipt = ErrorReceipt.create(task_id="task-1", stage="offline-test", reason_code=code, occurred_at="2026-07-17T00:00:00Z", platform="youtube", preserved_outputs=("report-v1.md",))
                payload = json.dumps(receipt.to_dict(), ensure_ascii=False)
                self.assertEqual(receipt.reason_code, code)
                self.assertTrue(receipt.summary)
                self.assertTrue(receipt.next_step)
                self.assertFalse(any(secret in payload for secret in forbidden))

    def test_business_judgment_and_retry_errors_route_differently(self):
        self.assertEqual(task_route_for_error(ErrorCode.ALL_CANDIDATES_FILTERED), "needs_confirmation")
        self.assertEqual(task_route_for_error(ErrorCode.NETWORK_TIMEOUT), "failed")
        self.assertEqual(task_route_for_error(ErrorCode.INSUFFICIENT_EVIDENCE, acceptance_requires_sufficient=False), "completed")
