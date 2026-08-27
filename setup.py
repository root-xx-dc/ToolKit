"""
ROOT//X TOOLKIT — setup.py

Obsługuje dwa tryby:
1. Normalna instalacja (pip install -e .):
   - Używa prekompilowanych .so/.pyd jeśli są dostępne
   - Fallback do .py jeśli brak skompilowanych plików
2. Budowanie plików chronionych (python build_protected.py build_ext --inplace):
   - Kompiluje license.py i _config.py przez Cython
"""
from setuptools import setup, find_packages

setup(
    name="rootx-toolkit",
    version="2.0.0",
    description="ROOT//X TOOLKIT",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "psutil>=5.9.0",
    ],
    entry_points={
        "console_scripts": [
            "rootx=rootx.cli:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    # Dołącz pliki .so i .pyd do dystrybucji
    package_data={
        "rootx": ["*.so", "*.pyd", "*.dll"],
    },
)
