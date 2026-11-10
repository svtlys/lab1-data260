import { createAsyncThunk, createSlice } from '@reduxjs/toolkit'
import * as authService from '../../services/authService'
import { extractErrorMessage } from '../../services/api'

// Restore the session that api.js and the login thunk keep in localStorage,
// so a page refresh does not send the user back to the login page.
function readStoredUser() {
  try {
    const token = localStorage.getItem('access_token')
    const stored = localStorage.getItem('user')
    return token && stored ? JSON.parse(stored) : null
  } catch {
    return null
  }
}

// login: call the API, keep the token for the axios interceptor, return the user
export const login = createAsyncThunk(
  'auth/login',
  async ({ email, password }, { rejectWithValue }) => {
    try {
      const data = await authService.login(email, password)
      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('user', JSON.stringify(data.user))
      return data.user
    } catch (error) {
      return rejectWithValue(
        extractErrorMessage(error, 'Could not log in. Check your email and password.'),
      )
    }
  },
)

const initialState = {
  user: readStoredUser(),
  status: 'idle', // idle | loading | succeeded | failed
  error: null,
}

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    // user chose to log out
    loggedOut(state) {
      state.user = null
      state.status = 'idle'
      state.error = null
    },
    // api.js saw a 401, so the token is no longer valid
    sessionExpired(state) {
      state.user = null
      state.status = 'idle'
      state.error = 'Your session expired. Please log in again.'
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(login.pending, (state) => {
        state.status = 'loading'
        state.error = null
      })
      .addCase(login.fulfilled, (state, action) => {
        state.status = 'succeeded'
        state.user = action.payload
      })
      .addCase(login.rejected, (state, action) => {
        state.status = 'failed'
        state.error = action.payload || 'Could not log in.'
      })
  },
})

export const { loggedOut, sessionExpired } = authSlice.actions

// logout: drop the stored token first (a side effect), then clear the state (pure reducer)
export const logout = () => (dispatch) => {
  authService.logout()
  dispatch(loggedOut())
}

// selectors
export const selectUser = (state) => state.auth.user
export const selectIsAuthenticated = (state) => Boolean(state.auth.user)
export const selectUserRole = (state) => (state.auth.user ? state.auth.user.role : null)
export const selectAuthStatus = (state) => state.auth.status
export const selectAuthError = (state) => state.auth.error

export default authSlice.reducer
