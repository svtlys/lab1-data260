import React, { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import * as companyService from '../services/companyService'
import { extractErrorMessage } from '../services/api'
import LoadingSpinner from '../components/LoadingSpinner.jsx'
import ErrorAlert from '../components/ErrorAlert.jsx'

const hasValue = (value) => value !== null && value !== undefined && value !== ''

// One label/value row; renders nothing when the student left the field blank.
function Detail({ label, value }) {
  if (!hasValue(value)) return null
  return (
    <>
      <dt className="col-sm-4 text-muted fw-normal">{label}</dt>
      <dd className="col-sm-8">{value}</dd>
    </>
  )
}

// Read-only view of a student's profile, for companies reviewing applicants.
export default function StudentProfileView() {
  const { studentId } = useParams()
  const navigate = useNavigate()
  const [student, setStudent] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError('')
    companyService
      .getApplicantProfile(studentId)
      .then((data) => {
        if (!cancelled) setStudent(data)
      })
      .catch((err) => {
        if (!cancelled) setError(extractErrorMessage(err, 'Could not load this student profile.'))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [studentId])

  const skills = student && student.skills
    ? student.skills.split(',').map((s) => s.trim()).filter(Boolean)
    : []
  const place = student
    ? [student.city, student.state, student.country].filter(Boolean).join(', ')
    : ''

  return (
    <div className="page-container" style={{ maxWidth: 720 }}>
      <button type="button" className="btn btn-link text-decoration-none px-0" onClick={() => navigate(-1)}>
        &larr; Back
      </button>

      {loading && <LoadingSpinner label="Loading student profile..." />}
      <ErrorAlert message={error} />

      {!loading && !error && student && (
        <div className="card shadow-sm mt-2">
          <div className="card-body p-4">
            <div className="d-flex align-items-center gap-3 mb-4">
              {student.profile_picture_url && (
                <img
                  key={student.profile_picture_url}
                  src={student.profile_picture_url}
                  alt=""
                  width="72"
                  height="72"
                  className="rounded-circle border"
                  style={{ objectFit: 'cover' }}
                  onError={(e) => {
                    e.currentTarget.style.display = 'none'
                  }}
                />
              )}
              <div>
                <h2 className="mb-0">{student.full_name}</h2>
                <div className="text-muted">{student.college_name}</div>
              </div>
            </div>

            {student.career_objective && (
              <div className="mb-4">
                <h6 className="text-muted text-uppercase small">Career objective</h6>
                <p className="mb-0">{student.career_objective}</p>
              </div>
            )}

            <dl className="row mb-4">
              <Detail label="Degree" value={student.degree} />
              <Detail label="Major" value={student.major} />
              <Detail label="Graduation year" value={student.graduation_year} />
              <Detail label="CGPA" value={student.cgpa} />
              <Detail label="Location" value={place} />
              <Detail label="Email" value={student.email} />
              <Detail label="Phone" value={student.phone} />
            </dl>

            {skills.length > 0 && (
              <div className="mb-4">
                <h6 className="text-muted text-uppercase small">Skills</h6>
                <div>
                  {skills.map((skill) => (
                    <span key={skill} className="badge rounded-pill bg-light text-dark border me-1 mb-1">
                      {skill}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {student.experience && (
              <div>
                <h6 className="text-muted text-uppercase small">Experience</h6>
                <p className="mb-0" style={{ whiteSpace: 'pre-wrap' }}>
                  {student.experience}
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
