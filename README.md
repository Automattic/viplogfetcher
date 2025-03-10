# VIP Log Fetch

A tool for fetching and processing WordPress VIP log files from S3.

## Installation

```bash
pip install -e .
```

## Development Setup

```bash
# Create and activate virtual environment
python3 -m venv .
source bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -r requirements-dev.txt

# Install package in editable mode
pip install -e .
```

## Running Tests

```bash
pytest
```

## Usage

```bash
# Basic usage
viplogfetcher my-bucket prod 2023-11-01T00:00:00Z 2023-11-02T00:00:00Z

# With AWS profile
viplogfetcher my-bucket prod 2023-11-01T00:00:00Z 2023-11-02T00:00:00Z --profile prod-readonly

# Output to file
viplogfetcher my-bucket prod 2023-11-01T00:00:00Z 2023-11-02T00:00:00Z -o output.log
```

## Features

- Fetches gzipped JSON log files from S3
- Filters logs by timestamp
- Handles AWS credentials and profiles
- Progress bars for long operations
- Pagination support for large sets of files

## License

GPLv3
