import api from './api'

// send one student message to the protected assistant endpoint
export function sendAssistantMessage(message, conversationId = null) {
  return api
    .post('/api/assistant/chat', {
      message,
      conversation_id: conversationId,
    })
    .then((res) => res.data)
}
