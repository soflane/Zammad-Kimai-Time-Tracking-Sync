#!/usr/bin/env python
"""
Seed script for creating sample conflicts for dev.
Run with: cd backend; python ../frontend/scripts/seed_conflicts.py 
Or: python -m scripts.seed_conflicts in backend with PYTHONPATH set.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)) + '/app')

from datetime import date, datetime

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.config import settings

engine_url = settings.database_url  # Assume settings has it, or os.getenv('DATABASE_URL')

engine = create_engine(engine_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def seed():
    db = SessionLocal()

    # Create sample conflicts for each major reason
    data = [
        {
            'reason_code': 'UNMAPPED_ACTIVITY',
            'reason_detail': 'Activity Support not mapped to Kimai. Zammad type ID: 3.',
            'customer_name': 'Acme Inc.',
            'project_name': 'Ticket #50 – Bug Fix',
            'activity_name': 'Support',
            'ticket_number': '#50',
            'zammad_created_at': datetime(2025, 1, 3, 10, 0),
            'zammad_entry_date': date(2025, 1, 1),
            'zammad_time_minutes': 60.0,
            'reason_context': {'activity_name': 'Support', 'zammad_type_id': 3}
        },
        {
            'reason_code': 'DUPLICATE',
            'reason_detail': 'Duplicate entry for ticket #51 on Jan 2, 2025.',
            'customer_name': 'Acme Inc.',
            'project_name': 'Ticket #51 – Meeting',
            'activity_name': 'Meeting',
            'ticket_number': '#51',
            'zammad_created_at': datetime(2025, 1, 3, 10, 0),
            'zammad_entry_date': date(2025, 1, 2),
            'zammad_time_minutes': 30.0,
        },
        {
            'reason_code': 'TIME_MISMATCH',
            'reason_detail': 'Time duration mismatch for ticket #52: Zammad 45.0 min vs Kimai 40.0 min.',
            'customer_name': 'Acme Inc.',
            'project_name': 'Ticket #52 – Call',
            'activity_name': 'Call',
            'ticket_number': '#52',
            'zammad_created_at': datetime(2025, 1, 3, 10, 0),
            'zammad_entry_date': date(2025, 1, 3),
            'zammad_time_minutes': 45.0,
            'kimai_begin': '2025-01-03T10:00:00',
            'kimai_end': '2025-01-03T10:45:00',
            'kimai_duration_minutes': 40.0,
            'kimai_id': 20,
        },
        {
            'reason_code': 'PROJECT_OR_CUSTOMER_MISSING',
            'reason_detail': 'Missing project or customer mapping for organization Unknown.',
            'customer_name': 'Unknown',
            'project_name': 'Ticket #53',
            'activity_name': 'Support',
            'ticket_number': '#53',
            'zammad_created_at': datetime(2025, 1, 4, 10, 0),
            'zammad_entry_date': date(2025, 1, 4),
            'zammad_time_minutes': 120.0,
        },
        {
            'reason_code': 'LOCKED_OR_EXPORTED',
            'reason_detail': 'Kimai entry locked or exported, cannot update: ID 21.',
            'customer_name': 'Acme Inc.',
            'project_name': 'Ticket #54',
            'activity_name': 'Review',
            'ticket_number': '#54',
            'zammad_created_at': datetime(2025, 1, 5, 10, 0),
            'zammad_entry_date': date(2025, 1, 5),
            'zammad_time_minutes': 15.0,
            'kimai_begin': '2025-01-05T10:00:00',
            'kimai_end': '2025-01-05T10:15:00',
            'kimai_duration_minutes': 15.0,
            'kimai_id': 21,
        },
        {
            'reason_code': 'CREATION_ERROR',
            'reason_detail': 'Error creating timesheet in Kimai: Invalid field.',
            'customer_name': 'Acme Inc.',
            'project_name': 'Ticket #55',
            'activity_name': 'Testing',
            'ticket_number': '#55',
            'zammad_created_at': datetime(2025, 1, 6, 10, 0),
            'zammad_entry_date': date(2025, 1, 6),
            'zammad_time_minutes': 0.0,
        },
    ]

    for i, entry in enumerate(data):
        reason_code = entry['reason_code']
        conflict = Conflict(
            conflict_type=reason_code,
            reason_code=reason_code,
            reason_detail=entry['reason_detail'],
            customer_name=entry['customer_name'],
            project_name=entry['project_name'],
            activity_name=entry['activity_name'],
            ticket_number=entry['ticket_number'],
            zammad_created_at=entry['zammad_created_at'],
            zammad_entry_date=entry['zammad_entry_date'],
            zammad_time_minutes=entry['zammad_time_minutes'],
            kimai_begin=entry.get('kimai_begin'),
            kimai_end=entry.get('kimai_end'),
            kimai_duration_minutes=entry.get('kimai_duration_minutes'),
            kimai_id=entry.get('kimai_id'),
            resolution_status='pending'
        )
        db.add(conflict)

    db.commit()
    print(f"Successfully created {len(data)} sample conflicts for development.")

    # Print query to verify
    all_conflicts = db.query(Conflict).all()
    print(f"\nDatabase now has {len(all_conflicts)} conflicts.")
    for c in all_conflicts[-6:]:  # Last 6
        print(f"- ID {c.id}: {c.reason_code} (ticket {c.ticket_number})")

if __name__ == '__main__':
    seed()
