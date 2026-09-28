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

// If the backend says the token is no longer valid, clear it so the app
// falls back to a logged-out state instead of looping on 401s.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('user')
    }
    return Promise.reject(error)
  },
)

// Turn whatever the backend/network gave us into a plain string message,
// so every page can show one line without repeating this logic.
export function extractErrorMessage(error, fallback = 'Something went wrong. Please try again.') {
  if (error.response && error.response.data) {
    const data = error.response.data
    if (typeof data.detail === 'string') return data.detail
    if (Array.isArray(data.detail)) {
      return data.detail.map((d) => d.msg || JSON.stringify(d)).join('; ')
    }
    if (typeof data === 'string') return data
  }
  if (error.message) return error.message
  return fallback
}

export default api
