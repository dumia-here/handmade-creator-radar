from __future__ import annotations

import hashlib
import json
import os
import selectors
import subprocess
import time
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Dict, Iterable, List, Sequence

from .models import HandsTask, Verification


MCP_PROTOCOL_VERSION = "2025-11-25"
MCP_REQUIRED_TOOLS = ("stat_path", "sha256_file", "read_text_file")


class McpVerificationError(RuntimeError):
    """A bounded failure inside the public read-only MCP verification seam."""


ServerArgvFactory = Callable[[Path, str], Sequence[str]]


def root_arg_server_factory(
    base_command: Sequence[str],
    *,
    root_flag: str = "--root",
) -> ServerArgvFactory:
    """Build argv for servers that bind a root as ``--root label=/path``.

    Credentials, server paths, and root paths stay caller-owned. The returned
    factory only appends the current workspace binding at execution time.
    """

    base = tuple(_validate_argv(base_command))
    if not isinstance(root_flag, str) or not root_flag or "\x00" in root_flag:
        raise ValueError("root_flag must be a non-empty argv token")

    def build(workspace: Path, root_label: str) -> Sequence[str]:
        return [*base, root_flag, f"{root_label}={workspace}"]

    return build


def _validate_argv(argv: Sequence[str]) -> List[str]:
    if isinstance(argv, (str, bytes)) or not argv:
        raise ValueError("server argv must be a non-empty sequence")
    clean: List[str] = []
    for token in argv:
        if not isinstance(token, str) or not token or "\x00" in token:
            raise ValueError("server argv contains an invalid token")
        clean.append(token)
    return clean


def _safe_relative_path(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if not value or path.is_absolute() or "." in path.parts or ".." in path.parts:
        raise McpVerificationError("artifact_path_not_safe")
    return path


class _JsonLineMcpClient:
    def __init__(
        self,
        argv: Sequence[str],
        *,
        cwd: Path,
        protocol_version: str,
        timeout_seconds: float,
        max_message_bytes: int,
    ) -> None:
        self.argv = _validate_argv(argv)
        self.protocol_version = protocol_version
        self.timeout_seconds = timeout_seconds
        self.max_message_bytes = max_message_bytes
        try:
            self.process = subprocess.Popen(
                self.argv,
                cwd=str(cwd),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
            )
        except (OSError, ValueError) as exc:
            raise McpVerificationError("mcp_spawn_failed") from exc
        self.pending = b""
        self.next_id = 1
        self.closed = False
        self.exit_code = None
        self.forced_termination = False

    def _write(self, message: Dict[str, Any]) -> None:
        if self.process.stdin is None:
            raise McpVerificationError("mcp_stdin_unavailable")
        raw = (json.dumps(message, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
        try:
            written = self.process.stdin.write(raw)
            self.process.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            raise McpVerificationError("mcp_stdin_write_failed") from exc
        if written is not None and written != len(raw):
            raise McpVerificationError("mcp_stdin_short_write")

    def _read_response(self, expected_id: int) -> Dict[str, Any]:
        if self.process.stdout is None:
            raise McpVerificationError("mcp_stdout_unavailable")
        descriptor = self.process.stdout.fileno()
        deadline = time.monotonic() + self.timeout_seconds
        with selectors.DefaultSelector() as selector:
            selector.register(descriptor, selectors.EVENT_READ)
            while b"\n" not in self.pending:
                remaining = deadline - time.monotonic()
                if remaining <= 0 or not selector.select(remaining):
                    raise McpVerificationError("mcp_timeout")
                chunk = os.read(descriptor, 65536)
                if not chunk:
                    raise McpVerificationError("mcp_eof")
                self.pending += chunk
                if len(self.pending) > self.max_message_bytes:
                    raise McpVerificationError("mcp_message_too_large")
        line, self.pending = self.pending.split(b"\n", 1)
        try:
            response = json.loads(line.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise McpVerificationError("mcp_json_invalid") from exc
        if (
            not isinstance(response, dict)
            or response.get("jsonrpc") != "2.0"
            or response.get("id") != expected_id
        ):
            raise McpVerificationError("mcp_response_id_mismatch")
        if "error" in response:
            raise McpVerificationError("mcp_jsonrpc_error")
        result = response.get("result")
        if not isinstance(result, dict):
            raise McpVerificationError("mcp_result_invalid")
        return result

    def request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        identifier = self.next_id
        self.next_id += 1
        self._write({"jsonrpc": "2.0", "id": identifier, "method": method, "params": params})
        return self._read_response(identifier)

    def notify(self, method: str, params: Dict[str, Any]) -> None:
        self._write({"jsonrpc": "2.0", "method": method, "params": params})

    def initialize(self) -> Dict[str, Any]:
        result = self.request(
            "initialize",
            {
                "protocolVersion": self.protocol_version,
                "capabilities": {},
                "clientInfo": {"name": "creator-hands", "version": "0.1"},
            },
        )
        if result.get("protocolVersion") != self.protocol_version:
            raise McpVerificationError("mcp_protocol_mismatch")
        server_info = result.get("serverInfo")
        if not isinstance(server_info, dict) or not isinstance(server_info.get("name"), str):
            raise McpVerificationError("mcp_server_identity_invalid")
        self.notify("notifications/initialized", {})
        listing = self.request("tools/list", {})
        tools = listing.get("tools")
        if not isinstance(tools, list):
            raise McpVerificationError("mcp_tools_invalid")
        names: List[str] = []
        for tool in tools:
            if not isinstance(tool, dict) or not isinstance(tool.get("name"), str):
                raise McpVerificationError("mcp_tool_descriptor_invalid")
            names.append(tool["name"])
        if len(names) != len(set(names)) or not set(MCP_REQUIRED_TOOLS).issubset(names):
            raise McpVerificationError("mcp_required_tool_missing")
        return {
            "server_identity": server_info["name"],
            "server_version": server_info.get("version"),
        }

    def call(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if name not in MCP_REQUIRED_TOOLS:
            raise McpVerificationError("mcp_tool_not_callable")
        result = self.request("tools/call", {"name": name, "arguments": arguments})
        if result.get("isError") is True:
            raise McpVerificationError("mcp_tool_failed")
        structured = result.get("structuredContent")
        if not isinstance(structured, dict):
            raise McpVerificationError("mcp_structured_result_missing")
        return structured

    def close(self) -> None:
        if self.closed:
            return
        self.closed = True
        if self.process.stdin is not None:
            try:
                self.process.stdin.close()
            except OSError:
                pass
        try:
            self.exit_code = self.process.wait(timeout=self.timeout_seconds)
        except subprocess.TimeoutExpired:
            self.forced_termination = True
            self.process.terminate()
            try:
                self.exit_code = self.process.wait(timeout=self.timeout_seconds)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.exit_code = self.process.wait(timeout=self.timeout_seconds)
        for stream in (self.process.stdout, self.process.stderr):
            if stream is not None:
                try:
                    stream.close()
                except OSError:
                    pass


def _read_full_text(
    client: _JsonLineMcpClient,
    *,
    root_label: str,
    relative_path: str,
    expected_size: int,
    max_read_calls: int,
) -> bytes:
    offset = 0
    chunks: List[bytes] = []
    calls = 0
    while True:
        calls += 1
        if calls > max_read_calls:
            raise McpVerificationError("mcp_read_call_limit")
        result = client.call(
            "read_text_file",
            {"root": root_label, "path": relative_path, "offset": offset, "max_bytes": 65536},
        )
        content = result.get("content")
        returned_offset = result.get("offset")
        bytes_read = result.get("bytes_read")
        eof = result.get("eof")
        if (
            not isinstance(content, str)
            or type(returned_offset) is not int
            or returned_offset != offset
            or type(bytes_read) is not int
            or bytes_read < 0
            or type(eof) is not bool
        ):
            raise McpVerificationError("mcp_read_result_invalid")
        encoded = content.encode("utf-8")
        if len(encoded) != bytes_read or offset + bytes_read > expected_size:
            raise McpVerificationError("mcp_read_size_invalid")
        expected_eof = offset + bytes_read >= expected_size
        if eof is not expected_eof:
            raise McpVerificationError("mcp_read_eof_invalid")
        if not eof and bytes_read == 0:
            raise McpVerificationError("mcp_read_no_progress")
        chunks.append(encoded)
        offset += bytes_read
        if eof:
            break
    if offset != expected_size:
        raise McpVerificationError("mcp_read_size_invalid")
    return b"".join(chunks)


class ReadOnlyMcpVerifier:
    """Verify worker artifacts through a separate read-only MCP stdio child.

    The caller owns the MCP server executable and launch policy. This adapter
    only calls ``stat_path``, ``sha256_file``, and ``read_text_file`` and never
    grants the task card control over server argv or environment.
    """

    name = "mcp-readonly-stdio"

    def __init__(
        self,
        *,
        server_argv_factory: ServerArgvFactory,
        root_label: str = "workspace",
        protocol_version: str = MCP_PROTOCOL_VERSION,
        timeout_seconds: float = 5.0,
        max_message_bytes: int = 1024 * 1024,
        max_read_calls: int = 1024,
    ) -> None:
        if not callable(server_argv_factory):
            raise ValueError("server_argv_factory must be callable")
        if not isinstance(root_label, str) or not root_label or any(ch.isspace() for ch in root_label):
            raise ValueError("root_label must be a non-empty token")
        if timeout_seconds <= 0 or max_message_bytes <= 0 or max_read_calls <= 0:
            raise ValueError("MCP verifier limits must be positive")
        self.server_argv_factory = server_argv_factory
        self.root_label = root_label
        self.protocol_version = protocol_version
        self.timeout_seconds = float(timeout_seconds)
        self.max_message_bytes = int(max_message_bytes)
        self.max_read_calls = int(max_read_calls)

    def verify(self, task: HandsTask, workspace: Path, artifacts: List[str]) -> Verification:
        del task
        client = None
        try:
            root = Path(workspace).resolve()
            if not root.is_dir() or root.is_symlink():
                raise McpVerificationError("workspace_invalid")
            if not artifacts:
                raise McpVerificationError("no_artifacts")

            expected: Dict[str, Dict[str, Any]] = {}
            for artifact in artifacts:
                relative = _safe_relative_path(artifact)
                path = root.joinpath(*relative.parts)
                if path.is_symlink() or not path.is_file():
                    raise McpVerificationError("artifact_missing_or_not_regular")
                raw = path.read_bytes()
                expected[relative.as_posix()] = {
                    "bytes": len(raw),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                }

            argv = self.server_argv_factory(root, self.root_label)
            client = _JsonLineMcpClient(
                argv,
                cwd=root,
                protocol_version=self.protocol_version,
                timeout_seconds=self.timeout_seconds,
                max_message_bytes=self.max_message_bytes,
            )
            metadata = client.initialize()
            verified = []
            for relative, local in expected.items():
                arguments = {"root": self.root_label, "path": relative}
                stat_result = client.call("stat_path", arguments)
                if stat_result.get("type") != "file" or type(stat_result.get("size")) is not int:
                    raise McpVerificationError("mcp_stat_result_invalid")
                hash_result = client.call("sha256_file", arguments)
                remote_digest = hash_result.get("sha256")
                remote_size = hash_result.get("size")
                if not isinstance(remote_digest, str) or type(remote_size) is not int:
                    raise McpVerificationError("mcp_hash_result_invalid")
                if remote_size != stat_result["size"] or remote_size != local["bytes"]:
                    raise McpVerificationError("mcp_size_mismatch")
                if remote_digest != local["sha256"]:
                    raise McpVerificationError("mcp_digest_mismatch")
                remote_bytes = _read_full_text(
                    client,
                    root_label=self.root_label,
                    relative_path=relative,
                    expected_size=remote_size,
                    max_read_calls=self.max_read_calls,
                )
                if hashlib.sha256(remote_bytes).hexdigest() != remote_digest:
                    raise McpVerificationError("mcp_content_integrity_mismatch")
                verified.append(
                    {"path": relative, "bytes": remote_size, "sha256": remote_digest}
                )

            client.close()
            if client.forced_termination or client.exit_code != 0:
                raise McpVerificationError("mcp_child_exit_not_clean")
            return Verification(
                True,
                self.name,
                {
                    "transport": "stdio-jsonrpc",
                    "protocol_version": self.protocol_version,
                    "server_identity": metadata["server_identity"],
                    "server_version": metadata.get("server_version"),
                    "tools_used": list(MCP_REQUIRED_TOOLS),
                    "artifacts": verified,
                    "child_exit": {"clean": True, "returncode": client.exit_code},
                },
            )
        except McpVerificationError as exc:
            return Verification(False, self.name, {"reason": str(exc)})
        except Exception:
            return Verification(False, self.name, {"reason": "mcp_runtime_failure"})
        finally:
            if client is not None and not client.closed:
                client.close()
