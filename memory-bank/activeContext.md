# Active Context

## Current Focus
Backend foundation complete! Database models, migrations setup, and FastAPI skeleton are ready.

## Recent Actions
1. Created comprehensive memory bank documentation
2. Set up complete backend project structure:
   - All database models (User, Connector, TimeEntry, ActivityMapping, SyncRun, Conflict, AuditLog)
   - Alembic migration configuration
   - FastAPI application skeleton with CORS
   - Configuration management with Pydantic Settings
   - Requirements.txt with all dependencies
3. Created project documentation (README.md, .gitignore, LICENSE, SECURITY.md, ARCHITECTURE.md, ROADMAP.md)
4. Implemented CI/CD infrastructure:
   - GitHub Actions workflows (lint, test, build, deploy)
   - Dependabot configuration for automated dependency updates
   - Issue and PR templates
   - Security scanning with Trivy
   - Multi-arch Docker builds (amd64, arm64)
   - Container registry integration (GHCR)

## Next Immediate Steps
1. Create authentication system (JWT, password hashing)
2. Create base connector interface (abstract class)
3. Implement Zammad connector
4. Implement Kimai connector
5. Create API endpoints for connectors
6. Build normalizer service
7. Implement reconciliation engine

## Active Decisions

### Project Structure
Using a monorepo approach with separate backend/ and frontend/ directories:
- `backend/` - Python FastAPI application
- `frontend/` - React + Vite application
- `docker-compose.yml` - Orchestration at root
- `memory-bank/` - Project documentation

### Database First Approach
Starting with solid database foundation:
1. Define SQLAlchemy models
2. Create initial Alembic migration
3. Set up database connection
4. Then build services on top

### API-First Design
FastAPI's automatic OpenAPI docs will serve as the contract between frontend and backend, allowing parallel development.

## Important Patterns to Follow

### Connector Development
Each connector must:
- Inherit from BaseConnector abstract class
- Implement all required methods (fetch, create, update, delete, validate)
- Handle its own authentication
- Return normalized data in standard format
- Include proper error handling with retries

### Data Normalization
All time entries flow through normalizer service before storage:
- Zammad format → Normalized format → Database
- Kimai format → Normalized format → Database
- Ensures consistency for reconciliation

### Error Handling
- External API calls: Retry with exponential backoff (3 attempts)
- Database operations: Transaction rollback on errors
- Validation errors: Return clear error messages
- Log all errors for debugging

## Configuration Management
- Sensitive data (API tokens): Encrypted in database
- Application config: Environment variables
- User preferences: Database tables
- Constants: Python config module

## Development Workflow
1. Create feature in backend first
2. Test with FastAPI auto-docs (/docs)
3. Create corresponding frontend component
4. Test end-to-end workflow
5. Document in memory bank if significant

## Key Learnings
- Zammad time_unit is in minutes (not hours)
- Kimai requires HTML5 datetime format (no timezone)
- Activity type mapping is critical for proper sync
- Webhook requires HMAC verification for security
- Tags in Kimai use format "billed:YYYY-MM" for billing status
