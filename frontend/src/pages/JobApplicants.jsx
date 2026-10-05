import React, { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import * as companyService from '../services/companyService'
import { extractErrorMessage } from '../services/api'
import { APPLICATION_STATUSES } from '../constants'
import { formatDate } from '../utils/format'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import ErrorAlert from '../components/ErrorAlert.jsx'
import EmptyState from '../components/EmptyState.jsx'
import StatusBadge from '../components/StatusBadge.jsx'

export default function JobApplicants() {
  const { jobId } = useParams()
  const [job, setJob] = useState(null)
  const [applications, setApplications] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [actionError, setActionError] = useState('')
  const [savingId, setSavingId] = useState(null)
  const [resumeId, setResumeId] = useState(null)
  const [filter, setFilter] = useState('All')

  useEffect(() => {
    let cancelled = false

    async function load() {
      setLoading(true)
      setError('')
      try {
        // Find the job among the company's OWN jobs first, so a made-up id in the
        // URL never even asks for another company's applicants. (The backend must
        // still enforce ownership -- this is just a friendlier first check.)
        const jobs = await companyService.getMyJobs()
        const found = jobs.find((j) => String(j.id) === String(jobId))
        if (!found) {
          if (!cancelled) setError('That job was not found, or it does not belong to your company.')
          return
        }
        const list = await companyService.getJobApplications(jobId)
        if (!cancelled) {
          setJob(found)
          setApplications(list)
        }
      } catch (err) {
        if (!cancelled) setError(extractErrorMessage(err, 'Could not load the applicants.'))
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [jobId])

  async function handleStatusChange(application, nextStatus) {
    if (nextStatus === application.status) return
    setActionError('')
    setSavingId(application.id)
    try {
      const updated = await companyService.updateApplicationStatus(application.id, nextStatus)
      // Only the status changes; keep the rest of the row as it was.
      setApplications((current) =>
        current.map((a) =>
          a.id === application.id ? { ...a, status: (updated && updated.status) || nextStatus } : a,
        ),
      )
    } catch (err) {
      // The select is controlled by the stored status, so it snaps back on failure.
      setActionError(extractErrorMessage(err, 'Could not update the application status.'))
    } finally {
      setSavingId(null)
    }
  }

  async function handleViewResume(application) {
    setActionError('')
    setResumeId(application.id)
    // Open the tab inside the click so pop-up blockers allow it, then point it at the PDF.
    const tab = window.open('', '_blank')
    try {
      const blob = await companyService.getApplicationResume(application.id)
      const url = URL.createObjectURL(new Blob([blob], { type: 'application/pdf' }))
      if (!tab) {
        URL.revokeObjectURL(url)
        setActionError('Your browser blocked the pop-up. Allow pop-ups for this site to preview resumes.')
        return
      }
      tab.location.href = url
      setTimeout(() => URL.revokeObjectURL(url), 60000)
    } catch (err) {
      if (tab) tab.close()
      setActionError(extractErrorMessage(err, 'Could not open the resume.'))
    } finally {
      setResumeId(null)
    }
  }

  const countFor = (status) => applications.filter((a) => a.status === status).length
  const visible =
    filter === 'All' ? applications : applications.filter((a) => a.status === filter)

  return (
    <div className="page-container">
      <Link to="/company/jobs" className="text-decoration-none">
        &larr; My jobs
      </Link>

      {loading && <LoadingSpinner label="Loading applicants..." />}
      <div className="mt-3">
        <ErrorAlert message={error} />
      </div>

      {!loading && !error && job && (
        <>
          <div className="mt-3 mb-4">
            <h2 className="mb-1">{job.title}</h2>
            <div className="text-muted">
              {job.category} &middot; {job.location} &middot; Deadline {formatDate(job.deadline)}
            </div>
          </div>

          <ErrorAlert message={actionError} />

          {applications.length === 0 ? (
            <div className="card shadow-sm">
              <EmptyState
                title="No applicants yet"
                message="Students who apply to this job will show up here."
              />
            </div>
          ) : (
            <div className="card shadow-sm">
              <div className="card-body d-flex flex-wrap justify-content-between align-items-center gap-2">
                <div className="text-muted">
                  {applications.length} applicant{applications.length === 1 ? '' : 's'}
                  {' · '}
                  {countFor('Pending')} pending
                </div>
                <div className="d-flex align-items-center gap-2">
                  <label htmlFor="status-filter" className="form-label mb-0 text-muted">
                    Show
                  </label>
                  <select
                    id="status-filter"
                    className="form-select form-select-sm"
                    style={{ width: 'auto' }}
                    value={filter}
                    onChange={(e) => setFilter(e.target.value)}
                  >
                    <option value="All">All ({applications.length})</option>
                    {APPLICATION_STATUSES.map((status) => (
                      <option key={status} value={status}>
                        {status} ({countFor(status)})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="table-responsive">
                <table className="table table-hover align-middle mb-0">
                  <thead>
                    <tr>
                      <th>Student</th>
                      <th>College</th>
                      <th>Applied</th>
                      <th>Resume</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {visible.length === 0 && (
                      <tr>
                        <td colSpan={5} className="text-center text-muted py-4">
                          No {filter.toLowerCase()} applications.
                        </td>
                      </tr>
                    )}
                    {visible.map((application) => (
                      <tr key={application.id}>
                        <td>
                          <Link to={`/company/students/${application.student_id}`} className="fw-semibold">
                            {application.student_name || `Student #${application.student_id}`}
                          </Link>
                          {application.major && (
                            <div className="small text-muted">{application.major}</div>
                          )}
                        </td>
                        <td>{application.college_name || '—'}</td>
                        <td>{formatDate(application.applied_at)}</td>
                        <td>
                          {application.resume_filename ? (
                            <button
                              type="button"
                              className="btn btn-outline-primary btn-sm"
                              onClick={() => handleViewResume(application)}
                              disabled={resumeId === application.id}
                            >
                              {resumeId === application.id ? 'Opening...' : 'View PDF'}
                            </button>
                          ) : (
                            <span className="text-muted">None</span>
                          )}
                        </td>
                        <td>
                          <div className="d-flex align-items-center gap-2">
                            <StatusBadge status={application.status} />
                            <select
                              className="form-select form-select-sm"
                              style={{ width: 'auto' }}
                              aria-label={`Change status for ${application.student_name || 'applicant'}`}
                              value={application.status}
                              onChange={(e) => handleStatusChange(application, e.target.value)}
                              disabled={savingId === application.id}
                            >
                              {APPLICATION_STATUSES.map((status) => (
                                <option key={status} value={status}>
                                  {status}
                                </option>
                              ))}
                            </select>
                            {savingId === application.id && (
                              <span
                                className="spinner-border spinner-border-sm text-secondary"
                                role="status"
                                aria-label="Saving"
                              />
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
