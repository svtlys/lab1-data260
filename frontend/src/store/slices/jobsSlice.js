import { createAsyncThunk, createSlice } from '@reduxjs/toolkit'
import * as jobService from '../../services/jobService'
import { extractErrorMessage } from '../../services/api'

export const initialJobFilters = {
  search: '',
  city: '',
  employment_type: '',
  is_remote: '',
}

// fetchJobs: search jobs with the given filters
export const fetchJobs = createAsyncThunk(
  'jobs/fetchJobs',
  async (filters, { rejectWithValue }) => {
    try {
      return await jobService.searchJobs(filters)
    } catch (error) {
      return rejectWithValue(extractErrorMessage(error, 'Could not load jobs.'))
    }
  },
)

const initialState = {
  items: [],
  filters: initialJobFilters,
  selectedId: null,
  status: 'idle', // idle | loading | succeeded | failed
  error: null,
}

const jobsSlice = createSlice({
  name: 'jobs',
  initialState,
  reducers: {
    // change one search filter, such as city or employment_type
    setJobFilter(state, action) {
      const { name, value } = action.payload
      state.filters[name] = value
    },
    clearJobFilters(state) {
      state.filters = initialJobFilters
    },
    // choose which job the detail panel shows
    selectJob(state, action) {
      state.selectedId = action.payload
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchJobs.pending, (state) => {
        state.status = 'loading'
        state.error = null
      })
      .addCase(fetchJobs.fulfilled, (state, action) => {
        state.status = 'succeeded'
        state.items = action.payload
        // keep the current selection if it is still in the results, else pick the first job
        const stillThere = action.payload.some((job) => job.id === state.selectedId)
        state.selectedId = stillThere ? state.selectedId : (action.payload[0]?.id ?? null)
      })
      .addCase(fetchJobs.rejected, (state, action) => {
        state.status = 'failed'
        state.error = action.payload || 'Could not load jobs.'
      })
  },
})

export const { setJobFilter, clearJobFilters, selectJob } = jobsSlice.actions

// selectors
export const selectJobs = (state) => state.jobs.items
export const selectJobFilters = (state) => state.jobs.filters
export const selectJobsStatus = (state) => state.jobs.status
export const selectJobsError = (state) => state.jobs.error
export const selectSelectedJob = (state) =>
  state.jobs.items.find((job) => job.id === state.jobs.selectedId) || null

export default jobsSlice.reducer
