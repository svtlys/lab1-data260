import React, { useEffect, useState } from 'react'
import * as companyService from '../services/companyService'
import { useAuth } from '../context/AuthContext.jsx'
import { extractErrorMessage } from '../services/api'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import ErrorAlert from '../components/ErrorAlert.jsx'

const emptyProfile = {
  company_name: '',
  location: '',
  description: '',
  contact_info: '',
}

export default function CompanyDashboard() {
  const { user } = useAuth()
  const [form, setForm] = useState(emptyProfile)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [endpointMissing, setEndpointMissing] = useState(false)
  const [saveMessage, setSaveMessage] = useState('')

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError('')
    companyService
      .getMyCompanyProfile()
      .then((data) => {
        if (cancelled) return
        setForm({ ...emptyProfile, ...data })
      })
      .catch((err) => {
        if (cancelled) return
        if (err.response && err.response.status === 404) {
          // The backend doesn't have this route yet -- expected until
          // your partner adds GET/PUT /api/companies/me.
          setEndpointMissing(true)
        } else {
          setError(extractErrorMessage(err, 'Could not load your company profile.'))
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  function handleChange(e) {
    setForm({ ...form, [e.target.name]: e.target.value })
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setSaving(true)
    setError('')
    setSaveMessage('')
    try {
      await companyService.updateMyCompanyProfile(form)
      setSaveMessage('Profile saved.')
    } catch (err) {
      setError(extractErrorMessage(err, 'Could not save your company profile.'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="page-container">
      <h2 className="mb-4">Company dashboard</h2>
      <p className="text-muted">Signed in as {user?.email}</p>

      {loading && <LoadingSpinner label="Loading your company profile..." />}
      <ErrorAlert message={error} />

      {endpointMissing && !loading && (
        <div className="alert alert-warning">
          The backend doesn&apos;t expose <code>/api/companies/me</code> yet, so this form can&apos;t
          load or save real data yet -- it&apos;s built and ready for as soon as that endpoint exists.
        </div>
      )}

      {!loading && (
        <div className="card shadow-sm">
          <div className="card-body p-4">
            {saveMessage && <div className="alert alert-success">{saveMessage}</div>}
            <form onSubmit={handleSubmit} className="row g-3">
              <div className="col-md-6">
                <label className="form-label">Company name</label>
                <input
                  className="form-control"
                  name="company_name"
                  value={form.company_name || ''}
                  onChange={handleChange}
                />
              </div>
              <div className="col-md-6">
                <label className="form-label">Location</label>
                <input
                  className="form-control"
                  name="location"
                  value={form.location || ''}
                  onChange={handleChange}
                />
              </div>
              <div className="col-12">
                <label className="form-label">Description</label>
                <textarea
                  className="form-control"
                  name="description"
                  rows={3}
                  value={form.description || ''}
                  onChange={handleChange}
                />
              </div>
              <div className="col-12">
                <label className="form-label">Contact information</label>
                <input
                  className="form-control"
                  name="contact_info"
                  value={form.contact_info || ''}
                  onChange={handleChange}
                />
              </div>
              <div className="col-12">
                <button type="submit" className="btn btn-primary" disabled={saving}>
                  {saving ? 'Saving...' : 'Save profile'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
