"""Development CLI; no device access or flashing."""
import argparse
import json
from pathlib import Path
import threading
import sys

from .core import AppError
from .i18n import tr
from .network import Client
from .service import SaveOptions, acquire


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=tr("Licorice EN Downloader 開発用CLI"))
    parser.add_argument("--download", type=Path, help=tr("検証済みBINの保存先。省略時は配布情報の照会のみ"))
    parser.add_argument("--overwrite", action="store_true", help=tr("同名ファイルを上書きする"))
    parser.add_argument("--extras", action="store_true", help=tr("XOTA・取得情報も保存"))
    args = parser.parse_args()
    cancel = threading.Event()
    try:
        release = Client().check(cancel)
        if not release:
            print(tr("現在取得できる配布物がありません。"))
            return
        print(json.dumps({"device": release.device.name, "version": release.version,
                          "size": release.size, "sha256": release.sha256}, ensure_ascii=False))
        if args.download:
            result = acquire(release, args.download, SaveOptions(args.extras, args.extras, args.overwrite), cancel,
                             lambda kind, value: print(value) if kind == "stage" else None)
            print(json.dumps({"saved": str(result.path), "verification": result.verification,
                              "warnings": result.warnings}, ensure_ascii=False))
    except AppError as exc:
        print(f"{exc.code}: {exc}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
