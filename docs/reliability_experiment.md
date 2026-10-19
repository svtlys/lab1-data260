# Assistant reliability experiment

## Method

The experiment ran 20 deterministic assistant turns against isolated in-memory
SQLite databases. It did not connect to MySQL, Ollama, or any real user data.
The scenarios used a fake Ollama client so each failure mode could be reproduced
and measured consistently.

The comparison used:

- Before repair: `max_repair_attempts=0`.
- After repair: the default `max_repair_attempts=1`.
- The existing assistant ceiling remained five iterations.

The 20 turns contained 8 valid calls, 3 malformed-argument cases, 2 unknown
tools, 2 text-only replies, 2 lost multi-step chains, 1 Ollama error, 1 database
error, and 1 iteration-ceiling case.

## Repair path

When a recoverable tool error begins with `error:`, the loop:

1. records the exact error in the tool-call trace;
2. appends one repair request containing that specific error;
3. gives the model one opportunity to correct the call;
4. stops issuing repair requests after that one attempt.

Confirmation cancellations are not retried. Ollama errors are classified and
returned as service errors. The five-iteration ceiling still stops repeated
tool calls even when repair cannot recover the run.

## Results

| Failure mode | Before repair | After repair | Example | Final outcome |
|---|---:|---:|---|---|
| Valid and correct tool calls | 8 | 14 | `search_jobs` with valid city arguments | Repaired calls became valid; successful |
| Malformed arguments | 3 | 0 unresolved | invalid JSON tool arguments | Recovered by one reprompt |
| Unknown tool names | 2 | 0 unresolved | `unknown_tool` | Recovered by one reprompt |
| Text response when a tool call was required | 2 | 2 | text answer without a tool call | Unchanged; requires model behavior improvement |
| Lost multi-step chains | 2 | 2 | preferences call followed by no job search | Unchanged; requires chain-planning improvement |
| Ollama errors | 1 | 1 | simulated Ollama timeout | Returned bounded service error |
| Database errors | 1 | 0 unresolved | simulated database error | Recovered by one reprompt |
| Iteration-ceiling events | 1 | 1 | repeated tool calls for five iterations | Correctly stopped at the ceiling |

The repair path attempted exactly once per recoverable failure and did not retry
forever. The measured recoverable failures decreased from 6 unresolved cases to
0. Text-only replies, lost chains, Ollama errors, and ceiling events were not
claimed as improved.

## Reproduce

From the `backend` folder:

```powershell
.\.venv\Scripts\python.exe scripts\reliability_experiment.py
.\.venv\Scripts\python.exe -m unittest tests.test_reliability
```

The experiment prints the before/after counts and reports `database writes: 0`.
Focused repair behavior is also covered by
`backend/tests/test_assistant_loop.py`.
