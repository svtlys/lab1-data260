import React from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'

export default function Home() {
  const { isAuthenticated, user } = useAuth()

  return (
    <div className="page-container">
      <div className="p-5 mb-4 bg-white rounded-3 shadow-sm">
        <h1 className="mb-3 text-gradient">Find your next opportunity.</h1>
        <p className="text-muted mb-4">
          Search jobs, register for events, and build a profile companies can find --
          the Handshake-style platform for Pair 16.
        </p>
        {!isAuthenticated && (
          <div className="d-flex gap-2">
            <Link to="/signup/student" className="btn btn-primary">
              I&apos;m a student
            </Link>
            <Link to="/signup/company" className="btn btn-outline-primary">
              I&apos;m hiring
            </Link>
          </div>
        )}
        {isAuthenticated && (
          <Link to={`/dashboard/${user.role}`} className="btn btn-primary">
            Go to my dashboard
          </Link>
        )}
      </div>
    </div>
  )
}
