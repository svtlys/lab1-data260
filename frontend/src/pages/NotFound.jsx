import React from 'react'
import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <div className="page-container text-center">
      <h2 className="mb-3">Page not found</h2>
      <p className="text-muted">That address doesn&apos;t match anything here.</p>
      <Link to="/" className="btn btn-primary">
        Back to home
      </Link>
    </div>
  )
}
