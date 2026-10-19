import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import * as companyService from '../services/companyService'
import { extractErrorMessage } from '../services/api'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import ErrorAlert from '../components/ErrorAlert.jsx'
import EmptyState from '../components/EmptyState.jsx'

const EMPTY_FILTERS = {
  name: '',
  college: '',
  major: '',
  skills: '',
}

const locationFor = (student) => [student.city, student.state].filter(Boolean).join(', ')

export default function StudentSearch() {
  const [filters, setFilters] = useState(EMPTY_FILTERS)
  const [students, setStudents] = useState([])
  const [loading, setLoading] = useState(true)
  const [searched, setSearched] = useState(false)
  const [error, setError] = useState('')

  async function loadStudents(nextFilters) {
    setLoading(true)
    setError('')
    try {
      const results = await companyService.searchStudents(nextFilters)
      setStudents(results)
      setSearched(true)
    } catch (err) {
      setError(extractErrorMessage(err, 'Could not search students.'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadStudents({})
  }, [])

  function updateFilter(event) {
    const { name, value } = event.target
    setFilters((current) => ({ ...current, [name]: value }))
  }

  function handleSubmit(event) {
    event.preventDefault()
    loadStudents(filters)
  }

  function handleClear() {
    setFilters(EMPTY_FILTERS)
    loadStudents({})
  }

  return (
    <div className="page-container">
      <div className="mb-4">
        <h2 className="mb-1">Find students</h2>
        <p className="text-muted mb-0">Search by name, college, major, or skills.</p>
      </div>

      <form className="card shadow-sm mb-4" onSubmit={handleSubmit}>
        <div className="card-body">
          <div className="row g-3">
            <div className="col-md-6">
              <label className="form-label" htmlFor="student-search-name">Name</label>
              <input
                id="student-search-name"
                className="form-control"
                name="name"
                value={filters.name}
                onChange={updateFilter}
                placeholder="Search by name"
              />
            </div>
            <div className="col-md-6">
              <label className="form-label" htmlFor="student-search-college">College</label>
              <input
                id="student-search-college"
                className="form-control"
                name="college"
                value={filters.college}
                onChange={updateFilter}
                placeholder="Search by college"
              />
            </div>
            <div className="col-md-6">
              <label className="form-label" htmlFor="student-search-major">Major</label>
              <input
                id="student-search-major"
                className="form-control"
                name="major"
                value={filters.major}
                onChange={updateFilter}
                placeholder="Search by major"
              />
            </div>
            <div className="col-md-6">
              <label className="form-label" htmlFor="student-search-skills">Skills</label>
              <input
                id="student-search-skills"
                className="form-control"
                name="skills"
                value={filters.skills}
                onChange={updateFilter}
                placeholder="Search by skill"
              />
            </div>
          </div>
          <div className="d-flex gap-2 mt-3">
            <button type="submit" className="btn btn-primary" disabled={loading}>
              Search
            </button>
            <button type="button" className="btn btn-outline-secondary" onClick={handleClear} disabled={loading}>
              Clear
            </button>
          </div>
        </div>
      </form>

      {loading && <LoadingSpinner label="Searching students..." />}
      <ErrorAlert message={error} />

      {!loading && !error && searched && students.length === 0 && (
        <EmptyState
          title="No students found"
          message="Try a different name, college, major, or skill."
        />
      )}

      {!loading && !error && students.length > 0 && (
        <div className="card shadow-sm">
          <div className="table-responsive">
            <table className="table table-hover align-middle mb-0">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>College</th>
                  <th>Major</th>
                  <th>Skills</th>
                  <th>Location</th>
                </tr>
              </thead>
              <tbody>
                {students.map((student) => (
                  <tr key={student.id}>
                    <td>
                      <Link to={`/company/students/${student.id}`} className="fw-semibold">
                        {student.full_name}
                      </Link>
                    </td>
                    <td>{student.college_name}</td>
                    <td>{student.major || '—'}</td>
                    <td>{student.skills || '—'}</td>
                    <td>{locationFor(student) || '—'}</td>
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
