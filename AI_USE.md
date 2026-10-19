# AI Use in the DATA 260 Lab 1 Project

AI assistance was used as a development partner for inspecting the repository, explaining unfamiliar code, proposing small changes, writing focused tests, and checking the results. The student reviewed the changes, ran the commands, and kept secrets and private uploads out of the work.

The assistant was not treated as proof that a feature worked. A result was recorded only after a command or test produced a checkable result.

## Example of an incorrect assistant suggestion

During reliability testing, the first direct command to run the experiment script was treated as ready to use from the backend folder:

```powershell
.\.venv\Scripts\python.exe scripts\reliability_experiment.py
```

The script initially failed with `ModuleNotFoundError: No module named 'app'`. This showed that the direct script entry point did not yet set the backend import path correctly.

## How the error was detected and corrected

The error appeared in the Python command output before the experiment ran, so no experiment result was accepted from that attempt. The script was corrected to add its backend directory to `sys.path` when run directly. It was then rerun with the deterministic fake Ollama client and isolated SQLite database.

The corrected run completed all 20 turns, reported zero database writes, and produced the before-and-after reliability counts documented in `METRICS.md` and `docs/reliability_experiment.md`.

## Limits on AI assistance

AI assistance did not receive or display `backend/.env`, passwords, JWT secrets, complete tokens, uploaded resumes, or private profile images. AI suggestions were checked against the actual source files and test output before being included in the project documentation.
## Vrishin’s Contribution

I used Codex as a development and debugging assistant for the FastAPI backend, MySQL and SQLAlchemy connection, bcrypt authentication, JWT handling, student profile APIs, job and event workflows, assistant tools, and testing documentation. I provided terminal output and manually checked the suggested code in the running application before treating a feature as complete.

One incorrect result occurred when the assistant produced an empty final response after successfully calling the event-search tool. I detected the problem from the Assistant page and the API response, which showed one tool call but an empty answer. I traced the issue to Ollama returning an empty final message after the tool result. The fix added a clear fallback response stating that no matching events were found, followed by focused regression tests and a frontend build check. I also documented the limitation that the event-search tool does not directly filter by computer-science major.