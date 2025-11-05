import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/hooks/use-toast';
import { connectorService, conflictService, mappingService, syncService, auditService } from '@/services/api.service';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  AlertCircle,
  Clock,
  Play,
  RefreshCw,
  Database,
  Activity,
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import type { AuditLog } from '@/types';

export default function Dashboard() {
  const [stats, setStats] = useState({
    connectors: 0,
    mappings: 0,
    conflicts: 0,
    lastSync: null as string | null,
  });
  const [recentActivity, setRecentActivity] = useState<{ action: string; time: string; status: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const { isAuthenticated } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      
      // Fetch data with individual error handling to prevent complete failure
      const [connectors, mappings, conflicts, syncRuns, auditLogs] = await Promise.allSettled([
        connectorService.getAll(),
        mappingService.getAll(),
        conflictService.getAll(),
        syncService.getSyncHistory(),
        auditService.getAll({ limit: 5 }),
      ]);

      const connectorsData = connectors.status === 'fulfilled' ? connectors.value : [];
      const mappingsData = mappings.status === 'fulfilled' ? mappings.value : [];
      const conflictsData = conflicts.status === 'fulfilled' ? conflicts.value : [];
      const syncRunsData = syncRuns.status === 'fulfilled' ? syncRuns.value : [];
      const auditLogsData = auditLogs.status === 'fulfilled' ? auditLogs.value : [];

      const activeConnectors = (connectorsData as any[]).filter((c: any) => c.is_active).length;
      const pendingConflicts = (conflictsData as any[]).filter((c: any) => c.resolution_status === 'pending').length;
      const lastSyncRun = syncRunsData && syncRunsData.length > 0 ? syncRunsData[0].started_at : null;

      setStats({
        connectors: activeConnectors,
        mappings: (mappingsData as any[]).length,
        conflicts: pendingConflicts,
        lastSync: lastSyncRun ? new Date(lastSyncRun).toLocaleString() : null,
      });

      // Set recent activity from audit logs
      setRecentActivity(
        auditLogsData.map((log: AuditLog) => ({
          action: log.action,
          time: formatDistanceToNow(new Date(log.created_at), { addSuffix: true }),
          status: 'default'  // Can map based on action if needed
        }))
      );

      // Show warning if any requests failed (but don't block the UI)
      const failedRequests = [connectors, mappings, conflicts, syncRuns, auditLogs].filter(r => r.status === 'rejected');
      if (failedRequests.length > 0) {
        console.warn('Some dashboard data failed to load:', failedRequests);
      }
    } catch (error: any) {
      console.error('Dashboard error:', error);
      toast({
        title: "Failed to load dashboard data",
        description: error.response?.data?.detail || "Please try again later",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleRunSync = async () => {
    try {
      await syncService.triggerSync({});
      toast({
        title: "Sync initiated",
        description: "Manual sync started successfully",
      });
      fetchDashboardData();
    } catch (error: any) {
      toast({
        title: "Sync failed",
        description: error.response?.data?.detail || "Please check configuration",
        variant: "destructive",
      });
    }
  };

  const handleViewDetails = () => {
    navigate('/audit-logs');
  };

  const StatCard = ({ 
    title, 
    value, 
    description, 
    icon: Icon, 
    color = "default" 
  }: {
    title: string;
    value: any;
    description: string;
    icon: React.ComponentType<{ className?: string }>;
    color?: "default" | "success" | "warning";
  }) => (
    <Card className="card-hover shadow-elevated border-border/50">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-foreground/80">{title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold text-foreground">{value}</div>
        <p className="text-xs text-muted-foreground mt-1">{description}</p>
        {color !== "default" && (
          <span className={`mt-2 inline-block px-2 py-1 rounded-full text-xs font-medium border ${
            color === "success" ? "bg-green-100 text-green-800 border-green-200" : "bg-yellow-100 text-yellow-800 border-yellow-200"
          }`}>
            {color === "success" ? "All good" : "Pending"}
          </span>
        )}
      </CardContent>
    </Card>
  );

  const LoadingCard = () => (
    <Card className="animate-pulse">
      <CardHeader className="space-y-2">
        <div className="h-4 bg-muted rounded w-3/4"></div>
        <div className="h-3 bg-muted rounded w-1/2"></div>
      </CardHeader>
      <CardContent>
        <div className="h-6 bg-muted rounded w-1/4 mb-2"></div>
        <div className="h-4 bg-muted rounded w-full"></div>
      </CardContent>
    </Card>
  );

  useEffect(() => {
    if (isAuthenticated) {
      fetchDashboardData();
    }
  }, [isAuthenticated]);

  if (loading) {
    return (
      <div className="space-y-6 p-6">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <div className="h-8 bg-muted rounded w-48"></div>
            <div className="h-4 bg-muted rounded w-64"></div>
          </div>
          <div className="h-10 bg-muted rounded w-32"></div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <LoadingCard />
          <LoadingCard />
          <LoadingCard />
          <LoadingCard />
        </div>
        <LoadingCard />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-3xl font-bold tracking-tight gradient-text">Dashboard</h1>
          <p className="text-muted-foreground text-lg">Overview of your Zammad-Kimai synchronization</p>
        </div>
        <Button onClick={handleRunSync} className="btn-modern gradient-bg text-primary-foreground hover:shadow-floating">
          <Play className="mr-2 h-4 w-4" />
          Run Sync Now
        </Button>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Connectors"
          value={stats.connectors}
          description="Active connections"
          icon={Database}
          color={stats.connectors === 2 ? "success" : "default"}
        />
        <StatCard
          title="Mappings"
          value={stats.mappings}
          description="Activity mappings"
          icon={Activity}
        />
        <StatCard
          title="Conflicts"
          value={stats.conflicts}
          description="Pending resolutions"
          icon={AlertCircle}
          color={stats.conflicts > 0 ? "warning" : "success"}
        />
        <StatCard
          title="Last Sync"
          value={stats.lastSync || "Never"}
          description="Most recent sync"
          icon={Clock}
        />
      </div>

      {/* Recent Activity */}
      <Card className="card-hover shadow-elevated border-border/50">
        <CardHeader className="pb-4">
          <CardTitle className="flex items-center text-xl">
            <RefreshCw className="mr-2 h-5 w-5 text-primary" />
            Recent Activity
          </CardTitle>
          <CardDescription className="text-base">Last events and syncs</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {recentActivity.map((item, i) => (
              <div key={i} className="flex items-center justify-between p-4 rounded-lg border border-border/50 hover:bg-accent/30 transition-all duration-200 hover-lift">
                <div className="flex items-center space-x-3">
                  <span className={`px-3 py-1.5 rounded-full text-xs font-medium ${
                    item.status === "success" ? "bg-green-100 text-green-800 border border-green-200" : 
                    item.status === "warning" ? "bg-yellow-100 text-yellow-800 border border-yellow-200" : "bg-gray-100 text-gray-800 border border-gray-200"
                  }`}>
                    {item.action}
                  </span>
                  <span className="text-sm text-muted-foreground">{item.time}</span>
                </div>
                <Button variant="ghost" size="sm" className="btn-modern" onClick={handleViewDetails}>
                  View Details
                </Button>
              </div>
            ))}
            {recentActivity.length === 0 && (
              <div className="text-center py-8 text-muted-foreground">
                No recent activity
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
