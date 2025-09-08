#!/usr/bin/env python3
"""
Generate synthetic ARGO measurement data for demo purposes.
Creates realistic temperature, salinity, and pressure profiles.
"""

import sys
import os
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import random
from typing import List, Tuple

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.config import settings
from db.models import ArgoFloat, ArgoProfile, ArgoMeasurement

def generate_realistic_profile(latitude: float, longitude: float, max_depth: float = 2000.0) -> List[Tuple[float, float, float]]:
    """
    Generate realistic temperature, salinity, pressure profile.
    Returns list of (pressure, temperature, salinity) tuples.
    """
    # Standard pressure levels (in dbar)
    pressures = np.array([
        0, 5, 10, 20, 30, 50, 75, 100, 125, 150, 200, 250, 300, 400, 500, 
        600, 700, 800, 900, 1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 
        1800, 1900, max_depth
    ])
    
    # Filter pressures within max depth
    pressures = pressures[pressures <= max_depth]
    
    # Generate realistic temperature profile (tropical to subtropical)
    surface_temp = 24.0 + 6.0 * np.sin(np.radians(latitude + 10))  # 18-30°C surface
    temp_gradient = np.linspace(surface_temp, 2.0, len(pressures))
    
    # Add thermocline structure
    thermocline_start = 50
    thermocline_end = 200
    for i, p in enumerate(pressures):
        if thermocline_start <= p <= thermocline_end:
            # Strong gradient in thermocline
            gradient_factor = (p - thermocline_start) / (thermocline_end - thermocline_start)
            temp_gradient[i] = surface_temp - gradient_factor * (surface_temp - 8.0)
        elif p > thermocline_end:
            # Gradual decrease in deep water
            deep_factor = min((p - thermocline_end) / (max_depth - thermocline_end), 1.0)
            temp_gradient[i] = 8.0 - deep_factor * 6.0  # 8°C to 2°C
    
    # Add realistic noise
    temperature = temp_gradient + np.random.normal(0, 0.2, len(pressures))
    temperature = np.maximum(temperature, 0.5)  # Physical minimum
    
    # Generate realistic salinity profile (PSU)
    surface_salinity = 34.0 + 1.5 * np.cos(np.radians(latitude * 2))  # 32.5-35.5 PSU
    salinity = np.full(len(pressures), surface_salinity)
    
    # Halocline structure
    for i, p in enumerate(pressures):
        if p > 100:
            # Slight increase with depth
            depth_factor = min((p - 100) / (max_depth - 100), 1.0)
            salinity[i] = surface_salinity + depth_factor * 0.5
        if p > 1000:
            # Deep water characteristics
            salinity[i] = surface_salinity + 0.3
    
    # Add realistic noise
    salinity += np.random.normal(0, 0.05, len(pressures))
    salinity = np.maximum(salinity, 30.0)  # Physical minimum
    
    return list(zip(pressures.tolist(), temperature.tolist(), salinity.tolist()))


def generate_measurements_for_profiles(session, max_profiles: int = 50):
    """Generate synthetic measurements for existing profiles."""
    
    # Get profiles without measurements
    profiles = session.query(ArgoProfile).limit(max_profiles).all()
    
    measurements_added = 0
    profiles_processed = 0
    
    for profile in profiles:
        try:
            # Check if profile already has measurements
            existing_count = session.query(ArgoMeasurement).filter_by(profile_id=profile.profile_id).count()
            if existing_count > 0:
                print(f"  Profile {profile.profile_id} already has {existing_count} measurements, skipping")
                continue
            
            # Generate realistic depth based on location (deeper in open ocean)
            max_pressure = 2000.0
            if abs(profile.latitude) < 10:  # Equatorial region, deeper
                max_pressure = 2000.0
            elif abs(profile.latitude) > 50:  # Polar regions, shallower
                max_pressure = 1000.0
            else:
                max_pressure = 1500.0
            
            # Add some randomness
            max_pressure *= (0.8 + 0.4 * random.random())
            
            # Generate profile
            profile_data = generate_realistic_profile(
                profile.latitude, 
                profile.longitude, 
                max_pressure
            )
            
            # Create measurement records
            measurements = []
            for pressure, temperature, salinity in profile_data:
                # Calculate approximate depth from pressure (rough conversion)
                depth = pressure * 1.02  # dbar to meters approximation
                
                # Generate oxygen (realistic profile)
                if pressure < 100:
                    oxygen = 200 + 50 * np.random.normal()  # High surface oxygen
                elif pressure < 500:
                    oxygen = 50 + 30 * np.random.normal()   # Oxygen minimum zone
                else:
                    oxygen = 150 + 40 * np.random.normal()  # Deep water recovery
                oxygen = max(oxygen, 10.0)  # Physical minimum
                
                measurement = ArgoMeasurement(
                    profile_id=profile.profile_id,
                    pressure=float(pressure),
                    depth=float(depth),
                    temperature=float(temperature),
                    salinity=float(salinity),
                    oxygen=float(oxygen),
                    pressure_qc='1',    # Good quality
                    temperature_qc='1',
                    salinity_qc='1',
                    oxygen_qc='1'
                )
                measurements.append(measurement)
            
            # Bulk insert measurements
            session.add_all(measurements)
            
            # Update profile metadata
            profile.data_points = len(measurements)
            profile.max_pressure = max([m.pressure for m in measurements])
            profile.min_pressure = min([m.pressure for m in measurements])
            
            measurements_added += len(measurements)
            profiles_processed += 1
            
            if profiles_processed % 10 == 0:
                session.commit()
                print(f"  Processed {profiles_processed} profiles, added {measurements_added:,} measurements")
        
        except Exception as e:
            print(f"  Error processing profile {profile.profile_id}: {e}")
            continue
    
    session.commit()
    return profiles_processed, measurements_added


def main():
    """Main workflow."""
    print("🌊 Generating synthetic ARGO measurement data...")
    
    # Create database session
    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Check current state
        float_count = session.query(ArgoFloat).count()
        profile_count = session.query(ArgoProfile).count()
        measurement_count = session.query(ArgoMeasurement).count()
        
        print(f"Current database state:")
        print(f"  Floats: {float_count}")
        print(f"  Profiles: {profile_count}")
        print(f"  Measurements: {measurement_count:,}")
        
        if measurement_count > 0:
            print("⚠️  Measurements already exist. Delete them first if you want to regenerate.")
            return 0
        
        if profile_count == 0:
            print("❌ No profiles found. Run import_argo_data.py first.")
            return 1
        
        # Generate measurements
        print(f"\nGenerating measurements for up to 50 profiles...")
        profiles_processed, measurements_added = generate_measurements_for_profiles(session, max_profiles=50)
        
        # Final stats
        final_measurement_count = session.query(ArgoMeasurement).count()
        
        print(f"\n✅ Synthetic data generation complete!")
        print(f"   Profiles processed: {profiles_processed}")
        print(f"   Measurements added: {measurements_added:,}")
        print(f"   Total measurements in DB: {final_measurement_count:,}")
        print(f"   Average measurements per profile: {final_measurement_count / profiles_processed:.1f}")
        
        # Sample data check
        sample_measurements = session.query(ArgoMeasurement).limit(5).all()
        print(f"\n📊 Sample measurements:")
        for m in sample_measurements:
            print(f"   Profile {m.profile_id}: {m.depth:.0f}m, {m.temperature:.1f}°C, {m.salinity:.2f}PSU")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        session.rollback()
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    exit(main())
