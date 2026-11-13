"""Bounded HTTPS I/O with validated redirects; no account or device identifier."""
from __future__ import annotations

import json
from http.client import HTTPException
import socket
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from . import __version__
from .core import AppError, Cancelled, Device, Release, X4_PRO, validate_url


def check_cancel(cancel: threading.Event) -> None:
    if cancel.is_set():
        raise Cancelled()


class ValidatedRedirect(HTTPRedirectHandler):
    def __init__(self, host):
        self.host = host

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_url(newurl, self.host)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class Client:
    timeout = 15
    attempts = 2

    def open(self, url, host):
        validate_url(url, host)
        parts = urlsplit(url)
        escaped = urlunsplit(parts._replace(path=quote(parts.path, safe="/%:@")))
        request = Request(escaped, headers={"User-Agent": f"LicoriceENDownloader/{__version__}",
                                            "Accept-Encoding": "identity"})
        return build_opener(ValidatedRedirect(host)).open(request, timeout=self.timeout)

    def _read(self, url, host, limit, cancel, progress=None, expected=None) -> bytes:
        deadline = time.monotonic() + 180
        def checkpoint():
            check_cancel(cancel)
            if time.monotonic() >= deadline:
                raise AppError("timeout", "転送に時間がかかりすぎています。接続を確認して再試行してください。")
        for attempt in range(self.attempts):
            checkpoint()
            try:
                with self.open(url, host) as response:
                    checkpoint()
                    if response.status != 200:
                        raise AppError("network", "公式配布先が正常な応答を返しませんでした。")
                    if expected is not None and response.headers.get("Content-Length"):
                        if int(response.headers["Content-Length"]) != expected:
                            raise AppError("size", "配布先が示す転送サイズと照会結果が一致しません。再確認してください。")
                    chunks, total = [], 0
                    while True:
                        checkpoint()
                        # HTTPResponse.read(n) may keep waiting for n bytes while
                        # a slow server trickles data. read1 returns after one
                        # buffered/socket read, allowing cancel/deadline checks.
                        block = response.read1(min(65536, limit + 1 - total))
                        checkpoint()
                        if not block:
                            break
                        chunks.append(block)
                        total += len(block)
                        if total > limit:
                            raise AppError("size", "受信データが許容サイズを超えています。")
                        if progress:
                            progress(total, expected or 0)
                    if expected is not None and total != expected:
                        raise AppError("size", "ダウンロードが途中で切れました。もう一度お試しください。")
                    check_cancel(cancel)
                    return b"".join(chunks)
            except HTTPError as exc:
                exc.close()
                check_cancel(cancel)
                if exc.code in (408, 429, 500, 502, 503, 504) and attempt + 1 < self.attempts:
                    pass
                else:
                    raise AppError("http", f"公式配布先への接続に失敗しました（HTTP {exc.code}）。配布情報を再確認してください。") from None
            except (URLError, TimeoutError, socket.timeout, ConnectionError, OSError, HTTPException):
                check_cancel(cancel)
                if attempt + 1 == self.attempts:
                    raise AppError("network", "通信に失敗しました。インターネット接続を確認して再試行してください。") from None
            except ValueError:
                raise AppError("network", "配布先の応答ヘッダーが不正です。") from None
            if cancel.wait(1):
                raise Cancelled()
        raise AppError("network", "通信を完了できませんでした。")

    def check(self, cancel, device: Device = X4_PRO) -> Release | None:
        query = urlencode({"device_type": device.model, "current_version": "V0.0.0",
                           "device_id": "", "ota_type": device.ota_type, "lng": "en"})
        data = self._read(f"https://{device.api_host}/api/v1/check-update?{query}",
                          device.api_host, 256 * 1024, cancel)
        try:
            payload = json.loads(data)
        except (ValueError, UnicodeError, RecursionError):
            raise AppError("api", "公式APIの応答をJSONとして読み取れません。") from None
        return Release.parse(payload, device)

    def download(self, release: Release, cancel, progress) -> bytes:
        return self._read(release.url, release.device.file_host, release.size,
                          cancel, progress, expected=release.size)
