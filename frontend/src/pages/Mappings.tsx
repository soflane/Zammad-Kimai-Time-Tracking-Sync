import { useState, useEffect } from 'react'
import { useAuth } from '@/context/AuthContext'
import { useToast } from '@/hooks/use-toast'
import { mappingService, connectorService } from '@/services/api.service'
import type { ActivityMapping, ActivityMappingCreate, Connector, Activity } from '@/types'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Loader2, Plus, Trash2, Edit, MapPin, Database } from 'lucide-react'

interface MappingFormData {
  zammad_type_id: number
  zammad_type_name: string
  kimai_activity_id: number
  kimai_activity_name: string
}

export default function Mappings() {
  const [mappings, setMappings] = useState<ActivityMapping[]>([])
  const [connectors, setConnectors] = useState<Connector[]>([])
  const [zammadActivities, setZammadActivities] = useState<Activity[]>([])
  const [kimaiActivities, setKimaiActivities] = useState<Activity[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [editing, setEditing] = useState<number | null>(null)
  const [formData, setFormData] = useState<MappingFormData>({
    zammad_type_id: 0,
    zammad_type_name: '',
    kimai_activity_id: 0,
    kimai_activity_name: ''
  })
  const { isAuthenticated } = useAuth()
  const { toast } = useToast()

  useEffect(() => {
    if (isAuthenticated) {
      fetchData()
    }
  }, [isAuthenticated])

  const fetchData = async () => {
    try {
      const [mappingsData, connectorsData] = await Promise.all([
        mappingService.getAll(),
        connectorService.getAll()
      ])
      setMappings(mappingsData)
      setConnectors(connectorsData)

      // Fetch activities from active connectors
      const zammadConnector = connectorsData.find(c => c.type === 'zammad' && c.is_active)
      const kimaiConnector = connectorsData.find(c => c.type === 'kimai' && c.is_active)

      if (zammadConnector) {
        const activities = await connectorService.getActivities(zammadConnector.id)
        setZammadActivities(activities)
      }

      if (kimaiConnector) {
        const activities = await connectorService.getActivities(kimaiConnector.id)
        setKimaiActivities(activities)
      }
    } catch (error: any) {
      toast({
        title: "Failed to load data",
        description: error.response?.data?.detail || "Please try again later",
        variant: "destructive"
      })
    } finally {
      setLoading(false)
    }
  }

  const resetForm = () => {
    setFormData({
      zammad_type_id: 0,
      zammad_type_name: '',
      kimai_activity_id: 0,
      kimai_activity_name: ''
    })
  }

  const startEdit = (mapping?: ActivityMapping) => {
    if (mapping) {
      setFormData({
        zammad_type_id: mapping.zammad_type_id,
        zammad_type_name: mapping.zammad_type_name,
        kimai_activity_id: mapping.kimai_activity_id,
        kimai_activity_name: mapping.kimai_activity_name
      })
      setEditing(mapping.id)
    } else {
      resetForm()
      setEditing(0)
    }
  }

  const handleSave = async () => {
    if (!formData.zammad_type_id || !formData.kimai_activity_id) {
      toast({
        title: "Validation error",
        description: "Please select both Zammad and Kimai activities",
        variant: "destructive"
      })
      return
    }

    setSaving(true)
    try {
      if (editing && editing !== 0) {
        // Update existing mapping
        await mappingService.update(editing, {
          kimai_activity_id: formData.kimai_activity_id,
          kimai_activity_name: formData.kimai_activity_name
        })
        toast({
          title: "Mapping updated",
          description: "Changes saved successfully"
        })
      } else {
        // Create new mapping
        const createData: ActivityMappingCreate = {
          zammad_type_id: formData.zammad_type_id,
          zammad_type_name: formData.zammad_type_name,
          kimai_activity_id: formData.kimai_activity_id,
          kimai_activity_name: formData.kimai_activity_name
        }
        await mappingService.create(createData)
        toast({
          title: "Mapping created",
          description: "New mapping added successfully"
        })
      }
      setEditing(null)
      resetForm()
      fetchData()
    } catch (error: any) {
      toast({
        title: "Failed to save mapping",
        description: error.response?.data?.detail || "This mapping may already exist",
        variant: "destructive"
      })
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this mapping?')) return
    try {
      await mappingService.delete(id)
      toast({
        title: "Mapping deleted",
        description: "Mapping removed successfully"
      })
      fetchData()
    } catch (error: any) {
      toast({
        title: "Failed to delete mapping",
        description: error.response?.data?.detail || "Please try again",
        variant: "destructive"
      })
    }
  }

  const handleZammadSelect = (activityId: string) => {
    const activity = zammadActivities.find(a => a.id.toString() === activityId)
    if (activity) {
      setFormData({
        ...formData,
        zammad_type_id: activity.id,
        zammad_type_name: activity.name
      })
    }
  }

  const handleKimaiSelect = (activityId: string) => {
    const activity = kimaiActivities.find(a => a.id.toString() === activityId)
    if (activity) {
      setFormData({
        ...formData,
        kimai_activity_id: activity.id,
        kimai_activity_name: activity.name
      })
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-lg">Loading mappings...</div>
      </div>
    )
  }

  const hasActiveConnectors = connectors.some(c => c.type === 'zammad' && c.is_active) && 
                              connectors.some(c => c.type === 'kimai' && c.is_active)

  return (
    <div className="container mx-auto p-4 space-y-6">
      <div className="flex justify-between items-center">
        <div className="flex items-center space-x-2">
          <MapPin className="h-6 w-6 text-primary" />
          <div>
            <h1 className="text-2xl font-bold">Activity Mappings</h1>
            <p className="text-muted-foreground">Map Zammad activity types to Kimai activities</p>
          </div>
        </div>
        <Button 
          onClick={() => startEdit()} 
          variant="outline"
          disabled={!hasActiveConnectors}
          className="shadow-modern"
        >
          <Plus className="mr-2 h-4 w-4" /> Add Mapping
        </Button>
      </div>

      {!hasActiveConnectors && (
        <Card className="border-yellow-500">
          <CardContent className="p-6">
            <p className="text-sm text-yellow-700">
              Please configure and activate both Zammad and Kimai connectors before creating mappings.
            </p>
          </CardContent>
        </Card>
      )}

      {mappings.length === 0 ? (
        <Card>
          <CardContent className="p-6 text-center">
            <p className="text-lg">No activity mappings configured</p>
            <p className="text-muted-foreground">
              Create mappings to sync time entries with the correct activities
            </p>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>Configured Mappings</CardTitle>
            <CardDescription>
              {mappings.length} mapping{mappings.length !== 1 ? 's' : ''} configured
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {mappings.map((mapping) => (
                <div 
                  key={mapping.id}
                  className="p-4 border rounded-lg hover:shadow-modern transition-shadow bg-card hover:bg-accent/10"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1 space-y-2">
                      <div className="flex items-center space-x-2">
                        <Database className="h-4 w-4 text-blue-500" />
                        <p className="text-sm font-medium text-muted-foreground">
                          Zammad: {mapping.zammad_type_name} (ID: {mapping.zammad_type_id})
                        </p>
                      </div>
                      <div className="flex items-center space-x-2">
                        <Database className="h-4 w-4 text-green-500" />
                        <p className="text-sm font-medium text-muted-foreground">
                          Kimai: {mapping.kimai_activity_name} (ID: {mapping.kimai_activity_id})
                        </p>
                      </div>
                    </div>
                    <div className="flex space-x-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => startEdit(mapping)}
                        className="h-8 w-8 p-0"
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDelete(mapping.id)}
                        className="h-8 w-8 p-0 text-destructive"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {editing !== null && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-background p-6 rounded-lg max-w-md w-full">
            <h2 className="text-xl font-bold mb-4">
              {editing === 0 ? 'Add New Mapping' : 'Edit Mapping'}
            </h2>
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium mb-2 block flex items-center">
                  <Database className="h-4 w-4 mr-2 text-blue-500" />
                  Zammad Activity Type
                </label>
                <Select 
                  value={formData.zammad_type_id.toString()}
                  onValueChange={handleZammadSelect}
                  disabled={editing !== 0}
                >
                  <SelectTrigger className="shadow-modern">
                    <SelectValue placeholder="Select Zammad activity" />
                  </SelectTrigger>
                  <SelectContent>
                    {zammadActivities.map((activity) => (
                      <SelectItem key={activity.id} value={activity.id.toString()}>
                        {activity.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {editing !== 0 && (
                  <p className="text-xs text-muted-foreground mt-1">
                    Zammad activity cannot be changed after creation
                  </p>
                )}
              </div>
              <div>
                <label className="text-sm font-medium mb-2 block flex items-center">
                  <Database className="h-4 w-4 mr-2 text-green-500" />
                  Kimai Activity
                </label>
                <Select 
                  value={formData.kimai_activity_id.toString()}
                  onValueChange={handleKimaiSelect}
                >
                  <SelectTrigger className="shadow-modern">
                    <SelectValue placeholder="Select Kimai activity" />
                  </SelectTrigger>
                  <SelectContent>
                    {kimaiActivities.map((activity) => (
                      <SelectItem key={activity.id} value={activity.id.toString()}>
                        {activity.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex justify-end space-x-2 pt-4">
                <Button 
                  variant="outline" 
                  onClick={() => { setEditing(null); resetForm(); }}
                  className="shadow-modern"
                >
                  Cancel
                </Button>
                <Button onClick={handleSave} disabled={saving} className="shadow-modern">
                  {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  {saving ? 'Saving...' : editing === 0 ? 'Create' : 'Update'}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
