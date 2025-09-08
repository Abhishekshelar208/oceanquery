#!/usr/bin/env python3
"""
Filter ARGO global index to get manageable subset for demo.
Targets last 12 months in Indian Ocean region for efficient processing.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import json
import logging
from typing import List, Dict, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_argo_date(date_str: str) -> Optional[datetime]:
    """Parse ARGO date format YYYYMMDDHHMMSS."""
    try:
        return datetime.strptime(date_str[:14], '%Y%m%d%H%M%S')
    except (ValueError, TypeError):
        return None


def filter_by_region(df: pd.DataFrame, region: str = "IO") -> pd.DataFrame:
    """Filter profiles by ocean region."""
    if region == "IO":
        # Indian Ocean: roughly 20°S-30°N, 20°E-120°E
        mask = (
            (df['latitude'] >= -20) & 
            (df['latitude'] <= 30) &
            (df['longitude'] >= 20) & 
            (df['longitude'] <= 120)
        )
        logger.info(f"Indian Ocean filter: {mask.sum()} profiles")
        return df[mask]
    elif region == "global_sample":
        # Take a global sampling across all oceans
        sample_size = min(1000, len(df))
        return df.sample(n=sample_size, random_state=42)
    else:
        return df


def filter_by_time(df: pd.DataFrame, months_back: int = 12) -> pd.DataFrame:
    """Filter for profiles from last N months."""
    cutoff_date = datetime.now() - timedelta(days=months_back * 30)
    
    # Parse dates
    df['parsed_date'] = df['date'].apply(parse_argo_date)
    valid_dates = df['parsed_date'].notna()
    
    logger.info(f"Valid dates: {valid_dates.sum()} of {len(df)}")
    
    if valid_dates.sum() == 0:
        logger.warning("No valid dates found, returning empty DataFrame")
        return df.iloc[:0]
    
    recent_mask = df['parsed_date'] >= cutoff_date
    logger.info(f"Recent profiles ({months_back} months): {recent_mask.sum()}")
    
    return df[valid_dates & recent_mask]


def filter_by_quality(df: pd.DataFrame) -> pd.DataFrame:
    """Filter for high-quality profiles."""
    # Prefer core ARGO profiles (not BGC or other variants)
    core_mask = df['file'].str.contains(r'/profiles/[RD]\d+_\d+\.nc')
    logger.info(f"Core ARGO profiles: {core_mask.sum()}")
    return df[core_mask]


def build_download_urls(df: pd.DataFrame, base_url: str = "https://data-argo.ifremer.fr") -> pd.DataFrame:
    """Build full download URLs for profiles."""
    df = df.copy()
    df['download_url'] = base_url + "/dac/" + df['file']
    return df


def main():
    """Main filtering workflow."""
    backend_dir = Path(__file__).parent.parent
    index_file = backend_dir / "ar_index_global_prof.txt"
    output_dir = backend_dir / "data"
    
    if not index_file.exists():
        logger.error(f"Index file not found: {index_file}")
        return 1
    
    logger.info(f"Reading ARGO index: {index_file}")
    logger.info(f"File size: {index_file.stat().st_size / 1024 / 1024:.1f} MB")
    
    # Read the index file (skip comment lines)
    with open(index_file, 'r') as f:
        lines = []
        for line in f:
            if not line.startswith('#'):
                lines.append(line)
    
    # Parse as CSV
    from io import StringIO
    csv_data = StringIO(''.join(lines))
    
    columns = ['file', 'date', 'latitude', 'longitude', 'ocean', 
               'profiler_type', 'institution', 'date_update']
    
    df = pd.read_csv(csv_data, names=columns, low_memory=False)
    logger.info(f"Total profiles in index: {len(df)}")
    
    # Convert coordinates to numeric
    df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
    df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
    
    # Filter steps
    logger.info("Applying filters...")
    
    # 1. Filter by quality (core profiles)
    df_quality = filter_by_quality(df)
    
    # 2. Filter by region (Indian Ocean)
    df_region = filter_by_region(df_quality, region="IO")
    
    # 3. Filter by time (last 12 months)
    df_recent = filter_by_time(df_region, months_back=12)
    
    # If too few recent profiles, expand time window
    if len(df_recent) < 50:
        logger.warning("Few recent profiles, expanding to 24 months")
        df_recent = filter_by_time(df_region, months_back=24)
    
    # If still too few, take global sample
    if len(df_recent) < 50:
        logger.warning("Still few profiles, taking global sample")
        df_recent = filter_by_region(df_quality, region="global_sample")
    
    # 4. Limit to manageable size for demo (max 200 profiles)
    if len(df_recent) > 200:
        logger.info(f"Sampling 200 profiles from {len(df_recent)}")
        df_recent = df_recent.sample(n=200, random_state=42)
    
    # 5. Build download URLs
    df_final = build_download_urls(df_recent)
    
    # Save results
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "argo_index_subset.csv"
    
    df_final.to_csv(output_file, index=False)
    logger.info(f"Saved {len(df_final)} profiles to {output_file}")
    
    # Save metadata
    metadata = {
        "total_profiles_in_index": len(df),
        "filtered_profiles": len(df_final),
        "filter_criteria": {
            "region": "Indian Ocean (20°S-30°N, 20°E-120°E)",
            "time_window": "Last 12-24 months",
            "quality": "Core ARGO profiles only",
            "max_profiles": 200
        },
        "created_at": datetime.now().isoformat(),
        "geographic_bounds": {
            "min_lat": float(df_final['latitude'].min()),
            "max_lat": float(df_final['latitude'].max()),
            "min_lon": float(df_final['longitude'].min()),
            "max_lon": float(df_final['longitude'].max())
        },
        "date_range": {
            "earliest": df_final['date'].min(),
            "latest": df_final['date'].max()
        }
    }
    
    metadata_file = output_dir / "argo_subset_metadata.json"
    with open(metadata_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    logger.info(f"Saved metadata to {metadata_file}")
    logger.info("✅ Filtering complete!")
    
    # Summary
    print(f"\n📊 ARGO Index Filtering Summary:")
    print(f"   Original profiles: {len(df):,}")
    print(f"   Filtered profiles: {len(df_final):,}")
    print(f"   Geographic coverage: {metadata['geographic_bounds']}")
    print(f"   Date range: {metadata['date_range']}")
    print(f"   Output files:")
    print(f"     • {output_file}")
    print(f"     • {metadata_file}")
    
    return 0


if __name__ == "__main__":
    exit(main())
