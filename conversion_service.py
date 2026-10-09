from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import AbstractSet, Sequence

from image_processing import convert_image_to_png


@dataclass(frozen=True)
class ConversionFailure:
    input_path: Path
    error: str


@dataclass(frozen=True)
class BatchResult:
    output_paths: tuple[Path, ...]
    failures: tuple[ConversionFailure, ...]


def natural_name_key(path: Path) -> tuple:
    import re

    name = path.name.casefold()
    parts = re.split(r"(\d+)", name)
    natural = tuple((0, int(part)) if part.isdigit() else (1, part) for part in parts)
    return natural, str(path.resolve()).casefold()


def sort_input_paths(paths: Sequence[Path]) -> list[Path]:
    unique: dict[str, Path] = {}
    for raw_path in paths:
        path = Path(raw_path)
        if path.suffix.casefold() in {".bmp", ".png"} and path.is_file():
            unique.setdefault(str(path.resolve()).casefold(), path)
    return sorted(unique.values(), key=natural_name_key)


def build_png_output_path(
    input_path: Path,
    output_dir: Path | None,
    png_suffix: str,
    overwrite: bool,
    protected_inputs: AbstractSet[Path],
    reserved_outputs: AbstractSet[Path],
) -> Path:
    input_path = Path(input_path)
    base = input_path.stem + (png_suffix if input_path.suffix.casefold() == ".png" else "")
    directory = Path(output_dir) if output_dir is not None else input_path.parent
    candidate = directory / f"{base}.png"
    protected = {item.resolve() for item in protected_inputs}
    reserved = {item.resolve() for item in reserved_outputs}
    candidate_key = candidate.resolve()
    if candidate_key not in protected and candidate_key not in reserved and (overwrite or not candidate.exists()):
        return candidate

    serial = 2
    while True:
        numbered = directory / f"{base}_{serial}.png"
        key = numbered.resolve()
        if key not in protected and key not in reserved and not numbered.exists():
            return numbered
        serial += 1


def build_output_path(
    requested_path: Path,
    overwrite: bool,
    protected_inputs: AbstractSet[Path] = frozenset(),
    reserved_outputs: AbstractSet[Path] = frozenset(),
) -> Path:
    requested_path = Path(requested_path)
    protected = {item.resolve() for item in protected_inputs}
    reserved = {item.resolve() for item in reserved_outputs}
    key = requested_path.resolve()
    if key not in protected and key not in reserved and (overwrite or not requested_path.exists()):
        return requested_path
    serial = 2
    while True:
        numbered = requested_path.with_name(f"{requested_path.stem}_{serial}{requested_path.suffix}")
        if numbered.resolve() not in protected | reserved and not numbered.exists():
            return numbered
        serial += 1


def convert_batch(
    inputs: Sequence[Path],
    output_dir: Path | None,
    png_suffix: str,
    compression_level: int,
    overwrite: bool,
) -> BatchResult:
    if not png_suffix or any(char in png_suffix for char in '<>:"/\\|?*'):
        raise ValueError("PNG接尾辞には空欄やファイル名に使えない文字を指定できません。")
    if not 0 <= compression_level <= 9:
        raise ValueError("PNG圧縮レベルは0〜9で指定してください。")

    ordered = [Path(path) for path in inputs]
    protected_inputs = {path.resolve() for path in ordered}
    reserved: set[Path] = set()
    outputs: list[Path] = []
    failures: list[ConversionFailure] = []
    for input_path in ordered:
        if input_path.suffix.casefold() not in {".bmp", ".png"}:
            failures.append(ConversionFailure(input_path, "BMPまたはPNGではありません。"))
            continue
        output_path = build_png_output_path(
            input_path, output_dir, png_suffix, overwrite, protected_inputs, reserved
        )
        reserved.add(output_path.resolve())
        try:
            outputs.append(convert_image_to_png(input_path, output_path, compression_level))
        except Exception as exc:
            failures.append(ConversionFailure(input_path, str(exc)))
    return BatchResult(tuple(outputs), tuple(failures))
