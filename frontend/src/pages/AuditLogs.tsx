import { useState, useEffect } from 'react'
import { useAuth } from '@/context/AuthContext'
import { useToast } from '@/hooks/use-toast'
import { auditService } from '@/services/api.service'
import type { AuditLog } from '@/types'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Download, Search, Filter, FileText, Calendar, Globe, Monitor } from 'lucide-react'

export default function AuditLogs() {
  const [logs, setLogs] = useState<AuditLog[]>([])
  const [sortBy, setSortBy] = useState<'action' | 'date' | 'entity'>('date')
  const [filter, setFilter] = useState('')
  const [filterAction, setFilterAction] = useState('')
  const [loading, setLoading] = useState(true)
  const { isAuthenticated } = useAuth()
  const { toast } = useToast()

  const actions = [...new Set(logs.map(log => log.action))]

  const filteredLogs = logs
    .filter(log => log.action.includes(filterAction))
    .filter(log => log.user_id?.toString().includes(filter) || log.action.includes(filter) || log.entity_type.includes(filter))
    .sort((a, b) => {
      if (sortBy === 'date') return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      if (sortBy === 'action') return a.action.localeCompare(b.action)
      return a.entity_type.localeCompare(b.entity_type)
    })

  useEffect(() => {
    if (isAuthenticated) {
      fetchLogs()
    }
  }, [isAuthenticated])

  useEffect(() => {
    if (logs.length > 0) {
      // Re-filter when data changes
    }
  }, [logs, filter, filterAction, sortBy])

  const fetchLogs = async () => {
    try {
      setLoading(true)
      const data = await auditService.getAll({ limit: 100 })
      setLogs(data)
    } catch (error: any) {
      toast({
        title: "Failed to load audit logs",
        description: error.response?.data?.detail || "Please try again later",
        variant: "destructive"
      })
    } finally {
      setLoading(false)
    }
  }

  const handleExport = async (format: 'csv' | 'json') => {
    try {
      const blob = await auditService.export(format)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `audit-logs-${new Date().toISOString().split('T')[0]}.${format}`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
      
      toast({
        title: "Export successful",
        description: `Audit logs exported as ${format.toUpperCase()}`,
      })
    } catch (error: any) {
      toast({
        title: "Export failed",
        description: error.response?.data?.detail || "Please try again",
        variant: "destructive",
      })
    }
  }

  const formatChanges = (changes: Record<string, any> | undefined) => {
    if (!changes) return 'No changes recorded'
    return JSON.stringify(changes, null, 2)
  }

  if (loading) {
    return (
      <div className="space-y-6 p-6">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <div className="h-8 bg-muted rounded w-48 animate-pulse"></div>
            <div className="h-4 bg-muted rounded w-64 animate-pulse"></div>
          </div>
          <div className="h-10 bg-muted rounded w-32 animate-pulse"></div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="h-32 bg-muted rounded animate-pulse"></div>
          <div className="h-32 bg-muted rounded animate-pulse"></div>
          <div className="h-32 bg-muted rounded animate-pulse"></div>
          <div className="h-32 bg-muted rounded animate-pulse"></div>
        </div>
        <div className="h-64 bg-muted rounded animate-pulse"></div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-4 space-y-6">
      <div className="flex justify-between items-center">
        <div className="flex items-center space-x-2">
          <FileText className="h-6 w-6 text-primary" />
          <h1 className="text-2xl font-bold">Audit Logs</h1>
        </div>
        <div className="flex items-center space-x-2">
          <Button onClick={() => handleExport('json')} variant="outline" size="sm" className="shadow-modern">
            <Download className="mr-2 h-4 w-4" /> JSON
          </Button>
          <Button onClick={() => handleExport('csv')} variant="outline" size="sm" className="shadow-modern">
            <Download className="mr-2 h-4 w-4" /> CSV
          </Button>
        </div>
      </div>

      <div className="flex flex-wrap gap-4 items-end">
        <div className="space-x-2 flex items-center">
          <Search className="h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search logs..."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="max-w-sm"
          />
        </div>
        <div className="space-x-2 flex items-center">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <Select value={filterAction} onValueChange={setFilterAction}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="All Actions" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">All Actions</SelectItem>
              {actions.map(action => (
                <SelectItem key={action} value={action}>{action}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-x-2 flex items-center">
          <Calendar className="h-4 w-4 text-muted-foreground" />
          <Select value={sortBy} onValueChange={(value) => setSortBy(value as 'action' | 'date' | 'entity')}>
            <SelectTrigger className="w-[120px]">
              <SelectValue placeholder="Sort by Date" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="date">Date</SelectItem>
              <SelectItem value="action">Action</SelectItem>
              <SelectItem value="entity">Entity</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {filteredLogs.length === 0 ? (
        <Card className="shadow-modern">
          <CardContent className="p-6 text-center">
            <FileText className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-lg">No audit logs found</p>
            <p className="text-muted-foreground">Try adjusting your search or filter</p>
          </CardContent>
        </Card>
      ) : (
        <Card className="shadow-modern">
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              Audit Log Entries ({filteredLogs.length})
              <span className="px-2 py-1 rounded-md text-xs font-medium bg-muted text-muted-foreground">
                {filteredLogs.length} total
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <div className="min-w-full border rounded-lg">
                <div className="bg-muted/50 grid grid-cols-[200px_150px_1fr_auto] p-4 font-medium border-b text-sm">
                  <span>Date & Time</span>
                  <span>Action</span>
                  <span>Entity</span>
                  <span>User</span>
                </div>
                {filteredLogs.map((log) => (
                  <div key={log.id} className="hover:bg-accent/50 transition-colors border-b last:border-b-0">
                    <div className="grid grid-cols-[200px_150px_1fr_auto] p-4">
                      <span className="text-sm">{new Date(log.created_at).toLocaleString()}</span>
                      <span className="text-sm font-medium">{log.action}</span>
                      <span className="text-sm">{log.entity_type}{log.entity_id ? ` #${log.entity_id}` : ''}</span>
                      <span className="text-sm text-muted-foreground">{log.user_id || 'System'}</span>
                    </div>
                    <div className="pl-4 pb-4 border-l-2 border-muted bg-muted/20">
                      {log.changes && (
                        <div className="space-y-2 p-4 bg-background rounded-r">
                          <p className="text-sm font-medium flex items-center">
                            <FileText className="h-4 w-4 mr-2" />
                            Changes
                          </p>
                          <pre className="text-xs overflow-x-auto max-h-32">
                            {formatChanges(log.changes)}
                          </pre>
                        </div>
                      )}
                      {(log.ip_address || log.user_agent) && (
                        <div className="space-y-1 p-4">
                          {log.ip_address && (
                            <p className="text-xs flex items-center">
                              <Globe className="h-3 w-3 mr-2 text-muted-foreground" />
                              IP: {log.ip_address}
                            </p>
                          )}
                          {log.user_agent && (
                            <p className="text-xs flex items-center">
                              <Monitor className="h-3 w-3 mr-2 text-muted-foreground" />
                              UA: {log.user_agent.substring(0, 50)}...
                            </p>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
