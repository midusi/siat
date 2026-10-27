#!/usr/bin/env python3
"""
Unit tests for Dataset Sample Transfer Tool (transfer_samples.py)
"""

import shutil
import tempfile
import unittest
import sys
from pathlib import Path

# Add script directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from transfer_samples import (
    DatasetConfig,
    DatasetTransferManager,
    TransferItem,
)


class TestDatasetTransferManager(unittest.TestCase):
    def setUp(self):
        # Create temporary directory structure mimicking Roboflow datasets
        self.test_dir = tempfile.mkdtemp()
        self.base_dir = Path(self.test_dir)

        # Source dataset: "source_ds"
        self.src_dir = self.base_dir / "source_ds"
        # Dest dataset: "dest_ds"
        self.dst_dir = self.base_dir / "dest_ds"

        for split in ("train", "valid", "test"):
            (self.src_dir / split / "images").mkdir(parents=True, exist_ok=True)
            (self.src_dir / split / "labels").mkdir(parents=True, exist_ok=True)

        # Populate sample files in source
        # train: sample1.jpg + sample1.txt, sample2.png + sample2.txt
        (self.src_dir / "train" / "images" / "sample1.jpg").write_text("img1")
        (self.src_dir / "train" / "labels" / "sample1.txt").write_text("0 0.5 0.5 0.2 0.2")

        (self.src_dir / "train" / "images" / "sample2.png").write_text("img2")
        (self.src_dir / "train" / "labels" / "sample2.txt").write_text("1 0.4 0.4 0.1 0.1")

        # valid: val_sample.jpg (no label - background/negative)
        (self.src_dir / "valid" / "images" / "val_sample.jpg").write_text("val_img")

        # Config
        self.config = DatasetConfig(
            source_dataset=self.src_dir,
            dest_dataset=self.dst_dir,
            dataset_base_dir=self.base_dir,
            action="copy",
            overwrite=False,
            dry_run=False,
        )
        self.mgr = DatasetTransferManager(self.config)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_find_sample_exact_name(self):
        items = self.mgr.find_samples("sample1.jpg")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].stem, "sample1")
        self.assertEqual(items[0].source_split, "train")
        self.assertIsNotNone(items[0].label_path)

    def test_find_sample_stem_without_extension(self):
        items = self.mgr.find_samples("sample2")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].image_path.name, "sample2.png")
        self.assertEqual(items[0].label_path.name, "sample2.txt")

    def test_find_sample_wildcard(self):
        items = self.mgr.find_samples("sample*")
        self.assertEqual(len(items), 2)
        stems = {i.stem for i in items}
        self.assertEqual(stems, {"sample1", "sample2"})

    def test_sample_without_label(self):
        items = self.mgr.find_samples("val_sample.jpg")
        self.assertEqual(len(items), 1)
        self.assertIsNone(items[0].label_path)
        self.assertEqual(items[0].source_split, "valid")

    def test_parse_input_line_various_formats(self):
        # Comma separated
        tokens = self.mgr.parse_input_line("img1.jpg, img2.jpg, img3.jpg")
        self.assertEqual(tokens, ["img1.jpg", "img2.jpg", "img3.jpg"])

        # Space separated
        tokens = self.mgr.parse_input_line("img1.jpg img2.jpg img3.jpg")
        self.assertEqual(tokens, ["img1.jpg", "img2.jpg", "img3.jpg"])

        # Mixed / without extension
        tokens = self.mgr.parse_input_line("sample1, sample2")
        self.assertEqual(tokens, ["sample1", "sample2"])

    def test_transfer_batch_copy(self):
        results = self.mgr.transfer_batch(["sample1.jpg", "sample2"])
        self.assertEqual(len(results), 2)
        self.assertTrue(all(r.success for r in results))

        # Check destination files exist
        dst_img1 = self.dst_dir / "train" / "images" / "sample1.jpg"
        dst_lbl1 = self.dst_dir / "train" / "labels" / "sample1.txt"
        self.assertTrue(dst_img1.exists())
        self.assertTrue(dst_lbl1.exists())
        self.assertEqual(dst_lbl1.read_text(), "0 0.5 0.5 0.2 0.2")

        # Source files should still exist after COPY
        src_img1 = self.src_dir / "train" / "images" / "sample1.jpg"
        self.assertTrue(src_img1.exists())

    def test_transfer_batch_move(self):
        self.config.action = "move"
        results = self.mgr.transfer_batch(["sample1.jpg"])
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].success)

        # Check destination exists
        dst_img1 = self.dst_dir / "train" / "images" / "sample1.jpg"
        dst_lbl1 = self.dst_dir / "train" / "labels" / "sample1.txt"
        self.assertTrue(dst_img1.exists())
        self.assertTrue(dst_lbl1.exists())

        # Source files should NOT exist after MOVE
        src_img1 = self.src_dir / "train" / "images" / "sample1.jpg"
        src_lbl1 = self.src_dir / "train" / "labels" / "sample1.txt"
        self.assertFalse(src_img1.exists())
        self.assertFalse(src_lbl1.exists())

    def test_target_split_override(self):
        # Transfer from valid into train
        self.config.target_split = "train"
        results = self.mgr.transfer_batch(["val_sample.jpg"])
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].success)

        dst_img = self.dst_dir / "train" / "images" / "val_sample.jpg"
        self.assertTrue(dst_img.exists())

    def test_nonexistent_file_handling(self):
        results = self.mgr.transfer_batch(["nonexistent_image_123.jpg"])
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].success)
        self.assertIn("No matching image found", results[0].message)

    def test_overwrite_protection(self):
        # First copy
        self.mgr.transfer_batch(["sample1.jpg"])
        # Second copy without overwrite should fail/skip
        self.config.overwrite = False
        results2 = self.mgr.transfer_batch(["sample1.jpg"])
        self.assertEqual(len(results2), 1)
        self.assertFalse(results2[0].success)
        self.assertIn("already exists", results2[0].message)

        # With overwrite should succeed
        self.config.overwrite = True
        results3 = self.mgr.transfer_batch(["sample1.jpg"])
        self.assertEqual(len(results3), 1)
        self.assertTrue(results3[0].success)


if __name__ == "__main__":
    unittest.main()
