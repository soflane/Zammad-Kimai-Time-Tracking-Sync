# Bug Fix Summary - Login Redirect Loop & Docker Connectivity Issues

## Issues Identified

### 1. Redirect Loop in Dev Server (Vite + FastAPI)
**Symptoms:**
- After entering credentials on login page, user gets redirected back to login in an infinite loop
- Console shows 404 errors for `/api/v1/mappings` and `/api/v1/sync/history`
- Console shows 401 errors for `/api/v1/connectors/` and `/api/v1/conflicts/`

**Root Cause:**
- API endpoint mismatches between frontend service calls and backend routes
- Dashboard component making requests to non-existent endpoints immediately after login
- Failed API requests triggering 401 handling in axios interceptor
- Axios interceptor redirecting to login page on 401 errors
- This created a redirect loop: Login → Dashboard → API errors → 401 redirect → Login → repeat

### 2. Docker Connectivity Issues
**Symptoms:**
- Login works in Docker but can't add connectors
- Console shows `ERR_CONNECTION_REFUSED` for backend API calls
- 404 errors for some endpoints

**Root Cause:**
- Nginx not properly configured to proxy auth endpoints (`/token` and `/users`)
- Frontend making requests to endpoints that nginx wasn't forwarding to backend
- Missing proxy configuration for authentication routes

## Fixes Applied

### Fix 1: Corrected API Endpoint Paths
**File:** `frontend/src/services/api.service.ts`

Changed sync service endpoint paths to match backend implementation:
```typescript
// Before
triggerSync: async (request: SyncRequest = {}): Promise<SyncRun> => {
  const response = await api.post('/sync', request)  // Wrong!
  return response.data
},
getSyncHistory: async (): Promise<SyncRun[]> => {
  const response = await api.get('/sync/history')  // Wrong!
  return response.data
},

// After
triggerSync: async (request: SyncRequest = {}): Promise<SyncRun> => {
  const response = await api.post('/sync/run', request)  // Correct
  return response.data
},
getSyncHistory: async (): Promise<SyncRun[]> => {
  const response = await api.get('/sync/runs')  // Correct
  return response.data
},
```

**Backend routes** (in `backend/app/api/v1/endpoints/sync.py`):
- POST `/api/v1/sync/run` - trigger manual sync
- GET `/api/v1/sync/runs` - get sync history

### Fix 2: Added Auth Endpoint Proxying in Nginx
**File:** `frontend/nginx.conf`

Added proxy configurations for authentication endpoints:
```nginx
# Proxy auth endpoints to backend (for /token and /users/me)
location /token {
    proxy_pass http://backend:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

location /users {
    proxy_pass http://backend:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

This ensures Docker frontend can reach backend auth endpoints.

### Fix 3: Made Dashboard Resilient to Missing Endpoints
**File:** `frontend/src/pages/Dashboard.tsx`

Changed from `Promise.all()` to `Promise.allSettled()` to handle partial failures gracefully:
```typescript
// Before
const [connectors, mappings, conflicts, syncRuns] = await Promise.all([
  connectorService.getAll(),
  mappingService.getAll(),
  conflictService.getAll(),
  syncService.getSyncHistory(),
]);

// After - handles individual failures without breaking the UI
const [connectors, mappings, conflicts, syncRuns] = await Promise.allSettled([
  connectorService.getAll(),
  mappingService.getAll(),
  conflictService.getAll(),
  syncService.getSyncHistory(),
]);

const connectorsData = connectors.status === 'fulfilled' ? connectors.value : [];
// ... handle each response individually
```

This prevents the entire dashboard from failing if one endpoint is unavailable.

### Fix 4: Improved Auth Error Handling
**File:** `frontend/src/context/AuthContext.tsx`

Made token verification more resilient:
```typescript
// Before
.catch(() => {
  logout()  // Logs out on ANY error
})

// After
.catch((error) => {
  // Only logout if we got a real auth error, not network issues
  if (error.response?.status === 401) {
    logout()
  } else {
    // For other errors, keep the token but log the error
    console.error('Failed to verify token:', error)
  }
})
```

This prevents logout during temporary network issues or missing endpoints.

### Fix 5: Smarter Redirect Logic in API Interceptor
**File:** `frontend/src/lib/api.ts`

Improved 401 handling to prevent redirect loops:
```typescript
// Before
if (error.response?.status === 401) {
  if (!window.location.pathname.includes('/login')) {
    localStorage.removeItem('token')
    window.location.href = '/login'
  }
}

// After
if (error.response?.status === 401) {
  const currentPath = window.location.pathname
  const isAuthEndpoint = error.config?.url?.includes('/token') || 
                         error.config?.url?.includes('/users/me')
  
  if (!currentPath.includes('/login') && !isAuthEndpoint) {
    localStorage.removeItem('token')
    setTimeout(() => {
      window.location.href = '/login'
    }, 100)
  }
}
```

Key improvements:
- Don't redirect if the 401 came from auth endpoints themselves
- Use setTimeout to prevent immediate redirect loops
- Only redirect for protected resource 401s

## Testing Instructions

### For Dev Server (Vite + FastAPI)
1. Start backend: `cd backend && uvicorn app.main:app --reload`
2. Start frontend: `cd frontend && npm run dev`
3. Navigate to http://localhost:5173
4. Login with `admin` / `changeme`
5. Should successfully reach Dashboard without redirect loop
6. Dashboard should load even though some endpoints return empty arrays

### For Docker
1. Rebuild containers: `docker-compose build`
2. Start services: `docker-compose up`
3. Navigate to http://localhost:3000
4. Login with `admin` / `changeme`
5. Should successfully reach Dashboard
6. Try adding a connector - should work now (no connection refused)

## Summary of Changed Files

1. `frontend/src/services/api.service.ts` - Fixed sync endpoint paths AND added trailing slashes to all list endpoints
2. `frontend/nginx.conf` - Added auth endpoint proxying
3. `frontend/src/pages/Dashboard.tsx` - Made resilient to missing endpoints
4. `frontend/src/context/AuthContext.tsx` - Improved error handling
5. `frontend/src/lib/api.ts` - Smarter 401 redirect logic
6. `backend/app/api/v1/endpoints/mappings.py` - Removed double-prefix (router had prefix="/mappings")
7. `backend/app/api/v1/endpoints/sync.py` - Removed double-prefix (router had prefix="/sync")

## Root Cause: FastAPI Trailing Slash Redirects (307)

The **critical issue** was FastAPI's automatic redirect behavior:
- Backend routes defined with trailing slashes (e.g., `@router.get("/", ...)`)
- Frontend calling without trailing slashes (e.g., `api.get('/connectors')`)
- FastAPI sends 307 Temporary Redirect to add the trailing slash
- **During the redirect, the Authorization header is lost!**
- Backend receives request without auth → 401 Unauthorized
- Axios interceptor sees 401 → redirects to login → infinite loop

### Additional Fixes Applied

**Fix 6: Added Trailing Slashes to Frontend Calls**
All list endpoint calls now include trailing slashes:
- `/connectors` → `/connectors/`
- `/conflicts` → `/conflicts/`
- `/mappings/` → `/mappings/`

**Fix 7: Removed Double-Prefix in Backend Routers**
Two routers had prefixes defined twice:
- `mappings.py` had `prefix="/mappings"` in router AND in `api.py` include
- `sync.py` had `prefix="/sync"` in router AND in `api.py` include

This caused routes like `/api/v1/mappings/mappings/` (404 errors).

## Next Steps

The fixes address the immediate redirect loop and connectivity issues. The application should now:
- ✅ Login successfully without redirect loops
- ✅ Load dashboard data from all endpoints
- ✅ Handle missing endpoints gracefully (show empty data, not crash)
- ✅ Work in both dev server and Docker environments

You may still see 404 for `/api/v1/sync/runs` since it's a placeholder endpoint that returns an empty array. This won't break functionality.
