from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

from setuptools import setup

setup(
    name="aura-g7-g8-finalizer",
    version="0.0.0",
    py_modules=["sitecustomize"],
)

if any(command in sys.argv for command in ("bdist_wheel", "install")):
    finalizer_path = Path(__file__).with_name("sitecustomize.py")
    spec = importlib.util.spec_from_file_location("aura_g7_g8_finalizer", finalizer_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load Aura G7-G8 finalizer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
