# Licorice EN Downloader v0.1.1（開発版）

X4 Pro用のLicorice EN版を公式Global APIから取得し、Rescue OSで導入するアプリBINとして保存する非公式ツールです。ソースコードをMITライセンスで公開します。

## ダウンロードと起動

1. `LicoriceENDownloader-v0.1.1-windows-x64-dev.zip` をダウンロードします。
2. ZIPをすべて展開し、`LicoriceENDownloader.exe` を起動します。
3. 配布情報と保存先を確認し、「BINをダウンロード」を押します。

Pythonの導入は不要です。Windows x64向けで、画面・マニュアルは日本語です。設定はEXEと同じフォルダに保存します。

- [操作マニュアル](https://miya-bee.github.io/licorice-en-downloader/)
- [Rescue OSの入手先](https://note.com/ample_zephyr2723/n/necd67d1bccb3)
- [不具合・要望](https://github.com/miya-bee/licorice-en-downloader/issues)

ZIPと同名の `.sha256` を添付しています。FW本体・端末バックアップ・個人設定は同梱していません。

## 機能と修正

- 公式API照会、XOTAの復号・抽出、サイズ・SHA-256・対象情報・ESPイメージの検証。
- 検証成功後のBIN保存、キャンセル、同名ファイルの上書き確認。
- 元XOTAと取得情報JSONの任意保存、ポータブル設定、ローカルマニュアル。
- 保存確定前の中止、上書き対象の制限、低速通信と異常応答、設定復旧、終了処理を修正。
- 小さい画面で主要操作を固定し、内容をスクロールできるように変更。

## 確認済み・制約

回帰テスト46件が成功しています。公式EN版26111201の取得・復号・検証・保存をCLIとWindows EXEの両方で確認しました。

**出力BINの実機導入・起動・言語選択は未検証のため、開発版として公開します。** 対応するRescue OSの説明を確認し、端末のバックアップ・復元方法を確認してから導入してください。本アプリは端末の書き込みやリージョン変更を実行しません。正式なWindows対応範囲は確認中で、EXEは未署名です。
