import React, { createContext, useContext, useEffect, useRef, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import {
  login as loginThunk,
  logout as logoutThunk,
  loggedOut,
  sessionExpired,
  selectIsAuthenticated,
  selectUser,
} from '../store/slices/authSlice'
import { ASSISTANT_STORAGE_KEY, newConversation } from '../store/slices/assistantSlice'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const dispatch = useDispatch()
  const user = useSelector(selectUser)
  const isAuthenticated = useSelector(selectIsAuthenticated)
  const [loading, setLoading] = useState(true)
  const previousUserId = useRef(undefined)

  function clearAssistantSession() {
    try {
      sessionStorage.removeItem(ASSISTANT_STORAGE_KEY)
    } catch {
      // storage can be unavailable; the app still works without it
    }
  }

  // On first load, restore whatever we already had in localStorage so a
  // page refresh doesn't kick the user back to the login page.
  useEffect(() => {
    const storedUser = localStorage.getItem('user')
    const storedToken = localStorage.getItem('access_token')
    if (storedUser && storedToken) {
      try {
        JSON.parse(storedUser)
      } catch {
        localStorage.removeItem('user')
        dispatch(loggedOut())
      }
    } else if (storedUser || storedToken) {
      localStorage.removeItem('user')
      localStorage.removeItem('access_token')
      dispatch(loggedOut())
    }
    setLoading(false)
  }, [dispatch])

  // clear assistant state if a different user appears in the same browser session.
  useEffect(() => {
    const currentUserId = user?.id ?? null
    if (previousUserId.current !== undefined && previousUserId.current !== currentUserId) {
      dispatch(newConversation())
      clearAssistantSession()
    }
    previousUserId.current = currentUserId
  }, [dispatch, user?.id])

  // api.js fires this when the backend rejects our token (401).
  useEffect(() => {
    function handleForcedLogout() {
      dispatch(sessionExpired())
      clearAssistantSession()
    }
    window.addEventListener('auth:logout', handleForcedLogout)
    return () => window.removeEventListener('auth:logout', handleForcedLogout)
  }, [dispatch])

  async function login(email, password) {
    const result = await dispatch(loginThunk({ email, password }))
    if (loginThunk.rejected.match(result)) {
      throw new Error(result.payload || 'Could not log in.')
    }
    return result.payload
  }

  function logout() {
    dispatch(logoutThunk())
    clearAssistantSession()
  }

  const value = {
    user,
    isAuthenticated,
    loading,
    login,
    logout,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return ctx
}
