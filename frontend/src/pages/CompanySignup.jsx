import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import * as authService from '../services/authService'
import { extractErrorMessage } from '../services/api'
import ErrorAlert from '../components/ErrorAlert.jsx'

const initialForm = {
  company_name: '',
  email: '',
  password: '',
  location: '',
}

export default function CompanySignup() {
  const navigate = useNavigate()
  const [form, setForm] = useState(initialForm)
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
      await authService.signupCompany(form)
      navigate('/login', { state: { justSignedUp: true } })
    } catch (err) {
      setError(extractErrorMessage(err, 'Could not create your company account. Please try again.'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page-container">
      <div className="card form-card shadow-sm">
        <div className="card-body p-4">
          <h2 className="mb-4">Company sign up</h2>
          <ErrorAlert message={error} />
          <form onSubmit={handleSubmit}>
            <div className="mb-3">
              <label className="form-label">Company name</label>
              <input
                type="text"
                name="company_name"
                className="form-control"
                value={form.company_name}
                onChange={handleChange}
                required
              />
            </div>
            <div className="mb-3">
              <label className="form-label">Location</label>
              <input
                type="text"
                name="location"
                className="form-control"
                value={form.location}
                onChange={handleChange}
                required
              />
            </div>
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
              {loading ? 'Creating account...' : 'Create account'}
            </button>
          </form>
          <p className="text-center text-muted mt-3 mb-0">
            Already have an account? <Link to="/login">Log in</Link>
          </p>
        </div>
      </div>
    </div>
  )
}
