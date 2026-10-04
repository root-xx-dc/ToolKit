#!/bin/bash
set -e

echo "=== Building ROOT//X Native Linux Executable ==="
pip install pyinstaller nuitka

# Build using PyInstaller standalone binary
pyinstaller --onefile \
  --name "rootx-toolkit" \
  --hidden-import "pypresence" \
  --hidden-import "psutil" \
  --hidden-import "colorama" \
  --hidden-import "cryptography" \
  --clean \
  main.py

echo "Build complete! Binary located at dist/rootx-toolkit"
