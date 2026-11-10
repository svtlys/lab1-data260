import { createSlice } from '@reduxjs/toolkit'
import { loggedOut, sessionExpired } from './authSlice'

// Saved jobs and events. The backend has no "list my saved items" endpoint yet, so this slice
// fills from successful assistant saves (dispatched by the assistant slice) and from
// savedItemsLoaded if an endpoint is added later.
const initialState = {
  items: [], // { item_type: 'job' | 'event', item_id }
}

const savedItemsSlice = createSlice({
  name: 'savedItems',
  initialState,
  reducers: {
    // one item was saved; ignore it if we already have it
    itemSaved(state, action) {
      const { item_type: type, item_id: id } = action.payload
      const exists = state.items.some((item) => item.item_type === type && item.item_id === id)
      if (!exists) state.items.push(action.payload)
    },
    // replace the whole list, for example from a future backend endpoint
    savedItemsLoaded(state, action) {
      state.items = action.payload
    },
  },
  extraReducers: (builder) => {
    builder.addCase(loggedOut, () => initialState).addCase(sessionExpired, () => initialState)
  },
})

export const { itemSaved, savedItemsLoaded } = savedItemsSlice.actions

// selectors
export const selectSavedItems = (state) => state.savedItems.items
export const selectSavedCount = (state) => state.savedItems.items.length

export default savedItemsSlice.reducer
