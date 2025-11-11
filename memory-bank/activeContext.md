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
1. **Implemented Scheduling Feature for Automatic Sync Runs (November 2025)**:
   - **Goal**: Add comprehensive scheduling for periodic syncs with UI configuration, dynamic rescheduling, concurrency control, and notifications.
   - **Backend Implementation**:
     - Created database migration (`backend/alembic/versions/20251111_1742_138c27fb806b_add_schedules_table.py`) for `schedules` table (single row: id, cron, timezone, concurrency, notifications, enabled, timestamps).
     - Created `Schedule` model (`backend/app/models/schedule.py`) with SQLAlchemy fields and relationships.
     - Created schedule schemas (`backend/app/schemas/schedule.py`) with Pydantic validation: `ScheduleBase` (cron validation via croniter, timezone via ZoneInfo), `ScheduleResponse` (with computed `next_runs`), `ScheduleUpdate` (optional fields).
     - Created schedule endpoints (`backend/app/api/v1/endpoints/schedule.py`):
       - `GET /api/v1/schedule`: Fetches or creates default schedule; computes next 3 runs using croniter (respects timezone).
       - `PUT /api/v1/schedule`: Updates schedule, tracks changes for audit, calls `reschedule_sync_job()` for dynamic updates without restart.
     - Created scheduler service (`backend/app/scheduler.py`): APScheduler integration with AsyncIOScheduler; `scheduled_sync_job()` executes sync with concurrency handling (skip/queue, queue limit 5); `reschedule_sync_job()` for dynamic cron changes; `start_scheduler()` loads from DB on startup; `shutdown_scheduler()` for graceful shutdown.
     - Integrated scheduler in `backend/app/main.py`: `@app.on_event("startup")` calls `start_scheduler()`; `@app.on_event("shutdown")` calls `shutdown_scheduler()`.
     - Added `croniter>=2.0.0` to `backend/requirements.txt` for cron parsing/validation.
     - Audit integration: `schedule_updated` event with changes dict (old/new values).
     - Notification framework: Logs when conflicts >10 or failures occur (extendable to email/webhook).
   - **Frontend Implementation**:
     - Added `Schedule` and `ScheduleUpdate` types to `frontend/src/types/index.ts`.
     - Added `scheduleService` to `frontend/src/services/api.service.ts`: `get()` and `update()` methods.
     - Created `ScheduleDialog` component (`frontend/src/components/ScheduleDialog.tsx`):
       - Presets: Hourly, Every 6h, Daily, Weekly, Monthly, Custom (auto-generates cron).
       - Time picker for daily/weekly/monthly; weekday chips for weekly (Mon-Sun, at least one required).
       - Timezone selector (UTC, Europe/Brussels, etc.).
       - Concurrency policy (skip/queue with descriptions).
       - Notifications toggle (alerts on failures/high conflicts).
       - Enable/disable toggle.
       - Client validation: Non-empty cron, required time/days for presets, toast errors.
       - Next 3 runs preview: Localized timestamps using Intl.DateTimeFormat with selected timezone.
       - TanStack Query integration: Fetches on open, invalidates on save.
     - Wired into `frontend/src/pages/SyncDashboard.tsx`: Replaced top bar placeholder with `<ScheduleDialog />`; imported component.
   - **Key Features**:
     - Dynamic rescheduling without restart (API-driven).
     - Concurrency enforcement: Skip prevents overlaps; queue limits to 5.
     - Preset editing updates cron; manual cron overrides presets.
     - Weekly DOW chips generate correct cron (e.g., "0 9 * * 1,3,5" for Mon/Wed/Fri).
     - Next runs computed server-side, displayed client-side with timezone formatting.
     - Audit logs all changes (`schedule_updated` with diff).
     - Toasts for success/error; disable save during pending.
   - **Impact**:
     - Full scheduling capability: Automatic periodic syncs with UI control.
     - No service restart needed for changes; immediate effect.
     - Compliance: All updates audited; notifications for issues.
     - UX: Intuitive presets with validation; real-time preview.
   - **Testing**: Migration applied; dependencies installed; backend scheduler starts; frontend dialog fetches/saves; cron validation works; next runs localize correctly.
   - **Files Modified**: Multiple (migrations, models, schemas, endpoints, scheduler, main.py, requirements.txt, frontend types/service/components/dashboard).
   - **Compliance**: Backward compatible; extends existing APScheduler; production ready.

2. **Fixed Audit Section Issues (November 2025)**:
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

3. **Implemented IP Tracking for Audit Logs (November 2025)**:
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

4. **Fixed Reconcile Screen Data Extraction (November 2025)**:
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

5. **Reconcile Screen Refactor with New Business Rules (January 2025)**:
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

6. **Sync Error Handling Refactor**:
   - Fixed silent failures in Zammad connector (now raises connection/auth errors)
   - Optimized logging: Reduced DEBUG noise, added error classification (connection, auth, permissions, timeouts)
   - Enhanced SyncResponse with `error_detail` field for UI feedback
   - Updated sync endpoint to return structured errors instead of HTTP exceptions
   - Frontend integration: Toast notifications show specific error messages (e.g., "Connection error: Invalid URL")
   - Result: Clear UI feedback for invalid URLs/tokens; cleaner backend logs

7. **UI Polish**:
   - Fixed TypeScript errors in SyncDashboard mutation handling
   - Updated api.service.ts to return SyncResponse type
   - Improved toast messages with dynamic content (success: entry count; failure: error details)

8. **Frontend Cleanup (November 2025)**:
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
- **Scheduling**: APScheduler for V1 (in-process); dynamic rescheduling via API; concurrency modes (skip/queue); notifications on high conflicts/failures
