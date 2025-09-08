#!/usr/bin/env python3
"""
Import real ARGO data into the database.
"""

import sys
import os
import csv
import re
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from core.config import settings
from db.models import ArgoFloat, ArgoProfile

def parse_argo_date(date_str):
    """Parse ARGO date format YYYYMMDDHHMMSS to datetime."""
    try:
        return datetime.strptime(date_str, '%Y%m%d%H%M%S')
    except:
        return None

def extract_float_id_from_file(file_path):
    """Extract float ID from file path like 'aoml/13857/profiles/R13857_001.nc'"""
    match = re.search(r'/(\d+)/', file_path)
    return match.group(1) if match else None

def import_argo_data(limit=1000):
    """Import ARGO data from the index file."""
    print(f"🌊 Importing first {limit} ARGO records...")
    
    # Create database session
    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        floats_added = 0
        profiles_added = 0
        
        with open('ar_index_global_prof.txt', 'r') as file:
            # Skip header lines (start with #)
            for line in file:
                if not line.startswith('#'):
                    break
            
            # Read CSV data
            reader = csv.DictReader(file, fieldnames=[
                'file', 'date', 'latitude', 'longitude', 'ocean', 
                'profiler_type', 'institution', 'date_update'
            ])
            
            processed = 0
            for row in reader:
                if processed >= limit:
                    break
                    
                try:
                    # Extract float ID from file path
                    float_id = extract_float_id_from_file(row['file'])
                    if not float_id:
                        continue
                    
                    # Parse dates
                    measurement_date = parse_argo_date(row['date'])
                    update_date = parse_argo_date(row['date_update'])
                    
                    if not measurement_date:
                        continue
                    
                    # Check if float exists, if not create it
                    float_record = session.query(ArgoFloat).filter_by(float_id=float_id).first()
                    if not float_record:
                        float_record = ArgoFloat(
                            float_id=float_id,
                            institution=row['institution'],
                            status='active',
                            last_latitude=float(row['latitude']),
                            last_longitude=float(row['longitude']),
                            total_profiles=0,
                            first_profile_date=measurement_date,
                            last_profile_date=measurement_date
                        )
                        session.add(float_record)
                        floats_added += 1
                    else:
                        # Update float's last position and profile count
                        float_record.last_latitude = float(row['latitude'])
                        float_record.last_longitude = float(row['longitude'])
                        if measurement_date > (float_record.last_profile_date or datetime.min):
                            float_record.last_profile_date = measurement_date
                        float_record.total_profiles += 1
                    
                    # Create profile record
                    profile_id = f"{float_id}_{row['date']}"
                    
                    # Check if profile already exists
                    existing_profile = session.query(ArgoProfile).filter_by(profile_id=profile_id).first()
                    if not existing_profile:
                        profile = ArgoProfile(
                            profile_id=profile_id,
                            float_id=float_id,
                            cycle_number=1,  # Default, would need to extract from filename
                            measurement_date=measurement_date,
                            latitude=float(row['latitude']),
                            longitude=float(row['longitude']),
                            processing_date=update_date
                        )
                        session.add(profile)
                        profiles_added += 1
                    
                    processed += 1
                    
                    if processed % 100 == 0:
                        print(f"  Processed {processed} records...")
                        session.commit()
                
                except Exception as e:
                    print(f"Error processing row: {e}")
                    continue
        
        # Final commit
        session.commit()
        
        print(f"✅ Import complete!")
        print(f"   Floats added: {floats_added}")
        print(f"   Profiles added: {profiles_added}")
        print(f"   Total processed: {processed}")
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    import_argo_data(limit=1000)  # Start with 1000 records
