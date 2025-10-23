# System Patterns & Architecture

## High-Level Architecture

```
┌─────────────┐
│   Web UI    │ (React + Vite)
│  (Frontend) │
└──────┬──────┘
       │ HTTP/REST
       ▼
┌─────────────────────────────────────┐
│     FastAPI Backend                 │
│  ┌──────────────────────────────┐  │
│  │      API Endpoints           │  │
│  └──────────────────────────────┘  │
│  ┌──────────────────────────────┐  │
│  │   Business Services          │  │
│  │  - Normalizer                │  │
│  │  - Reconciler                │  │
│  │  - Sync Service              │  │
│  └──────────────────────────────┘  │
│  ┌──────────────────────────────┐  │
│  │   Connector Plugins          │  │
│  │  - Zammad Connector          │  │
│  │  - Kimai Connector           │  │
│  └──────────────────────────────┘  │
└───────────┬─────────────────────────┘
            │
            ▼
    ┌──────────────┐
    │  PostgreSQL  │
    │   Database   │
    └──────────────┘

External Systems:
┌──────────┐         ┌──────────┐
│  Zammad  │────────▶│  System  │
│ (Webhook)│         │          │
└──────────┘         └──────────┘
```

## Core Design Patterns

### 1. Plugin Architecture (Strategy Pattern)
- **Abstract Base Class**: `BaseConnector` defines interface
- **Concrete Implementations**: `ZammadConnector`, `KimaiConnector`
- **Benefits**: Easy to add new connectors without modifying core logic
- **Implementation**: Each connector implements fetch, create, update, delete methods

### 2. Service Layer Pattern
- **Separation**: Business logic isolated from API endpoints
- **Services**: Normalizer, Reconciler, SyncService, ConflictResolver
- **Benefits**: Testable, reusable, maintainable

### 3. Repository Pattern (via SQLAlchemy ORM)
- **Models**: Define database schema
- **Queries**: Centralized in model classes
- **Benefits**: Database abstraction, easier to switch DB if needed

### 4. Data Transfer Objects (Pydantic Schemas)
- **Validation**: Automatic data validation
- **Serialization**: JSON conversion
- **Documentation**: Auto-generated API docs

## Key Technical Decisions

### Data Flow: Zammad → System → Kimai

```
Zammad Time Accounting
        ↓
   [Webhook/Poll]
        ↓
  Zammad Connector
        ↓
    Normalizer → Unified Format
        ↓
  Store in Database
        ↓
    Reconciler
        ↓
    ┌─────────┴─────────┐
    ▼                   ▼
Conflicts          Clear Matches
    ↓                   ↓
Manual Review      Auto-Sync
    ↓                   ↓
Resolution    →   Kimai Connector
                        ↓
                  Create/Update
                        ↓
                 Kimai Timesheet
```

### Reconciliation Logic

**Matching Strategy:**
1. Exact match by source_id (if previously synced)
2. Match by ticket_number + date + time_unit
3. Fuzzy match by date range + similar duration

**Conflict Types:**
- **Duplicate**: Entry exists in both systems with same data
- **Mismatch**: Same entry but different values (time, activity type)
- **Missing**: Entry in Zammad but not in Kimai (needs sync)

### Webhook vs Scheduled Sync

**Webhook (Real-time):**
- Triggered when Zammad ticket updated
- HMAC signature verification for security
- Immediate processing of single entry
- Used for: Individual ticket updates

**Scheduled (Periodic):**
- Runs every X hours (configurable)
- Fetches all entries in date range
- Batch reconciliation
- Used for: Catch-all, recovery, verification

### Data Normalization

**Unified Time Entry Format:**
```python
{
    "source": "zammad",           # Source system
    "source_id": "123",            # Original ID
    "ticket_number": "#50",        # Ticket reference
    "ticket_id": 50,               # Numeric ticket ID
    "description": "Text",         # Entry description
    "time_minutes": 30.0,          # Duration in minutes
    "activity_type_id": 3,         # Activity type ID
    "activity_name": "Support",    # Activity name
    "user_email": "user@domain",   # User identifier
    "entry_date": "2024-01-15",    # Date of work
    "created_at": "2024-01-15T10:00:00",
    "updated_at": "2024-01-15T10:00:00",
    "tags": ["billed:2024-01"]     # Optional tags
}
```

### Security Considerations

1. **Credential Storage**: API tokens encrypted in database using cryptography library
2. **Authentication**: JWT tokens for API access
3. **Webhook Verification**: HMAC signature validation for Zammad webhooks
4. **HTTPS**: All external API calls over TLS
5. **Environment Variables**: Sensitive config in .env files, not committed

### Error Handling Strategy

1. **API Errors**: Retry with exponential backoff
2. **Connection Failures**: Log and alert, continue with next sync
3. **Data Validation Errors**: Store in error log, flag for review
4. **Sync Failures**: Roll back transaction, preserve data integrity

## Component Relationships

### Database Relationships
```
connectors (1) ──────────────────> (N) time_entries
                                          │
activity_mappings ──────────────> (N) time_entries
                                          │
time_entries (1) ──────────────────> (1) conflicts
                                          │
sync_runs (1) ────────────────────> (N) audit_logs
```

### Service Dependencies
```
SyncService
    ├─> ZammadConnector
    ├─> KimaiConnector
    ├─> Normalizer
    ├─> Reconciler
    └─> AuditLogger

Reconciler
    ├─> TimeEntryRepository
    └─> ConflictDetector

ConflictResolver
    ├─> KimaiConnector
    └─> AuditLogger
```

## Scalability Considerations

### Current Design (V1)
- Single instance deployment
- Sequential sync processing
- Direct database queries

### Future Scalability (V2+)
- **Task Queue**: Celery for async job processing
- **Caching**: Redis for frequently accessed data (mappings, connector configs)
- **Horizontal Scaling**: Multiple backend instances behind load balancer
- **Batch Processing**: Process large sync operations in chunks
