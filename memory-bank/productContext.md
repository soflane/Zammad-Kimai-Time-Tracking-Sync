# Product Context

## Problem Statement
IT service providers using Zammad for ticketing face limitations with time tracking:
- Time entries in Zammad tickets don't cover non-ticket work (maintenance, migrations, etc.)
- Zammad's reporting is insufficient for billing and MSP management
- No way to track billable status (billed, non-billable, remaining to bill, included in MSP/offer)
- Manual data entry in multiple systems is error-prone and time-consuming

## Solution
A synchronization bridge that:
1. Automatically syncs time entries from Zammad to Kimai
2. Provides intelligent reconciliation to prevent duplicates
3. Offers web UI for configuration and conflict resolution
4. Maintains audit trail for compliance and troubleshooting

## New UX Direction: Single-Page Command Center
Refactor the frontend into one consolidated page (SyncDashboard) with anchored sections:
- Dashboard
- Connectors
- Mappings
- Reconcile
- Audit & History

Characteristics:
- Sticky top bar with global actions: “Schedule” and “Run sync now”
- Left sidebar with section shortcuts (anchors)
- Sections rendered as cards/tables with inline actions and dialogs
- All CRUD operations happen in-place (no route changes)
- Data refresh via TanStack Query invalidations after actions

## User Experience Goals

### For IT Service Managers
- Single Source of Truth: Manage setup, mappings, reconciliation and audit in one screen
- Visibility: KPI cards, chart of synced minutes, and recent runs visible at a glance
- Control: Inline dialogs for connector config and mappings; one-click apply in Reconcile
- Confidence: Audit trail section and deterministic logs

### Key User Journeys (Single-Page)

#### Initial Setup (One-time)
1. Login
2. In Connectors section, configure Zammad (URL + API token)
3. Configure Kimai (URL + API token)
4. In Mappings section, map Zammad activity types to Kimai activities
5. From top bar, open “Schedule” dialog to set sync schedule
6. Optionally configure Zammad webhook per backend docs

#### Daily Operations
1. Agents log time in Zammad
2. Automatic or scheduled sync processes entries
3. Manager reviews Reconcile section for any differences
4. Manager resolves rows via inline actions (Create/Update/Ignore/Skip)
5. KPI and Recent Runs update automatically

#### Conflict Resolution
1. Filter by All / Matches / Missing / Conflicts
2. Inspect diff row details
3. Choose resolution (Create/Update/Skip) or “Apply selected”
4. Outcome is recorded in Audit & History

## Business Value

### Time Savings
- Eliminate manual re-entry of time from tickets
- Reduce time spent on timesheet reconciliation
- Automated periodic sync reduces oversight burden

### Accuracy
- Prevent duplicate entries
- Ensure consistent activity type mapping
- Maintain data integrity with conflict detection

### Compliance & Billing
- Complete audit trail for all sync operations
- Proper tagging for billing status (billed:YY-MM)
- Better reporting through Kimai’s advanced features

### Extensibility
- Plugin architecture allows adding more connectors in future
- Single-page layout simplifies discoverability of new features
- UI additions can appear as new anchored sections or cards without routing changes
