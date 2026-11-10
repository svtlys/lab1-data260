import { createAsyncThunk, createSelector, createSlice } from '@reduxjs/toolkit'
import * as jobService from '../../services/jobService'
import { extractErrorMessage } from '../../services/api'
import { loggedOut, sessionExpired } from './authSlice'

// fetchMyApplications: the logged-in student's applications
export const fetchMyApplications = createAsyncThunk(
  'applications/fetchMine',
  async (_, { rejectWithValue }) => {
    try {
      return await jobService.getMyApplications()
    } catch (error) {
      return rejectWithValue(extractErrorMessage(error, 'Could not load your applications.'))
    }
  },
)

// applyForJob: submit an application (optional PDF resume), then reload the list
export const applyForJob = createAsyncThunk(
  'applications/apply',
  async ({ jobId, resumeFile }, { dispatch, rejectWithValue }) => {
    try {
      await jobService.applyToJob(jobId, resumeFile)
    } catch (error) {
      return rejectWithValue(extractErrorMessage(error, 'Could not submit your application.'))
    }
    await dispatch(fetchMyApplications())
    return jobId
  },
)

const initialState = {
  items: [],
  status: 'idle', // idle | loading | succeeded | failed
  error: null,
  applyingJobId: null,
}

const applicationsSlice = createSlice({
  name: 'applications',
  initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchMyApplications.pending, (state) => {
        state.status = 'loading'
        state.error = null
      })
      .addCase(fetchMyApplications.fulfilled, (state, action) => {
        state.status = 'succeeded'
        state.items = action.payload
      })
      .addCase(fetchMyApplications.rejected, (state, action) => {
        state.status = 'failed'
        state.error = action.payload || 'Could not load your applications.'
      })
      .addCase(applyForJob.pending, (state, action) => {
        state.applyingJobId = action.meta.arg.jobId
      })
      .addCase(applyForJob.fulfilled, (state) => {
        state.applyingJobId = null
      })
      .addCase(applyForJob.rejected, (state) => {
        state.applyingJobId = null
      })
      // a new user must never see the previous user's applications
      .addCase(loggedOut, () => initialState)
      .addCase(sessionExpired, () => initialState)
  },
})

// selectors
export const selectApplications = (state) => state.applications.items
export const selectApplicationsStatus = (state) => state.applications.status
export const selectApplicationsError = (state) => state.applications.error
export const selectApplyingJobId = (state) => state.applications.applyingJobId
export const selectAppliedJobIds = createSelector([selectApplications], (items) =>
  items.map((application) => application.job_id),
)

export default applicationsSlice.reducer
