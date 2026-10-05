import React, { useState } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'

const GUEST_LINKS = [
  { to: '/login', label: 'Log in' },
  { to: '/signup/student', label: 'Student sign up' },
  { to: '/signup/company', label: 'Company sign up' },
]

const STUDENT_LINKS = [{ to: '/dashboard/student', label: 'Dashboard' }]

const COMPANY_LINKS = [
  { to: '/dashboard/company', label: 'Dashboard' },
  { to: '/company/jobs', label: 'My jobs' },
  { to: '/company/jobs/new', label: 'Post a job' },
  { to: '/company/profile', label: 'Profile' },
]

export default function Navbar() {
  const { isAuthenticated, user, logout } = useAuth()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)

  let links = GUEST_LINKS
  if (isAuthenticated) {
    links = user.role === 'company' ? COMPANY_LINKS : STUDENT_LINKS
  }

  function closeMenu() {
    setOpen(false)
  }

  function handleLogout() {
    closeMenu()
    logout()
    navigate('/login')
  }

  return (
    <nav className="navbar navbar-expand-lg navbar-dark navbar-gradient">
      <div className="container">
        <Link className="navbar-brand" to="/" onClick={closeMenu}>
          Handshake &middot; Pair 16
        </Link>

        {/* Bootstrap's JS isn't loaded, so the toggler is driven by React state. */}
        <button
          className="navbar-toggler"
          type="button"
          aria-label="Toggle navigation"
          aria-expanded={open}
          onClick={() => setOpen(!open)}
        >
          <span className="navbar-toggler-icon" />
        </button>

        <div className={`collapse navbar-collapse justify-content-end${open ? ' show' : ''}`}>
          <ul className="navbar-nav align-items-lg-center gap-lg-2">
            {links.map((link) => (
              <li className="nav-item" key={link.to}>
                <NavLink
                  to={link.to}
                  end
                  onClick={closeMenu}
                  className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
                >
                  {link.label}
                </NavLink>
              </li>
            ))}
            {isAuthenticated && (
              <>
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
