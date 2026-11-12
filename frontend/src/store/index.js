import { configureStore } from '@reduxjs/toolkit'
import authReducer from './slices/authSlice'
import jobsReducer from './slices/jobsSlice'
import applicationsReducer from './slices/applicationsSlice'
import eventsReducer from './slices/eventsSlice'
import savedItemsReducer from './slices/savedItemsSlice'
import assistantReducer, {
  ASSISTANT_STORAGE_KEY,
  persistedAssistantState,
} from './slices/assistantSlice'

// One store for the whole app. Redux DevTools works in development automatically.
export const store = configureStore({
  reducer: {
    auth: authReducer,
    jobs: jobsReducer,
    applications: applicationsReducer,
    events: eventsReducer,
    savedItems: savedItemsReducer,
    assistant: assistantReducer,
  },
})

// keep the assistant conversation across page refreshes (this tab only)
let lastSaved = ''
store.subscribe(() => {
  try {
    const next = JSON.stringify(persistedAssistantState(store.getState().assistant))
    if (next !== lastSaved) {
      sessionStorage.setItem(ASSISTANT_STORAGE_KEY, next)
      lastSaved = next
    }
  } catch {
    // storage can be unavailable; the app still works without it
  }
})
