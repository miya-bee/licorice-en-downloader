"""Portable settings and atomic, collision-aware file writes."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import os
from pathlib import Path, PureWindowsPath
import re
import sys
import tempfile
import threading

from .core import AppError, Cancelled
from .i18n import LANGUAGES, tr


def app_directory() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def atomic_write(path: Path, data: bytes, overwrite: bool = False, *, cancel: threading.Event | None = None) -> None:
    """Keep an existing file intact until a complete replacement is ready."""
    temporary = None
    try:
        if cancel is not None and cancel.is_set():
            raise Cancelled()
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".licorice-", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if cancel is not None and cancel.is_set():
            raise Cancelled()
        if overwrite:
            os.replace(temporary, path)
        elif os.name == "nt":
            os.rename(temporary, path)  # Windows rename refuses an existing destination.
        else:
            os.link(temporary, path)  # POSIX rename would silently replace it.
            temporary.unlink()
        temporary = None
    except FileExistsError:
        raise AppError("exists", tr("同名ファイルがあります。保存先と上書きの指定を確認してください。")) from None
    except OSError:
        raise AppError("save", tr("ファイルを保存できません。空き容量・書き込み権限・ファイルが使用中でないか確認してください。")) from None
    finally:
        if temporary:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass


def validate_destination(value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("destination")
    value.encode("utf-8")
    path = PureWindowsPath(value)
    if ((path.drive or path.root) and not path.is_absolute()) or ".." in path.parts:
        raise ValueError("relative destination")
    for part in path.parts:
        if part == path.anchor:
            continue
        if (any(ord(char) < 32 or char in '<>:"|?*' for char in part)
                or part.endswith((" ", ".")) or PureWindowsPath(part).is_reserved()):
            raise ValueError("destination component")


@dataclass
class Settings:
    destination: str = "downloads"
    save_xota: bool = False
    save_metadata: bool = False
    geometry: str = "920x830"
    protected: bool = False
    language: str = "auto"

    def destination_path(self, base: Path) -> Path:
        path = Path(self.destination)
        return path if path.is_absolute() else base / path

    def set_destination(self, path: Path, base: Path):
        try:
            self.destination = str(path.resolve().relative_to(base.resolve()))
        except ValueError:
            self.destination = str(path.resolve())

    def save(self, base: Path):
        if self.protected:
            raise AppError("settings", tr("元の設定を安全に保管できないため、自動上書きを停止しています。"))
        try:
            validate_destination(self.destination)
        except (ValueError, TypeError):
            raise AppError("settings", tr("保存先の設定が不正です。保存先を選び直してください。")) from None
        payload = {"schema_version": 1, "destination": self.destination,
                   "save_xota": self.save_xota, "save_metadata": self.save_metadata,
                   "geometry": self.geometry, "language": self.language}
        atomic_write(base / "settings.json", json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"), True)

    @classmethod
    def load(cls, base: Path) -> tuple[Settings, str]:
        path = base / "settings.json"
        try:
            if not path.exists():
                return cls(), ""
            if path.stat().st_size > 65536:
                return cls(protected=True), tr("設定ファイルが大きすぎます。元の設定を保持し、自動上書きを停止しました。")
            # utf-8-sig: accept a BOM written by editors such as older Notepad.
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
            if type(payload.get("schema_version")) is not int or payload["schema_version"] != 1:
                return cls(protected=True), tr("この設定形式には未対応です。元の設定を保持し、自動上書きを停止しました。")
            destination = payload["destination"]
            validate_destination(destination)
            for key in ("save_xota", "save_metadata"):
                if type(payload[key]) is not bool:
                    raise ValueError(key)
            geometry = str(payload.get("geometry", "920x830"))
            if not re.fullmatch(r"\d{3,4}x\d{3,4}(?:[+-]\d{1,5}[+-]\d{1,5})?", geometry):
                geometry = "920x830"
            # Optional key added with English support; older files stay schema 1.
            language = payload.get("language", "auto")
            if language not in LANGUAGES:
                language = "auto"
            return cls(destination, payload["save_xota"], payload["save_metadata"], geometry,
                       language=language), ""
        except (OSError, ValueError, KeyError, TypeError, AttributeError, RecursionError):
            # Copy instead of moving: an unreadable/unwritable file stays intact.
            try:
                backup = base / f"settings.broken-{datetime.now():%Y%m%d-%H%M%S-%f}.json"
                atomic_write(backup, path.read_bytes())
                return cls(), tr("設定を読み取れませんでした。元の設定を別名で保管し、初期設定で起動しました。")
            except (OSError, AppError):
                return cls(protected=True), tr("設定を読み取れませんでした。元の設定を保持し、自動上書きを停止しました。")
