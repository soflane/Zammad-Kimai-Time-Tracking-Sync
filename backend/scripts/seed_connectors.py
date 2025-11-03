#!/usr/bin/env python
"""
Seed script for creating demo Zammad and Kimai connectors.
Run with: cd backend; python scripts/seed_connectors.py
Requires DATABASE_URL and ENCRYPTION_KEY in .env.
"""

import os
import sys

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db  # For session, but we'll use local
from app.models.connector import Connector
from app.models.user import User
from app.utils.encrypt import encrypt_data
from app.auth import get_password_hash  # For admin user
from app.config import settings

# Get DB URL from env or default
database_url = os.getenv('DATABASE_URL', 'postgresql://user:pass@localhost:5432/zammad_sync')
engine = create_engine(database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

def seed_connectors():
    # Check for existing connectors
    existing_zammad = db.query(Connector).filter(Connector.type == 'zammad').first()
    existing_kimai = db.query(Connector).filter(Connector.type == 'kimai').first()
    
    if existing_zammad and existing_kimai:
        print("Demo connectors already exist. Skipping seed.")
        return

    try:
        # Ensure admin user exists
        admin_user = db.query(User).filter(User.username == 'admin').first()
        if not admin_user:
            hashed_password = get_password_hash('changeme')
            admin_user = User(
                username='admin',
                full_name='Admin User',
                email='admin@zammad-sync.com',
                hashed_password=hashed_password,
                is_active=True
            )
            db.add(admin_user)
            print("Created demo admin user: admin / changeme")

        # Get encryption key; if not set, warn and use plain text (for dev only)
        encryption_key = os.getenv('ENCRYPTION_KEY')
        if not encryption_key:
            print("WARNING: ENCRYPTION_KEY not set. Tokens will be stored in plain text (dev only). Set it for production.")

        # Demo Zammad connector
        zammad_token = encrypt_data('demo-zammad-token', encryption_key) if encryption_key else 'demo-zammad-token'
        zammad_connector = Connector(
            name='Demo Zammad',
            type='zammad',
            base_url='https://zammad.example.com',
            api_token=zammad_token,
            is_active=True,
            settings={}
        )
        db.add(zammad_connector)
        print(f"Created demo Zammad connector: {zammad_connector.name}")

        # Demo Kimai connector
        kimai_token = encrypt_data('demo-kimai-token', encryption_key) if encryption_key else 'demo-kimai-token'
        kimai_connector = Connector(
            name='Demo Kimai',
            type='kimai',
            base_url='https://kimai.example.com',
            api_token=kimai_token,
            is_active=True,
            settings={
                'use_global_activities': True,
                'default_project_id': None,
                'default_country': 'BE',
                'default_currency': 'EUR',
                'default_timezone': 'Europe/Brussels'
            }
        )
        db.add(kimai_connector)
        print(f"Created demo Kimai connector: {kimai_connector.name}")

        db.commit()
        print("\nDemo connectors seeded successfully!")
        print("Next steps:")
        print("1. Update base_url and API tokens in the Connectors page (login: admin/changeme)")
        print("2. Test connections to validate configs")
        print("3. Create activity mappings")
        print("4. Run manual sync to test")

    except Exception as e:
        db.rollback()
        print(f"Error seeding connectors: {e}")
    finally:
        db.close()

if __name__ == '__main__':
    seed_connectors()
