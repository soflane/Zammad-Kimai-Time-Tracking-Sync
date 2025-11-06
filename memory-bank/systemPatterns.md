# System Patterns & Architecture

## High-Level Architecture

```
┌─────────────┐
│   Web UI    │  React 18 + Vite + TS
│ (Frontend)  │  Tailwind + shadcn/ui
└──────┬──────┘  TanStack Query + Axios
       │ HTTP/REST
       ▼
┌─────────────────────────────────────┐
│             FastAPI                │
│        (Backend Services)          │
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
│  Zammad  │────────▶│  Kimai   │
│ (Webhook)│         │          │
└──────────┘         └──────────┘
```

## Frontend UI Architecture (Single Page)

The UI is refactored into a single-page command center named `SyncDashboard` with anchored sections:
- Dashboard
- Connectors
- Mappings
- Reconcile
- Audit & History

Key patterns:
- Navigation: sticky top bar actions (Schedule, Run sync now) and left sidebar with in-page anchors. Router is kept minimal: `/login` and `/` (protected). All management happens on `/`.
- Components: shadcn/ui primitives (Button, Card, Dialog, Tabs, Table, Badge, Input, Switch, Select, Separator, Progress).
- Data: TanStack Query for server state; Axios service layer with strict types from `frontend/src/types/index.ts`. No API shape changes required.
- Charts/Visuals: Recharts for the KPI area chart; lucide-react icons; framer-motion for subtle entrance/hover effects.
- Section composition:
  - Dashboard: KPI stat cards, “Minutes synced (7d)” chart, recent runs list.
  - Connectors: Cards for Zammad/Kimai with status badges, Configure/Re-auth dialogs, “Test connection”.
  - Mappings: Searchable table with Create/Edit dialog; Export action.
  - Reconcile: Tabs (All/Matches/Missing/Conflicts); diff rows with inline actions and “Apply selected”.
  - Audit & History: Run history with progress bars and status badges.
- Query keys and invalidation map:
  - `["connectors"]`: CRUD in Connectors → invalidate on create/update/delete, test connection, re-auth.
  - `["mappings"]`: CRUD in Mappings → invalidate on create/update/delete/import/export.
  - `["conflicts", filter]`: resolve/ignore/apply-selected → invalidate current filter and `["auditLogs"]`, `["syncRuns"]`.
  - `["auditLogs"]`: invalidate after conflict resolutions and manual sync runs.
  - `["syncRuns"]`: invalidate after manual sync or schedule changes.
  - `["kpi"]`: derived from existing endpoints (sync runs, conflicts, mappings); recompute locally; re-fetch dependent queries and recompute on invalidations above.
- Error and toast pattern: Central toast hook (`use-toast`) for success/error; Axios interceptors map backend errors to human-readable messages.

## Core Design Patterns

### 1. Plugin Architecture (Strategy Pattern)
- Base class `BaseConnector` with concrete `ZammadConnector` and `KimaiConnector`.
- Additive: new connectors plug into the same interface without touching core.

### 2. Service Layer Pattern
- Normalizer, Reconciler, SyncService encapsulate business logic.
- API endpoints are thin; services are testable and reusable.

### 3. Repository Pattern (SQLAlchemy)
- Models define schema; queries centralized.
- Enables DB-agnostic evolution if needed.

### 4. DTOs (Pydantic Schemas)
- Input/output validation and OpenAPI documentation.

## Data Flow: Zammad → System → Kimai

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

## Reconciliation Logic

Matching strategy:
1. Exact match by source_id (if previously synced)
2. Match by ticket_number + date + time_unit
3. Fuzzy match by date range + similar duration

Conflict types:
- Duplicate, Mismatch, Missing

## Webhook vs Scheduled Sync

- Webhook: near real-time, HMAC-verified, single entry processing.
- Scheduled: periodic batches; catch-up and verification runs.
- The top bar “Schedule” dialog configures periodic syncs; “Run sync now” triggers manual sync.

## Data Normalization

Unified normalized entry (reference):

```python
{
    "source": "zammad",
    "source_id": "123",
    "ticket_number": "#50",
    "ticket_id": 50,
    "description": "Text",
    "time_minutes": 30.0,
    "activity_type_id": 3,
    "activity_name": "Support",
    "user_email": "user@domain",
    "entry_date": "2024-01-15",
    "created_at": "2024-01-15T10:00:00",
    "updated_at": "2024-01-15T10:00:00",
    "tags": ["billed:2024-01"]
}
```

## Security Considerations

- Encrypted credentials at rest.
- JWT-protected API.
- HMAC webhook verification.
- TLS for all external calls.
- Secrets via environment variables.

## Error Handling Strategy

- Retries with exponential backoff for API failures.
- Clear ValueError messages mapped to 4xx/5xx.
- UI toast surface for user-facing feedback.
- Audit trail records all mutation operations.

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
```

## SPA Navigation Model

- Routes:
  - `/login` → `Login` page
  - `/` → `Layout` + `SyncDashboard` (protected)
- In-page anchors for sections; URL fragments (e.g., `/#mappings`) supported for direct linking.
- Scroll position maintained; sticky headers for context.

## Scalability Considerations

Current (V1):
- Single instance
- Sequential processing
- Direct DB access

Future (V2+):
- Celery for async jobs
- Redis caching for connector configs and mappings
- Horizontal scaling behind a reverse proxy
- Virtualized long lists in UI sections (mappings, audit logs) when needed
