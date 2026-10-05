import React, { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import * as companyService from '../services/companyService'
import { extractErrorMessage } from '../services/api'
import { formatDate, formatSalary, todayISO } from '../utils/format'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import ErrorAlert from '../components/ErrorAlert.jsx'
import EmptyState from '../components/EmptyState.jsx'

export default function MyJobs() {
  const location = useLocation()
  const flash = location.state && location.state.flash
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    companyService
      .getMyJobs()
      .then((list) => {
        // Newest first.
        if (!cancelled) setJobs([...list].sort((a, b) => (b.id || 0) - (a.id || 0)))
      })
      .catch((err) => {
        if (!cancelled) setError(extractErrorMessage(err, 'Could not load your job postings.'))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const today = todayISO()

  return (
    <div className="page-container">
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h2 className="mb-0">My jobs</h2>
        <Link to="/company/jobs/new" className="btn btn-primary">
          Post a job
        </Link>
      </div>

      {flash && <div className="alert alert-success">{flash}</div>}
      {loading && <LoadingSpinner label="Loading your job postings..." />}
      <ErrorAlert message={error} />

      {!loading && !error && jobs.length === 0 && (
        <div className="card shadow-sm">
          <EmptyState
            title="No job postings yet"
            message="Post your first job and students will be able to apply."
          >
            <Link to="/company/jobs/new" className="btn btn-primary">
              Post a job
            </Link>
          </EmptyState>
        </div>
      )}

      {!loading && !error && jobs.length > 0 && (
        <div className="card shadow-sm">
          <div className="table-responsive">
            <table className="table table-hover align-middle mb-0">
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Category</th>
                  <th>Location</th>
                  <th>Posted</th>
                  <th>Deadline</th>
                  <th className="text-end">Salary</th>
                  <th className="text-center">Applicants</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => (
                  <tr key={job.id}>
                    <td>
                      <Link to={`/company/jobs/${job.id}/applicants`} className="fw-semibold">
                        {job.title}
                      </Link>
                    </td>
                    <td>{job.category}</td>
                    <td>{job.location}</td>
                    <td>{formatDate(job.posting_date)}</td>
                    <td>
                      {formatDate(job.deadline)}
                      {job.deadline && job.deadline < today && (
                        <span className="badge bg-light text-dark border ms-2">Past deadline</span>
                      )}
                    </td>
                    <td className="text-end">{formatSalary(job.salary)}</td>
                    <td className="text-center">
                      {job.applicant_count ?? 0}
                      {job.pending_count > 0 && (
                        <span className="badge bg-warning text-dark ms-2">
                          {job.pending_count} pending
                        </span>
                      )}
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
