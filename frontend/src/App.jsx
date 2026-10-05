import React from 'react'
import { Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar.jsx'
import ProtectedRoute from './components/ProtectedRoute.jsx'
import Home from './pages/Home.jsx'
import Login from './pages/Login.jsx'
import StudentSignup from './pages/StudentSignup.jsx'
import CompanySignup from './pages/CompanySignup.jsx'
import StudentDashboard from './pages/StudentDashboard.jsx'
import CompanyDashboard from './pages/CompanyDashboard.jsx'
import CompanyProfile from './pages/CompanyProfile.jsx'
import CreateJob from './pages/CreateJob.jsx'
import MyJobs from './pages/MyJobs.jsx'
import JobApplicants from './pages/JobApplicants.jsx'
import StudentProfileView from './pages/StudentProfileView.jsx'
import NotFound from './pages/NotFound.jsx'

// Pages only a logged-in company may open. Students get sent to their own dashboard.
const companyOnly = (page) => <ProtectedRoute role="company">{page}</ProtectedRoute>

export default function App() {
  return (
    <>
      <Navbar />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />
        <Route path="/signup/student" element={<StudentSignup />} />
        <Route path="/signup/company" element={<CompanySignup />} />

        <Route
          path="/dashboard/student"
          element={
            <ProtectedRoute role="student">
              <StudentDashboard />
            </ProtectedRoute>
          }
        />

        <Route path="/dashboard/company" element={companyOnly(<CompanyDashboard />)} />
        <Route path="/company/profile" element={companyOnly(<CompanyProfile />)} />
        <Route path="/company/jobs" element={companyOnly(<MyJobs />)} />
        <Route path="/company/jobs/new" element={companyOnly(<CreateJob />)} />
        <Route path="/company/jobs/:jobId/applicants" element={companyOnly(<JobApplicants />)} />
        <Route path="/company/students/:studentId" element={companyOnly(<StudentProfileView />)} />

        <Route path="*" element={<NotFound />} />
      </Routes>
    </>
  )
}
