#!/usr/bin/env python3
"""
Dataset Renaming Tool for Roboflow / YOLO Datasets.

Renames all source files of a dataset across splits (train, valid, test)
following the naming convention:
    <dataset_name><separator><split><separator><numeric_id_4_digits>
e.g.:
    v5-train-0001.jpg  and  v5-train-0001.txt
    aerial-test-1267.jpg  and  aerial-test-1267.txt

Both image and corresponding label files (.txt) are renamed synchronously.
Extensions are strictly preserved.
Includes safe two-phase renaming to prevent collision/overwrite issues,
support for dry-run simulation, and generating a rename_mapping.json audit file.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}
LABEL_EXTENSION = ".txt"
DEFAULT_SPLITS = ("train", "valid", "test")


class TerminalColor:
    """Terminal ANSI colors for user-friendly feedback."""
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"

    @classmethod
    def colorize(cls, text: str, color: str, enabled: bool = True) -> str:
        if not enabled or not sys.stdout.isatty():
            return text
        return f"{color}{text}{cls.ENDC}"


@dataclass
class RenamePair:
    """Represents a source file pair and their computed target paths."""
    split: str
    original_stem: str
    image_src: Path
    image_dst: Path
    label_src: Optional[Path] = None
    label_dst: Optional[Path] = None
    aux_files: List[Tuple[Path, Path]] = field(default_factory=list)


@dataclass
class RenamePlan:
    """Complete renaming execution plan."""
    dataset_path: Path
    prefix: str
    pairs: List[RenamePair]
    total_images: int
    total_labels: int
    unpaired_images: int
    unpaired_labels: int


@dataclass
class DatasetRenamerConfig:
    """Configuration options for renaming dataset files."""
    dataset_path: Path
    dataset_base_dir: Optional[Path] = None
    prefix: Optional[str] = None
    separator: str = "-"
    splits: Tuple[str, ...] = DEFAULT_SPLITS
    images_dir_name: str = "images"
    labels_dir_name: str = "labels"
    digits: int = 4
    start_index: int = 1
    global_counter: bool = False  # False = counter resets per split; True = single continuous counter
    dry_run: bool = False
    save_mapping: bool = True
    clean_zone_identifiers: bool = False


class DatasetRenamer:
    """
    Modular engine to discover, plan, and safely rename dataset images and labels.
    """

    def __init__(self, config: DatasetRenamerConfig):
        self.config = config

    @staticmethod
    def default_dataset_dir() -> Path:
        """Locates the default datasets directory."""
        script_dir = Path(__file__).resolve().parent
        candidates = [
            script_dir.parent.parent / "dataset",          # from scripts/utils -> experiments/dataset
            script_dir.parent / "dataset",                 # from scripts -> experiments/dataset
            Path.cwd() / "experiments" / "dataset",        # root
            Path.cwd() / "dataset",                        # experiments dir
            Path.cwd(),
        ]
        for candidate in candidates:
            if candidate.exists() and candidate.is_dir():
                return candidate.resolve()
        return (script_dir.parent.parent / "dataset").resolve()

    def resolve_dataset_path(self, path_or_name: Path | str) -> Path:
        """Resolves a dataset path or folder name."""
        p = Path(path_or_name)
        if p.is_absolute() and p.exists():
            return p.resolve()

        if self.config.dataset_base_dir:
            candidate = self.config.dataset_base_dir / p
            if candidate.exists():
                return candidate.resolve()

        cwd_cand = Path.cwd() / p
        if cwd_cand.exists():
            return cwd_cand.resolve()

        if self.config.dataset_base_dir:
            return (self.config.dataset_base_dir / p).resolve()
        return cwd_cand.resolve()

    def get_effective_prefix(self) -> str:
        """Determines the prefix to use for naming."""
        if self.config.prefix:
            return self.config.prefix.strip()
        # Fall back to dataset directory name
        return self.config.dataset_path.name

    def build_plan(self) -> RenamePlan:
        """
        Scans all configured splits, matches images with their labels,
        and computes the full renaming plan.
        """
        prefix = self.get_effective_prefix()
        pairs: List[RenamePair] = []
        global_idx = self.config.start_index
        total_images = 0
        total_labels = 0
        unpaired_images = 0
        unpaired_labels = 0

        for split in self.config.splits:
            split_dir = self.config.dataset_path / split
            if not split_dir.exists():
                continue

            images_dir = split_dir / self.config.images_dir_name
            labels_dir = split_dir / self.config.labels_dir_name

            if not images_dir.exists():
                continue

            # 1. Discover all image files
            images: List[Path] = []
            for f in images_dir.iterdir():
                if f.is_file() and not f.name.endswith(":Zone.Identifier"):
                    if f.suffix.lower() in IMAGE_EXTENSIONS:
                        images.append(f)

            # Sort files naturally for consistent, deterministic numbering
            images.sort(key=lambda x: x.name)

            # Map labels by stem for fast lookup
            labels_by_stem: Dict[str, Path] = {}
            if labels_dir.exists():
                for f in labels_dir.iterdir():
                    if f.is_file() and not f.name.endswith(":Zone.Identifier"):
                        if f.suffix.lower() == LABEL_EXTENSION:
                            labels_by_stem[f.stem] = f

            split_idx = self.config.start_index if not self.config.global_counter else global_idx

            matched_label_stems = set()

            for img in images:
                current_id = split_idx
                split_idx += 1
                if self.config.global_counter:
                    global_idx += 1

                id_str = f"{current_id:0{self.config.digits}d}"
                # Target base name: <prefix><separator><split><separator><id>
                # e.g.: v5-train-0001
                new_base_name = (
                    f"{prefix}{self.config.separator}{split}{self.config.separator}{id_str}"
                )

                new_img_name = f"{new_base_name}{img.suffix}"
                new_img_path = images_dir / new_img_name

                # Look for matching label
                lbl_file = labels_by_stem.get(img.stem)
                new_lbl_path: Optional[Path] = None
                if lbl_file:
                    matched_label_stems.add(img.stem)
                    new_lbl_name = f"{new_base_name}{lbl_file.suffix}"
                    new_lbl_path = labels_dir / new_lbl_name
                    total_labels += 1
                else:
                    unpaired_images += 1

                total_images += 1

                # Auxiliary files (e.g. Zone.Identifier)
                aux_files: List[Tuple[Path, Path]] = []
                img_zone = img.parent / f"{img.name}:Zone.Identifier"
                if img_zone.exists():
                    if not self.config.clean_zone_identifiers:
                        aux_files.append((img_zone, img.parent / f"{new_img_name}:Zone.Identifier"))

                if lbl_file:
                    lbl_zone = lbl_file.parent / f"{lbl_file.name}:Zone.Identifier"
                    if lbl_zone.exists():
                        if not self.config.clean_zone_identifiers:
                            aux_files.append((lbl_zone, lbl_file.parent / f"{new_base_name}{lbl_file.suffix}:Zone.Identifier"))

                pairs.append(
                    RenamePair(
                        split=split,
                        original_stem=img.stem,
                        image_src=img,
                        image_dst=new_img_path,
                        label_src=lbl_file,
                        label_dst=new_lbl_path,
                        aux_files=aux_files,
                    )
                )

            # Check if any label files were left without an image
            if labels_dir.exists():
                for stem, lbl_path in labels_by_stem.items():
                    if stem not in matched_label_stems:
                        unpaired_labels += 1

        return RenamePlan(
            dataset_path=self.config.dataset_path,
            prefix=prefix,
            pairs=pairs,
            total_images=total_images,
            total_labels=total_labels,
            unpaired_images=unpaired_images,
            unpaired_labels=unpaired_labels,
        )

    def execute_plan(self, plan: RenamePlan) -> Dict[str, str]:
        """
        Executes the plan using a safe two-phase rename.
        Phase 1: Rename all source files to temporary unique UUID names.
        Phase 2: Rename from temporary names to final target names.
        This guarantees zero name collisions or accidental overwrites.

        Returns a dictionary mapping old_name -> new_name.
        """
        if self.config.dry_run:
            return {}

        # If cleaning zone identifiers, delete them first
        if self.config.clean_zone_identifiers:
            for pair in plan.pairs:
                img_zone = pair.image_src.parent / f"{pair.image_src.name}:Zone.Identifier"
                if img_zone.exists():
                    img_zone.unlink()
                if pair.label_src:
                    lbl_zone = pair.label_src.parent / f"{pair.label_src.name}:Zone.Identifier"
                    if lbl_zone.exists():
                        lbl_zone.unlink()

        rename_map: Dict[str, str] = {}

        # List of operations: (src_path, temp_path, final_path)
        operations: List[Tuple[Path, Path, Path]] = []

        for pair in plan.pairs:
            session_id = uuid.uuid4().hex[:8]

            # 1. Image
            img_temp = pair.image_src.parent / f".tmp_rename_{session_id}_{pair.image_src.name}"
            operations.append((pair.image_src, img_temp, pair.image_dst))
            rename_map[pair.image_src.name] = pair.image_dst.name

            # 2. Label
            if pair.label_src and pair.label_dst:
                lbl_temp = pair.label_src.parent / f".tmp_rename_{session_id}_{pair.label_src.name}"
                operations.append((pair.label_src, lbl_temp, pair.label_dst))
                rename_map[pair.label_src.name] = pair.label_dst.name

            # 3. Aux files (if not cleaned)
            for src_aux, dst_aux in pair.aux_files:
                aux_temp = src_aux.parent / f".tmp_rename_{session_id}_{src_aux.name}"
                operations.append((src_aux, aux_temp, dst_aux))

        # --- PHASE 1: Move to temporary filenames ---
        completed_phase1: List[Tuple[Path, Path, Path]] = []
        try:
            for src, temp, final in operations:
                if src.exists():
                    os.replace(src, temp)
                    completed_phase1.append((src, temp, final))
        except Exception as exc:
            # Rollback phase 1
            print(
                TerminalColor.colorize(
                    f"Error during rename phase 1: {exc}. Rolling back...",
                    TerminalColor.FAIL,
                ),
                file=sys.stderr,
            )
            for src, temp, _ in reversed(completed_phase1):
                if temp.exists():
                    os.replace(temp, src)
            raise

        # --- PHASE 2: Move from temporary filenames to final filenames ---
        completed_phase2: List[Tuple[Path, Path, Path]] = []
        try:
            for _, temp, final in operations:
                if temp.exists():
                    os.replace(temp, final)
                    completed_phase2.append((_, temp, final))
        except Exception as exc:
            print(
                TerminalColor.colorize(
                    f"Error during rename phase 2: {exc}. Emergency state!",
                    TerminalColor.FAIL,
                ),
                file=sys.stderr,
            )
            raise

        # Optionally save audit mapping file
        if self.config.save_mapping:
            mapping_file = self.config.dataset_path / "rename_mapping.json"
            try:
                with open(mapping_file, "w", encoding="utf-8") as f:
                    json.dump(
                        {
                            "dataset": str(self.config.dataset_path.name),
                            "prefix": plan.prefix,
                            "separator": self.config.separator,
                            "total_images": plan.total_images,
                            "total_labels": plan.total_labels,
                            "mappings": rename_map,
                        },
                        f,
                        indent=2,
                    )
            except Exception as e:
                print(f"Warning: Could not save rename_mapping.json: {e}")

        return rename_map


def format_preview(plan: RenamePlan, sample_count: int = 5) -> str:
    """Formats a visual preview of the planned renaming operations."""
    lines = []
    lines.append("\n" + "=" * 70)
    lines.append(f" {TerminalColor.colorize('DATASET RENAMING PLAN PREVIEW', TerminalColor.BOLD)} ")
    lines.append("=" * 70)
    lines.append(f" Dataset Path   : {plan.dataset_path}")
    lines.append(f" Prefix Applied : {TerminalColor.colorize(plan.prefix, TerminalColor.OKCYAN)}")
    lines.append(f" Total Images   : {TerminalColor.colorize(str(plan.total_images), TerminalColor.OKGREEN)}")
    lines.append(f" Total Labels   : {TerminalColor.colorize(str(plan.total_labels), TerminalColor.OKGREEN)}")
    if plan.unpaired_images > 0:
        lines.append(
            TerminalColor.colorize(
                f" Images without label : {plan.unpaired_images} (will still be renamed)",
                TerminalColor.WARNING,
            )
        )
    if plan.unpaired_labels > 0:
        lines.append(
            TerminalColor.colorize(
                f" Labels without image : {plan.unpaired_labels} (will be skipped)",
                TerminalColor.WARNING,
            )
        )
    lines.append("-" * 70)
    lines.append(" Sample Mappings (first few items per split):")

    shown_per_split: Dict[str, int] = {}
    for p in plan.pairs:
        count = shown_per_split.get(p.split, 0)
        if count < sample_count:
            img_rel_src = f"{p.split}/images/{p.image_src.name}"
            img_rel_dst = f"{p.split}/images/{p.image_dst.name}"
            lines.append(f"   Image: {img_rel_src} -> {TerminalColor.colorize(img_rel_dst, TerminalColor.OKCYAN)}")

            if p.label_src and p.label_dst:
                lbl_rel_src = f"{p.split}/labels/{p.label_src.name}"
                lbl_rel_dst = f"{p.split}/labels/{p.label_dst.name}"
                lines.append(f"   Label: {lbl_rel_src} -> {TerminalColor.colorize(lbl_rel_dst, TerminalColor.OKCYAN)}")
            else:
                lines.append(f"   Label: [No matching label file found]")
            shown_per_split[p.split] = count + 1

    lines.append("=" * 70)
    return "\n".join(lines)


def build_arg_parser() -> argparse.ArgumentParser:
    """Builds CLI argument parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Rename dataset images and labels across splits (train/valid/test) to: "
            "<prefix><separator><split><separator><0001>"
        )
    )
    parser.add_argument(
        "--dataset", "-d",
        type=str,
        required=False,
        help="Name or directory path of the dataset to rename.",
    )
    parser.add_argument(
        "--prefix", "-p",
        type=str,
        default=None,
        help="Prefix string (e.g. 'v5', 'aerial'). Defaults to dataset folder name.",
    )
    parser.add_argument(
        "--dataset-dir",
        type=str,
        default=None,
        help="Base directory containing datasets (default: auto-detected experiments/dataset).",
    )
    parser.add_argument(
        "--separator",
        type=str,
        default="-",
        help="Separator string between prefix, split, and id (default: '-').",
    )
    parser.add_argument(
        "--digits",
        type=int,
        default=4,
        help="Number of digits for zero-padding (default: 4, e.g. 0001).",
    )
    parser.add_argument(
        "--start-index",
        type=int,
        default=1,
        help="Starting integer index for numbering (default: 1).",
    )
    parser.add_argument(
        "--global-counter",
        action="store_true",
        help="Keep a continuous incremental counter across all splits instead of resetting per split.",
    )
    parser.add_argument(
        "--splits",
        nargs="+",
        default=DEFAULT_SPLITS,
        help="Dataset splits to process (default: train valid test).",
    )
    parser.add_argument(
        "--clean-zone-identifiers",
        action="store_true",
        help="Automatically remove Windows Zone.Identifier metadata files.",
    )
    parser.add_argument(
        "--no-mapping-file",
        action="store_true",
        help="Do not write rename_mapping.json inside dataset directory.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Display the renaming plan without modifying any files.",
    )
    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Execute renaming immediately without interactive confirmation prompt.",
    )
    return parser


def main() -> int:
    """Main CLI execution."""
    parser = build_arg_parser()
    args = parser.parse_args()

    base_dir = (
        Path(args.dataset_dir).resolve()
        if args.dataset_dir
        else DatasetRenamer.default_dataset_dir()
    )

    # If dataset not provided via flag, list available datasets and prompt
    dataset_input = args.dataset
    if not dataset_input:
        available = []
        if base_dir.exists():
            available = [d.name for d in sorted(base_dir.iterdir()) if d.is_dir() and not d.name.startswith(".")]

        print(f"\nDatasets detected in '{base_dir}':")
        for idx, ds_name in enumerate(available, 1):
            print(f"  [{idx}] {ds_name}")

        if not available:
            print("No datasets found in dataset directory.", file=sys.stderr)
            return 1

        choice = input(f"\nEnter dataset name or number [1-{len(available)}]: ").strip()
        if not choice:
            print("Cancelled.")
            return 1

        if choice.isdigit() and 1 <= int(choice) <= len(available):
            dataset_input = available[int(choice) - 1]
        else:
            dataset_input = choice

    # Resolve dataset path
    config = DatasetRenamerConfig(
        dataset_path=Path(dataset_input),
        dataset_base_dir=base_dir,
        prefix=args.prefix,
        separator=args.separator,
        splits=tuple(args.splits),
        digits=args.digits,
        start_index=args.start_index,
        global_counter=args.global_counter,
        dry_run=args.dry_run,
        save_mapping=not args.no_mapping_file,
        clean_zone_identifiers=args.clean_zone_identifiers,
    )

    renamer = DatasetRenamer(config)
    resolved_path = renamer.resolve_dataset_path(config.dataset_path)

    if not resolved_path.exists():
        print(TerminalColor.colorize(f"Error: Dataset path does not exist: {resolved_path}", TerminalColor.FAIL), file=sys.stderr)
        return 1

    config.dataset_path = resolved_path

    # If prefix is not specified, let user confirm or change it
    if not args.prefix and not args.yes and not args.dry_run:
        default_pref = config.dataset_path.name
        pref_prompt = input(f"Enter prefix name [{default_pref}]: ").strip()
        if pref_prompt:
            config.prefix = pref_prompt

    # Build renaming plan
    plan = renamer.build_plan()

    if plan.total_images == 0:
        print(TerminalColor.colorize("No images found in the specified splits.", TerminalColor.WARNING))
        return 0

    # Display preview
    print(format_preview(plan, sample_count=4))

    if args.dry_run:
        print(TerminalColor.colorize("\n[DRY-RUN] Simulation finished. No files were modified.", TerminalColor.OKGREEN))
        return 0

    # Interactive confirmation unless -y is specified
    if not args.yes:
        confirm = input(
            f"\nAre you sure you want to rename {plan.total_images} images and {plan.total_labels} labels? (y/N): "
        ).strip().lower()
        if confirm not in ("y", "yes"):
            print("Operation aborted by user.")
            return 0

    # Execute
    print(f"\nExecuting safe two-phase rename on '{config.dataset_path.name}'...")
    try:
        rename_map = renamer.execute_plan(plan)
        print(
            TerminalColor.colorize(
                f"[SUCCESS] Renamed {len(rename_map)} files successfully!",
                TerminalColor.OKGREEN,
            )
        )
        if config.save_mapping:
            print(f"Audit mapping saved to: {config.dataset_path / 'rename_mapping.json'}")
        return 0
    except Exception as exc:
        print(
            TerminalColor.colorize(f"[FAILED] Error during renaming: {exc}", TerminalColor.FAIL),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
