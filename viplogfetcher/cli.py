#!/usr/bin/env python3

import click
import boto3
import tempfile
from tqdm import tqdm
from .core import LogFetcher, parse_iso8601

@click.command()
@click.argument('bucket_name', type=str)
@click.argument('environment', type=str)
@click.argument('start', type=str)
@click.argument('end', type=str)
@click.option('--profile', type=str, help='AWS profile name')
@click.option('--region', '-r', help='AWS region name (overrides AWS config)')
@click.option('--output-file', '-o', type=click.File('w'), default='-',
              help='Output file (default: stdout)')
@click.option('--quiet', '-q', is_flag=True, help='Suppress progress messages')

def download_and_sort_logs(bucket_name, environment, start, end, profile, region,
                          output_file, quiet):
    """
    This script downloads and processes log files from S3 within a specified time range.

    Arguments:
        BUCKET_NAME: Name of the S3 bucket
        ENVIRONMENT: Environment name (used in prefix path)
        START: Start time in ISO8601 format (YYYY-MM-DDTHH:MM:SSZ)
        END: End time in ISO8601 format (YYYY-MM-DDTHH:MM:SSZ)

    Example usage:
        # Basic usage
        python script.py my-bucket prod 2023-11-01T00:00:00Z 2023-11-02T00:00:00Z

        # With AWS profile
        python script.py my-bucket prod 2023-11-01T00:00:00Z 2023-11-02T00:00:00Z --profile prod-readonly

        # Output to file
        python script.py my-bucket prod 2023-11-01T00:00:00Z 2023-11-02T00:00:00Z -o output.log

    The script will search for files matching the pattern:
        /<environment>/YYYY/MM/DD/HH:MM-*.gz
    """
    try:
        start_time = parse_iso8601(start)
        end_time = parse_iso8601(end)

        session = boto3.Session(profile_name=profile) if profile else boto3.Session()
        s3_client = session.client('s3') if region is None else session.client('s3', region_name=region)

        fetcher = LogFetcher(s3_client, bucket_name, environment, start_time, end_time, quiet)

        with tempfile.TemporaryDirectory() as temp_dir:
            if not quiet:
                click.echo(f"Fetching logs from bucket: {bucket_name}", err=True)

            # Collect all matching objects across all prefixes
            all_objects = []
            prefixes = fetcher.generate_prefixes()
            for prefix in tqdm(prefixes, desc="Scanning prefixes", disable=quiet):
                objects = fetcher.list_objects(prefix)
                all_objects.extend(objects)

            if not all_objects:
                if not quiet:
                    click.echo(f"No files found in bucket {bucket_name}", err=True)
                return

            all_logs = fetcher.process_logs(all_objects, temp_dir)

            if not all_logs:
                if not quiet:
                    click.echo("No log entries found in the processed files.", err=True)
                return

            if not quiet:
                click.echo("Sorting log entries...", err=True)
            sorted_logs = sorted(all_logs, key=lambda x: x[0])

            for _, log_line in sorted_logs:
                click.echo(log_line, file=output_file)

            if not quiet:
                click.echo(f"Total log entries processed: {len(sorted_logs)}", err=True)

    except Exception as e:
        if not quiet:
            click.echo(f"An error occurred: {str(e)}", err=True)
        raise click.Abort()

def main():
    download_and_sort_logs()

if __name__ == "__main__":
    main()
