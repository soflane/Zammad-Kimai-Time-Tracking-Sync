import { Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Login from '@/pages/Login'
import SyncDashboard from '@/pages/SyncDashboard'
import ProtectedRoute from '@/components/ProtectedRoute'

// Legacy imports kept for potential fallback (can be removed later)
// import Layout from '@/components/Layout'
// import Dashboard from '@/pages/Dashboard'
// import Connectors from '@/pages/Connectors'
// import Mappings from '@/pages/Mappings'
// import Conflicts from '@/pages/Conflicts'
// import AuditLogs from '@/pages/AuditLogs'

const queryClient = new QueryClient()

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route 
          path="/" 
          element={
            <ProtectedRoute>
              <SyncDashboard />
            </ProtectedRoute>
          } 
        />
        {/* Legacy routes commented out - single-page dashboard replaces all 
        <Route element={<Layout />}>
          <Route path="/connectors" element={<ProtectedRoute><Connectors /></ProtectedRoute>} />
          <Route path="/mappings" element={<ProtectedRoute><Mappings /></ProtectedRoute>} />
          <Route path="/conflicts" element={<ProtectedRoute><Conflicts /></ProtectedRoute>} />
          <Route path="/audit-logs" element={<ProtectedRoute><AuditLogs /></ProtectedRoute>} />
        </Route>
        */}
      </Routes>
    </QueryClientProvider>
  )
}

export default App
