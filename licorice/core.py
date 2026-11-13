"""Device definitions and strict interpretation of vendor update manifests."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from urllib.parse import unquote, urlsplit


class AppError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class Cancelled(AppError):
    def __init__(self):
        super().__init__("cancelled", "処理を中止しました。")


@dataclass(frozen=True)
class Device:
    id: str
    name: str
    model: str
    image_device: str
    package_variant: str
    esp_chip: int
    max_image: int
    filename_tag: str
    distribution_tag: str
    api_host: str = "api-prod.xteink.cc"
    file_host: str = "overseas-static-file.oss-ap-southeast-1.aliyuncs.com"
    ota_type: int = 1


X4_PRO = Device("x4pro", "X4 Pro", "ESP32S3_X4_TL_Licorice",
                "ESP32S3_X4_TL", "Licorice", 9, 0x7E0000, "X4Pro", "X4PRO")
DEVICES = {X4_PRO.id: X4_PRO}


def validate_url(url: str, host: str) -> None:
    try:
        if not isinstance(url, str) or any(ord(char) < 32 or ord(char) == 127 for char in url):
            raise ValueError("url")
        url.encode("utf-8")
        parsed = urlsplit(url)
        valid = (parsed.scheme == "https" and parsed.hostname == host
                 and parsed.port in (None, 443) and not parsed.username
                 and not parsed.password and not parsed.fragment)
    except (ValueError, TypeError):
        valid = False
    if not valid:
        raise AppError("source", "対応する公式HTTPS配布先ではありません。配布情報を再確認してください。")


@dataclass(frozen=True)
class Release:
    device: Device
    version: str
    url: str
    size: int
    plain_size: int
    sha256: str
    changelog: str
    uploaded: str
    checked: str
    ota_type: int

    @property
    def stem(self) -> str:
        return f"XT_Licorice_{self.version}_{self.device.filename_tag}_EN"

    @classmethod
    def parse(cls, payload: object, device: Device = X4_PRO) -> Release | None:
        if not isinstance(payload, dict) or type(payload.get("code")) is not int or payload["code"] != 0:
            raise AppError("api", "公式APIが正常な配布情報を返しませんでした。後ほど再確認してください。")
        if "data" not in payload:
            raise AppError("api", "API応答に配布情報の項目がありません。")
        data = payload["data"]
        if data is None:
            if str(payload.get("message", "")).lower().strip() in {
                "no update available", "no update available."}:
                return None
            raise AppError("api", "配布情報が空でした。応答の意味を確認できません。")
        try:
            version = data["version"]
            if not isinstance(version, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,47}", version):
                raise ValueError("version")
            url = data["download_url"]
            validate_url(url, device.file_host)
            path = unquote(urlsplit(url).path)
            if (f"/firmware/encrypted/{device.model}/" not in path
                    or f"/ota_type_{device.ota_type}/" not in path
                    or not path.endswith(".xota") or "-EN-PROD-" not in path
                    or f"-{device.distribution_tag}-" not in path):
                raise ValueError("target")
            size, plain_size, ota = data["size"], data["plain_size"], data["ota_type"]
            if (type(size) is not int or type(plain_size) is not int
                    or not 256 <= plain_size <= device.max_image or size != plain_size + 202
                    or type(ota) is not int or ota != device.ota_type
                    or data["ota_format"] != "encrypted_v1"):
                raise ValueError("format")
            digest = data["plain_sha256"]
            if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", digest):
                raise ValueError("sha256")
            # The current vendor API's checksum.sha256 describes the PLAINTEXT.
            alternate = data.get("checksum", {}).get("sha256")
            if alternate and alternate.lower() != digest.lower():
                raise ValueError("checksum conflict")
            changelog, uploaded = data.get("change_log", ""), data.get("upload_time", "")
            if not isinstance(changelog, str) or not isinstance(uploaded, str):
                raise ValueError("text")
            changelog.encode("utf-8")
            uploaded.encode("utf-8")
        except AppError:
            raise
        except (KeyError, ValueError, TypeError, AttributeError):
            raise AppError("manifest", "X4 Pro用Licorice EN版の配布情報を検証できません。未対応の形式または情報の不一致です。") from None
        return cls(device, version, url, size, plain_size, digest.lower(), changelog,
                   uploaded, datetime.now(timezone.utc).isoformat(), ota)
