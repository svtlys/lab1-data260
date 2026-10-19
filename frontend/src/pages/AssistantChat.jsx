import React, { useState } from 'react'
import * as assistantService from '../services/assistantService'
import { extractErrorMessage } from '../services/api'
import ErrorAlert from '../components/ErrorAlert.jsx'
import LoadingSpinner from '../components/LoadingSpinner.jsx'

// The model writes **bold** and *italic* markdown; render them instead of showing the asterisks.
function renderInline(text) {
  return String(text)
    .split(/(\*\*[^*\n]+\*\*|\*[^*\n]+\*)/g)
    .map((part, index) => {
      if (part.startsWith('**') && part.endsWith('**') && part.length > 4) {
        return <strong key={index}>{part.slice(2, -2)}</strong>
      }
      if (part.startsWith('*') && part.endsWith('*') && part.length > 2) {
        return <em key={index}>{part.slice(1, -1)}</em>
      }
      return <React.Fragment key={index}>{part}</React.Fragment>
    })
}

function parseArguments(args) {
  if (args && typeof args === 'object') return args
  try {
    return JSON.parse(args)
  } catch {
    return {}
  }
}

// Did the backend's confirmation gate refuse a save in this answer? If so, return what it wanted to save.
// Tolerant on purpose: the result may be a string or an object, and the model may name the arguments differently.
function findDeclinedSave(toolCalls) {
  for (const call of toolCalls || []) {
    if (call.tool_name !== 'save_job_or_event') continue
    const outcome = `${typeof call.result === 'string' ? call.result : JSON.stringify(call.result ?? '')} ${call.error ?? ''}`
    if (!/cancelled/i.test(outcome)) continue
    const args = parseArguments(call.arguments)
    const itemType = args.item_type || args.type || (args.job_id ? 'job' : args.event_id ? 'event' : '')
    const itemId = args.item_id ?? args.job_id ?? args.event_id ?? args.id ?? ''
    return { itemType, itemId }
  }
  return null
}

export default function AssistantChat() {
  const [message, setMessage] = useState('')
  const [conversationId, setConversationId] = useState(null)
  const [messages, setMessages] = useState([])
  const [lastToolCalls, setLastToolCalls] = useState([])
  const [lastRun, setLastRun] = useState(null)
  const [pendingSave, setPendingSave] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function send(text, confirmSave = false) {
    setError('')
    setLoading(true)
    setPendingSave(null)
    setMessages((current) => [...current, { role: 'user', content: text }])

    try {
      const response = await assistantService.sendAssistantMessage(text, conversationId, confirmSave)
      setConversationId(response.conversation_id)
      setMessages((current) => [...current, { role: 'assistant', content: response.answer }])
      const calls = response.tool_calls || []
      setLastToolCalls(calls)
      setLastRun({
        iterations: response.iterations,
        toolCallCount: response.tool_call_count,
        repairAttempts: response.repair_attempts,
        failureMode: response.failure_mode,
        hitCeiling: response.reached_iteration_ceiling,
      })
      // The gate said no: ask the student, and only resend with approval if they say yes.
      setPendingSave(findDeclinedSave(calls))
    } catch (err) {
      setError(extractErrorMessage(err, 'The assistant could not answer right now.'))
    } finally {
      setLoading(false)
    }
  }

  function handleSubmit(event) {
    event.preventDefault()
    const trimmed = message.trim()
    if (!trimmed || loading) return
    setMessage('')
    send(trimmed)
  }

  function approveSave() {
    if (!pendingSave || loading) return
    send(
      pendingSave.itemType && pendingSave.itemId
        ? `Yes, please save the ${pendingSave.itemType} with id ${pendingSave.itemId}.`
        : 'Yes, please save the item you just tried to save.',
      true,
    )
  }

  function declineSave() {
    setPendingSave(null)
    setMessages((current) => [
      ...current,
      { role: 'assistant', content: 'Okay, I did not save it.', local: true },
    ])
  }

  function startNewConversation() {
    setConversationId(null)
    setMessages([])
    setLastToolCalls([])
    setLastRun(null)
    setPendingSave(null)
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
              <div style={{ whiteSpace: 'pre-wrap' }}>{renderInline(item.content)}</div>
            </div>
          ))}

          {loading && <LoadingSpinner label="Assistant is thinking..." />}

          {pendingSave && !loading && (
            <div className="alert alert-warning d-flex flex-wrap justify-content-between align-items-center gap-2" role="alert">
              <div>
                <strong>Confirm save.</strong> The assistant wants to save{' '}
                {pendingSave.itemType && pendingSave.itemId
                  ? `${pendingSave.itemType} #${pendingSave.itemId}`
                  : 'this item'}{' '}
                to your saved items. It has not been saved yet.
              </div>
              <div className="d-flex gap-2">
                <button type="button" className="btn btn-primary btn-sm" onClick={approveSave}>
                  Yes, save it
                </button>
                <button type="button" className="btn btn-outline-secondary btn-sm" onClick={declineSave}>
                  No, don&apos;t save
                </button>
              </div>
            </div>
          )}

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

      {lastRun && (
        <div className="card shadow-sm">
          <div className="card-body">
            <h5>How the last answer was produced</h5>
            <div className="d-flex flex-wrap gap-2 mb-3">
              <span className="badge text-bg-light border">Iterations: {lastRun.iterations}</span>
              <span className="badge text-bg-light border">Tool calls: {lastRun.toolCallCount}</span>
              <span className="badge text-bg-light border">Repair attempts: {lastRun.repairAttempts}</span>
              <span className={`badge ${lastRun.failureMode ? 'text-bg-warning' : 'text-bg-light border'}`}>
                Failure mode: {lastRun.failureMode || 'none'}
              </span>
              {lastRun.hitCeiling && <span className="badge text-bg-danger">Iteration limit reached</span>}
            </div>
            {lastToolCalls.length === 0 && (
              <p className="text-muted small mb-0">The assistant answered without calling a tool.</p>
            )}
            {lastToolCalls.map((toolCall, index) => (
              <div className="border rounded p-3 mb-2" key={`${toolCall.tool_call_id}-${index}`}>
                <div className="fw-semibold">{toolCall.tool_name}</div>
                <div className="small text-muted">Iteration {toolCall.iteration}</div>
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
