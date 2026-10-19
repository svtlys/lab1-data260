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
