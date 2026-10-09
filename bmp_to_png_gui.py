from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from conversion_service import build_output_path, convert_batch, sort_input_paths
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
        self._build_ui()

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
        ttk.Button(toolbar, text="画像を選択", command=self.select_files).pack(side="left")
        ttk.Button(toolbar, text="クリア", command=self.clear_files).pack(side="left", padx=6)
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
        ttk.Button(reorder, text="上へ", command=lambda: self.move_selected(-1)).pack(side="left")
        ttk.Button(reorder, text="下へ", command=lambda: self.move_selected(1)).pack(side="left", padx=6)
        ttk.Label(reorder, text="追加時はファイル名順。ドラッグまたはボタンで変更できます。").pack(side="left", padx=8)

        settings = ttk.LabelFrame(self.root, text="PNG出力")
        settings.pack(fill="x", padx=18, pady=(0, 8))
        folder_row = ttk.Frame(settings)
        folder_row.pack(fill="x", padx=8, pady=(7, 3))
        ttk.Label(folder_row, text="出力先").pack(side="left")
        ttk.Entry(folder_row, textvariable=self.output_dir_var, state="readonly").pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(folder_row, text="参照…", command=self.choose_output_dir).pack(side="left")
        ttk.Button(folder_row, text="解除", command=lambda: self.output_dir_var.set("")).pack(side="left", padx=(5, 0))
        options_row = ttk.Frame(settings)
        options_row.pack(fill="x", padx=8, pady=(3, 7))
        ttk.Label(options_row, text="PNG入力の接尾辞").pack(side="left")
        ttk.Entry(options_row, textvariable=self.suffix_var, width=18).pack(side="left", padx=8)
        ttk.Label(options_row, text="（BMPの出力名には付きません）").pack(side="left")
        ttk.Checkbutton(options_row, text="上書きする", variable=self.overwrite_var).pack(side="right")
        ttk.Label(settings, text="出力先未指定なら、各画像と同じフォルダーに保存します。").pack(anchor="w", padx=8, pady=(0, 6))

        pdf_row = ttk.LabelFrame(self.root, text="PDF出力")
        pdf_row.pack(fill="x", padx=18, pady=(0, 8))
        pdf_inner = ttk.Frame(pdf_row)
        pdf_inner.pack(fill="x", padx=8, pady=7)
        self.pdf_check = ttk.Checkbutton(pdf_inner, text="PDFにする", variable=self.pdf_enabled_var, command=self._toggle_pdf_name)
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

    def on_drop(self, event: tk.Event) -> None:
        self.add_files(self.root.tk.splitlist(event.data))

    def select_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title="BMP / PNGファイルを選択",
            filetypes=[("BMP / PNG files", "*.bmp *.png"), ("All files", "*.*")],
        )
        self.add_files(paths)

    def add_files(self, paths) -> None:
        existing = {str(path.resolve()).casefold() for path in self.files}
        new_paths = sort_input_paths([Path(raw) for raw in paths])
        additions = [path for path in new_paths if str(path.resolve()).casefold() not in existing]
        self.files.extend(additions)
        added = len(additions)
        self._rebuild_list()
        if added:
            self.status_var.set(f"{added}件追加しました。現在 {len(self.files)} 件です。")
        else:
            self.status_var.set("新しく追加されたBMP/PNGファイルはありません。")

    def clear_files(self) -> None:
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
        index = self.file_list.nearest(event.y)
        self.drag_index = index if 0 <= index < len(self.files) else None

    def _on_drag_motion(self, event: tk.Event) -> None:
        if self.drag_index is None or not self.files:
            return
        target = max(0, min(self.file_list.nearest(event.y), len(self.files) - 1))
        if target != self.drag_index:
            item = self.files.pop(self.drag_index)
            self.files.insert(target, item)
            self.drag_index = target
            self._rebuild_list((target,))
            self.file_list.activate(target)
            self.file_list.see(target)

    def _on_drag_end(self, _event: tk.Event) -> None:
        self.drag_index = None

    def move_selected(self, direction: int) -> None:
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
        folder = filedialog.askdirectory(title="PNGの出力先フォルダーを選択")
        if folder:
            self.output_dir_var.set(folder)

    def _toggle_pdf_name(self) -> None:
        self.pdf_name_entry.configure(state="normal" if self.pdf_enabled_var.get() else "disabled")

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

        self.convert_button.configure(state="disabled")
        self.status_var.set("変換中です…")
        self.root.update_idletasks()
        try:
            raw_output_dir = self.output_dir_var.get().strip()
            result = convert_batch(
                self.files, Path(raw_output_dir) if raw_output_dir else None,
                self.suffix_var.get(), compression, self.overwrite_var.get(),
            )
            if result.failures:
                details = "\n".join(f"{f.input_path.name}: {f.error}" for f in result.failures[:8])
                if len(result.failures) > 8:
                    details += f"\nほか {len(result.failures) - 8} 件"
                messagebox.showwarning(
                    "変換結果",
                    f"PNG成功 {len(result.output_paths)}件 / 失敗 {len(result.failures)}件。\n"
                    "不完全なPDFは作成していません。\n\n" + details,
                )
                self.status_var.set(f"完了: PNG成功 {len(result.output_paths)} 件 / 失敗 {len(result.failures)} 件")
                return
            final_pdf = None
            if pdf_path is not None:
                reserved = {path.resolve() for path in result.output_paths}
                final_pdf = build_output_path(
                    pdf_path, self.overwrite_var.get(),
                    {path.resolve() for path in self.files}, reserved,
                )
                create_combined_pdf(result.output_paths, final_pdf)
            if final_pdf:
                messagebox.showinfo("変換完了", f"{len(result.output_paths)}件のPNGを作成し、1つのPDFにまとめました。\n{final_pdf}")
                self.status_var.set(f"完了: PNG {len(result.output_paths)} 件 / PDF 1件")
            else:
                messagebox.showinfo("変換完了", f"{len(result.output_paths)}件をPNGに変換しました。")
                self.status_var.set(f"PNG変換完了: {len(result.output_paths)} 件")
        except Exception as exc:
            messagebox.showerror("変換エラー", str(exc))
            self.status_var.set("変換に失敗しました。")
        finally:
            self.convert_button.configure(state="normal")

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    root = TkinterDnD.Tk()
    BmpToPngApp(root).run()


if __name__ == "__main__":
    main()
