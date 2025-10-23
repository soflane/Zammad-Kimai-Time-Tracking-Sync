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

- **APScheduler**: Task scheduling
  - Cron-like scheduling
  - In-process scheduler (V1)
  - Can be replaced with Celery later for distributed tasks

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
  - Bcrypt algorithm
  - Secure credential storage

- **cryptography**: API token encryption
  - Fernet symmetric encryption
  - Secure credential storage in database

### Frontend
- **React** (18+): UI library
- **Vite**: Build tool and dev server
- **React Router** (v6): Client-side routing
- **TanStack Query**: Server state management
- **Axios**: HTTP client
- **Tailwind CSS**: Utility-first styling
- **Shadcn/UI**: Component library

### Database
- **PostgreSQL** (15+): Relational database
  - JSONB support for flexible data
  - Robust transaction handling
  - Excellent performance

### DevOps
- **Docker**: Containerization
- **Docker Compose**: Multi-container orchestration
- **Nginx**: Reverse proxy and static file serving

## Development Environment Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- Git

### Local Development

**Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

**Database:**
```bash
docker-compose up -d db
```

### Environment Variables

**Backend (.env):**
```
DATABASE_URL=postgresql://user:pass@localhost:5432/zammad_sync
SECRET_KEY=your-secret-key-here
ENCRYPTION_KEY=your-encryption-key-here
CORS_ORIGINS=http://localhost:5173
ADMIN_USERNAME=admin
ADMIN_PASSWORD=changeme
```

**Frontend (.env):**
```
VITE_API_URL=http://localhost:8000
```

## API Integration Details

### Zammad API
- **Base URL**: Configurable per installation
- **Authentication**: Bearer token (HTTP Token)
- **Key Endpoints**:
  - `GET /api/v1/tickets/{id}/time_accountings` - List time entries
  - `GET /api/v1/tickets/{id}/time_accountings/{aid}` - Get single entry
  - `POST /api/v1/tickets/{id}/time_accountings` - Create entry
  - `PUT /api/v1/tickets/{id}/time_accountings/{aid}` - Update entry
  - `DELETE /api/v1/tickets/{id}/time_accountings/{aid}` - Delete entry

- **Data Format**:
  ```json
  {
    "id": 6,
    "ticket_id": 50,
    "ticket_article_id": 87,
    "time_unit": "15.0",
    "type_id": 3,
    "created_by_id": 3,
    "created_at": "2023-08-16T08:11:49.315Z",
    "updated_at": "2023-08-16T08:11:49.315Z"
  }
  ```

- **Webhook Format**: HMAC-SHA1 signature in X-Zammad-Signature header

### Kimai API
- **Base URL**: Configurable per installation
- **Authentication**: Bearer token (API token from user profile)
- **Documentation**: Available at `/api/doc` on each instance
- **Key Endpoints**:
  - `GET /api/timesheets` - List timesheets
  - `POST /api/timesheets` - Create timesheet
  - `PATCH /api/timesheets/{id}` - Update timesheet
  - `DELETE /api/timesheets/{id}` - Delete timesheet
  - `GET /api/activities` - List activities
  - `GET /api/projects` - List projects

- **DateTime Format**: HTML5 local datetime (YYYY-MM-DDTHH:mm:ss)
- **Tags**: Array of strings, e.g., ["billed:2024-01", "internal"]

## Database Schema Notes

### Key Indexes
```sql
-- Performance indexes
CREATE INDEX idx_time_entries_source ON time_entries(source, source_id);
CREATE INDEX idx_time_entries_date ON time_entries(entry_date);
CREATE INDEX idx_time_entries_sync_status ON time_entries(sync_status);
CREATE INDEX idx_conflicts_resolution_status ON conflicts(resolution_status);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at DESC);
```

### Encryption Strategy
- API tokens stored encrypted using Fernet (symmetric encryption)
- Encryption key stored in environment variable
- Decrypted only when needed for API calls

## Testing Strategy (Future)

### Backend Tests
- **Unit Tests**: pytest for services and connectors
- **Integration Tests**: Test database operations
- **API Tests**: TestClient for endpoint testing

### Frontend Tests
- **Component Tests**: React Testing Library
- **E2E Tests**: Playwright for full workflows

## Performance Considerations

### Database
- Connection pooling (10 connections initially)
- Index on frequently queried fields
- JSONB for flexible connector settings

### API Calls
- Async HTTP clients for parallel requests
- Retry logic with exponential backoff
- Timeout settings (30s default)

### Caching (Future)
- Redis for connector configs and mappings
- Cache invalidation on updates
- TTL-based expiration

## Security Best Practices

1. **Never commit secrets**: Use .env files, add to .gitignore
2. **Encrypt sensitive data**: API tokens encrypted at rest
3. **Validate webhook signatures**: HMAC verification for Zammad
4. **Use HTTPS**: All external API calls over TLS
5. **JWT expiration**: Tokens expire after 24 hours
6. **Input validation**: Pydantic schemas validate all inputs
7. **SQL injection prevention**: SQLAlchemy ORM prevents injection
8. **CORS configuration**: Whitelist specific origins only

## Deployment Configuration

### Docker Compose Services
- **db**: PostgreSQL database
- **backend**: FastAPI application
- **frontend**: React application (built)
- **nginx**: Reverse proxy

### Health Checks
- Database: `pg_isready` command
- Backend: `/api/health` endpoint
- Frontend: Nginx status

### Logging
- Backend: Structured logging to stdout
- Nginx: Access and error logs to volumes
- Database: PostgreSQL logs

### Backup Strategy (Recommended)
- Daily database dumps
- Volume backups for postgres_data
- Config backup (.env files, encrypted)
