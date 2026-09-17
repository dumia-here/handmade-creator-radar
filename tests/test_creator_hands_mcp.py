import json
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from creator_hands import (
    CreatorHandsBridge,
    FileQueue,
    LocalTextWorker,
    ReadOnlyMcpVerifier,
    build_task,
    root_arg_server_factory,
)


_FAKE_SERVER = r'''
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath

parser = argparse.ArgumentParser()
parser.add_argument("--root", required=True)
parser.add_argument("--bad-hash", action="store_true")
args = parser.parse_args()
label, raw_root = args.root.split("=", 1)
root = Path(raw_root).resolve()
protocol = None


def emit(identifier, result):
    print(json.dumps({"jsonrpc": "2.0", "id": identifier, "result": result}, separators=(",", ":")), flush=True)


def safe_path(value):
    path = PurePosixPath(value)
    if not value or path.is_absolute() or "." in path.parts or ".." in path.parts:
        raise ValueError("unsafe path")
    target = root.joinpath(*path.parts).resolve()
    target.relative_to(root)
    return target


def descriptor(name):
    props = {"root": {"type": "string"}, "path": {"type": "string"}}
    if name == "read_text_file":
        props.update({"offset": {"type": "integer"}, "max_bytes": {"type": "integer"}})
    return {"name": name, "inputSchema": {"type": "object", "properties": props, "required": ["root", "path"]}}


for line in sys.stdin if False else iter(input, None):
    pass
'''

# The final server body is assembled separately so the fixture stays readable.
_FAKE_SERVER_BODY = r'''
import sys
for raw in sys.stdin:
    if not raw.strip():
        continue
    message = json.loads(raw)
    method = message.get("method")
    if "id" not in message:
        continue
    identifier = message["id"]
    params = message.get("params") or {}
    if method == "initialize":
        protocol = params.get("protocolVersion")
        emit(identifier, {"protocolVersion": protocol, "serverInfo": {"name": "fake-readonly-mcp", "version": "test"}})
        continue
    if method == "tools/list":
        emit(identifier, {"tools": [descriptor("stat_path"), descriptor("sha256_file"), descriptor("read_text_file")]})
        continue
    if method != "tools/call":
        emit(identifier, {})
        continue
    name = params.get("name")
    arguments = params.get("arguments") or {}
    if arguments.get("root") != label:
        emit(identifier, {"isError": True, "content": [], "structuredContent": {}})
        continue
    target = safe_path(arguments.get("path", ""))
    if name == "stat_path":
        result = {"type": "file", "size": target.stat().st_size}
    elif name == "sha256_file":
        data = target.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if args.bad_hash:
            digest = "0" * 64
        result = {"sha256": digest, "size": len(data)}
    elif name == "read_text_file":
        data = target.read_bytes()
        offset = int(arguments.get("offset", 0))
        max_bytes = int(arguments.get("max_bytes", 65536))
        chunk = data[offset:offset + max_bytes]
        result = {
            "content": chunk.decode("utf-8"),
            "offset": offset,
            "bytes_read": len(chunk),
            "eof": offset + len(chunk) >= len(data),
        }
    else:
        emit(identifier, {"isError": True, "content": [], "structuredContent": {}})
        continue
    emit(identifier, {"isError": False, "content": [{"type": "text", "text": "ok"}], "structuredContent": result})
'''


class CreatorHandsMcpTests(unittest.TestCase):
    def make_server(self, root: Path) -> Path:
        server = root / "fake_mcp.py"
        # Drop the dead readability stub before writing the executable fixture.
        prefix = _FAKE_SERVER.split("for line in sys.stdin if False", 1)[0]
        server.write_text(textwrap.dedent(prefix + _FAKE_SERVER_BODY), encoding="utf-8")
        return server

    def make_verifier(self, root: Path, *, bad_hash: bool = False) -> ReadOnlyMcpVerifier:
        server = self.make_server(root)
        command = [sys.executable, str(server)]
        if bad_hash:
            command.append("--bad-hash")
        return ReadOnlyMcpVerifier(
            server_argv_factory=root_arg_server_factory(command),
            root_label="workspace",
            timeout_seconds=2,
        )

    def test_mcp_verifier_reads_real_artifact_through_stdio_child(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            target = workspace / "output" / "note.txt"
            target.parent.mkdir(parents=True)
            target.write_text("verified by another process\n", encoding="utf-8")
            verifier = self.make_verifier(root)
            task = build_task(
                task_id="mcp-direct",
                request="Verify the artifact.",
                project_id="demo",
                action="write_text",
                acceptance=["artifact matches"],
                payload={"target": "output/note.txt", "content": "verified by another process\n"},
            )

            result = verifier.verify(task, workspace, ["output/note.txt"])

            self.assertTrue(result.ok)
            self.assertEqual(result.verifier, "mcp-readonly-stdio")
            self.assertEqual(result.evidence["server_identity"], "fake-readonly-mcp")
            self.assertEqual(result.evidence["tools_used"], ["stat_path", "sha256_file", "read_text_file"])
            self.assertTrue(result.evidence["child_exit"]["clean"])
            self.assertEqual(len(result.evidence["artifacts"][0]["sha256"]), 64)

    def test_bridge_closes_worker_to_mcp_to_receipt_loop(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            queue = FileQueue(root / "queue")
            verifier = self.make_verifier(root)
            bridge = CreatorHandsBridge(
                queue=queue,
                workspace=root / "workspace",
                workers=[LocalTextWorker()],
                verifier=verifier,
            )
            task = build_task(
                task_id="mcp-loop",
                request="Create the agreed note and verify it out of process.",
                project_id="demo",
                action="write_text",
                acceptance=["note exists", "MCP readback matches"],
                payload={"target": "output/note.txt", "content": "hands have senses\n"},
            )
            queue.enqueue(task)

            receipt = bridge.run_once()

            self.assertEqual(receipt.status, "completed")
            self.assertTrue(receipt.verification.ok)
            stored = json.loads((root / "queue/completed/mcp-loop.receipt.json").read_text())
            self.assertEqual(stored["verification"]["verifier"], "mcp-readonly-stdio")

    def test_mcp_digest_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            target = workspace / "out.txt"
            workspace.mkdir()
            target.write_text("truth\n", encoding="utf-8")
            verifier = self.make_verifier(root, bad_hash=True)
            task = build_task(
                task_id="mcp-bad-hash",
                request="Verify exactly.",
                project_id="demo",
                action="write_text",
                acceptance=["hash matches"],
            )

            result = verifier.verify(task, workspace, ["out.txt"])

            self.assertFalse(result.ok)
            self.assertEqual(result.evidence["reason"], "mcp_digest_mismatch")

    def test_mcp_verifier_rejects_unsafe_artifact_path_before_spawn(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "workspace"
            workspace.mkdir()
            verifier = self.make_verifier(root)
            task = build_task(
                task_id="mcp-escape",
                request="Do not escape.",
                project_id="demo",
                action="write_text",
                acceptance=["stay bounded"],
            )

            result = verifier.verify(task, workspace, ["../outside.txt"])

            self.assertFalse(result.ok)
            self.assertEqual(result.evidence["reason"], "artifact_path_not_safe")


if __name__ == "__main__":
    unittest.main()
