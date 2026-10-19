# Week 3 implementation summary

## Goal

Week 3 extends the Pair 16 Handshake prototype with event discovery,
registration, job search, and a manually built Ollama assistant.

## Student event workflow

Students can:

- search events by text
- filter by city, event type, format, and date range
- view event details
- register for an event
- view their registered events

The backend routes are:

- `GET /api/events`
- `GET /api/events/{event_id}`
- `POST /api/events/{event_id}/register`
- `GET /api/events/registered`

The React pages are `/events` and `/events/registered`.

## Assistant architecture

The assistant is intentionally hand-built. It does not use LangChain,
LlamaIndex, CrewAI, or another agent framework.

The flow is:

1. The student sends a message from the React assistant page.
2. `POST /api/assistant/chat` loads or creates a conversation.
3. `AssistantLoop` sends the conversation and tool definitions to Ollama.
4. The loop executes requested database tools directly.
5. Tool results are sent back to Ollama for a final answer.
6. Messages and tool calls are stored for conversation history and evidence.
7. The loop stops after five iterations.

The five required tools are:

- `get_student_preferences`
- `search_jobs`
- `get_job_details`
- `search_events`
- `save_job_or_event`

Ollama is configured to use the local `qwen3:8b` model.

## Persistence

Week 3 added these tables:

- `events`
- `event_registrations`
- `jobs`
- `saved_items`
- `assistant_conversations`
- `assistant_messages`
- `assistant_tool_logs`

The event and job seed files are repeatable and provide two records in each
Pair 16 city: Sunnyvale, Cupertino, and Mountain View.

## Verification commands

Run these commands from `backend`:

```text
python -m unittest tests.test_events -v
python -m unittest tests.test_assistant_tools -v
python -m unittest tests.test_required_assistant -v
python -m unittest tests.test_assistant_loop -v
python -m unittest tests.test_assistant_api -v
```

The frontend route is `/assistant`. The backend API route is
`POST /api/assistant/chat`.

## Scope boundary

This Week 3 work does not implement Week 4 prompt-injection defenses,
confirmation gates, or reliability experiments.
