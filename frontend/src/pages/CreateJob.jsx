import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import * as companyService from '../services/companyService'
import { extractErrorMessage } from '../services/api'
import { JOB_CATEGORIES, CITY_SET } from '../constants'
import { cleanPayload, hasErrors, validateJob } from '../utils/validation'
import { todayISO } from '../utils/format'
import FormField from '../components/FormField.jsx'
import ErrorAlert from '../components/ErrorAlert.jsx'

const emptyJob = () => ({
  title: '',
  employment_type: '',
  city: '',
  is_remote: false,
  salary_min: '',
  salary_max: '',
  required_skills: '',
  deadline: '',
  description: '',
})

export default function CreateJob() {
  const navigate = useNavigate()
  const [form, setForm] = useState(emptyJob)
  const [errors, setErrors] = useState({})
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState('')

  function handleChange(e) {
    const { name, type, checked, value } = e.target
    setForm({ ...form, [name]: type === 'checkbox' ? checked : value })
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setSubmitError('')

    const found = validateJob(form)
    setErrors(found)
    if (hasErrors(found)) return

    const payload = cleanPayload(form)
    ;['salary_min', 'salary_max'].forEach((key) => {
      payload[key] = payload[key] === null ? null : Number(payload[key])
    })
    // The server fills in posted_at and company_id (from the login token).

    setSubmitting(true)
    try {
      await companyService.createJob(payload)
      navigate('/company/jobs', { state: { flash: `"${payload.title}" was posted.` } })
    } catch (err) {
      setSubmitError(extractErrorMessage(err, 'Could not post the job. Please try again.'))
      setSubmitting(false)
    }
  }

  return (
    <div className="page-container" style={{ maxWidth: 720 }}>
      <h2 className="mb-4">Post a job</h2>

      <div className="card shadow-sm">
        <div className="card-body p-4">
          <ErrorAlert message={submitError} />

          <form onSubmit={handleSubmit} noValidate>
            <FormField
              label="Job title"
              name="title"
              value={form.title}
              onChange={handleChange}
              error={errors.title}
              required
              maxLength={150}
            />

            <div className="row">
              <div className="col-md-6">
                <FormField
                  label="Job type"
                  name="employment_type"
                  as="select"
                  value={form.employment_type}
                  onChange={handleChange}
                  error={errors.employment_type}
                  required
                >
                  <option value="">Choose a type...</option>
                  {JOB_CATEGORIES.map((category) => (
                    <option key={category} value={category}>
                      {category}
                    </option>
                  ))}
                </FormField>
              </div>
              <div className="col-md-6">
                <FormField
                  label="City"
                  name="city"
                  as="select"
                  value={form.city}
                  onChange={handleChange}
                  error={errors.city}
                  required
                >
                  <option value="">Choose a city...</option>
                  {CITY_SET.map((city) => (
                    <option key={city} value={city}>
                      {city}
                    </option>
                  ))}
                </FormField>
              </div>
            </div>

            <div className="form-check mb-3">
              <input
                className="form-check-input"
                type="checkbox"
                id="field-is_remote"
                name="is_remote"
                checked={form.is_remote}
                onChange={handleChange}
              />
              <label className="form-check-label" htmlFor="field-is_remote">
                Remote-friendly
              </label>
            </div>

            <div className="row">
              <div className="col-md-4">
                <FormField
                  label="Salary minimum (USD / year)"
                  name="salary_min"
                  type="number"
                  min="0"
                  step="1000"
                  value={form.salary_min}
                  onChange={handleChange}
                  error={errors.salary_min}
                  help="Optional."
                />
              </div>
              <div className="col-md-4">
                <FormField
                  label="Salary maximum (USD / year)"
                  name="salary_max"
                  type="number"
                  min="0"
                  step="1000"
                  value={form.salary_max}
                  onChange={handleChange}
                  error={errors.salary_max}
                  help="Optional."
                />
              </div>
              <div className="col-md-4">
                <FormField
                  label="Application deadline"
                  name="deadline"
                  type="date"
                  value={form.deadline}
                  onChange={handleChange}
                  error={errors.deadline}
                  required
                  min={todayISO()}
                />
              </div>
            </div>

            <FormField
              label="Required skills"
              name="required_skills"
              value={form.required_skills}
              onChange={handleChange}
              error={errors.required_skills}
              help="Comma-separated, e.g. Python, SQL, React."
              maxLength={500}
            />

            <FormField
              label="Description"
              name="description"
              as="textarea"
              rows={6}
              value={form.description}
              onChange={handleChange}
              error={errors.description}
              required
              maxLength={5000}
            />

            <div className="d-flex gap-2">
              <button type="submit" className="btn btn-primary" disabled={submitting}>
                {submitting ? 'Posting...' : 'Post job'}
              </button>
              <Link to="/company/jobs" className="btn btn-outline-secondary">
                Cancel
              </Link>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}
