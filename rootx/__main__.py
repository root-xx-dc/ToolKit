import os
import sys

# Ensure root directory is in sys.path
pkg_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(pkg_dir)

if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from rootx.app import main

if __name__ == "__main__":
    main()
