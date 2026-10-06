import os
import sys

# Ensure root directory is in sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from rootx.app import main

if __name__ == "__main__":
    main()
