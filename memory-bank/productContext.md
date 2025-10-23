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

## User Experience Goals

### For IT Service Managers
- **Single Source of Truth**: All time tracking consolidated in Kimai for comprehensive reporting
- **Visibility**: Clear view of what's synced, what conflicts exist, what actions were taken
- **Control**: Ability to review and resolve conflicts before they reach the time tracking system
- **Confidence**: Audit trail ensures nothing is lost or incorrectly synced

### Key User Journeys

#### Initial Setup (One-time)
1. Install and access web UI
2. Create admin account
3. Configure Zammad connection (URL + API token)
4. Configure Kimai connection (URL + API token)
5. Map Zammad activity types to Kimai activities
6. Set sync schedule
7. Optionally configure Zammad webhook for real-time updates

#### Daily Operations
1. Agents log time in Zammad tickets as usual
2. System automatically syncs to Kimai (webhook or scheduled)
3. Manager reviews any conflicts in web UI
4. Manager resolves conflicts with one-click actions
5. Time appears in Kimai with proper activity type and tags

#### Conflict Resolution
1. Notification of pending conflicts
2. View conflict details side-by-side
3. Understand why conflict was flagged
4. Choose resolution: Create new, Update existing, or Skip
5. Confirm action
6. See result immediately

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
- Better reporting through Kimai's advanced features

### Extensibility
- Plugin architecture allows adding more connectors in future
- Not locked into specific tools
- Can adapt to changing business needs
