import { createAsyncThunk, createSelector, createSlice } from '@reduxjs/toolkit'
import * as eventService from '../../services/eventService'
import { extractErrorMessage } from '../../services/api'
import { loggedOut, sessionExpired } from './authSlice'

export const initialEventFilters = {
  search: '',
  city: '',
  event_type: '',
  is_virtual: '',
  start_date: '',
  end_date: '',
}

// fetchEvents: search events with the given filters
export const fetchEvents = createAsyncThunk(
  'events/fetchEvents',
  async (filters, { rejectWithValue }) => {
    try {
      return await eventService.searchEvents(filters)
    } catch (error) {
      return rejectWithValue(extractErrorMessage(error, 'Could not load events.'))
    }
  },
)

// fetchRegisteredEvents: events the logged-in student already registered for
export const fetchRegisteredEvents = createAsyncThunk(
  'events/fetchRegistered',
  async (_, { rejectWithValue }) => {
    try {
      return await eventService.getRegisteredEvents()
    } catch (error) {
      return rejectWithValue(extractErrorMessage(error, 'Could not load registered events.'))
    }
  },
)

// registerForEvent: register, then reload the registered list
export const registerForEvent = createAsyncThunk(
  'events/register',
  async (eventId, { dispatch, rejectWithValue }) => {
    try {
      await eventService.registerForEvent(eventId)
    } catch (error) {
      return rejectWithValue(extractErrorMessage(error, 'Could not register for this event.'))
    }
    await dispatch(fetchRegisteredEvents())
    return eventId
  },
)

const initialState = {
  items: [],
  filters: initialEventFilters,
  selectedId: null,
  status: 'idle', // idle | loading | succeeded | failed
  error: null,
  registered: [],
  registeredStatus: 'idle',
  registeredError: null,
  registeringId: null,
}

const eventsSlice = createSlice({
  name: 'events',
  initialState,
  reducers: {
    setEventFilter(state, action) {
      const { name, value } = action.payload
      state.filters[name] = value
    },
    clearEventFilters(state) {
      state.filters = initialEventFilters
    },
    selectEvent(state, action) {
      state.selectedId = action.payload
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchEvents.pending, (state) => {
        state.status = 'loading'
        state.error = null
      })
      .addCase(fetchEvents.fulfilled, (state, action) => {
        state.status = 'succeeded'
        state.items = action.payload
        const stillThere = action.payload.some((event) => event.id === state.selectedId)
        state.selectedId = stillThere ? state.selectedId : (action.payload[0]?.id ?? null)
      })
      .addCase(fetchEvents.rejected, (state, action) => {
        state.status = 'failed'
        state.error = action.payload || 'Could not load events.'
      })
      .addCase(fetchRegisteredEvents.pending, (state) => {
        state.registeredStatus = 'loading'
        state.registeredError = null
      })
      .addCase(fetchRegisteredEvents.fulfilled, (state, action) => {
        state.registeredStatus = 'succeeded'
        state.registered = action.payload
      })
      .addCase(fetchRegisteredEvents.rejected, (state, action) => {
        state.registeredStatus = 'failed'
        state.registeredError = action.payload || 'Could not load registered events.'
      })
      .addCase(registerForEvent.pending, (state, action) => {
        state.registeringId = action.meta.arg
      })
      .addCase(registerForEvent.fulfilled, (state) => {
        state.registeringId = null
      })
      .addCase(registerForEvent.rejected, (state) => {
        state.registeringId = null
      })
      .addCase(loggedOut, () => initialState)
      .addCase(sessionExpired, () => initialState)
  },
})

export const { setEventFilter, clearEventFilters, selectEvent } = eventsSlice.actions

// selectors
export const selectEvents = (state) => state.events.items
export const selectEventFilters = (state) => state.events.filters
export const selectEventsStatus = (state) => state.events.status
export const selectEventsError = (state) => state.events.error
export const selectSelectedEvent = (state) =>
  state.events.items.find((event) => event.id === state.events.selectedId) || null
export const selectRegisteredEvents = (state) => state.events.registered
export const selectRegisteredStatus = (state) => state.events.registeredStatus
export const selectRegisteredError = (state) => state.events.registeredError
export const selectRegisteringId = (state) => state.events.registeringId
export const selectRegisteredEventIds = createSelector([selectRegisteredEvents], (events) =>
  events.map((event) => event.id),
)

export default eventsSlice.reducer
