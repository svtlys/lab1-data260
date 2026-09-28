import api from './api'

// POST /api/auth/student/signup
// { full_name, email, password, college_name }
export function signupStudent(payload) {
  return api.post('/api/auth/student/signup', payload).then((res) => res.data)
}

// POST /api/auth/company/signup
// { company_name, email, password, location }
export function signupCompany(payload) {
  return api.post('/api/auth/company/signup', payload).then((res) => res.data)
}

// POST /api/auth/login
// { email, password } -> { access_token, token_type, user: { id, role, email, is_active } }
export function login(email, password) {
  return api.post('/api/auth/login', { email, password }).then((res) => res.data)
}

// Client-side only: the backend has no logout endpoint (stateless JWT),
// so logging out just means dropping the token.
export function logout() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('user')
}
