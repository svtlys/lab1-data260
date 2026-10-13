import api from './api'

// fetch events using the filters selected by the student
export function searchEvents(filters = {}) {
  const params = Object.fromEntries(
    Object.entries(filters).filter(([, value]) => value !== '' && value !== null),
  )

  return api.get('/api/events', { params }).then((res) => res.data)
}

// register the logged-in student for one event
export function registerForEvent(eventId) {
  return api.post(`/api/events/${eventId}/register`).then((res) => res.data)
}

// fetch the events already registered by the logged-in student
export function getRegisteredEvents() {
  return api.get('/api/events/registered').then((res) => res.data)
}
