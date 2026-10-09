# bmp2png-pdf

BMP画像をPNGに変換し、生成したPNGを一覧順で1つの複数ページPDFにまとめるWindowsデスクトップツールです。

- PNG圧縮レベルを0〜9から指定できます（初期値6、可逆圧縮）。
- BMPを先にPNGへ変換し、生成PNGからPDFを作成します。
- PDFは画像ごとにA4 1ページ、画像の向きと縦横比を保ちます。
- Windows x64向けにPyInstallerでポータブル配布する計画です。

初回要件と設計は親Issueおよび docs/superpowers/specs/2026-10-09-bmp2png-pdf-design.md を参照してください。
