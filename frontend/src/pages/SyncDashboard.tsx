import React, { useMemo, useState } from "react";
import { motion } from "framer-motion";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  BadgeCheck,
  CalendarClock,
  Check,
  Database,
  FileClock,
  History,
  Link2,
  Play,
  RefreshCw,
  Settings,
  Tags,
  TimerReset,
  UploadCloud,
  Waypoints
} from "lucide-react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis } from "recharts";
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
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { useToast } from "@/hooks/use-toast";

import { connectorService, mappingService, syncService } from "@/services/api.service";
import type { Connector, ActivityMapping } from "@/types";

// Utility UI components
const Pill = ({ ok }: { ok: boolean }) => (
  <Badge variant={ok ? "default" : "destructive"} className="rounded-full px-2 py-0 text-xs">
    {ok ? "All good" : "Attention"}
  </Badge>
);

function StatCard({ label, value, icon: Icon }: { label: string; value: React.ReactNode; icon: any }) {
  return (
    <Card className="shadow-sm">
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

// Connector Dialog
function ConnectorDialog({ item, onSuccess }: { item?: Connector; onSuccess?: () => void }) {
  const [enabled, setEnabled] = useState(item?.is_active ?? true);
  const [baseUrl, setBaseUrl] = useState(item?.base_url ?? "");
  const [apiToken, setApiToken] = useState("");
  const [name, setName] = useState(item?.name ?? "");
  const [type, setType] = useState<'zammad' | 'kimai'>(item?.type ?? "zammad");
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const createMutation = useMutation({
    mutationFn: (data: any) => connectorService.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["connectors"] });
      queryClient.invalidateQueries({ queryKey: ["kpi"] });
      toast({ title: "Success", description: "Connector created successfully" });
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
      onSuccess?.();
    },
    onError: () => {
      toast({ title: "Error", description: "Failed to update connector", variant: "destructive" });
    }
  });

  const handleSave = () => {
    const createData = {
      type,
      name,
      base_url: baseUrl,
      api_token: apiToken,
      is_active: enabled,
      settings: {}
    };

    const updateData = {
      name,
      base_url: baseUrl,
      api_token: apiToken || undefined,
      is_active: enabled,
      settings: {}
    };

    if (item) {
      updateMutation.mutate(updateData);
    } else {
      createMutation.mutate(createData);
    }
  };

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="gap-2">
          <Settings className="h-4 w-4" /> {item ? "Configure" : "Add Connector"}
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>Configure {item?.name ?? "Connector"}</DialogTitle>
          <DialogDescription>Enter credentials and endpoint details. Secrets are stored encrypted in the service DB.</DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-2">
          {!item && (
            <>
              <div className="grid grid-cols-4 items-center gap-2">
                <Label className="text-right">Type</Label>
                <Select value={type} onValueChange={(v: 'zammad' | 'kimai') => setType(v)}>
                  <SelectTrigger className="col-span-3">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="zammad">Zammad</SelectItem>
                    <SelectItem value="kimai">Kimai</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="grid grid-cols-4 items-center gap-2">
                <Label className="text-right">Name</Label>
                <Input className="col-span-3" value={name} onChange={(e) => setName(e.target.value)} />
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
            <Input className="col-span-3" value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} />
          </div>
          <div className="grid grid-cols-4 items-center gap-2">
            <Label className="text-right">API Token</Label>
            <Input className="col-span-3" type="password" placeholder="••••••••••" value={apiToken} onChange={(e) => setApiToken(e.target.value)} />
          </div>
        </div>
        <DialogFooter>
          <Button variant="ghost">Cancel</Button>
          <Button className="gap-2" onClick={handleSave}>
            <BadgeCheck className="h-4 w-4" /> Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// Mapping Dialog
function MappingDialog({ row, onSuccess }: { row?: ActivityMapping; onSuccess?: () => void }) {
  const [source, setSource] = useState(row?.zammad_type_name ?? "");
  const [target, setTarget] = useState(row?.kimai_activity_name ?? "");
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const createMutation = useMutation({
    mutationFn: (data: any) => mappingService.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["mappings"] });
      queryClient.invalidateQueries({ queryKey: ["kpi"] });
      toast({ title: "Success", description: "Mapping created successfully" });
      onSuccess?.();
    },
    onError: () => {
      toast({ title: "Error", description: "Failed to create mapping", variant: "destructive" });
    }
  });

  const updateMutation = useMutation({
    mutationFn: (data: any) => mappingService.update(row!.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["mappings"] });
      queryClient.invalidateQueries({ queryKey: ["kpi"] });
      toast({ title: "Success", description: "Mapping updated successfully" });
      onSuccess?.();
    },
    onError: () => {
      toast({ title: "Error", description: "Failed to update mapping", variant: "destructive" });
    }
  });

  const handleSave = () => {
    const createData = {
      zammad_type_id: row?.zammad_type_id ?? 1,
      zammad_type_name: source,
      kimai_activity_id: row?.kimai_activity_id ?? 1,
      kimai_activity_name: target
    };

    const updateData = {
      zammad_type_name: source,
      kimai_activity_id: row?.kimai_activity_id,
      kimai_activity_name: target
    };

    if (row) {
      updateMutation.mutate(updateData);
    } else {
      createMutation.mutate(createData);
    }
  };

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button size="sm" variant="outline" className="gap-2">
          <Waypoints className="h-4 w-4" /> {row ? "Edit" : "New mapping"}
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{row ? "Edit mapping" : "Create mapping"}</DialogTitle>
          <DialogDescription>Define how Zammad activities map to Kimai activities, and whether the time is billable.</DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-2">
          <div className="grid grid-cols-4 items-center gap-2">
            <Label className="text-right">Source</Label>
            <Input className="col-span-3" value={source} onChange={(e) => setSource(e.target.value)} placeholder="Zammad: Support" />
          </div>
          <div className="grid grid-cols-4 items-center gap-2">
            <Label className="text-right">Target</Label>
            <Input className="col-span-3" value={target} onChange={(e) => setTarget(e.target.value)} placeholder="Kimai: Billable Support" />
          </div>
        </div>
        <DialogFooter>
          <Button variant="ghost">Cancel</Button>
          <Button className="gap-2" onClick={handleSave}>
            <Check className="h-4 w-4" /> Save mapping
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// Main Dashboard Component
export default function SyncDashboard() {
  const [query, setQuery] = useState("");
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

  const filteredMappings = useMemo(
    () => mappings.filter((m) => (m.zammad_type_name + m.kimai_activity_name).toLowerCase().includes(query.toLowerCase())),
    [mappings, query]
  );

  // Mock data for demo (replace with real queries)
  const kpi = [
    { label: "Active connectors", value: connectors.filter(c => c.is_active).length, icon: Link2 },
    { label: "Mappings", value: mappings.length, icon: Waypoints },
    { label: "Open conflicts", value: 0, icon: AlertTriangle },
    { label: "Last sync (UTC)", value: "2025‑11‑05 22:54:37", icon: History }
  ];

  const recentRuns = [
    { id: "#1276", status: "success", duration: "00:42", at: "2025‑11‑05 22:54:37" },
    { id: "#1275", status: "success", duration: "00:37", at: "2025‑11‑04 09:12:04" },
    { id: "#1274", status: "warning", duration: "01:18", at: "2025‑11‑03 17:03:18" }
  ];

  const chartData = [
    { day: "Mon", minutes: 132 },
    { day: "Tue", minutes: 248 },
    { day: "Wed", minutes: 187 },
    { day: "Thu", minutes: 210 },
    { day: "Fri", minutes: 275 },
    { day: "Sat", minutes: 95 },
    { day: "Sun", minutes: 60 }
  ];

  // Run sync mutation
  const runSyncMutation = useMutation({
    mutationFn: () => syncService.triggerSync(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["syncRuns"] });
      queryClient.invalidateQueries({ queryKey: ["kpi"] });
      toast({ title: "Success", description: "Sync completed successfully" });
    },
    onError: () => {
      toast({ title: "Error", description: "Sync failed", variant: "destructive" });
    }
  });

  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-muted/40">
      {/* Top Bar */}
      <div className="sticky top-0 z-40 border-b bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-3 px-4 py-3">
          <div className="flex items-center gap-2">
            <motion.div initial={{ rotate: -20, opacity: 0 }} animate={{ rotate: 0, opacity: 1 }}>
              <TimerReset className="h-6 w-6" />
            </motion.div>
            <span className="text-lg font-semibold tracking-tight">SyncHub · Zammad → Kimai</span>
            <Badge variant="secondary" className="ml-1">v0.9</Badge>
          </div>

          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" className="gap-2">
              <CalendarClock className="h-4 w-4" /> Schedule
            </Button>
            <Button size="sm" className="gap-2" onClick={() => runSyncMutation.mutate()}>
              <Play className="h-4 w-4" /> Run sync now
            </Button>
          </div>
        </div>
      </div>

      {/* Body */}
      <div className="mx-auto grid max-w-7xl gap-6 px-4 py-6 lg:grid-cols-[240px_1fr]">
        {/* Sidebar */}
        <aside className="hidden lg:block">
          <Card className="sticky top-20 shadow-sm">
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
                      <Tooltip />
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
                        <Badge variant={r.status === "success" ? "default" : r.status === "warning" ? "secondary" : "destructive"}>
                          {r.status}
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
              actions={<Button variant="outline" size="sm" className="gap-2"><UploadCloud className="h-4 w-4"/> Test connection</Button>}
            />
            <div className="grid gap-4 md:grid-cols-2">
              {connectors.map((c) => (
                <Card key={c.id} className="shadow-sm">
                  <CardHeader>
                    <CardTitle className="flex items-center justify-between text-base">
                      <span className="flex items-center gap-2"><Link2 className="h-4 w-4"/> {c.name}</span>
                      <Badge variant={c.is_active ? "default" : "destructive"}>{c.is_active ? "Enabled" : "Disabled"}</Badge>
                    </CardTitle>
                    <CardDescription>{c.base_url}</CardDescription>
                  </CardHeader>
                  <CardContent className="flex items-center justify-between">
                    <div className="text-sm text-muted-foreground">Connected</div>
                    <div className="flex items-center gap-2">
                      <ConnectorDialog item={c} />
                      <Button variant="ghost" size="sm" className="gap-2"><RefreshCw className="h-4 w-4"/> Re-auth</Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
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
                      <TableHead className="w-[40%]">Source (Zammad)</TableHead>
                      <TableHead className="w-[40%]">Target (Kimai)</TableHead>
                      <TableHead>Billable</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredMappings.map((row) => (
                      <TableRow key={row.id}>
                        <TableCell>{row.zammad_type_name}</TableCell>
                        <TableCell>{row.kimai_activity_name}</TableCell>
                        <TableCell>
                          <Badge variant="secondary">N/A</Badge>
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex justify-end gap-2">
                            <MappingDialog row={row} />
                            <Button size="sm" variant="ghost">Delete</Button>
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
              description="Match, diff and resolve between systems"
              actions={<Button size="sm" className="gap-2"><Check className="h-4 w-4"/> Apply selected</Button>}
            />
            <Tabs defaultValue="all" className="w-full">
              <TabsList>
                <TabsTrigger value="all">All</TabsTrigger>
                <TabsTrigger value="match">Matches</TabsTrigger>
                <TabsTrigger value="missing">Missing</TabsTrigger>
                <TabsTrigger value="conflicts">Conflicts</TabsTrigger>
              </TabsList>
              <TabsContent value="all" className="space-y-3">
                <Card>
                  <CardHeader>
                    <CardTitle>Diff view</CardTitle>
                    <CardDescription>Ticket → Project • Worklog → Timesheet</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {/* Demo row */}
                    <div className="rounded-xl border p-3">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div className="space-y-1">
                          <div className="font-medium">#2731 · Laptop migration</div>
                          <p className="text-xs text-muted-foreground">Customer: ACME (aggregated from Zammad org)</p>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge>match</Badge>
                          <Badge variant="outline">Zammad</Badge>
                          <ArrowRight className="h-4 w-4" />
                          <Badge variant="outline">Kimai</Badge>
                        </div>
                      </div>
                      <Separator className="my-3" />
                      <div className="grid gap-3 md:grid-cols-3">
                        <div className="space-y-1">
                          <div className="text-xs uppercase text-muted-foreground">Source worklog</div>
                          <div className="text-sm">02:30 · Support</div>
                        </div>
                        <div className="space-y-1">
                          <div className="text-xs uppercase text-muted-foreground">Target timesheet</div>
                          <div className="text-sm">02:30 · Billable Support</div>
                        </div>
                        <div className="flex items-center justify-end gap-2">
                          <Button variant="outline" size="sm">Ignore</Button>
                          <Button size="sm">Update</Button>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>
          </section>

          {/* AUDIT */}
          <section id="audit" className="space-y-4">
            <SectionHeader
              title="Audit & History"
              description="Deterministic logs of every change and API call"
            />
            <Card>
              <CardHeader>
                <CardTitle>Run history</CardTitle>
                <CardDescription>Immutable audit trail</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {recentRuns.map((r, i) => (
                  <div key={r.id} className="grid items-center gap-3 rounded-xl border p-3 md:grid-cols-[auto_1fr_auto]">
                    <div className="flex items-center gap-2">
                      <History className="h-4 w-4" />
                      <div className="text-sm font-medium">{r.id}</div>
                    </div>
                    <Progress value={i === 0 ? 100 : i === 1 ? 100 : 80} />
                    <div className="flex items-center gap-2">
                      <Badge variant={r.status === "success" ? "default" : r.status === "warning" ? "secondary" : "destructive"}>{r.status}</Badge>
                      <Badge variant="outline">{r.duration}</Badge>
                      <span className="text-xs text-muted-foreground">{r.at}</span>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          </section>

          <footer className="pb-10 pt-4 text-center text-xs text-muted-foreground">
            Built with ♥ for Belgian IT freelancers — configurable, auditable, and fast.
          </footer>
        </main>
      </div>
    </div>
  );
}
