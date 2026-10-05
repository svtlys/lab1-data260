# Company workflow API contract (proposal)

Written by Alyssa for Week 2, from the frontend side. The backend currently has
only the auth routes and the student profile routes, so every endpoint below is a
**proposal for the backend to confirm or change**. If anything differs, only
`frontend/src/services/companyService.js` (paths and shapes) and
`frontend/src/constants.js` (category and status values) need to change.

## Conventions (same as the existing routes)

- Base URL `http://127.0.0.1:9160`, every path under `/api`.
- JSON, snake_case field names.
- `Authorization: Bearer <access_token>` on every route below.
- Errors use `{"detail": "..."}`; validation failures are the normal FastAPI 422.

## Endpoints

| Method | Path | Who may call it | Purpose |
|---|---|---|---|
| GET | `/api/companies/me` | company | The logged-in company's profile |
| PUT | `/api/companies/me` | company | Update that profile |
| POST | `/api/companies/me/jobs` | company | Create a job posting |
| GET | `/api/companies/me/jobs` | company | List this company's own jobs, with applicant counts |
| GET | `/api/companies/me/jobs/{job_id}/applications` | company that owns the job | List applicants for a job |
| PUT | `/api/companies/me/applications/{application_id}/status` | company that owns the job | Set an application's status |
| GET | `/api/companies/me/applications/{application_id}/resume` | company that owns the job | Return the resume PDF |
| GET | `/api/students/{student_id}` | any logged-in user | Read one student's profile |

Route order: declare `/api/students/me` **before** `/api/students/{student_id}`,
otherwise FastAPI treats "me" as a student id.

## Request and response shapes

### Company profile (GET and PUT `/api/companies/me`)

```json
{
  "id": 1,
  "user_id": 4,
  "company_name": "Acme Robotics",
  "location": "Sunnyvale",
  "description": "We build warehouse robots.",
  "contact_email": "hiring@acme.example",
  "contact_phone": "408-555-0100",
  "profile_picture_url": "https://example.com/logo.png"
}
```

PUT accepts any of `company_name`, `location`, `description`, `contact_email`,
`contact_phone`, `profile_picture_url` and returns the updated profile.

### Create job (POST `/api/companies/me/jobs`)

Request:

```json
{
  "title": "Data Engineering Intern",
  "category": "Internship",
  "location": "Mountain View",
  "salary": 90000,
  "posting_date": "2026-10-05",
  "deadline": "2026-11-15",
  "description": "Work on our data pipelines."
}
```

Response `201`: the created job, same fields plus `id`, `company_id`.

### List own jobs (GET `/api/companies/me/jobs`)

A JSON array. Each job has the fields above plus `id`, `applicant_count`, and
(optional but used by the dashboard) `pending_count`:

```json
[
  {
    "id": 12, "title": "Data Engineering Intern", "category": "Internship",
    "location": "Mountain View", "salary": 90000,
    "posting_date": "2026-10-05", "deadline": "2026-11-15",
    "description": "...", "applicant_count": 7, "pending_count": 4
  }
]
```

### List applicants (GET `/api/companies/me/jobs/{job_id}/applications`)

A JSON array:

```json
[
  {
    "id": 31, "job_id": 12, "student_id": 8,
    "student_name": "Jordan Lee", "college_name": "San Jose State University",
    "major": "Data Analytics",
    "applied_at": "2026-10-06T14:22:10",
    "status": "Pending",
    "resume_filename": "jordan_lee_resume.pdf"
  }
]
```

`resume_filename` is `null` when the student applied without a resume.

### Update status (PUT `/api/companies/me/applications/{application_id}/status`)

Request `{"status": "Reviewed"}`. Response: the updated application (at minimum
`id` and `status`).

### Resume (GET `.../applications/{application_id}/resume`)

Returns the PDF bytes with `Content-Type: application/pdf`. The frontend fetches
it with the Authorization header and opens it as a blob, so a plain link would
not work.

### Student profile (GET `/api/students/{student_id}`)

Same shape as the existing `StudentProfileResponse`. **Please add `email`** (from
the user row): companies need a way to contact a student, and the current
response only has `phone`.

## Authorization rules the backend must enforce

The frontend hides things it shouldn't show, but that is not security.

1. Every `/api/companies/me/...` route rejects non-company users with `403`.
2. Job, applicant, status, and resume routes must check that the job belongs to
   the calling company. Return `404` for both "does not exist" and "belongs to
   someone else" so ids can't be probed.
3. Status must be one of the allowed values (below); anything else is a `422`.
4. A company can never create or edit jobs for another company: take the company
   from the token, never from the request body.

## Validation limits (the frontend already enforces these)

| Field | Rule |
|---|---|
| `title` | required, 2-150 characters |
| `category` | required, one of the categories below |
| `location` | required, 1-150 characters |
| `description` (job) | required, 10-5000 characters |
| `salary` | optional, number from 0 to 10,000,000 |
| `posting_date`, `deadline` | required, `YYYY-MM-DD`, deadline on or after posting date |
| `company_name` | required, 2-150 characters |
| `description` (company) | optional, up to 2000 characters |
| `contact_email` | optional, valid email |
| `contact_phone` | optional, 7-30 characters of digits, spaces, `+ - ( )` |
| `profile_picture_url` | optional, `http(s)` link, up to 500 characters |

## Decisions to agree on

1. **Category values:** `Full-time`, `Part-time`, `On-campus`, `Internship`.
2. **Status values:** `Pending`, `Reviewed`, `Declined`.
3. **Salary:** a number meaning USD per year. This also keeps "higher paying"
   comparisons simple for the Part B assistant's `search_jobs` tool.
4. **Dates:** `YYYY-MM-DD` for job dates, ISO datetime for `applied_at`.
5. **Company contact fields:** the frontend uses `contact_email` and
   `contact_phone`. If the `CompanyProfile` model uses different column names,
   change the `FIELDS` list at the top of `frontend/src/pages/CompanyProfile.jsx`.
