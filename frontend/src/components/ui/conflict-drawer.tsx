'use client'

import { useEffect } from 'react'
import { X } from 'lucide-react'
import { Button } from './button'
import type { Conflict } from '@/types'
import { format, isValid } from 'date-fns'

interface ConflictDrawerProps {
  open: boolean
  onClose: () => void
  conflict: Conflict | null
}

export function ConflictDrawer({ open, onClose, conflict }: ConflictDrawerProps) {
  if (!conflict) return null

  const isMismatch = conflict.reason_code === 'TIME_MISMATCH'
  const isUnmapped = conflict.reason_code === 'UNMAPPED_ACTIVITY'

  const formatField = (value: any) => value || 'N/A'

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

  return (
    <div className={`fixed inset-0 z-50 ${open ? 'block' : 'hidden'}`}>
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className={`absolute right-0 top-0 h-full w-full max-w-2xl bg-background shadow-2xl transition-transform ${open ? 'translate-x-0' : 'translate-x-full'}`}>
        <div className="flex h-full flex-col">
          {/* Header */}
          <div className="flex items-center justify-between border-b p-4">
  <div className="flex items-center space-x-2">
    <span className={`px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800`}>
      {conflict.reason_code}
    </span>
    <h2 className="text-lg font-semibold">Conflict Details</h2>
  </div>
            <Button variant="ghost" size="sm" onClick={onClose}>
              <X className="h-4 w-4" />
            </Button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-4 space-y-6">
            <div className="text-sm text-muted-foreground pb-2">
              {conflict.reason_detail}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Zammad Side */}
              <div>
                <h3 className="text-sm font-medium text-muted-foreground mb-3 border-b pb-1">Zammad Entry</h3>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-sm font-medium">Ticket Number</span>
                    <span className="text-sm">{formatField(conflict.ticket_number)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm font-medium">Entry Date</span>
                    <span className="text-sm">{formatDate(conflict.zammad_entry_date)}</span>
                  </div>
                  <div className={`flex justify-between ${isMismatch ? 'bg-yellow-50 p-2 rounded' : ''}`}>
                    <span className="text-sm font-medium">Duration (min)</span>
                    <span className={`text-sm ${isMismatch ? 'font-semibold text-destructive' : ''}`}>
                      {conflict.zammad_time_minutes ? `${conflict.zammad_time_minutes.toFixed(1)}` : '(no time)'}
                    </span>
                  </div>
                  <div className={`flex justify-between ${isUnmapped ? 'bg-yellow-50 p-2 rounded' : ''}`}>
                    <span className="text-sm font-medium">Activity</span>
                    <span className={`text-sm ${isUnmapped ? 'font-semibold text-warning' : ''}`}>
                      {formatField(conflict.activity_name)}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm font-medium">Customer</span>
                    <span className="text-sm">{formatField(conflict.customer_name)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm font-medium">Project</span>
                    <span className="text-sm">{formatField(conflict.project_name)}</span>
                  </div>
                </div>
              </div>

              {/* Kimai Side */}
              <div>
                <h3 className="text-sm font-medium text-muted-foreground mb-3 border-b pb-1">Kimai Entry {conflict.kimai_id ? `(ID: ${conflict.kimai_id})` : '(pending)'}</h3>
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-sm font-medium">Begin</span>
                    <span className="text-sm">{formatDate(conflict.kimai_begin)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm font-medium">End</span>
                    <span className="text-sm">{formatDate(conflict.kimai_end)}</span>
                  </div>
                  <div className={`flex justify-between ${isMismatch ? 'bg-yellow-50 p-2 rounded' : ''}`}>
                    <span className="text-sm font-medium">Duration (min)</span>
                    <span className={`text-sm ${isMismatch ? 'font-semibold text-destructive' : ''}`}>
                      {conflict.kimai_duration_minutes ? `${conflict.kimai_duration_minutes.toFixed(1)}` : 'N/A'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm font-medium">Activity</span>
                    <span className="text-sm">{formatField(conflict.activity_name)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm font-medium">Customer</span>
                    <span className="text-sm">{formatField(conflict.customer_name)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm font-medium">Project</span>
                    <span className="text-sm">{formatField(conflict.project_name)}</span>
                  </div>
                </div>
              </div>
            </div>

            {conflict.notes && (
              <div className="pt-4 border-t">
                <h3 className="text-sm font-medium mb-2">Notes</h3>
                <p className="text-sm text-muted-foreground">{conflict.notes}</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function formatDate(dateStr: string | undefined, fallback: string = 'N/A'): string {
  if (!dateStr || !isValid(new Date(dateStr))) return fallback
  return format(new Date(dateStr), 'MMM dd, yyyy HH:mm')
}
