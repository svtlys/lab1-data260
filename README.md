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
