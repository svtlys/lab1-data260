import api from './api'

// send one student message to the protected assistant endpoint.
// confirm_save is true only after the student explicitly approves a save.
export function sendAssistantMessage(message, conversationId = null, confirmSave = false) {
  return api
    .post('/api/assistant/chat', {
      message,
      conversation_id: conversationId,
      confirm_save: confirmSave,
    })
    .then((res) => res.data)
}
