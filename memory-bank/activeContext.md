# Active Context

## Current Focus
Authentication system, base connector interface, Zammad connector, Kimai connector, connector API endpoints, and normalizer service are implemented. Ready to proceed with reconciliation engine.

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
5. **Implemented Authentication System**:
   - Created `backend/app/auth.py` for JWT token management and password hashing.
   - Created `backend/app/schemas/auth.py` for Pydantic authentication schemas.
   - Integrated authentication logic into `backend/app/main.py` with login endpoint and user retrieval.
   - Updated `backend/app/models/user.py` to match new schema (added `full_name`, `email`, renamed `password_hash` to `hashed_password`).
   - Updated `backend/app/config.py` to correctly define `ACCESS_TOKEN_EXPIRE_MINUTES`.
6. **Created Base Connector Interface**:
   - Defined `backend/app/connectors/base.py` with `BaseConnector` abstract class and `TimeEntryNormalized` Pydantic model.
7. **Implemented Zammad Connector**:
   - Created `backend/app/connectors/zammad_connector.py`, implementing `BaseConnector` methods for Zammad API interaction.
8. **Implemented Kimai Connector**:
   - Created `backend/app/connectors/kimai_connector.py`, implementing `BaseConnector` methods for Kimai API interaction.
9. **Created API Endpoints for Connectors**:
   - Created `backend/app/api/v1/endpoints/connectors.py` with validation and activity fetching endpoints.
   - Created `backend/app/api/v1/api.py` to include the `connectors` router.
   - Integrated `api_router` into `backend/app/main.py`.
10. **Built Normalizer Service**:
    - Created `backend/app/services/normalizer.py` with `NormalizerService` class for Zammad and Kimai entry normalization.

## Next Immediate Steps
1. Implement reconciliation engine

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
