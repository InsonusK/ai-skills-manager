"""Tests for LinkUpdater adapter."""

import unittest
import tempfile
import shutil
from pathlib import Path

from ai_skills_manager.adapters.link_updater import LinkUpdater
from ai_skills_manager.discovery.base import SkillMapping


class TestLinkUpdater(unittest.TestCase):
    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.target = self.tmpdir / "target"
        self.target.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_no_links(self):
        md = self.target / "guide.md"
        md.write_text("# Guide\nNo links here.")

        updater = LinkUpdater([], {}, set())
        updater.adapt(md)

        content = md.read_text()
        self.assertEqual(content, "# Guide\nNo links here.")
        self.assertEqual(len(updater.fixes), 0)

    def test_external_link_unchanged(self):
        md = self.target / "guide.md"
        md.write_text("# Guide\nSee [example](https://example.com).")

        updater = LinkUpdater([], {}, set())
        updater.adapt(md)

        content = md.read_text()
        self.assertIn("https://example.com", content)
        self.assertEqual(len(updater.fixes), 0)

    def test_anchor_link_unchanged(self):
        md = self.target / "guide.md"
        md.write_text("# Guide\nSee [section](#section).")

        updater = LinkUpdater([], {}, set())
        updater.adapt(md)

        content = md.read_text()
        self.assertIn("#section", content)
        self.assertEqual(len(updater.fixes), 0)

    def test_absolute_link_unchanged(self):
        md = self.target / "guide.md"
        md.write_text("# Guide\nSee [root](/etc/passwd).")

        updater = LinkUpdater([], {}, set())
        updater.adapt(md)

        content = md.read_text()
        self.assertIn("/etc/passwd", content)
        self.assertEqual(len(updater.fixes), 0)

    def test_fix_managed_link(self):
        """Link to a file in source_to_target map gets updated."""
        # Setup source structure
        source_dir = self.tmpdir / "source"
        source_dir.mkdir()
        source_guide = source_dir / "guide.md"
        source_guide.write_text("# Guide\nSee [other](./other.md).")
        source_other = source_dir / "other.md"
        source_other.write_text("# Other")

        # Setup target structure (simulating copied files)
        target_guide = self.target / "guide" / "SKILL.md"
        target_guide.parent.mkdir()
        target_guide.write_text("# Guide\nSee [other](./other.md).")

        target_other = self.target / "other" / "SKILL.md"
        target_other.parent.mkdir()
        target_other.write_text("# Other")

        # Create mappings
        guide_mapping = SkillMapping(source_guide, target_guide.parent, "guide", True)
        other_mapping = SkillMapping(source_other, target_other.parent, "other", True)

        # Build source_to_target map
        source_to_target = {
            source_guide: target_guide,
            source_other: target_other,
        }

        updater = LinkUpdater([guide_mapping, other_mapping], source_to_target, {source_guide, source_other})
        updater.adapt(target_guide)

        content = target_guide.read_text()
        self.assertNotIn("./other.md", content)
        self.assertIn("../other/SKILL.md", content)

        # Check fix recorded
        fixes = [f for f in updater.fixes if f["status"] == "fixed"]
        self.assertEqual(len(fixes), 1)
        self.assertEqual(fixes[0]["old"], "./other.md")

    def test_dry_run_no_changes(self):
        """Dry run should not modify files but record fixes."""
        # Setup source
        source_dir = self.tmpdir / "source"
        source_dir.mkdir()
        source_guide = source_dir / "guide.md"
        source_guide.write_text("# Guide\nSee [other](./other.md).")
        source_other = source_dir / "other.md"
        source_other.write_text("# Other")

        # Setup target
        target_guide = self.target / "guide" / "SKILL.md"
        target_guide.parent.mkdir()
        target_guide.write_text("# Guide\nSee [other](./other.md).")

        target_other = self.target / "other" / "SKILL.md"
        target_other.parent.mkdir()
        target_other.write_text("# Other")

        guide_mapping = SkillMapping(source_guide, target_guide.parent, "guide", True)
        other_mapping = SkillMapping(source_other, target_other.parent, "other", True)

        source_to_target = {source_guide: target_guide, source_other: target_other}

        updater = LinkUpdater(
            [guide_mapping, other_mapping],
            source_to_target,
            {source_guide, source_other},
            dry_run=True
        )
        updater.adapt(target_guide)

        # File should be unchanged
        content = target_guide.read_text()
        self.assertIn("./other.md", content)

        # But fix should be recorded
        self.assertEqual(len(updater.fixes), 1)
        self.assertEqual(updater.fixes[0]["status"], "fixed")

    def test_broken_link(self):
        """Link to non-existent file is marked broken."""
        source_dir = self.tmpdir / "source"
        source_dir.mkdir()
        source_guide = source_dir / "guide.md"
        source_guide.write_text("# Guide\nSee [missing](./missing.md).")

        target_guide = self.target / "guide" / "SKILL.md"
        target_guide.parent.mkdir()
        target_guide.write_text("# Guide\nSee [missing](./missing.md).")

        guide_mapping = SkillMapping(source_guide, target_guide.parent, "guide", True)

        updater = LinkUpdater([guide_mapping], {}, {source_guide})
        updater.adapt(target_guide)

        # Link stays as-is
        content = target_guide.read_text()
        self.assertIn("./missing.md", content)

        # But recorded as broken
        broken = [f for f in updater.fixes if f["status"] == "broken"]
        self.assertEqual(len(broken), 1)

    def test_external_existing_file(self):
        """Link to existing file outside sources is external."""
        source_dir = self.tmpdir / "source"
        source_dir.mkdir()
        source_guide = source_dir / "guide.md"
        source_guide.write_text("# Guide\nSee [ext](./external.md).")

        # External file exists in source dir but not in our map
        external = source_dir / "external.md"
        external.write_text("# External")

        target_guide = self.target / "guide" / "SKILL.md"
        target_guide.parent.mkdir()
        target_guide.write_text("# Guide\nSee [ext](./external.md).")

        guide_mapping = SkillMapping(source_guide, target_guide.parent, "guide", True)

        updater = LinkUpdater([guide_mapping], {}, {source_guide})
        updater.adapt(target_guide)

        # Should be recorded as external (file exists but not in source_to_target)
        ext = [f for f in updater.fixes if f["status"] == "external"]
        self.assertEqual(len(ext), 1)

    def test_adapt_all_recursive(self):
        """adapt_all processes all .md files recursively."""
        sub = self.target / "sub"
        sub.mkdir()

        md1 = self.target / "a.md"
        md1.write_text("# A")

        md2 = sub / "b.md"
        md2.write_text("# B")

        updater = LinkUpdater([], {}, set())
        updater.adapt_all(self.target)

        # Should process both files
        self.assertEqual(len(updater.fixes), 0)  # No links to fix

    def test_image_link(self):
        """Image links should also be processed."""
        source_dir = self.tmpdir / "source"
        source_dir.mkdir()
        source_guide = source_dir / "guide.md"
        source_guide.write_text("# Guide\n![img](./img.png)")
        source_img = source_dir / "img.png"
        source_img.write_text("png")

        target_guide = self.target / "guide" / "SKILL.md"
        target_guide.parent.mkdir()
        target_guide.write_text("# Guide\n![img](./img.png)")

        target_img = self.target / "img.png"
        target_img.write_text("png")

        guide_mapping = SkillMapping(source_guide, target_guide.parent, "guide", True)

        source_to_target = {source_guide: target_guide, source_img: target_img}

        updater = LinkUpdater([guide_mapping], source_to_target, {source_guide, source_img})
        updater.adapt(target_guide)

        content = target_guide.read_text()
        # Check that the old relative link is gone and new one is present
        # Use regex-like check to ensure it's a proper link, not substring
        self.assertNotIn("](./img.png)", content)
        self.assertIn("](../img.png)", content)
        # Ensure image marker is preserved
        self.assertIn("![img](", content)


if __name__ == "__main__":
    unittest.main()
