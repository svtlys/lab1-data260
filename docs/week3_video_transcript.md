# Week 3 video transcript

## Opening

Hi, this is Pair 16 presenting the Week 3 work for our Handshake prototype.
Our goal was to move from the Week 2 authentication and profile foundation
to useful student workflows and a small hand-built AI assistant.

## Event workflow demonstration

First, I log in as a student and open the Events page. The page calls the
FastAPI event search endpoint. I can search by words, choose a city such as
Sunnyvale, choose an event type, and select virtual or in-person events.

When I click View details, the page shows the organizer, description, date,
location, and capacity. When I click Register, the backend creates an event
registration for the logged-in student. The database has a unique constraint,
so the same student cannot register for the same event twice.

The My events page calls the registered-events endpoint and shows the events
that this student has already registered for.

## Assistant demonstration

Next, I open the Assistant page. I can ask a question such as:

> Find remote jobs in Cupertino.

The React page sends the message to the protected assistant endpoint. The
backend loads the student identity from the JWT and sends the request to the
local Ollama model, `qwen3:8b`.

The model can request one of five manually written tools. For this question,
it can call `search_jobs` with a Cupertino and remote filter. The Python tool
queries the jobs table and returns real database results. The assistant then
turns those results into a readable response.

I can also ask for my preferences, search events, request details for a job,
or save a job or event. The tool-call panel on the page shows which tool was
used. This makes the assistant behavior visible instead of hiding it behind
an agent framework.

## History and safety demonstration

The assistant creates a conversation record and stores messages in order.
Tool calls are stored with their arguments, results, and errors. If the model
keeps requesting tools, the loop stops at five iterations and returns a clear
limit message.

## Testing demonstration

The project includes isolated Python tests for event routes, the five required
assistant tools, the assistant loop, and assistant API persistence. The tests
use an in-memory SQLite database, so they do not modify the local MySQL data.

## Closing

Week 3 now connects the student interface, FastAPI routes, SQLAlchemy models,
MySQL data, Ollama, and a manually controlled assistant loop. We kept the
Week 1 and Week 2 authentication functionality in place and did not begin
the Week 4 prompt-injection or reliability features.
