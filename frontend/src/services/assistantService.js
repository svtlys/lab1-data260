import api from './api'

// send one student message to the protected assistant endpoint.
// confirmSave=true tells the backend the student explicitly approved a save for this turn.
export function sendAssistantMessage(message, conversationId = null, confirmSave = false) {
  return api
    .post('/api/assistant/chat', {
      message,
      conversation_id: conversationId,
      confirm_save: confirmSave,
    })
    .then((res) => res.data)
}
