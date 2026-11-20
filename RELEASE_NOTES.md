# Licorice EN Downloader v0.2.1 (development build)

[English](#english) | [日本語](#日本語)

## English

An unofficial Windows tool that fetches the Licorice EN firmware for the XTEINK X4 Pro from the official Global API and saves it as the app BIN you install with Rescue OS. Source code is under the MIT License.

### What's fixed

- **Downloads no longer fail when the API leaves optional fields empty.** If the update API returned `null` for the changelog, upload time or checksum, v0.2.0 rejected the whole release info and could not download. These fields are now treated as absent. Required fields and file verification are as strict as before.
- **Touchpad scrolling.** Small scroll steps from precision touchpads were ignored, so the main window did not scroll. They now add up.
- **`settings.json` with a BOM.** A settings file saved as UTF-8 with a BOM (for example by older Notepad) was treated as broken and reset. It is now read normally.

The English UI from v0.2.0 is unchanged.

### Download and run

1. Download `LicoriceENDownloader-v0.2.1-windows-x64-dev.zip`.
2. Extract the whole ZIP and run `LicoriceENDownloader.exe`.
3. Check the release info and destination, then click **Download BIN**.

No Python needed. Windows x64. Settings are stored next to the EXE. To update, you can copy `settings.json` from your old folder into the new one.

- [Manual (English)](https://miya-bee.github.io/licorice-en-downloader/en/)
- [Rescue OS (release article, in Japanese)](https://note.com/ample_zephyr2723/n/necd67d1bccb3)
- [Bugs and requests](https://github.com/miya-bee/licorice-en-downloader/issues)

A `.sha256` file with the same name as the ZIP is attached. No firmware, device backups or personal settings are included.

### Status and limits

68 regression tests pass in both English and Japanese. Fetching, decrypting, verifying and saving the official EN firmware 26112001 were confirmed with this build.

**Installing, booting and choosing a language with the produced BIN on a real device have not been tested, so this is a development build.** Check the documentation of your Rescue OS and make sure you can back up and restore the device before installing. The app never writes to the device or changes its region. The supported Windows range is still being checked, and the EXE is unsigned.

## 日本語

X4 Pro用のLicorice EN版を公式Global APIから取得し、Rescue OSで導入するアプリBINとして保存する非公式ツールです。ソースコードをMITライセンスで公開します。

### 修正点

- **APIが任意項目を空で返しても取得できるように。** 更新APIが更新内容・配布日時・チェックサムに `null` を返すと、v0.2.0では配布情報全体を不正と判定し、取得できませんでした。これらは項目なしとして扱います。必須項目とファイルの検証は従来どおり厳密です。
- **タッチパッドでのスクロール。** 高精度タッチパッドの細かいスクロールが無視され、本文がスクロールしませんでした。細かい量を累積して動くようにしました。
- **BOM付きの `settings.json`。** 古いメモ帳などでBOM付きUTF-8として保存した設定ファイルを壊れた設定として扱い、初期化していました。通常どおり読み込みます。

v0.2.0の英語表示はそのままです。

### ダウンロードと起動

1. `LicoriceENDownloader-v0.2.1-windows-x64-dev.zip` をダウンロードします。
2. ZIPをすべて展開し、`LicoriceENDownloader.exe` を起動します。
3. 配布情報と保存先を確認し、「BINをダウンロード」を押します。

Pythonの導入は不要です。Windows x64向けです。設定はEXEと同じフォルダに保存します。旧版の `settings.json` を新しいフォルダへコピーすると、設定を引き継げます。

- [操作マニュアル](https://miya-bee.github.io/licorice-en-downloader/)
- [Rescue OSの入手先](https://note.com/ample_zephyr2723/n/necd67d1bccb3)
- [不具合・要望](https://github.com/miya-bee/licorice-en-downloader/issues)

ZIPと同名の `.sha256` を添付しています。FW本体・端末バックアップ・個人設定は同梱していません。

### 確認済み・制約

回帰テスト68件が日本語・英語の両方で成功しています。このビルドで、公式EN版26112001の取得・復号・検証・保存を確認しました。

**出力BINの実機導入・起動・言語選択は未検証のため、開発版として公開します。** 対応するRescue OSの説明を確認し、端末のバックアップ・復元方法を確認してから導入してください。本アプリは端末の書き込みやリージョン変更を実行しません。正式なWindows対応範囲は確認中で、EXEは未署名です。
