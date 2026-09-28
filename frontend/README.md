# Handshake Frontend -- Pair 16 (9/28/26)

React frontend for the Lab 1 Handshake platform. Built against the Week 1
backend handoff from your partner.

## Pair configuration

| Parameter | Value |
|---|---|
| PAIR | 16 |
| PORT_BASE | 9160 |
| Backend URL | http://127.0.0.1:9160 |
| Swagger docs | http://127.0.0.1:9160/docs |
| Frontend port | 5173 (Vite default) or 3000 -- backend CORS allows both |
| SEED | 16 (fill in CITY_SET from Canvas in the shared README) |

## Setup

```bash
cd frontend    # or wherever this folder lives in the repo
npm install
cp .env.example .env   # adjust VITE_API_BASE_URL if your backend port differs
npm run dev
```

Make sure the backend is running first:

```bash
python -m uvicorn app.main:app --app-dir ".\backend" --host 127.0.0.1 --port 9160
```

## Structure

```
src/
  main.jsx              entry point, wraps the app in AuthProvider + BrowserRouter
  App.jsx                route table
  context/AuthContext.jsx  holds the logged-in user + token, backed by localStorage
  components/
    Navbar.jsx            role-aware nav bar
    ProtectedRoute.jsx     redirects to /login (or the right dashboard) as needed
    LoadingSpinner.jsx / ErrorAlert.jsx   shared loading/error UI
  services/
    api.js                 single axios instance: attaches Bearer token, extracts error messages
    authService.js          signup (student/company), login, logout
    studentService.js       GET/PUT /api/students/me
    companyService.js       GET/PUT /api/companies/me (see note below)
  pages/
    Home.jsx, Login.jsx, StudentSignup.jsx, CompanySignup.jsx
    StudentDashboard.jsx, CompanyDashboard.jsx
```

## Auth flow (matches the backend handoff)

1. `POST /api/auth/login` returns `{ access_token, token_type, user }`.
2. Only `access_token` and `user` are stored, in `localStorage`.
3. Every request through `services/api.js` automatically attaches
   `Authorization: Bearer <access_token>`.
4. `user.role` (`student` or `company`) decides which dashboard route
   `ProtectedRoute` and post-login redirects send you to.
5. Logout just clears `localStorage` -- there's no backend logout endpoint
   since this is stateless JWT.

## Known gap: company profile endpoint

The Week 1 backend handoff only documents student profile endpoints
(`GET`/`PUT /api/students/me`). `CompanyDashboard.jsx` and
`companyService.js` assume a matching `/api/companies/me` pair so the page
has something to render, and the dashboard shows a plain warning banner
if that route 404s instead of crashing. Confirm the actual path and field
names with your partner before Part A grading, and update
`companyService.js` if it differs.

## What's still open for Week 1

- Wire in job search / event pages once those backend routes exist.
- Company job-posting dashboard views (Part A company features beyond auth).
- Swap the placeholder Bootstrap styling for whatever layout you settle on
  as a pair.
