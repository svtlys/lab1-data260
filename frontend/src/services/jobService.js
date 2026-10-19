import api from './api'

// search jobs using the filters selected by the student
export function searchJobs(filters = {}) {
  const params = Object.fromEntries(
    Object.entries(filters).filter(([, value]) => value !== '' && value !== null),
  )
  return api.get('/api/jobs', { params }).then((res) => res.data)
}

// fetch one job posting
export function getJob(jobId) {
  return api.get(`/api/jobs/${jobId}`).then((res) => res.data)
}

// apply to a job; the resume is an optional PDF file
export function applyToJob(jobId, resumeFile) {
  const form = new FormData()
  if (resumeFile) form.append('resume', resumeFile)
  return api
    .post(`/api/jobs/${jobId}/applications`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    .then((res) => res.data)
}

// applications that belong to the logged-in student
export function getMyApplications() {
  return api.get('/api/students/me/applications').then((res) => res.data)
}
