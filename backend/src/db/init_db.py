"""
Database initialization utilities for OceanQuery.
"""

import logging
from typing import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from alembic import command
from alembic.config import Config

from src.core.config import settings
from src.db.models import Base, ArgoFloat, ArgoProfile, ArgoMeasurement

logger = logging.getLogger(__name__)


# Create database engine
engine = create_engine(
    settings.database_url_sync,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    echo=settings.database_echo,
    pool_pre_ping=True,  # Validate connections before use
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Get database session with automatic cleanup."""
    session = SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    """Dependency for FastAPI route handlers."""
    with get_db_session() as session:
        yield session


def create_database_tables():
    """Create all database tables."""
    try:
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully!")
        
        # Verify table creation
        with get_db_session() as session:
            result = session.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name;
            """))
            tables = [row[0] for row in result]
            logger.info(f"Created tables: {', '.join(tables)}")
            
    except SQLAlchemyError as e:
        logger.error(f"Error creating database tables: {e}")
        raise


def drop_database_tables():
    """Drop all database tables (use with caution!)."""
    try:
        logger.warning("Dropping all database tables...")
        Base.metadata.drop_all(bind=engine)
        logger.info("All database tables dropped!")
    except SQLAlchemyError as e:
        logger.error(f"Error dropping database tables: {e}")
        raise


def check_database_connection():
    """Check if database connection is working."""
    try:
        with get_db_session() as session:
            result = session.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            logger.info(f"Database connection successful! PostgreSQL version: {version}")
            return True
    except SQLAlchemyError as e:
        logger.error(f"Database connection failed: {e}")
        return False


def get_database_stats():
    """Get basic database statistics."""
    try:
        with get_db_session() as session:
            # Get table row counts
            stats = {}
            
            # ARGO floats
            float_count = session.query(ArgoFloat).count()
            active_float_count = session.query(ArgoFloat).filter(
                ArgoFloat.status == 'active'
            ).count()
            stats['floats'] = {
                'total': float_count,
                'active': active_float_count
            }
            
            # ARGO profiles
            profile_count = session.query(ArgoProfile).count()
            stats['profiles'] = {'total': profile_count}
            
            # ARGO measurements
            measurement_count = session.query(ArgoMeasurement).count()
            stats['measurements'] = {'total': measurement_count}
            
            # Database size
            result = session.execute(text("""
                SELECT pg_size_pretty(pg_database_size(current_database())) as db_size;
            """))
            db_size = result.fetchone()[0]
            stats['database_size'] = db_size
            
            return stats
            
    except SQLAlchemyError as e:
        logger.error(f"Error getting database stats: {e}")
        return {}


def create_sample_data():
    """Create sample ARGO data for testing."""
    try:
        logger.info("Creating sample ARGO data...")
        
        with get_db_session() as session:
            # Check if sample data already exists
            existing_float = session.query(ArgoFloat).filter(
                ArgoFloat.float_id == '2902755'
            ).first()
            
            if existing_float:
                logger.info("Sample data already exists, skipping creation.")
                return
            
            # Create sample float
            sample_float = ArgoFloat(
                float_id='2902755',
                platform_number='7900522',
                wmo_number='7900522',
                project_name='Indian Ocean ARGO',
                pi_name='Dr. Sample Scientist',
                institution='Indian National Centre for Ocean Information Services',
                wmo_inst_type='863',
                status='active',
                deployment_date='2022-01-15',
                last_contact_date='2024-11-01',
                last_latitude=10.5,
                last_longitude=77.2,
                total_profiles=5,
                first_profile_date='2022-01-20',
                last_profile_date='2024-11-01'
            )
            session.add(sample_float)
            session.flush()  # Get the ID
            
            # Create sample profiles
            from datetime import datetime, timedelta
            
            base_date = datetime(2024, 11, 1, 12, 0, 0)
            base_lat = 10.5
            base_lon = 77.2
            
            for i in range(5):
                profile = ArgoProfile(
                    profile_id=f'2902755_{i+1:03d}',
                    float_id='2902755',
                    cycle_number=i + 1,
                    measurement_date=base_date - timedelta(days=i*10),
                    latitude=base_lat + (i * 0.1),
                    longitude=base_lon + (i * 0.1),
                    data_points=4,
                    max_pressure=100.0,
                    min_pressure=0.0,
                    quality_flag='A',
                    data_mode='R'
                )
                session.add(profile)
                session.flush()
                
                # Create sample measurements for each profile
                for j, pressure in enumerate([0.0, 10.0, 50.0, 100.0]):
                    measurement = ArgoMeasurement(
                        profile_id=profile.profile_id,
                        pressure=pressure,
                        depth=pressure * 0.99,  # Approximate conversion
                        temperature=29.0 - (pressure * 0.14) + (i * 0.1),  # Temperature decreases with depth
                        salinity=35.2 + (i * 0.02),
                        oxygen=210.0 - (pressure * 0.3),
                        pressure_qc='1',
                        temperature_qc='1',
                        salinity_qc='1',
                        oxygen_qc='1'
                    )
                    session.add(measurement)
            
            # Create second sample float
            sample_float2 = ArgoFloat(
                float_id='2902756',
                platform_number='7900523',
                wmo_number='7900523',
                project_name='Arabian Sea Monitoring',
                pi_name='Dr. Ocean Explorer',
                institution='National Institute of Oceanography',
                wmo_inst_type='863',
                status='active',
                deployment_date='2022-03-20',
                last_contact_date='2024-10-30',
                last_latitude=8.3,
                last_longitude=73.1,
                total_profiles=3,
                first_profile_date='2022-03-25',
                last_profile_date='2024-10-30'
            )
            session.add(sample_float2)
            
            session.commit()
            logger.info("Sample ARGO data created successfully!")
            
    except SQLAlchemyError as e:
        logger.error(f"Error creating sample data: {e}")
        raise


def reset_database():
    """Reset database by dropping and recreating tables."""
    logger.warning("Resetting database...")
    drop_database_tables()
    create_database_tables()
    create_sample_data()
    logger.info("Database reset completed!")


def main():
    """Main function for running database initialization."""
    import argparse
    
    parser = argparse.ArgumentParser(description='OceanQuery Database Initialization')
    parser.add_argument('--create', action='store_true', help='Create database tables')
    parser.add_argument('--drop', action='store_true', help='Drop database tables')
    parser.add_argument('--reset', action='store_true', help='Reset database (drop and recreate)')
    parser.add_argument('--check', action='store_true', help='Check database connection')
    parser.add_argument('--stats', action='store_true', help='Show database statistics')
    parser.add_argument('--sample', action='store_true', help='Create sample data')
    
    args = parser.parse_args()
    
    if args.check:
        if check_database_connection():
            print("✅ Database connection successful!")
        else:
            print("❌ Database connection failed!")
            return 1
    
    if args.drop:
        drop_database_tables()
    
    if args.create:
        create_database_tables()
    
    if args.reset:
        reset_database()
    
    if args.sample:
        create_sample_data()
    
    if args.stats:
        stats = get_database_stats()
        print("\n📊 Database Statistics:")
        for table, data in stats.items():
            if isinstance(data, dict):
                print(f"  {table}: {data}")
            else:
                print(f"  {table}: {data}")
    
    return 0


if __name__ == "__main__":
    exit(main())
