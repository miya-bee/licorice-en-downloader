"""Regressions for defects reproduced during the v0.1.1 bug audit."""
import io
import json
from http.client import BadStatusLine
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import URLError

from licorice.core import AppError, Cancelled, Release
from licorice.network import Client
from licorice.service import SaveOptions, acquire
from licorice.storage import Settings
from test_workflow import FakeClient, Response, sample


class AuditTests(unittest.TestCase):
    def test_overwrite_permission_does_not_cover_a_new_unapproved_bin(self):
        _, release, _, package = sample()
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            target = base / (release.stem + ".bin")
            original_xota = base / (release.stem + ".xota")
            original_xota.write_bytes(b"previous xota")
            class RacingClient(FakeClient):
                def download(self, release, cancel, progress):
                    target.write_bytes(b"created by another operation")
                    return super().download(release, cancel, progress)
            options = SaveOptions(xota=True, overwrite=True,
                                  approved_overwrites=frozenset({original_xota.name}))
            with self.assertRaises(AppError) as caught:
                acquire(release, base, options, threading.Event(), client=RacingClient(package))
            self.assertEqual(caught.exception.code, "exists")
            self.assertEqual(target.read_bytes(), b"created by another operation")
            self.assertEqual(original_xota.read_bytes(), b"previous xota")

    def test_cancellation_during_file_sync_does_not_replace_existing_bin(self):
        _, release, _, package = sample()
        cancel = threading.Event()
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / (release.stem + ".bin")
            target.write_bytes(b"previous good firmware")
            with patch("licorice.storage.os.fsync", side_effect=lambda fd: cancel.set()):
                with self.assertRaises(Cancelled):
                    acquire(release, Path(folder), SaveOptions(overwrite=True), cancel, client=FakeClient(package))
            self.assertEqual(target.read_bytes(), b"previous good firmware")
            self.assertFalse(list(Path(folder).glob("*.tmp")))

    def test_surrogate_in_settings_is_recovered_before_gui_or_save(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            payload = {"schema_version": 1, "destination": "\ud800", "save_xota": False, "save_metadata": False}
            original = json.dumps(payload).encode("ascii")
            (base / "settings.json").write_bytes(original)
            settings, warning = Settings.load(base)
            self.assertTrue(warning)
            self.assertEqual(settings.destination, "downloads")
            settings.save(base)
            self.assertEqual(next(base.glob("settings.broken-*.json")).read_bytes(), original)

    def test_settings_access_failure_does_not_abort_startup(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(Path, "exists", side_effect=PermissionError):
                settings, warning = Settings.load(Path(folder))
            self.assertTrue(warning)
            self.assertTrue(settings.protected)

    def test_drive_relative_and_escaping_portable_paths_are_rejected(self):
        for destination in ("C:downloads", "\\downloads", "..\\outside", "bad?folder", "downloads. "):
            with self.subTest(destination=destination), tempfile.TemporaryDirectory() as folder:
                base = Path(folder)
                (base / "settings.json").write_text(json.dumps({"schema_version": 1,
                    "destination": destination, "save_xota": False, "save_metadata": False}), encoding="utf-8")
                settings, warning = Settings.load(base)
                self.assertTrue(warning)
                self.assertEqual(settings.destination, "downloads")

    def test_malformed_unicode_manifest_never_reaches_tk_or_url_encoder(self):
        for field in ("download_url", "change_log", "upload_time"):
            payload, _, _, _ = sample()
            payload["data"][field] += "\ud800"
            with self.subTest(field=field), self.assertRaises(AppError):
                Release.parse(payload)

    def test_cancelled_network_failure_is_reported_as_cancelled(self):
        cancel = threading.Event()
        client = Client()
        client.attempts = 1
        def fail(*args):
            cancel.set()
            raise URLError("connection interrupted")
        with patch.object(client, "open", side_effect=fail), self.assertRaises(Cancelled):
            client.check(cancel)

    def test_download_uses_single_read_so_slow_stream_can_be_cancelled(self):
        class SlowResponse(Response):
            def read(self, size=-1):
                raise AssertionError("read(size) can wait for a full chunk on a trickling stream")
            def read1(self, size=-1):
                return io.BytesIO.read(self, size)
        client = Client()
        with patch.object(client, "open", return_value=SlowResponse(b"1234")):
            data = client._read("https://test", "test", 4, threading.Event(), expected=4)
        self.assertEqual(data, b"1234")

    def test_bad_http_status_line_is_a_network_error(self):
        client = Client()
        client.attempts = 1
        with patch.object(client, "open", side_effect=BadStatusLine("bad")):
            with self.assertRaises(AppError) as caught:
                client.check(threading.Event())
        self.assertEqual(caught.exception.code, "network")

    def test_connection_time_is_included_in_transfer_budget(self):
        clock = [0]
        def open_late(*args):
            clock[0] = 200
            return Response(b"1234")
        client = Client()
        with patch.object(client, "open", side_effect=open_late), patch("licorice.network.time.monotonic", side_effect=lambda: clock[0]):
            with self.assertRaises(AppError) as caught:
                client._read("https://test", "test", 4, threading.Event(), expected=4)
        self.assertEqual(caught.exception.code, "timeout")

    def test_deeply_nested_json_is_an_api_error(self):
        client = Client()
        with patch.object(client, "_read", return_value=b"[" * 1100 + b"]" * 1100):
            with self.assertRaises(AppError) as caught:
                client.check(threading.Event())
        self.assertEqual(caught.exception.code, "api")
