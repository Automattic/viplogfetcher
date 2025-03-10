import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch, mock_open
import gzip
import json
from typing import Iterator, Dict, Any
from viplogfetcher.core import LogFetcher, parse_iso8601

@pytest.fixture
def mock_s3_client():
    return Mock()

@pytest.fixture
def sample_start_time():
    return datetime(2023, 1, 1, tzinfo=timezone.utc)

@pytest.fixture
def sample_end_time():
    return datetime(2023, 1, 1, 1, tzinfo=timezone.utc)

@pytest.fixture
def log_fetcher(mock_s3_client, sample_start_time, sample_end_time):
    return LogFetcher(
        s3_client=mock_s3_client,
        bucket_name="test-bucket",
        environment="prod",
        start_time=sample_start_time,
        end_time=sample_end_time,
        quiet=True
    )

class TestParseISO8601:
    def test_parse_utc(self):
        """Test parsing UTC timestamps"""
        result = parse_iso8601("2023-01-01T00:00:00Z")
        expected = datetime(2023, 1, 1, tzinfo=timezone.utc)
        assert result == expected

    def test_parse_with_offset(self):
        """Test parsing timestamps with offset"""
        result = parse_iso8601("2023-01-01T00:00:00+00:00")
        expected = datetime(2023, 1, 1, tzinfo=timezone.utc)
        assert result == expected

class TestLogFetcher:
    def test_generate_prefixes(self, log_fetcher):
        """Test prefix generation for time range"""
        prefixes = log_fetcher.generate_prefixes()
        assert len(prefixes) == 61  # 1 hour + 1 minute = 61 minutes
        assert prefixes[0] == "prod/2023/01/01/00:00"
        assert prefixes[-1] == "prod/2023/01/01/01:00"

    def test_list_objects(self, log_fetcher):
        """Test S3 object listing with pagination"""
        # Mock paginator response
        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [
            {'Contents': [{'Key': 'test1.gz'}]},
            {'Contents': [{'Key': 'test2.gz'}]}
        ]
        log_fetcher.s3_client.get_paginator.return_value = mock_paginator

        objects = log_fetcher.list_objects("test-prefix")

        assert len(objects) == 2
        assert objects[0]['Key'] == 'test1.gz'
        assert objects[1]['Key'] == 'test2.gz'

    def test_process_logs(self, log_fetcher, tmp_path):
        """Test log processing from gzipped files"""
        # Create sample log data
        log_entry = {
            'timestamp_iso8601': '2023-01-01T00:30:00Z',
            'message': 'test message'
        }
        log_line = json.dumps(log_entry) + '\n'

        # Mock S3 download
        log_fetcher.s3_client.download_file = Mock()

        # Mock gzip.open
        mock_gzip = mock_open(read_data=log_line)

        with patch('gzip.open', mock_gzip):
            objects = [{'Key': 'test.gz'}]
            logs = log_fetcher.process_logs(objects, str(tmp_path))

            assert len(logs) == 1
            timestamp, line = logs[0]
            assert timestamp == parse_iso8601('2023-01-01T00:30:00Z')
            assert 'test message' in line

    def test_process_logs_invalid_entry(self, log_fetcher, tmp_path):
        """Test handling of invalid log entries"""
        invalid_line = 'invalid json\n'

        # Mock S3 download
        log_fetcher.s3_client.download_file = Mock()

        # Mock gzip.open
        mock_gzip = mock_open(read_data=invalid_line)

        with patch('gzip.open', mock_gzip):
            objects = [{'Key': 'test.gz'}]
            logs = log_fetcher.process_logs(objects, str(tmp_path))

            assert len(logs) == 0

    def test_is_within_timerange(self, log_fetcher):
        """Test timestamp range checking"""
        # Test timestamp within range
        timestamp = datetime(2023, 1, 1, 0, 30, tzinfo=timezone.utc)
        assert log_fetcher._is_within_timerange(timestamp) is True

        # Test timestamp before range
        timestamp = datetime(2022, 12, 31, 23, 59, tzinfo=timezone.utc)
        assert log_fetcher._is_within_timerange(timestamp) is False

        # Test timestamp after range
        timestamp = datetime(2023, 1, 1, 1, 1, tzinfo=timezone.utc)
        assert log_fetcher._is_within_timerange(timestamp) is False
