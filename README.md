# bmp2png-pdf

BMP画像をPNGに変換し、必要な場合は変換したPNGを一覧順で1つの複数ページPDFにまとめるWindowsデスクトップツールです。

- PNG圧縮レベルを0〜9から指定できます（初期値9、高圧縮、可逆）。
- 一覧はドラッグまたは上下ボタンで並べ替えできます。
- 「PDFにする」を選ぶと、ファイル名と保存場所を指定してPDFを作れます。
- PDFは画像1枚につきA4 1ページで、画像の向きと縦横比を保ち、初期表示はページ全体表示です。
- 利用者側にPythonやインターネット接続を求めないWindows x64向けポータブル版を目指します。

詳しい仕様は [docs/SPECIFICATION.md](docs/SPECIFICATION.md)、原案と今回の設計書は [Issue #1](https://github.com/kinoko34077/bmp2png-pdf/issues/1) を参照してください。
