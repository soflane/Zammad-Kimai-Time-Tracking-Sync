# Technical Context

## Technology Stack

### Backend
- **FastAPI** (0.104+): Modern Python web framework
  - Async support for better performance
  - Auto-generated OpenAPI documentation
  - Built-in data validation with Pydantic
  - Easy dependency injection

- **SQLAlchemy** (2.0+): ORM for database operations
  - Type-safe queries
  - Relationship management
  - Connection pooling

- **Alembic**: Database migration tool
  - Version-controlled schema changes
  - Automatic migration generation

- **APScheduler** (3.10.4): Task scheduling
  - Cron-like scheduling with AsyncIOScheduler
  - Dynamic job rescheduling via API
  - Concurrency handling (skip/queue modes)
  - In-process scheduler (V1)
  - Can be replaced with Celery later for distributed tasks

- **croniter** (2.0+): Cron expression parsing and validation
  - Used for schedule validation and next-run computation
  - Timezone-aware cron iteration

- **Pydantic** (2.0+): Data validation and serialization
  - Type hints for validation
  - JSON schema generation
  - Settings management

- **httpx**: Async HTTP client
  - Used for external API calls (Zammad, Kimai)
  - Timeout and retry support

- **python-jose**: JWT token handling
  - Token creation and validation
  - Secure authentication

- **passlib**: Password hashing
  - Bcrypt or pbkdf2_sha256
  - Secure credential storage

- **cryptography**: API token encryption
  - Fernet symmetric encryption
  - Secure credential storage in database

### Frontend
- **React** (18+) + **Vite**
- **TypeScript**
- **Tailwind CSS**
- **shadcn/ui** primitives (button, card, dialog, tabs, table, input, select, switch, badge, separator, progress)
- **TanStack Query** for server state
- **Axios** for HTTP client
- **React Router v6** (minimal routing: `/login` and `/`)
- **date-fns** for formatting
- New UI utilities for the single-page dashboard:
  - **lucide-react** icons
  - **recharts** for the KPI area chart
  - **framer-motion** for light transitions
  - **ScheduleDialog**: Scheduling configuration dialog with presets, validation, and preview

Single-page UI architecture:
- Route `/` renders `Layout` + `SyncDashboard` with anchored sections (`#dashboard`, `#connectors`, `#mappings`, `#reconcile`, `#audit`).
- Left sidebar provides anchor navigation; top bar exposes "Schedule" and "Run sync now".
- All CRUD operations (connectors, mappings, reconcile actions) occur via dialogs and inline buttons—no route changes.

Single-page UI architecture:
- Route `/` renders `Layout` + `SyncDashboard` with anchored sections (`#dashboard`, `#connectors`, `#mappings`, `#reconcile`, `#audit`).
- Left sidebar provides anchor navigation; top bar exposes “Schedule” and “Run sync now”.
- All CRUD operations (connectors, mappings, reconcile actions) occur via dialogs and inline buttons—no route changes.

### Database
- **PostgreSQL** (15+)
  - JSONB support
  - Robust transaction handling
  - Excellent performance

### DevOps
- **Docker** and **Docker Compose**
- **Nginx** as reverse proxy and static file server

## Development Environment Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- Git

### Local Development

Backend:
```bash
cd backend
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
# source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

Frontend:
```bash
cd frontend
npm install
npm run dev
```

Database:
```bash
docker-compose up -d db
```

### Environment Variables

Backend (.env):
```
DATABASE_URL=postgresql://user:pass@localhost:5432/zammad_sync
SECRET_KEY=your-secret-key-here
ENCRYPTION_KEY=your-encryption-key-here
CORS_ORIGINS=http://localhost:5173
ADMIN_USERNAME=admin
ADMIN_PASSWORD=changeme
```

Frontend (.env):
```
VITE_API_URL=http://localhost:8000
```

## API Integration Details

Important: Do not change API shapes for the UI refactor. The service layer and types are the contract.
- Service layer: `frontend/src/services/api.service.ts`
- Types: `frontend/src/types/index.ts`

### Zammad API
- Auth: HTTP Token
- Key endpoints:
  - GET `/api/v1/tickets/{id}/time_accountings`
  - GET `/api/v1/tickets/{id}/time_accountings/{aid}`
  - POST `/api/v1/tickets/{id}/time_accountings`
  - PUT `/api/v1/tickets/{id}/time_accountings/{aid}`
  - DELETE `/api/v1/tickets/{id}/time_accountings/{aid}`
- Webhook: HMAC-SHA1 signature header

### Kimai API
- Auth: API token
- Docs at `/api/doc`
- Key endpoints:
  - GET `/api/timesheets`
  - POST `/api/timesheets`
  - PATCH `/api/timesheets/{id}`
  - DELETE `/api/timesheets/{id}`
  - GET `/api/activities`
  - GET `/api/projects`
- Datetime: HTML5 local datetime (YYYY-MM-DDTHH:mm:ss)
- Tags: comma-separated string (e.g., `source:zammad`)

## Database Schema Notes

Key indexes:
```sql
CREATE INDEX idx_time_entries_source ON time_entries(source, source_id);
CREATE INDEX idx_time_entries_date ON time_entries(entry_date);
CREATE INDEX idx_time_entries_sync_status ON time_entries(sync_status);
CREATE INDEX idx_conflicts_resolution_status ON conflicts(resolution_status);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at DESC);
```

Encryption strategy:
- Tokens encrypted with Fernet; key in env var; decrypt only on use

## Frontend Data Access and Caching

TanStack Query setup:
- Axios instance uses `VITE_API_URL`
- Suggested query keys:
  - `["kpi"]`
  - `["syncRuns"]`
  - `["connectors"]`
  - `["mappings"]`
  - `["conflicts", filter]`
  - `["auditLogs"]`
- Invalidation rules:
  - Connector CRUD/test/re-auth → `["connectors"]`, `["kpi"]`
  - Mapping CRUD/import/export → `["mappings"]`, `["kpi"]`
  - Reconcile actions → `["conflicts", filter]`, `["auditLogs"]`, `["syncRuns"]`, `["kpi"]`
  - Manual run/schedule change → `["syncRuns"]`, `["kpi"]`

## Testing Strategy (Future)

Backend:
- pytest unit tests for services/connectors
- Integration tests for DB and API
- Webhook validation tests

Frontend:
- React Testing Library for components
- Playwright E2E for single-page flows (connectors → mappings → reconcile → audit)

## Performance Considerations

Database:
- Pooling; indexes on hot fields
- JSONB for flexible connector settings

API Calls:
- Async/parallel external requests
- Retries with backoff
- 30s timeout defaults

Caching (Future):
- Redis for connector configs/mappings
- Cache invalidation on updates

## Security Best Practices

1. No committed secrets
2. Encrypt tokens at rest
3. Verify webhook signatures
4. TLS for all external calls
5. JWT expiration policy
6. Input validation everywhere
7. Prefer ORM queries to avoid injection
8. CORS restricted to known origins

## Deployment Configuration

Docker Compose services:
- db, backend, frontend, nginx

Health checks:
- pg_isready for DB
- `/api/health` for backend
- Nginx status

Logging:
- Structured backend logs to stdout
- Nginx access/error logs
- Postgres logs

Backup strategy:
- Daily DB dumps
- Volume backups
- Config backups (.env, encrypted)

## Development Environment Notes

Windows local development:
- Frontend: `cd frontend && npm run dev`
- Backend: `cd backend && uvicorn app.main:app --reload`
- Vite dev server on 5173; backend on 8000; `/api` proxied by Vite (see `vite.config.ts`)
- PowerShell uses `;` for chaining; `cmd.exe` supports `&&`

Routing model for SPA:
- `/login` → auth flow
- `/` → `SyncDashboard` single page with anchors
- Keep existing pages for now during transition; final state should prefer single dashboard component
