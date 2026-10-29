#!/usr/bin/env python3
"""Run after installing the repository with python -m pip install -e '.[dev]'."""
from hermes_toolkit.evaluation import main

if __name__ == "__main__":
    raise SystemExit(main())
