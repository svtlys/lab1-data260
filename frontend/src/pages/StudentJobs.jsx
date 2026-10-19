import React, { useEffect, useState } from 'react'
import * as jobService from '../services/jobService'
import { extractErrorMessage } from '../services/api'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import ErrorAlert from '../components/ErrorAlert.jsx'

const initialFilters = {
  search: '',
  city: '',
  employment_type: '',
  is_remote: '',
}

function formatSalary(job) {
  const { salary_min: min, salary_max: max } = job
  if (min == null && max == null) return 'Not specified'
  const fmt = (n) => Number(n).toLocaleString()
  if (min != null && max != null) return `$${fmt(min)} - $${fmt(max)}`
  return min != null ? `From $${fmt(min)}` : `Up to $${fmt(max)}`
}

export default function StudentJobs() {
  const [filters, setFilters] = useState(initialFilters)
  const [jobs, setJobs] = useState([])
  const [selectedJob, setSelectedJob] = useState(null)
  const [appliedJobIds, setAppliedJobIds] = useState([])
  const [resumeFile, setResumeFile] = useState(null)
  const [loading, setLoading] = useState(true)
  const [applyingId, setApplyingId] = useState(null)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  async function loadJobs(activeFilters = filters) {
    setLoading(true)
    setError('')
    try {
      const data = await jobService.searchJobs(activeFilters)
      setJobs(data)
      setSelectedJob((current) => {
        if (!current) return data[0] || null
        return data.find((job) => job.id === current.id) || data[0] || null
      })
    } catch (err) {
      setError(extractErrorMessage(err, 'Could not load jobs.'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadJobs(initialFilters)
    // remember which jobs this student already applied to
    jobService
      .getMyApplications()
      .then((apps) => setAppliedJobIds(apps.map((app) => app.job_id)))
      .catch(() => {})
  }, [])

  function handleChange(event) {
    setFilters({ ...filters, [event.target.name]: event.target.value })
  }

  function handleSubmit(event) {
    event.preventDefault()
    setMessage('')
    loadJobs(filters)
  }

  function clearFilters() {
    setFilters(initialFilters)
    setMessage('')
    loadJobs(initialFilters)
  }

  function selectJob(job) {
    setSelectedJob(job)
    setResumeFile(null)
    setMessage('')
    setError('')
  }

  function handleResumeChange(event) {
    const file = event.target.files[0] || null
    setError('')
    if (file && !file.name.toLowerCase().endsWith('.pdf')) {
      setResumeFile(null)
      event.target.value = ''
      setError('Resume must be a PDF file.')
      return
    }
    if (file && file.size > 5 * 1024 * 1024) {
      setResumeFile(null)
      event.target.value = ''
      setError('Resume must be 5 MB or smaller.')
      return
    }
    setResumeFile(file)
  }

  async function handleApply(jobId) {
    setApplyingId(jobId)
    setError('')
    setMessage('')
    try {
      await jobService.applyToJob(jobId, resumeFile)
      setAppliedJobIds((current) => [...current, jobId])
      setResumeFile(null)
      setMessage('Application submitted. You can track it under My applications.')
    } catch (err) {
      setError(extractErrorMessage(err, 'Could not submit your application.'))
    } finally {
      setApplyingId(null)
    }
  }

  const alreadyApplied = selectedJob && appliedJobIds.includes(selectedJob.id)

  return (
    <div className="page-container">
      <div className="mb-4">
        <h2 className="mb-1">Find jobs</h2>
        <p className="text-muted mb-0">Search and filter jobs in the Pair 16 city set.</p>
      </div>

      <ErrorAlert message={error} />
      {message && <div className="alert alert-success">{message}</div>}

      <div className="card shadow-sm mb-4">
        <div className="card-body">
          <form onSubmit={handleSubmit} className="row g-3">
            <div className="col-md-4">
              <label className="form-label">Search</label>
              <input
                className="form-control"
                name="search"
                value={filters.search}
                onChange={handleChange}
                placeholder="Title, company, or skill"
              />
            </div>
            <div className="col-md-2">
              <label className="form-label">City</label>
              <select className="form-select" name="city" value={filters.city} onChange={handleChange}>
                <option value="">All cities</option>
                <option value="Sunnyvale">Sunnyvale</option>
                <option value="Cupertino">Cupertino</option>
                <option value="Mountain View">Mountain View</option>
              </select>
            </div>
            <div className="col-md-2">
              <label className="form-label">Job type</label>
              <select
                className="form-select"
                name="employment_type"
                value={filters.employment_type}
                onChange={handleChange}
              >
                <option value="">All types</option>
                <option value="internship">Internship</option>
                <option value="full-time">Full-time</option>
                <option value="part-time">Part-time</option>
              </select>
            </div>
            <div className="col-md-2">
              <label className="form-label">Location</label>
              <select
                className="form-select"
                name="is_remote"
                value={filters.is_remote}
                onChange={handleChange}
              >
                <option value="">Any</option>
                <option value="true">Remote</option>
                <option value="false">On site</option>
              </select>
            </div>
            <div className="col-md-2 d-flex align-items-end gap-2">
              <button type="submit" className="btn btn-primary flex-grow-1">
                Search
              </button>
              <button type="button" className="btn btn-outline-secondary" onClick={clearFilters}>
                Clear
              </button>
            </div>
          </form>
        </div>
      </div>

      {loading && <LoadingSpinner label="Loading jobs..." />}

      {!loading && jobs.length === 0 && (
        <div className="alert alert-info">No jobs matched your filters.</div>
      )}

      {!loading && jobs.length > 0 && (
        <div className="row g-4">
          <div className="col-lg-7">
            <p className="small text-muted">{jobs.length} jobs found</p>
            <div className="row g-3">
              {jobs.map((job) => (
                <div className="col-md-6" key={job.id}>
                  <div
                    className={`card h-100 shadow-sm ${
                      selectedJob && selectedJob.id === job.id ? 'border-primary' : ''
                    }`}
                  >
                    <div className="card-body d-flex flex-column">
                      <div className="mb-2">
                        <span className="badge text-bg-light me-1">{job.employment_type}</span>
                        {job.is_remote && <span className="badge text-bg-info">Remote</span>}
                        {appliedJobIds.includes(job.id) && (
                          <span className="badge text-bg-success ms-1">Applied</span>
                        )}
                      </div>
                      <h5 className="card-title">{job.title}</h5>
                      <p className="small text-muted mb-2">{job.company_name}</p>
                      <p className="small mb-3">{job.city}</p>
                      <button
                        type="button"
                        className="btn btn-outline-primary mt-auto"
                        onClick={() => selectJob(job)}
                      >
                        View details
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="col-lg-5">
            {selectedJob && (
              <div className="card shadow-sm sticky-lg-top" style={{ top: '1rem' }}>
                <div className="card-body">
                  <h4>{selectedJob.title}</h4>
                  <p className="text-muted">{selectedJob.company_name}</p>
                  <p>{selectedJob.description}</p>
                  <dl className="row small">
                    <dt className="col-5">Location</dt>
                    <dd className="col-7">
                      {selectedJob.location} ({selectedJob.city})
                      {selectedJob.is_remote ? ' · Remote' : ''}
                    </dd>
                    <dt className="col-5">Type</dt>
                    <dd className="col-7">{selectedJob.employment_type}</dd>
                    <dt className="col-5">Salary</dt>
                    <dd className="col-7">{formatSalary(selectedJob)}</dd>
                    <dt className="col-5">Skills</dt>
                    <dd className="col-7">{selectedJob.required_skills || 'Not specified'}</dd>
                    <dt className="col-5">Deadline</dt>
                    <dd className="col-7">{selectedJob.deadline || 'None'}</dd>
                  </dl>

                  {!alreadyApplied && (
                    <div className="mb-3">
                      <label className="form-label small" htmlFor="resume">
                        Resume (PDF, up to 5 MB, optional)
                      </label>
                      <input
                        id="resume"
                        type="file"
                        accept="application/pdf,.pdf"
                        className="form-control"
                        onChange={handleResumeChange}
                      />
                    </div>
                  )}

                  <button
                    type="button"
                    className="btn btn-primary w-100"
                    disabled={alreadyApplied || applyingId === selectedJob.id}
                    onClick={() => handleApply(selectedJob.id)}
                  >
                    {alreadyApplied
                      ? 'Applied'
                      : applyingId === selectedJob.id
                        ? 'Submitting...'
                        : 'Apply'}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
