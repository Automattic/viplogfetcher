import pytest
import boto3
from moto import mock_aws
import gzip
import json
from datetime import datetime, timezone
from viplogfetcher.core import LogFetcher, parse_iso8601

@pytest.fixture
def aws_credentials():
    """Mock AWS Credentials for moto"""
    import os
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

@pytest.fixture
def s3_client(aws_credentials):
    with mock_aws():
        yield boto3.client('s3', region_name='us-east-1')

@pytest.fixture
def s3_bucket(s3_client):
    """Create a test S3 bucket and add some test files"""
    bucket_name = 'test-bucket'
    s3_client.create_bucket(Bucket=bucket_name)
    return bucket_name

@pytest.fixture
def sample_log_data():
    """Create sample log data"""
    return [
        {
            'timestamp_iso8601': '2023-01-01T00:30:00Z',
            'message': 'test message 1'
        },
        {
            'timestamp_iso8601': '2023-01-01T00:31:00Z',
            'message': 'test message 2'
        }
    ]

@pytest.fixture
def s3_test_files(s3_client, s3_bucket, sample_log_data):
    """Upload test files to S3"""
    # Create gzipped log files
    test_files = [
        ('prod/2023/01/01/00:30-abc123.gz', sample_log_data[0]),
        ('prod/2023/01/01/00:31-def456.gz', sample_log_data[1])
    ]

    for key, log_entry in test_files:
        # Convert log entry to gzipped JSON
        json_data = json.dumps(log_entry) + '\n'
        gzipped_data = gzip.compress(json_data.encode('utf-8'))

        s3_client.put_object(
            Bucket=s3_bucket,
            Key=key,
            Body=gzipped_data
        )

    return test_files

class TestS3Integration:
    def test_list_objects(self, s3_client, s3_bucket, s3_test_files):
        """Test listing objects from S3"""
        fetcher = LogFetcher(
            s3_client=s3_client,
            bucket_name=s3_bucket,
            environment='prod',
            start_time=parse_iso8601('2023-01-01T00:00:00Z'),
            end_time=parse_iso8601('2023-01-01T01:00:00Z'),
            quiet=True
        )

        objects = fetcher.list_objects('prod/2023/01/01/00:30')
        assert len(objects) == 1
        assert objects[0]['Key'].endswith('abc123.gz')

    def test_process_logs(self, s3_client, s3_bucket, s3_test_files, tmp_path):
        """Test processing logs from S3"""
        fetcher = LogFetcher(
            s3_client=s3_client,
            bucket_name=s3_bucket,
            environment='prod',
            start_time=parse_iso8601('2023-01-01T00:00:00Z'),
            end_time=parse_iso8601('2023-01-01T01:00:00Z'),
            quiet=True
        )

        # List all objects
        all_objects = []
        for prefix in fetcher.generate_prefixes():
            objects = fetcher.list_objects(prefix)
            all_objects.extend(objects)

        # Process logs
        logs = fetcher.process_logs(all_objects, str(tmp_path))

        assert len(logs) == 2
        assert any('test message 1' in log[1] for log in logs)
        assert any('test message 2' in log[1] for log in logs)

    def test_time_range_filtering(self, s3_client, s3_bucket, s3_test_files, tmp_path):
        """Test filtering logs by time range"""
        fetcher = LogFetcher(
            s3_client=s3_client,
            bucket_name=s3_bucket,
            environment='prod',
            start_time=parse_iso8601('2023-01-01T00:30:00Z'),
            end_time=parse_iso8601('2023-01-01T00:30:30Z'),  # Only include first log
            quiet=True
        )

        # List all objects
        all_objects = []
        for prefix in fetcher.generate_prefixes():
            objects = fetcher.list_objects(prefix)
            all_objects.extend(objects)

        # Process logs
        logs = fetcher.process_logs(all_objects, str(tmp_path))

        assert len(logs) == 1
        assert 'test message 1' in logs[0][1]

    def test_large_file_set(self, s3_client, s3_bucket, tmp_path):
        """Test handling of large number of files"""
        # Create many test files
        for i in range(1100):  # More than default S3 pagination limit
            log_entry = {
                'timestamp_iso8601': f'2023-01-01T00:{i%60:02d}:00Z',
                'message': f'test message {i}'
            }
            json_data = json.dumps(log_entry) + '\n'
            gzipped_data = gzip.compress(json_data.encode('utf-8'))

            s3_client.put_object(
                Bucket=s3_bucket,
                Key=f'prod/2023/01/01/00:{i%60:02d}-file{i}.gz',
                Body=gzipped_data
            )

        fetcher = LogFetcher(
            s3_client=s3_client,
            bucket_name=s3_bucket,
            environment='prod',
            start_time=parse_iso8601('2023-01-01T00:00:00Z'),
            end_time=parse_iso8601('2023-01-01T00:59:59Z'),
            quiet=True
        )

        # Test that we can list all objects
        all_objects = []
        for prefix in fetcher.generate_prefixes():
            objects = fetcher.list_objects(prefix)
            all_objects.extend(objects)

        assert len(all_objects) == 1100
