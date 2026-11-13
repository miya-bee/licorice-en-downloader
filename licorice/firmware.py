"""Read-only XOTA extraction and ESP32-S3 image verification.

Format/key derivation based on crosspoint-reader/crosspoint-tools xota.rs (MIT).
See THIRD_PARTY_NOTICES.md. No packaging, encryption or flashing is provided.
"""
from __future__ import annotations

import hashlib
import struct
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from .core import AppError, Release

KEY_TABLES = (
    bytes.fromhex("2a28d5e48a2ba85804a5bf786c8c6391"),
    bytes.fromhex("ea915660e42d5176c2333dea482a53fa"),
)


def derive_key(channel: int) -> bytes:
    if type(channel) is not int or not 0 <= channel < len(KEY_TABLES):
        raise AppError("format", "このOTA種別には対応していません。")
    return bytes(value ^ ((17 * i - 0x5B) & 255)
                 for i, value in enumerate(KEY_TABLES[channel]))


def _cstring(data: bytes) -> str:
    value, separator, _ = data.partition(b"\0")
    if not separator:
        raise AppError("metadata", "XOTAの機種情報を読み取れません。")
    try:
        return value.decode("ascii")
    except UnicodeError:
        raise AppError("metadata", "XOTAの機種情報が不正です。") from None


def verify_esp_image(image: bytes, chip: int) -> dict:
    def fail(message: str):
        raise AppError("image", message)

    if len(image) < 24 or image[0] != 0xE9 or not 1 <= image[1] <= 16:
        fail("対応するESPアプリイメージではありません。")
    if struct.unpack_from("<H", image, 12)[0] != chip or image[23] != 1:
        fail("ESPチップ情報またはイメージのSHA-256設定が対応していません。")
    offset, checksum = 24, 0xEF
    descriptor = None
    for index in range(image[1]):
        if offset + 8 > len(image):
            fail("ESPセグメントヘッダーが途中で切れています。")
        _, length = struct.unpack_from("<II", image, offset)
        offset += 8
        if length > len(image) - offset:
            fail("ESPセグメントのサイズが不正です。")
        segment = image[offset:offset + length]
        if index == 0:
            if len(segment) < 80 or segment[:4] != b"\x32\x54\xcd\xab":
                fail("ESPアプリ記述情報を確認できません。")
            descriptor = segment
        for byte in segment:
            checksum ^= byte
        offset += length
    checksum_at = ((offset + 16) // 16) * 16 - 1
    if checksum_at + 33 != len(image):
        fail("ESPイメージの末尾サイズが不正です。")
    if any(image[offset:checksum_at]) or image[checksum_at] != checksum:
        fail("ESPイメージのXORチェックサムが一致しません。")
    if hashlib.sha256(image[:checksum_at + 1]).digest() != image[checksum_at + 1:]:
        fail("ESPイメージ末尾のSHA-256が一致しません。")
    return {"chip_id": chip, "segments": image[1],
            "app_version": descriptor[16:48].split(b"\0", 1)[0].decode("utf-8", "replace"),
            "project": descriptor[48:80].split(b"\0", 1)[0].decode("utf-8", "replace")}


def extract_xota(package: bytes, release: Release) -> tuple[bytes, dict]:
    if len(package) != release.size or package[:4] != b"XOTA":
        raise AppError("package", "XOTAのサイズまたは先頭の形式が一致しません。")
    decryptor = Cipher(algorithms.AES(derive_key(release.ota_type)),
                       modes.CTR(package[4:20])).decryptor()
    decoded = decryptor.update(package[20:]) + decryptor.finalize()
    meta, image = decoded[:182], decoded[182:]
    if (struct.unpack_from("<I", meta)[0] != release.plain_size
            or meta[36:38] != bytes((release.ota_type, 0))
            or meta[4:36].hex() != release.sha256):
        raise AppError("metadata", "XOTA内部情報と配布情報が一致しません。")
    device, variant = _cstring(meta[70:94]), _cstring(meta[94:118])
    if device != release.device.image_device or variant != release.device.package_variant:
        raise AppError("device", "XOTA内部の対象機種が一致しません。")
    if len(image) != release.plain_size or hashlib.sha256(image).hexdigest() != release.sha256:
        raise AppError("hash", "抽出したBINのサイズまたはSHA-256が一致しません。保存を中止しました。")
    info = verify_esp_image(image, release.device.esp_chip)
    info.update({"metadata_version": _cstring(meta[38:70]), "device_type": device,
                 "package_variant": variant, "plain_sha256": release.sha256,
                 "xota_sha256": hashlib.sha256(package).hexdigest()})
    return image, info
