# Zammad-Kimai Time Tracking Sync

A synchronization service with web UI that normalizes and reconciles time tracking entries between Zammad (ticketing system) and Kimai (time tracking), with support for future connectors.

## Features

- 🔄 **One-way Sync**: Automatically sync time entries from Zammad to Kimai
- 🔍 **Intelligent Reconciliation**: Detect duplicates, mismatches, and missing entries
- ⚡ **Real-time Updates**: Webhook support for immediate sync when tickets are updated
- 📅 **Scheduled Sync**: Periodic batch synchronization as backup
- 🎯 **Activity Mapping**: Configure how Zammad activity types map to Kimai activities
- ⚠️ **Conflict Resolution**: Web UI to review and resolve sync conflicts
- 📊 **Audit Trail**: Complete history of all operations
- 🔌 **Plugin Architecture**: Easy to add new connectors in the future
- 🐳 **Docker Ready**: Full Docker Compose setup for easy deployment

## Architecture

```
┌─────────────┐
│   Web UI    │ (React + Vite)
└──────┬──────┘
       │ REST API
       ▼
┌─────────────────────────────┐
│   FastAPI Backend          │
│  - Connector Plugins       │
│  - Reconciliation Engine   │
│  - Sync Service            │
└────────┬────────────────────┘
         │
         ▼
    ┌──────────┐
    │PostgreSQL│
    └──────────┘

External: Zammad ──webhook──> System ──sync──> Kimai
```

## Tech Stack

**Backend:**
- FastAPI (Python 3.11+)
- SQLAlchemy + Alembic
- PostgreSQL
- APScheduler
- httpx (async HTTP client)

**Frontend:**
- React 18+
- Vite
- TanStack Query
- Tailwind CSS
- Shadcn/UI

**Deployment:**
- Docker & Docker Compose
- Nginx

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── api/              # API endpoints
│   │   ├── connectors/       # Plugin system (Zammad, Kimai)
│   │   ├── models/           # Database models
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── services/         # Business logic
│   │   ├── tasks/            # Scheduled tasks
│   │   ├── config.py
│   │   ├── database.py
│   │   └── main.py
│   ├── alembic/              # Database migrations
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── api/
│   ├── package.json
│   └── Dockerfile
├── memory-bank/              # Project documentation
├── docker-compose.yml
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+ (or use Docker)
- Docker & Docker Compose (for deployment)

### Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Zammad-TimeTracking-Sync
   ```

2. **Backend Setup**
   ```bash
   cd backend
   
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Create .env file
   cp .env.example .env
   # Edit .env with your configuration
   
   # Run database migrations
   alembic upgrade head
   
   # Start development server
   uvicorn app.main:app --reload
   ```

3. **Frontend Setup** (coming soon)
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

4. **Access the Application**
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/api/docs
   - Frontend: http://localhost:5173 (when available)

### Docker Deployment

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Configuration

### Environment Variables

Create a `.env` file in the `backend/` directory:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/zammad_sync

# Security
SECRET_KEY=your-secret-key-here
ENCRYPTION_KEY=your-encryption-key-here

# CORS
CORS_ORIGINS=http://localhost:5173

# Admin User
ADMIN_USERNAME=admin
ADMIN_PASSWORD=changeme

# Sync Schedule
SYNC_SCHEDULE_HOURS=6
```

### Connector Setup

1. **Zammad Configuration**
   - Base URL: Your Zammad installation URL
   - API Token: Generate from Zammad user profile
   - Activity Types: Configure mappings in the web UI

2. **Kimai Configuration**
   - Base URL: Your Kimai installation URL
   - API Token: Generate from Kimai user profile (Settings → API)
   - Activities: Map to Zammad activity types

## API Endpoints

### Authentication
- `POST /api/auth/login` - Login and get JWT token

### Connectors
- `GET /api/connectors` - List all connectors
- `POST /api/connectors` - Create new connector
- `PUT /api/connectors/{id}` - Update connector
- `DELETE /api/connectors/{id}` - Delete connector
- `POST /api/connectors/{id}/test` - Test connection

### Mappings
- `GET /api/mappings` - List activity mappings
- `POST /api/mappings` - Create mapping
- `PUT /api/mappings/{id}` - Update mapping
- `DELETE /api/mappings/{id}` - Delete mapping

### Sync
- `POST /api/sync/manual` - Trigger manual sync
- `GET /api/sync/status` - Get current sync status
- `GET /api/sync/history` - List sync runs

### Conflicts
- `GET /api/conflicts` - List pending conflicts
- `POST /api/conflicts/{id}/resolve` - Resolve conflict

### Audit
- `GET /api/audit` - List audit logs

### Webhook
- `POST /api/webhook/zammad` - Zammad webhook endpoint

## Development Roadmap

### Phase 1: Backend Foundation ✅ (Current)
- [x] Project structure
- [x] Database models
- [x] Alembic migrations
- [x] FastAPI app skeleton
- [ ] Authentication system
- [ ] Base connector interface

### Phase 2: Connector Implementation
- [ ] Zammad connector
- [ ] Kimai connector
- [ ] Normalizer service
- [ ] Connection validation

### Phase 3: Sync & Reconciliation
- [ ] Reconciliation engine
- [ ] Sync service
- [ ] Conflict detection
- [ ] Scheduled tasks

### Phase 4: API Endpoints
- [ ] Complete all REST endpoints
- [ ] Webhook handler
- [ ] Error handling

### Phase 5: Frontend
- [ ] React setup
- [ ] Authentication UI
- [ ] Dashboard
- [ ] Connector management
- [ ] Mapping configuration
- [ ] Conflict resolution UI
- [ ] Audit log viewer

### Phase 6: Docker & Deployment
- [ ] Dockerfiles
- [ ] Docker Compose
- [ ] Nginx configuration
- [ ] Production setup guide

### Phase 7: Testing & Polish
- [ ] Integration tests
- [ ] Error handling
- [ ] Performance optimization
- [ ] Documentation

## Contributing

Contributions are welcome! Please read our contributing guidelines before submitting PRs.

## Production Features

### CI/CD Pipeline
- ✅ **GitHub Actions**: Automated testing and deployment
- ✅ **Multi-arch Builds**: Support for amd64 and arm64
- ✅ **Container Registry**: Automatic push to GitHub Container Registry (GHCR)
- ✅ **Dependency Updates**: Dependabot for automated security updates
- ✅ **Security Scanning**: Trivy vulnerability scanner integrated

### Security & Compliance
- 🔒 **Encryption**: API tokens encrypted at rest with Fernet
- 🔐 **Authentication**: JWT tokens with bcrypt password hashing
- 🛡️ **GDPR Ready**: Data export and purge endpoints
- ✅ **Security Policy**: Vulnerability reporting process
- 📝 **Audit Trail**: Complete logging of all operations

### Developer Experience
- 📋 **Issue Templates**: Bug reports and feature requests
- 🔄 **PR Template**: Standardized pull request format
- 📚 **Documentation**: Architecture, security, and roadmap docs
- 🧪 **Testing**: Automated CI pipeline with coverage reporting

## License

MIT License - see [LICENSE](LICENSE) file for details

## Support

For issues and questions:
- Create an issue in the repository
- Check the documentation in `memory-bank/`

## Acknowledgments

- Zammad API Documentation
- Kimai API Documentation
