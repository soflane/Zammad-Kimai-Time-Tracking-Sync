import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { authService } from '@/services/api.service'
interface AuthContextType {
  user: any | null
  token: string | null
  login: (username: string, password: string) => Promise<void>
  logout: () => void
  isAuthenticated: boolean
  loading: boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<any | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const savedToken = localStorage.getItem('token')
    if (savedToken) {
      setToken(savedToken)
      // Verify token by fetching user info
      authService.getCurrentUser()
        .then(userData => {
          setUser(userData)
        })
        .catch((error) => {
          // Only logout if we got a real auth error, not network issues
          if (error.response?.status === 401) {
            logout()
          } else {
            // For other errors, keep the token but log the error
            console.error('Failed to verify token:', error)
          }
        })
        .finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [])

  const login = async (username: string, password: string) => {
    try {
      const loginData = await authService.login({ username, password })
      localStorage.setItem('token', loginData.access_token)
      setToken(loginData.access_token)
      // Get user info after login
      const userData = await authService.getCurrentUser()
      setUser(userData)
    } catch (error) {
      // If login or user fetch fails, clean up
      localStorage.removeItem('token')
      setToken(null)
      setUser(null)
      throw error
    }
  }
  const logout = () => {
    localStorage.removeItem('token')
    setToken(null)
    setUser(null)
    // Clear API interceptor cache if needed
  }

  const value = {
    user,
    token,
    login,
    logout,
    isAuthenticated: !!token && !!user,
    loading
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
