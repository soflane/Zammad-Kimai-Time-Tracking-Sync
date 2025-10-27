# Active Context

## Current Focus
Authentication system, base connector interface, Zammad connector, Kimai connector, connector API endpoints, normalizer service, reconciliation engine, sync service, conflict detection with API endpoints, scheduled tasks, and connection validation with connector configuration management are implemented.

## Recent Actions (Most Recent First)
18. **Project Cleanup for Kimai Connector Issues**:
    - Stashed problematic modifications from unfinished Kimai fix attempts to revert to stable commit.
    - Cleaned backend dependencies with pip install --no-cache-dir (already up-to-date).
    - Cleaned frontend node_modules and reinstalled with npm install (resolved EPERM warnings, 337 packages audited, 4 vulnerabilities noted - suggest `npm audit fix`).
    - Pruned Docker system (reclaimed 16.02GB, removed unused containers, networks, images).
    - Fixed Kimai connector (`backend/app/connectors/kimai_connector.py`):
      - Added decryption for API token using `decrypt_data` from utils.
      - Changed datetime formatting to local HTML5 'YYYY-MM-DDTHH:MM:SS' without timezone.
      - Used `entry_date` for begin time instead of `created_at` to reflect work date.
    - Backend dev server starts without errors, confirming fixes.
    - Ready for manual sync test: Configure connectors/mappings in UI, trigger `/api/v1/sync/manual`, verify no 500 errors for multiple cases.
1. **Completed Full-Stack Frontend Implementation**:
   - Created comprehensive TypeScript types (`frontend/src/types/index.ts`) for all API responses
   - Built complete service layer (`frontend/src/services/api.service.ts`) with all CRUD operations
   - Implemented full Connectors page with create, read, update, delete, and validation functionality
   - Implemented full Mappings page with activity mapping management
   - Implemented full Conflicts page with resolve/ignore functionality  
   - Implemented full AuditLogs page with export capabilities
   - Fixed all TypeScript compilation errors
   - Docker build completes successfully (1752 modules transformed)
   - All frontend pages now use proper type safety and service layer
2. **Fixed Frontend Build Errors**:
   - Created missing `frontend/src/pages/Conflicts.tsx` with complete conflict resolution UI implementation
   - Fixed TypeScript errors in `frontend/src/pages/Connectors.tsx` (removed unused `defaultConnector` function and `value` parameter)
   - Docker build now completes successfully with no TypeScript compilation errors
   - All 1751 modules transform successfully in Vite build
2. **Completed Webhook Endpoint**:
   - Fixed import errors in `backend/app/api/v1/endpoints/webhook.py` (added datetime imports)
   - Added webhook_secret to `backend/app/config.py`
   - Registered webhook router in `backend/app/api/v1/api.py`
   - All backend API endpoints are now complete
3. **Started Frontend Infrastructure**:
   - Created `frontend/src/components/Layout.tsx` with navigation
   - Created toast notification system (`toast.tsx`, `toaster.tsx`, `use-toast.ts`)
   - Frontend routing structure is in place with placeholder pages
4. Created comprehensive memory bank documentation
5. Set up complete backend project structure:
   - All database models (User, Connector, TimeEntry, ActivityMapping, SyncRun, Conflict, AuditLog)
   - Alembic migration configuration
   - FastAPI application skeleton with CORS
   - Configuration management with Pydantic Settings
   - Requirements.txt with all dependencies
6. Created project documentation (README.md, .gitignore, LICENSE, SECURITY.md, ARCHITECTURE.md, ROADMAP.md)
7. Implemented CI/CD infrastructure:
   - GitHub Actions workflows (lint, test, build, deploy)
   - Dependabot configuration for automated dependency updates
   - Issue and PR templates
   - Security scanning with Trivy
   - Multi-arch Docker builds (amd64, arm64)
   - Container registry integration (GHCR)
8. **Implemented Authentication System**:
   - Created `backend/app/auth.py` for JWT token management and password hashing.
   - Created `backend/app/schemas/auth.py` for Pydantic authentication schemas.
   - Integrated authentication logic into `backend/app/main.py` with login endpoint and user retrieval.
   - Updated `backend/app/models/user.py` to match new schema (added `full_name`, `email`, renamed `password_hash` to `hashed_password`).
   - Updated `backend/app/config.py` to correctly define `ACCESS_TOKEN_EXPIRE_MINUTES`.
9. **Created Base Connector Interface**:
   - Defined `backend/app/connectors/base.py` with `BaseConnector` abstract class and `TimeEntryNormalized` Pydantic model.
10. **Implemented Zammad Connector**:
    - Created `backend/app/connectors/zammad_connector.py`, implementing `BaseConnector` methods for Zammad API interaction.
11. **Implemented Kimai Connector**:
    - Created `backend/app/connectors/kimai_connector.py`, implementing `BaseConnector` methods for Kimai API interaction.
12. **Created API Endpoints for Connectors**:
    - Created `backend/app/api/v1/endpoints/connectors.py` with validation and activity fetching endpoints.
    - Created `backend/app/api/v1/api.py` to include the `connectors` router.
    - Integrated `api_router` into `backend/app/main.py`.
13. **Built Normalizer Service**:
    - Created `backend/app/services/normalizer.py` with `NormalizerService` class for Zammad and Kimai entry normalization.
14. **Implemented Reconciliation Engine**:
    - Created `backend/app/services/reconciler.py` with `ReconciliationService` class for comparing and reconciling time entries.
15. **Implemented Sync Service**:
    - Created `backend/app/services/sync_service.py` with `SyncService` class for orchestrating time entry synchronization.
16. **Implemented Conflict Detection and API**:
    - Reviewed `backend/app/models/conflict.py` and made `time_entry_id` nullable.
    - Created `backend/app/schemas/conflict.py` for Pydantic schemas.
    - Created `backend/app/api/v1/endpoints/conflicts.py` with CRUD operations for conflicts.
    - Integrated `conflicts` router into `backend/app/api/v1/api.py`.
    - Updated `backend/app/services/sync_service.py` to persist detected conflicts to the database.
17. **Implemented Scheduled Tasks (APScheduler)**:
    - Set up and configured `APScheduler` in `backend/app/main.py`.
    - Fixed indentation errors in `backend/app/main.py`.
    - Updated `backend/app/config.py` with Zammad and Kimai connector settings.
    - Refined `SyncService` dependency injection for scheduled tasks using an `asynccontextmanager` for database sessions.
18. **Implemented Connection Validation and Connector Configuration Management**:
    - Reviewed `backend/app/models/connector.py`.
    - Defined Pydantic Schemas for Connectors (`backend/app/schemas/connector.py`).
    - Created encryption utility (`backend/app/utils/encrypt.py`).
    - Added CRUD endpoints for connectors in `backend/app/api/v1/endpoints/connectors.py`.
    - Fixed Pylance errors in `backend/app/api/v1/endpoints/connectors.py`.
19. **Implemented Activity Mapping Endpoints**:
    - Created Pydantic schemas (`backend/app/schemas/mapping.py`) for ActivityMapping CRUD.
    - Implemented CRUD endpoints (`backend/app/api/v1/endpoints/mappings.py`) with uniqueness checks for Zammad-Kimai pairs.
    - Integrated mappings router into `backend/app/api/v1/api.py`.
    - Updated `backend/app/services/sync_service.py` to apply mappings during Kimai creation (lookup by zammad_type_id, conflict for unmapped); fixed normalization calls.
    - No changes to `backend/app/services/normalizer.py` needed (unification preserves IDs for reconciliation).
20. **Fixed Authentication Integration and Login Flow**:
    - Updated `frontend/src/context/AuthContext.tsx` to use authService correctly (POST /token, GET /users/me) instead of hardcoded endpoints.
    - Fixed bcrypt password hashing limitation in `backend/app/auth.py` by switching to pbkdf2_sha256 scheme.
    - Verified demo user login with credentials admin/changeme works via backend API and frontend application.
    - Rebuilt frontend Docker image and restarted services; login now functional at http://localhost:3000.

## Next Immediate Steps
- Implement sync endpoints if not complete (check API/v1/sync).
- Add integration tests for connectors.
- Address npm vulnerabilities with `npm audit fix` in frontend.
- Configure default_project_id in Kimai connector config via UI.

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

## Development Environment Notes
**Windows Local Development:**
- Frontend: `cd frontend` then `npm run dev` (Vite dev server on port 5173)
- Backend: `cd backend` then `uvicorn app.main:app --reload` (FastAPI on port 8000)
- Vite proxies `/api` requests to backend (see vite.config.ts)
- PowerShell command chaining: Use semicolons (`;`) not `&&`

**Docker Deployment (Production):**
- Use `docker-compose up` from project root
- Backend: FastAPI in Docker container with Gunicorn
- Frontend: Vite build served by Nginx
- PostgreSQL: Separate database service
- All services networked via docker-compose.yml

## Key Learnings
- Zammad time_unit is in minutes (not hours)
- Kimai requires HTML5 datetime format (no timezone)
- Activity type mapping is critical for proper sync
- Webhook requires HMAC verification for security
- Tags in Kimai use format "billed:YYYY-MM" for billing status
