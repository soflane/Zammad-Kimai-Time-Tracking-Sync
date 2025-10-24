import { useState, useEffect } from 'react'
import { useAuth } from '@/context/AuthContext'
import { useToast } from '@/hooks/use-toast'
import { conflictService } from '@/services/api.service'
import type { Conflict } from '@/types'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { AlertCircle, CheckCircle, XCircle, ChevronDown, ChevronUp } from 'lucide-react'

export default function Conflicts() {
  const [conflicts, setConflicts] = useState<Conflict[]>([])
  const [expanded, setExpanded] = useState<Set<number>>(new Set())
  const [loading, setLoading] = useState(true)
  const { isAuthenticated } = useAuth()
  const { toast } = useToast()

  const toggleExpand = (id: number) => {
    const newExpanded = new Set(expanded)
    if (expanded.has(id)) {
      newExpanded.delete(id)
    } else {
      newExpanded.add(id)
    }
    setExpanded(newExpanded)
  }

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
        <div className="flex items-center space-x-2">
          <AlertCircle className="h-6 w-6 text-destructive" />
          <h1 className="text-2xl font-bold">Conflicts</h1>
        </div>
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
            <Card key={conflict.id} className="hover:shadow-modern transition-shadow">
              <CardHeader className="cursor-pointer" onClick={() => toggleExpand(conflict.id)}>
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center space-x-2">
                    {conflict.resolution_status === 'pending' && (
                      <AlertCircle className="h-5 w-5 text-destructive" />
                    )}
                    {conflict.resolution_status === 'resolved' && (
                      <CheckCircle className="h-5 w-5 text-green-500" />
                    )}
                    {conflict.resolution_status === 'ignored' && (
                      <XCircle className="h-5 w-5 text-gray-500" />
                    )}
                    <span className="px-2 py-1 rounded-full text-xs font-medium bg-primary/10 text-primary">
                      {conflict.conflict_type.toUpperCase()}
                    </span>
                    Conflict #{conflict.id}
                  </CardTitle>
                  <div className="flex items-center space-x-2">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      conflict.resolution_status === 'resolved' ? 'bg-green-100 text-green-800' :
                      conflict.resolution_status === 'ignored' ? 'bg-gray-100 text-gray-800' : 'bg-red-100 text-red-800'
                    }`}>
                      {conflict.resolution_status}
                    </span>
                    {expanded.has(conflict.id) ? (
                      <ChevronUp className="h-4 w-4" />
                    ) : (
                      <ChevronDown className="h-4 w-4" />
                    )}
                  </div>
                </div>
                <CardDescription className="mt-2">
                  Created: {new Date(conflict.created_at).toLocaleString()}
                  {conflict.resolved_at && ` | Resolved: ${new Date(conflict.resolved_at).toLocaleString()}`}
                </CardDescription>
              </CardHeader>
              {expanded.has(conflict.id) && (
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm font-medium">Source Entry ID</p>
                      <p className="text-sm text-muted-foreground">{conflict.source_entry_id}</p>
                    </div>
                    {conflict.target_entry_id && (
                      <div>
                        <p className="text-sm font-medium">Target Entry ID</p>
                        <p className="text-sm text-muted-foreground">{conflict.target_entry_id}</p>
                      </div>
                    )}
                  </div>
                  <div>
                    <p className="text-sm font-medium">Conflict Data</p>
                    <pre className="text-xs bg-muted p-2 rounded mt-1 overflow-x-auto max-h-32 overflow-y-auto">
                      {JSON.stringify(conflict.conflict_data, null, 2)}
                    </pre>
                  </div>
                  {conflict.resolution_status === 'pending' && (
                    <div className="flex space-x-2">
                      <Button 
                        size="sm" 
                        variant="default"
                        onClick={() => handleResolve(conflict.id, 'resolved')}
                        className="shadow-modern"
                      >
                        <CheckCircle className="mr-2 h-4 w-4" />
                        Mark as Resolved
                      </Button>
                      <Button 
                        size="sm" 
                        variant="outline"
                        onClick={() => handleResolve(conflict.id, 'ignored')}
                        className="shadow-modern"
                      >
                        <XCircle className="mr-2 h-4 w-4" />
                        Ignore
                      </Button>
                    </div>
                  )}
                </CardContent>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
