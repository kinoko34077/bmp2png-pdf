from __future__ import annotations

import queue
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from conversion_service import BatchResult, build_output_path, convert_batch, sort_input_paths
from pdf_export import create_combined_pdf
from tkinterdnd2 import DND_FILES, TkinterDnD


class BmpToPngApp:
    def __init__(self, root: tk.Misc):
        self.root = root
        self.root.title("BMP / PNG 圧縮・PDF作成")
        self.root.geometry("800x680")
        self.root.minsize(650, 560)
        self.files: list[Path] = []
        self.drag_index: int | None = None
        self.compression_var = tk.IntVar(value=9)
        self.suffix_var = tk.StringVar(value="_compressed")
        self.output_dir_var = tk.StringVar(value="")
        self.overwrite_var = tk.BooleanVar(value=False)
        self.pdf_enabled_var = tk.BooleanVar(value=False)
        self.pdf_name_var = tk.StringVar(value="まとめ.pdf")
        self._completion_queue: queue.SimpleQueue[
            tuple[BatchResult | None, Path | None, str | None]
        ] = queue.SimpleQueue()
        self._worker_thread: threading.Thread | None = None
        self._busy_controls: list[tk.Widget] = []
        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        ttk.Label(self.root, text="BMP / PNG 圧縮・PDF作成", font=("", 18, "bold")).pack(pady=(14, 4))
        ttk.Label(self.root, text="BMP・PNGを高圧縮PNGに変換し、必要なら一覧順で1つのPDFにまとめます。").pack(pady=(0, 10))

        self.drop_frame = tk.Frame(self.root, relief="groove", borderwidth=2, height=66)
        self.drop_frame.pack(fill="x", padx=18)
        self.drop_frame.pack_propagate(False)
        self.drop_label = ttk.Label(self.drop_frame, text="ここに .bmp / .png をドロップ", anchor="center")
        self.drop_label.pack(expand=True, fill="both")
        for widget in (self.drop_frame, self.drop_label):
            widget.drop_target_register(DND_FILES)
            widget.dnd_bind("<<Drop>>", self.on_drop)

        toolbar = ttk.Frame(self.root)
        toolbar.pack(fill="x", padx=18, pady=8)
        self.select_button = ttk.Button(toolbar, text="画像を選択", command=self.select_files)
        self.select_button.pack(side="left")
        self.clear_button = ttk.Button(toolbar, text="クリア", command=self.clear_files)
        self.clear_button.pack(side="left", padx=6)
        ttk.Label(toolbar, text="PNG圧縮").pack(side="left", padx=(15, 5))
        self.compression_spin = tk.Spinbox(toolbar, from_=0, to=9, width=4, textvariable=self.compression_var)
        self.compression_spin.pack(side="left")
        ttk.Label(toolbar, text="（9が高圧縮）").pack(side="left", padx=4)

        list_area = ttk.Frame(self.root)
        list_area.pack(fill="both", expand=True, padx=18, pady=(0, 6))
        self.file_list = tk.Listbox(list_area, selectmode=tk.EXTENDED, activestyle="dotbox", exportselection=False)
        scrollbar = ttk.Scrollbar(list_area, orient="vertical", command=self.file_list.yview)
        self.file_list.configure(yscrollcommand=scrollbar.set)
        self.file_list.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.file_list.bind("<Button-1>", self._on_drag_start, add="+")
        self.file_list.bind("<B1-Motion>", self._on_drag_motion, add="+")
        self.file_list.bind("<ButtonRelease-1>", self._on_drag_end, add="+")
        reorder = ttk.Frame(self.root)
        reorder.pack(fill="x", padx=18, pady=(0, 8))
        self.move_up_button = ttk.Button(reorder, text="上へ", command=lambda: self.move_selected(-1))
        self.move_up_button.pack(side="left")
        self.move_down_button = ttk.Button(reorder, text="下へ", command=lambda: self.move_selected(1))
        self.move_down_button.pack(side="left", padx=6)
        ttk.Label(reorder, text="追加時はファイル名順。ドラッグまたはボタンで変更できます。").pack(side="left", padx=8)

        settings = ttk.LabelFrame(self.root, text="PNG出力")
        settings.pack(fill="x", padx=18, pady=(0, 8))
        folder_row = ttk.Frame(settings)
        folder_row.pack(fill="x", padx=8, pady=(7, 3))
        ttk.Label(folder_row, text="出力先").pack(side="left")
        self.output_dir_entry = ttk.Entry(folder_row, textvariable=self.output_dir_var, state="readonly")
        self.output_dir_entry.pack(side="left", fill="x", expand=True, padx=8)
        self.output_dir_button = ttk.Button(folder_row, text="参照…", command=self.choose_output_dir)
        self.output_dir_button.pack(side="left")
        self.clear_output_dir_button = ttk.Button(folder_row, text="解除", command=lambda: self.output_dir_var.set(""))
        self.clear_output_dir_button.pack(side="left", padx=(5, 0))
        options_row = ttk.Frame(settings)
        options_row.pack(fill="x", padx=8, pady=(3, 7))
        ttk.Label(options_row, text="PNG入力の接尾辞").pack(side="left")
        self.suffix_entry = ttk.Entry(options_row, textvariable=self.suffix_var, width=18)
        self.suffix_entry.pack(side="left", padx=8)
        ttk.Label(options_row, text="（BMPの出力名には付きません）").pack(side="left")
        self.overwrite_check = ttk.Checkbutton(
            options_row,
            text="上書きする",
            variable=self.overwrite_var,
            command=self._toggle_suffix_entry,
        )
        self.overwrite_check.pack(side="right")
        ttk.Label(settings, text="出力先未指定なら、各画像と同じフォルダーに保存します。").pack(anchor="w", padx=8, pady=(0, 6))

        pdf_row = ttk.LabelFrame(self.root, text="PDF出力")
        pdf_row.pack(fill="x", padx=18, pady=(0, 8))
        pdf_inner = ttk.Frame(pdf_row)
        pdf_inner.pack(fill="x", padx=8, pady=7)
        self.pdf_check = ttk.Checkbutton(
            pdf_inner,
            text="PDFにする",
            variable=self.pdf_enabled_var,
            command=self._toggle_pdf_name,
        )
        self.pdf_check.pack(side="left")
        self.pdf_name_entry = ttk.Entry(pdf_inner, textvariable=self.pdf_name_var, state="disabled")
        self.pdf_name_entry.pack(side="left", fill="x", expand=True, padx=8)
        ttk.Label(pdf_row, text="画像1枚につきA4 1ページ。元の画素・解像度を維持します。").pack(anchor="w", padx=8, pady=(0, 6))

        bottom = ttk.Frame(self.root)
        bottom.pack(fill="x", padx=18, pady=(0, 12))
        self.status_var = tk.StringVar(value="BMPまたはPNGファイルを追加してください。")
        ttk.Label(bottom, textvariable=self.status_var, anchor="w").pack(side="left", fill="x", expand=True)
        self.convert_button = ttk.Button(bottom, text="変換", command=self.convert_files)
        self.convert_button.pack(side="right")
        self._busy_controls = [
            self.select_button,
            self.clear_button,
            self.compression_spin,
            self.file_list,
            self.move_up_button,
            self.move_down_button,
            self.output_dir_entry,
            self.output_dir_button,
            self.clear_output_dir_button,
            self.suffix_entry,
            self.overwrite_check,
            self.pdf_check,
            self.pdf_name_entry,
        ]
        self._toggle_suffix_entry()

    def on_drop(self, event: tk.Event) -> None:
        self.add_files(self.root.tk.splitlist(event.data))

    def select_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title="BMP / PNGファイルを選択",
            filetypes=[("BMP / PNG files", "*.bmp *.png"), ("All files", "*.*")],
        )
        self.add_files(paths)

    def add_files(self, paths) -> None:
        if self._worker_thread is not None:
            return
        existing = {str(path.resolve()).casefold() for path in self.files}
        new_paths = sort_input_paths([Path(raw) for raw in paths])
        additions = []
        for path in new_paths:
            key = str(path.resolve()).casefold()
            if key not in existing:
                existing.add(key)
                additions.append(path)
        self.files.extend(additions)
        added = len(additions)
        self._rebuild_list()
        if added:
            self.status_var.set(f"{added}件追加しました。現在 {len(self.files)} 件です。")
        else:
            self.status_var.set("新しく追加されたBMP/PNGファイルはありません。")

    def clear_files(self) -> None:
        if self._worker_thread is not None:
            return
        self.files.clear()
        self.file_list.delete(0, tk.END)
        self.status_var.set("BMPまたはPNGファイルを追加してください。")

    def _rebuild_list(self, selected: tuple[int, ...] = ()) -> None:
        self.file_list.delete(0, tk.END)
        for path in self.files:
            self.file_list.insert(tk.END, str(path))
        for index in selected:
            if 0 <= index < len(self.files):
                self.file_list.selection_set(index)

    def _on_drag_start(self, event: tk.Event) -> None:
        if self._worker_thread is not None:
            return
        index = self.file_list.nearest(event.y)
        self.drag_index = index if 0 <= index < len(self.files) else None

    def _on_drag_motion(self, event: tk.Event) -> None:
        if self._worker_thread is not None or self.drag_index is None or not self.files:
            return
        target = max(0, min(self.file_list.nearest(event.y), len(self.files) - 1))
        if target != self.drag_index:
            item = self.files.pop(self.drag_index)
            self.files.insert(target, item)
            self.file_list.delete(self.drag_index)
            self.file_list.insert(target, str(item))
            self.drag_index = target
            self.file_list.selection_clear(0, tk.END)
            self.file_list.selection_set(target)
            self.file_list.activate(target)
            self.file_list.see(target)

    def _on_drag_end(self, _event: tk.Event) -> None:
        self.drag_index = None

    def move_selected(self, direction: int) -> None:
        if self._worker_thread is not None:
            return
        selected = list(self.file_list.curselection())
        if not selected:
            return
        chosen = set(selected)
        if direction < 0:
            for index in selected:
                if index > 0 and index - 1 not in chosen:
                    self.files[index - 1], self.files[index] = self.files[index], self.files[index - 1]
                    chosen.remove(index)
                    chosen.add(index - 1)
        else:
            for index in reversed(selected):
                if index < len(self.files) - 1 and index + 1 not in chosen:
                    self.files[index + 1], self.files[index] = self.files[index], self.files[index + 1]
                    chosen.remove(index)
                    chosen.add(index + 1)
        self._rebuild_list(tuple(sorted(chosen)))

    def choose_output_dir(self) -> None:
        if self._worker_thread is not None:
            return
        folder = filedialog.askdirectory(title="PNGの出力先フォルダーを選択")
        if folder:
            self.output_dir_var.set(folder)

    def _toggle_pdf_name(self) -> None:
        self.pdf_name_entry.configure(state="normal" if self.pdf_enabled_var.get() else "disabled")

    def _toggle_suffix_entry(self) -> None:
        state = "disabled" if self.overwrite_var.get() else "normal"
        self.suffix_entry.configure(state=state)

    def _set_busy(self, busy: bool) -> None:
        for widget in self._busy_controls:
            widget.configure(state="disabled" if busy else "normal")
        self.convert_button.configure(state="disabled" if busy else "normal")
        if not busy:
            self.output_dir_entry.configure(state="readonly")
            self._toggle_suffix_entry()
            self._toggle_pdf_name()

    def _pdf_output_path(self) -> Path | None:
        raw_name = self.pdf_name_var.get().strip()
        if not raw_name or Path(raw_name).name != raw_name or raw_name in {".", ".."} or any(c in raw_name for c in '<>:"/\\|?*'):
            messagebox.showwarning("PDFファイル名", "PDFのファイル名を入力してください（保存先はダイアログで指定します）。")
            self.pdf_name_entry.focus_set()
            return None
        if not raw_name.casefold().endswith(".pdf"):
            raw_name += ".pdf"
        initial_dir = self.output_dir_var.get().strip() or (str(self.files[0].parent) if self.files else None)
        chosen = filedialog.asksaveasfilename(
            title="PDFの保存先を選択", initialdir=initial_dir, initialfile=raw_name,
            defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")],
        )
        return Path(chosen) if chosen else None

    def convert_files(self) -> None:
        if self._worker_thread is not None:
            return
        if not self.files:
            messagebox.showinfo("変換", "変換するBMPまたはPNGファイルがありません。")
            return
        try:
            compression = int(self.compression_var.get())
            if not 0 <= compression <= 9:
                raise ValueError
        except (ValueError, tk.TclError):
            messagebox.showwarning("PNG圧縮レベル", "0〜9の整数を指定してください。")
            return
        pdf_path = self._pdf_output_path() if self.pdf_enabled_var.get() else None
        if self.pdf_enabled_var.get() and pdf_path is None:
            return

        raw_output_dir = self.output_dir_var.get().strip()
        job_files = tuple(self.files)
        self._set_busy(True)
        self.status_var.set("変換中です…")
        self._worker_thread = threading.Thread(
            target=self._run_conversion,
            args=(
                job_files,
                Path(raw_output_dir) if raw_output_dir else None,
                self.suffix_var.get(),
                compression,
                self.overwrite_var.get(),
                pdf_path,
            ),
            name="bmp2png-conversion",
            daemon=True,
        )
        try:
            self._worker_thread.start()
        except RuntimeError as exc:
            self._worker_thread = None
            self._set_busy(False)
            messagebox.showerror("変換エラー", str(exc))
            self.status_var.set("変換を開始できませんでした。")
            return
        self.root.after(100, self._poll_conversion)

    def _run_conversion(
        self,
        files: tuple[Path, ...],
        output_dir: Path | None,
        png_suffix: str,
        compression: int,
        overwrite: bool,
        pdf_path: Path | None,
    ) -> None:
        result = None
        final_pdf = None
        try:
            result = convert_batch(files, output_dir, png_suffix, compression, overwrite)
            if result.failures or pdf_path is None:
                self._completion_queue.put((result, None, None))
                return

            final_pdf = build_output_path(
                pdf_path,
                overwrite,
                set(files),
                set(result.output_paths),
            )
            create_combined_pdf(result.output_paths, final_pdf)
            self._completion_queue.put((result, final_pdf, None))
        except Exception as exc:
            self._completion_queue.put((result, final_pdf, str(exc)))

    def _poll_conversion(self) -> None:
        try:
            result, final_pdf, error = self._completion_queue.get_nowait()
        except queue.Empty:
            if self._worker_thread is not None and self._worker_thread.is_alive():
                self.root.after(100, self._poll_conversion)
            else:
                self._worker_thread = None
                self._set_busy(False)
                messagebox.showerror("変換エラー", "処理結果を取得できませんでした。")
                self.status_var.set("変換に失敗しました。")
            return

        self._worker_thread = None
        self._set_busy(False)
        self._show_conversion_result(result, final_pdf, error)

    def _show_conversion_result(
        self,
        result: BatchResult | None,
        final_pdf: Path | None,
        error: str | None,
    ) -> None:
        if error:
            created_pngs = len(result.output_paths) if result else 0
            prefix = f"PNG {created_pngs}件は作成済みです。\n" if created_pngs else ""
            messagebox.showerror("変換エラー", prefix + error)
            self.status_var.set("PDF作成に失敗しました。" if created_pngs else "変換に失敗しました。")
            return
        if result is None:
            messagebox.showerror("変換エラー", "処理結果がありません。")
            self.status_var.set("変換に失敗しました。")
            return
        if result.failures:
            details = "\n".join(f"{failure.input_path.name}: {failure.error}" for failure in result.failures[:8])
            if len(result.failures) > 8:
                details += f"\nほか {len(result.failures) - 8} 件"
            messagebox.showwarning(
                "変換結果",
                f"PNG成功 {len(result.output_paths)}件 / 失敗 {len(result.failures)}件。\n"
                "不完全なPDFは作成していません。\n\n" + details,
            )
            self.status_var.set(
                f"完了: PNG成功 {len(result.output_paths)} 件 / 失敗 {len(result.failures)} 件"
            )
            return
        if final_pdf:
            messagebox.showinfo(
                "変換完了",
                f"{len(result.output_paths)}件のPNGを作成し、1つのPDFにまとめました。\n{final_pdf}",
            )
            self.status_var.set(f"完了: PNG {len(result.output_paths)} 件 / PDF 1件")
        else:
            messagebox.showinfo("変換完了", f"{len(result.output_paths)}件をPNGに変換しました。")
            self.status_var.set(f"PNG変換完了: {len(result.output_paths)} 件")

    def _on_close(self) -> None:
        if self._worker_thread is not None and self._worker_thread.is_alive():
            messagebox.showinfo("変換中", "処理が完了してからアプリを閉じてください。")
            return
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    root = TkinterDnD.Tk()
    BmpToPngApp(root).run()


if __name__ == "__main__":
    main()
