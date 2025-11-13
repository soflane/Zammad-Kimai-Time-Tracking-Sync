import React, { useMemo, useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  BadgeCheck,
  Check,
  Database,
  FileClock,
  History,
  Link2,
  Play,
  Plus,
  RefreshCw,
  Settings,
  Tags,
  TimerReset,
  Trash,
  UploadCloud,
  Waypoints
} from "lucide-react";

import ZammadIcon from '@/assets/icons/zammad-logo-only.svg?react'
import KimaiIcon from '@/assets/icons/kimai-logo-only.svg?react'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip as RechartsTooltip, XAxis } from "recharts";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { DialogClose } from "@/components/ui/dialog";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { useToast } from "@/hooks/use-toast";

import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious
} from "@/components/ui/pagination"

import { connectorService, mappingService, syncService, auditService, reconcileService } from "@/services/api.service";
import type { ValidationResponse, Connector, ActivityMapping, Activity as ActivityType, SyncRun, SyncResponse, AuditLog, ReconcileResponse, RowOp, PaginatedSyncRuns, PaginatedAuditLogs } from "@/types";
import { ScheduleDialog } from "@/components/ScheduleDialog";

// Utility UI components
const Pill = ({ ok }: { ok: boolean }) => (
  <Badge variant={ok ? "default" : "destructive"} className="rounded-full px-2 py-0 text-xs">
    {ok ? "All good" : "Attention"}
  </Badge>
);

function StatCard({ label, value, icon: Icon }: { label: string; value: React.ReactNode; icon: any }) {
  return (
    <Card className="shadow-xs">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{label}</CardTitle>
        <Icon className="h-4 w-4" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-semibold">{value}</div>
      </CardContent>
    </Card>
  );
}

function SectionHeader({
  title,
  description,
  actions
}: {
  title: string;
  description?: string;
  actions?: React.ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-3">
      <div>
        <h2 className="text-xl font-semibold tracking-tight">{title}</h2>
        {description && <p className="text-sm text-muted-foreground">{description}</p>}
      </div>
      <div className="flex items-center gap-2">{actions}</div>
    </div>
  );
}

function DeleteConnectorDialog({ item, onSuccess }: { item: Connector; onSuccess?: () => void }) {
  const [open, setOpen] = useState(false);
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const deleteMutation = useMutation({
    mutationFn: () => connectorService.delete(item.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["connectors"] });
      queryClient.invalidateQueries({ queryKey: ["kpi"] });
      toast({ title: "Success", description: `Connector "${item.name}" deleted successfully` });
      setOpen(false);
      onSuccess?.();
    },
    onError: (error: any) => {
      const errorMsg = error.response?.data?.detail || error.message || 'Failed to delete connector';
      toast({ title: "Error", description: errorMsg, variant: "destructive" });
    }
  });

  const handleDelete = () => {
    deleteMutation.mutate();
  };

  const handleOpenChange = (newOpen: boolean) => {
    setOpen(newOpen);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button variant="destructive" size="sm" disabled={deleteMutation.isPending} title="Delete connector">
          <Trash className="h-4 w-4" />
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete Connector?</DialogTitle>
          <DialogDescription>
            This will permanently remove the "{item.name}" connector and stop any associated syncs. This action cannot be undone.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <DialogClose asChild>
            <Button variant="outline">Cancel</Button>
          </DialogClose>
          <Button 
            variant="destructive" 
            onClick={handleDelete}
            disabled={deleteMutation.isPending}
          >
            {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// Delete Mapping Dialog
function DeleteMappingDialog({ item, onSuccess }: { item: ActivityMapping; onSuccess?: () => void }) {
  const [open, setOpen] = useState(false);
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const deleteMutation = useMutation({
    mutationFn: () => mappingService.delete(item.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["mappings"] });
      queryClient.invalidateQueries({ queryKey: ["kpi"] });
      toast({ title: "Success", description: `Mapping "${item.zammad_type_name} → ${item.kimai_activity_name}" deleted successfully` });
      setOpen(false);
      onSuccess?.();
    },
    onError: (error: any) => {
      const errorMsg = error.response?.data?.detail || error.message || 'Failed to delete mapping';
      toast({ title: "Error", description: errorMsg, variant: "destructive" });
    }
  });

  const handleDelete = () => {
    deleteMutation.mutate();
  };

  const handleOpenChange = (newOpen: boolean) => {
    setOpen(newOpen);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button variant="destructive" size="sm" disabled={deleteMutation.isPending} title="Delete mapping">
          <Trash className="h-4 w-4" />
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete Mapping?</DialogTitle>
          <DialogDescription>
            This will permanently remove the mapping between "{item.zammad_type_name}" and "{item.kimai_activity_name}". This action cannot be undone.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <DialogClose asChild>
            <Button variant="outline">Cancel</Button>
          </DialogClose>
          <Button 
            variant="destructive" 
            onClick={handleDelete}
            disabled={deleteMutation.isPending}
          >
            {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// Connector Dialog
function ConnectorDialog({ item, onSuccess }: { item?: Connector; onSuccess?: () => void }) {
  const [open, setOpen] = useState(false);
  const [enabled, setEnabled] = useState(item?.is_active ?? true);
  const [baseUrl, setBaseUrl] = useState(item?.base_url ?? "");
  const [apiToken, setApiToken] = useState("");
  const [name, setName] = useState(item?.name ?? "");
  const [type, setType] = useState<'zammad' | 'kimai'>(item?.type ?? "zammad");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitAttempted, setSubmitAttempted] = useState(false);
  const [isVerified, setIsVerified] = useState(false);
  const [testError, setTestError] = useState<string | null>(null);
  
  // Kimai-specific settings
  const itemSettings = item?.type === 'kimai' && item?.settings ? item.settings as any : {};
  const [roundingMode, setRoundingMode] = useState<string>(itemSettings.rounding_mode || 'default');
  const [roundBegin, setRoundBegin] = useState<number>(itemSettings.round_begin || 0);
  const [roundEnd] = useState<number>(itemSettings.round_end || 0);
  const [roundDuration, setRoundDuration] = useState<number>(itemSettings.round_duration || 0);
  const [roundingDays] = useState<number[]>(itemSettings.rounding_days || [0, 1, 2, 3, 4, 5, 6]);
  
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const validateField = (field: string): string => {
    switch (field) {
      case 'name':
        return !name.trim() ? "Name is required" : "";
      case 'type':
        return !type ? "Connector type is required" : "";
      case 'baseUrl':
        if (!baseUrl.trim()) return "Base URL is required";
        try {
          new URL(baseUrl);
          return "";
        } catch {
          return "Please enter a valid URL (e.g., https://example.com)";
        }
      case 'apiToken':
        if (item && !apiToken.trim()) return ""; // Allow empty for updates (no change)
        return !apiToken.trim() ? "API Token is required" : "";
      default:
        return "";
    }
  };

  const updateFieldError = (field: string) => {
    const error = validateField(field);
    if (error) {
      setErrors(prev => ({ ...prev, [field]: error }));
    } else {
      setErrors(prev => {
        const { [field]: _, ...rest } = prev;
        return rest;
      });
    }
  };

  const resetVerification = () => {
    setIsVerified(false);
    setTestError(null);
  };

  const testMutation = useMutation({
    mutationFn: () => {
      const request = item 
        ? { id: item.id, base_url: baseUrl, api_token: apiToken || undefined }
        : { type, base_url: baseUrl, api_token: apiToken };
      return connectorService.testConnection(request);
    },
    onSuccess: (data: ValidationResponse) => {
      setTestError(null);
      if (data.valid) {
        setIsVerified(true);
        toast({ title: "Success", description: data.message });
      } else {
        setIsVerified(false);
        setTestError(data.message);
        toast({ title: "Test Failed", description: data.message, variant: "destructive" });
      }
    },
    onError: (error: any) => {
      setIsVerified(false);
      const errorMsg = error.response?.data?.message || error.message || 'Test failed';
      setTestError(errorMsg);
      toast({ title: "Test Error", description: errorMsg, variant: "destructive" });
    }
  });

  const validateForm = (): Record<string, string> => {
    const newErrors: Record<string, string> = {};

    if (!item) {
      const typeError = validateField('type');
      if (typeError) newErrors.type = typeError;
    }
    const nameError = validateField('name');
    if (nameError) newErrors.name = nameError;
    const baseUrlError = validateField('baseUrl');
    if (baseUrlError) newErrors.baseUrl = baseUrlError;
    const apiTokenError = validateField('apiToken');
    if (apiTokenError) newErrors.apiToken = apiTokenError;

    return newErrors;
  };

  const createMutation = useMutation({
    mutationFn: (data: any) => connectorService.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["connectors"] });
      queryClient.invalidateQueries({ queryKey: ["kpi"] });
      toast({ title: "Success", description: "Connector created successfully" });
      setOpen(false);
      onSuccess?.();
    },
    onError: () => {
      toast({ title: "Error", description: "Failed to create connector", variant: "destructive" });
    }
  });

  const updateMutation = useMutation({
    mutationFn: (data: any) => connectorService.update(item!.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["connectors"] });
      queryClient.invalidateQueries({ queryKey: ["kpi"] });
      toast({ title: "Success", description: "Connector updated successfully" });
      setOpen(false);
      onSuccess?.();
    },
    onError: () => {
      toast({ title: "Error", description: "Failed to update connector", variant: "destructive" });
    }
  });

  const handleSave = () => {
    const formErrors = validateForm();
    setErrors(formErrors);
    setSubmitAttempted(true);
    if (Object.values(formErrors).some(e => e)) {
      toast({ 
        title: "Validation Error", 
        description: "Please fix the errors in the form before saving.", 
        variant: "destructive" 
      });
      return;
    }

    // Build settings for Kimai connectors
    const kimaiSettings = (type === 'kimai' || item?.type === 'kimai') ? {
      rounding_mode: roundingMode,
      round_begin: roundBegin,
      round_end: roundEnd,
      round_duration: roundDuration,
      rounding_days: roundingDays
    } : {};

    const createData = {
      type,
      name,
      base_url: baseUrl,
      api_token: apiToken,
      is_active: enabled,
      settings: kimaiSettings
    };

    const updateData = {
      name,
      base_url: baseUrl,
      api_token: apiToken || undefined,
      is_active: enabled,
      settings: kimaiSettings
    };

    if (item) {
      updateMutation.mutate(updateData);
    } else {
      createMutation.mutate(createData);
    }
  };

  const handleCancel = () => {
    setOpen(false);
  };

  const handleOpenChange = (newOpen: boolean) => {
    if (newOpen) {
      setErrors({});
      setSubmitAttempted(false);
      setIsVerified(false);
      setTestError(null);
    } else {
      // Reset form on close
      setEnabled(item?.is_active ?? true);
      setBaseUrl(item?.base_url ?? "");
      setApiToken("");
      setName(item?.name ?? "");
      setType(item?.type ?? "zammad");
      setSubmitAttempted(false);
      setIsVerified(false);
      setTestError(null);
    }
    setOpen(newOpen);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="gap-2">
          {item ? <Settings className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
          {item ? "Configure" : "Add Connector"}
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>Configure {item?.name ?? "Connector"}</DialogTitle>
          <DialogDescription>Enter credentials and endpoint details. Secrets are stored encrypted in the service DB.</DialogDescription>
        </DialogHeader>
        {item && (
          <div className="mb-4 p-3 bg-muted/50 rounded-md">
            <Label className="text-sm font-medium mb-2 block">Type</Label>
            <div className="flex items-center space-x-2">
              {item.type === 'zammad' ? (
                <ZammadIcon className="h-4 w-4 text-primary" />
              ) : (
                <KimaiIcon className="h-4 w-4 text-primary" />
              )}
              <span className="text-sm font-medium capitalize">{item.type}</span>
            </div>
          </div>
        )}
        {submitAttempted && Object.keys(errors).length > 0 && (
          <Alert variant="destructive" className="mb-4">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>Please fix the errors below before saving.</AlertDescription>
          </Alert>
        )}
        <div className="grid gap-4 py-2">
          {!item && (
            <>
              <div className="grid grid-cols-4 items-center gap-2">
                <Label className="text-right">Type</Label>
                <Select value={type} onValueChange={(v: 'zammad' | 'kimai') => { setType(v); updateFieldError('type'); }}>
                  <SelectTrigger className={`col-span-3 ${errors.type ? 'border-destructive' : ''}`}>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="zammad">Zammad</SelectItem>
                    <SelectItem value="kimai">Kimai</SelectItem>
                  </SelectContent>
                </Select>
                {errors.type && <p className="col-span-4 text-sm text-destructive mt-1">{errors.type}</p>}
              </div>
              <div className="grid grid-cols-4 items-center gap-2">
                <Label className="text-right">Name</Label>
                <Input 
                  className={`col-span-3 ${errors.name ? 'border-destructive' : ''}`} 
                  value={name} 
                  onChange={(e) => setName(e.target.value)}
                  onBlur={() => updateFieldError('name')}
                />
                {errors.name && <p className="col-span-4 text-sm text-destructive mt-1">{errors.name}</p>}
              </div>
            </>
          )}
          <div className="grid grid-cols-4 items-center gap-2">
            <Label className="text-right">Enabled</Label>
            <div className="col-span-3">
              <Switch checked={enabled} onCheckedChange={setEnabled} />
            </div>
          </div>
          <div className="grid grid-cols-4 items-center gap-2">
            <Label className="text-right">Base URL</Label>
            <Input 
              className={`col-span-3 ${errors.baseUrl ? 'border-destructive' : ''}`} 
              value={baseUrl} 
              onChange={(e) => { setBaseUrl(e.target.value); resetVerification(); }}
              onBlur={() => updateFieldError('baseUrl')}
            />
            {errors.baseUrl && <p className="col-span-4 text-sm text-destructive mt-1">{errors.baseUrl}</p>}
          </div>
          <div className="grid grid-cols-4 items-center gap-2">
            <Label className="text-right">API Token</Label>
            <Input 
              className={`col-span-3 ${errors.apiToken ? 'border-destructive' : ''}`} 
              type="password" 
              placeholder="••••••••••" 
              value={apiToken} 
              onChange={(e) => { setApiToken(e.target.value); resetVerification(); }}
              onBlur={() => updateFieldError('apiToken')}
            />
            {errors.apiToken && <p className="col-span-4 text-sm text-destructive mt-1">{errors.apiToken}</p>}
          </div>
          {(isVerified || testError) && (
            <div className="grid grid-cols-4 items-center gap-2">
              {isVerified && <p className="col-span-4 text-sm text-green-600 mt-1 flex items-center"><Check className="h-3 w-3 mr-1" /> Verified connection</p>}
              {testError && <p className="col-span-4 text-sm text-destructive mt-1">{testError}</p>}
            </div>
          )}
          
          {/* Kimai-specific rounding settings */}
          {(type === 'kimai' || item?.type === 'kimai') && (
            <>
              <div className="col-span-4 border-t pt-4 mt-2">
                <Label className="text-sm font-medium mb-2 block">Time Rounding (optional)</Label>
                <p className="text-xs text-muted-foreground mb-3">Configure rounding to match your Kimai user settings for accurate reconciliation</p>
              </div>
              
              <div className="grid grid-cols-4 items-center gap-2">
                <Label className="text-right text-sm">Rounding Mode</Label>
                <Select value={roundingMode} onValueChange={setRoundingMode}>
                  <SelectTrigger className="col-span-3">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="default">Default (begin↓ end/duration↑)</SelectItem>
                    <SelectItem value="closest">Closest (nearest value)</SelectItem>
                    <SelectItem value="floor">Floor (always down)</SelectItem>
                    <SelectItem value="ceil">Ceil (always up)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              <div className="grid grid-cols-4 items-center gap-2">
                <Label className="text-right text-sm">Round Begin (min)</Label>
                <Input 
                  type="number" 
                  min="0" 
                  step="1"
                  className="col-span-3" 
                  value={roundBegin} 
                  onChange={(e) => setRoundBegin(Number(e.target.value))}
                  placeholder="0 = disabled"
                />
              </div>
              
              <div className="grid grid-cols-4 items-center gap-2">
                <Label className="text-right text-sm">Round Duration (min)</Label>
                <Input 
                  type="number" 
                  min="0" 
                  step="1"
                  className="col-span-3" 
                  value={roundDuration} 
                  onChange={(e) => setRoundDuration(Number(e.target.value))}
                  placeholder="0 = disabled"
                />
              </div>
            </>
          )}
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={handleCancel}>
            Cancel
          </Button>
          <Button 
            variant="outline" 
            className="gap-2" 
            onClick={() => testMutation.mutate()}
            disabled={!!errors.baseUrl || !!errors.apiToken || !baseUrl.trim() || !apiToken.trim() || testMutation.isPending}
          >
            <RefreshCw className={`h-4 w-4 ${testMutation.isPending ? 'animate-spin' : ''}`} />
            {testMutation.isPending ? 'Testing...' : 'Test Connection'}
          </Button>
          <Button 
            className="gap-2" 
            onClick={handleSave}
            disabled={Object.values(errors).some(e => e) || createMutation.isPending || updateMutation.isPending}
          >
            <BadgeCheck className="h-4 w-4" /> Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// Mapping Dialog
function MappingDialog({ row, onSuccess }: { row?: ActivityMapping; onSuccess?: () => void }) {
  const [open, setOpen] = useState(false);
  const [zammadActivityId, setZammadActivityId] = useState<number | undefined>(row?.zammad_type_id);
  const [kimaiActivityId, setKimaiActivityId] = useState<number | undefined>(row?.kimai_activity_id);
  const { toast } = useToast();
  const queryClient = useQueryClient();

  // Fetch connectors
  const { data: connectors = [] } = useQuery<Connector[]>({
    queryKey: ["connectors"],
    queryFn: connectorService.getAll
  });

  const zammadConnector = useMemo(() => 
    connectors.find(c => c.type === 'zammad' && c.is_active),
    [connectors]
  );

  const kimaiConnector = useMemo(() => 
    connectors.find(c => c.type === 'kimai' && c.is_active),
    [connectors]
  );

  // Fetch activities from connectors
  const { data: zammadActivities = [], isLoading: loadingZammad } = useQuery<ActivityType[]>({
    queryKey: ["zammadActivities", zammadConnector?.id],
    queryFn: () => connectorService.getActivities(zammadConnector!.id),
    enabled: !!zammadConnector?.id
  });

  const { data: kimaiActivities = [], isLoading: loadingKimai } = useQuery<ActivityType[]>({
    queryKey: ["kimaiActivities", kimaiConnector?.id],
    queryFn: () => connectorService.getActivities(kimaiConnector!.id),
    enabled: !!kimaiConnector?.id
  });

  // Get selected activity names
  const selectedZammadActivity = useMemo(() => 
    zammadActivities.find(a => a.id === zammadActivityId),
    [zammadActivities, zammadActivityId]
  );

  const selectedKimaiActivity = useMemo(() => 
    kimaiActivities.find(a => a.id === kimaiActivityId),
    [kimaiActivities, kimaiActivityId]
  );

  const createMutation = useMutation({
    mutationFn: (data: any) => mappingService.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["mappings"] });
      queryClient.invalidateQueries({ queryKey: ["kpi"] });
      toast({ title: "Success", description: "Mapping created successfully" });
      setOpen(false);
      onSuccess?.();
    },
    onError: (error: any) => {
      const errorMsg = error.response?.data?.detail || error.message || 'Failed to create mapping';
      toast({ title: "Error", description: errorMsg, variant: "destructive" });
    }
  });

  const updateMutation = useMutation({
    mutationFn: (data: any) => mappingService.update(row!.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["mappings"] });
      queryClient.invalidateQueries({ queryKey: ["kpi"] });
      toast({ title: "Success", description: "Mapping updated successfully" });
      setOpen(false);
      onSuccess?.();
    },
    onError: (error: any) => {
      const errorMsg = error.response?.data?.detail || error.message || 'Failed to update mapping';
      toast({ title: "Error", description: errorMsg, variant: "destructive" });
    }
  });

  const handleSave = () => {
    if (!zammadActivityId || !kimaiActivityId) {
      toast({ 
        title: "Validation Error", 
        description: "Please select both Zammad and Kimai activities", 
        variant: "destructive" 
      });
      return;
    }

    const createData = {
      zammad_type_id: zammadActivityId,
      zammad_type_name: selectedZammadActivity?.name || '',
      kimai_activity_id: kimaiActivityId,
      kimai_activity_name: selectedKimaiActivity?.name || ''
    };

    const updateData = {
      zammad_type_id: zammadActivityId,
      zammad_type_name: selectedZammadActivity?.name || '',
      kimai_activity_id: kimaiActivityId,
      kimai_activity_name: selectedKimaiActivity?.name || ''
    };

    if (row) {
      updateMutation.mutate(updateData);
    } else {
      createMutation.mutate(createData);
    }
  };

  const handleOpenChange = (newOpen: boolean) => {
    if (newOpen) {
      // Reset to row values or undefined when opening
      setZammadActivityId(row?.zammad_type_id);
      setKimaiActivityId(row?.kimai_activity_id);
    }
    setOpen(newOpen);
  };

  const canSave = zammadActivityId && kimaiActivityId && !createMutation.isPending && !updateMutation.isPending;

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button size="sm" variant="outline" className="gap-2">
          <Waypoints className="h-4 w-4" /> {row ? "Edit" : "New mapping"}
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{row ? "Edit mapping" : "Create mapping"}</DialogTitle>
          <DialogDescription>Match activity types between Zammad and Kimai for accurate time tracking synchronization.</DialogDescription>
        </DialogHeader>

        {!zammadConnector && (
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>
              No active Zammad connector found. Please configure a Zammad connector first.
            </AlertDescription>
          </Alert>
        )}

        {!kimaiConnector && (
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>
              No active Kimai connector found. Please configure a Kimai connector first.
            </AlertDescription>
          </Alert>
        )}

        <div className="grid gap-4 py-2">
          <div className="grid grid-cols-4 items-center gap-2">
            <Label className="text-right">Zammad Activity</Label>
            <div className="col-span-3">
              <Select 
                value={zammadActivityId?.toString()} 
                onValueChange={(v) => setZammadActivityId(Number(v))}
                disabled={!zammadConnector || loadingZammad}
              >
                <SelectTrigger>
                  <SelectValue placeholder={loadingZammad ? "Loading activities..." : "Select Zammad activity"} />
                </SelectTrigger>
                <SelectContent>
                  {zammadActivities.map(activity => (
                    <SelectItem key={activity.id} value={activity.id.toString()}>
                      {activity.name}
                    </SelectItem>
                  ))}
                  {zammadActivities.length === 0 && !loadingZammad && (
                    <SelectItem value="none" disabled>No activities available</SelectItem>
                  )}
                </SelectContent>
              </Select>
              {zammadActivities.length === 0 && !loadingZammad && zammadConnector && (
                <p className="text-xs text-muted-foreground mt-1">
                  No activities found. Check your Zammad connector configuration.
                </p>
              )}
            </div>
          </div>

          <div className="grid grid-cols-4 items-center gap-2">
            <Label className="text-right">Kimai Activity</Label>
            <div className="col-span-3">
              <Select 
                value={kimaiActivityId?.toString()} 
                onValueChange={(v) => setKimaiActivityId(Number(v))}
                disabled={!kimaiConnector || loadingKimai}
              >
                <SelectTrigger>
                  <SelectValue placeholder={loadingKimai ? "Loading activities..." : "Select Kimai activity"} />
                </SelectTrigger>
                <SelectContent>
                  {kimaiActivities.map(activity => (
                    <SelectItem key={activity.id} value={activity.id.toString()}>
                      {activity.name}
                    </SelectItem>
                  ))}
                  {kimaiActivities.length === 0 && !loadingKimai && (
                    <SelectItem value="none" disabled>No activities available</SelectItem>
                  )}
                </SelectContent>
              </Select>
              {kimaiActivities.length === 0 && !loadingKimai && kimaiConnector && (
                <p className="text-xs text-muted-foreground mt-1">
                  No activities found. Check your Kimai connector configuration.
                </p>
              )}
            </div>
          </div>
        </div>

        <DialogFooter>
          <DialogClose asChild>
            <Button variant="ghost">Cancel</Button>
          </DialogClose>
          <Button 
            className="gap-2" 
            onClick={handleSave}
            disabled={!canSave}
          >
            <Check className="h-4 w-4" /> 
            {createMutation.isPending || updateMutation.isPending ? 'Saving...' : 'Save mapping'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function computeDuration(start: string, end: string): string {
  const s = new Date(start);
  const e = new Date(end);
  const diff = (e.getTime() - s.getTime()) / 1000 / 60;
  const minutes = Math.floor(diff);
  const seconds = Math.round((diff - minutes) * 60);
  return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
}

// Reconcile Section Component
function ReconcileSection() {
  const [activeFilter, setActiveFilter] = useState<'conflicts' | 'missing'>('conflicts');
  const [confirmDialog, setConfirmDialog] = useState<{ open: boolean; itemId: string; op: RowOp } | null>(null);
  const { toast } = useToast();
  const queryClient = useQueryClient();

  // Fetch reconcile data
  const { data: reconcileData, isLoading } = useQuery<ReconcileResponse>({
    queryKey: ["reconcile", activeFilter],
    queryFn: () => reconcileService.getDiff(activeFilter)
  });

  // Row action mutation with optimistic updates
  const actionMutation = useMutation({
    mutationFn: ({ id, op }: { id: string; op: RowOp }) => reconcileService.performAction(id, op),
    onMutate: async ({ id }) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: ["reconcile", activeFilter] });
      
      // Snapshot previous value
      const previousData = queryClient.getQueryData<ReconcileResponse>(["reconcile", activeFilter]);
      
      // Optimistically remove the item
      if (previousData) {
        queryClient.setQueryData<ReconcileResponse>(["reconcile", activeFilter], {
          ...previousData,
          items: previousData.items.filter(item => item.id !== id),
          total: previousData.total - 1
        });
      }
      
      return { previousData };
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["reconcile"] });
      queryClient.invalidateQueries({ queryKey: ["kpi"] });
      toast({ title: "Success", description: "Action completed successfully" });
    },
    onError: (error: any, _variables, context) => {
      // Rollback on error
      if (context?.previousData) {
        queryClient.setQueryData(["reconcile", activeFilter], context.previousData);
      }
      const errorMsg = error.response?.data?.detail || error.message || 'Action failed';
      toast({ title: "Error", description: errorMsg, variant: "destructive" });
    }
  });

  const handleAction = (itemId: string, op: RowOp) => {
    if (op === 'update') {
      // Show confirmation dialog for update
      setConfirmDialog({ open: true, itemId, op });
    } else {
      // Execute immediately for other actions
      actionMutation.mutate({ id: itemId, op });
    }
  };

  const handleConfirm = () => {
    if (confirmDialog) {
      actionMutation.mutate({ id: confirmDialog.itemId, op: confirmDialog.op });
      setConfirmDialog(null);
    }
  };

  const items = reconcileData?.items || [];
  const counts = reconcileData?.counts || { conflicts: 0, missing: 0 };

  return (
    <>
      <Tabs value={activeFilter} onValueChange={(v) => setActiveFilter(v as 'conflicts' | 'missing')} className="w-full">
        <TabsList>
          <TabsTrigger value="conflicts">Conflicts ({counts.conflicts})</TabsTrigger>
          <TabsTrigger value="missing">Missing ({counts.missing})</TabsTrigger>
        </TabsList>
        
        <TabsContent value={activeFilter} className="space-y-3">
          <Card>
            <CardHeader>
              <CardTitle>Diff Rows</CardTitle>
              <CardDescription>
                {activeFilter === 'conflicts' 
                  ? 'Entries that exist in both systems with different values' 
                  : 'Entries missing in Kimai that need to be synced'}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="text-center py-8 text-muted-foreground">Loading...</div>
              ) : items.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  No {activeFilter} found. Run a sync to detect differences.
                </div>
              ) : (
                <div className="space-y-4">
                  {items.map((item) => (
                    <div key={item.id} className="border rounded-lg p-4 space-y-3">
                      {/* Header */}
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="font-medium text-base">
                            {item.ticketId} · {item.ticketTitle}
                          </div>
                          <div className="text-sm text-muted-foreground">
                            Customer: {item.customer}
                          </div>
                          {item.conflictReason && (
                            <div className="mt-1 flex items-center gap-2">
                              <Badge variant="destructive" className="text-xs">
                                <AlertTriangle className="h-3 w-3 mr-1" />
                                {item.conflictReason}
                              </Badge>
                            </div>
                          )}
                        </div>
                        <div className="flex gap-2">
                          <Badge variant={item.status === 'conflict' ? 'destructive' : 'secondary'}>
                            {item.status}
                          </Badge>
                          <Badge variant="outline">Zammad → Kimai</Badge>
                        </div>
                      </div>

                      {/* Data comparison */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {item.source && (
                          <div className="space-y-1">
                            <div className="text-sm font-medium text-muted-foreground">Source (Zammad)</div>
                            <div className="bg-muted/50 rounded p-3 text-sm space-y-1.5">
                              <div className="flex items-center justify-between">
                                <span className="text-muted-foreground">Time:</span>
                                <span className="font-medium">{item.source.minutes} min</span>
                              </div>
                              <div className="flex items-center justify-between">
                                <span className="text-muted-foreground">Activity:</span>
                                <span className="font-medium">{item.source.activity}</span>
                              </div>
                              <div className="flex items-center justify-between">
                                <span className="text-muted-foreground">User:</span>
                                <span className="font-medium">{item.source.user}</span>
                              </div>
                              <div className="pt-1 border-t text-xs text-muted-foreground">
                                {new Date(item.source.startedAt).toLocaleString()}
                              </div>
                              {item.source.description && (
                                <div className="pt-1 border-t text-xs">
                                  <span className="text-muted-foreground">Note: </span>
                                  <span className="line-clamp-2">{item.source.description}</span>
                                </div>
                              )}
                            </div>
                          </div>
                        )}
                        
                        {item.target && (
                          <div className="space-y-1">
                            <div className="text-sm font-medium text-muted-foreground">Target (Kimai)</div>
                            <div className="bg-muted/50 rounded p-3 text-sm space-y-1.5">
                              <div className="flex items-center justify-between">
                                <span className="text-muted-foreground">Time:</span>
                                <span className="font-medium">{item.target.minutes} min</span>
                              </div>
                              <div className="flex items-center justify-between">
                                <span className="text-muted-foreground">Activity:</span>
                                <span className="font-medium">{item.target.activity}</span>
                              </div>
                              <div className="flex items-center justify-between">
                                <span className="text-muted-foreground">User:</span>
                                <span className="font-medium">{item.target.user}</span>
                              </div>
                              <div className="pt-1 border-t text-xs text-muted-foreground">
                                {new Date(item.target.startedAt).toLocaleString()}
                              </div>
                              {item.target.description && (
                                <div className="pt-1 border-t text-xs">
                                  <span className="text-muted-foreground">Note: </span>
                                  <span className="line-clamp-2">{item.target.description}</span>
                                </div>
                              )}
                            </div>
                          </div>
                        )}
                      </div>

                      {/* AutoPath chip */}
                      {item.autoPath && (item.autoPath.createCustomer || item.autoPath.createProject || item.autoPath.createTimesheet) && (
                        <Alert className="bg-blue-50 border-blue-200">
                          <Badge variant="secondary" className="mb-2">Will sync automatically</Badge>
                          <AlertDescription className="text-sm">
                            Will auto-create: 
                            {item.autoPath.createCustomer && ' customer (if needed)'} 
                            {item.autoPath.createProject && ` → project (${item.ticketId})`} 
                            {item.autoPath.createTimesheet && ' → timesheet with tag Zammad'}
                          </AlertDescription>
                        </Alert>
                      )}

                      {/* Actions */}
                      <div className="flex gap-2 pt-2">
                        {item.status === 'conflict' ? (
                          <>
                            <Button 
                              variant="outline" 
                              size="sm"
                              onClick={() => handleAction(item.id, 'keep-target')}
                              disabled={actionMutation.isPending}
                            >
                              Keep Target
                            </Button>
                            <Button 
                              variant="default" 
                              size="sm"
                              onClick={() => handleAction(item.id, 'update')}
                              disabled={actionMutation.isPending}
                            >
                              Update from Zammad
                            </Button>
                          </>
                        ) : (
                          <>
                            <Button 
                              variant="outline" 
                              size="sm"
                              onClick={() => handleAction(item.id, 'skip')}
                              disabled={actionMutation.isPending}
                            >
                              Skip
                            </Button>
                            <Button 
                              variant="default" 
                              size="sm"
                              onClick={() => handleAction(item.id, 'create')}
                              disabled={actionMutation.isPending}
                            >
                              Create in Kimai
                            </Button>
                          </>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Confirmation Dialog */}
      <Dialog open={confirmDialog?.open || false} onOpenChange={(open) => !open && setConfirmDialog(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Confirm Update</DialogTitle>
            <DialogDescription>
              This will update the Kimai timesheet with data from Zammad. This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline">Cancel</Button>
            </DialogClose>
            <Button onClick={handleConfirm} disabled={actionMutation.isPending}>
              {actionMutation.isPending ? 'Updating...' : 'Confirm Update'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

// AuditLogs Component
function AuditLogs({ runId }: { runId: number }) {
  const { data: logs = {data: [], total: 0} } = useQuery<PaginatedAuditLogs>({
    queryKey: ["auditLogs", runId],
    queryFn: () => auditService.getAuditLogs({ skip: 0, limit: 20 }),
  });

  return (
    <div className="space-y-2">
      <h4 className="font-medium">Logs for Run #{runId}</h4>
      {logs.data.length === 0 ? (
        <p className="text-sm text-muted-foreground">No logs available.</p>
      ) : (
        <ul className="text-sm space-y-1">
          {logs.data.map((log: AuditLog, index: number) => (
            <li key={index} className="text-xs text-muted-foreground">
              {log.action} - {log.created_at}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// Main Dashboard Component
export default function SyncDashboard() {
  const [query, setQuery] = useState("");
  const [testResults, setTestResults] = useState<Record<number, { valid: boolean; message: string; timestamp: string }>>({});
  const [pendingTests, setPendingTests] = useState<Set<number>>(new Set());
  const [testAllPending, setTestAllPending] = useState(false);
  const [statusFilter, setStatusFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [auditTab, setAuditTab] = useState<"sync-history" | "audit-logs">("sync-history");
  const [auditActionType, setAuditActionType] = useState<"all" | "access" | "sync">("all");
  const [auditSearch, setAuditSearch] = useState("");
  const [auditStartDate, setAuditStartDate] = useState("");
  const [auditEndDate, setAuditEndDate] = useState("");
  const [ipFilter, setIpFilter] = useState("");


  // Pagination for History
  const [historyPage, setHistoryPage] = useState(1)
  const [historyPageSize] = useState(5)

  // Pagination for Audit
  const [auditPage, setAuditPage] = useState(1)
  const [auditPageSize] = useState(5)

  useEffect(() => {
    setHistoryPage(1);
  }, [statusFilter, search, startDate, endDate]);

  useEffect(() => {
    setAuditPage(1);
  }, [auditActionType, auditSearch, auditStartDate, auditEndDate, ipFilter]);

  const { toast } = useToast();
  const queryClient = useQueryClient();

  // Data queries
  const { data: connectors = [] } = useQuery<Connector[]>({
    queryKey: ["connectors"],
    queryFn: connectorService.getAll
  });

  const { data: mappings = [] } = useQuery<ActivityMapping[]>({
    queryKey: ["mappings"],
    queryFn: mappingService.getAll
  });

  const { data: syncRunsData } = useQuery<PaginatedSyncRuns>({
    queryKey: ["syncRuns", historyPage, historyPageSize, statusFilter, search, startDate, endDate],
    queryFn: () => syncService.getSyncHistory(historyPage, historyPageSize, statusFilter, startDate, endDate, search),
  });
  const syncRuns = syncRunsData?.data || [];

  const { data: auditLogs = {data: [], total: 0} } = useQuery<PaginatedAuditLogs>({
    queryKey: ["auditLogs", auditActionType, auditSearch, auditStartDate, auditEndDate, ipFilter, auditPage, auditPageSize],
    queryFn: () => auditService.getAuditLogs({ 
      skip: (auditPage - 1) * auditPageSize,
      limit: auditPageSize, 
      action_type: auditActionType, 
      start_date: auditStartDate, 
      end_date: auditEndDate, 
      user: auditSearch, 
      ip_address: ipFilter 
    })
  });

  const { data: kpiData } = useQuery({
    queryKey: ["kpi"],
    queryFn: syncService.getKpi
  });

  const filteredMappings = useMemo(
    () => mappings.filter((m) => (m.zammad_type_name + m.kimai_activity_name).toLowerCase().includes(query.toLowerCase())),
    [mappings, query]
  );

  // Compute KPIs
  const kpi = useMemo(() => [
    { label: "Active connectors", value: connectors.filter(c => c.is_active).length, icon: Link2 },
    { label: "Mappings", value: mappings.length, icon: Waypoints },
    { label: "Open conflicts", value: kpiData?.open_conflicts || 0, icon: AlertTriangle },
    { label: "Last sync (UTC)", value: kpiData?.last_sync ? new Date(kpiData.last_sync).toLocaleString() : "Never", icon: History }
  ], [connectors, mappings, kpiData]);

  const recentRuns = useMemo(() => 
    syncRuns.slice(0, 3).map((run: SyncRun) => ({
      id: `#${run.id}`,
      status: run.status === 'completed' ? 'success' : run.status === 'running' ? 'running' : 'failed',
      duration: run.ended_at ? computeDuration(run.started_at, run.ended_at) : "00:00",
      at: new Date(run.started_at).toLocaleString()
    })),
    [syncRuns]
  );

  const chartData = kpiData?.weekly_minutes || [];

  // Run sync mutation
  const runSyncMutation = useMutation<SyncResponse>({
    mutationFn: () => syncService.triggerSync(),
    onSuccess: (response: SyncResponse) => {
      queryClient.invalidateQueries({ queryKey: ["syncRuns"] });
      queryClient.invalidateQueries({ queryKey: ["conflicts"] });
      queryClient.invalidateQueries({ queryKey: ["kpi"] });
      queryClient.invalidateQueries({ queryKey: ["auditLogs"] });
      
      if (response.status === 'failed') {
        toast({ 
          title: "Sync Failed", 
          description: response.error_detail || "Sync encountered an error",
          variant: "destructive" 
        });
      } else {
        toast({ 
          title: "Sync Completed", 
          description: response.message || `Successfully synced ${response.num_created} entries`
        });
      }
    },
    onError: (error: any) => {
      const errorMsg = error.response?.data?.detail || error.message || 'Sync failed';
      toast({ title: "Error", description: errorMsg, variant: "destructive" });
    }
  });

  // Test existing connector mutation
  const testExistingMutation = useMutation({
    mutationFn: (id: number) => connectorService.testConnection({ id }),
    onMutate: (variables: number) => {
      const id = variables;
      setPendingTests(prev => new Set([...prev, id]));
    },
    onSuccess: (data: ValidationResponse, variables: number) => {
      const id = variables;
      setTestResults(prev => ({ ...prev, [id]: { valid: data.valid, message: data.message, timestamp: new Date().toISOString() } }));
      setPendingTests(prev => {
        const newSet = new Set(prev);
        newSet.delete(id);
        return newSet;
      });
      queryClient.invalidateQueries({ queryKey: ["connectors"] });
      if (data.valid) {
        toast({ title: "Success", description: data.message });
      } else {
        toast({ title: "Test Failed", description: data.message, variant: "destructive" });
      }
    },
    onError: (error: any, variables: number) => {
      const id = variables;
      setPendingTests(prev => {
        const newSet = new Set(prev);
        newSet.delete(id);
        return newSet;
      });
      const errorMsg = error.response?.data?.message || error.message || 'Test failed';
      toast({ title: "Test Error", description: errorMsg, variant: "destructive" });
    }
  });

  const handleTestAll = async () => {
    const activeConnectors = connectors.filter(c => c.is_active);
    if (activeConnectors.length === 0) {
      toast({ title: "No Active Connectors", description: "Enable connectors to test them.", variant: "default" });
      return;
    }

    setTestResults({});
    setTestAllPending(true);
    let passed = 0;
    let total = activeConnectors.length;

    for (const connector of activeConnectors) {
      try {
        await testExistingMutation.mutateAsync(connector.id);
        if (testResults[connector.id]?.valid) passed++;
      } catch (error) {
        // Error already handled by mutation
      }
    }

    setTestAllPending(false);
    const summary = `${passed} of ${total} tests passed`;
    toast({ 
      title: "Test All Complete", 
      description: summary,
      variant: passed === total ? "default" : "destructive" 
    });

    queryClient.invalidateQueries({ queryKey: ["connectors"] });
  };

  return (
    <div className="min-h-screen bg-linear-to-b from-background to-muted/40">
      {/* Top Bar */}
      <div className="sticky top-0 z-40 border-b bg-background/80 backdrop-blur-sm supports-backdrop-filter:bg-background/60">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-3 px-4 py-3">
          <div className="flex items-center gap-2">
            <motion.div initial={{ rotate: -20, opacity: 0 }} animate={{ rotate: 0, opacity: 1 }}>
              <TimerReset className="h-6 w-6" />
            </motion.div>
            <span className="text-lg font-semibold tracking-tight">SyncHub · Zammad → Kimai</span>
            <Badge variant="secondary" className="ml-1">v0.9</Badge>
          </div>

          <div className="flex items-center gap-2">
            <ScheduleDialog />
            <Button size="sm" className="gap-2" onClick={() => runSyncMutation.mutate()}>
              <Play className="h-4 w-4" /> Run sync now
            </Button>
          </div>
        </div>
      </div>

      {/* Body */}
      <div className="mx-auto grid grid-cols-1 max-w-7xl gap-6 px-4 py-6 lg:grid-cols-[240px_1fr]">
        {/* Sidebar */}
        <aside className="hidden lg:block">
          <Card className="sticky top-20 shadow-xs">
            <CardHeader>
              <CardTitle className="text-base">Navigation</CardTitle>
              <CardDescription>Configure, map, reconcile, audit.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-1 text-sm">
              <a className="flex items-center justify-between rounded-xl p-2 hover:bg-muted" href="#dashboard">
                <span className="flex items-center gap-2"><Database className="h-4 w-4"/> Dashboard</span>
                <ArrowRight className="h-4 w-4"/>
              </a>
              <a className="flex items-center justify-between rounded-xl p-2 hover:bg-muted" href="#connectors">
                <span className="flex items-center gap-2"><Link2 className="h-4 w-4"/> Connectors</span>
                <ArrowRight className="h-4 w-4"/>
              </a>
              <a className="flex items-center justify-between rounded-xl p-2 hover:bg-muted" href="#mappings">
                <span className="flex items-center gap-2"><Waypoints className="h-4 w-4"/> Mappings</span>
                <ArrowRight className="h-4 w-4"/>
              </a>
              <a className="flex items-center justify-between rounded-xl p-2 hover:bg-muted" href="#reconcile">
                <span className="flex items-center gap-2"><Activity className="h-4 w-4"/> Reconcile</span>
                <ArrowRight className="h-4 w-4"/>
              </a>
              <a className="flex items-center justify-between rounded-xl p-2 hover:bg-muted" href="#audit">
                <span className="flex items-center gap-2"><FileClock className="h-4 w-4"/> Audit & History</span>
                <ArrowRight className="h-4 w-4"/>
              </a>
            </CardContent>
          </Card>
        </aside>

        {/* Main Column */}
        <main className="space-y-8">
          {/* DASHBOARD */}
          <section id="dashboard" className="space-y-4">
            <SectionHeader
              title="Dashboard"
              description="Overview of your Zammad ↔︎ Kimai synchronization"
              actions={<Pill ok />}
            />
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {kpi.map((s) => (
                <StatCard key={s.label} label={s.label} value={s.value} icon={s.icon} />
              ))}
            </div>

            <div className="grid gap-4 lg:grid-cols-3">
              <Card className="lg:col-span-2">
                <CardHeader>
                  <CardTitle>Minutes synced (last 7 days)</CardTitle>
                  <CardDescription>Sum of unique timesheets pushed to Kimai</CardDescription>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={220}>
                    <AreaChart data={chartData} margin={{ left: 0, right: 0 }}>
                      <defs>
                        <linearGradient id="fill" x1="0" x2="0" y1="0" y2="1">
                          <stop offset="5%" stopOpacity={0.3} />
                          <stop offset="95%" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid vertical={false} />
                      <XAxis dataKey="day" tickLine={false} axisLine={false} />
                      <RechartsTooltip />
                      <Area type="monotone" dataKey="minutes" strokeWidth={2} fillOpacity={1} fill="url(#fill)" />
                    </AreaChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Recent Runs</CardTitle>
                  <CardDescription>Last 3 sync executions</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  {recentRuns.map((r) => (
                    <div key={r.id} className="flex items-center justify-between rounded-xl border p-3">
                      <div className="space-y-1">
                        <div className="font-medium">{r.id}</div>
                        <div className="text-xs text-muted-foreground">{r.at}</div>
                      </div>
                      <div className="flex items-center gap-3">
                        <Badge variant={r.status === "success" ? "default" : r.status === "running" ? "secondary" : "destructive"}>
                          {r.status === 'running' ? 'running' : r.status === 'success' ? 'completed' : 'failed'}
                        </Badge>
                        <Badge variant="outline">{r.duration}</Badge>
                      </div>
                    </div>
                  ))}
                </CardContent>
              </Card>
            </div>
          </section>

          {/* CONNECTORS */}
          <section id="connectors" className="space-y-4">
            <SectionHeader
              title="Connectors"
              description="Authorize and configure integrations"
              actions={
                <div className="flex items-center gap-2">
                  <ConnectorDialog />
                  <Button 
                    variant="outline" 
                    size="sm" 
                    className="gap-2" 
                    onClick={handleTestAll}
                    disabled={connectors.filter(c => c.is_active).length === 0 || testAllPending}
                  >
                    <RefreshCw className={`h-4 w-4 ${testAllPending ? 'animate-spin' : ''}`} />
                    {testAllPending ? 'Testing All...' : 'Test All'}
                  </Button>
                </div>
              }
            />
            {connectors.length === 0 ? (
              <Card className="flex flex-col items-center justify-center p-8 text-center">
                <UploadCloud className="h-12 w-12 text-muted-foreground mb-4" />
                <h3 className="text-lg font-semibold mb-2">No connectors yet</h3>
                <p className="text-sm text-muted-foreground mb-4">Get started by adding your first integration.</p>
                <ConnectorDialog />
              </Card>
            ) : (
              <div className="grid gap-4 md:grid-cols-2">
                {connectors.map((c) => (
                  <Card key={c.id} className="shadow-xs">
                    <CardHeader>
                    <CardTitle className="flex items-center justify-between text-base">
                      <span className="flex items-center gap-2">{c.type === 'zammad' ? <ZammadIcon className="h-4 w-4" /> : <KimaiIcon className="h-4 w-4" />} {c.name}</span>
                      <div className="flex items-center space-x-1">
                        <span className="px-2 py-1 rounded-full text-xs font-medium bg-primary/10 text-primary">
                          {c.type.charAt(0).toUpperCase() + c.type.slice(1)}
                        </span>
                        <Badge variant={c.is_active ? "default" : "destructive"}>{c.is_active ? "Enabled" : "Disabled"}</Badge>
                      </div>
                    </CardTitle>
                      <CardDescription>{c.base_url}</CardDescription>
                    </CardHeader>
                    <CardContent className="flex items-center justify-between">
                      {pendingTests.has(c.id) ? (
                        <div className="text-sm text-muted-foreground flex items-center gap-1">
                          <RefreshCw className="h-3 w-3 animate-spin" />
                          Testing...
                        </div>
                      ) : testResults[c.id]?.valid ? (
                        <Badge variant="default" className="text-xs flex items-center gap-1">
                          <Check className="h-3 w-3" />
                          Connected
                        </Badge>
                      ) : testResults[c.id] ? (
                        <Badge variant="destructive" className="text-xs flex items-center gap-1">
                          <AlertTriangle className="h-3 w-3" />
                          Failed
                        </Badge>
                      ) : (
                        <div className="text-sm text-muted-foreground">Untested</div>
                      )}
                      <div className="flex items-center gap-2">
                        <ConnectorDialog item={c} />
                        <Button 
                          variant="outline" 
                          size="sm" 
                          className="gap-2" 
                          onClick={() => testExistingMutation.mutate(c.id)}
                          disabled={pendingTests.has(c.id)}
                        >
                          <RefreshCw className={`h-4 w-4 ${pendingTests.has(c.id) ? 'animate-spin' : ''}`} />
                          {pendingTests.has(c.id) ? 'Testing...' : 'Test'}
                        </Button>
                        <DeleteConnectorDialog item={c} />
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </section>

          {/* MAPPINGS */}
          <section id="mappings" className="space-y-4">
            <SectionHeader
              title="Mappings"
              description="Map Zammad activity types to Kimai activities — set billable rules"
              actions={<MappingDialog />}
            />
            <Card>
              <CardHeader className="flex flex-row items-end justify-between gap-4">
                <div>
                  <CardTitle>Activity mappings</CardTitle>
                  <CardDescription>Used during normalization & reconciliation</CardDescription>
                </div>
                <div className="flex items-center gap-2">
                  <Input placeholder="Search…" value={query} onChange={(e) => setQuery(e.target.value)} className="w-56" />
                  <Button variant="outline" size="sm" className="gap-2"><Tags className="h-4 w-4"/> Export</Button>
                </div>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-full sm:w-[40%]">Source (Zammad)</TableHead>
                      <TableHead className="w-full sm:w-[40%]">Target (Kimai)</TableHead>
                      <TableHead className="hidden sm:table-cell">Billable</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredMappings.map((row) => (
                      <TableRow key={row.id}>
                        <TableCell className="break-words">{row.zammad_type_name}</TableCell>
                        <TableCell className="break-words">{row.kimai_activity_name}</TableCell>
                        <TableCell className="hidden sm:table-cell">
                          <Badge variant="secondary">N/A</Badge>
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex justify-end gap-2">
                            <MappingDialog row={row} />
                            <DeleteMappingDialog item={row} />
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </section>

          {/* RECONCILE */}
          <section id="reconcile" className="space-y-4">
            <SectionHeader
              title="Reconcile"
              description="Review conflicts and missing entries for manual resolution"
            />
            
            {/* Info Banner */}
            <Alert>
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription>
                <div className="font-medium mb-1">Sync Mapping Rules:</div>
                <ul className="text-sm space-y-1 list-disc list-inside">
                  <li><strong>Ticket → Project:</strong> Each Zammad ticket becomes a Kimai project (title = ticket number)</li>
                  <li><strong>Customer Auto-creation:</strong> If customer missing in Kimai, created from Zammad user/org. All Zammad org users aggregate to the same customer</li>
                  <li><strong>Worklog → Timesheet:</strong> Each Zammad worklog becomes a Kimai timesheet with mapped activity + <code className="bg-muted px-1 rounded">Zammad</code> tag</li>
                </ul>
              </AlertDescription>
            </Alert>

            <ReconcileSection />
          </section>

          {/* AUDIT */}
          <section id="audit" className="space-y-4">
            <SectionHeader
              title="Audit & History"
              description="Deterministic logs of every change and API call"
            />
            <Card>
              <CardHeader className="flex flex-row items-end justify-between gap-4">
                <div>
                  <CardTitle>Audit & History</CardTitle>
                  <CardDescription>Sync runs and audit logs</CardDescription>
                </div>
              </CardHeader>
              <CardContent>
                <Tabs value={auditTab} onValueChange={(v) => setAuditTab(v as "sync-history" | "audit-logs")} className="w-full">
                  <TabsList>
                    <TabsTrigger value="sync-history">Sync History</TabsTrigger>
                    <TabsTrigger value="audit-logs">Audit Logs</TabsTrigger>
                  </TabsList>
                  <TabsContent value="sync-history" className="space-y-4">
                    <div className="flex items-center gap-2">
                      <Select value={statusFilter} onValueChange={setStatusFilter}>
                        <SelectTrigger className="w-[180px]">
                          <SelectValue placeholder="Filter status" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">All</SelectItem>
                          <SelectItem value="completed">Completed</SelectItem>
                          <SelectItem value="failed">Failed</SelectItem>
                          <SelectItem value="running">Running</SelectItem>
                        </SelectContent>
                      </Select>
                      <Input placeholder="Search ID or error" value={search} onChange={(e) => setSearch(e.target.value)} className="max-w-sm" />
                      <Input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} className="w-40" />
                      <Input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} className="w-40" />
                    </div>
                    <Button variant="outline" onClick={async () => {
                      try {
                        const blob = await syncService.exportSyncRuns('csv', statusFilter, startDate, endDate);
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = 'sync-history.csv';
                        a.click();
                        URL.revokeObjectURL(url);
                        toast({ title: "Export started", description: "Download will begin shortly" });
                      } catch (error) {
                        toast({ title: "Export failed", description: "Failed to generate export", variant: "destructive" });
                      }
                    }}>
                      Export CSV
                    </Button>
                    <div className="rounded-md border">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>ID</TableHead>
                            <TableHead>Trigger</TableHead>
                            <TableHead>Status</TableHead>
                            <TableHead>Started</TableHead>
                            <TableHead>Duration</TableHead>
                            <TableHead>Synced</TableHead>
                            <TableHead>Already Synced</TableHead>
                            <TableHead>Skipped</TableHead>
                            <TableHead>Failed</TableHead>
                            <TableHead>Conflicts</TableHead>
                            <TableHead>Actions</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {syncRuns.map((run: SyncRun) => (
                            <TableRow key={run.id}>
                              <TableCell>#{run.id}</TableCell>
                              <TableCell>
                                <Badge variant={run.trigger_type === 'manual' ? "default" : "secondary"}>
                                  {run.trigger_type ? run.trigger_type.charAt(0).toUpperCase() + run.trigger_type.slice(1) : 'Unknown'}
                                </Badge>
                              </TableCell>
                              <TableCell>
                                <Badge variant={run.status === 'completed' ? "default" : run.status === 'running' ? "secondary" : "destructive"}>
                                  {run.status}
                                </Badge>
                              </TableCell>
                              <TableCell>{new Date(run.started_at).toLocaleString()}</TableCell>
                              <TableCell>{run.ended_at ? computeDuration(run.started_at, run.ended_at) : 'Running'}</TableCell>
                              <TableCell><Badge variant="default">{run.entries_synced}</Badge></TableCell>
                              <TableCell><Badge variant="secondary">{run.entries_already_synced ?? 0}</Badge></TableCell>
                              <TableCell><Badge variant="secondary">{run.entries_skipped ?? 0}</Badge></TableCell>
                              <TableCell><Badge variant="destructive">{run.entries_failed ?? 0}</Badge></TableCell>
                              <TableCell><Badge variant="destructive">{run.conflicts_detected}</Badge></TableCell>
                              <TableCell>
                                <div className="flex gap-2">
                                  <Dialog>
                                    <DialogTrigger asChild>
                                      <Button variant="outline" size="sm">
                                        View Logs
                                      </Button>
                                    </DialogTrigger>
                                    <DialogContent>
                                      <DialogHeader>
                                        <DialogTitle>Logs for Run #{run.id}</DialogTitle>
                                      </DialogHeader>
                                      <AuditLogs runId={run.id} />
                                    </DialogContent>
                                  </Dialog>
                                  {run.status === 'failed' && (
                                    <Button variant="outline" size="sm" onClick={() => runSyncMutation.mutate()}>
                                      Retry
                                    </Button>
                                  )}
                                </div>
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                    {syncRuns.length === 0 && (
                      <div className="text-center text-muted-foreground py-8">
                        <p>No sync runs match the filter. Trigger a sync to start tracking executions.</p>
                        <Button onClick={() => runSyncMutation.mutate()} className="mt-4">
                          <Play className="h-4 w-4 mr-2" />
                          Run Sync Now
                        </Button>
                      </div>
                    )}
                    {syncRuns.length > 0 && (
                      <div className="flex items-center justify-between mt-4">
                        <div className="text-sm text-muted-foreground">
                          Showing {((historyPage - 1) * historyPageSize) + 1} to {Math.min(historyPage * historyPageSize, syncRunsData?.total || 0)} of {syncRunsData?.total || 0} results
                        </div>
                        <Pagination>
                          <PaginationContent>
                            <PaginationItem>
                              <PaginationPrevious 
                                onClick={() => setHistoryPage(p => Math.max(1, p - 1))} 
                                className={historyPage === 1 ? 'pointer-events-none opacity-50' : 'cursor-pointer'}
                              />
                            </PaginationItem>
                            {historyPage > 2 && (
                              <>
                                <PaginationItem>
                                  <PaginationLink onClick={() => setHistoryPage(1)} className="cursor-pointer">
                                    1
                                  </PaginationLink>
                                </PaginationItem>
                                <PaginationItem>
                                  <PaginationEllipsis />
                                </PaginationItem>
                              </>
                            )}
                            {historyPage > 1 && (
                              <PaginationItem>
                                <PaginationLink onClick={() => setHistoryPage(historyPage - 1)} className="cursor-pointer">
                                  {historyPage - 1}
                                </PaginationLink>
                              </PaginationItem>
                            )}
                            <PaginationItem>
                              <PaginationLink className="bg-primary text-primary-foreground">
                                {historyPage}
                              </PaginationLink>
                            </PaginationItem>
                            {historyPage < Math.ceil((syncRunsData?.total || 0) / historyPageSize) && (
                              <PaginationItem>
                                <PaginationLink onClick={() => setHistoryPage(historyPage + 1)} className="cursor-pointer">
                                  {historyPage + 1}
                                </PaginationLink>
                              </PaginationItem>
                            )}
                            {historyPage < Math.ceil((syncRunsData?.total || 0) / historyPageSize) - 1 && (
                              <>
                                <PaginationItem>
                                  <PaginationEllipsis />
                                </PaginationItem>
                                <PaginationItem>
                                  <PaginationLink 
                                    onClick={() => setHistoryPage(Math.ceil((syncRunsData?.total || 0) / historyPageSize))} 
                                    className="cursor-pointer"
                                  >
                                    {Math.ceil((syncRunsData?.total || 0) / historyPageSize)}
                                  </PaginationLink>
                                </PaginationItem>
                              </>
                            )}
                            <PaginationItem>
                              <PaginationNext 
                                onClick={() => setHistoryPage(p => p < Math.ceil((syncRunsData?.total || 0) / historyPageSize) ? p + 1 : p)} 
                                className={historyPage >= Math.ceil((syncRunsData?.total || 0) / historyPageSize) ? 'pointer-events-none opacity-50' : 'cursor-pointer'}
                              />
                            </PaginationItem>
                          </PaginationContent>
                        </Pagination>
                      </div>
                    )}
                  </TabsContent>
                  <TabsContent value="audit-logs" className="space-y-4">
                    <div className="flex items-center gap-2">
                      <Select value={auditActionType} onValueChange={(v) => setAuditActionType(v as "all" | "access" | "sync")}>
                        <SelectTrigger className="w-[180px]">
                          <SelectValue placeholder="Filter action type" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="all">All</SelectItem>
                          <SelectItem value="access">Access</SelectItem>
                          <SelectItem value="sync">Sync</SelectItem>
                        </SelectContent>
                      </Select>
                      <Input placeholder="Search user or action" value={auditSearch} onChange={(e) => setAuditSearch(e.target.value)} className="max-w-sm" />
                      <Input type="date" value={auditStartDate} onChange={(e) => setAuditStartDate(e.target.value)} className="w-40" />
                      <Input type="date" value={auditEndDate} onChange={(e) => setAuditEndDate(e.target.value)} className="w-40" />
                      <Input placeholder="IP Address" value={ipFilter} onChange={(e) => setIpFilter(e.target.value)} className="w-32" />
                    </div>
                    <div className="flex items-center gap-2">
                      <Button variant="outline" onClick={() => queryClient.invalidateQueries({ queryKey: ["auditLogs"] })}>
                        Refresh
                      </Button>
                      <Button variant="outline" onClick={async () => {
                        try {
                          const blob = await auditService.export('csv');
                          const url = URL.createObjectURL(blob);
                          const a = document.createElement('a');
                          a.href = url;
                          a.download = 'audit-logs.csv';
                          a.click();
                          URL.revokeObjectURL(url);
                          toast({ title: "Export started", description: "Download will begin shortly" });
                        } catch (error) {
                          toast({ title: "Export failed", description: "Failed to generate export", variant: "destructive" });
                        }
                      }}>
                        Export CSV
                      </Button>
                    </div>
                    <div className="rounded-md border">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Action</TableHead>
                            <TableHead>Entity</TableHead>
                            <TableHead>User</TableHead>
                            <TableHead>IP Address</TableHead>
                            <TableHead>Timestamp</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {auditLogs.data.map((log: AuditLog) => (
                            <TableRow key={log.id}>
                              <TableCell className="font-medium">
                                <Badge variant={log.action.startsWith('sync') ? "default" : "secondary"}>
                                  {log.action}
                                </Badge>
                              </TableCell>
                              <TableCell>
                                {log.entity_type && log.entity_id ? (
                                  <span className="text-sm">{log.entity_type} #{log.entity_id}</span>
                                ) : (
                                  <span className="text-sm text-muted-foreground">N/A</span>
                                )}
                              </TableCell>
                              <TableCell>{log.user || "System"}</TableCell>
                              <TableCell>
                                {log.ip_address ? (
                                  <TooltipProvider>
                                    <Tooltip>
                                      <TooltipTrigger asChild>
                                        <span className="text-sm">{log.ip_address}</span>
                                      </TooltipTrigger>
                                      <TooltipContent>
                                        <p>User Agent: {log.user_agent || "N/A"}</p>
                                      </TooltipContent>
                                    </Tooltip>
                                  </TooltipProvider>
                                ) : (
                                  <span className="text-sm text-muted-foreground">N/A</span>
                                )}
                              </TableCell>
                              <TableCell className="text-sm text-muted-foreground">
                                {new Date(log.created_at).toLocaleString()}
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                    {auditLogs.data.length === 0 && (
                      <div className="text-center text-muted-foreground py-8">
                        <p>No audit logs match the filter. Perform actions (e.g., sync, configure connectors) to generate logs.</p>
                      </div>
                    )}
                    <div className="flex items-center justify-between mt-4">
                      <div className="text-sm text-muted-foreground">
                        Showing {((auditPage - 1) * auditPageSize) + 1} to {Math.min(auditPage * auditPageSize, auditLogs.total)} of {auditLogs.total} results
                      </div>
                      <Pagination>
                        <PaginationContent>
                          <PaginationItem>
                            <PaginationPrevious 
                              onClick={() => setAuditPage(p => Math.max(1, p - 1))} 
                              className={auditPage === 1 ? 'pointer-events-none opacity-50' : 'cursor-pointer'}
                            />
                          </PaginationItem>
                          {auditPage > 2 && (
                            <>
                              <PaginationItem>
                                <PaginationLink onClick={() => setAuditPage(1)} className="cursor-pointer">
                                  1
                                </PaginationLink>
                              </PaginationItem>
                              <PaginationItem>
                                <PaginationEllipsis />
                              </PaginationItem>
                            </>
                          )}
                          {auditPage > 1 && (
                            <PaginationItem>
                              <PaginationLink onClick={() => setAuditPage(auditPage - 1)} className="cursor-pointer">
                                {auditPage - 1}
                              </PaginationLink>
                            </PaginationItem>
                          )}
                          <PaginationItem>
                            <PaginationLink className="bg-primary text-primary-foreground">
                              {auditPage}
                            </PaginationLink>
                          </PaginationItem>
                          {auditPage < Math.ceil(auditLogs.total / auditPageSize) && (
                            <PaginationItem>
                              <PaginationLink onClick={() => setAuditPage(auditPage + 1)} className="cursor-pointer">
                                {auditPage + 1}
                              </PaginationLink>
                            </PaginationItem>
                          )}
                          {auditPage < Math.ceil(auditLogs.total / auditPageSize) - 1 && (
                            <>
                              <PaginationItem>
                                <PaginationEllipsis />
                              </PaginationItem>
                              <PaginationItem>
                                <PaginationLink 
                                  onClick={() => setAuditPage(Math.ceil(auditLogs.total / auditPageSize))} 
                                  className="cursor-pointer"
                                >
                                  {Math.ceil(auditLogs.total / auditPageSize)}
                                </PaginationLink>
                              </PaginationItem>
                            </>
                          )}
                          <PaginationItem>
                            <PaginationNext 
                              onClick={() => setAuditPage(p => p < Math.ceil(auditLogs.total / auditPageSize) ? p + 1 : p)} 
                              className={auditPage >= Math.ceil(auditLogs.total / auditPageSize) ? 'pointer-events-none opacity-50' : 'cursor-pointer'}
                            />
                          </PaginationItem>
                        </PaginationContent>
                      </Pagination>
                    </div>
                  </TabsContent>
                </Tabs>
              </CardContent>
            </Card>
          </section>
        </main>
      </div>
    </div>
  );
}
