# Licorice EN Downloader v0.2.0 (development build)

[English](#english) | [日本語](#日本語)

## English

An unofficial Windows tool that fetches the Licorice EN firmware for the XTEINK X4 Pro from the official Global API and saves it as the app BIN you install with Rescue OS. Source code is under the MIT License.

### What's new

- **English UI.** The app follows the Windows display language: English, or Japanese on Japanese Windows. Switch under **Settings → 表示言語 / Language** (applied after restart).
- Error and progress messages and the development CLI are translated too.
- English manual, README and `README.txt` in the ZIP.

### Download and run

1. Download `LicoriceENDownloader-v0.2.0-windows-x64-dev.zip`.
2. Extract the whole ZIP and run `LicoriceENDownloader.exe`.
3. Check the release info and destination, then click **Download BIN**.

No Python needed. Windows x64. Settings are stored next to the EXE, and existing `settings.json` files from v0.1.x keep working.

- [Manual (English)](https://miya-bee.github.io/licorice-en-downloader/en/)
- [Rescue OS (release article, in Japanese)](https://note.com/ample_zephyr2723/n/necd67d1bccb3)
- [Bugs and requests](https://github.com/miya-bee/licorice-en-downloader/issues)

A `.sha256` file with the same name as the ZIP is attached. No firmware, device backups or personal settings are included.

### Status and limits

64 regression tests pass. Fetching, decrypting, verifying and saving the official EN firmware 26112001 were confirmed with the English UI.

**Installing, booting and choosing a language with the produced BIN on a real device have not been tested, so this is a development build.** Check the documentation of your Rescue OS and make sure you can back up and restore the device before installing. The app never writes to the device or changes its region. The supported Windows range is still being checked, and the EXE is unsigned.

## 日本語

X4 Pro用のLicorice EN版を公式Global APIから取得し、Rescue OSで導入するアプリBINとして保存する非公式ツールです。ソースコードをMITライセンスで公開します。

### 変更点

- **英語表示に対応。** Windowsの表示言語に合わせて日本語・英語を自動で選びます。「設定」→「表示言語 / Language」で変更でき、再起動後に反映されます。
- エラー・進行状況のメッセージと開発用CLIも英語に対応。
- 英語版のマニュアル・README、ZIP同梱の `README.txt` を追加。

### ダウンロードと起動

1. `LicoriceENDownloader-v0.2.0-windows-x64-dev.zip` をダウンロードします。
2. ZIPをすべて展開し、`LicoriceENDownloader.exe` を起動します。
3. 配布情報と保存先を確認し、「BINをダウンロード」を押します。

Pythonの導入は不要です。Windows x64向けです。設定はEXEと同じフォルダに保存し、v0.1.xの `settings.json` もそのまま使えます。

- [操作マニュアル](https://miya-bee.github.io/licorice-en-downloader/)
- [Rescue OSの入手先](https://note.com/ample_zephyr2723/n/necd67d1bccb3)
- [不具合・要望](https://github.com/miya-bee/licorice-en-downloader/issues)

ZIPと同名の `.sha256` を添付しています。FW本体・端末バックアップ・個人設定は同梱していません。

### 確認済み・制約

回帰テスト64件が成功しています。英語表示で、公式EN版26112001の取得・復号・検証・保存を確認しました。

**出力BINの実機導入・起動・言語選択は未検証のため、開発版として公開します。** 対応するRescue OSの説明を確認し、端末のバックアップ・復元方法を確認してから導入してください。本アプリは端末の書き込みやリージョン変更を実行しません。正式なWindows対応範囲は確認中で、EXEは未署名です。
