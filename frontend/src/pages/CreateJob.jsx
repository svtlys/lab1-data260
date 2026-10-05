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
  category: '',
  location: '',
  salary: '',
  posting_date: todayISO(),
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
    setForm({ ...form, [e.target.name]: e.target.value })
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setSubmitError('')

    const found = validateJob(form)
    setErrors(found)
    if (hasErrors(found)) return

    const payload = cleanPayload(form)
    payload.salary = payload.salary === null ? null : Number(payload.salary)

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
                  label="Category"
                  name="category"
                  as="select"
                  value={form.category}
                  onChange={handleChange}
                  error={errors.category}
                  required
                >
                  <option value="">Choose a category...</option>
                  {JOB_CATEGORIES.map((category) => (
                    <option key={category} value={category}>
                      {category}
                    </option>
                  ))}
                </FormField>
              </div>
              <div className="col-md-6">
                <FormField
                  label="Location"
                  name="location"
                  value={form.location}
                  onChange={handleChange}
                  error={errors.location}
                  required
                  maxLength={150}
                  list="city-suggestions"
                  autoComplete="off"
                />
                <datalist id="city-suggestions">
                  {[...CITY_SET, 'Remote'].map((city) => (
                    <option key={city} value={city} />
                  ))}
                </datalist>
              </div>
            </div>

            <div className="row">
              <div className="col-md-4">
                <FormField
                  label="Salary (USD per year)"
                  name="salary"
                  type="number"
                  min="0"
                  step="1"
                  value={form.salary}
                  onChange={handleChange}
                  error={errors.salary}
                  help="Optional."
                />
              </div>
              <div className="col-md-4">
                <FormField
                  label="Posting date"
                  name="posting_date"
                  type="date"
                  value={form.posting_date}
                  onChange={handleChange}
                  error={errors.posting_date}
                  required
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
                  min={form.posting_date || undefined}
                />
              </div>
            </div>

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
