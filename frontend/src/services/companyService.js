import api from './api'

// NOTE: the Week 1 backend handoff only documents student profile endpoints
// (GET/PUT /api/students/me). It does not yet list a company equivalent.
// This mirrors that same shape at /api/companies/me so the company dashboard
// has something to call as soon as your partner adds it on the backend --
// flag this with your partner rather than assuming the path is final.

// GET /api/companies/me -- requires Authorization: Bearer <company_token>
export function getMyCompanyProfile() {
  return api.get('/api/companies/me').then((res) => res.data)
}

// PUT /api/companies/me
export function updateMyCompanyProfile(payload) {
  return api.put('/api/companies/me', payload).then((res) => res.data)
}
