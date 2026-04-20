from setuptools import setup, find_packages

setup(
    name="veriflow",
    version="1.0.0",
    description="RTL verification and documentation framework for SemiCoLab IP tiles",
    author="Roman Lugo",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "veriflow": ["template/*.v"],
    },
    install_requires=[
        "pyyaml",
    ],
    entry_points={
        "console_scripts": [
            "veriflow=veriflow.cli:main",
        ],
    },
    python_requires=">=3.10",
)
