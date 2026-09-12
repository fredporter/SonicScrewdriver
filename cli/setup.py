"""Build the standalone Sonic Python package."""
from pathlib import Path
import runpy
from setuptools import setup, find_packages

root = Path(__file__).parent
version = runpy.run_path(str(root / "sonic" / "__init__.py"))["__version__"]
setup(
    name="sonic-screwdriver",
    version=version,
    description="Hardware revival and uDOS provisioning toolkit",
    packages=find_packages(include=["sonic", "sonic.*"]),
    package_data={"sonic": ["data/devices/*.yaml"]},
    install_requires=["click>=8.0", "pyyaml>=6.0", "pydantic>=2.0", "rich>=13.0"],
    extras_require={"dev": ["pytest>=7.0"]},
    entry_points={"console_scripts": ["sonic=sonic.cli:cli"]},
    python_requires=">=3.11",
)
