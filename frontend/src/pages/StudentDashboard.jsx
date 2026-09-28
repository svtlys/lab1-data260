import React, { useEffect, useState } from 'react'
import * as studentService from '../services/studentService'
import { extractErrorMessage } from '../services/api'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import ErrorAlert from '../components/ErrorAlert.jsx'

const emptyProfile = {
  full_name: '',
  college_name: '',
  career_objective: '',
  city: '',
  state: '',
  country: '',
  degree: '',
  major: '',
  graduation_year: '',
  cgpa: '',
  experience: '',
  skills: '',
  phone: '',
}

export default function StudentDashboard() {
  const [profile, setProfile] = useState(null)
  const [form, setForm] = useState(emptyProfile)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [saveMessage, setSaveMessage] = useState('')

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError('')
    studentService
      .getMyStudentProfile()
      .then((data) => {
        if (cancelled) return
        setProfile(data)
        setForm({ ...emptyProfile, ...data })
      })
      .catch((err) => {
        if (!cancelled) setError(extractErrorMessage(err, 'Could not load your profile.'))
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
      const updated = await studentService.updateMyStudentProfile(form)
      setProfile(updated)
      setSaveMessage('Profile saved.')
    } catch (err) {
      setError(extractErrorMessage(err, 'Could not save your profile.'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="page-container">
      <h2 className="mb-4">
        {profile?.full_name ? `Welcome, ${profile.full_name}` : 'Student dashboard'}
      </h2>

      {loading && <LoadingSpinner label="Loading your profile..." />}
      <ErrorAlert message={error} />

      {!loading && (
        <div className="card shadow-sm">
          <div className="card-body p-4">
            {saveMessage && <div className="alert alert-success">{saveMessage}</div>}
            <form onSubmit={handleSubmit} className="row g-3">
              <div className="col-md-6">
                <label className="form-label">Full name</label>
                <input
                  className="form-control"
                  name="full_name"
                  value={form.full_name || ''}
                  onChange={handleChange}
                />
              </div>
              <div className="col-md-6">
                <label className="form-label">College</label>
                <input
                  className="form-control"
                  name="college_name"
                  value={form.college_name || ''}
                  onChange={handleChange}
                />
              </div>
              <div className="col-12">
                <label className="form-label">Career objective</label>
                <textarea
                  className="form-control"
                  name="career_objective"
                  rows={2}
                  value={form.career_objective || ''}
                  onChange={handleChange}
                />
              </div>
              <div className="col-md-4">
                <label className="form-label">City</label>
                <input
                  className="form-control"
                  name="city"
                  value={form.city || ''}
                  onChange={handleChange}
                />
              </div>
              <div className="col-md-4">
                <label className="form-label">State</label>
                <input
                  className="form-control"
                  name="state"
                  value={form.state || ''}
                  onChange={handleChange}
                />
              </div>
              <div className="col-md-4">
                <label className="form-label">Country</label>
                <input
                  className="form-control"
                  name="country"
                  value={form.country || ''}
                  onChange={handleChange}
                />
              </div>
              <div className="col-md-6">
                <label className="form-label">Degree</label>
                <input
                  className="form-control"
                  name="degree"
                  value={form.degree || ''}
                  onChange={handleChange}
                />
              </div>
              <div className="col-md-6">
                <label className="form-label">Major</label>
                <input
                  className="form-control"
                  name="major"
                  value={form.major || ''}
                  onChange={handleChange}
                />
              </div>
              <div className="col-md-6">
                <label className="form-label">Graduation year</label>
                <input
                  type="number"
                  className="form-control"
                  name="graduation_year"
                  value={form.graduation_year || ''}
                  onChange={handleChange}
                />
              </div>
              <div className="col-md-6">
                <label className="form-label">CGPA</label>
                <input
                  type="number"
                  step="0.01"
                  className="form-control"
                  name="cgpa"
                  value={form.cgpa || ''}
                  onChange={handleChange}
                />
              </div>
              <div className="col-12">
                <label className="form-label">Experience</label>
                <textarea
                  className="form-control"
                  name="experience"
                  rows={2}
                  value={form.experience || ''}
                  onChange={handleChange}
                />
              </div>
              <div className="col-md-8">
                <label className="form-label">Skills</label>
                <input
                  className="form-control"
                  name="skills"
                  value={form.skills || ''}
                  onChange={handleChange}
                  placeholder="Python, FastAPI, MySQL, React"
                />
              </div>
              <div className="col-md-4">
                <label className="form-label">Phone</label>
                <input
                  className="form-control"
                  name="phone"
                  value={form.phone || ''}
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
