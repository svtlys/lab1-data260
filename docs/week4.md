# Week 4 and Part B/C Backend Work

This document summarizes the backend work verified for the company workflow, assistant safety, and reliability requirements. The implementation preserves the existing student authentication, student event workflow, job workflow, and assistant persistence.

## Company profile pictures

Companies can upload a profile picture through:

- `POST /api/companies/me/profile-picture`
- `GET /api/companies/profile-images/{filename}`

The existing URL-based profile update remains available through `PUT /api/companies/me`. Uploads are restricted to JPEG, PNG, and WebP content, require a matching filename extension and file signature, and are limited to 2 MB. Files are stored under the ignored `backend/uploads/profile_images/` directory with generated filenames. The upload route uses the company JWT role check and updates `profile_picture_url`.

## Company student search

Company users can search students through:

`GET /api/students/search?name=...&college=...&major=...&skills=...`

All supplied filters are combined. The response is a sanitized student profile containing the allowed profile fields needed for recruiting, including the student id, name, college, major, and skills. It does not include student email. The route requires a company role. The existing individual lookup route, `GET /api/students/{student_id}`, remains available with its existing authorization behavior.

## Seed generator

The repeatable generator is at `backend/scripts/generate_seed_data.py`. It uses seed 16 and validates:

- 200 students
- 50 companies
- 300 jobs
- 1,500 applications
- 100 events
- cities limited to Sunnyvale, Cupertino, and Mountain View
- foreign-key and duplicate checks

Use these safe previews from the `backend` folder:

```powershell
.\.venv\Scripts\python.exe scripts\generate_seed_data.py --summary
.\.venv\Scripts\python.exe scripts\generate_seed_data.py --dry-run
```

The verified preview also reported 1,482 event registrations. It did not write to the database. The generator supports reset behavior only behind explicit flags; `--reset` was not used for the verified preview.

## Confirmation gate

`backend/app/assistant/confirmation.py` contains:

`confirm_action(tool_name, arguments, auto_approve=False)`

Read-only tools do not require confirmation. `save_job_or_event` requires explicit student confirmation. A refusal returns a cancellation string, is acknowledged by the assistant, and is not automatically retried. Focused confirmation tests passed as part of the assistant regression suite.

## Prompt-injection defense

Retrieved job and event descriptions are treated as untrusted database content. The assistant loop places retrieved content inside clear delimiters and labels it as untrusted. System instructions remain separate, so a description cannot override the assistant rules, promote itself through instructions, or request another student's private data.

Five poisoned-content queries were run before and after the defense:

- Before: 4 of 5 were unsafe in the deterministic baseline.
- After: 0 of 5 were unsafe.

The focused automated tests are in `backend/tests/test_prompt_injection.py`. Detailed evidence is in `docs/prompt_injection_before_after.md`.

## Assistant interface and logging

The required hand-built tools are:

- `get_student_preferences`
- `search_jobs`
- `get_job_details`
- `search_events`
- `save_job_or_event`

Each tool returns a string for success and failure. The loop logs one line per tool call with the tool name and arguments, records the tool-call count, and persists tool-call data. The API exposes the count and repair metadata. `OllamaClient.complete(messages, tools)` is available while the older `chat()` method remains compatible. The loop still stops after five iterations.

## Reliability experiment: deterministic repair path

The reliability experiment is at `backend/scripts/reliability_experiment.py`. It used a deterministic fake Ollama client and isolated in-memory SQLite, so it did not change real user data. It ran 20 assistant turns and classified valid calls, malformed arguments, unknown tools, text-only responses, lost chains, Ollama errors, database errors, and iteration-ceiling events.

The repair path identifies a recoverable error, reprompts once with that error, and stops after the one-attempt budget. The measured results were:

| Failure mode | Before | After | Final outcome |
| --- | ---: | ---: | --- |
| Valid and correct tool calls | 8 | 14 | Improved |
| Malformed arguments | 3 | 0 unresolved | Repaired |
| Unknown tool names | 2 | 0 unresolved | Repaired |
| Text responses when a tool was required | 2 | 2 | Not repaired |
| Lost multi-step chains | 2 | 2 | Not repaired |
| Ollama errors | 1 | 1 | Safely stopped |
| Database errors | 1 | 0 unresolved | Repaired |
| Iteration-ceiling events | 1 | 1 | Preserved |

The reliability tests are in `backend/tests/test_reliability.py`, and the full experiment notes are in `docs/reliability_experiment.md`.

## Live reliability evidence

The live run is separate from the deterministic repair-path experiment above. On 2026-10-19, the 26-turn script used the isolated FastAPI backend at `http://127.0.0.1:9161`, the isolated database `p16_handshake_reliability`, and Ollama `qwen3:8b`.

No save was approved and no cleanup SQL ran. The results were:

| Classification | Count |
| --- | ---: |
| Total turns | 26 |
| Valid and correct | 15 |
| Ollama errors | 5 |
| Wrong tool results | 3 |
| Lost multi-step chains | 2 |
| API/database error | 1 |
| Total tool calls | 24 |
| Live repair attempts | 0 |
| Iteration-ceiling events | 0 |
| Save attempts blocked by confirmation | 4 |
| Approved saves | 0 |
| `saved_items` created | 0 |

Tool-call totals:

- `search_jobs`: 8
- `get_student_preferences`: 5
- `get_job_details`: 4
- `save_job_or_event`: 4
- `search_events`: 3

Read-only database verification after the run reported 25 assistant conversations, 91 assistant messages, 24 assistant tool logs, 1,500 applications, and 0 saved items. One failed turn did not create a conversation.

Sanitized evidence files:

- `docs/evidence/live_reliability_2026-10-19/live_reliability_results.json`
- `docs/evidence/live_reliability_2026-10-19/live_reliability_results.md`
- `docs/evidence/live_reliability_2026-10-19/live_transcripts.md`

## Route and test summary

The Week 4 backend route groups include:

- company profile and profile-picture routes under `/api/companies`;
- company jobs under `/api/companies/me/jobs` and student browsing under `/api/jobs`;
- student applications under `/api/jobs/{job_id}/applications` and `/api/students/me/applications`;
- company applicant review under `/api/companies/me/jobs/{job_id}/applications` and `/api/companies/me/applications`;
- company events under `/api/companies/me/events`;
- company-only student search under `/api/students/search`.

The verified assistant regression command passed 24 tests. The final reliability and assistant-loop focused command passed 9 tests. The frontend production build also passed and transformed 126 modules.

## Known limitations

- The reliability experiment used deterministic fakes and isolated SQLite; it is evidence of bounded behavior, not a substitute for a live Ollama load test.
- The documented test results are focused results recorded during this work. They do not claim that every manual browser flow or every possible database state was tested.
- `database/05_company_workflow.sql` is now included in the branch and matches the already-applied schema. It must not be rerun against the current database because the `ALTER TABLE` statements are intended to run once.
- Frontend finishing touches and final report formatting remain outside this backend handoff.
