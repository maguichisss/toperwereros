import { createContext, useContext, useState, useEffect, useCallback } from 'react'

const API_BASE = '/api'
const STORAGE_KEY = 'store_token'
const REFRESH_KEY = 'store_refresh_token'

const AuthContext = createContext(null)

function parseJwtExp(token) {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    return payload.exp
  } catch {
    return null
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(() => localStorage.getItem(STORAGE_KEY))
  const [refreshToken, setRefreshToken] = useState(() => localStorage.getItem(REFRESH_KEY))
  const [loading, setLoading] = useState(true)

  const storeTokens = useCallback((accessToken, refreshTokenValue) => {
    localStorage.setItem(STORAGE_KEY, accessToken)
    localStorage.setItem(REFRESH_KEY, refreshTokenValue)
    setToken(accessToken)
    setRefreshToken(refreshTokenValue)
  }, [])

  const clearTokens = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY)
    localStorage.removeItem(REFRESH_KEY)
    setToken(null)
    setRefreshToken(null)
    setUser(null)
  }, [])

  const fetchUser = useCallback(async (t) => {
    try {
      const res = await fetch(`${API_BASE}/auth/me`, {
        headers: { Authorization: `Bearer ${t}` },
      })
      if (!res.ok) throw new Error('Unauthorized')
      const data = await res.json()
      setUser(data)
    } catch {
      clearTokens()
    } finally {
      setLoading(false)
    }
  }, [clearTokens])

  const refreshAccessToken = useCallback(async () => {
    const rt = localStorage.getItem(REFRESH_KEY)
    if (!rt) return null
    try {
      const res = await fetch(`${API_BASE}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: rt }),
      })
      if (!res.ok) return null
      const data = await res.json()
      storeTokens(data.access_token, data.refresh_token)
      return data.access_token
    } catch {
      return null
    }
  }, [storeTokens])

  useEffect(() => {
    const init = async () => {
      if (!token) {
        setLoading(false)
        return
      }
      const exp = parseJwtExp(token)
      if (exp && exp * 1000 < Date.now()) {
        const newToken = await refreshAccessToken()
        if (newToken) {
          await fetchUser(newToken)
        } else {
          clearTokens()
          setLoading(false)
        }
      } else {
        await fetchUser(token)
      }
    }
    init()
  }, [])

  const login = async (username, password) => {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    })
    if (!res.ok) {
      const data = await res.json()
      throw new Error(data.detail || 'Error al iniciar sesión')
    }
    const data = await res.json()
    storeTokens(data.access_token, data.refresh_token)
    await fetchUser(data.access_token)
  }

  const logout = async () => {
    const t = localStorage.getItem(STORAGE_KEY)
    if (t) {
      try {
        await fetch(`${API_BASE}/auth/logout`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${t}` },
        })
      } catch { /* ignore */ }
    }
    clearTokens()
  }

  const refreshUser = useCallback(async () => {
    if (token) await fetchUser(token)
  }, [token, fetchUser])

  const can = (permission) => {
    if (!user) return false
    if (user.role_name === 'admin') return true
    if (user.role_name === 'viewer') {
      const viewOnly = ['product.view', 'sale.view', 'apartado.view', 'customer.view', 'category.view', 'color.view']
      return viewOnly.includes(permission)
    }
    if (user.role_name === 'employee') {
      const employeePerms = [
        'product.view', 'product.create', 'product.edit', 'product.delete',
        'sale.view', 'sale.create',
        'apartado.view', 'apartado.create', 'apartado.edit',
        'customer.view', 'customer.create', 'customer.edit', 'customer.delete',
        'category.view', 'color.view',
      ]
      return employeePerms.includes(permission)
    }
    return false
  }

  return (
    <AuthContext.Provider value={{ user, login, logout, refreshUser, can, loading }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
