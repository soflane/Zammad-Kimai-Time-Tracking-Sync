# Architecture Documentation

## System Overview

Zammad-Kimai Time Tracking Sync is a microservices-based application that synchronizes time tracking data between Zammad (ticketing system) and Kimai (time tracking) with a plugin-based connector architecture.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       User Interface                         │
│                   (React + Vite + Tailwind)                  │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTPS/REST
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                      Nginx Reverse Proxy                     │
│              (SSL Termination, Static Files)                 │
└────────────┬───────────────────────────────┬────────────────┘
             │                               │
             ▼                               ▼
┌────────────────────────┐        ┌────────────────────────┐
│   Backend API          │        │   Static Frontend      │
│   (FastAPI/Python)     │        │   (Built React)        │
│                        │        └────────────────────────┘
│  ┌──────────────────┐ │
│  │  API Endpoints   │ │
│  └──────────────────┘ │
│  ┌──────────────────┐ │
│  │  Services Layer  │ │
│  │  - Normalizer    │ │
│  │  - Reconciler    │ │
│  │  - Sync Service  │ │
│  └──────────────────┘ │
│  ┌──────────────────┐ │
│  │ Connector Plugin │ │
│  │  - Zammad        │ │
│  │  - Kimai         │ │
│  └──────────────────┘ │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│   PostgreSQL Database  │
│   - Time Entries       │
│   - Connectors         │
│   - Mappings           │
│   - Conflicts          │
│   - Audit Logs         │
└────────────────────────┘

External Systems:
┌──────────┐  webhook   ┌──────────┐
│  Zammad  │─────────────▶│  System  │
└──────────┘             └──────────┘
                              │
                              │ sync
                              ▼
                         ┌──────────┐
                         │  Kimai   │
                         └──────────┘
```

## Component Architecture

### 1. Frontend (React + Vite)

**Technology Stack:**
- React 18 for UI components
- Vite for fast development and building
- TanStack Query for server state management
- React Router for navigation
- Tailwind CSS for styling
- Shadcn/UI for pre-built components

**Structure:**
```
frontend/src/
├── components/          # Reusable UI components
│   ├── layout/         # Header, Sidebar, Layout
│   ├── connectors/     # Connector management
│   ├── mappings/       # Activity mappings
│   ├── sync/           # Sync controls & history
│   ├── conflicts/      # Conflict resolution
│   └── audit/          # Audit log viewer
├── pages/              # Route pages
├── api/                # API client with auth
├── hooks/              # Custom React hooks
├── utils/              # Utility functions
└── App.jsx             # Main app component
```

### 2. Backend (FastAPI/Python)

**Technology Stack:**
- FastAPI for REST API
- SQLAlchemy for ORM
- Alembic for migrations
- Pydantic for validation
- httpx for async HTTP
- APScheduler for cron jobs
- cryptography for encryption

**Layered Architecture:**

#### API Layer (`app/api/`)
- REST endpoints organized by resource
- Input validation with Pydantic schemas
- Authentication middleware
- Error handling

#### Services Layer (`app/services/`)
- Business logic separated from API
- Normalizer: Transforms data formats
- Reconciler: Matches and detects conflicts
- SyncService: Orchestrates sync operations
- ConflictResolver: Handles conflict resolution

#### Connector Layer (`app/connectors/`)
- Plugin-based architecture
- BaseConnector abstract class
- Each connector implements:
  - `fetch()`: Retrieve time entries
  - `create()`: Create new entries
  - `update()`: Modify entries
  - `delete()`: Remove entries
  - `validate()`: Test connection

#### Data Layer (`app/models/`)
- SQLAlchemy models
- Database schema definitions
- Relationships and indexes

### 3. Database (PostgreSQL)

**Schema Design:**

```sql
-- Core tables
┌─────────────┐
│   users     │  (Authentication)
└─────────────┘

┌─────────────┐       ┌──────────────┐
│ connectors  │──────▶│ time_entries │
└─────────────┘       └───────┬──────┘
                              │
┌──────────────────┐          │
│ activity_mappings│          │
└──────────────────┘          ▼
                      ┌──────────────┐
                      │  conflicts   │
                      └──────────────┘

┌─────────────┐
│ sync_runs   │  (History)
└─────────────┘

┌─────────────┐
│ audit_logs  │  (Compliance)
└─────────────┘
```

**Indexes:**
- `time_entries(source, source_id)` - Unique constraint
- `time_entries(entry_date)` - Date queries
- `time_entries(sync_status)` - Status filtering
- `conflicts(resolution_status)` - Conflict queries
- `audit_logs(created_at DESC)` - Recent logs

## Data Flow

### Sync Process

```
1. Trigger (Webhook or Schedule)
        ↓
2. Fetch from Zammad
   GET /api/v1/tickets/{id}/time_accountings
        ↓
3. Normalize Data
   Transform to unified format
        ↓
4. Store in Database
   time_entries table
        ↓
5. Reconciliation
   Compare with existing Kimai data
        ↓
   ┌────┴────┐
   ▼         ▼
Conflict   Match
   ↓         ↓
Manual    Auto-sync
Review       ↓
   ↓         ▼
Resolve  Create/Update in Kimai
   ↓    POST /api/timesheets
   ↓         ↓
   └────┬────┘
        ▼
6. Audit Log
   Record all operations
```

### Normalization Process

**Input (Zammad):**
```json
{
  "id": 6,
  "ticket_id": 50,
  "time_unit": "15.0",
  "type_id": 3,
  "created_at": "2025-08-16T08:11:49.315Z"
}
```

**Normalized:**
```json
{
  "source": "zammad",
  "source_id": "6",
  "ticket_number": "#50",
  "ticket_id": 50,
  "time_minutes": 15.0,
  "activity_type_id": 3,
  "entry_date": "2025-08-16",
  "created_at": "2025-08-16T08:11:49.315Z"
}
```

**Output (Kimai):**
```json
{
  "begin": "2025-08-16T08:00:00",
  "end": "2025-08-16T08:15:00",
  "project": 1,
  "activity": 5,
  "description": "Ticket #50",
  "tags": ["zammad", "synced"]
}
```

## Security Architecture

### Authentication Flow

```
1. User Login
   POST /api/auth/login
   { username, password }
        ↓
2. Validate Credentials
   bcrypt.verify(password, hash)
        ↓
3. Generate JWT
   jwt.encode({ user_id, exp })
        ↓
4. Return Token
   { access_token, token_type }
        ↓
5. Subsequent Requests
   Authorization: Bearer <token>
        ↓
6. Validate Token
   jwt.decode(token, secret_key)
        ↓
7. Process Request
```

### Data Encryption

**At Rest:**
- API tokens encrypted with Fernet (symmetric)
- Passwords hashed with bcrypt
- Encryption key from environment variable

**In Transit:**
- HTTPS/TLS for all external communication
- Internal Docker network for services

### GDPR Compliance

**Data Minimization:**
- Store only essential fields
- No unnecessary personal data
- Configurable retention periods

**User Rights:**
- Export: `GET /api/gdpr/export`
- Purge: `DELETE /api/gdpr/purge`
- Audit: Complete trail in `audit_logs`

## Deployment Architecture

### Docker Compose (Development)

```yaml
services:
  db:         # PostgreSQL database
  backend:    # FastAPI application
  frontend:   # Development server (Vite)
  nginx:      # Reverse proxy
```

### Docker Compose (Production)

```yaml
services:
  db:         # PostgreSQL with volume
  backend:    # Built backend container
  frontend:   # Built static files
  nginx:      # SSL termination + proxy
```

### Container Architecture

```
┌─────────────────────────────────────┐
│           nginx:alpine              │
│  - SSL termination                  │
│  - Reverse proxy                    │
│  - Static file serving              │
│  Ports: 80, 443                     │
└────────────┬────────────────────────┘
             │
    ┌────────┴────────┐
    ▼                 ▼
┌────────────┐  ┌─────────────┐
│  backend   │  │  frontend   │
│  (Python)  │  │  (Built)    │
│  Port:8000 │  │  /dist/     │
└─────┬──────┘  └─────────────┘
      │
      ▼
┌────────────┐
│ postgres:15│
│ Port: 5432 │
│ Volume:    │
│ postgres_  │
│ data       │
└────────────┘
```

## Scalability Considerations

### Current Design (V1)
- Single backend instance
- Sequential sync processing
- Direct database queries
- APScheduler for cron jobs

### Future Improvements (V2+)

**Horizontal Scaling:**
- Multiple backend instances
- Load balancer (nginx/HAProxy)
- Shared database connection pool

**Background Jobs:**
- Replace APScheduler with Celery
- Redis for task queue
- Separate worker containers
- Distributed task processing

**Caching:**
- Redis for session storage
- Cache frequently accessed data
- Reduce database load

**Database:**
- Read replicas for queries
- Connection pooling optimization
- Partitioning for large tables

## Monitoring & Observability

### Logging
- Structured JSON logs
- Log levels: DEBUG, INFO, WARNING, ERROR
- Centralized logging (stdout → Docker logs)

### Metrics (Future)
- OpenTelemetry for tracing
- Prometheus for metrics
- Grafana for visualization

### Health Checks
- `/api/health` - Application status
- Database connectivity check
- External API availability

### Audit Trail
- All operations logged to `audit_logs`
- User actions tracked
- Data changes recorded
- Retention policy configurable

## API Design

### REST Principles
- Resource-based URLs
- HTTP methods (GET, POST, PUT, DELETE)
- Status codes (200, 201, 400, 401, 404, 500)
- JSON request/response

### Versioning
- URL-based: `/api/v1/`
- Backward compatibility in minor versions
- Breaking changes require major version

### Documentation
- Auto-generated with FastAPI
- OpenAPI 3.0 specification
- Interactive docs at `/api/docs`
- ReDoc at `/api/redoc`

## Error Handling

### Error Response Format
```json
{
  "detail": "Error message",
  "status_code": 400,
  "timestamp": "2024-01-15T10:00:00Z",
  "request_id": "uuid"
}
```

### Error Categories
- Validation errors (400)
- Authentication errors (401)
- Authorization errors (403)
- Not found errors (404)
- Server errors (500)
- External API errors (502)

## Testing Strategy

### Backend Tests
- Unit tests: pytest
- Integration tests: TestClient
- Database tests: pytest-postgresql
- API tests: httpx

### Frontend Tests
- Component tests: React Testing Library
- E2E tests: Playwright
- Visual regression: Chromatic (future)

### CI/CD Testing
- Automated on every PR
- Coverage reporting
- Performance benchmarks

## Performance Optimization

### Database
- Indexes on frequently queried columns
- Connection pooling (10-20 connections)
- Query optimization
- Bulk operations for sync

### API
- Async endpoints with FastAPI
- Pagination for large results
- Response compression
- ETags for caching

### Frontend
- Code splitting
- Lazy loading
- Asset optimization
- CDN for static files (future)

## Disaster Recovery

### Backups
- Automated daily database backups
- Retention: 30 days
- Encrypted backups
- Offsite storage

### Recovery
- Database restore procedures
- Configuration backup
- Disaster recovery plan
- RTO: 4 hours, RPO: 24 hours

---

For implementation details, see source code comments and inline documentation.
