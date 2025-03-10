import pytest
from click.testing import CliRunner
from unittest.mock import Mock, patch
from datetime import datetime, timezone
from viplogfetcher.cli import download_and_sort_logs

@pytest.fixture
def cli_runner():
    return CliRunner()

@pytest.fixture
def mock_s3_client():
    mock = Mock()
    # Mock paginator
    mock_paginator = Mock()
    mock_paginator.paginate.return_value = [{'Contents': [{'Key': 'test.gz'}]}]
    mock.get_paginator.return_value = mock_paginator
    return mock

@pytest.fixture
def mock_boto3_session(mock_s3_client):
    with patch('boto3.Session') as mock_session:
        mock_session.return_value.client.return_value = mock_s3_client
        yield mock_session

class TestCLI:
    def test_missing_arguments(self, cli_runner):
        """Test CLI with missing required arguments"""
        result = cli_runner.invoke(download_and_sort_logs, [])
        assert result.exit_code == 2
        assert 'Missing argument' in result.output

    @patch('tempfile.TemporaryDirectory')
    @patch('gzip.open')
    def test_successful_execution(self, mock_gzip_open, mock_temp_dir,
                                cli_runner, mock_boto3_session):
        """Test successful execution of the CLI"""
        # Mock temporary directory
        mock_temp_dir.return_value.__enter__.return_value = '/tmp'

        # Mock log file content
        mock_gzip_open.return_value.__enter__.return_value = [
            f'{{"timestamp_iso8601": "2023-01-01T00:30:00Z", "message": "test message"}}\n'
        ]

        # Run CLI command
        result = cli_runner.invoke(download_and_sort_logs, [
            'test-bucket',
            'prod',
            '2023-01-01T00:00:00Z',
            '2023-01-01T01:00:00Z',
            '--quiet'
        ])

        assert result.exit_code == 0
        assert 'test message' in result.output

    def test_invalid_date_format(self, cli_runner):
        """Test CLI with invalid date format"""
        result = cli_runner.invoke(download_and_sort_logs, [
            'test-bucket',
            'prod',
            'invalid-date',  # Invalid date format
            '2023-01-01T01:00:00Z'
        ])
        assert result.exit_code == 1
        assert 'Invalid isoformat string' in result.stdout

    def test_aws_profile_usage(self, cli_runner, mock_boto3_session):
        """Test CLI with AWS profile specification"""
        result = cli_runner.invoke(download_and_sort_logs, [
            'test-bucket',
            'prod',
            '2023-01-01T00:00:00Z',
            '2023-01-01T01:00:00Z',
            '--profile',
            'test-profile'
        ])

        mock_boto3_session.assert_called_with(profile_name='test-profile')

    def test_aws_region_usage(self, cli_runner, mock_boto3_session):
        """Test CLI with AWS region specification"""
        result = cli_runner.invoke(download_and_sort_logs, [
            'test-bucket',
            'prod',
            '2023-01-01T00:00:00Z',
            '2023-01-01T01:00:00Z',
            '--region',
            'us-west-2'
        ])

        mock_boto3_session.return_value.client.assert_called_with('s3', region_name='us-west-2')

    def test_output_file(self, cli_runner, mock_boto3_session, tmp_path):
        """Test CLI with output file specification"""
        output_file = tmp_path / "output.log"

        with patch('gzip.open') as mock_gzip_open:
            mock_gzip_open.return_value.__enter__.return_value = [
                f'{{"timestamp_iso8601": "2023-01-01T00:30:00Z", "message": "test message"}}\n'
            ]

            result = cli_runner.invoke(download_and_sort_logs, [
                'test-bucket',
                'prod',
                '2023-01-01T00:00:00Z',
                '2023-01-01T01:00:00Z',
                '--output-file',
                str(output_file),
                '--quiet'
            ])

            assert result.exit_code == 0
            assert output_file.exists()
            assert 'test message' in output_file.read_text()
