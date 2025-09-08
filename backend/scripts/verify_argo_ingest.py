#!/usr/bin/env python3
"""
Verify ARGO data ingestion and database integrity.
Performs checks to ensure measurement data is present and valid.
"""

import sys
import os
from datetime import datetime
from sqlalchemy import create_engine, func, text
from sqlalchemy.orm import sessionmaker
import numpy as np

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.config import settings
from db.models import ArgoFloat, ArgoProfile, ArgoMeasurement


def check_database_connectivity(session):
    """Test basic database connectivity."""
    try:
        session.execute(text('SELECT 1'))
        return True, "Database connection successful"
    except Exception as e:
        return False, f"Database connection failed: {e}"


def check_table_counts(session):
    """Check counts of each table."""
    try:
        float_count = session.query(ArgoFloat).count()
        profile_count = session.query(ArgoProfile).count()
        measurement_count = session.query(ArgoMeasurement).count()
        
        results = {
            'floats': float_count,
            'profiles': profile_count,
            'measurements': measurement_count
        }
        
        # Basic sanity checks
        issues = []
        if float_count == 0:
            issues.append("No floats found")
        if profile_count == 0:
            issues.append("No profiles found")
        if measurement_count == 0:
            issues.append("❌ CRITICAL: No measurements found")
        if profile_count < float_count:
            issues.append("Warning: Fewer profiles than floats (unusual)")
        if measurement_count < profile_count:
            issues.append("Warning: Fewer measurements than profiles (possible data issue)")
        
        return True, results, issues
    except Exception as e:
        return False, {}, [f"Error checking table counts: {e}"]


def check_measurement_quality(session):
    """Check measurement data quality and completeness."""
    try:
        total_measurements = session.query(ArgoMeasurement).count()
        
        if total_measurements == 0:
            return False, {}, ["No measurements to check"]
        
        # Check parameter availability
        temp_count = session.query(ArgoMeasurement).filter(
            ArgoMeasurement.temperature.isnot(None)
        ).count()
        
        sal_count = session.query(ArgoMeasurement).filter(
            ArgoMeasurement.salinity.isnot(None)
        ).count()
        
        oxygen_count = session.query(ArgoMeasurement).filter(
            ArgoMeasurement.oxygen.isnot(None)
        ).count()
        
        depth_count = session.query(ArgoMeasurement).filter(
            ArgoMeasurement.depth.isnot(None)
        ).count()
        
        # Check QC flags
        good_temp_qc = session.query(ArgoMeasurement).filter(
            ArgoMeasurement.temperature_qc == '1'
        ).count()
        
        # Check for valid ranges
        temp_stats = session.query(
            func.min(ArgoMeasurement.temperature).label('min_temp'),
            func.max(ArgoMeasurement.temperature).label('max_temp'),
            func.avg(ArgoMeasurement.temperature).label('avg_temp')
        ).filter(ArgoMeasurement.temperature.isnot(None)).first()
        
        sal_stats = session.query(
            func.min(ArgoMeasurement.salinity).label('min_sal'),
            func.max(ArgoMeasurement.salinity).label('max_sal'),
            func.avg(ArgoMeasurement.salinity).label('avg_sal')
        ).filter(ArgoMeasurement.salinity.isnot(None)).first()
        
        depth_stats = session.query(
            func.min(ArgoMeasurement.depth).label('min_depth'),
            func.max(ArgoMeasurement.depth).label('max_depth'),
            func.avg(ArgoMeasurement.depth).label('avg_depth')
        ).filter(ArgoMeasurement.depth.isnot(None)).first()
        
        results = {
            'total_measurements': total_measurements,
            'parameter_counts': {
                'temperature': temp_count,
                'salinity': sal_count,
                'oxygen': oxygen_count,
                'depth': depth_count
            },
            'qc_stats': {
                'good_temperature_qc': good_temp_qc
            },
            'parameter_ranges': {
                'temperature': {
                    'min': float(temp_stats.min_temp) if temp_stats and temp_stats.min_temp else None,
                    'max': float(temp_stats.max_temp) if temp_stats and temp_stats.max_temp else None,
                    'avg': float(temp_stats.avg_temp) if temp_stats and temp_stats.avg_temp else None
                },
                'salinity': {
                    'min': float(sal_stats.min_sal) if sal_stats and sal_stats.min_sal else None,
                    'max': float(sal_stats.max_sal) if sal_stats and sal_stats.max_sal else None,
                    'avg': float(sal_stats.avg_sal) if sal_stats and sal_stats.avg_sal else None
                },
                'depth': {
                    'min': float(depth_stats.min_depth) if depth_stats and depth_stats.min_depth else None,
                    'max': float(depth_stats.max_depth) if depth_stats and depth_stats.max_depth else None,
                    'avg': float(depth_stats.avg_depth) if depth_stats and depth_stats.avg_depth else None
                }
            }
        }
        
        # Validation checks
        issues = []
        
        # Check parameter completeness
        if temp_count < total_measurements * 0.5:
            issues.append(f"Low temperature data coverage: {temp_count}/{total_measurements} ({100*temp_count/total_measurements:.1f}%)")
        
        if sal_count < total_measurements * 0.5:
            issues.append(f"Low salinity data coverage: {sal_count}/{total_measurements} ({100*sal_count/total_measurements:.1f}%)")
        
        # Check realistic ranges
        if temp_stats and temp_stats.min_temp is not None:
            if temp_stats.min_temp < -5 or temp_stats.max_temp > 40:
                issues.append(f"Temperature out of realistic range: {temp_stats.min_temp:.1f}°C to {temp_stats.max_temp:.1f}°C")
        
        if sal_stats and sal_stats.min_sal is not None:
            if sal_stats.min_sal < 25 or sal_stats.max_sal > 40:
                issues.append(f"Salinity out of realistic range: {sal_stats.min_sal:.1f} to {sal_stats.max_sal:.1f} PSU")
        
        if depth_stats and depth_stats.max_depth is not None:
            if depth_stats.max_depth > 6000:
                issues.append(f"Unusually deep measurements: max depth {depth_stats.max_depth:.0f}m")
        
        return True, results, issues
        
    except Exception as e:
        return False, {}, [f"Error checking measurement quality: {e}"]


def check_profile_completeness(session):
    """Check that profiles have corresponding measurements."""
    try:
        profiles_with_measurements = session.query(
            func.count(func.distinct(ArgoMeasurement.profile_id))
        ).scalar()
        
        total_profiles = session.query(ArgoProfile).count()
        
        # Check profile-measurement linkage
        orphaned_profiles = session.query(ArgoProfile).filter(
            ~ArgoProfile.profile_id.in_(
                session.query(func.distinct(ArgoMeasurement.profile_id))
            )
        ).count()
        
        results = {
            'total_profiles': total_profiles,
            'profiles_with_measurements': profiles_with_measurements,
            'orphaned_profiles': orphaned_profiles,
            'coverage_percentage': 100 * profiles_with_measurements / total_profiles if total_profiles > 0 else 0
        }
        
        issues = []
        if orphaned_profiles > total_profiles * 0.1:
            issues.append(f"High number of profiles without measurements: {orphaned_profiles}/{total_profiles}")
        
        return True, results, issues
        
    except Exception as e:
        return False, {}, [f"Error checking profile completeness: {e}"]


def check_temporal_range(session):
    """Check temporal coverage of the data."""
    try:
        date_range = session.query(
            func.min(ArgoProfile.measurement_date).label('start_date'),
            func.max(ArgoProfile.measurement_date).label('end_date')
        ).first()
        
        if not date_range or not date_range.start_date:
            return False, {}, ["No measurement dates found"]
        
        # Count profiles by year
        profiles_by_year = session.query(
            func.extract('year', ArgoProfile.measurement_date).label('year'),
            func.count(ArgoProfile.id).label('count')
        ).group_by(func.extract('year', ArgoProfile.measurement_date)).all()
        
        results = {
            'start_date': date_range.start_date.isoformat(),
            'end_date': date_range.end_date.isoformat(),
            'time_span_days': (date_range.end_date - date_range.start_date).days,
            'profiles_by_year': dict(profiles_by_year)
        }
        
        issues = []
        if results['time_span_days'] < 30:
            issues.append(f"Limited temporal coverage: only {results['time_span_days']} days")
        
        return True, results, issues
        
    except Exception as e:
        return False, {}, [f"Error checking temporal range: {e}"]


def main():
    """Run all verification checks."""
    print("🔍 ARGO Data Ingestion Verification")
    print("=" * 50)
    
    # Create database session
    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    all_passed = True
    
    try:
        # 1. Database connectivity
        print("\n1. Database Connectivity")
        success, message = check_database_connectivity(session)
        if success:
            print(f"   ✅ {message}")
        else:
            print(f"   ❌ {message}")
            all_passed = False
            return 1
        
        # 2. Table counts
        print("\n2. Table Counts")
        success, results, issues = check_table_counts(session)
        if success:
            print(f"   📊 Floats: {results['floats']:,}")
            print(f"   📊 Profiles: {results['profiles']:,}")
            print(f"   📊 Measurements: {results['measurements']:,}")
            
            for issue in issues:
                if "CRITICAL" in issue:
                    print(f"   ❌ {issue}")
                    all_passed = False
                elif "Warning" in issue:
                    print(f"   ⚠️  {issue}")
                else:
                    print(f"   ❌ {issue}")
                    all_passed = False
        else:
            print(f"   ❌ Failed to check table counts")
            all_passed = False
        
        # 3. Measurement quality
        print("\n3. Measurement Data Quality")
        success, results, issues = check_measurement_quality(session)
        if success:
            params = results['parameter_counts']
            print(f"   📈 Temperature measurements: {params['temperature']:,}")
            print(f"   📈 Salinity measurements: {params['salinity']:,}")
            print(f"   📈 Oxygen measurements: {params['oxygen']:,}")
            print(f"   📈 Depth measurements: {params['depth']:,}")
            
            # Show ranges
            temp_range = results['parameter_ranges']['temperature']
            if temp_range['min'] is not None:
                print(f"   🌡️  Temperature range: {temp_range['min']:.1f}°C to {temp_range['max']:.1f}°C (avg: {temp_range['avg']:.1f}°C)")
            
            sal_range = results['parameter_ranges']['salinity']
            if sal_range['min'] is not None:
                print(f"   🧂 Salinity range: {sal_range['min']:.2f} to {sal_range['max']:.2f} PSU (avg: {sal_range['avg']:.2f} PSU)")
            
            depth_range = results['parameter_ranges']['depth']
            if depth_range['min'] is not None:
                print(f"   🌊 Depth range: {depth_range['min']:.0f}m to {depth_range['max']:.0f}m (avg: {depth_range['avg']:.0f}m)")
            
            for issue in issues:
                print(f"   ⚠️  {issue}")
        else:
            print(f"   ❌ Failed to check measurement quality")
            for issue in issues:
                print(f"   ❌ {issue}")
            all_passed = False
        
        # 4. Profile completeness
        print("\n4. Profile-Measurement Linkage")
        success, results, issues = check_profile_completeness(session)
        if success:
            print(f"   📊 Profiles with measurements: {results['profiles_with_measurements']:,}/{results['total_profiles']:,} ({results['coverage_percentage']:.1f}%)")
            if results['orphaned_profiles'] > 0:
                print(f"   🔍 Orphaned profiles: {results['orphaned_profiles']:,}")
            
            for issue in issues:
                print(f"   ⚠️  {issue}")
        else:
            print(f"   ❌ Failed to check profile completeness")
            all_passed = False
        
        # 5. Temporal range
        print("\n5. Temporal Coverage")
        success, results, issues = check_temporal_range(session)
        if success:
            print(f"   📅 Date range: {results['start_date']} to {results['end_date']}")
            print(f"   📅 Time span: {results['time_span_days']} days")
            
            if results['profiles_by_year']:
                print(f"   📅 Profiles by year: {dict(results['profiles_by_year'])}")
            
            for issue in issues:
                print(f"   ⚠️  {issue}")
        else:
            print(f"   ❌ Failed to check temporal coverage")
            all_passed = False
        
        # Summary
        print("\n" + "=" * 50)
        if all_passed:
            print("✅ All verification checks passed!")
            print("🌊 ARGO data ingestion appears to be successful.")
            return 0
        else:
            print("❌ Some verification checks failed!")
            print("🔧 Please review the issues above and re-run data ingestion if needed.")
            return 1
            
    except Exception as e:
        print(f"\n❌ Verification failed with error: {e}")
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    exit(main())
