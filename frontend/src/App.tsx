import { Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Layout from '@/components/Layout'
import Dashboard from '@/pages/Dashboard'
import Login from '@/pages/Login'
import Connectors from '@/pages/Connectors'
import ProtectedRoute from '@/components/ProtectedRoute'
import Mappings from '@/pages/Mappings'
import Conflicts from '@/pages/Conflicts'
import AuditLogs from '@/pages/AuditLogs'

const queryClient = new QueryClient()

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route element={<Layout />}>
          <Route 
            path="/" 
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/connectors" 
            element={
              <ProtectedRoute>
                <Connectors />
              </ProtectedRoute>
            }
          />
          <Route 
            path="/mappings" 
            element={
              <ProtectedRoute>
                <Mappings />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/conflicts" 
            element={
              <ProtectedRoute>
                <Conflicts />
              </ProtectedRoute>
            } 
          />
          <Route 
            path="/audit-logs" 
            element={
              <ProtectedRoute>
                <AuditLogs />
              </ProtectedRoute>
            } 
          />
        </Route>
      </Routes>
    </QueryClientProvider>
  )
}

export default App
