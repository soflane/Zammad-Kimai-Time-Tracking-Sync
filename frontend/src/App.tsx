import { Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Login from '@/pages/Login'
import SyncDashboard from '@/pages/SyncDashboard'
import ProtectedRoute from '@/components/ProtectedRoute'


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
      </Routes>
    </QueryClientProvider>
  )
}

export default App
