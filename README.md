# bmp2png-pdf

BMP・PNG画像を高圧縮PNGに変換し、必要な場合は変換結果を一覧順で1つの複数ページPDFにまとめるWindowsデスクトップツールです。

## 使い方

1. BMPまたはPNGをファイル選択またはドラッグ＆ドロップで追加します。追加時はファイル名順（数字部分は自然順）に並びます。
2. 一覧をドラッグするか、上下ボタンで処理順を並べ替えます。
3. PNG圧縮レベル（0〜9）を選びます。初期値は9です。PNGは可逆圧縮なので画質は変わりません。
4. 必要なら出力先フォルダー、PNG入力に付ける接尾辞（初期値 `_compressed`）、上書きの有無を設定します。出力先未指定なら各画像と同じフォルダーです。BMPから作るPNG名には接尾辞は付きません。
5. PNGだけ作る場合はそのまま「変換」を押します。PDFも必要なら「PDFにする」を選び、ファイル名と保存先を指定してください。

BMP・PNGは先にPNGへ変換されます。PDFは全変換が成功した場合だけ、一覧順で全画像を含む単一ファイルです。PDFは画像1枚につきA4 1ページで、元画像のピクセルを再サンプリングせず、解像度情報と縦横比を保ちます。PDFを開くとページ全体が見える単ページ表示を指定しています。上書きがオフの場合、既存ファイルは残して新しい名前に連番を付けます。選択中の入力画像は上書きしません。

## 開発環境での起動

WindowsにPython 3.12以降を用意し、リポジトリのフォルダーで実行します。

```powershell
py -m pip install -r requirements.txt
py bmp_to_png_gui.py
```

または `gui.bat` を起動します。TkinterはPython for Windowsに付属するものを使います。

## Windows x64向け単体アプリ

利用者はGitHub Actionsが作成した `bmp2png_pdf.exe` をダウンロードして起動します。インストールや管理者権限は不要で、Pythonやネット接続も使いません。最初の起動時にプログラム本体をユーザー別の `%LOCALAPPDATA%` キャッシュへ展開し、次回以降は同じ版のキャッシュを再利用します。更新版は別フォルダーに展開されます。古いキャッシュが不要になったら、アプリを閉じてから `%LOCALAPPDATA%\kinoko34077\bmp2png-pdf` 内の古い版フォルダーを削除できます。

## Windows x64向けビルド

GitHub Actionsの「Windows single-file portable build」を実行すると、Artifactとして `bmp2png_pdf.exe` を作成します。ローカルでビルドする場合はPython 3.12とネット接続が必要です。Nuitkaが対応するMinGW64コンパイラーをリポジトリ内のキャッシュへ取得するため、Visual Studioや管理者権限は不要です。

```powershell
py -3.12 -m venv .venv-build
.\.venv-build\Scripts\Activate.ps1
python -m pip install -r requirements-build.txt
.\build_windows.ps1
```

生成物は `dist/bmp2png_pdf.exe` です。アプリ利用者にCコンパイラーは不要です。GitHub Releaseへの恒久公開はこの手順に含みません。

## 仕様と開発

- [仕様書](docs/SPECIFICATION.md)
- [原案および設計書 Issue #1](https://github.com/kinoko34077/bmp2png-pdf/issues/1)

リポジトリにライセンスはまだ設定されていません。
