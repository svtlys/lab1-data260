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

## Reliability experiment

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

## Live reliability test (real model)

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
