import React, { useEffect } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import {
  fetchRegisteredEvents,
  selectRegisteredError,
  selectRegisteredEvents,
  selectRegisteredStatus,
} from '../store/slices/eventsSlice'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import ErrorAlert from '../components/ErrorAlert.jsx'

function formatEventDate(value) {
  return new Date(value).toLocaleString([], {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

export default function StudentRegisteredEvents() {
  const dispatch = useDispatch()
  const events = useSelector(selectRegisteredEvents)
  const status = useSelector(selectRegisteredStatus)
  const error = useSelector(selectRegisteredError) || ''
  const loading = status === 'idle' || (status === 'loading' && events.length === 0)

  useEffect(() => {
    dispatch(fetchRegisteredEvents())
  }, [dispatch])

  return (
    <div className="page-container">
      <h2 className="mb-1">My registered events</h2>
      <p className="text-muted mb-4">Keep track of the opportunities you plan to attend.</p>

      <ErrorAlert message={error} />
      {loading && <LoadingSpinner label="Loading your registered events..." />}

      {!loading && !error && events.length === 0 && (
        <div className="alert alert-info">
          You have not registered for any events yet. Visit the Events page to find one.
        </div>
      )}

      {!loading && events.length > 0 && (
        <div className="row g-4">
          {events.map((event) => (
            <div className="col-md-6 col-lg-4" key={event.id}>
              <div className="card h-100 shadow-sm">
                <div className="card-body">
                  <span className="badge text-bg-success mb-2">Registered</span>
                  <h5 className="card-title">{event.title}</h5>
                  <p className="small text-muted">{event.event_type}</p>
                  <p className="mb-2">{event.description}</p>
                  <dl className="row small mb-0">
                    <dt className="col-4">When</dt>
                    <dd className="col-8">{formatEventDate(event.event_date)}</dd>
                    <dt className="col-4">Where</dt>
                    <dd className="col-8">{event.location}</dd>
                    <dt className="col-4">City</dt>
                    <dd className="col-8">{event.city}</dd>
                  </dl>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
