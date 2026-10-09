# BMP/PNG圧縮とPDF出力 リファクタリング実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** BMPとPNGを高圧縮PNGへ変換し、任意で一覧順の単一PDFにまとめるWindowsアプリを、保守しやすく軽量で無駄な再処理の少ない構成に整理する。

**Architecture:** Python/Tkinter/Pillowを維持する。GUI、変換ワークフロー、画像変換、PDF出力を分離し、出力パスと上書き判定をGUIから独立させる。PDFは `img2pdf` を現行方式と実測比較し、画素・DPI・ページ設定を保てる場合のみ採用する。

**Tech Stack:** Python 3.12、Tkinter、tkinterdnd2、Pillow、pypdf、PyInstaller。PDF比較候補はimg2pdf。

**Spec:** `docs/superpowers/specs/2026-10-09-bmp2png-pdf-refactor-design.md`

## Global Constraints

- Windows x64向けone-folder配布を維持し、利用者にPythonやネット接続を求めない。
- BMPとPNGを入力し、PNG圧縮レベルは0〜9、初期値は9とする。
- PDFは全PNGの生成成功後にだけ、一覧順で一つ作る。画像1枚につきA4 1ページとする。
- PNG出力先未指定なら各入力画像と同じフォルダー、指定時は指定フォルダーとする。
- PNG入力の出力名には接尾辞欄（初期値 `_compressed`）を使い、BMP入力の出力名は従来どおり維持する。
- 「上書きする」は初期状態オフ。オンでも選択中の入力ファイル自体は上書きしない。
- PDF内の画像ピクセルを再サンプリングせず、元PNGのDPIをページ寸法へ反映し、初期表示をFit/単ページにする。
- ユーザーに依頼されていない自動テストは追加・実行せず、処理時間・メモリ・容量の比較とWindows配布ビルドで確認する。

## Review Focus

- `.BMP` のような大文字拡張子とBMP/PNG混在を受け付け、名前順の初期表示と変換順が一致すること。
- `2.png` と `10.png` の自然順、同名画像のパス順、ドラッグ後の順序が安定すること。
- 透過PNG・パレットPNGの画素とDPIを保って再圧縮し、PDFにも画素劣化なく載せられること。
- 同名入力、既存出力、選択入力との出力パス衝突で、チェック設定に沿って安全に採番または上書きすること。
- 大きな画像群でPDF化時に全画像を一括メモリ展開せず、部分PDFや不完全なPNGを残さないこと。

---

## ファイル構成

- `bmp_to_png_gui.py`: 起動入口とTkinter画面。入力、一覧、並べ替え、圧縮・出力設定、進行状況表示。
- `conversion_service.py`: 選択順の入力処理、出力パス作成、衝突・上書き制御、部分失敗方針。
- `image_processing.py`: BMP/PNGからPNGへの可逆再圧縮。DPI情報の維持と一時ファイル書き込み。
- `pdf_export.py`: 複数PNGを一つのA4 PDFへ配置し、ページ全体表示・単ページ表示を設定。
- `requirements.txt`: 実行時依存。PDF比較結果によりReportLabまたはimg2pdfを確定。
- `bmp2png_pdf.spec`: PyInstaller収集設定。
- `.github/workflows/build-windows.yml`: 追加・移動したモジュールと依存ファイルの変更でビルドするトリガー。
- `README.md`, `docs/SPECIFICATION.md`: 操作、入力形式、出力名、上書き、出力先、PDF仕様、開発・ビルド手順。
- `docs/superpowers/specs/2026-10-09-bmp2png-pdf-refactor-design.md`: 合意した設計。
- `docs/superpowers/plans/2026-10-09-bmp2png-pdf-refactor.md`: この計画。

## Task 1: 変更前の性能基準を記録

**Files:**
- Modify: none
- Record results in: implementation PR description

**Interfaces:**
- Consumes: current branch `e6be4e6` implementation and current Windows x64 artifact.
- Produces: a reproducible local BMP/PNG corpus and baseline conversion time, PDF time, peak memory, and distribution size.

- [ ] 現行版でBMP、RGB PNG、パレットPNG、透過PNGを含む固定画像セットを用意し、合計画素数とファイルサイズを記録する。
- [ ] 現行PDF方式で同セットを変換し、PNG時間、PDF時間、ピークメモリ、PDFサイズ、配布物サイズを記録する。既存artifactの約23MBも比較欄に記録する。
- [ ] 同じPNG群でimg2pdf候補を別一時出力へ作り、処理時間、ピークメモリ、PDFサイズ、DPI、ページ数、画像XObjectの画素一致、Fit/SinglePage設定を比較する。
- [ ] 採用方式を設計書とPR説明へ記録する。品質・ページ設定を満たさない場合はReportLabを維持する。
- [ ] Commit: `perf: capture image and pdf baseline`

## Task 2: 出力規則と画像変換を分離

**Files:**
- Create: `conversion_service.py`
- Modify: `image_processing.py`

**Interfaces:**
- Produces: `build_png_output_path(input_path: Path, output_dir: Path | None, png_suffix: str, overwrite: bool, protected_inputs: set[Path], reserved_outputs: set[Path]) -> Path`
- Produces: `convert_image_to_png(input_path: Path, output_path: Path, compression_level: int) -> Path`
- Produces: `convert_batch(inputs: Sequence[Path], output_dir: Path | None, png_suffix: str, compression_level: int, overwrite: bool) -> BatchResult`
- `BatchResult` carries successful PNG paths in processing order plus per-input failures; PDF creation is requested by GUI only when all conversions succeed.

- [ ] 出力パス生成を実装する。BMPは従来のベース名、PNGは指定接尾辞を追加し、未チェック時は既存出力・同一実行内衝突に連番を付ける。
- [ ] 上書きチェック時は前回実行などで既にある出力を置き換える。同じ実行内の出力同士および選択入力に含まれるファイルは常に保護し、衝突時は連番へ切り替える。
- [ ] 拡張子や接尾辞の検証と、自然順で確定した入力列の保持をサービス層に実装する。
- [ ] BMP/PNGのどちらもPillowでPNG圧縮レベル0〜9を適用して保存し、画素・アルファ・DPIを維持する。一時ファイルを完成させてから出力先へ確定する。
- [ ] 既存同名ファイル、保護入力、混合形式、変換エラーの振る舞いを手順で確認し、エラー時に不完全な出力が残らないことを記録する。
- [ ] Commit: `refactor: separate conversion workflow`

## Task 3: PDF出力方式を選択して分離

**Files:**
- Create: `pdf_export.py`
- Modify: `image_processing.py`
- Modify: `requirements.txt`
- Modify: `bmp2png_pdf.spec`

**Interfaces:**
- Produces: `create_combined_pdf(png_paths: Sequence[Path], output_path: Path) -> Path`
- Consumes: Task 1で比較したPDF方式とTask 2の確定済みPNGパス列。

- [ ] Task 1の結果に基づきPDF実装を一つ選び、未採用ライブラリを実行時依存とPyInstaller収集対象から削除する。
- [ ] 1入力につきA4 1ページ、向きと縦横比を維持、再サンプリングなし、元PNGのDPI反映、余白、PDFタイトルを実装する。
- [ ] PDFライブラリの出力ストリームを一時ファイルに接続し、PDF全体をメモリに保持しない。pypdfで初期表示FitとSinglePageを設定し、完成後に確定する。
- [ ] 同じ画像セットでPDFのページ数、ページ順、DPI由来のページ寸法、画像画素一致、初期表示設定、生成時間、メモリ、容量を記録する。
- [ ] Commit: `perf: streamline combined pdf output`

## Task 4: GUIに混在入力と出力設定を追加

**Files:**
- Modify: `bmp_to_png_gui.py`
- Modify: `conversion_service.py`

**Interfaces:**
- Consumes: `convert_batch(...) -> BatchResult` and `create_combined_pdf(...) -> Path`.
- UI state: compression level `9`; PNG suffix `_compressed`; overwrite `False`; output directory unset; PDF disabled by default.

- [ ] ファイル選択・ドロップの受け入れ拡張子をBMP/PNGにし、重複パスを除外する。
- [ ] 追加時の初期順を大文字小文字を無視する自然ファイル名順、同名はフルパス順とする。手動ドラッグと上下ボタンによる順序はPDF順にも使う。
- [ ] PNG出力先選択、PNG入力用接尾辞、上書きチェックを追加し、規則が分かる日本語ラベルを付ける。
- [ ] 変換中に一覧・設定の二重操作を防ぎ、結果・失敗一覧・PDF作成結果を表示する。Tkイベントループを止める時間が顕著な場合のみバックグラウンド処理を追加する。
- [ ] PDFチェック時は全画像のPNG変換成功後のみ単一PDFを作成し、PDF保存ダイアログの初期フォルダーには指定済みPNG出力先を使う。
- [ ] GUI操作でBMP/PNG混在、名前順、手動順、保存先、上書きオフ/オン、PDFなし/ありを確認し、画面応答と出力結果を記録する。
- [ ] Commit: `feat: add png input and output controls`

## Task 5: 配布・ドキュメント・PRを整える

**Files:**
- Modify: `README.md`
- Modify: `docs/SPECIFICATION.md`
- Modify: `.github/workflows/build-windows.yml`
- Modify: `bmp2png_pdf.spec`
- Modify: GitHub Issue #1、PR #2、devflow Control #394

**Interfaces:**
- Consumes: final GUI, image service, and PDF exporter from Tasks 2–4.
- Produces: Windows x64 one-folder artifact attached to the existing PR branch, updated usage and design records.

- [ ] READMEと仕様書に入力形式、自然順、ドラッグ並べ替え、圧縮、出力先、PNG接尾辞、上書き、PDF名・保存先・ページ仕様を日本語で記載する。
- [ ] GitHub Actionsの変更パスを新モジュール・依存変更に合わせ、Windows x64 artifactをビルドする。
- [ ] PRビルドを確認し、変更前後のサイズ・所要時間・ピークメモリをPR本文に比較して、GUI操作未確認事項も明記する。
- [ ] Issue #1に原案と既存設計を残したうえで、新しいリファクタリング設計と実装結果を追記する。Control #394の状態と次アクションを実際のPR/CI状態に合わせる。
- [ ] Commit: `docs: document image input and output behavior`
- [ ] Push `feature/bmp2png-pdf-export` を実行し、PR #2の差分・CI・Issueリンクを最終確認する。

## 完了条件

- BMP/PNGからPNGへ、設定した可逆圧縮で変換できる。PNG入力は設定接尾辞つきで出力される。
- 名前順が初期値で、ドラッグ・上下移動でユーザー指定順にできる。
- 指定フォルダーと同ディレクトリ既定動作が機能し、上書きオフでは既存出力を残し、オンでは既存出力を置き換える。選択入力ファイルは常に保護する。
- 任意で画像順どおりの単一PDFを生成し、PDF上の画像画素、DPI、ページ全体表示、単ページ表示を維持する。
- 失敗時の結果が明確で、不完全PDFや破損出力を確定しない。
- Windows x64向けポータブル配布物がCIで生成され、変更前後のサイズと性能比較がPRで説明される。
