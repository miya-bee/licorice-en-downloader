"""GUI-independent download, verification and saving workflow."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import threading
from urllib.parse import urlsplit, urlunsplit

from . import APP_NAME, __version__
from .core import AppError, Release
from .firmware import extract_xota
from .network import Client, check_cancel
from .storage import atomic_write


@dataclass(frozen=True)
class SaveOptions:
    xota: bool = False
    metadata: bool = False
    overwrite: bool = False
    approved_overwrites: frozenset[str] | None = None

    def may_overwrite(self, path: Path) -> bool:
        return self.overwrite and (self.approved_overwrites is None or path.name in self.approved_overwrites)


@dataclass
class DownloadResult:
    path: Path
    verification: dict
    warnings: list[str]


def output_paths(release: Release, directory: Path, options: SaveOptions) -> list[Path]:
    extensions = [".bin"]
    if options.xota:
        extensions.append(".xota")
    if options.metadata:
        extensions.append(".json")
    return [directory / (release.stem + ext) for ext in extensions]


def acquire(release: Release, directory: Path, options: SaveOptions,
            cancel: threading.Event, emit=lambda kind, data: None,
            client: Client | None = None) -> DownloadResult:
    check_cancel(cancel)
    targets = output_paths(release, directory, options)
    try:
        directory.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryFile(dir=directory):
            pass
    except OSError:
        raise AppError("save", "保存先に書き込めません。別のフォルダを選んでください。") from None
    if any(path.exists() and not options.may_overwrite(path) for path in targets):
        raise AppError("exists", "同名ファイルがあります。保存先と上書きの指定を確認してください。")
    emit("stage", "公式配布先からダウンロードしています…")
    package = (client or Client()).download(release, cancel,
                   lambda current, total: emit("progress", (current, total)))
    check_cancel(cancel)
    emit("stage", "XOTAを復号・抽出し、BINを検証しています…")
    image, verification = extract_xota(package, release)
    check_cancel(cancel)
    emit("stage", "検証済みBINを保存しています…")
    # Cancellation before commit leaves the previous BIN intact. Once committed,
    # finish the optional writes and report success rather than 'cancelled'.
    atomic_write(targets[0], image, options.may_overwrite(targets[0]), cancel=cancel)
    warnings = []
    if options.xota:
        try:
            path = directory / (release.stem + ".xota")
            atomic_write(path, package, options.may_overwrite(path))
        except AppError:
            warnings.append("元のXOTAを追加保存できませんでした。BINは保存済みです。")
    if options.metadata:
        parsed = urlsplit(release.url)
        payload = {"schema_version": 1, "app": APP_NAME, "app_version": __version__,
                   "device": release.device.id, "distribution": "EN", "version": release.version,
                   "source": urlunsplit(parsed._replace(query="", fragment="")),
                   "checked_at": release.checked, "upload_time_original": release.uploaded,
                   "saved_at": datetime.now(timezone.utc).isoformat(),
                   "xota_size": release.size, "plain_size": release.plain_size,
                   "verification": verification, "change_log": release.changelog}
        try:
            path = directory / (release.stem + ".json")
            atomic_write(path, json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"), options.may_overwrite(path))
        except AppError:
            warnings.append("取得情報JSONを追加保存できませんでした。BINは保存済みです。")
    return DownloadResult(targets[0], verification, warnings)
