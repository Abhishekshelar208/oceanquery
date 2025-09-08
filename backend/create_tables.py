#!/usr/bin/env python3
"""
Create database tables for OceanQuery ARGO data.
"""

import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add src to path so we can import our models
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from core.config import settings
from db.models import Base

def create_tables():
    """Create all database tables."""
    print("🗄️ Creating database tables...")
    
    # Create database engine
    engine = create_engine(settings.database_url)
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    print("✅ Database tables created successfully!")
    print("\nTables created:")
    for table_name in Base.metadata.tables.keys():
        print(f"  - {table_name}")

if __name__ == "__main__":
    create_tables()
