# Handshake Frontend -- Pair 16

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
  constants.js            job categories, application statuses, CITY_SET (one place to change)
  components/
    Navbar.jsx            role-aware nav bar with a working mobile menu
    ProtectedRoute.jsx     redirects to /login (or the right dashboard) as needed
    FormField.jsx          labelled input/select/textarea with inline validation errors
    StatusBadge.jsx / EmptyState.jsx / LoadingSpinner.jsx / ErrorAlert.jsx   shared UI
  services/
    api.js                 single axios instance: Bearer token, 401 -> forced logout, error messages
    authService.js          signup (student/company), login, logout
    studentService.js       GET/PUT /api/students/me
    companyService.js       company profile, jobs, applicants, status, resume (proposed API)
  utils/
    validation.js          form validators + cleanPayload (blank -> null)
    format.js              date and salary formatting
  pages/
    Home.jsx, Login.jsx, StudentSignup.jsx, CompanySignup.jsx, NotFound.jsx
    StudentDashboard.jsx
    CompanyDashboard.jsx, CompanyProfile.jsx, CreateJob.jsx, MyJobs.jsx,
    JobApplicants.jsx, StudentProfileView.jsx
docs/
  company-api-contract.md  endpoints the company pages expect from the backend
```

## Company workflow routes (Week 2)

| Route | Page |
|---|---|
| `/dashboard/company` | Summary tiles and recent postings |
| `/company/profile` | View and edit company profile |
| `/company/jobs` | Jobs this company posted |
| `/company/jobs/new` | Post a job |
| `/company/jobs/:jobId/applicants` | Applicants, status changes, resume preview |
| `/company/students/:studentId` | Read-only student profile |

All of them are wrapped in `ProtectedRoute role="company"`.

## Auth flow (matches the backend handoff)

1. `POST /api/auth/login` returns `{ access_token, token_type, user }`.
2. Only `access_token` and `user` are stored, in `localStorage`.
3. Every request through `services/api.js` automatically attaches
   `Authorization: Bearer <access_token>`.
4. `user.role` (`student` or `company`) decides which dashboard route
   `ProtectedRoute` and post-login redirects send you to.
5. Logout just clears `localStorage` -- there's no backend logout endpoint
   since this is stateless JWT.

## Known gap: the company API is a proposal

The backend currently has only the auth and student-profile routes. The company
pages are built against the endpoints in `docs/company-api-contract.md`, which
your partner needs to confirm or change. Until a route exists, the page shows
"The backend doesn't have this endpoint yet (GET /api/...)" instead of crashing.
Paths and shapes live in `src/services/companyService.js`; category and status
values live in `src/constants.js`.

## What's still open

- Student workflow pages (job search, filters, apply with resume, application
  status) are your partner's Week 2 work.
- Company events tab and student search (Part A) are not built yet.
- Check in with your partner on the contract's "Decisions to agree on" list.
