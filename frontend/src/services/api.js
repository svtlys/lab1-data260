import axios from 'axios'

// Single axios instance. Every other service module goes through this,
// so the Bearer-token attachment and 401 handling only live in one place.
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:9160',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Attach the stored access token (if any) to every request.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// If the backend says the token is no longer valid (expired after 60 minutes,
// for example), clear it and tell AuthContext so the UI drops back to the
// logged-out state and ProtectedRoute sends the user to /login.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('user')
      window.dispatchEvent(new Event('auth:logout'))
    }
    return Promise.reject(error)
  },
)

// Turn whatever the backend/network gave us into a plain string message,
// so every page can show one line without repeating this logic.
export function extractErrorMessage(error, fallback = 'Something went wrong. Please try again.') {
  const response = error.response
  if (response) {
    const data = response.data

    // FastAPI's default answer for a route that doesn't exist is exactly
    // {"detail": "Not Found"}. Real "record not found" errors carry their own text.
    if (response.status === 404 && data && data.detail === 'Not Found') {
      const method = String((error.config && error.config.method) || '').toUpperCase()
      const url = (error.config && error.config.url) || ''
      return `The backend doesn't have this endpoint yet (${method} ${url}).`
    }

    if (data) {
      if (typeof data.detail === 'string') return data.detail
      if (Array.isArray(data.detail)) {
        // Pydantic validation errors: include which field each message is about.
        return data.detail
          .map((d) => {
            const field = Array.isArray(d.loc) ? d.loc.filter((p) => p !== 'body').join('.') : ''
            return field ? `${field}: ${d.msg}` : d.msg || JSON.stringify(d)
          })
          .join('; ')
      }
      if (typeof data === 'string') return data
    }
  }
  if (error.message) return error.message
  return fallback
}

export default api
