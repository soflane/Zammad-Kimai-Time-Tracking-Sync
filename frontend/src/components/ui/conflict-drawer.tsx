import { useEffect, useState, ChangeEvent } from 'react'
import { X } from 'lucide-react'
import { Button } from './button'
import { Loader2 } from 'lucide-react'
import type { Conflict } from '@/types'
import { Card, CardContent, CardHeader, CardTitle } from './card'
import { format, isValid } from 'date-fns'

interface ConflictDrawerProps {
  open: boolean
  onClose: () => void
  conflict: Conflict | null
  onAction?: (id: number, action: 'create' | 'update' | 'skip', notes?: string) => Promise<void>
  onDelete?: (id: number) => Promise<void>
}

export function ConflictDrawer({ open, onClose, conflict, onAction, onDelete }: ConflictDrawerProps) {
  const [notes, setNotes] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (open) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = 'unset'
    }
    return () => {
      document.body.style.overflow = 'unset'
    }
  }, [open])

  useEffect(() => {
    if (open && conflict) {
      setNotes('')
    }
  }, [open, conflict])

  if (!open || !conflict) return null

  const handleAction = async (action: 'create' | 'update' | 'skip') => {
    if (!onAction || loading) return
    setLoading(true)
    try {
      await onAction(conflict.id, action, notes || undefined)
      setNotes('')
    } catch (error) {
      // Error handled in parent
    }
    setLoading(false)
  }

  const handleDelete = async () => {
    if (!onDelete || loading || !window.confirm('Delete this conflict?')) return
    setLoading(true)
    try {
      await onDelete(conflict.id)
    } catch (error) {
      // Error handled in parent
    }
    setLoading(false)
  }

  const hasKimaiEntry = !!conflict.kimai_id

  const isMismatch = conflict.reason_code === 'TIME_MISMATCH'
  const isUnmapped = conflict.reason_code === 'UNMAPPED_ACTIVITY'

  const formatField = (value: any) => value || 'N/A'

  return (
    <div className={`fixed inset-0 z-50 transition-opacity ${open ? 'opacity-100' : 'opacity-0'}`}>
      <div className={`absolute inset-0 bg-black/50 transition-opacity ${open ? 'opacity-100' : 'opacity-0'}`} onClick={onClose} />
      <div className={`absolute right-0 top-0 h-full w-full max-w-2xl bg-background shadow-2xl transform transition-transform duration-300 ease-in-out ${open ? 'translate-x-0' : 'translate-x-full'}`}>
        <div className="flex h-full flex-col">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-border p-6">
            <div className="flex items-center space-x-3">
              <span className={`px-3 py-1 rounded-full text-xs font-semibold ${getReasonBadgeColor(conflict.reason_code || 'OTHER')}`}>
                {conflict.reason_code || 'OTHER'}
              </span>
              <h2 className="text-xl font-semibold text-foreground">Conflict Details</h2>
            </div>
            <Button variant="ghost" size="sm" onClick={onClose}>
              <X className="h-4 w-4" />
            </Button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-6 space-y-8">
            <div className="text-sm text-muted-foreground leading-relaxed">
              {conflict.reason_detail || 'No additional details available.'}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              {/* Zammad Side */}
              <Card className="p-4">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Zammad Entry</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex justify-between">
                    <span className="text-sm font-medium text-muted-foreground">Ticket Number</span>
                    <span className="text-sm font-medium">{formatField(conflict.ticket_number)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm font-medium text-muted-foreground">Entry Date</span>
                    <span className="text-sm">{formatDate(conflict.zammad_entry_date)}</span>
                  </div>
                  <div className={`flex justify-between p-3 rounded-lg border ${isMismatch ? 'bg-yellow-50 border-yellow-200' : 'border-border bg-muted/20'}`}>
                    <span className="text-sm font-medium">Duration (min)</span>
                    <span className={`text-sm font-semibold ${isMismatch ? 'text-destructive' : ''}`}>
                      {conflict.zammad_time_minutes ? `${conflict.zammad_time_minutes.toFixed(1)}` : '(no time)'}
                    </span>
                  </div>
                  <div className={`flex justify-between p-3 rounded-lg border ${isUnmapped ? 'bg-yellow-50 border-yellow-200' : 'border-border bg-muted/20'}`}>
                    <span className="text-sm font-medium">Activity</span>
                    <span className={`text-sm font-semibold ${isUnmapped ? 'text-warning' : ''}`}>
                      {formatField(conflict.activity_name)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm font-medium text-muted-foreground">Customer</span>
                    <span className="text-sm">{formatField(conflict.customer_name)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm font-medium text-muted-foreground">Project</span>
                    <span className="text-sm">{formatField(conflict.project_name)}</span>
                  </div>
                </CardContent>
              </Card>

              {/* Kimai Side */}
              <Card className="p-4">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    Kimai Entry {conflict.kimai_id ? `(ID: ${conflict.kimai_id})` : '(pending)'}
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex justify-between">
                    <span className="text-sm font-medium text-muted-foreground">Begin</span>
                    <span className="text-sm">{formatDate(conflict.kimai_begin)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm font-medium text-muted-foreground">End</span>
                    <span className="text-sm">{formatDate(conflict.kimai_end)}</span>
                  </div>
                  <div className={`flex justify-between p-3 rounded-lg border ${isMismatch ? 'bg-yellow-50 border-yellow-200' : 'border-border bg-muted/20'}`}>
                    <span className="text-sm font-medium">Duration (min)</span>
                    <span className={`text-sm font-semibold ${isMismatch ? 'text-destructive' : ''}`}>
                      {conflict.kimai_duration_minutes ? `${conflict.kimai_duration_minutes.toFixed(1)}` : 'N/A'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm font-medium text-muted-foreground">Activity</span>
                    <span className="text-sm">{formatField(conflict.activity_name)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm font-medium text-muted-foreground">Customer</span>
                    <span className="text-sm">{formatField(conflict.customer_name)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm font-medium text-muted-foreground">Project</span>
                    <span className="text-sm">{formatField(conflict.project_name)}</span>
                  </div>
                </CardContent>
              </Card>
            </div>

            {conflict.notes && (
              <Card className="p-4">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium">Previous Notes</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground whitespace-pre-wrap">{conflict.notes}</p>
                </CardContent>
              </Card>
            )}

            {/* Footer with notes and actions */}
            <div className="border-t bg-background">
              <div className="p-6 space-y-4">
                <div>
                  <label className="text-sm font-medium block mb-2" htmlFor="resolution-notes">
                    Resolution Notes (optional, max 500 chars)
                  </label>
                  <div className="relative">
                    <textarea
                      id="resolution-notes"
                      value={notes}
                      onChange={(e: ChangeEvent<HTMLTextAreaElement>) => setNotes(e.target.value)}
                      placeholder="Add notes for this resolution..."
                      rows={3}
                      maxLength={500}
                      disabled={loading}
                      className="w-full p-3 border border-border rounded-md focus:ring-2 focus:ring-primary focus:border-primary resize-vertical min-h-[100px] pr-12"
                    />
                    <div className="absolute bottom-2 right-3 text-xs text-muted-foreground">
                      {notes.length}/500
                    </div>
                  </div>
                </div>
                <div className="flex flex-col sm:flex-row gap-3 justify-end">
                  {onDelete && (
                    <Button 
                      onClick={handleDelete} 
                      variant="destructive" 
                      disabled={loading}
                    >
                      {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                      Delete Conflict
                    </Button>
                  )}
                  {onAction && !loading && (
                    <>
                      {!hasKimaiEntry && (
                        <Button 
                          onClick={() => handleAction('create')} 
                          variant="default" 
                          disabled={loading}
                        >
                          {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                          Create in Kimai
                        </Button>
                      )}
                      {hasKimaiEntry && (
                        <Button 
                          onClick={() => handleAction('update')} 
                          variant="default" 
                          disabled={loading}
                        >
                          {loading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                          Update in Kimai
                        </Button>
                      )}
                      <Button 
                        onClick={() => handleAction('skip')} 
                        variant="outline" 
                        disabled={loading}
                      >
                        Skip
                      </Button>
                    </>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function getReasonBadgeColor(code: string): string {
  const colors: Record<string, string> = {
    'TIME_MISMATCH': 'bg-destructive text-destructive-foreground',
    'UNMAPPED_ACTIVITY': 'bg-warning text-warning-foreground',
    'DUPLICATE': 'bg-yellow-100 text-yellow-800',
    'PROJECT_OR_CUSTOMER_MISSING': 'bg-muted text-muted-foreground',
    'LOCKED_OR_EXPORTED': 'bg-secondary text-secondary-foreground',
    'CREATION_ERROR': 'bg-destructive text-destructive-foreground',
    'OTHER': 'bg-primary/10 text-primary',
    default: 'bg-yellow-100 text-yellow-800'
  }
  return colors[code as keyof typeof colors] || colors.default
}

function formatDate(dateStr: string | undefined, fallback: string = 'N/A'): string {
  if (!dateStr || !isValid(new Date(dateStr))) return fallback
  return format(new Date(dateStr), 'MMM dd, yyyy HH:mm')
}
