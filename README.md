# DATA 260 Lab 1: Handshake Prototype

This project is the Pair 16 Handshake prototype. It has a FastAPI backend, a React frontend, a MySQL database, JWT authentication, bcrypt password hashing, and a hand-built assistant that can use the local Ollama model.

## Pair configuration

- Pair: 16
- Cities: Sunnyvale, Cupertino, Mountain View
- Database: `p16_handshake`
- Backend address: `http://127.0.0.1:9160`
- Frontend address: `http://localhost:5173`
- Ollama model: `qwen3:8b`

## Requirements

- Python with the existing virtual environment in `backend/.venv`.
- MySQL with the `MySQL80` service running.
- Node.js and npm.
- Ollama with the `qwen3:8b` model available locally.

Local values such as database connection settings belong in `backend/.env`. That file is ignored and must not be committed.

## Start the backend

From PowerShell at the repository root:

```powershell
.\backend\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --app-dir ".\backend" --host 127.0.0.1 --port 9160
```

The health check is `http://127.0.0.1:9160/health`. FastAPI documentation is available at `http://127.0.0.1:9160/docs`.

## Start the frontend

In a second PowerShell window:

```powershell
Set-Location .\frontend
npm.cmd install
npm.cmd run dev
```

The frontend uses Vite and normally opens at `http://localhost:5173`.

## MySQL and Ollama

Start the local `MySQL80` service and confirm that `p16_handshake` exists before using protected features. Start Ollama separately when assistant chat is being tested, and make sure the local `qwen3:8b` model is available. No credentials or tokens are stored in this README.

## Main API route groups

The backend currently includes these protected route groups:

- `/api/auth`: student and company signup, login, and logout.
- `/api/students`: the current student's profile, company-only student search, and individual student lookup.
- `/api/events`: student event search, event details, registration, and registered events.
- `/api/companies`: company profile get/update, profile-picture upload, and safe profile-image retrieval.
- `/api/jobs`: student job browsing and job details.
- `/api/companies/me/jobs`: company job creation and the company's own job list.
- `/api/jobs/{job_id}/applications` and `/api/students/me/applications`: student applications with optional PDF resumes.
- `/api/companies/me/jobs/{job_id}/applications` and `/api/companies/me/applications`: company applicant review, status updates, and resume retrieval.
- `/api/companies/me/events`: company event creation, listing, details, and registration lists.
- `/api/assistant/chat`: authenticated student assistant chat with persisted messages and tool-call logs.

JWT role checks prevent students from using company-only operations and prevent companies from using student-only operations.

## Safe seed preview

The generator is deterministic with `random_state=16`. Run it from the `backend` folder:

```powershell
Set-Location .\backend
.\.venv\Scripts\python.exe scripts\generate_seed_data.py --summary
.\.venv\Scripts\python.exe scripts\generate_seed_data.py --dry-run
```

Both commands are database-safe previews. They do not write rows. The generator creates the verified target counts of 200 students, 50 companies, 300 jobs, 1,500 applications, and 100 events, with cities limited to the Pair 16 city set. Do not use `--reset` on real data without a separate review and explicit confirmation.

The company workflow migration was reviewed and applied earlier in the integration work, and `database/05_company_workflow.sql` is now included in this branch. Do not run it again against the already-migrated database because its `ALTER TABLE` statements are intended to run once. Before using it on a new database, review the file and run it only after the earlier schema files.

For a new local database, the migration command is:

```powershell
mysql -u root -p p16_handshake < .\database\05_company_workflow.sql
```

The password is entered interactively and is not stored in this README.

## Tests and build

From `backend`:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_assistant_loop tests.test_assistant_tools tests.test_assistant_api tests.test_confirmation tests.test_prompt_injection tests.test_required_assistant
.\.venv\Scripts\python.exe -m unittest tests.test_reliability tests.test_assistant_loop
```

The seed generator and reliability experiment also have focused tests. The frontend production build is run from `frontend`:

```powershell
npm.cmd run build
```

The verified build transformed 126 modules and completed successfully.

## Upload safety

Application resumes and company profile images are stored under ignored upload directories. Uploaded resumes are validated as PDF files, and profile images are limited to JPEG, PNG, or WebP files of 2 MB or less. Uploaded files, local environments, and secrets must remain outside Git commits.

## Lab 2 local Kafka and worker verification

The Pair 16 local Kafka broker runs on the internal Docker network as
`p16-kafka:9092`. Start the shared local infrastructure with:

```powershell
docker compose --env-file .\compose.lab2.env -f .\docker-compose.lab2.yml up -d p16-mysql p16-mongo p16-kafka
docker compose --env-file .\compose.lab2.env -f .\docker-compose.lab2.yml ps p16-mysql p16-mongo p16-kafka
```

The required Pair 16 topics are:

- `p16.application.created`
- `p16.application.updated`
- `p16.application.status_changed`
- `p16.event.registration_created`
- `p16.job.created`
- `p16.memory.consolidate`
- `p16.dlq`

The local topic verification used three partitions and replication factor one
for the single-broker environment. Inspect topics without publishing messages:

```powershell
docker exec p16-kafka sh -c '/opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list'
docker exec p16-kafka sh -c '/opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --describe --topic p16.job.created'
docker exec p16-kafka sh -c '/opt/kafka/bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 --list'
docker exec p16-kafka sh -c '/opt/kafka/bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 --describe --group p16-memory-worker'
```

The implemented worker consumer groups are:

- `p16-application-worker` for `application.created` and `application.updated`.
- `p16-event-worker` for `event.registration_created`.
- `p16-job-worker` for `job.created`.
- `p16-notification-worker` for `application.status_changed`.
- `p16-memory-worker` for `memory.consolidate`.

Workers use manual Kafka offsets, `processed_events.event_id` idempotency,
three bounded attempts, and `p16.dlq` for a third failure. A worker can be
run from the existing assistant image for local demonstrations:

```powershell
docker compose --env-file .\compose.lab2.env -f .\docker-compose.split.lab2.yml run --rm --no-deps -e KAFKA_ENABLED=true -e MONGO_READS_ENABLED=true p16-assistant-service python -m app.workers.job_worker
```

The three verified failure demonstrations used temporary isolated consumer
groups and unique demo event IDs. Their sanitized results are recorded in:

- `docs/evidence/lab2/kafka-failures/duplicate-event.txt`
- `docs/evidence/lab2/kafka-failures/worker-restart.txt`
- `docs/evidence/lab2/kafka-failures/poison-message-dlq.txt`

The duplicate demonstration published the same valid event twice and produced
one activity log and one processed-event record. The restart demonstration
left the event uncommitted while the delayed helper was stopped, then recovered
it with the same group. The poison demonstration retried three times, sent the
event to `p16.dlq`, and continued with the following valid event.

The verified assistant-memory demonstration uses the existing memory worker
and the internal broker/database endpoints:

```powershell
docker compose --env-file .\compose.lab2.env -f .\docker-compose.split.lab2.yml run --rm --no-deps -e KAFKA_ENABLED=true -e MONGO_READS_ENABLED=true p16-assistant-service python -m scripts.seed_memory --kafka
```

Its sanitized result is recorded in
`docs/evidence/lab2/memory-consolidation-final.txt`. Use unique local demo
identifiers and inspect the consumer group and Mongo counts after processing.

Secrets must come only from ignored local configuration such as
`compose.lab2.env` or the local backend environment. Never commit environment
files, passwords, JWT secrets, Kafka credentials, Mongo credentials, tokens,
or private uploads.
