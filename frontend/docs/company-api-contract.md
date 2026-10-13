# Company workflow API contract (v2, Week 3)

Written by Alyssa from the frontend side. Field names now match the real tables in
`database/02_schema.sql` plus `database/05_company_workflow.sql`. Anything marked
**not built yet** has a frontend page waiting for it; until the route exists the page
shows "The backend doesn't have this endpoint yet (GET /api/...)".

If a path or field differs, only `frontend/src/services/companyService.js` (paths) and
`frontend/src/constants.js` (job types, event types, majors) need to change.

## Conventions

- Base URL `http://127.0.0.1:9160`, every path under `/api`, JSON, snake_case.
- `Authorization: Bearer <access_token>` on every route below.
- Errors are `{"detail": "..."}`; validation failures are the normal FastAPI 422.
- The company is **always taken from the token**, never from the request body.
- Return `404` for both "does not exist" and "belongs to another company".

## Endpoints

| Method | Path | Caller | Purpose |
|---|---|---|---|
| GET | `/api/companies/me` | company | Own profile |
| PUT | `/api/companies/me` | company | Update profile |
| POST | `/api/companies/me/jobs` | company | Post a job |
| GET | `/api/companies/me/jobs` | company | Own jobs with `applicant_count`, `pending_count` |
| GET | `/api/companies/me/jobs/{job_id}/applications` | owner | Applicants |
| PUT | `/api/companies/me/applications/{id}/status` | owner | Set status |
| GET | `/api/companies/me/applications/{id}/resume` | owner | Resume PDF |
| GET | `/api/students/{student_id}` | any login | Read a student profile (declare after `/me`) |
| POST | `/api/companies/me/events` | company | Create an event |
| GET | `/api/companies/me/events` | company | Own events with `registered_count` |
| GET | `/api/companies/me/events/{event_id}` | owner | One event |
| GET | `/api/companies/me/events/{event_id}/registrations` | owner | Registered students + eligibility verdict |

## Shapes

### Company profile (GET / PUT `/api/companies/me`)

`id, user_id, company_name, location, description, contact_phone, profile_picture_url`.
(The old `contact_email` is gone: `company_profiles` has no such column. Use the login
email from `users` if you want to show one.)

### Create job (POST `/api/companies/me/jobs`)

```json
{
  "title": "Data Engineering Intern",
  "employment_type": "Internship",
  "city": "Mountain View",
  "is_remote": false,
  "salary_min": 60000,
  "salary_max": 90000,
  "required_skills": "Python, SQL",
  "deadline": "2026-11-15",
  "description": "Work on our data pipelines."
}
```

The server sets `company_id` (token), `company_name` (from the profile), `posted_at`
(now) and `location` (`"<city>, CA"`). `salary_min`, `salary_max`, `required_skills` may be null.
Rules: `employment_type` in `Full-time | Part-time | On-campus | Internship`;
`salary_max >= salary_min` when both are given; `city` in the pair's CITY_SET.

`GET /api/companies/me/jobs` returns the same fields plus `id, posted_at, applicant_count, pending_count`.

### Applications

`GET .../jobs/{job_id}/applications` returns
`id, job_id, student_id, student_name, college_name, major, applied_at, status, resume_filename`.
Status is `Pending | Reviewed | Declined`. `PUT .../status` takes `{"status": "Reviewed"}`.

### Create event (POST `/api/companies/me/events`)

```json
{
  "title": "Resume Workshop",
  "event_type": "Workshop",
  "city": "Cupertino",
  "is_virtual": false,
  "location": "Main hall",
  "event_date": "2026-10-20T15:00:00",
  "capacity": 40,
  "description": "...",
  "eligible_majors": "Computer Science, Data Analytics",
  "min_cgpa": 3.0,
  "min_grad_year": 2027,
  "max_grad_year": null
}
```

The server sets `company_id` and `organizer` (the company name). `eligible_majors` is a
comma-separated string (or null for every major); all `min_*`/`max_*` fields may be null.
`event_type` is one of `Career Fair | Workshop | Info Session | Networking | Hackathon | Panel`.

`GET /api/companies/me/events` returns each event with `id`, the fields above and
`registered_count`.

### Event registrations (GET `.../events/{event_id}/registrations`)

```json
[
  {
    "student_id": 8, "student_name": "Jordan Lee", "college_name": "San Jose State University",
    "major": "Data Analytics", "cgpa": 3.4, "graduation_year": 2027,
    "registered_at": "2026-10-08T14:22:10",
    "eligible": true, "ineligible_reasons": []
  }
]
```

`eligible` / `ineligible_reasons` come from `app/services/eligibility.py::check_eligibility`
(event row, student profile row). Use the same function when a student registers
(reject with `409` or `403` and the reasons joined into `detail`), and in the assistant's
`search_events` tool so all three agree.

## Eligibility rule (one place: `eligibility.py`)

An event is open to everyone unless it sets `eligible_majors` (case-insensitive match),
`min_cgpa`, `min_grad_year` or `max_grad_year` (inclusive). A student missing a value an
event requires is treated as not eligible. Registration also fails if the event date has
passed or `registered_count >= capacity` (`check_registration_open`).
