import api from './api'

// GET /api/students/me -- requires Authorization: Bearer <student_token>
export function getMyStudentProfile() {
  return api.get('/api/students/me').then((res) => res.data)
}

// PUT /api/students/me
export function updateMyStudentProfile(payload) {
  return api.put('/api/students/me', payload).then((res) => res.data)
}
