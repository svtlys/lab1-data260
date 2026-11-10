# Function reference (Pair 16 Handshake)

Generated from the source code. Descriptions come from each function's docstring (Python) or the comment above it (JavaScript); functions without one were described from reading the code.


## Backend: API routes (HTTP endpoints)


### `backend/app/api/routes/applications.py`

- `application_row(application, job, student)` - convert joined database objects into a safe response dictionary.
- `read_pdf_resume(resume)` - validate and store an optional PDF resume outside tracked source files.
- `apply_to_job(job_id, resume, current_user, db)` - create one application for the logged-in student.
- `get_my_applications(current_user, db)` - return only applications owned by the logged-in student.
- `get_job_applications(job_id, current_user, db)` - return applicants only for a job owned by the company.
- `_update_application_status(application_id, request, current_user, db)` - update status only for an application on the company's job.
- `update_application_status(application_id, request, current_user, db)` - update an application through the required patch route.
- `update_application_status_legacy(application_id, request, current_user, db)` - support the integrated frontend's existing put request.
- `get_application_resume(application_id, current_user, db)` - return a PDF resume only to the job-owning company.

### `backend/app/api/routes/assistant.py`

- `find_student_profile(current_user, db)` - find the profile belonging to the logged-in student.
- `load_history(conversation_id, db)` - load prior messages in the format expected by the assistant loop.
- `next_sequence_number(conversation_id, db)` - return the next ordered message number for a conversation.
- `normalize_json_value(value)` - convert tool metadata into JSON-compatible values.
- `chat_with_assistant(request, current_user, db)` - run one bounded assistant turn and persist its conversation trace.

### `backend/app/api/routes/auth.py`

- `student_signup(request, db)` - create a student user and an empty student profile.
- `company_signup(request, db)` - create a company user and a company profile.
- `login(request, db)` - verify credentials and return a JWT access token.
- `logout()` - complete client-side logout.

### `backend/app/api/routes/company.py`

- `find_company_profile(current_user, db)` - find the profile belonging to the logged-in company.
- `get_my_company_profile(current_user, db)` - return the logged-in company's profile.
- `update_my_company_profile(request, current_user, db)` - update only the company profile fields sent by the company.
- `read_profile_image(image)` - validate one image and return its bytes and safe extension.
- `upload_company_profile_picture(request, image, current_user, db)` - store a profile image for the logged-in company.
- `get_company_profile_picture(filename)` - return a stored company logo by its generated filename.

### `backend/app/api/routes/company_events.py`

- `event_response(event, registered_count)` - build a response with the count expected by the frontend.
- `count_registrations(event_id, db)` - count registrations without loading every student row.
- `find_owned_event(event_id, current_user, db)` - find an event only when it belongs to the logged-in company.
- `create_company_event(request, current_user, db)` - create an event owned by the logged-in company.
- `get_my_company_events(current_user, db)` - return only events owned by the logged-in company.
- `get_my_company_event(event_id, current_user, db)` - return one event only when it belongs to the logged-in company.
- `get_event_registrations(event_id, current_user, db)` - return registered students and their eligibility results.

### `backend/app/api/routes/events.py`

- `find_student_profile(current_user, db)` - find the profile belonging to the logged-in student.
- `search_events(city, event_type, is_virtual, start_date, end_date, search, current_user, db)` - search events using optional filters for the logged-in student.
- `get_registered_events(current_user, db)` - return all events registered by the logged-in student.
- `get_event_details(event_id, current_user, db)` - return details for one event.
- `register_for_event(event_id, current_user, db)` - register the logged-in student for one event.

### `backend/app/api/routes/jobs.py`

- `job_response(job, db)` - add applicant counts without exposing application records.
- `create_job(request, current_user, db)` - create a job owned by the logged-in company.
- `get_my_jobs(current_user, db)` - return only jobs owned by the logged-in company.
- `search_jobs(search, city, employment_type, is_remote, current_user, db)` - search all job postings as a logged-in student.
- `get_job_details(job_id, current_user, db)` - return one job posting to a logged-in student.

### `backend/app/api/routes/student_profile.py`

- `find_student_profile(current_user, db)` - find the profile belonging to the logged-in student.
- `get_my_student_profile(current_user, db)` - return the logged-in student's profile.
- `update_my_student_profile(request, current_user, db)` - update only the profile fields sent by the student.
- `search_students(name, college, major, skills, current_user, db)` - search student profiles using company-approved filters.
- `get_student_profile(student_id, current_user, db)` - allow companies to view students and students to view only themselves.

## Backend: AI assistant (loop, tools, gate, guards)


### `backend/app/assistant/confirmation.py`

- `confirm_action(tool_name, arguments, auto_approve)` - approve read-only tools and require explicit approval for saves.

### `backend/app/assistant/guards.py`

- `normalize_job_search_args(query, employment_type, is_remote)` - move misplaced job-type and remote words into the correct filter.
- `protect_instructions(answer)` - drop any paragraph that quotes the system prompt from an answer.

### `backend/app/assistant/loop.py`

- `_system_prompt()` - add today's date so relative dates such as next month resolve correctly.
- **class AssistantRunResult** - contain the assistant answer and trace information.
- `AssistantRunResult.tool_call_count()` - return the number of tool calls made during this run.
- **class AssistantLoop** - coordinate Ollama responses and manual database tools.
- `AssistantLoop.__init__(client, max_iterations, max_repair_attempts)` - Store the model client and the limits (iteration ceiling and repair attempts).
- `AssistantLoop._tool_functions(db, student_id)` - bind the current database and student to each tool.
- `AssistantLoop._tool_arguments(raw_arguments)` - normalize Ollama tool arguments into a dictionary.
- `AssistantLoop._complete(messages)` - use complete when available while supporting older chat clients.
- `AssistantLoop._log_arguments(arguments)` - format arguments as one safe log line.
- `AssistantLoop._model_tool_content(tool_name, tool_result)` - separate retrieved database content from assistant instructions.
- `AssistantLoop.run(db, student_id, user_message, history, confirmed_save)` - run one bounded conversation through Ollama and the manual tools.

### `backend/app/assistant/tools.py`

- **class AssistantToolError** - represent invalid input supplied to an assistant tool.
- `_string_tool(function)` - return JSON text for success and a safe error string for failure.
- `_json_value(value)` - convert database values into values safe for tool responses.
- `_student_preferences_dict(profile)` - convert a student profile into assistant-friendly preferences.
- `_job_dict(job)` - convert one job model into an assistant result.
- `_event_dict(event)` - convert one event model into an assistant result.
- `_parse_datetime(value)` - parse an optional ISO datetime supplied by the assistant.
- `get_student_preferences(db, student_id)` - return the profile preferences for one student.
- `search_jobs(db, query, city, employment_type, is_remote, required_skill, limit)` - search seeded jobs using optional student-friendly filters.
- `get_job_details(db, job_id)` - return details for one job.
- `search_events(db, query, city, event_type, is_virtual, start_date, end_date, limit, major)` - search events using optional student-friendly filters.
- `save_job_or_event(db, student_id, item_type, item_id)` - save one job or event for a student without creating duplicates.

## Backend: services


### `backend/app/services/eligibility.py`

- `_get(obj, name)` - read a field from either a dictionary or an ORM object.
- `parse_majors(value)` - normalize a comma-separated major list.
- `check_eligibility(event, student)` - return whether a student meets every event requirement.
- `check_registration_open(event, registered_count, now)` - check whether an event is still within its date and capacity limits.

### `backend/app/services/ollama_client.py`

- **class OllamaError** - represent a local Ollama connection or response failure.
- **class OllamaClient** - call the local Ollama chat and generation endpoints.
- `OllamaClient.__init__(base_url, model, timeout_seconds)` - Store the Ollama address, model name and request timeout.
- `OllamaClient._request(method, path, payload)` - send one JSON request to Ollama and return its JSON response.
- `OllamaClient.list_models()` - return the models currently available in Ollama.
- `OllamaClient.chat(messages, tools, temperature)` - send chat messages and optional manual tool definitions.
- `OllamaClient.complete(messages, tools)` - complete one chat turn using the manual assistant interface.
- `OllamaClient.generate(prompt, system, temperature)` - generate one plain-text response from Ollama.

## Backend: core (database, security, config)


### `backend/app/core/config.py`

- **class Settings** - store application and security settings.

### `backend/app/core/database.py`

- **class Base** - base class for all SQLAlchemy database models.
- `get_db()` - provide one database session and close it after the request.

### `backend/app/core/security.py`

- `hash_password(password)` - convert a plain password into a bcrypt hash.
- `verify_password(password, password_hash)` - check whether a plain password matches its stored hash.
- `create_access_token(subject, role, expires_delta)` - create a signed JWT containing the user ID and role.
- `decode_access_token(token)` - decode a JWT or raise a clear error when it is invalid.

## Backend: database models


### `backend/app/models/application.py`

- **class Application** - store one student's application for one job.

### `backend/app/models/assistant_conversation.py`

- **class AssistantConversation** - store one student's assistant conversation.
- **class AssistantMessage** - store one ordered message inside a conversation.

### `backend/app/models/assistant_tool_log.py`

- **class AssistantToolLog** - store one manual tool call and its result or error.

### `backend/app/models/company_profile.py`

- **class CompanyProfile** - store information specific to a company.

### `backend/app/models/event.py`

- **class Event** - store an event that students can search and view.

### `backend/app/models/event_registration.py`

- **class EventRegistration** - store one student's registration for one event.

### `backend/app/models/job.py`

- **class Job** - store a job opportunity that students can search.

### `backend/app/models/saved_item.py`

- **class SavedItem** - store one saved job or event for one student.

### `backend/app/models/student_profile.py`

- **class StudentProfile** - store information specific to a student.

### `backend/app/models/user.py`

- **class UserRole** - define the two allowed user roles.
- **class User** - store shared login information for students and companies.

## Backend: request/response schemas


### `backend/app/schemas/application.py`

- **class ApplicationStatusUpdateRequest** - validate a company-side application status update.
- **class ApplicationResponse** - return an application without exposing stored file paths.

### `backend/app/schemas/assistant.py`

- **class AssistantChatRequest** - validate one assistant chat request.
- **class AssistantToolCallResponse** - return one tool-call record to the frontend.
- **class AssistantChatResponse** - return the assistant answer and trace metadata.

### `backend/app/schemas/auth.py`

- **class StudentSignupRequest** - validate data required to create a student account.
- **class CompanySignupRequest** - validate data required to create a company account.
- **class LoginRequest** - validate data required for login.
- **class UserResponse** - return safe user information without the password hash.
- **class TokenResponse** - return the JWT access token after successful login.

### `backend/app/schemas/company.py`

- **class CompanyProfileResponse** - return the logged-in company's profile.
- **class CompanyProfileUpdateRequest** - validate fields a company may update.

### `backend/app/schemas/company_event.py`

- **class CompanyEventCreateRequest** - validate fields required to create a company event.
- `CompanyEventCreateRequest.validate_choices()` - enforce pair 16 event choices on the server.
- **class CompanyEventResponse** - return a company event and its registration count.
- **class EventRegistrationStudentResponse** - return a registered student's profile and eligibility result.

### `backend/app/schemas/event.py`

- **class EventResponse** - return event information to a student.
- **class EventRegistrationResponse** - return confirmation information after registration.

### `backend/app/schemas/job.py`

- **class JobCreateRequest** - validate fields required to create a job posting.
- `JobCreateRequest.validate_salary_range()` - ensure the maximum salary is not below the minimum.
- **class JobResponse** - return one job posting.

### `backend/app/schemas/student_profile.py`

- **class StudentProfileResponse** - return a student's profile information.
- **class StudentSearchResult** - return only the profile fields needed for company student search.
- **class StudentProfileUpdateRequest** - validate fields that a student may update.

## Backend: scripts (seed generator, reliability runs)


### `backend/scripts/generate_seed_data.py`

- `_sample_skills(rng, k)` - Pick k random skills from the skill list and join them as text.
- `generate(seed)` - Return {table_name: [row dict, ...]} with all ids assigned and all FKs valid.
- `check_integrity(t)` - Raise AssertionError if counts or foreign keys are wrong.
- `jobs_posted(t, job_id)` - Return the posted_at timestamp of a generated job by its id.
- `_sql_value(v)` - Convert a Python value into a SQL literal (quoted string, number or NULL).
- `to_sql(t, password_col, include_clear)` - Turn the generated tables into INSERT statements, optionally with a clear-first step.
- `_read_env(path)` - Read key=value settings from a .env file.
- `_connect_args(args)` - Use flags, then DATABASE_URL from backend/.env, then DB_* environment variables.
- `load_into_mysql(t, args)` - Connect to MySQL and load the generated data.
- `summary(t)` - Print or return row counts for each generated table.
- `main()` - Command-line entry point: parse arguments and run the script.

### `backend/scripts/live_reliability_run.py`

- `parse(value)` - Tool results arrive as JSON text or already-parsed data; return parsed data when possible.
- `rows(result)` - Parse a tool result string into a list of rows for checking.
- `all_rows(pred)` - Check: at least one row came back and every row satisfies pred.
- `city_is(name)` - Build a check that a result row is in the given city.
- `no_leak()` - Build a check that the answer contains none of the forbidden strings.
- `mentions_failure_gracefully(calls, answer)` - Check that the answer explains a missing or failed result instead of inventing one.
- `http_json(method, url, body, token, timeout)` - Send an HTTP request with an optional JSON body and token, and return the JSON reply.
- `classify(turn, status, payload, called, check_problem)` - Return (category, note). Categories follow the failure-mode table in METRICS.md.
- `run(args)` - Run every selected turn against the live assistant and collect the records.
- `write_outputs(records, args)` - Write the result tables, raw JSON and transcripts to the docs folder.
- `main()` - Command-line entry point: parse arguments and run the script.

### `backend/scripts/live_reliability_run_isolated.py`

- `sanitize_text(value)` - remove credentials, tokens, emails, and private field values from evidence text.
- `sanitize_records(records)` - keep the 26-turn evidence fields while sanitizing user-facing text.
- `get_credentials(email, input_fn, password_fn, environ)` - read the dedicated test student's email and password without printing the password.
- `parse(value)` - parse JSON tool results when the backend returned JSON text.
- `rows(result)` - return result rows from the supported assistant result shapes.
- `all_rows(predicate)` - check that at least one returned row matches the requested predicate.
- `city_is(name)` - Build a check that a result row is in the given city.
- `no_leak()` - Build a check that the answer contains none of the forbidden strings.
- `mentions_failure_gracefully(calls, answer)` - Check that the answer explains a missing or failed result instead of inventing one.
- `http_json(method, url, body, token, timeout)` - send one JSON request without printing authorization data.
- `parse_approval(value)` - parse an explicit job:ID or event:ID save approval.
- `save_call_matches_approval(call, approved_item)` - confirm that a save tool call names the explicitly approved item.
- `classify(turn, status, payload, called, check_problem)` - return the bounded reliability category and a short note.
- `prepare_output_dir(output_dir)` - create a dedicated empty evidence directory and refuse existing files.
- `write_outputs(records, output_dir, student_label)` - write only sanitized evidence into a new dedicated directory.
- `run(args, input_fn, password_fn)` - run the 26 turns against the configured backend.
- `main()` - Command-line entry point: parse arguments and run the script.

### `backend/scripts/reliability_experiment.py`

- **class ScenarioClient** - return deterministic responses for one reliability scenario.
- `ScenarioClient.__init__(mode)` - Set which failure scenario the stand-in model will act out.
- `ScenarioClient._tool_response(name, arguments)` - Build a fake model reply that calls the given tool.
- `ScenarioClient.complete(messages, tools)` - Return the scripted reply for the current scenario, standing in for Ollama.
- `_make_database()` - create the isolated records used by every experiment turn.
- `_run_one(mode, max_repair_attempts)` - run one scenario and return its observable reliability metadata.
- `_category(mode, result)` - classify one deterministic run for the report.
- `run_experiment()` - run all 20 turns before and after the one-attempt repair path.
- `main()` - Command-line entry point: parse arguments and run the script.

## Backend: other


### `backend/app/main.py`

- `read_root()` - return a simple message from the backend.
- `health_check()` - confirm that the backend is healthy.

### `backend/app/api/dependencies.py`

- `get_current_user(token, db)` - decode the token and return the matching active user.
- `require_student(current_user)` - allow only authenticated student users.
- `require_company(current_user)` - allow only authenticated company users.

## Backend tests


### `backend/tests/test_applications.py`

8 tests: `setUpClass`, `setUp`, `tearDown`, `make_pdf_upload`, `test_student_can_apply_with_pdf_and_view_own_application`, `test_duplicate_application_is_rejected`, `test_company_can_review_owned_application_but_other_company_cannot`, `test_non_pdf_upload_is_rejected`


### `backend/tests/test_assistant_api.py`

6 tests: `__init__`, `run`, `setUpClass`, `setUp`, `tearDown`, `test_chat_persists_conversation_messages_and_tool_log`


### `backend/tests/test_assistant_loop.py`

13 tests: `__init__`, `chat`, `setUpClass`, `setUp`, `tearDown`, `test_loop_executes_tool_and_returns_final_answer`, `test_loop_stops_at_iteration_ceiling`, `test_ollama_complete_keeps_chat_compatibility`, `test_repair_reprompts_once_and_recovers`, `test_repair_stops_after_one_attempt`, `test_ollama_error_is_classified_and_stops`, `test_save_is_cancelled_without_confirmation`, `test_save_runs_after_explicit_confirmation`


### `backend/tests/test_assistant_tools.py`

8 tests: `setUpClass`, `setUp`, `tearDown`, `test_get_student_preferences`, `test_search_jobs_and_get_job_details`, `test_search_events`, `test_save_job_or_event_is_idempotent`, `test_tool_failures_are_returned_as_strings`


### `backend/tests/test_company_events.py`

7 tests: `setUpClass`, `setUp`, `tearDown`, `test_company_can_create_and_list_own_events`, `test_company_can_view_registered_students_and_eligibility`, `test_student_cannot_use_company_event_route`, `test_company_event_registration_checks_eligibility`


### `backend/tests/test_company_profile.py`

11 tests: `setUpClass`, `setUp`, `tearDown`, `test_company_can_read_and_update_own_profile`, `test_student_cannot_read_company_profile`, `test_company_can_upload_valid_profile_picture`, `test_invalid_profile_picture_type_is_rejected`, `test_oversized_profile_picture_is_rejected`, `test_unauthenticated_upload_is_rejected`, `test_student_cannot_upload_company_profile_picture`, `make_request`


### `backend/tests/test_confirmation.py`

3 tests: `test_read_only_tools_do_not_require_confirmation`, `test_save_requires_explicit_confirmation`, `test_explicit_save_confirmation_approves_action`


### `backend/tests/test_event_eligibility_search.py`

6 tests: `_event`, `setUpClass`, `setUp`, `tearDown`, `test_major_filter_keeps_matching_and_open_events`, `test_system_prompt_includes_todays_date`


### `backend/tests/test_events.py`

7 tests: `setUpClass`, `setUp`, `tearDown`, `test_search_filters_by_city_and_virtual_format`, `test_event_details_returns_not_found_for_unknown_event`, `test_registration_and_registered_events`, `test_duplicate_registration_returns_conflict`


### `backend/tests/test_guards.py`

7 tests: `test_remote_in_employment_type_becomes_remote_flag`, `test_internship_in_query_becomes_employment_type`, `test_remote_in_query_becomes_remote_flag`, `test_explicit_remote_flag_is_kept`, `test_real_keyword_query_is_untouched`, `test_normal_answer_is_unchanged`, `test_quoted_prompt_is_removed_and_jobs_are_kept`


### `backend/tests/test_jobs.py`

8 tests: `setUpClass`, `setUp`, `tearDown`, `test_company_can_create_and_list_only_own_jobs`, `test_student_can_filter_each_canonical_employment_type`, `test_employment_type_filter_preserves_city_filter`, `test_student_can_search_and_view_job_details`, `test_role_guards_reject_wrong_users`


### `backend/tests/test_live_reliability_run.py`

7 tests: `test_credentials_use_configured_email_and_hidden_password_prompt`, `test_credentials_require_an_email`, `test_sanitization_removes_credentials_tokens_emails_and_private_fields`, `test_record_sanitization_preserves_turn_count`, `test_evidence_refuses_to_overwrite_existing_directory`, `test_save_confirmation_matches_only_the_approved_item`, `test_all_26_turns_are_preserved`


### `backend/tests/test_prompt_injection.py`

7 tests: `__init__`, `complete`, `setUpClass`, `setUp`, `tearDown`, `test_poisoned_job_description_is_delimited_and_ignored`, `test_poisoned_event_description_is_delimited_and_ignored`


### `backend/tests/test_reliability.py`

1 tests: `test_reliability_counts_and_repair_results`


### `backend/tests/test_required_assistant.py`

8 tests: `setUpClass`, `setUp`, `tearDown`, `test_get_student_preferences`, `test_search_jobs`, `test_get_job_details`, `test_search_events`, `test_save_job_or_event`


### `backend/tests/test_seed_generator.py`

6 tests: `setUpClass`, `test_seed_and_required_counts`, `test_all_generated_cities_use_pair_16_city_set`, `test_duplicate_keys_are_prevented`, `test_default_sql_output_does_not_clear_tables`, `test_same_seed_produces_same_data`


### `backend/tests/test_student_lookup.py`

13 tests: `setUpClass`, `setUp`, `tearDown`, `test_company_can_view_any_student`, `test_student_can_view_only_own_profile`, `test_company_can_search_by_name`, `test_company_can_search_by_college`, `test_company_can_search_by_major`, `test_company_can_search_by_skills`, `test_company_can_combine_search_filters`, `test_company_receives_empty_list_for_no_matches`, `test_student_cannot_search_students`, `test_unauthenticated_user_cannot_search_students`


## Frontend (React)


### `frontend/src/App.jsx`

- `studentOnly(page)` - Pages only a logged-in company may open. Students get sent to their own dashboard.
- `companyOnly(page)` - Wrap a page so only a signed-in company user can open it.
- `App()` - Top-level component: navbar plus all routes, with student-only and company-only protection.

### `frontend/src/components/EmptyState.jsx`

- `EmptyState({ title, message, children })` - Shown when a list loads successfully but has nothing in it.

### `frontend/src/components/ErrorAlert.jsx`

- `ErrorAlert({ message })` - Show an error message in a red alert box.

### `frontend/src/components/FormField.jsx`

- `FormField({ label, name, value, onChange, error, help, required = false, as = 'input', type = 'text', rows = 3, children, ...rest })` - One labelled form control with inline validation feedback. <FormField label="Title" name="title" value={...} onChange={...} error={errors.title} /> Use as="textarea" or as="select" (pass <option>s as children) for other controls.

### `frontend/src/components/LoadingSpinner.jsx`

- `LoadingSpinner({ label = 'Loading...' })` - Show a loading spinner with a label.

### `frontend/src/components/Navbar.jsx`

- `Navbar()` - Top navigation bar; links change with the signed-in role.

### `frontend/src/components/ProtectedRoute.jsx`

- `ProtectedRoute({ role, children })` - Wrap a page with <ProtectedRoute role="student">...</ProtectedRoute> to require login, and optionally a specific role. A logged-in user hitting the wrong role's route gets sent to their own dashboard instead of a dead end.

### `frontend/src/components/StatusBadge.jsx`

- `StatusBadge({ status })` - Colored badge for an application status (Pending, Reviewed, Declined).

### `frontend/src/context/AuthContext.jsx`

- `AuthProvider({ children })` - Provide the signed-in user and login/logout functions to the whole app.
- `useAuth()` - Hook that returns the current auth state and actions.

### `frontend/src/pages/AssistantChat.jsx`

- `renderInline(text)` - render the assistant's simple inline markdown without adding a markdown package
- `parseArguments(argumentsValue)` - Turn a tool call's arguments (object or JSON string) into an object.
- `findDeclinedSave(toolCalls)` - Look in the tool calls for a save the confirmation gate refused, and return what it was.
- `AssistantChat()` - Assistant page: chat box, tool-call panel and the save approval box.

### `frontend/src/pages/CompanyDashboard.jsx`

- `StatTile({ label, value })` - A headline number with a quiet label. Plain ink on purpose: colour is saved for things that carry meaning (status badges), not for decoration.
- `CompanyDashboard()` - Company home page with links to jobs, events and applicants.

### `frontend/src/pages/CompanyEvents.jsx`

- `eligibilitySummary(event)` - Short, human-readable summary of an event's eligibility rules.
- `CompanyEvents()` - List the company's events.

### `frontend/src/pages/CompanyProfile.jsx`

- `toForm(data)` - Convert company profile data from the API into form values.
- `CompanyProfile()` - View and edit the company profile and profile picture.

### `frontend/src/pages/CompanySignup.jsx`

- `CompanySignup()` - Company sign-up form.

### `frontend/src/pages/CreateEvent.jsx`

- `emptyEvent()` - Return a blank event form state.
- `withSeconds(value)` - "2026-10-20T15:00" (what <input type="datetime-local"> gives) -> "2026-10-20T15:00:00"
- `CreateEvent()` - Form for a company to post an event, including eligibility.

### `frontend/src/pages/CreateJob.jsx`

- `emptyJob()` - Return a blank job form state.
- `CreateJob()` - Form for a company to post a job.

### `frontend/src/pages/EventRegistrations.jsx`

- `EventRegistrations()` - Show the students registered for one event.

### `frontend/src/pages/Home.jsx`

- `Home()` - Landing page.

### `frontend/src/pages/JobApplicants.jsx`

- `JobApplicants()` - List applicants for one job and let the company change their status.

### `frontend/src/pages/Login.jsx`

- `Login()` - Sign-in form for students and companies.

### `frontend/src/pages/MyApplications.jsx`

- `MyApplications()` - Student page listing their applications with date and status.

### `frontend/src/pages/MyJobs.jsx`

- `MyJobs()` - List the company's job postings.

### `frontend/src/pages/NotFound.jsx`

- `NotFound()` - 404 page.

### `frontend/src/pages/StudentDashboard.jsx`

- `StudentDashboard()` - Student home page.

### `frontend/src/pages/StudentEvents.jsx`

- `formatEventDate(value)` - Format an event date for display.
- `StudentEvents()` - Student page to search, view and register for events.

### `frontend/src/pages/StudentJobs.jsx`

- `formatSalary(job)` - Format a salary range for display.
- `StudentJobs()` - Student page to search and filter jobs, view details and apply with a PDF resume.

### `frontend/src/pages/StudentProfileView.jsx`

- `hasValue(value)` - True if a profile field has a value worth showing.
- `Detail({ label, value })` - One label/value row; renders nothing when the student left the field blank.
- `StudentProfileView()` - Read-only view of a student's profile, for companies reviewing applicants.

### `frontend/src/pages/StudentRegisteredEvents.jsx`

- `formatEventDate(value)` - Format an event date for display.
- `StudentRegisteredEvents()` - Student page listing events they registered for.

### `frontend/src/pages/StudentSearch.jsx`

- `locationFor(student)` - Build a student's display location from city, state and country.
- `StudentSearch()` - Company page to search students by name, college, skill or major.

### `frontend/src/pages/StudentSignup.jsx`

- `StudentSignup()` - Student sign-up form.

### `frontend/src/services/api.js`

- `extractErrorMessage(error, fallback = 'Something went wrong. Please try again.')` - Turn whatever the backend/network gave us into a plain string message, so every page can show one line without repeating this logic.

### `frontend/src/services/assistantService.js`

- `sendAssistantMessage(message, conversationId = null, confirmSave = false)` - send one student message to the protected assistant endpoint. confirm_save is true only after the student explicitly approves a save.

### `frontend/src/services/authService.js`

- `signupStudent(payload)` - POST /api/auth/student/signup { full_name, email, password, college_name }
- `signupCompany(payload)` - POST /api/auth/company/signup { company_name, email, password, location }
- `login(email, password)` - POST /api/auth/login { email, password } -> { access_token, token_type, user: { id, role, email, is_active } }
- `logout()` - Client-side only: the backend has no logout endpoint (stateless JWT), so logging out just means dropping the token.

### `frontend/src/services/companyService.js`

- `toList(data)` - Normalize an API response into a plain list.
- `seg(value)` - URL-encode a value for use in a request path.
- `getMyCompanyProfile()` - GET the signed-in company's profile.
- `updateMyCompanyProfile(payload)` - PUT changes to the company profile.
- `uploadCompanyProfilePicture(file)` - Upload a profile picture file.
- `createJob(payload)` - POST a new job posting.
- `getMyJobs()` - GET the company's job postings.
- `getJobApplications(jobId)` - GET the applications for one job.
- `updateApplicationStatus(applicationId, status)` - PATCH an application's status.
- `getApplicationResume(applicationId)` - Returns the PDF as a Blob. It has to go through axios (not a plain link) because the endpoint needs the Authorization header.
- `getApplicantProfile(studentId)` - GET one applicant's student profile.
- `searchStudents(filters = {})` - GET students matching the search filters.
- `createEvent(payload)` - POST a new event.
- `getMyEvents()` - GET the company's events.
- `getMyEvent(eventId)` - GET one event owned by the company.
- `getEventRegistrations(eventId)` - Students registered for one of this company's events, each with an eligibility verdict: { eligible: boolean, ineligible_reasons: string[] }.

### `frontend/src/services/eventService.js`

- `searchEvents(filters = {})` - fetch events using the filters selected by the student
- `registerForEvent(eventId)` - register the logged-in student for one event
- `getRegisteredEvents()` - fetch the events already registered by the logged-in student

### `frontend/src/services/jobService.js`

- `searchJobs(filters = {})` - search jobs using the filters selected by the student
- `getJob(jobId)` - fetch one job posting
- `applyToJob(jobId, resumeFile)` - apply to a job; the resume is an optional PDF file
- `getMyApplications()` - applications that belong to the logged-in student

### `frontend/src/services/studentService.js`

- `getMyStudentProfile()` - GET /api/students/me -- requires Authorization: Bearer <student_token>
- `updateMyStudentProfile(payload)` - PUT /api/students/me

### `frontend/src/utils/format.js`

- `todayISO()` - Today's date as YYYY-MM-DD in the user's local timezone. (toISOString() is UTC, which gives "tomorrow" for Pacific-time evenings.)
- `formatDate(value)` - Accepts "YYYY-MM-DD" or a full ISO datetime. Date-only strings are parsed as local midnight so they don't slip back a day in US timezones.
- `formatSalary(value)` - Format a salary range for display.
- `formatSalaryRange(min, max)` - "$90,000 - $120,000", "From $90,000", "Up to $120,000" or "Not listed".
- `formatDateTime(value)` - "Oct 20, 2026, 3:00 PM" from an ISO datetime such as "2026-10-20T15:00:00".

### `frontend/src/utils/validation.js`

- `str(value)` - Convert a value to a trimmed string, with null as empty.
- `hasErrors(errors)` - True if the errors object has any entries.
- `cleanPayload(values)` - Trim strings and turn blanks into null. FastAPI rejects '' for numeric and date fields (422), and null is what an optional field should send anyway.
- `validateJob(form)` - Check the job form and return field errors.
- `validateEvent(form)` - Events: title, type, city, when, capacity, and optional eligibility rules.
- `validateCompanyProfile(form)` - Check the company profile form and return field errors.

---
Total functions and tests listed: 354
