from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Protocol, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from .models import HandsTask, Receipt


@dataclass(frozen=True)
class DriveFile:
    file_id: str
    name: str


@dataclass(frozen=True)
class DriveFolders:
    queued: str
    running: str
    completed: str
    failed: str

    def all_ids(self) -> Tuple[str, str, str, str]:
        return (self.queued, self.running, self.completed, self.failed)


@dataclass(frozen=True)
class DriveClaim:
    file_id: str
    name: str


class DriveBackend(Protocol):
    """Minimal provider surface needed by DriveQueue.

    Authentication and token refresh stay outside the queue contract. This keeps
    credentials out of task cards and lets applications use their own OAuth layer.
    """

    def list_files(self, folder_id: str) -> List[DriveFile]: ...

    def create_text_file(self, folder_id: str, name: str, text: str) -> DriveFile: ...

    def read_text(self, file_id: str) -> str: ...

    def move_file(self, file_id: str, from_folder_id: str, to_folder_id: str) -> None: ...


class DriveApiError(RuntimeError):
    pass


class GoogleDriveRestBackend:
    """Small Google Drive v3 REST backend with injected OAuth token ownership.

    The caller supplies a token provider. No refresh token, client secret, folder ID,
    or access token is stored by this module. The provider is called for every HTTP
    request so an application can refresh credentials independently.
    """

    API_ROOT = "https://www.googleapis.com/drive/v3"
    UPLOAD_ROOT = "https://www.googleapis.com/upload/drive/v3"

    def __init__(
        self,
        token_provider: Callable[[], str],
        *,
        opener: Callable[..., object] = urlopen,
        timeout_seconds: float = 30.0,
    ):
        self._token_provider = token_provider
        self._opener = opener
        self.timeout_seconds = timeout_seconds

    def list_files(self, folder_id: str) -> List[DriveFile]:
        files: List[DriveFile] = []
        page_token: Optional[str] = None
        while True:
            params = {
                "q": f"'{folder_id}' in parents and trashed = false",
                "fields": "nextPageToken,files(id,name)",
                "pageSize": "1000",
                "orderBy": "name",
            }
            if page_token:
                params["pageToken"] = page_token
            data = self._request_json("GET", f"{self.API_ROOT}/files?{urlencode(params)}")
            for item in data.get("files", []):
                files.append(DriveFile(file_id=str(item["id"]), name=str(item["name"])))
            page_token = data.get("nextPageToken")
            if not page_token:
                return files

    def create_text_file(self, folder_id: str, name: str, text: str) -> DriveFile:
        boundary = f"creator-hands-{uuid.uuid4().hex}"
        metadata = json.dumps(
            {"name": name, "parents": [folder_id], "mimeType": "application/json"},
            separators=(",", ":"),
        ).encode("utf-8")
        payload = text.encode("utf-8")
        body = b"".join(
            [
                f"--{boundary}\r\n".encode("ascii"),
                b"Content-Type: application/json; charset=UTF-8\r\n\r\n",
                metadata,
                b"\r\n",
                f"--{boundary}\r\n".encode("ascii"),
                b"Content-Type: application/json; charset=UTF-8\r\n\r\n",
                payload,
                b"\r\n",
                f"--{boundary}--\r\n".encode("ascii"),
            ]
        )
        params = urlencode({"uploadType": "multipart", "fields": "id,name"})
        data = self._request_json(
            "POST",
            f"{self.UPLOAD_ROOT}/files?{params}",
            body=body,
            content_type=f"multipart/related; boundary={boundary}",
        )
        return DriveFile(file_id=str(data["id"]), name=str(data["name"]))

    def read_text(self, file_id: str) -> str:
        raw = self._request("GET", f"{self.API_ROOT}/files/{quote(file_id)}?alt=media")
        return raw.decode("utf-8")

    def move_file(self, file_id: str, from_folder_id: str, to_folder_id: str) -> None:
        params = urlencode(
            {
                "addParents": to_folder_id,
                "removeParents": from_folder_id,
                "fields": "id,parents",
            }
        )
        self._request_json(
            "PATCH",
            f"{self.API_ROOT}/files/{quote(file_id)}?{params}",
            body=b"{}",
            content_type="application/json",
        )

    def _request_json(
        self,
        method: str,
        url: str,
        *,
        body: Optional[bytes] = None,
        content_type: Optional[str] = None,
    ) -> Dict[str, object]:
        raw = self._request(method, url, body=body, content_type=content_type)
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            raise DriveApiError("Google Drive returned a non-object JSON response")
        return data

    def _request(
        self,
        method: str,
        url: str,
        *,
        body: Optional[bytes] = None,
        content_type: Optional[str] = None,
    ) -> bytes:
        token = self._token_provider().strip()
        if not token:
            raise DriveApiError("token provider returned an empty access token")
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        if content_type:
            headers["Content-Type"] = content_type
        request = Request(url, data=body, headers=headers, method=method)
        try:
            with self._opener(request, timeout=self.timeout_seconds) as response:
                return response.read()
        except HTTPError as exc:
            raise DriveApiError(f"Google Drive HTTP {exc.code}") from exc
        except URLError as exc:
            raise DriveApiError("Google Drive request failed") from exc


class DriveQueue:
    """Durable task queue using four caller-owned Google Drive folders.

    v0.1 intentionally assumes one queue consumer. Google Drive moves are durable but
    not a distributed lock, so multi-worker claim ownership is not claimed here.
    """

    def __init__(self, backend: DriveBackend, folders: DriveFolders):
        self.backend = backend
        self.folders = folders

    def enqueue(self, task: HandsTask) -> DriveFile:
        filename = f"{task.task_id}.json"
        self._reject_duplicate(filename)
        text = json.dumps(task.to_dict(), indent=2, sort_keys=True)
        return self.backend.create_text_file(self.folders.queued, filename, text)

    def claim_next(self) -> Optional[Tuple[HandsTask, DriveClaim]]:
        candidates = sorted(
            (item for item in self.backend.list_files(self.folders.queued) if item.name.endswith(".json")),
            key=lambda item: item.name,
        )
        if not candidates:
            return None
        source = candidates[0]
        data = json.loads(self.backend.read_text(source.file_id))
        if not isinstance(data, dict):
            raise ValueError("queued task must contain a JSON object")
        task = HandsTask.from_dict(data)
        expected_name = f"{task.task_id}.json"
        if source.name != expected_name:
            raise ValueError("task_id does not match queued filename")
        self.backend.move_file(source.file_id, self.folders.queued, self.folders.running)
        return task, DriveClaim(file_id=source.file_id, name=source.name)

    def finish(self, claim: DriveClaim, receipt: Receipt) -> DriveFile:
        if claim.name != f"{receipt.task_id}.json":
            raise ValueError("receipt task_id does not match claimed task")
        destination = self.folders.completed if receipt.status == "completed" else self.folders.failed
        self.backend.move_file(claim.file_id, self.folders.running, destination)
        receipt_name = f"{receipt.task_id}.receipt.json"
        receipt_text = json.dumps(receipt.to_dict(), indent=2, sort_keys=True)
        return self.backend.create_text_file(destination, receipt_name, receipt_text)

    def _reject_duplicate(self, filename: str) -> None:
        for folder_id in self.folders.all_ids():
            if any(item.name == filename for item in self.backend.list_files(folder_id)):
                task_id = filename[: -len(".json")]
                raise ValueError(f"task_id already exists: {task_id}")
