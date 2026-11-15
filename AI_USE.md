# AI use

Each question below has two answers, one from Alyssa and one from Vrishin. Lab 1 and Lab 2 answers are kept together.

## 1. How did you use AI?

### Alyssa

I mainly used Claude for debugging and for help with small pieces of React code. Most of my use was pasting terminal errors, failing tests and screenshots to work out what was going wrong, including git merge conflicts, MySQL access errors, missing environment settings, and a “Network Error” in the assistant page that turned out to be Ollama not running. For the frontend, it helped me write and fix parts of the company pages and the assistant chat page, such as the confirmation box that appears when the assistant cancels a save. I also used it for some Week 3 backend pieces (the database migration, seed-data generator and eligibility check) and to draft the live reliability test script. I ran every command myself, tested each change in the running application, and only counted something as working after I saw it work.

For Lab 2 I used Claude for the Redux refactor of the student pages, the agent evaluation harness, token tracking and trace IDs, the assistant memory design, the JMeter plans and the merge of my partner's branch. I ran every git, npm, backend and JMeter command myself, tested the memory and Redux changes by hand in the running app, and only counted something as done after a test, a build or a load-test result showed it worked.

### Vrishin

I used Codex as a development and debugging assistant for the FastAPI backend, MySQL and SQLAlchemy connection, bcrypt authentication, JWT handling, student profile APIs, job and event workflows, assistant tools, and testing documentation. I provided terminal output and manually checked the suggested code in the running application before treating a feature as complete.

## 2. Give an example of an incorrect AI result.

### Alyssa

My first JMeter run of the assistant (20 and 50 users) showed logins failing with HTTP 500 at exactly 30 seconds. Claude diagnosed it as database connection pool exhaustion, because each chat kept its database connection during the model call. It added a rollback before each model call and told me this would remove the failures. That claim was incomplete: when I reran the 50-user test with the backend restarted, 181 chat requests still failed with HTTP 500 at 30 seconds and my backend log still showed `QueuePool limit of size 5 overflow 10 reached`.

A patch Claude gave me for a React page emptied `MyApplications.jsx`. Claude first generated trace IDs as 16 random hex characters, which did not match the UUID `trace_id` in my partner's Kafka event envelope. A "real answers" column that Claude added to the load-test summary guessed from the response time whether the model had answered, and it showed 0 of 100 answers at 50 users.

**Lab 1.** The AI’s output was wrong several times, and testing caught each case. A simple chatbot confirmation box did not appear at first because the code only matched one exact result format, which I noticed from a screenshot of the chat; it was fixed and I retested the full refuse, confirm and save path. A copy step overwrote three of my partner’s files, which I found by diffing against their branch and restored. The company student-search page called a wrong API path, and creating an event with no description failed validation with a 422 error; both showed up while testing and were fixed. Everything else the AI suggested was checked against the real code and command output before it went into the project.

### Vrishin

**Lab 2:** <to be added: one incorrect AI result from Lab 2, in Vrishin's own words>

**Lab 1.** One incorrect result occurred when the assistant produced an empty final response after successfully calling the event-search tool.

### Vrishin — Lab 2 example

Incorrect result: Kafka publishing failed because the producer configuration included `delivery_timeout_ms`, which the installed kafka-python package rejected as unsupported. The memory demonstration failed before the Kafka message was sent.

During reliability testing, the first direct command to run the experiment script was treated as ready to use from the backend folder:

```powershell
.\.venv\Scripts\python.exe scripts\reliability_experiment.py
```

The script initially failed with `ModuleNotFoundError: No module named 'app'`. This showed that the direct script entry point did not yet set the backend import path correctly. The Windows PowerShell `.venv\Scripts\python.exe` workflow is Vrishin's development workflow.

## 3. How was the error detected and corrected?

### Alyssa

**Lab 2.** For the database fix, my 50-user rerun and backend log contradicted the claim. Reading the log again, Claude found a second cause: a request holds its connection while it waits for a free worker thread, so the default pool of 15 connections still ran out. The pool was enlarged to 20 + 60 and made configurable (`DB_POOL_SIZE`, `DB_MAX_OVERFLOW`), and the next run had no pool errors and no failed logins at 5 to 50 users. The first fix (the rollback) is still in the code, but it was not the whole fix. The empty `MyApplications.jsx` was caught by `npm run build` ("default is not exported") and the file was rewritten. The trace-ID format was caught by the unit tests and the IDs became UUIDs. The "real answers" column was caught because it contradicted my backend log, since a chat with two model calls can legitimately take longer than 120 seconds; I removed it, and the JMeter plan now checks the response body for the model-timeout message instead. None of these were accepted from the AI's description alone. Each was found by a failing build, a failing test, a log line or a number that contradicted another measurement.

**Lab 1.** The Lab 1 cases above were each found by testing (a screenshot of the chat, a diff against my partner's branch, errors while using the pages), then fixed and retested.

### Vrishin

**Lab 2:** <to be added: how the Lab 2 example was detected and corrected>

**Lab 1.** I detected the empty-response problem from the Assistant page and the API response, which showed one tool call but an empty answer. I traced it to Ollama returning an empty final message after the tool result. The fix added a clear fallback response stating that no matching events were found, followed by focused regression tests and a frontend build check. I also documented the limitation that the event-search tool does not directly filter by computer-science major.

### Vrishin — Lab 2 example

Detection and correction: I inspected the sanitized producer/worker error output, identified the unsupported configuration option, removed `delivery_timeout_ms` from `backend/app/core/kafka.py`, reran the producer and memory tests, and repeated the demonstration successfully. The final run published to `p16.memory.consolidate`, processed the event, removed duplicates, resolved contradictions, and produced zero consumer lag.

The error appeared in the Python command output before the experiment ran, so no experiment result was accepted from that attempt. The script was corrected to add its backend directory to `sys.path` when run directly. It was then rerun with the deterministic fake Ollama client and isolated SQLite database.

The corrected run completed all 20 turns, reported zero database writes, and produced the before-and-after reliability counts documented in `METRICS.md` and `docs/reliability_experiment.md`.

## 4. What limits did you put on AI assistance?

### Alyssa

The assistant was not treated as proof that a feature worked. A result was recorded only after a command or test produced a checkable result.

In Lab 1 I once pasted my local development database settings, including the password for a throwaway MySQL instance on my own machine, into the chat, and I changed that password afterward.

### Vrishin

AI assistance did not receive or display `backend/.env`, passwords, JWT secrets, complete tokens, uploaded resumes, or private profile images. AI suggestions were checked against the actual source files and test output before being included in the project documentation.
