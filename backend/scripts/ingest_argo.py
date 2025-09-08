#!/usr/bin/env python3
"""
Command-line interface for ARGO NetCDF data ingestion.
"""

import argparse
import json
import sys
from pathlib import Path

from src.data.ingestion.config import load_config_from_env, IngestionConfig, create_sample_config
from src.data.ingestion.service import ArgoIngestionService, create_ingestion_service


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ARGO NetCDF Ingestion CLI")

    parser.add_argument("command", choices=["ingest", "ingest-file", "resume", "stats", "optimize"],
                        help="Command to execute")

    parser.add_argument("--input", "-i", type=str, help="Input directory or file path")
    parser.add_argument("--patterns", "-p", type=str, nargs="*", help="Glob patterns for files (e.g., *.nc **/*.nc)")
    parser.add_argument("--dry-run", action="store_true", help="Parse files without inserting into DB")
    parser.add_argument("--max-workers", type=int, help="Override max workers")
    parser.add_argument("--batch-size", type=int, help="Override batch size")
    parser.add_argument("--log-level", type=str, help="Logging level (DEBUG, INFO, WARNING, ERROR)")
    parser.add_argument("--sample", action="store_true", help="Use sample config (data/samples/argo)")

    return parser.parse_args()


def main():
    args = parse_args()

    # Load configuration
    if args.sample:
        config: IngestionConfig = create_sample_config()
    else:
        config: IngestionConfig = load_config_from_env()

    # Apply overrides
    if args.max_workers:
        config.max_workers = args.max_workers
    if args.batch_size:
        config.batch_size = args.batch_size
    if args.log_level:
        config.log_level = args.log_level.upper()

    # Create service
    service: ArgoIngestionService = create_ingestion_service()

    # Command execution
    if args.command == "ingest":
        directory = Path(args.input) if args.input else config.input_directory
        patterns = args.patterns if args.patterns else config.file_patterns
        summary = service.ingest_directory(directory=directory, file_patterns=patterns, dry_run=args.dry_run)
        print(json.dumps(summary.__dict__, indent=2))

    elif args.command == "ingest-file":
        if not args.input:
            print("--input is required for ingest-file", file=sys.stderr)
            sys.exit(2)
        result = service.ingest_file(Path(args.input), dry_run=args.dry_run)
        print(json.dumps({
          "file_path": str(result.file_path),
          "success": result.success,
          "records_processed": result.records_processed,
          "records_inserted": result.records_inserted,
          "errors": result.errors,
          "warnings": result.warnings,
          "processing_time": result.processing_time,
        }, indent=2))

    elif args.command == "resume":
        directory = Path(args.input) if args.input else config.input_directory
        summary = service.resume_ingestion(directory=directory)
        print(json.dumps(summary.__dict__, indent=2))

    elif args.command == "stats":
        stats = service.get_ingestion_statistics()
        print(json.dumps(stats, indent=2))

    elif args.command == "optimize":
        result = service.cleanup_and_optimize()
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

