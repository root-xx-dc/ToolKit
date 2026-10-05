from setuptools import setup, find_packages

setup(
    name="rootx",
    version="2.4.0",
    description="ROOT//X Advanced System & Network Toolkit",
    author="11wikkss",
    packages=find_packages(),
    py_modules=["main"],
    include_package_data=True,
    install_requires=[
        "requests>=2.31.0",
        "colorama>=0.4.6",
        "psutil>=5.9.0",
        "cryptography>=41.0.0",
        "pypresence>=4.3.0",
    ],
    entry_points={
        "console_scripts": [
            "rootx=rootx.main:main",
            "rootx-toolkit=rootx.main:main",
        ],
    },
    python_requires=">=3.10",
)
