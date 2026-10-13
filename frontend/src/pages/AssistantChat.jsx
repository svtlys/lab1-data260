import React, { useState } from 'react'
import * as assistantService from '../services/assistantService'
import { extractErrorMessage } from '../services/api'
import ErrorAlert from '../components/ErrorAlert.jsx'
import LoadingSpinner from '../components/LoadingSpinner.jsx'

export default function AssistantChat() {
  const [message, setMessage] = useState('')
  const [conversationId, setConversationId] = useState(null)
  const [messages, setMessages] = useState([])
  const [lastToolCalls, setLastToolCalls] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleSubmit(event) {
    event.preventDefault()
    const trimmedMessage = message.trim()
    if (!trimmedMessage || loading) return

    setError('')
    setMessage('')
    setLoading(true)
    setMessages((current) => [...current, { role: 'user', content: trimmedMessage }])

    try {
      const response = await assistantService.sendAssistantMessage(
        trimmedMessage,
        conversationId,
      )
      setConversationId(response.conversation_id)
      setMessages((current) => [
        ...current,
        { role: 'assistant', content: response.answer },
      ])
      setLastToolCalls(response.tool_calls || [])
    } catch (err) {
      setError(extractErrorMessage(err, 'The assistant could not answer right now.'))
    } finally {
      setLoading(false)
    }
  }

  function startNewConversation() {
    setConversationId(null)
    setMessages([])
    setLastToolCalls([])
    setError('')
  }

  return (
    <div className="page-container">
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
          <h2 className="mb-1">Assistant</h2>
          <p className="text-muted mb-0">
            Ask about your preferences, jobs, events, or saved opportunities.
          </p>
        </div>
        <button type="button" className="btn btn-outline-secondary" onClick={startNewConversation}>
          New conversation
        </button>
      </div>

      <ErrorAlert message={error} />

      <div className="card shadow-sm mb-4">
        <div className="card-body">
          {messages.length === 0 && (
            <div className="text-muted mb-3">
              Try: “Find remote jobs in Cupertino” or “Show me virtual events.”
            </div>
          )}

          {messages.map((item, index) => (
            <div
              className={`mb-3 p-3 rounded ${item.role === 'user' ? 'bg-light' : 'bg-primary-subtle'}`}
              key={`${item.role}-${index}`}
            >
              <div className="small text-muted mb-1">
                {item.role === 'user' ? 'You' : 'Assistant'}
              </div>
              <div style={{ whiteSpace: 'pre-wrap' }}>{item.content}</div>
            </div>
          ))}

          {loading && <LoadingSpinner label="Assistant is thinking..." />}

          <form onSubmit={handleSubmit} className="d-flex gap-2 mt-3">
            <input
              className="form-control"
              value={message}
              onChange={(event) => setMessage(event.target.value)}
              placeholder="Ask the assistant something..."
              disabled={loading}
            />
            <button type="submit" className="btn btn-primary" disabled={loading || !message.trim()}>
              Send
            </button>
          </form>
        </div>
      </div>

      {lastToolCalls.length > 0 && (
        <div className="card shadow-sm">
          <div className="card-body">
            <h5>Tool calls from the last answer</h5>
            <p className="text-muted small">
              This shows how the hand-built assistant used project data.
            </p>
            {lastToolCalls.map((toolCall, index) => (
              <div className="border rounded p-3 mb-2" key={`${toolCall.tool_call_id}-${index}`}>
                <div className="fw-semibold">{toolCall.tool_name}</div>
                <div className="small text-muted">
                  Iteration {toolCall.iteration}
                </div>
                <pre className="small mb-0 mt-2">
                  {JSON.stringify(toolCall.result || toolCall.error || toolCall.arguments, null, 2)}
                </pre>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
