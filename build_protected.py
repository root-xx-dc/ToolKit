"""
ROOT//X TOOLKIT — build_protected.py
Compiles _config.py and license.py into native binary modules (.pyd on Windows, .so on Linux) using Cython.
"""
import os
import sys
import shutil
from setuptools import setup
from Cython.Build import cythonize

def build():
    targets = [
        os.path.join("rootx", "_config.py"),
        os.path.join("rootx", "license.py"),
    ]
    for target in targets:
        if not os.path.exists(target):
            bak = target + ".bak"
            if os.path.exists(bak):
                shutil.copy(bak, target)
            else:
                print(f"[!] Target file not found: {target}")
                return

    print("[*] Compiling _config.py and license.py with Cython...")
    setup(
        ext_modules=cythonize(targets, compiler_directives={"language_level": "3"}),
        script_args=["build_ext", "--inplace"],
    )

    # Clean intermediate files
    for c_file in [os.path.join("rootx", "_config.c"), os.path.join("rootx", "license.c")]:
        if os.path.exists(c_file):
            os.remove(c_file)
    build_dir = os.path.join(os.path.dirname(__file__), "build")
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir, ignore_errors=True)

    print("[OK] Binary compilation complete! (.pyd on Windows, .so on Linux)")

if __name__ == "__main__":
    build()
