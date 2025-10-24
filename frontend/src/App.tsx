import { Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from '@/components/ui/toaster'
import Layout from '@/components/Layout' // Placeholder
import Dashboard from '@/pages/Dashboard'
import Login from '@/pages/Login'

// Placeholder components for now
const Connectors = () => <div className="p-4">Connectors Page Placeholder</div>
const Mappings = () => <div className="p-4">Mappings Page Placeholder</div>
const Conflicts = () => <div className="p-4">Conflicts Page Placeholder</div>
const AuditLogs = () => <div className="p-4">Audit Logs Page Placeholder</div>

const queryClient = new QueryClient()

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route element={<Layout />} >
          <Route path="/" element={<Dashboard />} />
          <Route path="/connectors" element={<Connectors />} />
          <Route path="/mappings" element={<Mappings />} />
          <Route path="/conflicts" element={<Conflicts />} />
          <Route path="/audit-logs" element={<AuditLogs />} />
        </Route>
      </Routes>
      <Toaster />
    </QueryClientProvider>
  )
}

export default App
