"""VIP Log Fetch - A tool for fetching and processing log files from S3"""

from .core import LogFetcher, parse_iso8601
from .cli import download_and_sort_logs

__version__ = '0.1.0'
__all__ = ['LogFetcher', 'parse_iso8601', 'download_and_sort_logs']
