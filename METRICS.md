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

## Assistant interface metrics

The five required tools are present and tested:

- `get_student_preferences`
- `search_jobs`
- `get_job_details`
- `search_events`
- `save_job_or_event`

Tool results are returned as strings for both success and failure. Each tool call is logged with its name and arguments, and each assistant response includes a tool-call count. The save tool is protected by the confirmation gate and the loop remains limited to five iterations.
