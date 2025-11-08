import { useState, useEffect } from 'react'
import { useAuth } from '@/context/AuthContext'
import { useToast } from '@/hooks/use-toast'
import { connectorService } from '@/services/api.service'
import type { Connector, ConnectorCreate, ConnectorUpdate, KimaiConnectorConfig } from '@/types'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Loader2, Plus, Trash2, AlertTriangle } from 'lucide-react'
import ZammadIcon from '@/assets/icons/zammad-logo-only.svg?react'
import KimaiIcon from '@/assets/icons/kimai-logo-only.svg?react'

interface ConnectorFormData {
  type: 'zammad' | 'kimai'
  name: string
  base_url: string
  api_token: string
  is_active: boolean
  settings?: KimaiConnectorConfig
}

export default function Connectors() {
  const [connectors, setConnectors] = useState<Connector[]>([])
  const [sortBy, setSortBy] = useState<'name' | 'type' | 'active'>('name')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [validating, setValidating] = useState(false)
  const [testing, setTesting] = useState(false)
  const [connectionValid, setConnectionValid] = useState<boolean | null>(null)
  const [editing, setEditing] = useState<number | null>(null)
  const [formData, setFormData] = useState<ConnectorFormData>({
    type: 'zammad',
    name: '',
    base_url: '',
    api_token: '',
    is_active: true
  })
  const [errors, setErrors] = useState<Record<string, string | null>>({})
  const [isFormValid, setIsFormValid] = useState(false)
  const { isAuthenticated } = useAuth()
  const { toast } = useToast()

  useEffect(() => {
    if (isAuthenticated) {
      fetchConnectors()
    }
  }, [isAuthenticated, sortBy])

  const fetchConnectors = async () => {
    try {
      const data = await connectorService.getAll()
      let sorted = [...data];
      if (sortBy === 'name') {
        sorted.sort((a, b) => a.name.localeCompare(b.name));
      } else if (sortBy === 'type') {
        sorted.sort((a, b) => a.type.localeCompare(b.type));
      } else if (sortBy === 'active') {
        sorted.sort((a, b) => Number(b.is_active) - Number(a.is_active));
      }
      setConnectors(sorted)
    } catch (error: any) {
      toast({
        title: "Failed to load connectors",
        description: error.response?.data?.detail || "Please try again later",
        variant: "destructive"
      })
    } finally {
      setLoading(false)
    }
  }

  const resetForm = () => {
    setFormData({
      type: 'zammad',
      name: '',
      base_url: '',
      api_token: '',
      is_active: true,
      settings: {
        use_global_activities: true,
        default_project_id: null,
        ignore_unmapped_activities: false,
        default_country: 'BE',
        default_currency: 'EUR',
        default_timezone: 'Europe/Brussels'
      }
    })
  }

  const startEdit = (connector?: Connector) => {
    if (connector) {
      setFormData({
        type: connector.type,
        name: connector.name,
        base_url: connector.base_url,
        api_token: '', // Don't pre-fill token for security
        is_active: connector.is_active,
        settings: connector.type === 'kimai' ? (connector.settings as KimaiConnectorConfig || {
          use_global_activities: true,
          default_project_id: null,
          ignore_unmapped_activities: false,
          default_country: 'BE',
          default_currency: 'EUR',
          default_timezone: 'Europe/Brussels'
        }) : undefined
      })
      setEditing(connector.id)
    } else {
      resetForm()
      setEditing(0)
    }
  }

  const handleSave = async () => {
    if (!formData.name || !formData.base_url || !formData.api_token) {
      toast({
        title: "Validation error",
        description: "Please fill in all required fields",
        variant: "destructive"
      })
      return
    }

    // Validate URL
    let url: URL
    try {
      url = new URL(formData.base_url)
      if (!url.protocol) {
        throw new Error("Invalid URL format")
      }
      if (formData.base_url.startsWith("http://")) {
        toast({
          title: "Security recommendation",
          description: "Consider using HTTPS for secure connections. The URL will be automatically upgraded.",
          variant: "default"
        })
      }
    } catch (e) {
      toast({
        title: "Invalid URL",
        description: "Please enter a valid URL (e.g., https://example.com)",
        variant: "destructive"
      })
      return
    }

    setSaving(true)
    try {
      if (editing && editing !== 0) {
        // Update existing connector
        const updateData: ConnectorUpdate = {
          name: formData.name,
          base_url: formData.base_url,
          is_active: formData.is_active
        }
        // Only include token if it was changed
        if (formData.api_token) {
          updateData.api_token = formData.api_token
        }
        // Include settings for Kimai connectors
        if (formData.type === 'kimai' && formData.settings) {
          updateData.settings = formData.settings
        }
        await connectorService.update(editing, updateData)
        toast({
          title: "Connector updated",
          description: "Changes saved successfully"
        })
      } else {
        // Create new connector
        const createData: ConnectorCreate = {
          type: formData.type,
          name: formData.name,
          base_url: formData.base_url,
          api_token: formData.api_token,
          is_active: formData.is_active
        }
        // Include settings for Kimai connectors
        if (formData.type === 'kimai' && formData.settings) {
          createData.settings = formData.settings
        }
        await connectorService.create(createData)
        toast({
          title: "Connector created",
          description: "New connector added successfully"
        })
      }
      setEditing(null)
      resetForm()
      fetchConnectors()
    } catch (error: any) {
      toast({
        title: "Failed to save connector",
        description: error.response?.data?.detail || "Please check your input",
        variant: "destructive"
      })
    } finally {
      setSaving(false)
    }
  }

  const handleValidate = async (id: number) => {
    setValidating(true)
    try {
      const result = await connectorService.validate(id)
      toast({
        title: result.valid ? "Connection successful" : "Connection failed",
        description: result.message,
        variant: result.valid ? "default" : "destructive"
      })
    } catch (error: any) {
      toast({
        title: "Validation failed",
        description: error.response?.data?.detail || "Please try again",
        variant: "destructive"
      })
    } finally {
      setValidating(false)
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this connector?')) return
    try {
      await connectorService.delete(id)
      toast({
        title: "Connector deleted",
        description: "Connector removed successfully"
      })
      fetchConnectors()
    } catch (error: any) {
      toast({
        title: "Failed to delete connector",
        description: error.response?.data?.detail || "Please try again",
        variant: "destructive"
      })
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-lg">Loading connectors...</div>
      </div>
    )
  }

  return (
    <div className="container mx-auto p-4 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Connectors</h1>
        <div className="flex items-center space-x-4">
          <Select value={sortBy} onValueChange={(value) => setSortBy(value as 'name' | 'type' | 'active')}>
            <SelectTrigger className="w-40">
              <SelectValue placeholder="Sort by" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="name">Name</SelectItem>
              <SelectItem value="type">Type</SelectItem>
              <SelectItem value="active">Status</SelectItem>
            </SelectContent>
          </Select>
          <Button onClick={() => startEdit()} variant="outline">
            <Plus className="mr-2 h-4 w-4" /> Add Connector
          </Button>
        </div>
      </div>

      {connectors.length === 0 ? (
        <Card>
          <CardContent className="p-6 text-center">
            <p className="text-lg">No connectors configured</p>
            <p className="text-muted-foreground">Add a Zammad or Kimai connector to get started</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {connectors.map((connector) => (
            <Card key={connector.id} className="hover:shadow-modern transition-shadow">
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      {connector.type === 'zammad' ? (
                        <ZammadIcon className="h-5 w-5 text-primary" />
                      ) : (
                        <KimaiIcon className="h-5 w-5 text-primary" />
                      )}
                      <span>{connector.name}</span>
                    </div>
                  <div className="flex items-center space-x-1">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${connector.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}>
                      {connector.is_active ? "Active" : "Inactive"}
                    </span>
                    <span className="px-2 py-1 rounded-full text-xs font-medium bg-primary/10 text-primary">
                      {connector.type.toUpperCase()}
                    </span>
                  </div>
                </CardTitle>
                <CardDescription>
                  ID: {connector.id} • Last validated: {new Date(connector.updated_at).toLocaleString()}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="space-y-1">
                  <p className="text-sm font-medium">URL</p>
                  <p className="text-sm text-muted-foreground truncate">
                    {connector.base_url}
                  </p>
                </div>
                <div className="flex flex-col space-y-1">
                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={() => handleValidate(connector.id)}
                    disabled={validating}
                    className="w-full shadow-modern"
                  >
                    {validating && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                    Test Connection
                  </Button>
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    onClick={() => startEdit(connector)}
                    className="w-full"
                  >
                    Edit
                  </Button>
                  <Button 
                    variant="destructive" 
                    size="sm" 
                    onClick={() => handleDelete(connector.id)}
                    className="w-full"
                  >
                    <Trash2 className="mr-2 h-4 w-4" /> Delete
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {editing !== null && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-background p-6 rounded-lg max-w-md w-full">
            <h2 className="text-xl font-bold mb-4">
              {editing === 0 ? 'Add New Connector' : 'Edit Connector'}
            </h2>
            <div className="space-y-4">
              {editing !== 0 && (
                <div className="mb-4 p-3 bg-muted/50 rounded-md">
                  <label className="text-sm font-medium mb-2 block">Type</label>
                  <div className="flex items-center space-x-2">
                    {formData.type === 'zammad' ? (
                      <ZammadIcon className="h-4 w-4 text-primary" />
                    ) : (
                      <KimaiIcon className="h-4 w-4 text-primary" />
                    )}
                    <span className="text-sm font-medium capitalize">{formData.type}</span>
                  </div>
                </div>
              )}
              {editing === 0 && (
                <div>
                  <label className="text-sm font-medium mb-2 block">Type</label>
                  <Select 
                    value={formData.type} 
                    onValueChange={(value) => setFormData({ ...formData, type: value as 'zammad' | 'kimai' })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="zammad">Zammad</SelectItem>
                      <SelectItem value="kimai">Kimai</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              )}
              <div>
                <label className="text-sm font-medium mb-2 block">Name</label>
                <Input 
                  placeholder="My Connector" 
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                />
              </div>
              <div>
                <label className="text-sm font-medium mb-2 block">Base URL</label>
                <Input 
                  placeholder="https://example.com" 
                  value={formData.base_url}
                  onChange={(e) => setFormData({ ...formData, base_url: e.target.value })}
                />
                {formData.type === 'kimai' && formData.base_url.startsWith('http://') && (
                  <Alert className="mt-2 border-yellow-500 bg-yellow-50">
                    <AlertTriangle className="h-4 w-4 text-yellow-600" />
                    <AlertDescription className="text-sm text-yellow-800">
                      <strong>Security Notice:</strong> Kimai requires HTTPS for secure connections. 
                      The system will automatically redirect HTTP to HTTPS, but please update the URL 
                      to <span className="font-mono">https://</span> for better reliability.
                    </AlertDescription>
                  </Alert>
                )}
              </div>
              <div>
                <label className="text-sm font-medium mb-2 block">
                  API Token {editing !== 0 && '(leave empty to keep current)'}
                </label>
                <Input 
                  type="password" 
                  placeholder="Enter API token" 
                  value={formData.api_token}
                  onChange={(e) => setFormData({ ...formData, api_token: e.target.value })}
                />
              </div>
              <div className="flex items-center space-x-2">
                <input 
                  type="checkbox" 
                  id="active" 
                  checked={formData.is_active}
                  onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                  className="h-4 w-4"
                />
                <label htmlFor="active" className="text-sm font-medium">Active</label>
              </div>

              {formData.type === 'kimai' && (
                <>
                  <div className="border-t pt-4">
                    <h3 className="text-sm font-semibold mb-3">Kimai Configuration</h3>
                    <div className="space-y-3">
                      <div className="flex items-center space-x-2">
                        <input 
                          type="checkbox" 
                          id="use_global_activities" 
                          checked={formData.settings?.use_global_activities ?? true}
                          onChange={(e) => setFormData({ 
                            ...formData, 
                            settings: { ...formData.settings!, use_global_activities: e.target.checked }
                          })}
                          className="h-4 w-4"
                        />
                        <label htmlFor="use_global_activities" className="text-sm">Use Global Activities</label>
                      </div>
                      <div className="flex items-center space-x-2">
                        <input 
                          type="checkbox" 
                          id="ignore_unmapped_activities" 
                          checked={formData.settings?.ignore_unmapped_activities ?? false}
                          onChange={(e) => setFormData({ 
                            ...formData, 
                            settings: { ...formData.settings!, ignore_unmapped_activities: e.target.checked }
                          })}
                          className="h-4 w-4"
                        />
                        <label htmlFor="ignore_unmapped_activities" className="text-sm">Ignore Unmapped Activities</label>
                        <p className="text-xs text-muted-foreground ml-6">Skip entries with unmapped Zammad activities instead of flagging as conflicts during sync.</p>
                      </div>
                      <div>
                        <label className="text-sm font-medium mb-2 block">Default Project ID (optional)</label>
                        <Input 
                          type="number" 
                          placeholder="e.g., 123" 
                          value={formData.settings?.default_project_id ?? ''}
                          onChange={(e) => setFormData({ 
                            ...formData, 
                            settings: { ...formData.settings!, default_project_id: e.target.value ? parseInt(e.target.value) : null }
                          })}
                        />
                        <p className="text-xs text-muted-foreground mt-1">Used when global activities is disabled</p>
                      </div>
                      <div>
                        <label className="text-sm font-medium mb-2 block">Default Country</label>
                        <Input 
                          placeholder="BE" 
                          value={formData.settings?.default_country ?? 'BE'}
                          onChange={(e) => setFormData({ 
                            ...formData, 
                            settings: { ...formData.settings!, default_country: e.target.value }
                          })}
                        />
                      </div>
                      <div>
                        <label className="text-sm font-medium mb-2 block">Default Currency</label>
                        <Input 
                          placeholder="EUR" 
                          value={formData.settings?.default_currency ?? 'EUR'}
                          onChange={(e) => setFormData({ 
                            ...formData, 
                            settings: { ...formData.settings!, default_currency: e.target.value }
                          })}
                        />
                      </div>
                      <div>
                        <label className="text-sm font-medium mb-2 block">Default Timezone</label>
                        <Input 
                          placeholder="Europe/Brussels" 
                          value={formData.settings?.default_timezone ?? 'Europe/Brussels'}
                          onChange={(e) => setFormData({ 
                            ...formData, 
                            settings: { ...formData.settings!, default_timezone: e.target.value }
                          })}
                        />
                      </div>
                    </div>
                  </div>
                </>
              )}

              <div className="flex justify-end space-x-2 pt-4">
                <Button 
                  variant="outline" 
                  onClick={() => { setEditing(null); resetForm(); }}
                >
                  Cancel
                </Button>
                <Button onClick={handleSave} disabled={saving}>
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
