import React, { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import * as companyService from '../services/companyService'
import { extractErrorMessage } from '../services/api'
import { formatDateTime } from '../utils/format'
import { eligibilitySummary } from './CompanyEvents.jsx'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import ErrorAlert from '../components/ErrorAlert.jsx'
import EmptyState from '../components/EmptyState.jsx'

export default function EventRegistrations() {
  const { eventId } = useParams()
  const [event, setEvent] = useState(null)
  const [students, setStudents] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [onlyIssues, setOnlyIssues] = useState(false)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError('')
    Promise.all([companyService.getMyEvent(eventId), companyService.getEventRegistrations(eventId)])
      .then(([ev, list]) => {
        if (cancelled) return
        setEvent(ev)
        setStudents(list)
      })
      .catch((err) => {
        if (!cancelled) setError(extractErrorMessage(err, 'Could not load this event.'))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [eventId])

  const ineligible = students.filter((s) => s.eligible === false)
  const shown = onlyIssues ? ineligible : students

  return (
    <div className="page-container">
      <Link to="/company/events" className="small">
        &larr; Back to my events
      </Link>

      {loading && <LoadingSpinner label="Loading registrations..." />}
      <ErrorAlert message={error} />

      {event && (
        <>
          <div className="mt-2 mb-4">
            <h2 className="mb-1">{event.title}</h2>
            <div className="text-muted">
              {event.event_type} &middot; {formatDateTime(event.event_date)} &middot;{' '}
              {event.is_virtual ? 'Online' : event.location || event.city}
            </div>
            <div className="small mt-1">
              <strong>Who can attend:</strong> {eligibilitySummary(event)}
            </div>
          </div>

          <div className="row g-3 mb-4">
            <div className="col-6 col-md-3">
              <div className="card shadow-sm h-100">
                <div className="card-body">
                  <div className="text-muted small">Registered</div>
                  <div className="fs-3 fw-semibold">
                    {students.length}
                    {event.capacity ? <span className="fs-6 text-muted"> / {event.capacity}</span> : null}
                  </div>
                </div>
              </div>
            </div>
            <div className="col-6 col-md-3">
              <div className="card shadow-sm h-100">
                <div className="card-body">
                  <div className="text-muted small">Not eligible</div>
                  <div className={`fs-3 fw-semibold ${ineligible.length ? 'text-danger' : ''}`}>
                    {ineligible.length}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {students.length === 0 ? (
            <div className="card shadow-sm">
              <EmptyState title="No registrations yet" message="Students who register will appear here." />
            </div>
          ) : (
            <div className="card shadow-sm">
              <div className="card-body pb-0 d-flex justify-content-between align-items-center">
                <h5 className="mb-0">Registered students</h5>
                {ineligible.length > 0 && (
                  <div className="form-check form-switch mb-0">
                    <input
                      className="form-check-input"
                      type="checkbox"
                      id="only-issues"
                      checked={onlyIssues}
                      onChange={(e) => setOnlyIssues(e.target.checked)}
                    />
                    <label className="form-check-label small" htmlFor="only-issues">
                      Show only students who don&apos;t meet the requirements
                    </label>
                  </div>
                )}
              </div>
              <div className="table-responsive mt-3">
                <table className="table table-hover align-middle mb-0">
                  <thead>
                    <tr>
                      <th>Student</th>
                      <th>Major</th>
                      <th className="text-center">CGPA</th>
                      <th className="text-center">Grad year</th>
                      <th>Registered</th>
                      <th>Eligibility</th>
                    </tr>
                  </thead>
                  <tbody>
                    {shown.map((s) => (
                      <tr key={s.student_id}>
                        <td>
                          <Link to={`/company/students/${s.student_id}`} className="fw-semibold">
                            {s.student_name}
                          </Link>
                          <div className="small text-muted">{s.college_name}</div>
                        </td>
                        <td>{s.major || '—'}</td>
                        <td className="text-center">{s.cgpa ?? '—'}</td>
                        <td className="text-center">{s.graduation_year ?? '—'}</td>
                        <td className="small">{formatDateTime(s.registered_at)}</td>
                        <td>
                          {s.eligible === false ? (
                            <>
                              <span className="badge bg-danger">Not eligible</span>
                              <div className="small text-muted mt-1">
                                {(s.ineligible_reasons || []).join('; ')}
                              </div>
                            </>
                          ) : (
                            <span className="badge bg-success">Eligible</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
