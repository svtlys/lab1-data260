import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import * as companyService from '../services/companyService'
import { extractErrorMessage } from '../services/api'
import { formatDate, todayISO } from '../utils/format'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import ErrorAlert from '../components/ErrorAlert.jsx'
import EmptyState from '../components/EmptyState.jsx'

// A headline number with a quiet label. Plain ink on purpose: colour is saved
// for things that carry meaning (status badges), not for decoration.
function StatTile({ label, value }) {
  return (
    <div className="col-6 col-md-3">
      <div className="card shadow-sm h-100">
        <div className="card-body">
          <div className="text-muted small">{label}</div>
          <div className="display-6 fw-semibold">{value}</div>
        </div>
      </div>
    </div>
  )
}

export default function CompanyDashboard() {
  const [profile, setProfile] = useState(null)
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)
  const [profileError, setProfileError] = useState('')
  const [jobsError, setJobsError] = useState('')

  useEffect(() => {
    let cancelled = false

    async function load() {
      // Load both at once; if one fails the other still shows.
      const [profileResult, jobsResult] = await Promise.allSettled([
        companyService.getMyCompanyProfile(),
        companyService.getMyJobs(),
      ])
      if (cancelled) return

      if (profileResult.status === 'fulfilled') {
        setProfile(profileResult.value)
      } else {
        setProfileError(extractErrorMessage(profileResult.reason, 'Could not load your company profile.'))
      }
      if (jobsResult.status === 'fulfilled') {
        setJobs(jobsResult.value)
      } else {
        setJobsError(extractErrorMessage(jobsResult.reason, 'Could not load your job postings.'))
      }
      setLoading(false)
    }

    load()
    return () => {
      cancelled = true
    }
  }, [])

  const today = todayISO()
  const activeCount = jobs.filter((j) => j.deadline && j.deadline >= today).length
  const totalApplicants = jobs.reduce((sum, j) => sum + (Number(j.applicant_count) || 0), 0)
  const awaitingReview = jobs.reduce((sum, j) => sum + (Number(j.pending_count) || 0), 0)
  // Only show the "awaiting review" tile if the backend sends pending counts at all.
  const hasPendingCounts = jobs.some((j) => typeof j.pending_count === 'number')
  const recent = [...jobs].sort((a, b) => (b.id || 0) - (a.id || 0)).slice(0, 5)

  return (
    <div className="page-container">
      <div className="mb-4">
        <h2 className="mb-1">{profile && profile.company_name ? profile.company_name : 'Company dashboard'}</h2>
        {profile && profile.location && <div className="text-muted">{profile.location}</div>}
      </div>

      {loading && <LoadingSpinner label="Loading your dashboard..." />}
      <ErrorAlert message={profileError} />

      {!loading && (
        <>
          <ErrorAlert message={jobsError} />

          {!jobsError && (
            <div className="row g-3 mb-4">
              <StatTile label="Active postings" value={activeCount} />
              <StatTile label="Total postings" value={jobs.length} />
              <StatTile label="Total applicants" value={totalApplicants} />
              {hasPendingCounts && <StatTile label="Awaiting review" value={awaitingReview} />}
            </div>
          )}

          <div className="d-flex flex-wrap gap-2 mb-4">
            <Link to="/company/jobs/new" className="btn btn-primary">
              Post a job
            </Link>
            <Link to="/company/jobs" className="btn btn-outline-primary">
              All my jobs
            </Link>
            <Link to="/company/profile" className="btn btn-outline-primary">
              Edit company profile
            </Link>
          </div>

          {!jobsError && (
            <div className="card shadow-sm">
              <div className="card-body pb-0">
                <h5 className="mb-0">Recent postings</h5>
              </div>
              {recent.length === 0 ? (
                <EmptyState
                  title="No job postings yet"
                  message="Post a job to start receiving applications."
                />
              ) : (
                <ul className="list-group list-group-flush mt-3">
                  {recent.map((job) => (
                    <li
                      key={job.id}
                      className="list-group-item d-flex flex-wrap justify-content-between align-items-center gap-2"
                    >
                      <div>
                        <Link to={`/company/jobs/${job.id}/applicants`} className="fw-semibold">
                          {job.title}
                        </Link>
                        <div className="small text-muted">
                          {job.category} &middot; {job.location} &middot; Deadline {formatDate(job.deadline)}
                        </div>
                      </div>
                      <div className="text-muted">
                        {job.applicant_count ?? 0} applicant{(job.applicant_count ?? 0) === 1 ? '' : 's'}
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </>
      )}
    </div>
  )
}
