import { useState, useEffect } from 'react'
import { useAuth } from '@/context/AuthContext'
import { useToast } from '@/hooks/use-toast'
import { auditService } from '@/services/api.service'
import type { AuditLog } from '@/types'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Download } from 'lucide-react'

export default function AuditLogs() {
  const [logs, setLogs] = useState<AuditLog[]>([])
  const [loading, setLoading] = useState(true)
  const { isAuthenticated } = useAuth()
  const { toast } = useToast()

  useEffect(() => {
    if (isAuthenticated) {
      fetchLogs()
    }
  }, [isAuthenticated])

  const fetchLogs = async () => {
    try {
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
      a.download = `audit-logs-${new Date().toISOString()}.${format}`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
      
      toast({
        title: "Export successful",
        description: `Audit logs exported as ${format.toUpperCase()}`
      })
    } catch (error: any) {
      toast({
        title: "Export failed",
        description: error.response?.data?.detail || "Please try again",
        variant: "destructive"
      })
    }
  }

  const formatChanges = (changes: Record<string, any> | undefined) => {
    if (!changes) return 'No changes recorded'
    return JSON.stringify(changes, null, 2)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-lg">Loading audit logs...</div>
      </div>
    )
  }

  return (
    <div className="container mx-auto p-4 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Audit Logs</h1>
        <div className="space-x-2">
          <Button onClick={() => handleExport('json')} variant="outline" size="sm">
            <Download className="mr-2 h-4 w-4" /> Export JSON
          </Button>
          <Button onClick={() => handleExport('csv')} variant="outline" size="sm">
            <Download className="mr-2 h-4 w-4" /> Export CSV
          </Button>
        </div>
      </div>

      {logs.length === 0 ? (
        <Card>
          <CardContent className="p-6 text-center">
            <p className="text-lg">No audit logs found</p>
            <p className="text-muted-foreground">System activity will appear here</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {logs.map((log) => (
            <Card key={log.id}>
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  <span>{log.action}</span>
                  <span className="text-sm font-normal text-muted-foreground">
                    {new Date(log.created_at).toLocaleString()}
                  </span>
                </CardTitle>
                <CardDescription>
                  {log.entity_type}
                  {log.entity_id && ` #${log.entity_id}`}
                  {log.user_id && ` • User ID: ${log.user_id}`}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {log.changes && (
                    <div>
                      <p className="text-sm font-medium">Changes:</p>
                      <pre className="text-xs bg-muted p-2 rounded mt-1 overflow-x-auto">
                        {formatChanges(log.changes)}
                      </pre>
                    </div>
                  )}
                  {log.ip_address && (
                    <p className="text-xs text-muted-foreground">
                      IP: {log.ip_address}
                    </p>
                  )}
                  {log.user_agent && (
                    <p className="text-xs text-muted-foreground truncate">
                      User Agent: {log.user_agent}
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
