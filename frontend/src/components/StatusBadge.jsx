import React from 'react'

// The status is always spelled out, so colour is never the only signal.
const STYLES = {
  Pending: 'bg-warning text-dark',
  Reviewed: 'bg-success',
  Declined: 'bg-danger',
}

export default function StatusBadge({ status }) {
  return (
    <span className={`badge ${STYLES[status] || 'bg-light text-dark border'}`}>
      {status || 'Unknown'}
    </span>
  )
}
