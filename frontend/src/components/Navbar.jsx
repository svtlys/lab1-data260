import React from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'

export default function Navbar() {
  const { isAuthenticated, user, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
      <nav className="navbar navbar-expand-lg navbar-dark navbar-gradient">
      <div className="container">
        <Link className="navbar-brand" to="/">
          Handshake &middot; Pair 16
        </Link>
        <div className="collapse navbar-collapse justify-content-end">
          <ul className="navbar-nav align-items-lg-center gap-lg-2">
            {!isAuthenticated && (
              <>
                <li className="nav-item">
                  <Link className="nav-link" to="/login">
                    Log in
                  </Link>
                </li>
                <li className="nav-item">
                  <Link className="nav-link" to="/signup/student">
                    Student sign up
                  </Link>
                </li>
                <li className="nav-item">
                  <Link className="nav-link" to="/signup/company">
                    Company sign up
                  </Link>
                </li>
              </>
            )}
            {isAuthenticated && (
              <>
                <li className="nav-item">
                  <Link className="nav-link" to={`/dashboard/${user.role}`}>
                    Dashboard
                  </Link>
                </li>
                <li className="nav-item">
                  <span className="nav-link text-white-50">{user.email}</span>
                </li>
                <li className="nav-item">
                  <button className="btn btn-outline-light btn-sm" onClick={handleLogout}>
                    Log out
                  </button>
                </li>
              </>
            )}
          </ul>
        </div>
      </div>
    </nav>
  )
}
