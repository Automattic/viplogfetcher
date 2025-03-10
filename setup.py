from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="viplogfetcher",
    version="0.1.0",
    author="Joshua Coughlan",
    author_email="josh.coughlan@automattic.com",
    description="A tool for fetching and processing VIP edge logs files from S3",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Automattic/viplogfetcher",
    packages=find_packages(),
    license_files = ('LICENSE',),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Information Technology",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.7",
    install_requires=[
        "boto3>=1.20.0",
        "click>=7.0",
        "tqdm>=4.45.0",
    ],
    entry_points={
        "console_scripts": [
            "viplogfetcher=viplogfetcher.cli:main",
        ],
    },
)
