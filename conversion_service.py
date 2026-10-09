from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import AbstractSet, Sequence

from image_processing import SUPPORTED_SUFFIXES, convert_image_to_png


_DIGIT_PARTS = re.compile(r"(\d+)")


@dataclass(frozen=True)
class ConversionFailure:
    input_path: Path
    error: str


@dataclass(frozen=True)
class BatchResult:
    output_paths: tuple[Path, ...]
    failures: tuple[ConversionFailure, ...]


def sort_input_paths(paths: Sequence[Path]) -> list[Path]:
    # Resolve each path once; resolving again in the sort key is needless filesystem work.
    unique: dict[str, tuple[Path, tuple, str]] = {}
    for raw_path in paths:
        path = Path(raw_path)
        if path.suffix.casefold() not in SUPPORTED_SUFFIXES or not path.is_file():
            continue
        resolved_key = str(path.resolve()).casefold()
        name_parts = _DIGIT_PARTS.split(path.name.casefold())
        natural = tuple(
            (0, int(part)) if part.isdigit() else (1, part)
            for part in name_parts
        )
        unique.setdefault(resolved_key, (path, natural, resolved_key))
    ordered = sorted(unique.values(), key=lambda item: (item[1], item[2]))
    return [item[0] for item in ordered]


def _available_output_path(
    requested_path: Path,
    overwrite: bool,
    protected_inputs: AbstractSet[Path],
    reserved_outputs: AbstractSet[Path],
) -> Path:
    """Select a safe path; input sets contain already-resolved paths."""
    requested_key = requested_path.resolve()
    if (
        requested_key not in protected_inputs
        and requested_key not in reserved_outputs
        and (overwrite or not requested_path.exists())
    ):
        return requested_path

    serial = 2
    while True:
        numbered = requested_path.with_name(
            f"{requested_path.stem}_{serial}{requested_path.suffix}"
        )
        numbered_key = numbered.resolve()
        if (
            numbered_key not in protected_inputs
            and numbered_key not in reserved_outputs
            and not numbered.exists()
        ):
            return numbered
        serial += 1


def _build_png_output_path(
    input_path: Path,
    output_dir: Path | None,
    png_suffix: str,
    overwrite: bool,
    protected_inputs: AbstractSet[Path],
    reserved_outputs: AbstractSet[Path],
) -> Path:
    """Build a PNG path from already-resolved protected and reserved sets."""
    input_path = Path(input_path)
    base = input_path.stem + (png_suffix if input_path.suffix.casefold() == ".png" else "")
    directory = Path(output_dir) if output_dir is not None else input_path.parent
    candidate = directory / f"{base}.png"
    return _available_output_path(
        candidate, overwrite, protected_inputs, reserved_outputs
    )


def build_png_output_path(
    input_path: Path,
    output_dir: Path | None,
    png_suffix: str,
    overwrite: bool,
    protected_inputs: AbstractSet[Path],
    reserved_outputs: AbstractSet[Path],
) -> Path:
    """Build a PNG output path while accepting ordinary, unresolved path sets."""
    protected = {Path(path).resolve() for path in protected_inputs}
    reserved = {Path(path).resolve() for path in reserved_outputs}
    return _build_png_output_path(
        input_path, output_dir, png_suffix, overwrite, protected, reserved
    )


def build_output_path(
    requested_path: Path,
    overwrite: bool,
    protected_inputs: AbstractSet[Path] = frozenset(),
    reserved_outputs: AbstractSet[Path] = frozenset(),
) -> Path:
    """Select a safe path, resolving the protected and reserved sets once."""
    requested_path = Path(requested_path)
    protected = {path.resolve() for path in protected_inputs}
    reserved = {path.resolve() for path in reserved_outputs}
    return _available_output_path(
        requested_path, overwrite, protected, reserved
    )


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
        if input_path.suffix.casefold() not in SUPPORTED_SUFFIXES:
            failures.append(ConversionFailure(input_path, "BMPまたはPNGではありません。"))
            continue
        output_path = _build_png_output_path(
            input_path, output_dir, png_suffix, overwrite, protected_inputs, reserved
        )
        output_key = output_path.resolve()
        reserved.add(output_key)
        try:
            outputs.append(convert_image_to_png(input_path, output_path, compression_level))
        except Exception as exc:
            reserved.discard(output_key)
            failures.append(ConversionFailure(input_path, str(exc)))
    return BatchResult(tuple(outputs), tuple(failures))
