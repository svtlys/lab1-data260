# Live reliability run

Run on 2026-10-18 23:02 against the real API, real Ollama model and real MySQL data. 3 assistant turns, one fresh conversation each, as `student1@students.handshake-demo.com`.

## Summary by outcome

| Outcome | Turns |
| --- | ---: |
| valid and correct | 3 |

Turns that needed a repair attempt: 2. Average response time: 49.6 s.

## Confirmation gate

| Turn | Prompt | confirm_save | Gate outcome |
| ---: | --- | --- | --- |
| 18 | Save job 999999 | True | other |

## Every turn

| # | Prompt | Tools called | Iter. | Repairs | Backend failure mode | Outcome | Notes | s |
| ---: | --- | --- | ---: | ---: | --- | --- | --- | ---: |
| 10 | Tell me more about job 999999 | get_job_details | 2 | 1 | none | valid and correct |  | 35.7 |
| 18 | Save job 999999 | save_job_or_event, get_job_details | 3 | 1 | none | valid and correct |  | 50.3 |
| 24 | Find me a job | get_student_preferences, search_jobs | 3 | 0 | none | valid and correct |  | 62.9 |
