from typing import List
from datetime import datetime

from app.connectors.base import TimeEntryNormalized

class NormalizerService:
    """
    Service responsible for normalizing time entries from various sources
    into a unified `TimeEntryNormalized` format.
    """

    def __init__(self):
        pass # Currently, no external dependencies for normalization logic itself

    def normalize_zammad_entry(self, zammad_data: dict) -> TimeEntryNormalized:
        """
        Normalizes a raw Zammad time entry dictionary into TimeEntryNormalized format.
        """
        # Example Zammad data structure (from techContext.md):
        # {
        #   "id": 6, "ticket_id": 50, "ticket_article_id": 87, "time_unit": "15.0",
        #   "type_id": 3, "created_by_id": 3, "created_at": "2023-08-16T08:11:49.315Z",
        #   "updated_at": "2023-08-16T08:11:49.315Z"
        # }
        # Note: Zammad's API often provides activity type name/ID via a separate lookup
        # and user email is not directly on time_accounting.
        # This will need to be enriched with more context from Zammad if available.

        created_at_dt = datetime.fromisoformat(zammad_data["created_at"].replace("Z", "+00:00"))
        updated_at_dt = datetime.fromisoformat(zammad_data["updated_at"].replace("Z", "+00:00"))

        duration_sec = int(float(zammad_data.get("time_unit", 0)) * 60)
        zid = zammad_data["id"]
        ticket_id = zammad_data.get("ticket_id")
        return TimeEntryNormalized(
            source_id=str(zid),
            source="zammad",
            ticket_id=ticket_id,
            ticket_number=None,
            description=f"Time on Ticket {ticket_id} (zid: {zid})",
            duration_sec=duration_sec,
            begin_time=None,
            end_time=None,
            activity_type_id=zammad_data.get("type_id"),
            activity_name=None,
            user_email="unknown@example.com",
            entry_date=created_at_dt.strftime("%Y-%m-%d"),
            created_at=zammad_data["created_at"],
            updated_at=zammad_data["updated_at"],
            tags=["source:zammad"],
            customer_name=None,
            project_name=None
        )

    def normalize_kimai_entry(self, kimai_data: dict) -> TimeEntryNormalized:
        """
        Normalizes a raw Kimai timesheet entry dictionary into TimeEntryNormalized format.
        """
        # Example Kimai data structure (from kimai_connector.py, fetch_time_entries)
        # Assuming the Kimai API response contains 'begin', 'end', 'activity', 'user', 'createdAt', 'updatedAt' etc.

        begin_datetime = datetime.fromisoformat(kimai_data["begin"])
        end_datetime = datetime.fromisoformat(kimai_data["end"])
        duration_sec = int((end_datetime - begin_datetime).total_seconds())
        if "duration" in kimai_data and kimai_data["duration"] > 0:
            duration_sec = int(kimai_data["duration"])
        begin_time = kimai_data["begin"]
        end_time = kimai_data["end"]

        return TimeEntryNormalized(
            source_id=str(kimai_data["id"]),
            source="kimai",
            ticket_number=None,
            ticket_id=None,
            description=kimai_data.get("description", ""),
            duration_sec=duration_sec,
            begin_time=begin_time,
            end_time=end_time,
            activity_type_id=kimai_data["activity"]["id"],
            activity_name=kimai_data["activity"]["name"],
            user_email=kimai_data["user"]["email"],
            entry_date=begin_datetime.strftime("%Y-%m-%d"),
            created_at=kimai_data["createdAt"],
            updated_at=kimai_data["updatedAt"],
            tags=kimai_data.get("tags", []),
            customer_name=None,
            project_name=None
        )
