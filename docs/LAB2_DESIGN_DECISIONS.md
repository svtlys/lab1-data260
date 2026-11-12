# Lab 2 design decisions (Pair 16)

These choices were fixed up front so that Docker, Kafka, MongoDB, Redux, JMeter and the
assistant work all fit together. PAIR = 16, PORT_BASE = 9160, SEED = 16, prefix = `p16`.
Cities: Sunnyvale, Cupertino, Mountain View.

## 1. Services, ports and names

Six services, each with its own Dockerfile, sharing the Lab 1 code package. Each service has its
own entry point and exposes `GET /health`. A small nginx gateway keeps one base URL for the
frontend, JMeter and tests.

| Service | Container / image / K8s name | Port |
|---|---|---|
| Gateway (nginx, single entry URL) | `p16-gateway` | 9160 |
| Student (auth, student profile, student search) | `p16-student-service` | 9161 |
| Company (company auth and profile, company jobs/events management) | `p16-company-service` | 9162 |
| Job (job search, job details) | `p16-job-service` | 9163 |
| Application (apply, list, status, resumes) | `p16-application-service` | 9164 |
| Event (events, registrations) | `p16-event-service` | 9165 |
| AI Assistant (loop, tools, memory) | `p16-assistant-service` | 9166 |
| Frontend (built React app) | `p16-frontend` | 9167 |

Supporting containers: `p16-mongo` (27017), `p16-kafka` (9092, internal), `p16-zookeeper` or
KRaft mode (Kafka's choice), workers `p16-application-worker`, `p16-event-worker`,
`p16-job-worker`, `p16-notification-worker`, `p16-memory-worker`.

Gateway routing (regex locations, most specific first):
- `/api/jobs/{id}/applications`, `/api/students/me/applications`, `/api/companies/me/jobs/{id}/applications`,
  `/api/companies/me/applications/...` -> application service
- `/api/events`, `/api/companies/me/events` -> event service
- `/api/jobs` -> job service; `/api/companies/me/jobs` (create/list) -> company service
- `/api/assistant` -> assistant service
- `/api/companies` -> company service; `/api/auth`, `/api/students` -> student service

## 2. MongoDB

Database `p16_handshake`. The numeric `id` fields from the MySQL version are kept as each
document's public `id` (a `counters` collection hands out the next id), and documents reference
each other by those ids. This keeps the API responses and the frontend unchanged.

| Collection | Contents |
|---|---|
| `users` | email (unique), bcrypt `password_hash`, role, is_active |
| `sessions` | one per login: `session_id`, user_id, `expires_at` with a TTL index; JWT carries the session id; logout deletes it |
| `student_profiles`, `company_profiles` | profile fields from Lab 1 |
| `jobs`, `events` | postings, with `company_id`; events keep eligibility fields |
| `applications` | job_id, student_id, status, applied_at, resume metadata |
| `resumes` | PDF bytes (5 MB limit) plus filename; stored in Mongo so no volume is needed on Kubernetes |
| `event_registrations`, `saved_items` | as in Lab 1 (saved item has exactly one of job_id/event_id) |
| `activity_logs` | assistant tool-call logs and other activity |
| `assistant_rules` | instruction layer, always injected |
| `student_memory` | one entry per line: `student_id`, ISO `date`, `category`, `text` |
| `conversations` | current conversation: messages embedded, trace_id, token counts |
| `processed_events` | `event_id` unique index, used for idempotent consumers |
| `counters` | next numeric id per collection |

## 3. Kafka

Topics (all prefixed `p16.`): `p16.application.created`, `p16.application.updated`,
`p16.application.status_changed`, `p16.event.registration_created`, `p16.job.created`,
`p16.memory.consolidate`, and the dead-letter topic `p16.dlq`.

| Topic | Producer | Consumer (group) |
|---|---|---|
| application.created / updated | Application API | Application worker (`p16-application-worker`) |
| application.status_changed | Company or Application API | Notification worker (`p16-notification-worker`) |
| event.registration_created | Event API | Event worker (`p16-event-worker`) |
| job.created | Job API | Job worker (`p16-job-worker`) |
| memory.consolidate | Assistant service | Memory worker (`p16-memory-worker`) |

Every message uses this envelope, and the message key is the entity id as a string:

```json
{
  "event_id": "uuid",
  "event_type": "application.created",
  "occurred_at": "2026-11-09T18:00:00Z",
  "trace_id": "uuid",
  "actor": {"user_id": 1, "role": "student"},
  "payload": {"application_id": 12, "job_id": 5, "student_id": 1}
}
```

Rules: consumers disable auto-commit and commit the offset only after the database write;
`event_id` is recorded in `processed_events` (unique) so a duplicate does nothing; a failing
message is retried 3 times, then published to `p16.dlq` and the consumer moves on.

Tracing: every HTTP request gets `X-Trace-Id` (generated if missing). The same `trace_id` goes in
the event envelope and in every log line.

## 4. AWS and Kubernetes naming

- Region: the region of the instructor-assigned cluster; if none is assigned, `us-west-2`.
- EKS cluster: the assigned one, else `p16-eks`.
- Namespace: `p16`. Every Deployment, Service, ConfigMap and Secret is named `p16-...`.
- ECR repositories: `p16-<service>` (one per image), tag `v1`.
- Secrets (Mongo and JWT secrets, API tokens) come from Kubernetes Secrets created with
  `kubectl create secret` and are never committed.
