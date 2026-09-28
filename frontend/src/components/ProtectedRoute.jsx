import React from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'

// Wrap a page with <ProtectedRoute role="student">...</ProtectedRoute> to
// require login, and optionally a specific role. A logged-in user hitting
// the wrong role's route gets sent to their own dashboard instead of a dead end.
export default function ProtectedRoute({ role, children }) {
  const { isAuthenticated, user, loading } = useAuth()

  if (loading) {
    return null
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  if (role && user.role !== role) {
    return <Navigate to={`/dashboard/${user.role}`} replace />
  }

  return children
}
