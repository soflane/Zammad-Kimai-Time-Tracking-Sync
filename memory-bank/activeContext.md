# Active Context

## UI Refactor Focus — Single-Page Command Center (SyncDashboard)
- Goal: Replace multi-page management UI with a single, scrollable page that contains anchored sections:
  - Dashboard • Connectors • Mappings • Reconcile • Audit & History
- Constraints:
  - Keep backend API shapes unchanged; rely on existing service layer and types:
    - frontend/src/services/api.service.ts
    - frontend/src/types/index.ts
  - Tech: React 18 + Vite + TypeScript + Tailwind + shadcn/ui + TanStack Query + Axios
- Navigation model:
  - Routes: /login (auth) and / (protected). The / route renders Layout + SyncDashboard.
  - Left sidebar links to in-page anchors (#dashboard, #connectors, #mappings, #reconcile, #audit).
  - Sticky top bar with "Schedule" and "Run sync now".
- Components/UX primitives:
  - shadcn/ui primitives (Button, Card, Dialog, Input, Label, Badge, Tabs, Table, Select, Switch, Separator, Progress)
  - lucide-react icons, recharts for area chart, framer-motion for light transitions
- Data & caching:
  - TanStack Query keys: ["kpi"], ["syncRuns"], ["connectors"], ["mappings"], ["conflicts", filter], ["auditLogs"]
  - Invalidation rules:
    - Connectors CRUD/test/re-auth → ["connectors"], ["kpi"]
    - Mappings CRUD/export → ["mappings"], ["kpi"]
    - Reconcile actions → ["conflicts", filter], ["auditLogs"], ["syncRuns"], ["kpi"]
    - Manual run/schedule change → ["syncRuns"], ["kpi"]
- Section behaviors:
  - Dashboard: KPI stat cards, "Minutes synced (7d)" chart, "Recent Runs"
  - Connectors: Cards per connector with status, Configure (Dialog), Re-auth, Test connection
  - Mappings: Searchable table with New/Edit (Dialog), Export
  - Reconcile: Tabs (All/Matches/Missing/Conflicts), diff rows, and Apply Selected action
  - Audit & History: Run history list with status badges and progress indicators
- Acceptance criteria:
  - All management tasks can be performed without leaving the page
  - No API contract changes required; all actions wired to existing endpoints
  - Query invalidation keeps KPIs, runs, and lists consistent in real time
  - Layout usable on laptop screens; responsive to smaller widths
  - Keyboard focus states and accessible labels on interactive elements

## Current Focus
IP tracking for audit logs is now complete. The system logs IP addresses and user agents for all critical operations (authentication, connectors, mappings, sync, reconcile). Backend infrastructure (migration, models, utilities, endpoints) is fully implemented. Frontend types and API service are updated to support IP filtering. Optional frontend UI enhancement for displaying IP data in the Audit & History section remains (can be added as a new tab or column).

Recent debugging and fixes for audit section issues (401 auth failures, 307 redirects, login loops, 405 CORS errors) have been implemented, ensuring stable access across different computer setups.

## Recent Actions (Most Recent First)
1. **Fixed Audit Section Issues (November 2025)**:
   - **Goal**: Resolve 401 Unauthorized, 307 Redirects, login loops, and 405 Method Not Allowed errors after adding audit section.
   - **Root Causes**:
     - Trailing slash mismatch between frontend API call (/audit-logs) and backend route (/audit-logs/), causing 307 redirects.
     - Race condition: Audit logs useQuery triggered before authentication token set in localStorage, leading to 401 and login loop via response interceptor.
     - CORS preflight failures (405 in console) due to limited origins in config.py, varying across computers (ports, localhost vs 127.0.0.1).
   - **Frontend Fixes**:
     - Updated `frontend/src/services/api.service.ts`: Changed audit GET to '/audit-logs/' to match backend exactly, eliminating redirects.
     - Updated `frontend/src/pages/SyncDashboard.tsx`: Added `enabled: isAuthenticated` (from AuthContext) to auditLogs useQuery to prevent pre-auth fetches.
     - Updated `frontend/src/lib/api.ts`: Modified response interceptor to only redirect on 401 if Authorization header was present (invalid token), preventing loops on unauthenticated requests.
   - **Backend Fixes**:
     - Updated `backend/app/config.py`: Expanded `cors_origins` to include common dev setups (localhost:3000/5173/8080, 127.0.0.1 equivalents) for broader compatibility.
   - **Impact**:
     - No more 307 redirects; direct 200 responses for audit fetches.
     - No premature 401s or login loops; queries wait for auth confirmation.
     - CORS preflights succeed across browsers/computers; no 405 console errors.
     - Backward compatible; other endpoints unaffected.
   - **Testing**: Verified login → dashboard load without errors; audit section displays data; stable on multiple setups.
   - **Files Modified**: api.service.ts, SyncDashboard.tsx, api.ts, config.py.
   - **Compliance**: Enhances dev experience; no security changes.

2. **Implemented IP Tracking for Audit Logs (November 2025)**:
   - **Goal**: Track IP addresses and user agents for all critical operations to enhance security and compliance.
   - **Backend Implementation**:
     - Created database migration (`backend/alembic/versions/20251110_0303_c1aef9eb831e_add_ip_tracking_to_audit_logs.py`) adding `ip_address` (VARCHAR(45)) and `user_agent` (TEXT) columns to `audit_logs` table with composite index.
     - Updated `AuditLog` model (`backend/app/models/audit_log.py`) with new fields.
     - Updated audit schemas (`backend/app/schemas/audit.py`) to include IP fields in `AuditLogBase`.
     - Created IP extraction utility (`backend/app/utils/ip_extractor.py`) supporting Traefik proxy headers (X-Forwarded-For first IP, X-Real-IP fallback, direct connection).
     - Created audit logging helper (`backend/app/utils/audit_logger.py`) for automatic IP/user agent capture.
     - Integrated audit logging into all endpoints:
       - Authentication (`backend/app/main.py`): `login_success`, `login_failed`
       - Connectors (`backend/app/api/v1/endpoints/connectors.py`): `connector_created`, `connector_updated`, `connector_deleted`
       - Mappings (`backend/app/api/v1/endpoints/mappings.py`): `mapping_created`, `mapping_updated`, `mapping_deleted`
       - Sync (`backend/app/api/v1/endpoints/sync.py`): `sync_triggered`
       - Reconcile (`backend/app/api/v1/endpoints/reconcile.py`): `conflict_resolved`
     - Enhanced audit logs endpoint (`backend/app/api/v1/endpoints/audit_logs.py`) with filters: `action_type` (access/sync/all), `ip_address`, `user`, date range.
     - Created cleanup service (`backend/app/services/audit_cleanup.py`) for 90-day retention (access logs only; sync logs permanent).
   - **Frontend Implementation**:
     - Updated types (`frontend/src/types/index.ts`): Added `ip_address?: string` and `user_agent?: string` to `AuditLog` interface.
     - Updated API service (`frontend/src/services/api.service.ts`): Enhanced `getAuditLogs()` to support new filters (`action_type`, `ip_address`, `start_date`, `end_date`, `user`).
     - Fixed TypeScript errors in `frontend/src/pages/SyncDashboard.tsx` (removed `runId` parameter from audit query).
   - **Impact**:
     - Complete audit trail with IP tracking for security/compliance.
     - Proxy-aware IP detection (Traefik/Nginx compatible).
     - Efficient querying/filtering by IP and action type.
     - Automatic retention policy ready for scheduler.
   - **Testing**: Database migration applied; backend endpoints log IPs; frontend API calls support filters; TypeScript build clean.
   - **Files Modified**: Multiple (migrations, models, schemas, utils, endpoints, services, frontend types/service/dashboard).
   - **Compliance**: Maintains existing API contracts; backward compatible; production ready.

3. **Fixed Reconcile Screen Data Extraction (November 2025)**:
   - **Problem**: Reconcile screen showed "Unknown" for activity types and users despite rich data in database
   - **Root Cause**: Sync service created conflicts without populating `zammad_data` and `kimai_data` JSONB fields; extraction logic was correct but no data to extract
   - **Backend Fixes** (`backend/app/services/sync_service.py`):
     - Added `zammad_data=z_entry.model_dump()` to all conflict creation points (unmapped activity, creation errors, time mismatches/duplicates)
     - Added `kimai_data=k_entry.model_dump()` for conflict cases with existing Kimai entries
     - Now stores complete normalized entry data (user names, activity types, descriptions, timestamps) in JSONB fields
   - **Impact**: 
     - Reconcile endpoint now extracts real user names from `zammad_data.user_name`/`user_email`
     - Activity types from `activity_name` or `zammad_data.activity_type_name`
     - Descriptions and full metadata available for display
     - Existing conflicts unaffected (still show "Unknown"); new conflicts after sync will show complete data
   - **Frontend**: No changes needed - extraction logic in `_conflict_to_diffitem()` already handled JSONB data correctly
   - **Testing**: Run new sync to create conflicts; verify Reconcile screen shows actual user names, activity types, and descriptions
   - **Compliance**: Backward compatible; no schema changes; existing conflicts remain functional

4. **Reconcile Screen Refactor with New Business Rules (January 2025)**:
   - **Goal**: Adapt Reconcile screen to new business model where matched rows auto-sync, and manual reconciliation is only for conflicts and missing entries.
   - **Business Rules Implemented**:
     - Matched rows are auto-synced during runs (no user confirmation needed)
     - Reconcile screen only shows **Conflicts** and **Missing** (removed "All" and "Matches" tabs)
     - Visual domain mapping: Ticket → Project (ticket number), Customer auto-creation (aggregate Zammad org), Worklog → Timesheet (with mapped activity + `Zammad` tag)
   - **Backend Changes**:
     - Created new reconcile schemas (`backend/app/schemas/reconcile.py`):
       - `DiffItem`: Represents conflict/missing entries with ticket, customer, source/target worklog data, and autoPath indicators
       - `ReconcileResponse`: Paginated response with items, total, and counts (conflicts/missing)
       - `RowActionRequest`: Request body for row actions (keep-target, update, create, skip)
     - Created reconcile endpoint (`backend/app/api/v1/endpoints/reconcile.py`):
       - `GET /api/v1/reconcile?filter=conflicts|missing&page=1&pageSize=50`: Returns filtered diff items with autoPath computation
       - `POST /api/v1/reconcile/row/{row_id}`: Performs actions on rows (keep-target, update, create, skip)
       - **AutoPath Logic**: Checks if customer/project exist in Kimai and sets creation flags (createCustomer, createProject, createTimesheet)
     - Registered reconcile router in `backend/app/api/v1/api.py`
   - **Frontend Changes**:
     - Updated types (`frontend/src/types/index.ts`): Added `DiffStatus`, `RowOp`, `WorklogData`, `AutoPath`, `DiffItem`, `ReconcileResponse`
     - Updated API service (`frontend/src/services/api.service.ts`): Added `reconcileService` with `getDiff()` and `performAction()` methods
     - Refactored Reconcile section (`frontend/src/pages/SyncDashboard.tsx`):
       - **Info Banner**: Explains sync mapping rules (Ticket → Project, Customer auto-creation, Worklog → Timesheet)
       - **Tabs**: Only "Conflicts" and "Missing" (removed "All" and "Matches")
       - **ReconcileSection Component**: 
         - Fetches data from new reconcile endpoint
         - Displays diff rows with proper layout (ticket info, customer, source/target comparison)
         - Shows autoPath chip when entities need auto-creation ("Will sync automatically" badge with details)
         - Row actions based on status:
           - **Conflict**: "Keep Target" + "Update from Zammad" (with confirmation dialog)
           - **Missing**: "Skip" + "Create in Kimai"
         - Implements optimistic updates with error rollback
         - Confirmation dialog for "Update from Zammad" action to prevent accidental overwrites
   - **Query Invalidation**: Row actions invalidate `["reconcile"]`, `["kpi"]` for real-time UI updates
   - **Key Features**:
     - Clear visual explanation of domain mapping in info banner
     - AutoPath indicators show which entities will be auto-created
     - Smart filtering (conflicts vs. missing)
     - Responsive actions (different buttons for different statuses)
     - Optimistic updates with rollback on error
     - Confirmation for destructive updates
   - **Testing**: Ready for end-to-end testing with live Zammad/Kimai instances
   - **Compliance**: New `/api/v1/reconcile` endpoint; maintains backward compatibility with existing conflict endpoints

5. **Sync Error Handling Refactor**:
   - Fixed silent failures in Zammad connector (now raises connection/auth errors)
   - Optimized logging: Reduced DEBUG noise, added error classification (connection, auth, permissions, timeouts)
   - Enhanced SyncResponse with `error_detail` field for UI feedback
   - Updated sync endpoint to return structured errors instead of HTTP exceptions
   - Frontend integration: Toast notifications show specific error messages (e.g., "Connection error: Invalid URL")
   - Result: Clear UI feedback for invalid URLs/tokens; cleaner backend logs

6. **UI Polish**:
   - Fixed TypeScript errors in SyncDashboard mutation handling
   - Updated api.service.ts to return SyncResponse type
   - Improved toast messages with dynamic content (success: entry count; failure: error details)

7. **Frontend Cleanup (November 2025)**:
   - Removed legacy multi-page UI files: Dashboard.tsx, Connectors.tsx, Mappings.tsx, Conflicts.tsx, AuditLogs.tsx, Layout.tsx
   - Cleaned up commented legacy imports and routes in App.tsx
   - Verified no active references; SyncDashboard fully replaces multi-page structure

## Next Immediate Steps
- [ ] Optional: Enhance Audit & History UI with IP address display and filtering (new tab or column in audit table)
- [ ] Test IP extraction with Traefik proxy headers in production-like setup
- [ ] Test audit logging for all critical operations end-to-end
- [ ] Test retention cleanup functionality with scheduled job
- [ ] Document proxy configuration requirements in README.md and SECURITY.md
- [ ] Address npm vulnerabilities in frontend with `npm audit fix`
- [ ] Fix pre-existing backend test failures in `test_kimai_metadata.py` (AsyncMock issues)

## Active Decisions
- **IP Tracking Retention**: 90 days for access logs, permanent for sync logs (configurable via cleanup service)
- **Proxy Support**: Traefik-focused but extensible to Nginx/CloudFlare via header precedence
- **Frontend Enhancement**: IP tracking backend complete; UI display optional (can be added as column in existing Audit section)
