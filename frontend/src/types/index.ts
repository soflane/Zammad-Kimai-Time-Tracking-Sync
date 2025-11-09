// API Response Types based on backend schemas

export interface User {
  id: number
  username: string
  email: string
  full_name: string
  is_active: boolean
  created_at: string
}

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
}

export interface KimaiConnectorConfig {
  use_global_activities?: boolean
  default_project_id?: number | null
  default_activity_id?: number | null
  ignore_unmapped_activities?: boolean
  default_country?: string
  default_currency?: string
  default_timezone?: string
  // Time rounding configuration (matching Kimai's rounding behavior for better reconciliation)
  rounding_mode?: 'default' | 'closest' | 'floor' | 'ceil'
  round_begin?: number  // minutes, 0 = disabled
  round_end?: number    // minutes, 0 = disabled
  round_duration?: number  // minutes, 0 = disabled
  rounding_days?: number[]  // Days when rounding applies (0=Mon, 6=Sun)
}

export interface Connector {
  id: number
  type: 'zammad' | 'kimai'
  name: string
  base_url: string
  api_token: string
  is_active: boolean
  settings?: KimaiConnectorConfig | Record<string, any>
  created_at: string
  updated_at: string
}

export interface ConnectorCreate {
  type: 'zammad' | 'kimai'
  name: string
  base_url: string
  api_token: string
  is_active?: boolean
  settings?: KimaiConnectorConfig | Record<string, any>
}

export interface ConnectorUpdate {
  name?: string
  base_url?: string
  api_token?: string
  is_active?: boolean
  settings?: KimaiConnectorConfig | Record<string, any>
}

export interface ActivityMapping {
  id: number
  zammad_type_id: number
  zammad_type_name: string
  kimai_activity_id: number
  kimai_activity_name: string
  created_at: string
  updated_at: string
}

export interface ActivityMappingCreate {
  zammad_type_id: number
  zammad_type_name: string
  kimai_activity_id: number
  kimai_activity_name: string
}

export interface ActivityMappingUpdate {
  zammad_type_name?: string
  kimai_activity_id?: number
  kimai_activity_name?: string
}

export interface TimeEntry {
  id: number
  source: 'zammad' | 'kimai'
  source_id: string
  connector_id: number
  ticket_number?: string
  ticket_id?: number
  description: string
  time_minutes: number
  activity_type_id?: number
  activity_name?: string
  user_email: string
  entry_date: string
  sync_status: 'pending' | 'synced' | 'conflict' | 'error'
  target_id?: string
  tags?: string[]
  raw_data?: Record<string, any>
  created_at: string
  updated_at: string
}

export interface Conflict {
  id: number
  conflict_type: string
  zammad_data: any
  kimai_data: any
  resolution_status: string
  resolution_action?: string
  resolved_at?: string
  resolved_by?: string
  notes?: string
  time_entry_id?: number
  created_at?: string

  // Rich metadata
  reason_code?: string
  reason_detail?: string
  customer_name?: string
  project_name?: string
  activity_name?: string
  ticket_number?: string
  zammad_created_at?: string
  zammad_entry_date?: string
  zammad_time_minutes?: number
  kimai_begin?: string
  kimai_end?: string
  kimai_duration_minutes?: number
  kimai_id?: number
}

export interface ConflictUpdate {
  resolution_status?: string
  resolution_action?: string
  notes?: string
}

export interface SyncRun {
  id: number
  connector_id: number
  status: 'running' | 'completed' | 'failed'
  entries_fetched: number
  entries_synced: number
  conflicts_detected: number
  started_at: string
  ended_at?: string
  error_message?: string
}

export interface AuditLog {
  id: number
  action: string
  entity_type: string
  entity_id?: number
  user_id?: number
  changes?: Record<string, any>
  ip_address?: string
  user_agent?: string
  created_at: string
}

export interface SyncRequest {
  connector_id?: number
  start_date?: string
  end_date?: string
}

export interface SyncResponse {
  status: 'success' | 'failed';
  message: string;
  start_date: string;
  end_date: string;
  num_processed: number;
  num_created: number;
  num_conflicts: number;
  num_skipped: number;
  error_detail?: string;
}

export interface ValidationResponse {
  valid: boolean
  message: string
  details?: Record<string, any>
}

export interface Activity {
  id: number
  name: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  size: number
  pages: number
}

export interface ApiError {
  detail: string
  status_code?: number
}

// Reconcile types
export type DiffStatus = 'missing' | 'conflict';
export type RowOp = 'keep-target' | 'update' | 'create' | 'skip';

export interface WorklogData {
  minutes: number;
  activity: string;
  user: string;
  startedAt: string;
  ticketNumber?: string;
  description?: string;
}

export interface AutoPath {
  createCustomer?: boolean;
  createProject?: boolean;
  createTimesheet?: boolean;
}

export interface DiffItem {
  id: string;
  status: DiffStatus;
  ticketId: string;
  ticketTitle: string;
  customer: string;
  source?: WorklogData;
  target?: WorklogData;
  autoPath?: AutoPath;
  conflictReason?: string;
  reasonCode?: string;
}

export interface ReconcileResponse {
  items: DiffItem[];
  total: number;
  counts: {
    conflicts: number;
    missing: number;
  };
}

export interface RowActionRequest {
  op: RowOp;
}
