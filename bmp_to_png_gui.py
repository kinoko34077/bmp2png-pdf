from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from image_processing import convert_bmp_to_png, create_combined_pdf
from tkinterdnd2 import DND_FILES, TkinterDnD


class BmpToPngApp:
    def __init__(self, root: tk.Misc):
        self.root = root
        self.root.title("BMP → PNG 変換")
        self.root.geometry("760x600")
        self.root.minsize(600, 480)
        self.files: list[Path] = []
        self.drag_index: int | None = None
        self.compression_var = tk.IntVar(value=9)
        self.pdf_enabled_var = tk.BooleanVar(value=False)
        self.pdf_name_var = tk.StringVar(value="まとめ.pdf")
        self._build_ui()

    def _build_ui(self) -> None:
        ttk.Label(self.root, text="BMP → PNG 変換", font=("", 18, "bold")).pack(pady=(16, 5))
        ttk.Label(
            self.root,
            text="BMPを追加して順番を整え、「変換」を押してください。PDFは任意で作成できます。",
        ).pack(pady=(0, 12))

        self.drop_frame = tk.Frame(self.root, relief="groove", borderwidth=2, height=72)
        self.drop_frame.pack(fill="x", padx=18)
        self.drop_frame.pack_propagate(False)
        self.drop_label = ttk.Label(self.drop_frame, text="ここに .bmp をドロップ", anchor="center")
        self.drop_label.pack(expand=True, fill="both")
        for widget in (self.drop_frame, self.drop_label):
            widget.drop_target_register(DND_FILES)
            widget.dnd_bind("<<Drop>>", self.on_drop)

        toolbar = ttk.Frame(self.root)
        toolbar.pack(fill="x", padx=18, pady=10)
        ttk.Button(toolbar, text="BMPを選択", command=self.select_files).pack(side="left")
        ttk.Button(toolbar, text="クリア", command=self.clear_files).pack(side="left", padx=6)
        ttk.Label(toolbar, text="PNG圧縮レベル").pack(side="left", padx=(18, 5))
        self.compression_spin = tk.Spinbox(
            toolbar, from_=0, to=9, width=4, textvariable=self.compression_var
        )
        self.compression_spin.pack(side="left")
        ttk.Label(toolbar, text="（9が高圧縮）").pack(side="left", padx=4)

        list_area = ttk.Frame(self.root)
        list_area.pack(fill="both", expand=True, padx=18, pady=(0, 8))
        self.file_list = tk.Listbox(
            list_area, selectmode=tk.EXTENDED, activestyle="dotbox", exportselection=False
        )
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

        pdf_row = ttk.Frame(self.root)
        pdf_row.pack(fill="x", padx=18, pady=(0, 8))
        self.pdf_check = ttk.Checkbutton(
            pdf_row, text="PDFにする", variable=self.pdf_enabled_var, command=self._toggle_pdf_name
        )
        self.pdf_check.pack(side="left")
        self.pdf_name_entry = ttk.Entry(pdf_row, textvariable=self.pdf_name_var, state="disabled")
        self.pdf_name_entry.pack(side="left", fill="x", expand=True, padx=8)
        self.pdf_button = ttk.Button(pdf_row, text="保存先…", command=self.choose_pdf_name, state="disabled")
        self.pdf_button.pack(side="left")

        bottom = ttk.Frame(self.root)
        bottom.pack(fill="x", padx=18, pady=(0, 12))
        self.status_var = tk.StringVar(value="BMPファイルを追加してください。")
        ttk.Label(bottom, textvariable=self.status_var, anchor="w").pack(side="left", fill="x", expand=True)
        ttk.Button(bottom, text="変換", command=self.convert_files).pack(side="right")

    def on_drop(self, event: tk.Event) -> None:
        self.add_files(self.root.tk.splitlist(event.data))

    def select_files(self) -> None:
        paths = filedialog.askopenfilenames(
            title="BMPファイルを選択",
            filetypes=[("Bitmap files", "*.bmp"), ("All files", "*.*")],
        )
        self.add_files(paths)

    def add_files(self, paths) -> None:
        added = 0
        ignored = 0
        existing = {str(path.resolve()).casefold() for path in self.files}
        for raw_path in paths:
            path = Path(raw_path)
            if not path.is_file() or path.suffix.casefold() != ".bmp":
                ignored += 1
                continue
            key = str(path.resolve()).casefold()
            if key not in existing:
                self.files.append(path)
                self.file_list.insert(tk.END, str(path))
                existing.add(key)
                added += 1
        if added:
            self.status_var.set(f"{added}件追加しました。現在 {len(self.files)} 件のBMPがあります。")
        elif ignored:
            self.status_var.set("BMP以外のファイルは追加されませんでした。")
        else:
            self.status_var.set("新しく追加されたファイルはありません。")

    def clear_files(self) -> None:
        self.files.clear()
        self.file_list.delete(0, tk.END)
        self.status_var.set("BMPファイルを追加してください。")

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
        target = self.file_list.nearest(event.y)
        target = max(0, min(target, len(self.files) - 1))
        if target == self.drag_index:
            return
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
        moved = tuple(sorted(chosen))
        self._rebuild_list(moved)
        if moved:
            self.file_list.see(moved[0])

    def _toggle_pdf_name(self) -> None:
        state = "normal" if self.pdf_enabled_var.get() else "disabled"
        self.pdf_name_entry.configure(state=state)
        self.pdf_button.configure(state=state)

    def choose_pdf_name(self) -> None:
        name = self.pdf_name_var.get().strip() or "まとめ.pdf"
        path = filedialog.asksaveasfilename(
            title="PDFの保存先を選択",
            initialfile=name,
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
        )
        if path:
            self.pdf_name_var.set(Path(path).name)

    def _pdf_output_path(self) -> Path | None:
        raw_name = self.pdf_name_var.get().strip()
        if not raw_name:
            messagebox.showwarning("PDFファイル名", "PDFファイル名を入力してください。")
            self.pdf_name_entry.focus_set()
            return None
        if Path(raw_name).name != raw_name or raw_name in {".", ".."}:
            messagebox.showwarning("PDFファイル名", "ファイル名だけを入力してください。保存先はダイアログで指定します。")
            return None
        if not raw_name.casefold().endswith(".pdf"):
            raw_name += ".pdf"
        chosen = filedialog.asksaveasfilename(
            title="PDFの保存先を選択",
            initialfile=raw_name,
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
        )
        return Path(chosen) if chosen else None

    def convert_files(self) -> None:
        if not self.files:
            messagebox.showinfo("BMP → PNG", "変換するBMPファイルがありません。")
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

        png_paths_expected = [path.with_suffix(".png").resolve() for path in self.files]
        if pdf_path is not None:
            pdf_resolved = pdf_path.resolve()
            if pdf_resolved in {path.resolve() for path in self.files} | set(png_paths_expected):
                messagebox.showwarning("保存先エラー", "PDFの保存先がBMPまたはPNGの保存先と重複しています。")
                return

        created_pngs: list[Path] = []
        failed: list[str] = []
        for input_path in self.files:
            try:
                created_pngs.append(convert_bmp_to_png(input_path, compression))
            except Exception as exc:
                failed.append(f"{input_path.name}: {exc}")

        if failed:
            details = "\n".join(failed[:8])
            if len(failed) > 8:
                details += f"\nほか {len(failed) - 8} 件"
            messagebox.showwarning(
                "変換結果",
                f"{len(created_pngs)}件のPNGを作成しましたが、{len(failed)}件でエラーが発生しました。\n"
                "不完全なPDFは作成していません。\n\n" + details,
            )
            self.status_var.set(f"完了: PNG成功 {len(created_pngs)} 件 / 失敗 {len(failed)} 件")
            return

        if pdf_path is not None:
            try:
                create_combined_pdf(created_pngs, pdf_path)
            except Exception as exc:
                messagebox.showerror("PDF作成エラー", f"PNGは作成しましたが、PDFを作成できませんでした。\n{exc}")
                self.status_var.set("PNG変換完了。PDF作成に失敗しました。")
                return
            messagebox.showinfo(
                "変換完了",
                f"{len(created_pngs)}件のPNGを作成し、1つのPDFにまとめました。\n{pdf_path}",
            )
            self.status_var.set(f"完了: PNG {len(created_pngs)} 件 / PDF 1件")
        else:
            messagebox.showinfo(
                "変換完了",
                f"{len(created_pngs)}件のBMPをPNGへ変換しました。\nPDFは作成していません。",
            )
            self.status_var.set(f"PNG変換完了: {len(created_pngs)} 件")

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    root = TkinterDnD.Tk()
    BmpToPngApp(root).run()


if __name__ == "__main__":
    main()
