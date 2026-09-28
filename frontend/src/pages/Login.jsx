import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { extractErrorMessage } from '../services/api'
import ErrorAlert from '../components/ErrorAlert.jsx'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ email: '', password: '' })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  function handleChange(e) {
    setForm({ ...form, [e.target.name]: e.target.value })
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const user = await login(form.email, form.password)
      navigate(`/dashboard/${user.role}`)
    } catch (err) {
      setError(extractErrorMessage(err, 'Could not log in. Check your email and password.'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page-container">
      <div className="card form-card shadow-sm">
        <div className="card-body p-4">
          <h2 className="mb-4">Log in</h2>
          <ErrorAlert message={error} />
          <form onSubmit={handleSubmit}>
            <div className="mb-3">
              <label className="form-label">Email</label>
              <input
                type="email"
                name="email"
                className="form-control"
                value={form.email}
                onChange={handleChange}
                required
              />
            </div>
            <div className="mb-3">
              <label className="form-label">Password</label>
              <input
                type="password"
                name="password"
                className="form-control"
                value={form.password}
                onChange={handleChange}
                required
              />
            </div>
            <button type="submit" className="btn btn-primary w-100" disabled={loading}>
              {loading ? 'Logging in...' : 'Log in'}
            </button>
          </form>
          <p className="text-center text-muted mt-3 mb-0">
            New here?{' '}
            <Link to="/signup/student">Sign up as a student</Link> or{' '}
            <Link to="/signup/company">as a company</Link>.
          </p>
        </div>
      </div>
    </div>
  )
}
