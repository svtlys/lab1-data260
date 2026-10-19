import React from 'react'

// Shown when a list loads successfully but has nothing in it.
export default function EmptyState({ title, message, children }) {
  return (
    <div className="text-center text-muted py-5">
      <h5 className="text-body">{title}</h5>
      {message && <p className="mb-3">{message}</p>}
      {children}
    </div>
  )
}
