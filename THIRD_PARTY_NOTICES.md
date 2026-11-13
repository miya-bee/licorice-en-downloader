# 第三者表記

## XOTA形式の解析資料

XOTAの構造、OTA種別ごとの鍵テーブルと導出式、AES-128-CTRの適用方法は、以下のMITライセンスのコードを参照してPythonで実装しています。

- プロジェクト：crosspoint-reader/crosspoint-tools
- 資料：https://github.com/crosspoint-reader/crosspoint-tools/blob/master/unlocker-tool/crates/unlocker-core/src/xota.rs
- ライセンス：https://github.com/crosspoint-reader/crosspoint-tools/blob/master/LICENSE
- 著作権：Copyright (c) 2025 SoFriendly

ライセンス全文は `licenses/crosspoint-tools-MIT.txt` に同梱しています。端末の解除・配信・書き込みに関する実装は含みません。

## cryptography

AES-128-CTRの復号にcryptography 46.0.5を利用します。Apache License 2.0またはBSDのデュアルライセンスです。公式資料：https://cryptography.io/

配布版には、使用したパッケージに同梱されたライセンス全文を `licenses/cryptography/` にコピーします。バイナリに含まれる第三者コンポーネントの表記も同ライセンス文書を参照してください。

## Python / Tcl/Tk / PyInstaller

Pythonの標準ライブラリとTkinter（Tcl/Tk）を利用し、EXE化にPyInstallerを利用します。配布版の `licenses/` に、ビルド環境に同梱された各ライセンスとPyInstallerの例外条項を収録します。Tcl 8.6.12のライセンスが環境にない場合は、同じ版の公式ソースから収録した `licenses/tcl8.6.12-license.terms` を使用します（出典：https://github.com/tcltk/tcl/blob/core-8-6-12/license.terms）。バージョンは `BUILD_INFO.json` に記録します。

## XTEINKのファームウェア

ファームウェアはXTEINKの公式配布先から利用時に取得します。アプリのソースや配布ZIPにFWを同梱せず、独自パッチも加えません。XTEINKとLicoriceに関する名称は製品・配布物を識別するために使用しています。本アプリはXTEINKの公式アプリではありません。
