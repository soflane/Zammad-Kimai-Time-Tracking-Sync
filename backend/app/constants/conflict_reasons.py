from enum import Enum
from typing import Dict

class ReasonCode(Enum):
    UNMAPPED_ACTIVITY = "UNMAPPED_ACTIVITY"
    DUPLICATE = "DUPLICATE"
    TIME_MISMATCH = "TIME_MISMATCH"
    PROJECT_OR_CUSTOMER_MISSING = "PROJECT_OR_CUSTOMER_MISSING"
    LOCKED_OR_EXPORTED = "LOCKED_OR_EXPORTED"
    CONFLICT = "CONFLICT"
    CREATION_ERROR = "CREATION_ERROR"
    OTHER = "OTHER"

def explain_reason(code: ReasonCode, context: Dict) -> str:
    templates = {
        ReasonCode.UNMAPPED_ACTIVITY: "Activity {activity_name} not mapped to Kimai. Zammad type ID: {zammad_type_id}.",
        ReasonCode.DUPLICATE: "Duplicate entry for ticket {ticket_number} on {entry_date}.",
        ReasonCode.TIME_MISMATCH: "Time duration mismatch for ticket {ticket_number}: Zammad {zammad_minutes} min vs Kimai {kimai_minutes} min.",
        ReasonCode.PROJECT_OR_CUSTOMER_MISSING: "Missing project or customer mapping for organization {org_name}.",
        ReasonCode.LOCKED_OR_EXPORTED: "Kimai entry locked or exported, cannot update: ID {kimai_id}.",
        ReasonCode.CONFLICT: "Conflict between Zammad and Kimai entries for ticket {ticket_number} on {entry_date}.",
        ReasonCode.CREATION_ERROR: "Error creating timesheet in Kimai: {error_detail}.",
        ReasonCode.OTHER: "Other conflict - manual review required: {detail}.",
    }
    template = templates.get(code, templates[ReasonCode.OTHER])
    return template.format(**context, detail=context.get('detail', ''))
