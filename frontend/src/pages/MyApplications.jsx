import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import * as jobService from '../services/jobService'
import { extractErrorMessage } from '../services/api'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import ErrorAlert from '../components/ErrorAlert.jsx'
import EmptyState from '../components/EmptyState.jsx'
import StatusBadge from '../components/StatusBadge.jsx'

export default function MyApplications() {
  const [applications, setApplications] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    jobService
      .getMyApplications()
      .then(setApplications)
      .catch((err) => setError(extractErrorMessage(err, 'Could not load your applications.')))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="page-container">
      <div className="mb-4">
        <h2 className="mb-1">My applications</h2>
        <p className="text-muted mb-0">Track the status of every job you applied to.</p>
      </div>

      <ErrorAlert message={error} />
      {loading && <LoadingSpinner label="Loading applications..." />}

      {!loading && !error && applications.length === 0 && (
        <EmptyState title="No applications yet" message="Find a job and apply to see it here.">
          <Link to="/jobs" className="btn btn-primary">
            Find jobs
          </Link>
        </EmptyState>
      )}

      {!loading && applications.length > 0 && (
        <div className="card shadow-sm">
          <div className="table-responsive">
            <table className="table align-middle mb-0">
              <thead>
                <tr>
                  <th>Job</th>
                  <th>Company</th>
                  <th>Applied</th>
                  <th>Resume</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {applications.map((app) => (
                  <tr key={app.id}>
                    <td>{app.job_title}</td>
                    <td>{app.company_name}</td>
                    <td>{new Date(app.applied_at).toLocaleDateString()}</td>
                    <td>{app.resume_filename || 'None'}</td>
                    <td>
                      <StatusBadge status={app.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
