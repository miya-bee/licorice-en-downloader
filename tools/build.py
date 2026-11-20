"""Reproducible local Windows development packaging; never publishes anything."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import sysconfig
import tempfile
import zipfile

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
from licorice import __version__


def copy_package_licenses(package, destination):
    dist = importlib.metadata.distribution(package)
    count = 0
    for entry in dist.files or []:
        if "license" in str(entry).lower() and dist.locate_file(entry).is_file():
            source = dist.locate_file(entry)
            # Preserve license path structure; avoid flattening same-name files.
            relative = Path(*entry.parts[1:]) if ".dist-info" in entry.parts[0] else Path(*entry.parts)
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            count += 1
    if count == 0:
        raise RuntimeError(f"{package}: license files not found")


def main():
    if sys.platform != "win32":
        raise SystemExit("Windows上で実行してください。")
    if sysconfig.get_platform().lower() != "win-amd64":
        raise SystemExit("windows-x64版のビルドには、Windows x64版Pythonを使用してください。")
    subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], cwd=BASE, check=True)
    dist, build = BASE / "dist", BASE / "build"
    build.mkdir(exist_ok=True)
    dist.mkdir(exist_ok=True)
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--onefile", "--windowed",
                    "--name", "LicoriceENDownloader", "--distpath", str(dist / "exe"),
                    "--workpath", str(build / "pyinstaller"), "--specpath", str(build), str(BASE / "main.py")],
                   cwd=BASE, check=True)
    # A fresh staging directory prevents settings/logs/FW from leaking into ZIPs.
    with tempfile.TemporaryDirectory(prefix="package-", dir=build) as temporary:
        stage = Path(temporary) / "LicoriceENDownloader"
        stage.mkdir()
        shutil.copy2(dist / "exe" / "LicoriceENDownloader.exe", stage)
        for name in ("はじめに.txt", "README.txt", "LICENSE", "THIRD_PARTY_NOTICES.md", "BUG_AUDIT.md"):
            shutil.copy2(BASE / name, stage)
        shutil.copytree(BASE / "docs", stage / "docs")
        shutil.copytree(BASE / "licenses", stage / "licenses")
        copy_package_licenses("cryptography", stage / "licenses" / "cryptography")
        copy_package_licenses("pyinstaller", stage / "licenses" / "pyinstaller")
        python_license = Path(sys.base_prefix) / "LICENSE.txt"
        if not python_license.is_file():
            raise RuntimeError("Python LICENSE.txt not found")
        shutil.copy2(python_license, stage / "licenses" / "Python-LICENSE.txt")
        for name in ("tcl8.6", "tk8.6"):
            candidates = [Path(sys.base_prefix) / "tcl" / name / "license.terms",
                          Path(sys.base_prefix) / "tcl" / name / "license.txt"]
            if name == "tcl8.6":
                import tkinter
                interpreter = tkinter.Tcl()
                if interpreter.call("info", "patchlevel") == "8.6.12":
                    candidates.append(BASE / "licenses" / "tcl8.6.12-license.terms")
            source = next((p for p in candidates if p.is_file()), None)
            if source is None:
                raise RuntimeError(f"{name} license not found")
            shutil.copy2(source, stage / "licenses" / f"{name}-license.terms")
        info = {"app_version": __version__, "python": sys.version, "platform": platform.platform(),
                "cryptography": importlib.metadata.version("cryptography"),
                "pyinstaller": importlib.metadata.version("pyinstaller"), "development_build": True}
        (stage / "BUILD_INFO.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
        zip_path = dist / f"LicoriceENDownloader-v{__version__}-windows-x64-dev.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for source in sorted(stage.rglob("*")):
                if source.is_file():
                    archive.write(source, source.relative_to(stage.parent))
        digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
        zip_path.with_suffix(".zip.sha256").write_text(f"{digest}  {zip_path.name}\n", encoding="ascii")
        print(zip_path)
        print(digest)


if __name__ == "__main__":
    main()
