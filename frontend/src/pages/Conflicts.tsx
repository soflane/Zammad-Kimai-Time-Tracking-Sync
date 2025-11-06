import { useState, useEffect } from 'react'
import { useAuth } from '@/context/AuthContext'
import { useToast } from '@/hooks/use-toast'
import { conflictService } from '@/services/api.service'
import type { Conflict } from '@/types'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { AlertCircle, CheckCircle, Eye, Loader2, ArrowUpDown, Download } from 'lucide-react'
import { format } from 'date-fns'
import { ConflictDrawer } from '../components/ui/conflict-drawer'

export default function Conflicts() {
  const [conflicts, setConflicts] = useState<Conflict[]>([])
  const [selectedConflict, setSelectedConflict] = useState<Conflict | null>(null)
  const [loading, setLoading] = useState(true)
  const [searchCustomer, setSearchCustomer] = useState('')
  const [debouncedSearchCustomer, setDebouncedSearchCustomer] = useState('')
  const [searchTicket, setSearchTicket] = useState('')
  const [debouncedSearchTicket, setDebouncedSearchTicket] = useState('')
  const [sortField, setSortField] = useState<'date' | 'customer' | 'reason'>('date')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())
  const [selectAll, setSelectAll] = useState(false)
  const { isAuthenticated } = useAuth()
  const { toast } = useToast()

  const getStatusBadge = (status: string) => {
    const classNames = {
      'resolved': 'bg-green-100 text-green-800',
      'ignored': 'bg-gray-100 text-gray-800',
      'pending': 'bg-red-100 text-red-800'
    }
    const cn = classNames[status as keyof typeof classNames] || 'bg-red-100 text-red-800'
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${cn}`}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    )
  }

  const getReasonBadge = (code: string) => {
    const classMap = {
      'UNMAPPED_ACTIVITY': 'bg-secondary text-secondary-foreground',
      'DUPLICATE': 'bg-yellow-100 text-yellow-800',
      'TIME_MISMATCH': 'bg-destructive text-destructive-foreground',
      'PROJECT_OR_CUSTOMER_MISSING': 'bg-muted text-muted-foreground',
      'LOCKED_OR_EXPORTED': 'bg-secondary text-secondary-foreground',
      'CREATION_ERROR': 'bg-destructive text-destructive-foreground',
      'OTHER': 'bg-primary/10 text-primary'
    }
    const cn = classMap[code as keyof typeof classMap] || 'bg-primary/10 text-primary'
    return (
      <span className={`px-2 py-1 rounded-full text-xs font-medium ${cn}`}>
        {code}
      </span>
    )
  }

  const formatDate = (dateStr: string | undefined) => {
    if (!dateStr) return 'N/A'
    return format(new Date(dateStr), 'MMM dd, yyyy HH:mm')
  }

  const getDuration = (conflict: Conflict) => {
    const duration = conflict.kimai_duration_minutes ?? conflict.zammad_time_minutes
    return duration ? `${duration.toFixed(1)} min` : 'N/A'
  }

  const getStart = (conflict: Conflict) => {
    return formatDate(conflict.kimai_begin || conflict.zammad_entry_date ? `${conflict.zammad_entry_date || ''}` : undefined)
  }

  const getEnd = (conflict: Conflict) => {
    return formatDate(conflict.kimai_end)
  }

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearchCustomer(searchCustomer)
    }, 300)
    return () => clearTimeout(timer)
  }, [searchCustomer])

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearchTicket(searchTicket)
    }, 300)
    return () => clearTimeout(timer)
  }, [searchTicket])

  const filteredAndSortedConflicts = conflicts
    .filter(c => 
      (!debouncedSearchCustomer || (c.customer_name || '').toLowerCase().includes(debouncedSearchCustomer.toLowerCase())) &&
      (!debouncedSearchTicket || (c.ticket_number || '').includes(debouncedSearchTicket))
    )
    .sort((a, b) => {
      let valA, valB
      if (sortField === 'date') {
        valA = a.zammad_entry_date || ''
        valB = b.zammad_entry_date || ''
      } else if (sortField === 'customer') {
        valA = a.customer_name || ''
        valB = b.customer_name || ''
      } else {
        valA = a.reason_code || ''
        valB = b.reason_code || ''
      }
      if (valA < valB) return sortOrder === 'asc' ? -1 : 1
      if (valA > valB) return sortOrder === 'asc' ? 1 : -1
      return 0
    })

  const toggleSort = (field: 'date' | 'customer' | 'reason') => {
    if (sortField !== field) {
      setSortField(field)
      setSortOrder('asc')
    } else {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    }
  }

  useEffect(() => {
    if (isAuthenticated) {
      fetchConflicts()
    }
  }, [isAuthenticated])

  const fetchConflicts = async () => {
    try {
      setLoading(true)
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
        description: `Conflict marked as ${resolution}`,
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

  const handleAction = async (id: number, action: 'create' | 'update' | 'skip', notes?: string) => {
    try {
      await conflictService.resolve(id, { 
        resolution_status: 'resolved', 
        resolution_action: action, 
        notes 
      })
      toast({
        title: "Conflict resolved",
        description: `Action '${action.toUpperCase()}' applied successfully.`,
      })
      setSelectedConflict(null)
      fetchConflicts()
    } catch (error: any) {
      toast({
        title: "Failed to resolve conflict",
        description: error.response?.data?.detail || "Please try again",
        variant: "destructive"
      })
    }
  }

  const handleBulkAction = async (action: 'resolve' | 'ignore' | 'delete') => {
    if (selectedIds.size === 0) return

    const ids = Array.from(selectedIds)
    try {
      if (action === 'delete') {
        if (!window.confirm(`Delete ${selectedIds.size} conflict(s)?`)) return
        await Promise.all(ids.map(id => conflictService.delete(id)))
        toast({ title: "Conflicts deleted", description: `${selectedIds.size} conflicts removed.` })
      } else {
        await Promise.all(ids.map(id => conflictService.resolve(id, { resolution_status: action })))
        toast({ title: "Bulk action applied", description: `${selectedIds.size} conflicts ${action}d.` })
      }
      setSelectedIds(new Set())
      setSelectAll(false)
      fetchConflicts()
    } catch (error: any) {
      toast({
        title: "Bulk action failed",
        description: error.response?.data?.detail || "Please try again",
        variant: "destructive"
      })
    }
  }

  const toggleSelection = (id: number, checked: boolean) => {
    setSelectedIds(prev => {
      const newSet = new Set(prev)
      if (checked) {
        newSet.add(id)
      } else {
        newSet.delete(id)
      }
      setSelectAll(newSet.size === filteredAndSortedConflicts.length && filteredAndSortedConflicts.length > 0)
      return newSet
    })
  }

  const toggleSelectAll = () => {
    if (selectAll || selectedIds.size === filteredAndSortedConflicts.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(filteredAndSortedConflicts.map(c => c.id)))
    }
    setSelectAll(!selectAll)
  }

  const handleDelete = async (id: number) => {
    if (!window.confirm('Are you sure you want to delete this conflict? This action cannot be undone.')) {
      return
    }
    try {
      await conflictService.delete(id)
      toast({
        title: "Conflict deleted",
        description: "The conflict has been permanently removed.",
      })
      if (selectedConflict?.id === id) {
        setSelectedConflict(null)
      }
      fetchConflicts()
    } catch (error: any) {
      toast({
        title: "Failed to delete conflict",
        description: error.response?.data?.detail || "Please try again",
        variant: "destructive"
      })
    }
  }

  const openDrawer = (conflict: Conflict) => {
    setSelectedConflict(conflict)
  }

  const TableSkeleton = () => (
    <div className="space-y-4">
      <div className="h-4 bg-muted rounded w-full"></div>
      <div className="space-y-2">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="flex gap-4 p-4 border-b">
            <div className="h-4 bg-muted rounded w-16"></div>
            <div className="h-4 bg-muted rounded w-32 flex-1"></div>
            <div className="h-4 bg-muted rounded w-24"></div>
            <div className="h-4 bg-muted rounded w-20"></div>
            <div className="h-4 bg-muted rounded w-32"></div>
            <div className="h-4 bg-muted rounded w-24"></div>
            <div className="h-4 bg-muted rounded w-20"></div>
            <div className="h-4 bg-muted rounded w-16"></div>
            <div className="h-4 bg-muted rounded w-24"></div>
            <div className="h-4 bg-muted rounded w-32"></div>
          </div>
        ))}
      </div>
    </div>
  )

  if (loading) {
    return (
      <div className="container mx-auto p-4 space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <AlertCircle className="h-6 w-6 text-destructive" />
            <h1 className="text-2xl font-bold">Conflicts</h1>
          </div>
        </div>
        <Card>
          <CardContent className="p-6">
            <TableSkeleton />
          </CardContent>
        </Card>
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
        <Button variant="outline" onClick={fetchConflicts} disabled={loading}>
          <Loader2 className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          {loading ? 'Loading...' : 'Refresh'}
        </Button>
      </div>

      {conflicts.length === 0 ? (
        <Card>
          <CardContent className="p-6 text-center">
            <CheckCircle className="mx-auto h-12 w-12 text-green-500 mb-4" />
            <h3 className="text-lg font-semibold mb-2">No conflicts found</h3>
            <p className="text-muted-foreground mb-4">All time entries are syncing smoothly</p>
            <Button variant="outline" onClick={fetchConflicts}>
              <Download className="mr-2 h-4 w-4" />
              Run Sync to Check
            </Button>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader className="px-6">
            <CardTitle>Total Conflicts: {conflicts.length}</CardTitle>
          </CardHeader>
          <CardContent className="p-6">
            {selectedIds.size > 0 && (
              <div className="mb-4 p-3 bg-muted rounded-md flex justify-between items-center">
                <span className="text-sm font-medium">{selectedIds.size} selected</span>
                <div className="flex gap-2">
                  <Button size="sm" variant="default" onClick={() => handleBulkAction('resolve')}>
                    Resolve All
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => handleBulkAction('ignore')}>
                    Ignore All
                  </Button>
                  <Button size="sm" variant="destructive" onClick={() => handleBulkAction('delete')}>
                    Delete All
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => setSelectedIds(new Set())}>
                    Clear
                  </Button>
                </div>
              </div>
            )}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
              <div>
                <label className="text-sm font-medium block mb-2">Filter by Customer</label>
                <input
                  type="text"
                  placeholder="Search customer..."
                  value={searchCustomer}
                  onChange={(e) => setSearchCustomer(e.target.value)}
                  className="w-full p-2 border border-border rounded-md focus:ring-2 focus:ring-primary"
                />
              </div>
              <div>
                <label className="text-sm font-medium block mb-2">Filter by Ticket</label>
                <input
                  type="text"
                  placeholder="Search ticket..."
                  value={searchTicket}
                  onChange={(e) => setSearchTicket(e.target.value)}
                  className="w-full p-2 border border-border rounded-md focus:ring-2 focus:ring-primary"
                />
              </div>
              <div>
                <label className="text-sm font-medium block mb-2">Sort By</label>
                <select
                  value={`${sortField}-${sortOrder}`}
                  onChange={(e) => {
                    const [field, order] = e.target.value.split('-')
                    setSortField(field as 'date' | 'customer' | 'reason')
                    setSortOrder(order as 'asc' | 'desc')
                  }}
                  className="w-full p-2 border border-border rounded-md focus:ring-2 focus:ring-primary"
                >
                  <option value="date-desc">Date (newest)</option>
                  <option value="date-asc">Date (oldest)</option>
                  <option value="customer-asc">Customer A-Z</option>
                  <option value="reason-asc">Reason A-Z</option>
                </select>
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[800px]">
                <thead>
                  <tr className="border-b bg-muted/50">
                    <th className="p-4">
                      <Checkbox
                        checked={selectAll || (filteredAndSortedConflicts.length > 0 && selectedIds.size === filteredAndSortedConflicts.length)}
                        onCheckedChange={toggleSelectAll}
                        aria-label="Select all"
                      />
                    </th>
                    <th className="text-left p-4 font-medium cursor-pointer flex items-center gap-1" onClick={() => toggleSort('reason')}>
                      Reason <ArrowUpDown className="h-3 w-3" />
                    </th>
                    <th className="text-left p-4 font-medium cursor-pointer flex items-center gap-1" onClick={() => toggleSort('customer')}>
                      Customer <ArrowUpDown className="h-3 w-3" />
                    </th>
                    <th className="text-left p-4 font-medium">Project</th>
                    <th className="text-left p-4 font-medium">Ticket</th>
                    <th className="text-left p-4 font-medium cursor-pointer flex items-center gap-1" onClick={() => toggleSort('date')}>
                      Start <ArrowUpDown className="h-3 w-3" />
                    </th>
                    <th className="text-left p-4 font-medium">End</th>
                    <th className="text-left p-4 font-medium">Duration</th>
                    <th className="text-left p-4 font-medium">Activity</th>
                    <th className="text-left p-4 font-medium">Status</th>
                    <th className="text-left p-4 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredAndSortedConflicts.map((conflict) => (
                    <tr key={conflict.id} className="border-b hover:bg-muted/50">
                      <td className="p-4">
                        <Checkbox
                          checked={selectedIds.has(conflict.id)}
                          onCheckedChange={(checked) => toggleSelection(conflict.id, !!checked)}
                          aria-label={`Select ${conflict.ticket_number || 'conflict'}`}
                        />
                      </td>
                      <td className="p-4">{getReasonBadge(conflict.reason_code || conflict.conflict_type)}</td>
                      <td className="p-4">{conflict.customer_name || 'N/A'}</td>
                      <td className="p-4">{conflict.project_name || 'N/A'}</td>
                      <td className="p-4">{conflict.ticket_number || 'N/A'}</td>
                      <td className="p-4">{getStart(conflict)}</td>
                      <td className="p-4">{getEnd(conflict)}</td>
                      <td className="p-4">{getDuration(conflict)}</td>
                      <td className="p-4">{conflict.activity_name || 'N/A'}</td>
                      <td className="p-4">{getStatusBadge(conflict.resolution_status)}</td>
                      <td className="p-4">
                        <div className="flex space-x-2">
                          {conflict.resolution_status === 'pending' && (
                            <>
                              <Button 
                                size="sm" 
                                variant="default"
                                onClick={() => handleResolve(conflict.id, 'resolved')}
                                className="px-3"
                              >
                                Resolve
                              </Button>
                              <Button 
                                size="sm" 
                                variant="outline"
                                onClick={() => handleResolve(conflict.id, 'ignored')}
                                className="px-3"
                              >
                                Ignore
                              </Button>
                            </>
                          )}
                          <Button 
                            size="sm" 
                            variant="ghost"
                            onClick={() => openDrawer(conflict)}
                            title="View details"
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {filteredAndSortedConflicts.length === 0 && conflicts.length > 0 && (
              <p className="text-center text-muted-foreground mt-4">No conflicts match your filters. Try adjusting them.</p>
            )}
          </CardContent>
        </Card>
      )}
      <ConflictDrawer 
        open={!!selectedConflict} 
        onClose={() => setSelectedConflict(null)} 
        conflict={selectedConflict} 
        onAction={handleAction}
        onDelete={handleDelete}
      />
    </div>
  )
}
