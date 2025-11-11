import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { CalendarClock, Check, Clock } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useToast } from "@/hooks/use-toast";
import { scheduleService } from "@/services/api.service";
import type { Schedule, ScheduleUpdate } from "@/types";

// Cron presets
const PRESETS = {
  hourly: { label: "Every hour", cron: "0 * * * *" },
  every6h: { label: "Every 6 hours", cron: "0 */6 * * *" },
  daily: { label: "Daily", cron: "0 9 * * *" },
  weekly: { label: "Weekly", cron: "0 9 * * 1" },
  monthly: { label: "Monthly", cron: "0 9 1 * *" }
};

// Common timezones
const TIMEZONES = [
  "UTC",
  "Europe/Brussels",
  "Europe/London",
  "Europe/Paris",
  "America/New_York",
  "America/Los_Angeles",
  "America/Chicago",
  "Asia/Tokyo",
  "Australia/Sydney"
];

// Days of week for weekly preset
const WEEKDAYS = [
  { value: 1, label: "Mon" },
  { value: 2, label: "Tue" },
  { value: 3, label: "Wed" },
  { value: 4, label: "Thu" },
  { value: 5, label: "Fri" },
  { value: 6, label: "Sat" },
  { value: 0, label: "Sun" }
];

export function ScheduleDialog() {
  const [open, setOpen] = useState(false);
  const [cron, setCron] = useState("");
  const [timezone, setTimezone] = useState("UTC");
  const [concurrency, setConcurrency] = useState<'skip' | 'queue'>('skip');
  const [notifications, setNotifications] = useState(false);
  const [enabled, setEnabled] = useState(false);
  const [selectedPreset, setSelectedPreset] = useState<string>("");
  const [customTime, setCustomTime] = useState("09:00");
  const [selectedDays, setSelectedDays] = useState<number[]>([1, 2, 3, 4, 5]); // Mon-Fri
  const [errors, setErrors] = useState<Record<string, string>>({});
  
  const { toast } = useToast();
  const queryClient = useQueryClient();

  // Fetch current schedule
  const { data: schedule, isLoading } = useQuery<Schedule>({
    queryKey: ["schedule"],
    queryFn: scheduleService.get,
    enabled: open
  });

  // Load schedule data when dialog opens
  useEffect(() => {
    if (schedule && open) {
      setCron(schedule.cron);
      setTimezone(schedule.timezone);
      setConcurrency(schedule.concurrency);
      setNotifications(schedule.notifications);
      setEnabled(schedule.enabled);
      
      // Try to match preset
      const matchedPreset = Object.entries(PRESETS).find(([_, p]) => p.cron === schedule.cron);
      if (matchedPreset) {
        setSelectedPreset(matchedPreset[0]);
      } else {
        setSelectedPreset("custom");
      }
    }
  }, [schedule, open]);

  // Update cron when preset or custom settings change
  useEffect(() => {
    if (!selectedPreset || selectedPreset === "custom") return;
    
    let newCron = PRESETS[selectedPreset as keyof typeof PRESETS]?.cron || "";
    
    // Adjust based on preset type
    if (selectedPreset === "daily" || selectedPreset === "weekly" || selectedPreset === "monthly") {
      const [hours, minutes] = customTime.split(':');
      
      if (selectedPreset === "daily") {
        newCron = `${minutes} ${hours} * * *`;
      } else if (selectedPreset === "weekly") {
        if (selectedDays.length === 0) {
          setErrors(prev => ({ ...prev, days: "Select at least one day for weekly schedule" }));
          return;
        }
        const days = selectedDays.sort().join(',');
        newCron = `${minutes} ${hours} * * ${days}`;
        setErrors(prev => {
          const { days, ...rest } = prev;
          return rest;
        });
      } else if (selectedPreset === "monthly") {
        newCron = `${minutes} ${hours} 1 * *`;
      }
    }
    
    setCron(newCron);
  }, [selectedPreset, customTime, selectedDays]);

  // Validate cron expression
  const validateCron = (cronExpr: string): string => {
    if (!cronExpr.trim()) return "Cron expression is required";
    const parts = cronExpr.trim().split(/\s+/);
    if (parts.length !== 5) return "Cron must have 5 parts (minute hour day month weekday)";
    return "";
  };

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: (update: ScheduleUpdate) => scheduleService.update(update),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["schedule"] });
      queryClient.invalidateQueries({ queryKey: ["syncRuns"] });
      queryClient.invalidateQueries({ queryKey: ["auditLogs"] });
      toast({ 
        title: "Success", 
        description: enabled ? "Schedule updated and enabled" : "Schedule saved (disabled)" 
      });
      setOpen(false);
    },
    onError: (error: any) => {
      const errorMsg = error.response?.data?.detail || error.message || 'Failed to update schedule';
      toast({ title: "Error", description: errorMsg, variant: "destructive" });
    }
  });

  const handleSave = () => {
    const cronError = validateCron(cron);
    if (cronError) {
      setErrors({ cron: cronError });
      toast({ title: "Validation Error", description: cronError, variant: "destructive" });
      return;
    }

    // Additional validations for presets
    if (selectedPreset === "weekly" && selectedDays.length === 0) {
      setErrors({ days: "Select at least one day for weekly schedule" });
      toast({ title: "Validation Error", description: "Select at least one weekday", variant: "destructive" });
      return;
    }

    if ((selectedPreset === "daily" || selectedPreset === "weekly" || selectedPreset === "monthly") && !customTime) {
      setErrors({ time: "Time is required for this schedule type" });
      toast({ title: "Validation Error", description: "Please select a time", variant: "destructive" });
      return;
    }

    setErrors({});

    updateMutation.mutate({
      cron,
      timezone,
      concurrency,
      notifications,
      enabled
    });
  };

  const handleDayToggle = (day: number) => {
    setSelectedDays(prev => 
      prev.includes(day) 
        ? prev.filter(d => d !== day)
        : [...prev, day].sort()
    );
  };

  const nextRuns = schedule?.next_runs || [];

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="gap-2">
          <CalendarClock className="h-4 w-4" /> Schedule
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Configure Sync Schedule</DialogTitle>
          <DialogDescription>
            Set up automatic periodic syncs. Changes take effect immediately without restarting the service.
          </DialogDescription>
        </DialogHeader>

        {isLoading ? (
          <div className="py-8 text-center text-muted-foreground">Loading schedule...</div>
        ) : (
          <div className="space-y-6 py-4">
            {/* Enable/Disable */}
            <div className="flex items-center justify-between">
              <div>
                <Label className="text-base font-medium">Enable Schedule</Label>
                <p className="text-sm text-muted-foreground">Activate automatic periodic syncs</p>
              </div>
              <Switch checked={enabled} onCheckedChange={setEnabled} />
            </div>

            {/* Preset Selection */}
            <div className="space-y-2">
              <Label>Preset</Label>
              <div className="grid grid-cols-3 gap-2">
                {Object.entries(PRESETS).map(([key, { label }]) => (
                  <Button
                    key={key}
                    type="button"
                    variant={selectedPreset === key ? "default" : "outline"}
                    size="sm"
                    onClick={() => setSelectedPreset(key)}
                  >
                    {label}
                  </Button>
                ))}
                <Button
                  type="button"
                  variant={selectedPreset === "custom" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setSelectedPreset("custom")}
                >
                  Custom
                </Button>
              </div>
            </div>

            {/* Time picker for daily/weekly/monthly */}
            {(selectedPreset === "daily" || selectedPreset === "weekly" || selectedPreset === "monthly") && (
              <div className="space-y-2">
                <Label>Time</Label>
                <div className="flex items-center gap-2">
                  <Clock className="h-4 w-4 text-muted-foreground" />
                  <Input
                    type="time"
                    value={customTime}
                    onChange={(e) => setCustomTime(e.target.value)}
                    className={errors.time ? 'border-destructive' : ''}
                  />
                </div>
                {errors.time && <p className="text-sm text-destructive">{errors.time}</p>}
              </div>
            )}

            {/* Day chips for weekly */}
            {selectedPreset === "weekly" && (
              <div className="space-y-2">
                <Label>Days of Week</Label>
                <div className="flex flex-wrap gap-2">
                  {WEEKDAYS.map(({ value, label }) => (
                    <Badge
                      key={value}
                      variant={selectedDays.includes(value) ? "default" : "outline"}
                      className="cursor-pointer"
                      onClick={() => handleDayToggle(value)}
                    >
                      {label}
                    </Badge>
                  ))}
                </div>
                {errors.days && <p className="text-sm text-destructive">{errors.days}</p>}
              </div>
            )}

            {/* Custom cron */}
            <div className="space-y-2">
              <Label>Cron Expression</Label>
              <Input
                value={cron}
                onChange={(e) => setCron(e.target.value)}
                placeholder="0 */6 * * *"
                className={errors.cron ? 'border-destructive' : ''}
                disabled={selectedPreset !== "custom"}
              />
              {errors.cron && <p className="text-sm text-destructive">{errors.cron}</p>}
              <p className="text-xs text-muted-foreground">
                Format: minute hour day month weekday (e.g., "0 9 * * 1-5" = 9am Mon-Fri)
              </p>
            </div>

            {/* Timezone */}
            <div className="space-y-2">
              <Label>Timezone</Label>
              <Select value={timezone} onValueChange={setTimezone}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {TIMEZONES.map(tz => (
                    <SelectItem key={tz} value={tz}>
                      {tz}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Concurrency */}
            <div className="space-y-2">
              <Label>Concurrency Policy</Label>
              <Select value={concurrency} onValueChange={(v) => setConcurrency(v as 'skip' | 'queue')}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="skip">Skip if running (recommended)</SelectItem>
                  <SelectItem value="queue">Queue next run</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                {concurrency === 'skip' 
                  ? "Skip scheduled run if previous sync is still active"
                  : "Queue next run if sync is active (max 5 queued)"}
              </p>
            </div>

            {/* Notifications */}
            <div className="flex items-center justify-between">
              <div>
                <Label>Notifications</Label>
                <p className="text-sm text-muted-foreground">
                  Alert on failures or high conflicts (&gt;10)
                </p>
              </div>
              <Switch checked={notifications} onCheckedChange={setNotifications} />
            </div>

            {/* Preview next runs */}
            {enabled && nextRuns.length > 0 && (
              <Alert>
                <Check className="h-4 w-4" />
                <AlertDescription>
                  <div className="font-medium mb-2">Next 3 scheduled runs:</div>
                  <ul className="text-sm space-y-1">
                    {nextRuns.map((run, idx) => (
                      <li key={idx}>
                        {new Date(run).toLocaleString(undefined, { 
                          timeZone: timezone,
                          dateStyle: 'medium',
                          timeStyle: 'short'
                        })}
                      </li>
                    ))}
                  </ul>
                </AlertDescription>
              </Alert>
            )}

            {!enabled && (
              <Alert>
                <AlertDescription>
                  Schedule is disabled. Enable it to activate automatic syncs.
                </AlertDescription>
              </Alert>
            )}
          </div>
        )}

        <DialogFooter>
          <Button variant="ghost" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button 
            onClick={handleSave}
            disabled={isLoading || updateMutation.isPending}
          >
            {updateMutation.isPending ? 'Saving...' : 'Save Schedule'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
