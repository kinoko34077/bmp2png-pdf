# bmp2png-pdf

BMP画像をPNGに変換し、必要な場合は変換したPNGを一覧順で1つの複数ページPDFにまとめるWindowsデスクトップツールです。

## 使い方

1. BMPをファイル選択またはドラッグ＆ドロップで追加します。
2. 一覧をドラッグするか、上下ボタンで並べ替えます。
3. PNG圧縮レベル（0〜9）を選びます。初期値は9です。PNGは可逆圧縮なので画質は変わりません。
4. PNGだけ作る場合はそのまま「変換」を押します。PDFも必要なら「PDFにする」を選び、ファイル名と保存先を指定してください。

BMPは先にPNGへ変換され、PNGは元BMPと同じフォルダーに保存されます。PDFは変換に成功したすべてのPNGを一覧順で含む単一ファイルです。PDFは画像1枚につきA4 1ページで、元PNGのピクセルを再サンプリングせず、縦横比を保ちます。PDFを開くとページ全体が見える表示を指定しています。

## 開発環境での起動

WindowsにPython 3.12以降を用意し、リポジトリのフォルダーで実行します。

```powershell
py -m pip install -r requirements.txt
py bmp_to_png_gui.py
```

または `gui.bat` を起動します。TkinterはPython for Windowsに付属するものを使います。

## Windows x64向けポータブル版のビルド

ビルドするPCにPython 3.12以降が必要です。

```powershell
py -m pip install -r requirements-build.txt
pyinstaller --noconfirm bmp2png_pdf.spec
```

作成された `dist/bmp2png_pdf/` フォルダーを一緒に配布してください。アプリ利用者はPythonやネット接続なしで起動できます。GitHub Actionsの「Windows portable build」は手動実行で同じフォルダーをArtifactとして作ります。Release公開はこの手順に含みません。

## 仕様と開発

- [仕様書](docs/SPECIFICATION.md)
- [原案および設計書 Issue #1](https://github.com/kinoko34077/bmp2png-pdf/issues/1)

リポジトリにライセンスはまだ設定されていません。
