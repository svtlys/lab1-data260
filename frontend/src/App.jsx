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
import StudentEvents from './pages/StudentEvents.jsx'
import StudentRegisteredEvents from './pages/StudentRegisteredEvents.jsx'
import AssistantChat from './pages/AssistantChat.jsx'

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
        <Route
          path="/dashboard/company"
          element={
            <ProtectedRoute role="company">
              <CompanyDashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/events"
          element={
            <ProtectedRoute role="student">
              <StudentEvents />
            </ProtectedRoute>
          }
        />
        <Route
          path="/events/registered"
          element={
            <ProtectedRoute role="student">
              <StudentRegisteredEvents />
            </ProtectedRoute>
          }
        />
        <Route
          path="/assistant"
          element={
            <ProtectedRoute role="student">
              <AssistantChat />
            </ProtectedRoute>
          }
        />
      </Routes>
    </>
  )
}
