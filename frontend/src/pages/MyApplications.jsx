import React, { useEffect } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { Link } from 'react-router-dom'
import {
  fetchMyApplications,
  selectApplications,
  selectApplicationsError,
  selectApplicationsStatus,
} from '../store/slices/applicationsSlice'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import ErrorAlert from '../components/ErrorAlert.jsx'
import EmptyState from '../components/EmptyState.jsx'
import StatusBadge from '../components/StatusBadge.jsx'

export default function MyApplications() {
  // applications live in the Redux "applications" slice
  const dispatch = useDispatch()
  const applications = useSelector(selectApplications)
  const status = useSelector(selectApplicationsStatus)
  const error = useSelector(selectApplicationsError) || ''
  // show the spinner only on the first load; later visits show the cached list while it refreshes
  const loading = status === 'idle' || (status === 'loading' && applications.length === 0)

  useEffect(() => {
    dispatch(fetchMyApplications())
  }, [dispatch])

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
                {applications.map((application) => (
                  <tr key={application.id}>
                    <td>{application.job_title}</td>
                    <td>{application.company_name}</td>
                    <td>{new Date(application.applied_at).toLocaleDateString()}</td>
                    <td>{application.resume_filename || 'None'}</td>
                    <td>
                      <StatusBadge status={application.status} />
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
