#!/usr/bin/env python3
import sys
from pathlib import Path

repository_src = Path(__file__).resolve().parents[3] / "src"
if repository_src.is_dir():
    sys.path.insert(0, str(repository_src))

from hermes_toolkit.cli import main

raise SystemExit(main(["--skill", "bug-hunter", *sys.argv[1:]]))
