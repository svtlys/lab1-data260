import React, { useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import {
  newConversation,
  saveDeclined,
  selectAssistantError,
  selectAssistantLoading,
  selectLastRun,
  selectLastToolCalls,
  selectMessages,
  selectPendingSave,
  sendMessage,
} from '../store/slices/assistantSlice'
import ErrorAlert from '../components/ErrorAlert.jsx'
import LoadingSpinner from '../components/LoadingSpinner.jsx'

// render the assistant's simple inline markdown without adding a markdown package
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

export default function AssistantChat() {
  const dispatch = useDispatch()
  const messages = useSelector(selectMessages)
  const lastToolCalls = useSelector(selectLastToolCalls)
  const lastRun = useSelector(selectLastRun)
  const pendingSave = useSelector(selectPendingSave)
  const loading = useSelector(selectAssistantLoading)
  const error = useSelector(selectAssistantError) || ''
  const [message, setMessage] = useState('')

  function handleSubmit(event) {
    event.preventDefault()
    const trimmed = message.trim()
    if (!trimmed || loading) return
    setMessage('')
    dispatch(sendMessage({ text: trimmed }))
  }

  function approveSave() {
    if (!pendingSave || loading) return
    dispatch(
      sendMessage({
        text: pendingSave.itemType && pendingSave.itemId
          ? `Yes, please save the ${pendingSave.itemType} with id ${pendingSave.itemId}.`
          : 'Yes, please save the item you just asked about.',
        confirmSave: true,
      }),
    )
  }

  function declineSave() {
    dispatch(saveDeclined())
  }

  function startNewConversation() {
    dispatch(newConversation())
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
