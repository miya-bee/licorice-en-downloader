"""Offline regression tests. No vendor firmware is distributed as a fixture."""
from dataclasses import replace
import hashlib
import io
import json
from pathlib import Path
import struct
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import URLError

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from licorice.core import AppError, Cancelled, Release, X4_PRO, validate_url
from licorice.firmware import derive_key, extract_xota, verify_esp_image
from licorice.network import Client, ValidatedRedirect
from licorice.service import SaveOptions, acquire
from licorice.storage import Settings, atomic_write


def sample_image():
    header = bytearray(24)
    header[0:2] = b"\xe9\x01"
    header[12:14] = struct.pack("<H", 9)
    header[23] = 1
    segment = bytearray(192)
    segment[:4] = bytes.fromhex("3254cdab")
    segment[16:20] = b"test"
    segment[48:54] = b"sample"
    image = bytes(header) + struct.pack("<II", 0x3C000020, len(segment)) + segment
    xor = 0xEF
    for byte in segment:
        xor ^= byte
    image += b"\0" * ((15 - len(image) % 16) % 16) + bytes([xor])
    return image + hashlib.sha256(image).digest()


def sample():
    image = sample_image()
    digest = hashlib.sha256(image).hexdigest()
    payload = {"code": 0, "data": {
        "version": "26111201", "download_url": "https://" + X4_PRO.file_host +
        "/firmware/encrypted/ESP32S3_X4_TL_Licorice/test/ota_type_1/XT%20Licorice%2026111201-X4PRO-EN-PROD-test.xota",
        "size": len(image) + 202, "plain_size": len(image), "plain_sha256": digest,
        "checksum": {"sha256": digest}, "ota_format": "encrypted_v1", "ota_type": 1,
        "change_log": "Test", "upload_time": "2026-11-12T06:14:23"}}
    release = Release.parse(payload)
    meta = bytearray(182)
    struct.pack_into("<I", meta, 0, len(image))
    meta[4:36] = bytes.fromhex(digest)
    meta[36] = 1
    meta[38:46] = b"26111202"  # Public and internal versions legitimately differ.
    meta[70:83] = b"ESP32S3_X4_TL"
    meta[94:102] = b"Licorice"
    iv = bytes(range(16))
    enc = Cipher(algorithms.AES(derive_key(1)), modes.CTR(iv)).encryptor()
    package = b"XOTA" + iv + enc.update(bytes(meta) + image) + enc.finalize()
    return payload, release, image, package


class Response(io.BytesIO):
    status = 200

    def __init__(self, data, headers=None):
        super().__init__(data)
        self.headers = headers or {}


class FakeClient:
    def __init__(self, package):
        self.package = package

    def download(self, release, cancel, progress):
        progress(len(self.package), release.size)
        return self.package


class ManifestTests(unittest.TestCase):
    def test_valid_manifest(self):
        _, release, _, _ = sample()
        self.assertEqual(release.stem, "XT_Licorice_26111201_X4Pro_EN")

    def test_rejects_wrong_distribution_and_model(self):
        for original, replacement in [("-EN-", "-CH-"), ("-X4PRO-", "-X4C-"),
                                      ("ESP32S3_X4_TL_Licorice", "ESP32S3_X4_CLA_Licorice")]:
            with self.subTest(original=original):
                payload, _, _, _ = sample()
                payload["data"]["download_url"] = payload["data"]["download_url"].replace(original, replacement)
                with self.assertRaises(AppError):
                    Release.parse(payload)

    def test_rejects_inconsistent_manifest(self):
        for field, value in [("size", 1), ("plain_size", True), ("ota_type", 0),
                             ("ota_format", "new_format"), ("plain_sha256", "bad"),
                             ("version", "../../other"), ("version", "..")]:
            payload, _, _, _ = sample()
            payload["data"][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(AppError):
                Release.parse(payload)

    def test_checksum_conflict(self):
        payload, _, _, _ = sample()
        payload["data"]["checksum"]["sha256"] = "0" * 64
        with self.assertRaises(AppError):
            Release.parse(payload)

    def test_no_update_distinguished_from_malformed(self):
        self.assertIsNone(Release.parse({"code": 0, "data": None, "message": "No update available"}))
        for payload in [{"code": 0}, {"code": 0, "data": None, "message": "Error"},
                        {"code": 9, "data": None}, [], {"code": False, "data": None}]:
            with self.subTest(payload=payload), self.assertRaises(AppError):
                Release.parse(payload)

    def test_trusted_url_only(self):
        for url in ["http://" + X4_PRO.file_host, "https://" + X4_PRO.file_host + ".evil.test/fw",
                    "https://user:secret@" + X4_PRO.file_host, "https://" + X4_PRO.file_host + ":444/fw"]:
            with self.subTest(url=url), self.assertRaises(AppError):
                validate_url(url, X4_PRO.file_host)

    def test_redirect_cannot_escape_host(self):
        with self.assertRaises(AppError):
            ValidatedRedirect(X4_PRO.file_host).redirect_request(None, None, 302, "", {}, "https://other.test/fw")


class FirmwareTests(unittest.TestCase):
    def test_extracts_unmodified_image_and_keeps_internal_version(self):
        _, release, image, package = sample()
        extracted, info = extract_xota(package, release)
        self.assertEqual(image, extracted)
        self.assertEqual(info["metadata_version"], "26111202")
        self.assertEqual(info["project"], "sample")

    def test_truncation_and_payload_corruption(self):
        _, release, _, package = sample()
        broken = bytearray(package)
        broken[-10] ^= 1
        for content in (package[:-1], bytes(broken), b"NOPE" + package[4:]):
            with self.assertRaises(AppError):
                extract_xota(content, release)

    def test_rejects_wrong_device_even_if_hash_matches(self):
        _, release, _, package = sample()
        device = replace(release.device, image_device="ESP32S3_X4_CLA")
        with self.assertRaises(AppError) as caught:
            extract_xota(package, replace(release, device=device))
        self.assertEqual(caught.exception.code, "device")

    def test_checks_esp_integrity_independently_of_manifest_hash(self):
        image = bytearray(sample_image())
        image[-1] ^= 1
        with self.assertRaises(AppError):
            verify_esp_image(bytes(image), 9)

    def test_rejects_wrong_chip_missing_descriptor_and_extra_padding(self):
        image = sample_image()
        for content, chip in [(image, 5), (image + b"\xff" * 16, 9),
                              (image[:32] + b"BAD!" + image[36:], 9)]:
            with self.assertRaises(AppError):
                verify_esp_image(content, chip)


class StorageAndWorkflowTests(unittest.TestCase):
    def test_no_overwrite_without_permission(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "既存.bin"
            path.write_bytes(b"original")
            with self.assertRaises(AppError):
                atomic_write(path, b"replacement")
            self.assertEqual(path.read_bytes(), b"original")
            self.assertEqual(list(Path(folder).glob("*.tmp")), [])
            atomic_write(path, b"replacement", True)
            self.assertEqual(path.read_bytes(), b"replacement")

    def test_replace_failure_preserves_previous_and_removes_temporary(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "image.bin"
            path.write_bytes(b"original")
            with patch("licorice.storage.os.replace", side_effect=PermissionError), self.assertRaises(AppError):
                atomic_write(path, b"replacement", True)
            self.assertEqual(path.read_bytes(), b"original")
            self.assertEqual(list(Path(folder).glob("*.tmp")), [])

    def test_portable_settings_and_external_paths(self):
        with tempfile.TemporaryDirectory(prefix="日本語 path ") as folder:
            base = Path(folder)
            settings = Settings()
            settings.set_destination(base / "downloads" / "FW", base)
            settings.save(base)
            loaded, warning = Settings.load(base)
            self.assertFalse(warning)
            self.assertFalse(Path(loaded.destination).is_absolute())
            moved = base / "移動後"
            self.assertEqual(loaded.destination_path(moved), moved / "downloads" / "FW")
            settings.set_destination(base.parent / "external", base)
            self.assertTrue(Path(settings.destination).is_absolute())

    def test_broken_settings_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            (base / "settings.json").write_bytes(b"{broken")
            settings, warning = Settings.load(base)
            self.assertTrue(warning)
            backups = list(base.glob("settings.broken-*.json"))
            self.assertEqual(len(backups), 1)
            settings.save(base)
            self.assertEqual(backups[0].read_bytes(), b"{broken")

    def test_future_settings_not_destroyed(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            (base / "settings.json").write_text('{"schema_version": 999}', encoding="utf-8")
            settings, _ = Settings.load(base)
            with self.assertRaises(AppError):
                settings.save(base)
            self.assertEqual(json.loads((base / "settings.json").read_text())["schema_version"], 999)

    def test_workflow_writes_verified_image_and_optional_files(self):
        _, release, image, package = sample()
        with tempfile.TemporaryDirectory(prefix="FW 保存 ") as folder:
            result = acquire(release, Path(folder), SaveOptions(True, True), threading.Event(), client=FakeClient(package))
            self.assertEqual(result.path.read_bytes(), image)
            self.assertEqual(result.path.with_suffix(".xota").read_bytes(), package)
            info = json.loads(result.path.with_suffix(".json").read_text(encoding="utf-8"))
            self.assertEqual(info["version"], release.version)
            self.assertEqual(result.warnings, [])

    def test_failed_validation_preserves_existing_file(self):
        _, release, _, package = sample()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / (release.stem + ".bin")
            path.write_bytes(b"old")
            with self.assertRaises(AppError):
                acquire(release, Path(folder), SaveOptions(overwrite=True), threading.Event(), client=FakeClient(package[:-1]))
            self.assertEqual(path.read_bytes(), b"old")

    def test_cancellation_before_commit_preserves_existing(self):
        _, release, _, package = sample()
        with tempfile.TemporaryDirectory() as folder:
            cancel = threading.Event()
            path = Path(folder) / (release.stem + ".bin")
            path.write_bytes(b"old")
            def emit(kind, value):
                if kind == "progress":
                    cancel.set()
            with self.assertRaises(Cancelled):
                acquire(release, Path(folder), SaveOptions(overwrite=True), cancel, emit, FakeClient(package))
            self.assertEqual(path.read_bytes(), b"old")

    def test_optional_save_failure_is_partial_success(self):
        _, release, image, package = sample()
        with tempfile.TemporaryDirectory() as folder:
            real_write = atomic_write
            def save(path, content, overwrite=False, **kwargs):
                if path.suffix == ".xota":
                    raise AppError("save", "failed")
                real_write(path, content, overwrite, **kwargs)
            with patch("licorice.service.atomic_write", side_effect=save):
                result = acquire(release, Path(folder), SaveOptions(xota=True), threading.Event(), client=FakeClient(package))
            self.assertEqual(result.path.read_bytes(), image)
            self.assertEqual(len(result.warnings), 1)


class NetworkTests(unittest.TestCase):
    def test_query_contains_empty_id_and_no_real_device_identity(self):
        payload, release, _, _ = sample()
        client = Client()
        with patch.object(client, "open", return_value=Response(json.dumps(payload).encode())) as opened:
            result = client.check(threading.Event())
        query_url = opened.call_args.args[0]
        self.assertIn("device_id=&", query_url)
        self.assertIn("current_version=V0.0.0", query_url)
        self.assertEqual(result.version, release.version)

    def test_receive_limit_and_short_read(self):
        client = Client()
        for data, expected in [(b"12345", 4), (b"12", 4)]:
            with patch.object(client, "open", return_value=Response(data)), self.assertRaises(AppError):
                client._read("https://test", "test", 4, threading.Event(), expected=expected)

    def test_declared_size_mismatch(self):
        client = Client()
        with patch.object(client, "open", return_value=Response(b"1234", {"Content-Length": "5"})), self.assertRaises(AppError):
            client._read("https://test", "test", 4, threading.Event(), expected=4)

    def test_retry_is_bounded(self):
        client = Client()
        with patch.object(client, "open", side_effect=URLError("offline")) as opened, \
                patch.object(threading.Event, "wait", return_value=False), self.assertRaises(AppError):
            client.check(threading.Event())
        self.assertEqual(opened.call_count, 2)

    def test_already_cancelled_performs_no_network_io(self):
        cancel = threading.Event()
        cancel.set()
        client = Client()
        with patch.object(client, "open") as opened, self.assertRaises(Cancelled):
            client.check(cancel)
        opened.assert_not_called()


if __name__ == "__main__":
    unittest.main()
