# 実装・検証状況

更新日：2026年11月20日（日本時間）／ 開発版 v0.2.0

## 実装済み

- Python 3.10以降・Tkinterによる日本語・英語GUI。初回の自動照会と再確認。
- 表示言語はWindowsの表示言語から自動選択し、設定で自動・日本語・Englishを選択可能（v0.2.0）。文言は `licorice/i18n.py` に集約。
- 公式Global APIによる、X4 Pro用Licorice EN版の照会。
- HTTPS・取得先制限・同一ホストへのリダイレクト検証・サイズ上限・有限回の通信再試行。
- XOTA encrypted_v1 / OTA種別1の復号・抽出。チャネルごとの鍵導出処理を分離。
- XOTA内部の機種・配布種別・サイズ・SHA-256とAPI情報の照合。
- ESP32-S3の識別、セグメント境界、アプリ記述情報、XOR、末尾SHA-256の検証。
- 検証済みBINの保存、同名ファイルの上書き確認、既存ファイルを保持した保存確定。
- キャンセル、再試行、元XOTA・取得情報JSONの任意保存、追加保存の部分失敗の表示。
- EXEのフォルダを基準とした設定・ログ保存。設定破損時の保管と未対応形式の保護。
- アプリ内保存先の相対指定、画面位置の記憶、表示倍率を考慮した初期画面サイズと、主要操作の固定・内容のスクロール。
- ローカルログ（256 KiB×最大3ファイル）、個人のパスを含まない報告用情報のコピー。
- 同梱HTMLマニュアルと実画面の掲載。Rescue OS準備を別章に分離。
- PyInstallerによるWindows x64の開発版EXE・ポータブルZIP・SHA-256作成。

## 構成

| ファイル | 担当 |
|---|---|
| licorice/core.py | 機種定義と配布情報の解釈・検証 |
| licorice/network.py | API照会・HTTPS取得・中断と有限回再試行 |
| licorice/firmware.py | XOTA復号・抽出とESPイメージ検証 |
| licorice/storage.py | ポータブル設定と保存確定 |
| licorice/service.py | GUIから独立した取得・検証・保存の手順 |
| licorice/gui.py | 日本語画面・ワーカースレッドとのイベント連携 |
| licorice/cli.py | 照会・取得の開発用CLI |
| tools/build.py | テスト・EXE化・配布ZIP作成 |

機種固有のモデル、配布名、パッケージ識別子、ESPチップ、アプリ領域上限をDeviceへ分離した。初版の有効な定義はX4 Proのみ。異なる機種・形式には、検証のうえで定義・処理を追加する。

## 現行APIの確認結果

2026年11月13日に、以下の読み取り専用リクエストが成功した。

```text
GET https://api-prod.xteink.cc/api/v1/check-update
    ?device_type=ESP32S3_X4_TL_Licorice
    &current_version=V0.0.0
    &device_id=
    &ota_type=1
    &lng=en
```

- 認証・実端末ID・アカウントは送信していない。
- device_idを省略するとHTTP 422になり、空の値を明示すると照会に成功した。
- 取得した配布版：**26111201**。
- XOTA：6,169,002バイト。アプリBIN：6,168,800バイト。
- APIのplain_sha256とchecksum.sha256は、この応答ではどちらもアプリBINのハッシュだった。
- XOTA内部の機種はESP32S3_X4_TL、種別はLicorice。旧FWで同じ位置にあったSSD1677とは異なる。
- 内部管理バージョンは26111202。配布版26111201へ勝手に置き換えず、別情報として記録する。

検証したアプリBINのSHA-256：

```text
f8f09188b945b102a9c23fab76ce0fdb5c8f0f7ecf195c7d84268f1ea7cc48ab
```

APIが案内する版は変動するため、26111201を最新版として固定していない。

## 確認したこと

1. 手元の公式EN版26110701 XOTAで、抽出内容が既存の公式BINと整合することを確認。
2. 開発用CLIで公式APIから26111201を取得し、復号・全検証・BIN/XOTA/JSON保存に成功。
3. ポータブルZIPを新しいフォルダへ展開し、EXEの日本語画面で照会・BIN取得・検証・保存に成功。
4. Windows表示倍率125%で操作ボタンが収まることを確認。初期実装の表示切れを修正。
5. オフラインテスト64件が成功（v0.2.0、日英両方のGUIテストと翻訳カタログの整合性検査を含む）。破損、対象外機種・配布先、不正サイズ、ハッシュ不一致、通信の上限・有限回再試行、キャンセル、既存ファイル保護、設定破損、追加保存の部分失敗、GUI状態を検証。

v0.1.1のバグ調査では、保存・通信・設定・画面・終了等の不具合を修正し、CLIと配布EXEの両方で取得・検証・保存を再確認した。詳細は[バグ調査・修正記録](BUG_AUDIT.md)を参照。

v0.2.0では英語表示のEXE・ソースで、公式EN版26112001の照会・取得・検証・保存を確認した。

検証用に取得した公式FWは `.dev-validation/` 内に置き、ソース・配布ZIPから除外している。

## 今後の確認事項

- 本アプリで取得したBINの、対象Rescue OSからの実機導入・起動・言語選択の確認。
- Rescue OS準備章で扱う版・端末状態を決め、実機確認済みの手順と写真を整備。
- 別のWindows環境での配布EXE確認と、正式な対応OS・画面環境の決定。
公開ライセンスはMITに決定した。公開先は以下のとおり。

- ソース：https://github.com/miya-bee/licorice-en-downloader
- 配布：https://github.com/miya-bee/licorice-en-downloader/releases
- マニュアル：https://miya-bee.github.io/licorice-en-downloader/
- 問い合わせ：https://github.com/miya-bee/licorice-en-downloader/issues

公開する開発版ZIPにはMITライセンスと第三者表記を収録する。同梱マニュアルはネットワーク接続なしでも開ける。GitHub ActionsでWindows上のオフライン回帰テストを実行する。
