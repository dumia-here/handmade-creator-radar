from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Callable

from .errors import ErrorCode


class ArtifactWriteError(RuntimeError):
    def __init__(self, reason_code: ErrorCode):
        super().__init__(reason_code.value)
        self.reason_code = reason_code


def atomic_write_new(
    path: Path,
    text: str,
    *,
    validator: Callable[[Path], None] | None = None,
    replace_func: Callable[[str, str], None] = os.replace,
) -> None:
    if path.exists():
        raise ArtifactWriteError(ErrorCode.OUTPUT_ALREADY_EXISTS)
    if not path.parent.is_dir():
        raise ArtifactWriteError(ErrorCode.INTERNAL_ERROR)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, prefix=".radar-", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        if validator:
            validator(temporary)
        replace_func(str(temporary), str(path))
        temporary = None
    except ArtifactWriteError:
        raise
    except Exception as exc:
        raise ArtifactWriteError(ErrorCode.INTERNAL_ERROR) from exc
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def atomic_write_json_new(path: Path, payload: dict[str, Any]) -> None:
    atomic_write_new(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n", validator=_validate_json)


def atomic_replace_json(path: Path, payload: dict[str, Any]) -> None:
    if not path.parent.is_dir():
        raise ArtifactWriteError(ErrorCode.INTERNAL_ERROR)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, prefix=".radar-state-", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        _validate_json(temporary)
        os.replace(str(temporary), str(path))
        temporary = None
    except Exception as exc:
        raise ArtifactWriteError(ErrorCode.INTERNAL_ERROR) from exc
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def _validate_json(path: Path) -> None:
    json.loads(path.read_text(encoding="utf-8"))
