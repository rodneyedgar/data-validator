from __future__ import annotations

import tomllib
import unittest
from pathlib import Path

from cnds_validator import __version__


class VersionMetadataTests(unittest.TestCase):
    def test_module_version_matches_pyproject(self) -> None:
        pyproject_path = Path(__file__).resolve().parents[1] / "pyproject.toml"
        project_data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
        self.assertEqual(project_data["project"]["version"], __version__)


if __name__ == "__main__":
    unittest.main()
