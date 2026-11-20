"""Japanese / English UI text.

Japanese source strings are the catalog keys, so the Japanese UI needs no
lookup and a missing English entry falls back to Japanese instead of failing.
Placeholders use str.format syntax and must match between both languages
(enforced by tests/test_i18n.py).
"""
from __future__ import annotations

import locale
import os

LANGUAGES = ("auto", "ja", "en")
_language: str | None = None


def detect() -> str:
    """Japanese when the Windows display language is Japanese, otherwise English.

    LICORICE_LANG=ja|en overrides detection (CLI users and tests)."""
    forced = os.environ.get("LICORICE_LANG", "").strip().lower()
    if forced in ("ja", "en"):
        return forced
    if os.name == "nt":
        try:
            import ctypes
            # LANG_JAPANESE == 0x11 (primary language id, low 10 bits).
            return "ja" if ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF == 0x11 else "en"
        except (AttributeError, OSError):
            pass
    try:
        name = locale.getlocale()[0] or ""
    except ValueError:
        name = ""
    name = name or os.environ.get("LC_ALL") or os.environ.get("LANG") or ""
    return "ja" if name.lower().startswith(("ja", "japanese")) else "en"


def set_language(preference: str) -> str:
    global _language
    _language = preference if preference in ("ja", "en") else detect()
    return _language


def language() -> str:
    return _language or set_language("auto")


def tr(text: str, **values) -> str:
    if language() == "en":
        text = EN.get(text, text)
    return text.format(**values) if values else text


def font_family() -> str:
    return "Segoe UI" if language() == "en" else "Yu Gothic UI"


EN = {
    # core
    "処理を中止しました。": "Cancelled.",
    "対応する公式HTTPS配布先ではありません。配布情報を再確認してください。":
        "This is not a supported official HTTPS download location. Please check the release info again.",
    "公式APIが正常な配布情報を返しませんでした。後ほど再確認してください。":
        "The official API did not return valid release info. Please check again later.",
    "API応答に配布情報の項目がありません。": "The API response contains no release info.",
    "配布情報が空でした。応答の意味を確認できません。":
        "The release info was empty, so the response could not be interpreted.",
    "X4 Pro用Licorice EN版の配布情報を検証できません。未対応の形式または情報の不一致です。":
        "Could not verify the Licorice EN release info for X4 Pro. The format is unsupported or the details do not match.",
    # network
    "転送に時間がかかりすぎています。接続を確認して再試行してください。":
        "The transfer is taking too long. Check your connection and try again.",
    "公式配布先が正常な応答を返しませんでした。": "The official download server did not return a valid response.",
    "配布先が示す転送サイズと照会結果が一致しません。再確認してください。":
        "The size reported by the download server does not match the release info. Please check again.",
    "受信データが許容サイズを超えています。": "The received data exceeds the allowed size.",
    "ダウンロードが途中で切れました。もう一度お試しください。": "The download was interrupted. Please try again.",
    "公式配布先への接続に失敗しました（HTTP {code}）。配布情報を再確認してください。":
        "Could not connect to the official download server (HTTP {code}). Please check the release info again.",
    "通信に失敗しました。インターネット接続を確認して再試行してください。":
        "Network error. Check your internet connection and try again.",
    "配布先の応答ヘッダーが不正です。": "The download server sent invalid response headers.",
    "通信を完了できませんでした。": "Could not complete the transfer.",
    "公式APIの応答をJSONとして読み取れません。": "Could not read the official API response as JSON.",
    # service
    "保存先に書き込めません。別のフォルダを選んでください。":
        "Cannot write to the destination folder. Please choose another folder.",
    "同名ファイルがあります。保存先と上書きの指定を確認してください。":
        "A file with the same name already exists. Check the destination and the overwrite choice.",
    "公式配布先からダウンロードしています…": "Downloading from the official server…",
    "XOTAを復号・抽出し、BINを検証しています…": "Decrypting the XOTA and extracting and verifying the BIN…",
    "検証済みBINを保存しています…": "Saving the verified BIN…",
    "元のXOTAを追加保存できませんでした。BINは保存済みです。":
        "Could not also save the original XOTA. The BIN has been saved.",
    "取得情報JSONを追加保存できませんでした。BINは保存済みです。":
        "Could not also save the info JSON. The BIN has been saved.",
    # firmware
    "このOTA種別には対応していません。": "This OTA type is not supported.",
    "XOTAの機種情報を読み取れません。": "Could not read the device info in the XOTA.",
    "XOTAの機種情報が不正です。": "The device info in the XOTA is invalid.",
    "対応するESPアプリイメージではありません。": "This is not a supported ESP app image.",
    "ESPチップ情報またはイメージのSHA-256設定が対応していません。":
        "The ESP chip ID or the image's SHA-256 setting is not supported.",
    "ESPセグメントヘッダーが途中で切れています。": "An ESP segment header is truncated.",
    "ESPセグメントのサイズが不正です。": "An ESP segment has an invalid size.",
    "ESPアプリ記述情報を確認できません。": "The ESP app descriptor could not be found.",
    "ESPイメージの末尾サイズが不正です。": "The ESP image trailer has an invalid size.",
    "ESPイメージのXORチェックサムが一致しません。": "The ESP image XOR checksum does not match.",
    "ESPイメージ末尾のSHA-256が一致しません。": "The SHA-256 at the end of the ESP image does not match.",
    "XOTAのサイズまたは先頭の形式が一致しません。": "The XOTA size or header format does not match.",
    "XOTA内部情報と配布情報が一致しません。": "The XOTA's internal info does not match the release info.",
    "XOTA内部の対象機種が一致しません。": "The target device inside the XOTA does not match.",
    "抽出したBINのサイズまたはSHA-256が一致しません。保存を中止しました。":
        "The extracted BIN's size or SHA-256 does not match. Nothing was saved.",
    # storage
    "ファイルを保存できません。空き容量・書き込み権限・ファイルが使用中でないか確認してください。":
        "Could not save the file. Check free space and write permission, and make sure the file is not in use.",
    "元の設定を安全に保管できないため、自動上書きを停止しています。":
        "Settings are not being saved because the original settings file could not be backed up safely.",
    "保存先の設定が不正です。保存先を選び直してください。":
        "The destination setting is invalid. Please choose the destination again.",
    "設定ファイルが大きすぎます。元の設定を保持し、自動上書きを停止しました。":
        "The settings file is too large. It was left untouched and settings will not be saved.",
    "この設定形式には未対応です。元の設定を保持し、自動上書きを停止しました。":
        "This settings format is not supported. The file was left untouched and settings will not be saved.",
    "設定を読み取れませんでした。元の設定を別名で保管し、初期設定で起動しました。":
        "Could not read the settings. The original file was kept under another name and the app started with defaults.",
    "設定を読み取れませんでした。元の設定を保持し、自動上書きを停止しました。":
        "Could not read the settings. The file was left untouched and settings will not be saved.",
    # gui: main window
    "まだ処理を実行していません。": "Nothing has been run yet.",
    "ログを保存できません。アプリフォルダの書き込み権限を確認してください。":
        "Cannot write the log. Check write permission for the app folder.",
    "設定・保存の確認": "Settings and saving",
    "X4 Pro用  ·  Licorice EN版を取得して、検証済みBINとして保存  /  アプリ v{version}":
        "For X4 Pro  ·  Fetches the Licorice EN firmware and saves it as a verified BIN  /  App v{version}",
    "公式APIが案内する配布FW": "Firmware offered by the official API",
    "再確認": "Check again",
    "配布情報を未確認": "Release info not checked yet",
    "対象：X4 Pro ／ EN版": "Target: X4 Pro / EN",
    "確認日時：—": "Checked: —",
    "配布元の更新内容（原文）": "Changelog from the vendor (original text)",
    "配布情報の取得後に表示します。": "Shown after the release info is retrieved.",
    "保存先": "Save to",
    "変更…": "Change…",
    "保存するファイル：配布情報の取得後に表示": "File to save: shown after the release info is retrieved",
    "配布情報を確認してください。": "Please check the release info.",
    "BINをダウンロード": "Download BIN",
    "キャンセル": "Cancel",
    "保存先を開く": "Open folder",
    "設定": "Settings",
    "マニュアル・導入手順": "Manual & install guide",
    "詳細・報告用情報": "Details & report info",
    "このアプリについて": "About",
    "非公式ツールです。公式配布物からアプリBINを抽出します。端末への書き込みはRescue OSから行ってください。":
        "Unofficial tool. It extracts the app BIN from the official release. Flash it to the device using Rescue OS.",
    "設定を保存できません": "Cannot save settings",
    "設定を保存できませんでした。この操作で選んだ内容は今回の起動中は有効です。\nアプリフォルダの書き込み権限を確認してください。":
        "Could not save the settings. Your choice stays in effect until the app is closed.\nCheck write permission for the app folder.",
    "予期しないエラーが発生しました（{name}）。報告用情報を確認してください。":
        "An unexpected error occurred ({name}). Please see the report info.",
    "前回確認時の情報です。再確認中…": "Showing info from the last check. Checking again…",
    "公式APIで配布情報を確認しています…": "Checking the release info with the official API…",
    "FWの保存先を選択": "Choose where to save the firmware",
    "保存先を選べません": "Cannot use this folder",
    "フォルダが存在し、利用できるか確認してください。": "Make sure the folder exists and is accessible.",
    "アプリのフォルダ / {path}": "App folder / {path}",
    "保存先を確認できません": "Cannot check the destination",
    "保存先の権限と接続状態を確認してください。": "Check the destination's permissions and that it is connected.",
    "同名ファイルの確認": "Files already exist",
    "以下のファイルを、検証成功後に上書きしますか？\n\n":
        "Overwrite the following files after verification succeeds?\n\n",
    "中止を要求しました。通信や保存の終了を待っています…":
        "Cancel requested. Waiting for the transfer or save to stop…",
    "ダウンロード中：{current:.2f} / {total:.2f} MiB": "Downloading: {current:.2f} / {total:.2f} MiB",
    "前回確認時の情報：{time}": "Info from the last check: {time}",
    "\nエラー分類：{code}\n内容：{message}": "\nError type: {code}\nDetails: {message}",
    "X4 Pro ／ EN版　転送サイズ：{size:,} バイト": "X4 Pro / EN   Download size: {size:,} bytes",
    "確認：{checked}　配布日時（配布元表記）：{uploaded}":
        "Checked: {checked}   Released (as stated by the vendor): {uploaded}",
    "不明": "unknown",
    "保存するファイル：{name}": "File to save: {name}",
    "更新内容の記載はありません。": "No changelog was provided.",
    "配布情報を確認しました。保存先を確認し、ダウンロードしてください。":
        "Release info retrieved. Check the destination, then download.",
    "\n配布情報の取得：成功": "\nRelease info: retrieved",
    "現在の配布物はありません": "No release available",
    "今回の照会では更新なしの応答でした。": "The API reported no update for this check.",
    "保存するファイル：—": "File to save: —",
    "現在取得できる配布物がありません。時間をおいて再確認してください。":
        "No release is available right now. Please check again later.",
    "公式APIから「更新なし」の応答がありました。": "The official API reported “no update”.",
    "\n配布情報：更新なし": "\nRelease info: no update",
    "ダウンロード・検証完了。BINを保存しました。": "Downloaded and verified. The BIN has been saved.",
    "　追加保存に問題があります。詳細をご確認ください。": "  Some extra files could not be saved. See the details.",
    "\nBIN保存：成功\nサイズ・SHA-256・ESPイメージ検証：成功\nSHA-256：":
        "\nBIN saved: yes\nSize / SHA-256 / ESP image verification: passed\nSHA-256: ",
    "追加保存について": "Extra files",
    "{app} v{version}\nOS：{os}\n対象：X4 Pro / EN\nFW版：{firmware}":
        "{app} v{version}\nOS: {os}\nTarget: X4 Pro / EN\nFirmware version: {firmware}",
    "未取得": "not retrieved",
    # gui: dialogs
    "保存設定": "Settings",
    "BINに加えて保存するファイル": "Files to save in addition to the BIN",
    "配布元のXOTAも保存する": "Also save the vendor's XOTA",
    "取得情報JSONも保存する": "Also save an info JSON",
    "設定はEXEと同じフォルダの settings.json に保存します。\n取得情報には機種・版・取得元・検証結果を記録します。":
        "Settings are saved to settings.json in the same folder as the EXE.\nThe info JSON records the device, version, source and verification results.",
    "自動（Windowsの表示言語）": "Auto (Windows display language)",
    "設定を保存": "Save settings",
    "報告用情報をコピー": "Copy report info",
    "保存先を開けません": "Cannot open the folder",
    "保存先フォルダが存在するか確認してください。": "Make sure the destination folder exists.",
    "マニュアル": "Manual",
    "配布ZIPの {path} を確認してください。": "See {path} in the release ZIP.",
    "{app}\nアプリ v{version}\n\nX4 Pro用Licorice EN版ファームウェア取得ツール\nXTEINK非公式・開発版\n\nFWは公式Global配布先から取得します。\n本アプリは端末への書き込みや地域設定の変更を行いません。\n\n第三者表記：THIRD_PARTY_NOTICES.md":
        "{app}\nApp v{version}\n\nDownloads the Licorice EN firmware for X4 Pro\nUnofficial (not affiliated with XTEINK), development build\n\nThe firmware is fetched from the official Global server.\nThis app does not write to the device or change its region.\n\nThird-party notices: THIRD_PARTY_NOTICES.md",
    "処理中です": "Busy",
    "処理の中止を要求して、終了を待ってから閉じますか？":
        "Cancel the current task and close once it has stopped?",
    # cli
    "Licorice EN Downloader 開発用CLI": "Licorice EN Downloader development CLI",
    "検証済みBINの保存先。省略時は配布情報の照会のみ":
        "Folder to save the verified BIN to. Without it, only the release info is checked",
    "同名ファイルを上書きする": "Overwrite existing files with the same name",
    "XOTA・取得情報も保存": "Also save the XOTA and info JSON",
    "現在取得できる配布物がありません。": "No release is available right now.",
}
