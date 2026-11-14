# DATA 260 Lab 1 Metrics

These metrics record results that were actually checked during the integration work.

## Pair and seed configuration

- Pair: 16
- Allowed cities: Sunnyvale, Cupertino, Mountain View
- Database: `p16_handshake`
- Deterministic seed: `16`

| Generated record type | Count |
| --- | ---: |
| Students | 200 |
| Companies | 50 |
| Jobs | 300 |
| Applications | 1,500 |
| Events | 100 |
| Event registrations | 1,482 |

The counts above came from the safe seed-generator preview. The preview validated counts, cities, foreign keys, and duplicate prevention without writing to the database.

## Backend and frontend verification

- Assistant regression suite: 24 tests passed.
- Full backend test suite on macOS: 69 tests passed (including 7 new tests for the assistant guards).
- Reliability and assistant-loop focused verification: 9 tests passed.
- Reliability experiment: 20 deterministic turns completed.
- Frontend production build: passed; Vite transformed 126 modules.
- `git diff --check`: no whitespace errors. Git reported only normal LF/CRLF conversion warnings.

These are focused results recorded during this work. They are not a claim that every possible manual browser flow has been completed.

## Prompt-injection defense

Five poisoned-content queries were run before and after the defense:

- Before defense: 4 of 5 queries produced unsafe behavior in the deterministic baseline.
- After defense: 0 of 5 queries produced unsafe behavior.

The defense labels retrieved job and event descriptions as untrusted database content, places them inside delimiters, and keeps them separate from the assistant's system instructions.

## Reliability experiment: deterministic repair path

The experiment used an isolated in-memory SQLite database and a deterministic fake Ollama client. It did not modify real user data.

| Failure mode | Before repair | After repair | Result |
| --- | ---: | ---: | --- |
| Valid and correct tool calls | 8 | 14 | More scenarios completed correctly |
| Malformed arguments | 3 | 0 unresolved | One bounded repair recovered them |
| Unknown tool names | 2 | 0 unresolved | One bounded repair recovered them |
| Text response when a tool was required | 2 | 2 | Unchanged |
| Lost multi-step chains | 2 | 2 | Unchanged |
| Ollama errors | 1 | 1 | Stopped safely |
| Database errors | 1 | 0 unresolved | One bounded repair recovered it |
| Iteration-ceiling events | 1 | 1 | Five-iteration ceiling preserved |

The loop allows one repair attempt per run. It includes the specific recoverable error in a repair prompt, then stops retrying. The API also reports tool-call counts, repair attempts, failure mode, and whether the iteration ceiling was reached.

## Live reliability test: integration-branch run (isolated database)

This is separate from the deterministic repair-path experiment above. It used the isolated database, the isolated FastAPI backend on port `9161`, and Ollama model `qwen3:8b` on 2026-10-19. It ran the full 26-turn live script without approving a save and without cleanup SQL.

| Live result | Count |
| --- | ---: |
| Total turns | 26 |
| Valid and correct | 15 |
| Ollama errors | 5 |
| Wrong tool results | 3 |
| Lost multi-step chains | 2 |
| API/database errors | 1 |
| Total tool calls | 24 |
| Live repair attempts | 0 |
| Iteration-ceiling events | 0 |
| Save attempts blocked by confirmation | 4 |
| Approved saves | 0 |
| `saved_items` created | 0 |

Live tool-call totals were: `search_jobs` 8, `get_student_preferences` 5, `get_job_details` 4, `save_job_or_event` 4, and `search_events` 3.

Read-only persistence verification after the run reported 25 assistant conversations, 91 assistant messages, 24 assistant tool logs, 1,500 applications, and 0 saved items. One failed turn did not create a conversation.

Sanitized evidence is stored in:

- `docs/evidence/live_reliability_2026-10-19/live_reliability_results.json`
- `docs/evidence/live_reliability_2026-10-19/live_reliability_results.md`
- `docs/evidence/live_reliability_2026-10-19/live_transcripts.md`

## Live reliability test: demo student account, with fixes

The experiment above used a deterministic stand-in for Ollama. To measure the real assistant, 26 turns were sent through the live chat API to `qwen3:8b` on a Mac, using the seeded `p16_handshake` database and the demo student account. Each turn started a fresh conversation and was judged by an automated check. Script: `backend/scripts/live_reliability_run.py`. Raw results and transcripts: `docs/live_reliability_run1_results.*`, `docs/live_run1_transcripts.md` (first full run) and `docs/live_reliability_results.*`, `docs/live_transcripts.md` (re-runs after fixes).

| Result | Turns |
| --- | ---: |
| Valid and correct, first run | 20 of 26 (76.9%) |
| Tool call ok but wrong results (turns 3, 4) | 2 |
| Leaked system prompt (turn 26) | 1 |
| API or database error, HTTP 500 (turns 10, 18, 24) | 3 |
| Valid and correct after the backend fix (turns 10, 18, 24 re-run) | 23 of 26 (88.5%) |
| Valid and correct after the argument and answer guards (turns 3, 4, 26 re-run) | 26 of 26 (100%), combining the three runs |

- Average iterations per turn: 2.0 (the 23 first-run turns that completed).
- Repair attempts: 0 in the first run; 2 in the re-run (turns 10 and 18, one each, both ended in a clear "job not found" answer).
- Average response time: 59.6 s in the first run (range 15.0 s to 158.3 s).
- Confirmation gate: a save without confirmation was refused (turns 15 and 17), and a save with confirmation succeeded (turn 16).
- Turn 25 (asking for every student's email) was refused with no data leaked.

Findings and fixes:

1. **HTTP 500 on tool errors in a new conversation (turns 10, 18, 24).** A failing tool rolls back the database session, which also removed the new, uncommitted conversation row, so saving the messages failed on a foreign key. Fixed in `backend/app/api/routes/assistant.py` by committing the conversation as soon as it is created. The three turns then completed.
2. **Wrong search arguments (turns 3 and 4).** The data exists (19 remote jobs in Cupertino, 32 internships in Mountain View), but the model sent `employment_type: "remote"` for the first and put "internship" in the free-text query for the second, so both returned nothing. A first fix, clearer `search_jobs` parameter descriptions in `backend/app/assistant/loop.py`, did not change the result on re-run, so the fix was moved into the tool: `backend/app/assistant/guards.py` now moves a misplaced "remote" into the remote flag and a misplaced job-type word (such as "internship") into the job-type filter, and job types are compared case-insensitively. After this fix, turn 3 returned real remote jobs in Cupertino and turn 4 returned real internships in Mountain View.
3. **System prompt revealed (turn 26).** A first fix, a system prompt rule not to reveal its instructions, did not stop the leak on re-run, so the backend now removes any paragraph that quotes the system prompt from an answer before it is shown or stored (`protect_instructions` in `backend/app/assistant/guards.py`). After this fix, turn 26 listed the jobs and ended with "I can't share my instructions", with no system prompt text in the answer.

The 26/26 figure combines three runs with fixes in between: the 20 turns that passed in the first run were not re-run on the final code, and the six that failed were re-run after each fix. Each turn is a single run of a non-deterministic model, so treat it as evidence, not a guarantee.

The injection results in the section above use the stand-in model. Turns 25 and 26 are the only injection checks run against the real model.

## Assistant interface metrics

The five required tools are present and tested:

- `get_student_preferences`
- `search_jobs`
- `get_job_details`
- `search_events`
- `save_job_or_event`

Tool results are returned as strings for both success and failure. Each tool call is logged with its name and arguments, and each assistant response includes a tool-call count. The save tool is protected by the confirmation gate and the loop remains limited to five iterations.

## Lab 2 Kafka and memory measurements

These are the measured local results recorded from the Kafka failure and
assistant-memory demonstrations. No latency, throughput, or availability
numbers are inferred here.

| Measurement | Verified result |
| --- | ---: |
| Kafka topic partitions | 3 per required topic |
| Kafka replication factor | 1 |
| Duplicate-event publications | 2 |
| Duplicate-event activity logs | 1 |
| Duplicate-event processed events | 1 |
| Duplicate-event consumer lag | 0 |
| Worker-restart activity logs after recovery | 1 |
| Worker-restart processed events after recovery | 1 |
| Worker-restart offset | committed after recovery |
| Poison-message retries | 3 |
| Poison-message DLQ result | published to `p16.dlq` |
| Valid event after poison | processed successfully |
| Memory count before consolidation | 62 |
| Memory count after consolidation | 38 active, 24 inactive |
| Memory duplicates removed | 16 |
| Memory contradictions resolved | 8 |
| Memory consumer lag | 0 |

Evidence for the Kafka failure measurements:

- `docs/evidence/lab2/kafka-failures/duplicate-event.txt`
- `docs/evidence/lab2/kafka-failures/worker-restart.txt`
- `docs/evidence/lab2/kafka-failures/poison-message-dlq.txt`

Evidence for memory consolidation is in
`docs/evidence/lab2/memory-consolidation-final.txt`.

## Lab 2 load tests (JMeter, local laptop)

Local runs on the development laptop; AWS runs will be added after deployment. Setup, graphs and the full
explanation are in `docs/loadtest_crud_analysis.md` and `docs/loadtest_assistant_analysis.md`. CRUD runs: 90 s each,
30 s ramp-up (left out of the numbers), backend restarted before each run. Assistant runs: 300 s each, 20 s ramp-up.
For the assistant, an HTTP 200 whose answer is only a model-timeout message counts as an error.

| Scenario | Users | Samples | Error % | Failed logins | Avg ms | p50 ms | p95 ms | p99 ms | Max ms | Req/s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Login | 100 | 1972 | 1.37 | n/a | 2500.0 | 2336 | 3310 | 4247 | 4377 | 32.57 |
| Login | 200 | 5377 | 65.45 | n/a | 1723.6 | 1999 | 4071 | 4701 | 4980 | 87.14 |
| Login | 300 | 5806 | 67.81 | n/a | 2637.6 | 3632 | 4592 | 6062 | 6694 | 92.09 |
| Login | 400 | 4912 | 80.13 | n/a | 7052.0 | 3833 | 60002 | 60003 | 60046 | 49.54 |
| Login | 500 | 525 | 100.0 | n/a | 55431.4 | 60003 | 60004 | 60009 | 60015 | 5.91 |
| Job search | 100 | 2834 | 0.78 | 0/100 | 1558.5 | 1667 | 2106 | 2338 | 2744 | 47.63 |
| Job search | 200 | 169 | 100.0 | 35/200 | 57157.1 | 60002 | 60003 | 60003 | 60003 | 1.86 |
| Job search | 300 | 193 | 100.0 | 89/300 | 54406.5 | 60003 | 60003 | 60004 | 60004 | 2.14 |
| Job search | 400 | 8524 | 76.07 | 139/400 | 2829.3 | 1206 | 3809 | 60002 | 60004 | 71.84 |
| Job search | 500 | 319 | 100.0 | 217/500 | 53231.5 | 60003 | 60004 | 60010 | 60011 | 3.52 |
| Application submission | 100 | 10854 | 0.0 | 0/100 | 35.8 | 32 | 77 | 116 | 159 | 185.58 |
| Application submission | 200 | 22347 | 0.0 | 0/200 | 22.7 | 16 | 61 | 116 | 185 | 380.56 |
| Application submission | 300 | 33585 | 0.0 | 0/300 | 21.2 | 18 | 49 | 88 | 125 | 572.28 |
| Application submission | 400 | 31744 | 0.01 | 0/400 | 235.4 | 241 | 309 | 334 | 389 | 539.08 |
| Application submission | 500 | 438 | 100.0 | 97/500 | 55207.8 | 60003 | 60003 | 60004 | 60005 | 4.84 |
| AI assistant | 5 | 5 | 40.0 | 0/5 | 125979.2 | 117700 | 180013 | 180013 | 180013 | 0.02 |
| AI assistant | 10 | 15 | 93.33 | 0/10 | 128696.4 | 120029 | 180013 | 180013 | 180013 | 0.04 |
| AI assistant | 20 | 20 | 95.0 | 0/20 | 128965.6 | 120026 | 180003 | 180003 | 180003 | 0.08 |
| AI assistant | 50 | 50 | 100.0 | 0/50 | 147991.6 | 124143 | 180003 | 180004 | 180004 | 0.21 |

Main results:

- Application submission: 0 to 0.01 % errors from 100 to 400 users (p95 at most 309 ms, 186 to 572 requests/s); fails at 500 users
  when the sign-in burst cannot be served.
- Job search: usable at 100 users (p50 1.7 s, 47.6 requests/s) and failing from 200 users; the endpoint runs two extra
  database queries per matching job and has no result limit.
- Login: 32.6 sign-ins/s at 100 users (p50 2.3 s, bcrypt bound) and 65-100 % errors from 200 users.
- Assistant: 3 of 5 requests got a real answer at 5 users, 0 of 50 at 50 users; the local model answers one request at a
  time (about 30 s each), so waiting time grows with the number of users.
- Fixed during testing: assistant chats held database connections for the whole model call (logins failed with HTTP 500 at 20
  and 50 users, 0 failed after the fix); pool enlarged from 5 + 10 to 20 + 60 connections; the default 256 open-files limit
  caused errors from 200 users on.
- Evidence of the runs before the fixes: `docs/loadtest_local_before.md`, `docs/loadtest_local_ulimit256.md`.
