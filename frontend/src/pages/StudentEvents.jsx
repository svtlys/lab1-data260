import React, { useEffect, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import {
  clearEventFilters,
  fetchEvents,
  fetchRegisteredEvents,
  initialEventFilters,
  registerForEvent,
  selectEvent,
  selectEventFilters,
  selectEvents,
  selectEventsError,
  selectEventsStatus,
  selectRegisteredEventIds,
  selectRegisteringId,
  selectSelectedEvent,
  setEventFilter,
} from '../store/slices/eventsSlice'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import ErrorAlert from '../components/ErrorAlert.jsx'

function formatEventDate(value) {
  return new Date(value).toLocaleString([], {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

export default function StudentEvents() {
  const dispatch = useDispatch()
  const filters = useSelector(selectEventFilters)
  const events = useSelector(selectEvents)
  const selectedEvent = useSelector(selectSelectedEvent)
  const eventsStatus = useSelector(selectEventsStatus)
  const loadError = useSelector(selectEventsError)
  const registeredEventIds = useSelector(selectRegisteredEventIds)
  const registeringId = useSelector(selectRegisteringId)
  const loading = eventsStatus === 'loading' || eventsStatus === 'idle'

  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  useEffect(() => {
    dispatch(fetchEvents(filters))
    dispatch(fetchRegisteredEvents())
  }, [])

  function handleChange(event) {
    dispatch(setEventFilter({ name: event.target.name, value: event.target.value }))
  }

  function handleSubmit(event) {
    event.preventDefault()
    setMessage('')
    dispatch(fetchEvents(filters))
  }

  function clearFilters() {
    dispatch(clearEventFilters())
    setMessage('')
    dispatch(fetchEvents(initialEventFilters))
  }

  async function handleRegister(eventId) {
    setError('')
    setMessage('')

    try {
      await dispatch(registerForEvent(eventId)).unwrap()
      setMessage('You are registered for this event.')
    } catch (err) {
      setError(typeof err === 'string' ? err : 'Could not register for this event.')
    }
  }

  return (
    <div className="page-container">
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h2 className="mb-1">Find events</h2>
          <p className="text-muted mb-0">Discover opportunities in the Pair 16 city set.</p>
        </div>
      </div>

      <ErrorAlert message={error || loadError} />
      {message && <div className="alert alert-success">{message}</div>}

      <div className="card shadow-sm mb-4">
        <div className="card-body">
          <form onSubmit={handleSubmit} className="row g-3">
            <div className="col-md-4">
              <label className="form-label">Search</label>
              <input
                className="form-control"
                name="search"
                value={filters.search}
                onChange={handleChange}
                placeholder="Title, organizer, or description"
              />
            </div>
            <div className="col-md-2">
              <label className="form-label">City</label>
              <select className="form-select" name="city" value={filters.city} onChange={handleChange}>
                <option value="">All cities</option>
                <option value="Sunnyvale">Sunnyvale</option>
                <option value="Cupertino">Cupertino</option>
                <option value="Mountain View">Mountain View</option>
              </select>
            </div>
            <div className="col-md-2">
              <label className="form-label">Type</label>
              <input
                className="form-control"
                name="event_type"
                value={filters.event_type}
                onChange={handleChange}
                placeholder="workshop"
              />
            </div>
            <div className="col-md-2">
              <label className="form-label">Format</label>
              <select
                className="form-select"
                name="is_virtual"
                value={filters.is_virtual}
                onChange={handleChange}
              >
                <option value="">All formats</option>
                <option value="true">Virtual</option>
                <option value="false">In person</option>
              </select>
            </div>
            <div className="col-md-2 d-flex align-items-end gap-2">
              <button type="submit" className="btn btn-primary flex-grow-1">
                Search
              </button>
              <button type="button" className="btn btn-outline-secondary" onClick={clearFilters}>
                Clear
              </button>
            </div>
            <div className="col-md-3">
              <label className="form-label">From</label>
              <input
                type="datetime-local"
                className="form-control"
                name="start_date"
                value={filters.start_date}
                onChange={handleChange}
              />
            </div>
            <div className="col-md-3">
              <label className="form-label">To</label>
              <input
                type="datetime-local"
                className="form-control"
                name="end_date"
                value={filters.end_date}
                onChange={handleChange}
              />
            </div>
          </form>
        </div>
      </div>

      {loading && <LoadingSpinner label="Loading events..." />}

      {!loading && events.length === 0 && (
        <div className="alert alert-info">No events matched your filters.</div>
      )}

      {!loading && events.length > 0 && (
        <div className="row g-4">
          <div className="col-lg-7">
            <div className="row g-3">
              {events.map((event) => (
                <div className="col-md-6" key={event.id}>
                  <div className="card h-100 shadow-sm">
                    <div className="card-body d-flex flex-column">
                      <span className="badge text-bg-light align-self-start mb-2">
                        {event.event_type}
                      </span>
                      <h5 className="card-title">{event.title}</h5>
                      <p className="small text-muted mb-2">{formatEventDate(event.event_date)}</p>
                      <p className="small mb-3">
                        {event.city} · {event.is_virtual ? 'Virtual' : 'In person'}
                      </p>
                      <button
                        type="button"
                        className="btn btn-outline-primary mt-auto"
                        onClick={() => dispatch(selectEvent(event.id))}
                      >
                        View details
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="col-lg-5">
            {selectedEvent && (
              <div className="card shadow-sm sticky-lg-top" style={{ top: '1rem' }}>
                <div className="card-body">
                  <h4>{selectedEvent.title}</h4>
                  <p className="text-muted">organized by {selectedEvent.organizer}</p>
                  <p>{selectedEvent.description}</p>
                  <dl className="row small">
                    <dt className="col-5">When</dt>
                    <dd className="col-7">{formatEventDate(selectedEvent.event_date)}</dd>
                    <dt className="col-5">Where</dt>
                    <dd className="col-7">{selectedEvent.location}</dd>
                    <dt className="col-5">City</dt>
                    <dd className="col-7">{selectedEvent.city}</dd>
                    <dt className="col-5">Capacity</dt>
                    <dd className="col-7">{selectedEvent.capacity || 'Not specified'}</dd>
                  </dl>
                  <button
                    type="button"
                    className="btn btn-primary w-100"
                    disabled={
                      registeredEventIds.includes(selectedEvent.id)
                      || registeringId === selectedEvent.id
                    }
                    onClick={() => handleRegister(selectedEvent.id)}
                  >
                    {registeredEventIds.includes(selectedEvent.id)
                      ? 'Registered'
                      : registeringId === selectedEvent.id
                        ? 'Registering...'
                        : 'Register for event'}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
