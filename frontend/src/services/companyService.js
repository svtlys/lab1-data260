import api from './api'

// Every call here is part of the PROPOSED company API in
// docs/company-api-contract.md. The backend currently only has auth and
// student-profile routes, so these paths need to be confirmed with your partner.
// If a path or field name changes, this is the only file that needs to change.

const toList = (data) => (Array.isArray(data) ? data : (data && data.items) || [])
const seg = (value) => encodeURIComponent(value)

// ---- Company profile ----

export function getMyCompanyProfile() {
  return api.get('/api/companies/me').then((res) => res.data)
}

export function updateMyCompanyProfile(payload) {
  return api.put('/api/companies/me', payload).then((res) => res.data)
}

export function uploadCompanyProfilePicture(file) {
  const formData = new FormData()
  formData.append('image', file)
  return api
    .post('/api/companies/me/profile-picture', formData)
    .then((res) => res.data)
}

// ---- Job postings (owned by the logged-in company) ----

export function createJob(payload) {
  return api.post('/api/companies/me/jobs', payload).then((res) => res.data)
}

export function getMyJobs() {
  return api.get('/api/companies/me/jobs').then((res) => toList(res.data))
}

// ---- Applicants ----

export function getJobApplications(jobId) {
  return api
    .get(`/api/companies/me/jobs/${seg(jobId)}/applications`)
    .then((res) => toList(res.data))
}

export function updateApplicationStatus(applicationId, status) {
  return api
    .put(`/api/companies/me/applications/${seg(applicationId)}/status`, { status })
    .then((res) => res.data)
}

// Returns the PDF as a Blob. It has to go through axios (not a plain link)
// because the endpoint needs the Authorization header.
export function getApplicationResume(applicationId) {
  return api
    .get(`/api/companies/me/applications/${seg(applicationId)}/resume`, { responseType: 'blob' })
    .then((res) => res.data)
}

// ---- Student profiles (read-only for companies) ----

export function getApplicantProfile(studentId) {
  return api.get(`/api/students/${seg(studentId)}`).then((res) => res.data)
}

export function searchStudents(filters = {}) {
  const params = Object.fromEntries(
    Object.entries(filters).filter(([, value]) => value !== null && value !== undefined && String(value).trim() !== ''),
  )
  return api.get('/api/companies/students/search', { params }).then((res) => toList(res.data))
}

// ---- Events (Week 3) ----

export function createEvent(payload) {
  return api.post('/api/companies/me/events', payload).then((res) => res.data)
}

export function getMyEvents() {
  return api.get('/api/companies/me/events').then((res) => toList(res.data))
}

export function getMyEvent(eventId) {
  return api.get(`/api/companies/me/events/${seg(eventId)}`).then((res) => res.data)
}

// Students registered for one of this company's events, each with an
// eligibility verdict: { eligible: boolean, ineligible_reasons: string[] }.
export function getEventRegistrations(eventId) {
  return api
    .get(`/api/companies/me/events/${seg(eventId)}/registrations`)
    .then((res) => toList(res.data))
}
