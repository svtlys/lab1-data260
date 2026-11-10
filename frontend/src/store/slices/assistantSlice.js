import { createAsyncThunk, createSlice } from '@reduxjs/toolkit'
import * as assistantService from '../../services/assistantService'
import { extractErrorMessage } from '../../services/api'
import { extractSavedItems, findDeclinedSave } from '../../utils/assistantTools'
import { loggedOut, sessionExpired } from './authSlice'
import { itemSaved } from './savedItemsSlice'

// The conversation thread is kept here, not in the page, so leaving the Assistant page and coming
// back (or refreshing the tab) does not lose it. It is mirrored to sessionStorage by the store.
export const ASSISTANT_STORAGE_KEY = 'p16_assistant_conversation'

const emptyConversation = {
  conversationId: null,
  messages: [],
  lastToolCalls: [],
  lastRun: null,
  pendingSave: null,
}

function loadPersisted() {
  try {
    const raw = sessionStorage.getItem(ASSISTANT_STORAGE_KEY)
    return raw ? { ...emptyConversation, ...JSON.parse(raw) } : emptyConversation
  } catch {
    return emptyConversation
  }
}

// the part of the state worth saving between page loads
export function persistedAssistantState(state) {
  const { conversationId, messages, lastToolCalls, lastRun, pendingSave } = state
  return { conversationId, messages, lastToolCalls, lastRun, pendingSave }
}

// sendMessage: send one student message in the current conversation
export const sendMessage = createAsyncThunk(
  'assistant/sendMessage',
  async ({ text, confirmSave = false }, { getState, dispatch, rejectWithValue }) => {
    try {
      const conversationId = getState().assistant.conversationId
      const response = await assistantService.sendAssistantMessage(text, conversationId, confirmSave)
      // anything the assistant really saved also goes into the saved-items slice
      extractSavedItems(response.tool_calls).forEach((item) => dispatch(itemSaved(item)))
      return response
    } catch (error) {
      return rejectWithValue(extractErrorMessage(error, 'The assistant could not answer right now.'))
    }
  },
)

const initialState = {
  ...loadPersisted(),
  status: 'idle', // idle | sending
  error: null,
}

const assistantSlice = createSlice({
  name: 'assistant',
  initialState,
  reducers: {
    // the student said no to a pending save: nothing is sent to the backend
    saveDeclined(state) {
      state.pendingSave = null
      state.messages.push({ role: 'assistant', content: 'Okay, I did not save it.', local: true })
    },
    // start over with a fresh thread
    newConversation() {
      return { ...emptyConversation, status: 'idle', error: null }
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(sendMessage.pending, (state, action) => {
        state.status = 'sending'
        state.error = null
        state.pendingSave = null
        state.messages.push({ role: 'user', content: action.meta.arg.text })
      })
      .addCase(sendMessage.fulfilled, (state, action) => {
        const response = action.payload
        const calls = response.tool_calls || []
        state.status = 'idle'
        state.conversationId = response.conversation_id
        state.messages.push({ role: 'assistant', content: response.answer })
        state.lastToolCalls = calls
        state.lastRun = {
          iterations: response.iterations,
          toolCallCount: response.tool_call_count,
          repairAttempts: response.repair_attempts,
          failureMode: response.failure_mode,
          hitCeiling: response.reached_iteration_ceiling,
          traceId: response.trace_id,
          tokenUsage: response.token_usage,
          compactions: response.compaction?.count ?? 0,
        }
        state.pendingSave = findDeclinedSave(calls)
      })
      .addCase(sendMessage.rejected, (state, action) => {
        state.status = 'idle'
        state.error = action.payload || 'The assistant could not answer right now.'
      })
      // a new user must never see the previous user's conversation
      .addCase(loggedOut, () => ({ ...emptyConversation, status: 'idle', error: null }))
      .addCase(sessionExpired, () => ({ ...emptyConversation, status: 'idle', error: null }))
  },
})

export const { saveDeclined, newConversation } = assistantSlice.actions

// selectors
export const selectConversationId = (state) => state.assistant.conversationId
export const selectMessages = (state) => state.assistant.messages
export const selectLastToolCalls = (state) => state.assistant.lastToolCalls
export const selectLastRun = (state) => state.assistant.lastRun
export const selectPendingSave = (state) => state.assistant.pendingSave
export const selectAssistantLoading = (state) => state.assistant.status === 'sending'
export const selectAssistantError = (state) => state.assistant.error

export default assistantSlice.reducer
