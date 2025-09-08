#!/usr/bin/env python3
"""
Download ARGO NetCDF profile files from GDAC mirrors.
Processes the filtered index and downloads files in parallel.
"""

import asyncio
import aiohttp
import aiofiles
import pandas as pd
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import time
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ArgoDownloader:
    """Async ARGO profile downloader with retry logic and progress tracking."""
    
    def __init__(self, base_url: str = "https://usgodae.org/ftp/outgoing/argo", 
                 max_concurrent: int = 5, max_retries: int = 3):
        self.base_url = base_url
        self.max_concurrent = max_concurrent 
        self.max_retries = max_retries
        self.session: Optional[aiohttp.ClientSession] = None
        self.stats = {
            'downloaded': 0,
            'skipped': 0,
            'failed': 0,
            'total_size': 0,
            'start_time': None
        }
    
    async def __aenter__(self):
        """Async context manager entry."""
        import ssl
        timeout = aiohttp.ClientTimeout(total=300, connect=60)
        # Disable SSL verification for now to handle cert issues
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        connector = aiohttp.TCPConnector(
            limit=self.max_concurrent, 
            limit_per_host=self.max_concurrent,
            ssl=ssl_context
        )
        self.session = aiohttp.ClientSession(timeout=timeout, connector=connector)
        self.stats['start_time'] = time.time()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    def get_local_path(self, file_path: str, base_dir: Path) -> Path:
        """Convert ARGO file path to local file system path."""
        # Remove leading slash if present
        clean_path = file_path.lstrip('/')
        return base_dir / clean_path
    
    def get_download_url(self, file_path: str) -> str:
        """Build full download URL."""
        clean_path = file_path.lstrip('/')
        return f"{self.base_url}/{clean_path}"
    
    async def download_file(self, file_path: str, local_path: Path) -> Tuple[bool, str, int]:
        """
        Download a single file with retry logic.
        Returns (success, message, file_size)
        """
        url = self.get_download_url(file_path)
        
        # Skip if file already exists
        if local_path.exists():
            size = local_path.stat().st_size
            if size > 0:  # File exists and has content
                self.stats['skipped'] += 1
                return True, "Already exists", size
        
        # Create parent directory
        local_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Download with retries
        for attempt in range(self.max_retries):
            try:
                async with self.session.get(url) as response:
                    if response.status == 200:
                        content = await response.read()
                        
                        async with aiofiles.open(local_path, 'wb') as f:
                            await f.write(content)
                        
                        file_size = len(content)
                        self.stats['downloaded'] += 1
                        self.stats['total_size'] += file_size
                        return True, f"Downloaded {file_size} bytes", file_size
                    
                    elif response.status == 404:
                        return False, "File not found (404)", 0
                    else:
                        error_msg = f"HTTP {response.status}"
                        if attempt < self.max_retries - 1:
                            await asyncio.sleep(2 ** attempt)  # Exponential backoff
                            continue
                        return False, error_msg, 0
                        
            except asyncio.TimeoutError:
                error_msg = "Timeout"
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                return False, error_msg, 0
            except Exception as e:
                error_msg = str(e)
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                return False, error_msg, 0
        
        self.stats['failed'] += 1
        return False, "Max retries exceeded", 0
    
    async def download_batch(self, file_paths: List[str], base_dir: Path, 
                           progress_callback=None) -> List[Dict]:
        """Download a batch of files concurrently."""
        semaphore = asyncio.Semaphore(self.max_concurrent)
        results = []
        
        async def download_with_semaphore(file_path: str):
            async with semaphore:
                local_path = self.get_local_path(file_path, base_dir)
                success, message, size = await self.download_file(file_path, local_path)
                
                result = {
                    'file_path': file_path,
                    'local_path': str(local_path),
                    'success': success,
                    'message': message,
                    'size': size,
                    'timestamp': datetime.now().isoformat()
                }
                
                if progress_callback:
                    progress_callback(result, len(results) + 1, len(file_paths))
                
                return result
        
        # Create tasks
        tasks = [download_with_semaphore(fp) for fp in file_paths]
        
        # Execute with progress
        for coro in asyncio.as_completed(tasks):
            result = await coro
            results.append(result)
        
        return results
    
    def get_stats_summary(self) -> Dict:
        """Get download statistics summary."""
        elapsed = time.time() - (self.stats['start_time'] or time.time())
        total_files = self.stats['downloaded'] + self.stats['skipped'] + self.stats['failed']
        
        return {
            'downloaded': self.stats['downloaded'],
            'skipped': self.stats['skipped'], 
            'failed': self.stats['failed'],
            'total_files': total_files,
            'total_size_mb': self.stats['total_size'] / 1024 / 1024,
            'elapsed_seconds': elapsed,
            'download_rate_mbps': (self.stats['total_size'] / 1024 / 1024) / elapsed if elapsed > 0 else 0
        }


def progress_callback(result: Dict, current: int, total: int):
    """Progress callback for download status."""
    status = "✅" if result['success'] else "❌"
    size_mb = result['size'] / 1024 / 1024
    file_name = Path(result['file_path']).name
    
    print(f"[{current:3d}/{total:3d}] {status} {file_name} ({size_mb:.1f}MB) - {result['message']}")


async def main():
    """Main download workflow."""
    parser = argparse.ArgumentParser(description='Download ARGO NetCDF profile files')
    parser.add_argument('--index-file', type=Path, 
                       default=Path(__file__).parent.parent / 'data' / 'argo_index_subset.csv',
                       help='Path to filtered ARGO index CSV')
    parser.add_argument('--output-dir', type=Path,
                       default=Path(__file__).parent.parent / 'data' / 'raw',
                       help='Output directory for NetCDF files')
    parser.add_argument('--limit', type=int, default=50,
                       help='Maximum number of files to download')
    parser.add_argument('--max-concurrent', type=int, default=5,
                       help='Maximum concurrent downloads')
    parser.add_argument('--base-url', type=str, default="https://usgodae.org/ftp/outgoing/argo",
                       help='ARGO GDAC base URL')
    
    args = parser.parse_args()
    
    # Check input file
    if not args.index_file.exists():
        logger.error(f"Index file not found: {args.index_file}")
        return 1
    
    # Read the index
    logger.info(f"Reading index: {args.index_file}")
    df = pd.read_csv(args.index_file)
    logger.info(f"Found {len(df)} profiles in index")
    
    # Limit the number of files
    if args.limit and len(df) > args.limit:
        df = df.head(args.limit)
        logger.info(f"Limited to first {args.limit} profiles")
    
    # Create output directory
    args.output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output directory: {args.output_dir}")
    
    # Start download
    logger.info(f"Starting download with {args.max_concurrent} concurrent connections...")
    
    async with ArgoDownloader(base_url=args.base_url, max_concurrent=args.max_concurrent) as downloader:
        file_paths = df['file'].tolist()
        
        results = await downloader.download_batch(
            file_paths=file_paths,
            base_dir=args.output_dir,
            progress_callback=progress_callback
        )
        
        # Save results log
        results_file = args.output_dir.parent / f"download_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump({
                'download_results': results,
                'statistics': downloader.get_stats_summary(),
                'arguments': {
                    'index_file': str(args.index_file),
                    'output_dir': str(args.output_dir),
                    'limit': args.limit,
                    'max_concurrent': args.max_concurrent,
                    'base_url': args.base_url
                }
            }, f, indent=2)
        
        logger.info(f"Results saved to: {results_file}")
        
        # Print summary
        stats = downloader.get_stats_summary()
        print(f"\n📥 Download Summary:")
        print(f"   Downloaded: {stats['downloaded']:,} files ({stats['total_size_mb']:.1f} MB)")
        print(f"   Skipped: {stats['skipped']:,} files (already exist)")
        print(f"   Failed: {stats['failed']:,} files")
        print(f"   Total time: {stats['elapsed_seconds']:.1f} seconds")
        print(f"   Download rate: {stats['download_rate_mbps']:.1f} MB/s")
        
        # Count successful NetCDF files
        nc_files = list(args.output_dir.glob('**/*.nc'))
        print(f"   NetCDF files in output: {len(nc_files):,}")
        
        if stats['failed'] > 0:
            failed_files = [r['file_path'] for r in results if not r['success']]
            logger.warning(f"Failed downloads: {failed_files[:5]}...")
        
        return 0 if stats['failed'] == 0 else 1


if __name__ == "__main__":
    exit(asyncio.run(main()))
