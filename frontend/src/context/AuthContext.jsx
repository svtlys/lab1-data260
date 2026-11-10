import React, { useEffect } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import {
  login as loginThunk,
  logout as logoutThunk,
  sessionExpired,
  selectIsAuthenticated,
  selectUser,
} from '../store/slices/authSlice'

// Auth state now lives in the Redux "auth" slice. This file keeps the old
// AuthProvider/useAuth names so existing pages (Navbar, Login, ProtectedRoute,
// Home) keep working unchanged.

export function AuthProvider({ children }) {
  const dispatch = useDispatch()

  // api.js fires this when the backend rejects our token (401).
  useEffect(() => {
    function handleForcedLogout() {
      dispatch(sessionExpired())
    }
    window.addEventListener('auth:logout', handleForcedLogout)
    return () => window.removeEventListener('auth:logout', handleForcedLogout)
  }, [dispatch])

  return <>{children}</>
}

export function useAuth() {
  const dispatch = useDispatch()
  const user = useSelector(selectUser)
  const isAuthenticated = useSelector(selectIsAuthenticated)

  async function login(email, password) {
    const result = await dispatch(loginThunk({ email, password }))
    if (loginThunk.rejected.match(result)) {
      throw new Error(result.payload || 'Could not log in.')
    }
    return result.payload
  }

  function logout() {
    dispatch(logoutThunk())
  }

  // the session is restored synchronously from localStorage, so there is no loading phase
  return { user, isAuthenticated, loading: false, login, logout }
}
