# Assistant traces (0 batch requests)

## Successful trace `trace-ok-6ef88d2d`

failure_mode: None; tool calls: [{'tool': 'search_jobs', 'error': None}]

| Span | Start (ms) | Duration (ms) | Detail |
|---|---:|---:|---|
| memory_store | 13.2 | 0.5 | step=build_context |
| model_inference | 13.9 | 15770.3 | iteration=1 |
| tool_total | 15785.8 | 18.2 | iteration=1, tool=search_jobs |
| model_inference | 15805.0 | 41541.6 | iteration=2 |

## Failed trace `trace-failed-d0427972`

failure_mode: None; tool calls: [{'tool': 'get_job_details', 'error': 'error: job was not found'}]

| Span | Start (ms) | Duration (ms) | Detail |
|---|---:|---:|---|
| memory_store | 5.3 | 0.8 | step=build_context |
| model_inference | 6.7 | 8182.6 | iteration=1 |
| tool_total | 8189.9 | 5.1 | iteration=1, tool=get_job_details |
| model_inference | 8195.3 | 17984.0 | iteration=2 |
