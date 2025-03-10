import os
import json
import gzip
from datetime import datetime, timedelta
from typing import List, Tuple, Optional, Iterator, Dict, Any
from tqdm import tqdm

class LogFetcher:
    def __init__(self, s3_client, bucket_name: str, environment: str,
                 start_time: datetime, end_time: datetime, quiet: bool = False):
        self.s3_client = s3_client
        self.bucket_name = bucket_name
        self.environment = environment
        self.start_time = start_time
        self.end_time = end_time
        self.quiet = quiet

    def generate_prefixes(self) -> List[str]:
        """Generate list of prefixes to search based on time range"""
        prefixes = []
        current = self.start_time

        while current <= self.end_time:
            prefix = f"{self.environment}/{current.strftime('%Y/%m/%d/%H:%M')}"
            prefixes.append(prefix)
            current += timedelta(minutes=1)

        return prefixes

    def list_objects(self, prefix: str) -> List[dict]:
        """List all objects in S3 bucket with prefix, handling pagination"""
        objects = []
        paginator = self.s3_client.get_paginator('list_objects_v2')

        for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
            if 'Contents' in page:
                objects.extend(page['Contents'])

        return objects

    def process_logs(self, objects: List[dict], temp_dir: str) -> List[Tuple[datetime, str]]:
        """Process log files and extract relevant log entries"""
        all_logs = []
        progress_objects = self._get_progress_objects(objects)

        for obj in progress_objects:
            if not obj['Key'].endswith('.gz'):
                continue

            local_file_path = os.path.join(temp_dir, os.path.basename(obj['Key']))
            self.s3_client.download_file(self.bucket_name, obj['Key'], local_file_path)

            with gzip.open(local_file_path, 'rt') as f:
                for line in f:
                    try:
                        log_entry = json.loads(line)
                        timestamp = parse_iso8601(log_entry['timestamp_iso8601'])

                        if self._is_within_timerange(timestamp):
                            all_logs.append((timestamp, line.strip()))
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue  # Skip invalid entries

        return all_logs

    def _get_progress_objects(self, objects: List[Dict[str, Any]]) -> Any:
            """Wrap objects with progress bar if not quiet"""
            if not self.quiet:
                return tqdm(
                    objects,
                    desc='Downloading and processing files',
                    unit='file'
                )
            return iter(objects)

    def _is_within_timerange(self, timestamp: datetime) -> bool:
        """Check if timestamp is within the specified time range"""
        return self.start_time <= timestamp <= self.end_time

def parse_iso8601(timestamp_str: str) -> datetime:
    """Parse ISO8601 timestamp string to datetime object"""
    return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
