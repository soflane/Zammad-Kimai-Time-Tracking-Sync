# Zammad-Kimai Time Tracking Sync - Project Brief

## Overview
A synchronization service with web UI that normalizes and reconciles time tracking entries between Zammad (ticketing system) and Kimai (time tracking), with support for future connectors.

## Core Requirements

### Primary Goal
Synchronize time tracking data from Zammad tickets to Kimai timesheets in one direction (Zammad → Kimai).

### Key Features
1. **Multi-Source Normalization**: Transform time entries from different sources (Zammad, Kimai, future systems) into a unified format
2. **Reconciliation Engine**: Match, detect conflicts, and identify missing entries between systems
3. **Conflict Resolution UI**: Web interface to review and resolve differences
4. **Plugin Architecture**: Connector-based system for extensibility
5. **Real-time & Scheduled Sync**: Both webhook-triggered and periodic synchronization
6. **Configuration Management**: Web UI for all settings and mappings

### Technical Constraints
- **Language**: Python (backend)
- **Deployment**: Docker containers on VPS
- **Database**: PostgreSQL
- **Authentication**: Single admin user (V1)
- **Sync Direction**: Zammad → Kimai (one-way)

## User Workflows

### Setup Flow
1. Configure Zammad connector (URL, API token)
2. Configure Kimai connector (URL, API token)
3. Map Zammad activity types to Kimai activities
4. Set up sync schedule
5. Configure Zammad webhook (optional for real-time sync)

### Sync Flow
1. System fetches time accountings from Zammad
2. Normalizes data into standard format
3. Compares with existing Kimai timesheets
4. Auto-syncs clear matches
5. Flags conflicts for manual review
6. Creates timesheets in Kimai with proper tags

### Conflict Resolution Flow
1. View list of conflicts in UI
2. See side-by-side comparison of Zammad vs Kimai data
3. Choose action: Create/Update in Kimai or Skip
4. Apply resolution
5. Log action in audit trail

## Success Criteria
- ✅ Successfully sync Zammad time entries to Kimai
- ✅ Detect and highlight conflicts for manual resolution
- ✅ Maintain complete audit trail of all operations
- ✅ Support billable status tracking via Kimai tags
- ✅ Run reliably in Docker environment
- ✅ Provide intuitive web UI for all operations

## Production & DevOps Features

### CI/CD (V1)
- GitHub Actions for automated testing and deployment
- Automated linting and tests for backend & frontend
- Container builds pushed to GitHub Container Registry (GHCR)
- Tag-based releases with versioned containers

### Security & GDPR (V1)
- API tokens encrypted at rest using Fernet/libsodium
- Minimal personal data storage with data retention policies
- Export and purge endpoints for GDPR compliance
- Secure password hashing with bcrypt
- HMAC webhook signature verification

### Open-Source Hygiene
- MIT License for wide adoption
- Comprehensive documentation (README, ARCHITECTURE, ROADMAP)
- Security policy (SECURITY.md) for vulnerability reporting
- Dependabot for dependency updates
- GitHub issue/PR templates
- One-click Docker Compose demo stack

### Observability
- Structured logging to stdout
- Audit trail for all operations
- Health check endpoints
- Error tracking and reporting

## Future Enhancements (Post-MVP)

### V2 Features
- Multi-user authentication with role-based access
- Bi-directional sync (Zammad ← Kimai)
- Rule simulator for testing changes
- OIDC authentication (Keycloak, GitHub)

### Advanced Capabilities
- Sentry + OpenTelemetry for tracing
- Kubernetes Helm chart for production
- Pluggable adapter pattern for new connectors
- Advanced reporting and analytics
- Mobile-responsive UI improvements

## Non-Goals (V1)
- Multi-user authentication (single admin only in V1)
- Bi-directional sync (Zammad ← Kimai, planned for V2)
- Mobile app (responsive web UI instead)
- Advanced reporting/analytics (basic audit logs only)
