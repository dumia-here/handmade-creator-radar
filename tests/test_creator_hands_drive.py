import json
import tempfile
import unittest
from pathlib import Path

from creator_hands import (
    CreatorHandsBridge,
    DriveFile,
    DriveFolders,
    DriveQueue,
    GoogleDriveRestBackend,
    LocalTextWorker,
    ReadbackVerifier,
    build_task,
)


class MemoryDriveBackend:
    def __init__(self):
        self._folders = {}
        self._files = {}
        self._counter = 0

    def list_files(self, folder_id):
        ids = self._folders.get(folder_id, [])
        return [DriveFile(file_id=file_id, name=self._files[file_id]["name"]) for file_id in ids]

    def create_text_file(self, folder_id, name, text):
        self._counter += 1
        file_id = f"file-{self._counter}"
        self._files[file_id] = {"name": name, "text": text}
        self._folders.setdefault(folder_id, []).append(file_id)
        return DriveFile(file_id=file_id, name=name)

    def read_text(self, file_id):
        return self._files[file_id]["text"]

    def move_file(self, file_id, from_folder_id, to_folder_id):
        self._folders[from_folder_id].remove(file_id)
        self._folders.setdefault(to_folder_id, []).append(file_id)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def read(self):
        return self.payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class SequenceOpener:
    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.requests = []

    def __call__(self, request, timeout=None):
        self.requests.append((request, timeout))
        if not self.payloads:
            raise AssertionError("unexpected HTTP request")
        return FakeResponse(self.payloads.pop(0))


class CreatorHandsDriveTests(unittest.TestCase):
    def folders(self):
        return DriveFolders(
            queued="folder-queued",
            running="folder-running",
            completed="folder-completed",
            failed="folder-failed",
        )

    def test_drive_queue_closes_full_action_loop(self):
        backend = MemoryDriveBackend()
        queue = DriveQueue(backend, self.folders())
        with tempfile.TemporaryDirectory() as tmp:
            bridge = CreatorHandsBridge(
                queue=queue,
                workspace=Path(tmp) / "workspace",
                workers=[LocalTextWorker()],
                verifier=ReadbackVerifier(),
            )
            task = build_task(
                task_id="drive-loop-001",
                request="Create the agreed note from a durable remote queue.",
                project_id="demo",
                action="write_text",
                acceptance=["artifact exists", "content reads back exactly"],
                payload={"target": "output/from-drive.txt", "content": "phone -> queue -> hand -> receipt\n"},
            )

            queue.enqueue(task)
            receipt = bridge.run_once()

            self.assertEqual(receipt.status, "completed")
            self.assertTrue(receipt.verification.ok)
            completed_names = [item.name for item in backend.list_files(self.folders().completed)]
            self.assertEqual(
                completed_names,
                ["drive-loop-001.json", "drive-loop-001.receipt.json"],
            )
            stored_receipt = json.loads(
                backend.read_text(
                    next(
                        item.file_id
                        for item in backend.list_files(self.folders().completed)
                        if item.name.endswith(".receipt.json")
                    )
                )
            )
            self.assertEqual(stored_receipt["status"], "completed")
            self.assertEqual(stored_receipt["task_id"], "drive-loop-001")

    def test_drive_queue_rejects_reusing_terminal_task_id(self):
        backend = MemoryDriveBackend()
        queue = DriveQueue(backend, self.folders())
        with tempfile.TemporaryDirectory() as tmp:
            bridge = CreatorHandsBridge(
                queue=queue,
                workspace=Path(tmp),
                workers=[LocalTextWorker()],
                verifier=ReadbackVerifier(),
            )
            task = build_task(
                task_id="drive-duplicate",
                request="Write once.",
                project_id="demo",
                action="write_text",
                acceptance=["write once"],
                payload={"target": "once.txt", "content": "once"},
            )
            queue.enqueue(task)
            self.assertEqual(bridge.run_once().status, "completed")
            with self.assertRaises(ValueError):
                queue.enqueue(task)

    def test_drive_queue_rejects_filename_task_id_mismatch(self):
        backend = MemoryDriveBackend()
        folders = self.folders()
        task = build_task(
            task_id="inside-id",
            request="Mismatch must fail closed.",
            project_id="demo",
            action="write_text",
            acceptance=["reject mismatch"],
            payload={"target": "x.txt", "content": "x"},
        )
        backend.create_text_file(folders.queued, "outside-id.json", json.dumps(task.to_dict()))
        queue = DriveQueue(backend, folders)
        with self.assertRaises(ValueError):
            queue.claim_next()
        self.assertEqual([item.name for item in backend.list_files(folders.queued)], ["outside-id.json"])

    def test_google_drive_rest_list_uses_bearer_header_not_url(self):
        opener = SequenceOpener([b'{"files":[{"id":"abc","name":"task.json"}]}'])
        backend = GoogleDriveRestBackend(lambda: "secret-access-token", opener=opener)

        files = backend.list_files("queue-folder")

        self.assertEqual(files, [DriveFile(file_id="abc", name="task.json")])
        request, timeout = opener.requests[0]
        self.assertEqual(request.get_method(), "GET")
        self.assertEqual(request.get_header("Authorization"), "Bearer secret-access-token")
        self.assertNotIn("secret-access-token", request.full_url)
        self.assertEqual(timeout, 30.0)

    def test_google_drive_rest_create_and_move_use_drive_v3_contract(self):
        opener = SequenceOpener(
            [
                b'{"id":"new-file","name":"task.json"}',
                b'{"id":"new-file","parents":["running-folder"]}',
            ]
        )
        backend = GoogleDriveRestBackend(lambda: "token", opener=opener)

        created = backend.create_text_file("queued-folder", "task.json", '{"hello":"world"}')
        backend.move_file("new-file", "queued-folder", "running-folder")

        self.assertEqual(created, DriveFile(file_id="new-file", name="task.json"))
        create_request, _ = opener.requests[0]
        move_request, _ = opener.requests[1]
        self.assertEqual(create_request.get_method(), "POST")
        self.assertIn("uploadType=multipart", create_request.full_url)
        self.assertIn(b'"parents":["queued-folder"]', create_request.data)
        self.assertIn(b'{"hello":"world"}', create_request.data)
        self.assertEqual(move_request.get_method(), "PATCH")
        self.assertIn("addParents=running-folder", move_request.full_url)
        self.assertIn("removeParents=queued-folder", move_request.full_url)


if __name__ == "__main__":
    unittest.main()
