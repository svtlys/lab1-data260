# Assistant load test: results and bottleneck analysis

Setup: JMeter on the same MacBook as the backend (FastAPI, MySQL in Docker) and Ollama (qwen3:8b). Each virtual
student signs in once, then sends a chat message, waits for the answer and repeats (500 ms think time). Runs were
300 s each with a 20 s ramp-up; samples from the ramp-up are left out. JMeter gives up after 180 s, and the backend
gives up on the model after 120 s (`OLLAMA_TIMEOUT_SECONDS`) and then answers HTTP 200 with an "assistant service
error" message. The plan counts that message as a failure, so the Error % below means "no real answer".

## Final results (after the fixes)

| Users | Samples | Real answers | Model timeouts (backend, 120 s) | Client timeouts (JMeter, 180 s) | Failed logins | HTTP 500 | p50 ms | p95 ms |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 5 | 5 | 3 | 1 | 1 | 0/5 | 0 | 117700 | 180013 |
| 10 | 15 | 1 | 12 | 2 | 0/10 | 0 | 120029 | 180013 |
| 20 | 20 | 1 | 17 | 2 | 0/20 | 0 | 120026 | 180003 |
| 50 | 50 | 0 | 34 | 16 | 0/50 | 0 | 124143 | 180003 |

Graph: `docs/loadtest_local_assistant.png`. Raw table: `docs/loadtest_local.md` and `.json`.
Sample counts are small because every sample takes minutes; read the numbers as the shape of the problem, not as
precise percentiles. A single chat on its own took about 30 s in the smoke run (3 requests, mean 32 s, max 65 s).

## Bottleneck 1: the model serializes requests (not fixed, only measured)

Ollama on one laptop handles one generation at a time, so concurrent chats queue behind each other. With a solo
answer time of about 30 s, five users already wait about 100-120 s for their turn, which is at the backend's 120 s
limit. From 10 users on almost every request waits longer than the limit and ends as a timeout, so throughput stays
flat at roughly 0.02-0.2 requests/s while users are added. Adding users does not add throughput; it only adds
waiting. This is the real capacity limit of the assistant on this hardware, and it is the same on AWS unless the
model runs on a GPU instance or on more than one model server.

## Bottleneck 2: the database connection pool (found and fixed)

| Run | Failed logins | HTTP 500 on chat | Cause |
|---|---|---|---|
| Before any fix, 20 users | 3/20 | 38 | each chat kept its database connection during the model call |
| Before any fix, 50 users | 27/50 | (hundreds of 401s from users without a token) | same |
| After releasing the connection before the model call, 50 users | 13/50 | 181 | requests still hold a connection while they wait for a free worker thread |
| After sizing the pool (20 + 60), 5-50 users | 0 | 0 | no pool errors in the backend log |

Two changes were needed. First, `db.rollback()` before each model call so a chat does not hold a connection for
the 30-120 s of the model call (`app/assistant/loop.py`, test in `tests/test_loop_db_release.py`). Second, a larger pool
(`DB_POOL_SIZE=20`, `DB_MAX_OVERFLOW=60`): a FastAPI request keeps its connection from the sign-in check until its
handler gets a worker thread, and with 40 threads busy waiting on the model, about 15 requests sat holding every
connection of the default pool (5 + 10). The backend log showed `QueuePool limit of size 5 overflow 10 reached` at the
exact 30 s timeout. The final run has no such errors and no failed logins at 50 users.

## What the load test also changed in the test plan

- A user whose login failed no longer sends hundreds of 401 requests (an `IfController` skips the chat), and failed
  logins are counted in their own column. The first 50-user run showed 99 % errors mostly because of that.
- A 200 response that only says the model timed out is counted as a failure.

## Options for the model bottleneck (not done)

1. Admission control: answer "busy, try again" immediately when the model queue is full, instead of holding the
   request for 120 s. This keeps the other endpoints responsive and gives users an honest answer.
2. More model capacity: `OLLAMA_NUM_PARALLEL` on a machine with enough memory, a smaller model, or a GPU node on AWS.
3. Streaming the answer so the first words arrive early (the wait feels shorter, throughput is the same).
