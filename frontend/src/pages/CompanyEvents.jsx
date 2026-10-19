import React, { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import * as companyService from '../services/companyService'
import { extractErrorMessage } from '../services/api'
import { formatDateTime } from '../utils/format'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import ErrorAlert from '../components/ErrorAlert.jsx'
import EmptyState from '../components/EmptyState.jsx'

// Short, human-readable summary of an event's eligibility rules.
export function eligibilitySummary(event) {
  const bits = []
  if (event.eligible_majors) bits.push(event.eligible_majors)
  if (event.min_cgpa !== null && event.min_cgpa !== undefined) bits.push(`CGPA ${Number(event.min_cgpa).toFixed(2)}+`)
  if (event.min_grad_year) bits.push(`class of ${event.min_grad_year}+`)
  if (event.max_grad_year) bits.push(`class of ${event.max_grad_year} or earlier`)
  return bits.length ? bits.join(' · ') : 'Open to everyone'
}

export default function CompanyEvents() {
  const location = useLocation()
  const flash = location.state && location.state.flash
  const [events, setEvents] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    companyService
      .getMyEvents()
      .then((list) => {
        if (!cancelled) setEvents([...list].sort((a, b) => String(b.event_date).localeCompare(String(a.event_date))))
      })
      .catch((err) => {
        if (!cancelled) setError(extractErrorMessage(err, 'Could not load your events.'))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const now = new Date()

  return (
    <div className="page-container">
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h2 className="mb-0">My events</h2>
        <Link to="/company/events/new" className="btn btn-primary">
          Create an event
        </Link>
      </div>

      {flash && <div className="alert alert-success">{flash}</div>}
      {loading && <LoadingSpinner label="Loading your events..." />}
      <ErrorAlert message={error} />

      {!loading && !error && events.length === 0 && (
        <div className="card shadow-sm">
          <EmptyState title="No events yet" message="Create an event and students can register for it.">
            <Link to="/company/events/new" className="btn btn-primary">
              Create an event
            </Link>
          </EmptyState>
        </div>
      )}

      {!loading && !error && events.length > 0 && (
        <div className="card shadow-sm">
          <div className="table-responsive">
            <table className="table table-hover align-middle mb-0">
              <thead>
                <tr>
                  <th>Event</th>
                  <th>When</th>
                  <th>Where</th>
                  <th>Who can attend</th>
                  <th className="text-center">Registered</th>
                </tr>
              </thead>
              <tbody>
                {events.map((event) => {
                  const past = new Date(event.event_date) < now
                  const count = event.registered_count ?? 0
                  return (
                    <tr key={event.id}>
                      <td>
                        <Link to={`/company/events/${event.id}/registrations`} className="fw-semibold">
                          {event.title}
                        </Link>
                        <div className="small text-muted">{event.event_type}</div>
                      </td>
                      <td>
                        {formatDateTime(event.event_date)}
                        {past && <span className="badge bg-light text-dark border ms-2">Past</span>}
                      </td>
                      <td>
                        {event.is_virtual ? 'Online' : event.city}
                      </td>
                      <td className="small">{eligibilitySummary(event)}</td>
                      <td className="text-center">
                        {count}
                        {event.capacity ? ` / ${event.capacity}` : ''}
                        {event.capacity && count >= event.capacity && (
                          <span className="badge bg-warning text-dark ms-2">Full</span>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
