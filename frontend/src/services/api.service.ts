import api from '@/lib/api'
import type {
  User,
  LoginRequest,
  LoginResponse,
  Connector,
  ConnectorCreate,
  ConnectorUpdate,
  ActivityMapping,
  ActivityMappingCreate,
  ActivityMappingUpdate,
  Conflict,
  ConflictUpdate,
  AuditLog,
  SyncRun,
  SyncRequest,
  ValidationResponse,
  Activity
} from '@/types'

// Authentication
export const authService = {
  login: async (credentials: LoginRequest): Promise<LoginResponse> => {
    const formData = new URLSearchParams()
    formData.append('username', credentials.username)
    formData.append('password', credentials.password)
    
    // Use axios directly for login to bypass the baseURL
    const response = await api.post('/token', formData, {
      baseURL: '', // Override baseURL to use root
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    })
    return response.data
  },

  getCurrentUser: async (): Promise<User> => {
    // Use axios directly for getCurrentUser to bypass the baseURL
    const response = await api.get('/users/me/', {
      baseURL: '' // Override baseURL to use root
    })
    return response.data
  },

  logout: () => {
    localStorage.removeItem('token')
  }
}

// Connectors
export const connectorService = {
  getAll: async (): Promise<Connector[]> => {
    const response = await api.get('/connectors/')
    return response.data
  },

  getById: async (id: number): Promise<Connector> => {
    const response = await api.get(`/connectors/${id}`)
    return response.data
  },

  create: async (connector: ConnectorCreate): Promise<Connector> => {
    const response = await api.post('/connectors/', connector)
    return response.data
  },

  update: async (id: number, connector: ConnectorUpdate): Promise<Connector> => {
    const response = await api.patch(`/connectors/${id}`, connector)
    return response.data
  },

  delete: async (id: number): Promise<void> => {
    await api.delete(`/connectors/${id}`)
  },

  validate: async (id: number): Promise<ValidationResponse> => {
    const response = await api.post(`/connectors/validate?connector_id=${id}`)
    return response.data
  },

  getActivities: async (id: number): Promise<Activity[]> => {
    const response = await api.get(`/connectors/${id}/activities`)
    return response.data
  }
}

// Activity Mappings
export const mappingService = {
  getAll: async (): Promise<ActivityMapping[]> => {
    const response = await api.get('/mappings/')
    return response.data
  },

  getById: async (id: number): Promise<ActivityMapping> => {
    const response = await api.get(`/mappings/${id}`)
    return response.data
  },

  create: async (mapping: ActivityMappingCreate): Promise<ActivityMapping> => {
    const response = await api.post('/mappings/', mapping)
    return response.data
  },

  update: async (id: number, mapping: ActivityMappingUpdate): Promise<ActivityMapping> => {
    const response = await api.put(`/mappings/${id}`, mapping)
    return response.data
  },

  delete: async (id: number): Promise<void> => {
    await api.delete(`/mappings/${id}`)
  }
}

// Conflicts
export const conflictService = {
  getAll: async (): Promise<Conflict[]> => {
    const response = await api.get('/conflicts/')
    return response.data
  },

  getById: async (id: number): Promise<Conflict> => {
    const response = await api.get(`/conflicts/${id}`)
    return response.data
  },

  resolve: async (id: number, resolution: ConflictUpdate): Promise<Conflict> => {
    const response = await api.patch(`/conflicts/${id}`, resolution)
    return response.data
  },

  delete: async (id: number): Promise<void> => {
    await api.delete(`/conflicts/${id}`)
  }
}

// Sync
export const syncService = {
  triggerSync: async (request: SyncRequest = {}): Promise<SyncRun> => {
    const response = await api.post('/sync/run', request)
    return response.data
  },

  getSyncHistory: async (): Promise<SyncRun[]> => {
    const response = await api.get('/sync/runs')
    return response.data
  },

  getSyncStatus: async (id: number): Promise<SyncRun> => {
    const response = await api.get(`/sync/runs/${id}`)
    return response.data
  },

  getKpi: async (): Promise<any> => {
    const response = await api.get('/sync/kpi')
    return response.data
  }
}

// Audit Logs
export const auditService = {
  getAll: async (params?: {
    skip?: number
    limit?: number
    action?: string
    entity_type?: string
  }): Promise<AuditLog[]> => {
    const response = await api.get('/audit-logs', { params })
    return response.data
  },

  export: async (format: 'csv' | 'json' = 'json'): Promise<Blob> => {
    const response = await api.get(`/audit-logs/export?format=${format}`, {
      responseType: 'blob'
    })
    return response.data
  }
}
