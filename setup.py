from setuptools import setup, find_packages

setup(
    name="murder-wizard",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "click>=8.0",
        "anthropic>=0.20.0",
        "python-dotenv>=1.0.0",
        "reportlab>=4.0.0",
    ],
    entry_points={
        "console_scripts": [
            "murder-wizard=murder_wizard.cli:main",
        ],
    },
    author="",
    description="RPG Maker-style murder mystery creation wizard",
    python_requires=">=3.9",
)
