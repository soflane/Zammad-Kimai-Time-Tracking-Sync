import { useState } from 'react';
import { Outlet, Link, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';

import {
  Home,
  Settings,
  MapPin,
  AlertCircle,
  FileText,
  LogOut,
  ChevronLeft,
  Menu,
  User,
} from 'lucide-react';

export default function Layout() {
  const [isOpen, setIsOpen] = useState(true);
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/login');
  };

  const toggleSidebar = () => {
    setIsOpen(!isOpen);
  };

  const toggleMobileSidebar = () => {
    setIsMobileOpen(!isMobileOpen);
  };

  const menuItems = [
    { path: '/', icon: Home, label: 'Dashboard' },
    { path: '/connectors', icon: Settings, label: 'Connectors' },
    { path: '/mappings', icon: MapPin, label: 'Mappings' },
    { path: '/conflicts', icon: AlertCircle, label: 'Conflicts' },
    { path: '/audit-logs', icon: FileText, label: 'Audit Logs' },
  ];

  return (
    <div className="flex h-screen bg-background">
      {/* Mobile menu button */}
      <Button
        variant="outline"
        size="sm"
        className="fixed top-4 left-4 z-50 lg:hidden shadow-modern"
        onClick={toggleMobileSidebar}
      >
        <Menu className="h-4 w-4" />
      </Button>

      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-40 w-64 transform bg-card border-r shadow-modern lg:translate-x-0 transition-transform duration-200 ease-in-out ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        } ${isMobileOpen ? 'translate-x-0' : ''} lg:relative lg:relative lg:w-64 overflow-y-auto`}
      >
        <div className="flex h-full flex-col">
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b bg-gradient-to-br from-primary/5 to-secondary/5">
            <h1 className="text-xl font-bold text-foreground">Zammad Sync</h1>
            <Button
              variant="ghost"
              size="sm"
              onClick={toggleSidebar}
              className="lg:hidden"
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-2 space-y-2">
            {menuItems.map((item) => {
              const Icon = item.icon;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className="flex items-center w-full px-3 py-2 text-sm font-medium rounded-md hover:bg-accent hover:text-accent-foreground transition-colors hover:shadow-modern"
                >
                  <Icon className="mr-3 h-4 w-4" />
                  {item.label}
                </Link>
              );
            })}
          </nav>

          {/* Footer */}
          <div className="p-2 border-t mt-auto">
            <div className="flex items-center space-x-3 p-2 rounded-md hover:bg-accent hover:text-accent-foreground transition-colors cursor-pointer" onClick={handleLogout}>
              <div className="flex items-center justify-center w-8 h-8 bg-primary/10 rounded-md">
                <User className="h-4 w-4 text-primary" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium">Admin</p>
                <p className="text-xs text-muted-foreground truncate">admin@sync.local</p>
              </div>
              <LogOut className="h-4 w-4" />
            </div>
          </div>
        </div>
      </aside>

      {/* Mobile overlay */}
      {isMobileOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-30 lg:hidden"
          onClick={() => setIsMobileOpen(false)}
        />
      )}

      {/* Main content */}
      <div className={`flex-1 transition-all duration-200 ${isOpen ? 'lg:ml-64' : 'lg:ml-64'}`}>
        <main className="h-full p-6 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
