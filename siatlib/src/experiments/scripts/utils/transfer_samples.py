#!/usr/bin/env python3
"""
Dataset Sample Transfer Tool for Roboflow / YOLO Datasets.

Allows selective copying or moving of sample images and their corresponding
label (.txt) files between datasets with train/valid/test splits.
Supports single-file or batch inputs, wildcard patterns, and interactive/CLI usage.
"""

from __future__ import annotations

import argparse
import glob
import os
import re
import shlex
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Sequence, Tuple


# Common image extensions supported
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}
LABEL_EXTENSION = ".txt"
DEFAULT_SPLITS = ("train", "valid", "test")


class TerminalColor:
    """ANSI color codes for terminal formatting."""
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"

    @classmethod
    def colorize(cls, text: str, color: str, enabled: bool = True) -> str:
        if not enabled or not sys.stdout.isatty():
            return text
        return f"{color}{text}{cls.ENDC}"


@dataclass
class DatasetConfig:
    """Configuration for dataset transfer operations."""
    source_dataset: Path
    dest_dataset: Path
    dataset_base_dir: Optional[Path] = None
    splits: Tuple[str, ...] = DEFAULT_SPLITS
    images_dir_name: str = "images"
    labels_dir_name: str = "labels"
    target_split: Optional[str] = None  # None means preserve original split
    action: str = "copy"  # 'copy' or 'move'
    overwrite: bool = False
    dry_run: bool = False
    include_zone_identifiers: bool = False

    def validate(self) -> List[str]:
        """Validate paths and configuration, returning any error messages."""
        errors = []
        if not self.source_dataset.exists():
            errors.append(f"Source dataset directory does not exist: {self.source_dataset}")
        if self.action not in ("copy", "move"):
            errors.append(f"Invalid action '{self.action}'. Must be 'copy' or 'move'.")
        if self.target_split and self.target_split not in self.splits:
            errors.append(
                f"Target split '{self.target_split}' is not in configured splits: {self.splits}"
            )
        return errors


@dataclass
class TransferItem:
    """Represents a discovered sample ready for transfer."""
    stem: str
    image_path: Path
    label_path: Optional[Path]
    source_split: str
    aux_files: List[Path] = field(default_factory=list)


@dataclass
class TransferResult:
    """Result of an individual transfer operation."""
    item: TransferItem
    target_split: str
    image_dest: Path
    label_dest: Optional[Path]
    success: bool
    action: str
    message: str = ""


class DatasetTransferManager:
    """
    Modular manager to locate and transfer images and label files
    between Roboflow / YOLO formatted datasets.
    """

    def __init__(self, config: DatasetConfig):
        self.config = config

    @staticmethod
    def default_dataset_dir() -> Path:
        """
        Locates the default datasets directory by checking:
        1. experiments/dataset relative to this script
        2. current working directory ./experiments/dataset
        3. current working directory ./dataset
        """
        script_dir = Path(__file__).resolve().parent
        candidates = [
            script_dir.parent.parent / "dataset",          # .../experiments/dataset (from utils/)
            script_dir.parent / "dataset",                 # .../experiments/dataset (if in scripts/)
            Path.cwd() / "experiments" / "dataset",        # run from root
            Path.cwd() / "dataset",                        # run from experiments dir
            Path.cwd(),
        ]
        for candidate in candidates:
            if candidate.exists() and candidate.is_dir():
                return candidate.resolve()
        return (script_dir.parent.parent / "dataset").resolve()

    def resolve_dataset_path(self, path_or_name: Path | str) -> Path:
        """
        Resolves a dataset name or path.
        If given a simple folder name, checks inside dataset_base_dir.
        """
        p = Path(path_or_name)
        if p.is_absolute() and p.exists():
            return p.resolve()

        if self.config.dataset_base_dir:
            base_p = self.config.dataset_base_dir / p
            if base_p.exists():
                return base_p.resolve()

        cwd_p = Path.cwd() / p
        if cwd_p.exists():
            return cwd_p.resolve()

        # If base dir exists, default to placing it there
        if self.config.dataset_base_dir:
            return (self.config.dataset_base_dir / p).resolve()
        return cwd_p.resolve()

    def get_available_datasets(self) -> List[str]:
        """Lists available dataset folders in dataset_base_dir."""
        base = self.config.dataset_base_dir
        if not base or not base.exists():
            return []
        datasets = []
        for item in sorted(base.iterdir()):
            if item.is_dir() and not item.name.startswith("."):
                datasets.append(item.name)
        return datasets

    def find_samples(
        self,
        query: str,
        search_split: Optional[str] = None
    ) -> List[TransferItem]:
        """
        Finds sample items matching a query (filename, stem, or glob pattern).
        Searches across splits or within a specified split.
        """
        query = query.strip()
        if not query:
            return []

        # Remove quotes if present
        if (query.startswith('"') and query.endswith('"')) or (
            query.startswith("'") and query.endswith("'")
        ):
            query = query[1:-1].strip()

        # Check if user passed full relative path e.g. train/images/abc.jpg
        p_query = Path(query)
        if len(p_query.parts) > 1:
            query = p_query.name

        splits_to_search = (
            [search_split] if search_split else list(self.config.splits)
        )
        results: List[TransferItem] = []
        seen_images = set()

        for split in splits_to_search:
            images_dir = self.config.source_dataset / split / self.config.images_dir_name
            labels_dir = self.config.source_dataset / split / self.config.labels_dir_name

            if not images_dir.exists():
                continue

            # Determine matching candidate image files
            matched_images: List[Path] = []

            # 1. Glob / wildcard matching
            if any(char in query for char in ["*", "?", "[", "]"]):
                for img_candidate in images_dir.glob(query):
                    if img_candidate.is_file() and not img_candidate.name.endswith(":Zone.Identifier"):
                        matched_images.append(img_candidate)
            else:
                # 2. Exact match with extension
                exact_path = images_dir / query
                if exact_path.is_file() and not exact_path.name.endswith(":Zone.Identifier"):
                    matched_images.append(exact_path)
                else:
                    # 3. Match without extension (try all known image extensions)
                    query_stem = Path(query).stem if Path(query).suffix.lower() in IMAGE_EXTENSIONS else query
                    for ext in IMAGE_EXTENSIONS:
                        cand = images_dir / f"{query_stem}{ext}"
                        if cand.is_file():
                            matched_images.append(cand)
                    # 4. Also scan files whose stem equals query_stem
                    if not matched_images:
                        for item in images_dir.iterdir():
                            if item.is_file() and not item.name.endswith(":Zone.Identifier"):
                                if item.stem == query_stem or item.name == query:
                                    matched_images.append(item)

            for img_path in matched_images:
                if img_path in seen_images:
                    continue
                seen_images.add(img_path)

                stem = img_path.stem
                label_candidate = labels_dir / f"{stem}{LABEL_EXTENSION}"
                label_path = label_candidate if label_candidate.is_file() else None

                # Search auxiliary files (like Zone.Identifier)
                aux_files: List[Path] = []
                if self.config.include_zone_identifiers:
                    img_zone = img_path.parent / f"{img_path.name}:Zone.Identifier"
                    if img_zone.exists():
                        aux_files.append(img_zone)
                    if label_path:
                        lbl_zone = label_path.parent / f"{label_path.name}:Zone.Identifier"
                        if lbl_zone.exists():
                            aux_files.append(lbl_zone)

                results.append(
                    TransferItem(
                        stem=stem,
                        image_path=img_path,
                        label_path=label_path,
                        source_split=split,
                        aux_files=aux_files,
                    )
                )

        return results

    def transfer_item(
        self,
        item: TransferItem,
        target_split_override: Optional[str] = None
    ) -> TransferResult:
        """
        Executes copy or move for an individual sample and its label.
        """
        target_split = target_split_override or self.config.target_split or item.source_split

        dest_img_dir = (
            self.config.dest_dataset
            / target_split
            / self.config.images_dir_name
        )
        dest_lbl_dir = (
            self.config.dest_dataset
            / target_split
            / self.config.labels_dir_name
        )

        dest_img_path = dest_img_dir / item.image_path.name
        dest_lbl_path = (
            (dest_lbl_dir / item.label_path.name) if item.label_path else None
        )

        # Check existing destination files
        if not self.config.overwrite:
            if dest_img_path.exists():
                return TransferResult(
                    item=item,
                    target_split=target_split,
                    image_dest=dest_img_path,
                    label_dest=dest_lbl_path,
                    success=False,
                    action=self.config.action,
                    message=f"Destination image already exists: {dest_img_path.name}",
                )
            if dest_lbl_path and dest_lbl_path.exists():
                return TransferResult(
                    item=item,
                    target_split=target_split,
                    image_dest=dest_img_path,
                    label_dest=dest_lbl_path,
                    success=False,
                    action=self.config.action,
                    message=f"Destination label already exists: {dest_lbl_path.name}",
                )

        if self.config.dry_run:
            msg = f"[DRY-RUN] Would {self.config.action} {item.image_path.name}"
            if item.label_path:
                msg += f" and {item.label_path.name}"
            msg += f" to {target_split}/"
            return TransferResult(
                item=item,
                target_split=target_split,
                image_dest=dest_img_path,
                label_dest=dest_lbl_path,
                success=True,
                action=self.config.action,
                message=msg,
            )

        # Create destination directories if they don't exist
        dest_img_dir.mkdir(parents=True, exist_ok=True)
        dest_lbl_dir.mkdir(parents=True, exist_ok=True)

        try:
            op = shutil.move if self.config.action == "move" else shutil.copy2

            # Transfer image
            op(str(item.image_path), str(dest_img_path))

            # Transfer label if present
            if item.label_path:
                op(str(item.label_path), str(dest_lbl_path))

            # Transfer aux files if configured
            if self.config.include_zone_identifiers:
                for aux in item.aux_files:
                    target_aux_dir = dest_img_dir if "images" in str(aux) else dest_lbl_dir
                    op(str(aux), str(target_aux_dir / aux.name))

            msg = f"{self.config.action.capitalize()}d image {item.image_path.name}"
            if item.label_path:
                msg += f" + label {item.label_path.name}"
            else:
                msg += " (warning: no label file found)"
            msg += f" -> {target_split}/"

            return TransferResult(
                item=item,
                target_split=target_split,
                image_dest=dest_img_path,
                label_dest=dest_lbl_path,
                success=True,
                action=self.config.action,
                message=msg,
            )
        except Exception as exc:
            return TransferResult(
                item=item,
                target_split=target_split,
                image_dest=dest_img_path,
                label_dest=dest_lbl_path,
                success=False,
                action=self.config.action,
                message=f"Error during {self.config.action}: {exc}",
            )

    @staticmethod
    def parse_input_line(raw_input: str) -> List[str]:
        """
        Parses a single user input containing one or multiple filenames/queries.
        Supports comma-separated, space-separated, and shell-quoted tokens.
        """
        raw_input = raw_input.strip()
        if not raw_input:
            return []

        # If comma-separated
        if "," in raw_input:
            tokens = [t.strip() for t in raw_input.split(",") if t.strip()]
            return tokens

        # Use shlex to handle spaces and quotes
        try:
            tokens = shlex.split(raw_input)
            if tokens:
                return tokens
        except ValueError:
            pass

        # Fallback to whitespace split
        return [t.strip() for t in raw_input.split() if t.strip()]

    def transfer_batch(
        self,
        queries: Sequence[str],
        target_split_override: Optional[str] = None
    ) -> List[TransferResult]:
        """
        Transfers all items found from a sequence of queries.
        """
        flattened_queries: List[str] = []
        for q in queries:
            tokens = self.parse_input_line(q)
            if tokens:
                flattened_queries.extend(tokens)
            else:
                flattened_queries.append(q)

        results: List[TransferResult] = []
        for query in flattened_queries:
            matched = self.find_samples(query)
            if not matched:
                results.append(
                    TransferResult(
                        item=TransferItem(
                            stem=query,
                            image_path=Path(query),
                            label_path=None,
                            source_split="unknown",
                        ),
                        target_split=target_split_override or self.config.target_split or "unknown",
                        image_dest=Path(),
                        label_dest=None,
                        success=False,
                        action=self.config.action,
                        message=f"No matching image found for query: '{query}'",
                    )
                )
                continue

            for item in matched:
                res = self.transfer_item(item, target_split_override=target_split_override)
                results.append(res)

        return results

    def list_samples(self, split: Optional[str] = None, limit: int = 20) -> List[str]:
        """Returns sample names from the source dataset for inspection."""
        splits = [split] if split else list(self.config.splits)
        samples = []
        for s in splits:
            img_dir = self.config.source_dataset / s / self.config.images_dir_name
            if img_dir.exists():
                for f in sorted(img_dir.iterdir()):
                    if f.is_file() and not f.name.endswith(":Zone.Identifier"):
                        if f.suffix.lower() in IMAGE_EXTENSIONS:
                            samples.append(f"[{s}] {f.name}")
                            if len(samples) >= limit:
                                return samples
        return samples


class InteractiveSession:
    """Provides a user-friendly CLI loop to configure and transfer files."""

    def __init__(self, manager: DatasetTransferManager):
        self.mgr = manager
        self.config = manager.config

    def print_status(self) -> None:
        """Prints current configuration summary."""
        print("\n" + "=" * 65)
        print(f" {TerminalColor.colorize('DATASET SAMPLE TRANSFER TOOL', TerminalColor.BOLD)} ")
        print("=" * 65)
        print(f" Source Dataset : {TerminalColor.colorize(str(self.config.source_dataset), TerminalColor.OKCYAN)}")
        print(f" Dest Dataset   : {TerminalColor.colorize(str(self.config.dest_dataset), TerminalColor.OKCYAN)}")
        print(f" Action Mode    : {TerminalColor.colorize(self.config.action.upper(), TerminalColor.OKGREEN if self.config.action == 'copy' else TerminalColor.WARNING)}")
        target_split_label = self.config.target_split if self.config.target_split else "Auto (match source split)"
        print(f" Target Split   : {TerminalColor.colorize(target_split_label, TerminalColor.OKBLUE)}")
        print(f" Overwrite      : {self.config.overwrite} | Dry-run: {self.config.dry_run}")
        print("-" * 65)
        print(" Commands:")
        print("   :src <path/name>    Change source dataset")
        print("   :dst <path/name>    Change destination dataset")
        print("   :split <name|auto>  Set target split (train/valid/test/auto)")
        print("   :mode <copy|move>   Toggle between copy and move")
        print("   :list [split]       List available sample images in source")
        print("   :status             Show this configuration status")
        print("   :help               Show instructions")
        print("   :quit or q          Exit")
        print("=" * 65 + "\n")

    def run(self) -> None:
        """Main interactive loop."""
        self.print_status()

        # Check if source exists, if not guide the user
        while not self.config.source_dataset.exists():
            print(TerminalColor.colorize(f"Source dataset does not exist: {self.config.source_dataset}", TerminalColor.FAIL))
            available = self.mgr.get_available_datasets()
            if available:
                print(f"Available datasets in {self.config.dataset_base_dir}: {', '.join(available)}")
            new_src = input("Enter valid source dataset name or path: ").strip()
            if not new_src:
                return
            self.config.source_dataset = self.mgr.resolve_dataset_path(new_src)

        while True:
            try:
                prompt_text = (
                    f"[{TerminalColor.colorize(self.config.action.upper(), TerminalColor.BOLD)}] "
                    f"{self.config.source_dataset.name} -> {self.config.dest_dataset.name} > "
                )
                user_input = input(prompt_text).strip()
            except (KeyboardInterrupt, EOFError):
                print("\nExiting.")
                break

            if not user_input:
                continue

            # Command handling
            if user_input.lower() in (":quit", ":q", "exit", "quit", "q"):
                print("Goodbye!")
                break

            if user_input.startswith(":"):
                self.handle_command(user_input)
                continue

            # Process file inputs (supports single or multiple items)
            tokens = self.mgr.parse_input_line(user_input)
            if not tokens:
                continue

            print(f"\nProcessing {len(tokens)} input pattern(s)...")
            results = self.mgr.transfer_batch(tokens)

            # Display results
            success_count = sum(1 for r in results if r.success)
            fail_count = len(results) - success_count

            for r in results:
                if r.success:
                    print(TerminalColor.colorize(f" [OK] {r.message}", TerminalColor.OKGREEN))
                else:
                    print(TerminalColor.colorize(f" [FAILED] {r.message}", TerminalColor.FAIL))

            print(
                f"\nSummary: {TerminalColor.colorize(str(success_count) + ' succeeded', TerminalColor.OKGREEN)}, "
                f"{TerminalColor.colorize(str(fail_count) + ' failed/skipped', TerminalColor.WARNING if fail_count > 0 else TerminalColor.ENDC)}\n"
            )

    def handle_command(self, cmd_line: str) -> None:
        """Handles ':' interactive commands."""
        parts = cmd_line.split(maxsplit=1)
        cmd = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if cmd in (":src", ":source"):
            if not arg:
                print("Usage: :src <dataset_name_or_path>")
                return
            new_path = self.mgr.resolve_dataset_path(arg)
            if not new_path.exists():
                print(TerminalColor.colorize(f"Path does not exist: {new_path}", TerminalColor.FAIL))
                return
            self.config.source_dataset = new_path
            print(f"Source dataset updated to: {new_path}")

        elif cmd in (":dst", ":dest", ":destination"):
            if not arg:
                print("Usage: :dst <dataset_name_or_path>")
                return
            new_path = self.mgr.resolve_dataset_path(arg)
            self.config.dest_dataset = new_path
            print(f"Destination dataset updated to: {new_path}")

        elif cmd in (":mode", ":action"):
            if arg.lower() in ("copy", "move"):
                self.config.action = arg.lower()
                print(f"Action set to: {self.config.action.upper()}")
            else:
                print("Usage: :mode <copy|move>")

        elif cmd in (":split", ":target_split"):
            if not arg or arg.lower() in ("auto", "none"):
                self.config.target_split = None
                print("Target split set to: Auto (preserves original split)")
            elif arg.lower() in self.config.splits:
                self.config.target_split = arg.lower()
                print(f"Target split fixed to: {self.config.target_split}")
            else:
                print(f"Invalid split. Choose from: auto, {', '.join(self.config.splits)}")

        elif cmd in (":list", ":ls"):
            split_arg = arg.lower() if arg.lower() in self.config.splits else None
            samples = self.mgr.list_samples(split=split_arg, limit=30)
            print(f"\nAvailable samples in source ({len(samples)} shown):")
            for s in samples:
                print(f"  {s}")
            print()

        elif cmd in (":status", ":config", ":settings"):
            self.print_status()

        elif cmd in (":help", ":h"):
            print("\nHelp:")
            print("  - To transfer a single file: enter the image name or stem, e.g. `img_0` or `img_0.jpg`")
            print("  - To transfer multiple files in one input: separate by commas or spaces, e.g.:")
            print("      `img_0, img_1, img_2`  or  `img_0.jpg img_1.jpg img_2.jpg`")
            print("  - Wildcards are supported: `frame_000*` or `*.jpg`")
            print("  - Both image and matching `.txt` label file will be moved/copied to the correct folders.")
            print("  - Type :status to view paths, or :quit to exit.\n")
        else:
            print(f"Unknown command: '{cmd}'. Type :help for commands.")


def build_arg_parser() -> argparse.ArgumentParser:
    """Builds CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Selectively copy or move images and labels between Roboflow/YOLO datasets."
    )
    parser.add_argument(
        "--source", "-s",
        type=str,
        help="Source dataset name or directory path."
    )
    parser.add_argument(
        "--dest", "-d",
        type=str,
        help="Destination dataset name or directory path."
    )
    parser.add_argument(
        "--dataset-dir",
        type=str,
        default=None,
        help="Base directory containing datasets (default: auto-detected experiments/dataset)."
    )
    parser.add_argument(
        "--files", "-f",
        nargs="+",
        help="Image filenames or stems to transfer (in one input or multiple arguments)."
    )
    parser.add_argument(
        "--action", "-a",
        choices=["copy", "move"],
        default="copy",
        help="Action to perform: 'copy' (default) or 'move'."
    )
    parser.add_argument(
        "--target-split",
        type=str,
        choices=["train", "valid", "test"],
        default=None,
        help="Force target split (default: match source split)."
    )
    parser.add_argument(
        "--source-split",
        type=str,
        choices=["train", "valid", "test"],
        default=None,
        help="Restrict search to a specific source split."
    )
    parser.add_argument(
        "--images-dir",
        type=str,
        default="images",
        help="Folder name for images (default: 'images')."
    )
    parser.add_argument(
        "--labels-dir",
        type=str,
        default="labels",
        help="Folder name for labels (default: 'labels')."
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing files in destination."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate transfer without copying or moving files."
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Force interactive mode."
    )
    return parser


def main() -> int:
    """Main entry point."""
    parser = build_arg_parser()
    args = parser.parse_args()

    base_dir = (
        Path(args.dataset_dir).resolve()
        if args.dataset_dir
        else DatasetTransferManager.default_dataset_dir()
    )

    # If source / dest are not provided on CLI, try sensible defaults or prompt
    source_path = (
        base_dir / args.source if args.source and not Path(args.source).is_absolute()
        else Path(args.source).resolve() if args.source
        else None
    )

    dest_path = (
        base_dir / args.dest if args.dest and not Path(args.dest).is_absolute()
        else Path(args.dest).resolve() if args.dest
        else None
    )

    # If not provided, inspect base_dir to pick defaults for interactive mode
    if not source_path or not dest_path:
        available = []
        if base_dir.exists():
            available = [d.name for d in base_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]

        if not source_path:
            source_path = base_dir / (available[0] if available else "source_dataset")
        if not dest_path:
            dest_path = base_dir / (available[1] if len(available) > 1 else "target_dataset")

    config = DatasetConfig(
        source_dataset=source_path,
        dest_dataset=dest_path,
        dataset_base_dir=base_dir,
        splits=DEFAULT_SPLITS,
        images_dir_name=args.images_dir,
        labels_dir_name=args.labels_dir,
        target_split=args.target_split,
        action=args.action,
        overwrite=args.overwrite,
        dry_run=args.dry_run,
    )

    manager = DatasetTransferManager(config)

    # CLI batch execution mode if --files provided and not explicitly interactive
    if args.files and not args.interactive:
        errors = config.validate()
        if errors:
            for err in errors:
                print(TerminalColor.colorize(f"Error: {err}", TerminalColor.FAIL), file=sys.stderr)
            return 1

        print(f"Starting transfer from '{config.source_dataset}' to '{config.dest_dataset}'...")
        results = manager.transfer_batch(args.files, target_split_override=args.target_split)

        success = sum(1 for r in results if r.success)
        failed = len(results) - success

        for r in results:
            if r.success:
                print(TerminalColor.colorize(f"[OK] {r.message}", TerminalColor.OKGREEN))
            else:
                print(TerminalColor.colorize(f"[FAILED] {r.message}", TerminalColor.FAIL))

        print(f"\nDone: {success} succeeded, {failed} failed/skipped.")
        return 0 if failed == 0 else 1

    # Otherwise run interactive session
    session = InteractiveSession(manager)
    session.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
