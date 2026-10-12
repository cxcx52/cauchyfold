"""Recompute the saved comparison from compiler metadata."""
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parent
subprocess.run([sys.executable,str(ROOT/'carrier/calculate.py')],check=True)
