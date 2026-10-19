import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import * as companyService from '../services/companyService'
import { extractErrorMessage } from '../services/api'
import { EVENT_TYPES, CITY_SET, MAJORS } from '../constants'
import { cleanPayload, hasErrors, validateEvent } from '../utils/validation'
import FormField from '../components/FormField.jsx'
import ErrorAlert from '../components/ErrorAlert.jsx'

const emptyEvent = () => ({
  title: '',
  event_type: '',
  city: '',
  is_virtual: false,
  location: '',
  event_date: '',
  capacity: '',
  description: '',
  eligible_majors: [],
  min_cgpa: '',
  min_grad_year: '',
  max_grad_year: '',
})

// "2026-10-20T15:00" (what <input type="datetime-local"> gives) -> "2026-10-20T15:00:00"
const withSeconds = (value) => (value.length === 16 ? `${value}:00` : value)

export default function CreateEvent() {
  const navigate = useNavigate()
  const [form, setForm] = useState(emptyEvent)
  const [errors, setErrors] = useState({})
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState('')

  function handleChange(e) {
    const { name, type, checked, value } = e.target
    setForm({ ...form, [name]: type === 'checkbox' ? checked : value })
  }

  function toggleMajor(major) {
    const has = form.eligible_majors.includes(major)
    setForm({
      ...form,
      eligible_majors: has ? form.eligible_majors.filter((m) => m !== major) : [...form.eligible_majors, major],
    })
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setSubmitError('')

    const found = validateEvent(form)
    setErrors(found)
    if (hasErrors(found)) return

    const payload = cleanPayload({
      ...form,
      eligible_majors: form.eligible_majors.join(', '),
      event_date: withSeconds(form.event_date),
      location: form.is_virtual ? 'Online' : form.location,
    })
    payload.capacity = Number(payload.capacity)
    // The backend accepts text here, never null, so a blank description is sent as ''.
    payload.description = payload.description ?? ''
    ;['min_cgpa', 'min_grad_year', 'max_grad_year'].forEach((key) => {
      payload[key] = payload[key] === null ? null : Number(payload[key])
    })
    // The server fills in company_id and organizer from the login token.

    setSubmitting(true)
    try {
      await companyService.createEvent(payload)
      navigate('/company/events', { state: { flash: `"${payload.title}" was created.` } })
    } catch (err) {
      setSubmitError(extractErrorMessage(err, 'Could not create the event. Please try again.'))
      setSubmitting(false)
    }
  }

  return (
    <div className="page-container" style={{ maxWidth: 760 }}>
      <h2 className="mb-4">Create an event</h2>

      <div className="card shadow-sm">
        <div className="card-body p-4">
          <ErrorAlert message={submitError} />

          <form onSubmit={handleSubmit} noValidate>
            <FormField
              label="Event title"
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
                  label="Event type"
                  name="event_type"
                  as="select"
                  value={form.event_type}
                  onChange={handleChange}
                  error={errors.event_type}
                  required
                >
                  <option value="">Choose a type...</option>
                  {EVENT_TYPES.map((type) => (
                    <option key={type} value={type}>
                      {type}
                    </option>
                  ))}
                </FormField>
              </div>
              <div className="col-md-6">
                <FormField
                  label="Date and time"
                  name="event_date"
                  type="datetime-local"
                  value={form.event_date}
                  onChange={handleChange}
                  error={errors.event_date}
                  required
                />
              </div>
            </div>

            <div className="row">
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
              <div className="col-md-6">
                <FormField
                  label="Capacity"
                  name="capacity"
                  type="number"
                  min="1"
                  step="1"
                  value={form.capacity}
                  onChange={handleChange}
                  error={errors.capacity}
                  required
                  help="Registration closes when this many students have signed up."
                />
              </div>
            </div>

            <div className="form-check mb-3">
              <input
                className="form-check-input"
                type="checkbox"
                id="field-is_virtual"
                name="is_virtual"
                checked={form.is_virtual}
                onChange={handleChange}
              />
              <label className="form-check-label" htmlFor="field-is_virtual">
                Online event
              </label>
            </div>

            {!form.is_virtual && (
              <FormField
                label="Venue"
                name="location"
                value={form.location}
                onChange={handleChange}
                error={errors.location}
                required
                maxLength={150}
                help="Building or address."
              />
            )}

            <FormField
              label="Description"
              name="description"
              as="textarea"
              rows={4}
              value={form.description}
              onChange={handleChange}
              error={errors.description}
              maxLength={5000}
            />

            <hr className="my-4" />
            <h5 className="mb-1">Who can register?</h5>
            <p className="text-muted small">
              Leave everything blank to open the event to all students. Students who don&apos;t
              meet a requirement will be told why when they try to register.
            </p>

            <div className="mb-3">
              <div className="form-label">Majors</div>
              <div className="row row-cols-1 row-cols-sm-2 g-1">
                {MAJORS.map((major) => (
                  <div className="col" key={major}>
                    <div className="form-check">
                      <input
                        className="form-check-input"
                        type="checkbox"
                        id={`major-${major}`}
                        checked={form.eligible_majors.includes(major)}
                        onChange={() => toggleMajor(major)}
                      />
                      <label className="form-check-label" htmlFor={`major-${major}`}>
                        {major}
                      </label>
                    </div>
                  </div>
                ))}
              </div>
              <div className="form-text">Tick none for &quot;all majors&quot;.</div>
            </div>

            <div className="row">
              <div className="col-md-4">
                <FormField
                  label="Minimum CGPA"
                  name="min_cgpa"
                  type="number"
                  min="0"
                  max="4"
                  step="0.01"
                  value={form.min_cgpa}
                  onChange={handleChange}
                  error={errors.min_cgpa}
                />
              </div>
              <div className="col-md-4">
                <FormField
                  label="Earliest graduation year"
                  name="min_grad_year"
                  type="number"
                  value={form.min_grad_year}
                  onChange={handleChange}
                  error={errors.min_grad_year}
                />
              </div>
              <div className="col-md-4">
                <FormField
                  label="Latest graduation year"
                  name="max_grad_year"
                  type="number"
                  value={form.max_grad_year}
                  onChange={handleChange}
                  error={errors.max_grad_year}
                />
              </div>
            </div>

            <div className="d-flex gap-2">
              <button type="submit" className="btn btn-primary" disabled={submitting}>
                {submitting ? 'Creating...' : 'Create event'}
              </button>
              <Link to="/company/events" className="btn btn-outline-secondary">
                Cancel
              </Link>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}
