# Assistant latency breakdown: 50 requests (local laptop, qwen3:8b via Ollama)

Source: the console output of `python -m scripts.trace_breakdown --count 50` (50 sequential requests, one new conversation each, ten prompts cycled five times: job searches, event searches, profile lookups and one no-tool question). The run printed total, model, database and tool time per request. The script crashed afterwards on an expired login token before it could write its JSON, so these figures are computed from the printed lines (total and model are rounded to 0.1 s; database and tool times to 0.1 ms). Queue wait is 0 for assistant chats because they are synchronous; memory-store time was not printed per request and is part of the unlisted remainder.

| Stage | Mean (ms) | Median (ms) | p95 (ms) | Share of mean total |
|---|---:|---:|---:|---:|
| total request | 50,902.0 | 49,500.0 | 81,200.0 | 100.00% |
| model inference | 50,858.0 | 49,450.0 | 81,100.0 | 99.91% |
| database queries | 20.6 | 16.5 | 60.0 | 0.04% |
| tool execution (non-SQL) | 6.6 | 4.4 | 19.1 | 0.01% |

**Model inference dominates**: 99.9% of the mean request time (50.9 s of 50.9 s). Database queries average 20.6 ms and tool code 6.6 ms per request, together about 0.05% of the total. The fastest request (18.9 s) was the one with no tool call; requests that call a tool need two model calls, which is why they take 40 to 100 s.

Per request (seconds for total and model, milliseconds for database and tools):

| # | total s | model s | db ms | tools ms |
|---:|---:|---:|---:|---:|
| 1 | 45.6 | 45.6 | 28.7 | 5.9 |
| 2 | 45.9 | 45.9 | 14.4 | 5.1 |
| 3 | 32.2 | 32.2 | 9.5 | 1.6 |
| 4 | 33.3 | 33.3 | 10.8 | 5.0 |
| 5 | 42.3 | 42.3 | 18.9 | 6.5 |
| 6 | 49.1 | 49.1 | 14.5 | 2.8 |
| 7 | 18.9 | 18.9 | 8.0 | 0.0 |
| 8 | 53.9 | 53.9 | 13.6 | 6.1 |
| 9 | 50.2 | 50.1 | 34.4 | 22.7 |
| 10 | 67.0 | 67.0 | 15.4 | 11.8 |
| 11 | 54.0 | 53.9 | 17.5 | 4.7 |
| 12 | 48.5 | 48.4 | 16.5 | 2.4 |
| 13 | 35.5 | 35.5 | 13.0 | 19.1 |
| 14 | 43.5 | 43.4 | 44.1 | 8.7 |
| 15 | 42.9 | 42.8 | 15.7 | 4.8 |
| 16 | 75.6 | 75.6 | 25.6 | 8.9 |
| 17 | 20.2 | 20.1 | 7.9 | 0.0 |
| 18 | 49.3 | 49.3 | 16.1 | 4.8 |
| 19 | 81.2 | 81.1 | 28.0 | 7.7 |
| 20 | 60.4 | 60.3 | 25.8 | 14.0 |
| 21 | 59.9 | 59.8 | 19.8 | 3.2 |
| 22 | 49.7 | 49.6 | 15.7 | 2.7 |
| 23 | 40.4 | 40.3 | 14.4 | 2.0 |
| 24 | 43.2 | 43.2 | 10.8 | 3.0 |
| 25 | 50.6 | 50.5 | 18.5 | 15.6 |
| 26 | 94.3 | 94.2 | 60.0 | 13.5 |
| 27 | 19.4 | 19.4 | 9.5 | 0.0 |
| 28 | 49.9 | 49.9 | 14.9 | 1.8 |
| 29 | 78.1 | 78.0 | 17.5 | 2.9 |
| 30 | 71.2 | 71.2 | 29.5 | 14.5 |
| 31 | 59.6 | 59.5 | 66.3 | 40.7 |
| 32 | 48.0 | 48.0 | 25.0 | 2.5 |
| 33 | 40.9 | 40.9 | 9.3 | 1.6 |
| 34 | 45.8 | 45.7 | 16.9 | 4.0 |
| 35 | 43.6 | 43.6 | 14.7 | 13.6 |
| 36 | 67.1 | 67.1 | 11.2 | 2.9 |
| 37 | 20.4 | 20.3 | 61.2 | 0.0 |
| 38 | 51.8 | 51.8 | 21.0 | 4.5 |
| 39 | 52.1 | 52.0 | 17.1 | 4.1 |
| 40 | 64.0 | 63.9 | 48.1 | 9.7 |
| 41 | 49.7 | 49.7 | 13.0 | 2.6 |
| 42 | 48.5 | 48.5 | 15.2 | 2.4 |
| 43 | 37.2 | 37.2 | 11.6 | 3.2 |
| 44 | 37.2 | 37.2 | 16.5 | 4.5 |
| 45 | 101.5 | 101.5 | 16.9 | 16.9 |
| 46 | 57.8 | 57.7 | 19.1 | 5.1 |
| 47 | 22.2 | 22.2 | 8.1 | 0.0 |
| 48 | 50.8 | 50.8 | 17.6 | 3.3 |
| 49 | 69.9 | 69.8 | 16.5 | 2.7 |
| 50 | 70.8 | 70.7 | 13.4 | 4.3 |
