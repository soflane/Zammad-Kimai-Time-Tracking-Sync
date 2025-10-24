import { useState, useEffect } from 'react'
import { useAuth } from '@/context/AuthContext'
import { useToast } from '@/hooks/use-toast'
import { conflictService } from '@/services/api.service'
import type { Conflict } from '@/types'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { AlertCircle, CheckCircle, XCircle } from 'lucide-react'

export default function Conflicts() {
  const [conflicts, setConflicts] = useState<Conflict[]>([])
  const [loading, setLoading] = useState(true)
  const { isAuthenticated } = useAuth()
  const { toast } = useToast()

  useEffect(() => {
    if (isAuthenticated) {
      fetchConflicts()
    }
  }, [isAuthenticated])

  const fetchConflicts = async () => {
    try {
      const data = await conflictService.getAll()
      setConflicts(data)
    } catch (error: any) {
      toast({
        title: "Failed to load conflicts",
        description: error.response?.data?.detail || "Please try again later",
        variant: "destructive"
      })
    } finally {
      setLoading(false)
    }
  }

  const handleResolve = async (id: number, resolution: 'resolved' | 'ignored') => {
    try {
      await conflictService.resolve(id, { resolution_status: resolution })
      toast({
        title: "Conflict updated",
        description: `Conflict marked as ${resolution}`
      })
      fetchConflicts()
    } catch (error: any) {
      toast({
        title: "Failed to update conflict",
        description: error.response?.data?.detail || "Please try again",
        variant: "destructive"
      })
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-lg">Loading conflicts...</div>
      </div>
    )
  }

  return (
    <div className="container mx-auto p-4 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Conflicts</h1>
      </div>

      {conflicts.length === 0 ? (
        <Card>
          <CardContent className="p-6 text-center">
            <CheckCircle className="mx-auto h-12 w-12 text-green-500 mb-4" />
            <p className="text-lg">No conflicts found</p>
            <p className="text-muted-foreground">All time entries are syncing smoothly</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {conflicts.map((conflict) => (
            <Card key={conflict.id} className={
              conflict.resolution_status === 'resolved' ? 'border-green-500' :
              conflict.resolution_status === 'ignored' ? 'border-gray-500' :
              'border-red-500'
            }>
              <CardHeader>
                <CardTitle className="flex items-center">
                  {conflict.resolution_status === 'pending' && (
                    <AlertCircle className="mr-2 h-5 w-5 text-red-500" />
                  )}
                  {conflict.resolution_status === 'resolved' && (
                    <CheckCircle className="mr-2 h-5 w-5 text-green-500" />
                  )}
                  {conflict.resolution_status === 'ignored' && (
                    <XCircle className="mr-2 h-5 w-5 text-gray-500" />
                  )}
                  Conflict #{conflict.id} - {conflict.conflict_type}
                </CardTitle>
                <CardDescription>
                  Created: {new Date(conflict.created_at).toLocaleString()}
                  {conflict.resolved_at && ` | Resolved: ${new Date(conflict.resolved_at).toLocaleString()}`}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <p className="text-sm font-medium">Source Entry ID:</p>
                    <p className="text-sm text-muted-foreground">{conflict.source_entry_id}</p>
                  </div>
                  {conflict.target_entry_id && (
                    <div>
                      <p className="text-sm font-medium">Target Entry ID:</p>
                      <p className="text-sm text-muted-foreground">{conflict.target_entry_id}</p>
                    </div>
                  )}
                  <div>
                    <p className="text-sm font-medium">Conflict Data:</p>
                    <pre className="text-xs bg-muted p-2 rounded mt-1 overflow-x-auto">
                      {JSON.stringify(conflict.conflict_data, null, 2)}
                    </pre>
                  </div>
                  {conflict.resolution_status === 'pending' && (
                    <div className="flex space-x-2 pt-2">
                      <Button 
                        size="sm" 
                        variant="default"
                        onClick={() => handleResolve(conflict.id, 'resolved')}
                      >
                        Mark as Resolved
                      </Button>
                      <Button 
                        size="sm" 
                        variant="outline"
                        onClick={() => handleResolve(conflict.id, 'ignored')}
                      >
                        Ignore
                      </Button>
                    </div>
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
