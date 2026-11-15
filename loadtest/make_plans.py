"""
build the JMeter test plans for Lab 2, Part 5.

run once (from the loadtest folder):   python make_plans.py
it writes login.jmx, job_search.jmx, apply.jmx, assistant.jmx, students.csv and resume.pdf.

every plan reads its settings from JMeter properties, so the same file runs against your laptop or
against AWS:   -Jhost  -Jport  -Jprotocol  -Jusers  -Jramp  -Jduration  -Jthink_ms
the plans sign in as the seeded demo students (student1..student200 @students.handshake-demo.com,
the shared seed password from backend/scripts/generate_seed_data.py).
"""

from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
SEED_PASSWORD = "Password123!"  # the demo password every seeded account shares
N_STUDENTS = 200
N_JOBS = 300


def x(value: str) -> str:
    return escape(str(value), {'"': "&quot;"})


# ----------------------------------------------------------------------------- building blocks
def string_prop(name: str, value: str) -> str:
    return f'<stringProp name="{x(name)}">{x(value)}</stringProp>'


def bool_prop(name: str, value: bool) -> str:
    return f'<boolProp name="{x(name)}">{str(value).lower()}</boolProp>'


def arguments_block(variables: dict[str, str]) -> str:
    items = "".join(
        f'<elementProp name="{x(k)}" elementType="Argument">'
        f'{string_prop("Argument.name", k)}{string_prop("Argument.value", v)}'
        f'{string_prop("Argument.metadata", "=")}</elementProp>'
        for k, v in variables.items()
    )
    return (f'<elementProp name="TestPlan.user_defined_variables" elementType="Arguments" '
            f'guiclass="ArgumentsPanel" testclass="Arguments" testname="User Defined Variables" enabled="true">'
            f'<collectionProp name="Arguments.arguments">{items}</collectionProp></elementProp>')


def http_defaults() -> str:
    return (
        '<ConfigTestElement guiclass="HttpDefaultsGui" testclass="ConfigTestElement" '
        'testname="HTTP Request Defaults" enabled="true">'
        '<elementProp name="HTTPsampler.Arguments" elementType="Arguments" guiclass="HTTPArgumentsPanel" '
        'testclass="Arguments" testname="User Defined Variables" enabled="true">'
        '<collectionProp name="Arguments.arguments"/></elementProp>'
        + string_prop("HTTPSampler.domain", "${__P(host,127.0.0.1)}")
        + string_prop("HTTPSampler.port", "${__P(port,9160)}")
        + string_prop("HTTPSampler.protocol", "${__P(protocol,http)}")
        + string_prop("HTTPSampler.connect_timeout", "10000")
        + string_prop("HTTPSampler.response_timeout", "${__P(timeout_ms,60000)}")
        + "</ConfigTestElement><hashTree/>"
    )


def csv_students() -> str:
    return (
        '<CSVDataSet guiclass="TestBeanGUI" testclass="CSVDataSet" testname="Seeded students" enabled="true">'
        + string_prop("filename", "students.csv")
        + string_prop("fileEncoding", "UTF-8")
        + string_prop("variableNames", "email,password")
        + bool_prop("ignoreFirstLine", True)
        + string_prop("delimiter", ",")
        + bool_prop("quotedData", False)
        + bool_prop("recycle", True)
        + bool_prop("stopThread", False)
        + string_prop("shareMode", "shareMode.all")
        + "</CSVDataSet><hashTree/>"
    )


def header_manager(headers: dict[str, str]) -> str:
    items = "".join(
        f'<elementProp name="" elementType="Header">{string_prop("Header.name", k)}'
        f'{string_prop("Header.value", v)}</elementProp>'
        for k, v in headers.items()
    )
    return ('<HeaderManager guiclass="HeaderPanel" testclass="HeaderManager" testname="Headers" enabled="true">'
            f'<collectionProp name="HeaderManager.headers">{items}</collectionProp></HeaderManager><hashTree/>')


def http_arg(name: str, value: str) -> str:
    return (f'<elementProp name="{x(name)}" elementType="HTTPArgument">'
            + bool_prop("HTTPArgument.always_encode", True)
            + string_prop("Argument.value", value)
            + string_prop("Argument.metadata", "=")
            + bool_prop("HTTPArgument.use_equals", True)
            + string_prop("Argument.name", name)
            + "</elementProp>")


def assertion(expected: str, label: str, ignore_status: bool = False) -> str:
    """check the response code against a regular expression (Matches).

    ignore_status=True lets this assertion decide pass/fail on its own; without it JMeter still marks
    any 4xx/5xx response as failed even when the assertion accepts it (needed for the expected 409).
    """
    return (
        f'<ResponseAssertion guiclass="AssertionGui" testclass="ResponseAssertion" testname="{x(label)}" enabled="true">'
        f'<collectionProp name="Asserion.test_strings">{string_prop("0", expected)}</collectionProp>'
        + string_prop("Assertion.custom_message", "")
        + string_prop("Assertion.test_field", "Assertion.response_code")
        + bool_prop("Assertion.assume_success", ignore_status)
        + '<intProp name="Assertion.test_type">1</intProp></ResponseAssertion><hashTree/>'
    )


def real_answer_assertion() -> str:
    """fail the sample when the backend answers 200 but only to say the model timed out.

    the backend gives up on the model after OLLAMA_TIMEOUT_SECONDS and still returns HTTP 200 with
    an "assistant service error" answer, so the status code alone would call that a success.
    """
    return (
        '<ResponseAssertion guiclass="AssertionGui" testclass="ResponseAssertion" testname="Answer is not a service error" enabled="true">'
        f'<collectionProp name="Asserion.test_strings">{string_prop("0", "assistant service error")}</collectionProp>'
        + string_prop("Assertion.custom_message", "model did not answer (service error)")
        + string_prop("Assertion.test_field", "Assertion.response_data")
        + bool_prop("Assertion.assume_success", False)
        # 16 = substring, 4 = not
        + '<intProp name="Assertion.test_type">20</intProp></ResponseAssertion><hashTree/>'
    )


def token_extractor() -> str:
    return (
        '<JSONPostProcessor guiclass="JSONPostProcessorGui" testclass="JSONPostProcessor" '
        'testname="Save access_token" enabled="true">'
        + string_prop("JSONPostProcessor.referenceNames", "token")
        + string_prop("JSONPostProcessor.jsonPathExprs", "$.access_token")
        + string_prop("JSONPostProcessor.match_numbers", "1")
        + string_prop("JSONPostProcessor.defaultValues", "NO_TOKEN")
        + "</JSONPostProcessor><hashTree/>"
    )


def think_time() -> str:
    return ('<ConstantTimer guiclass="ConstantTimerGui" testclass="ConstantTimer" testname="Think time" enabled="true">'
            + string_prop("ConstantTimer.delay", "${__P(think_ms,500)}") + "</ConstantTimer><hashTree/>")


def sampler(name: str, method: str, path: str, *, params: dict[str, str] | None = None,
            body: str | None = None, file_part: tuple[str, str, str] | None = None,
            children: str = "", timeout: str | None = None) -> str:
    """one HTTP request. body = raw JSON body; file_part = (path, form field, mime type) for multipart."""
    if body is not None:
        args = ('<elementProp name="" elementType="HTTPArgument">'
                + bool_prop("HTTPArgument.always_encode", False)
                + string_prop("Argument.value", body) + string_prop("Argument.metadata", "=")
                + "</elementProp>")
    else:
        args = "".join(http_arg(k, v) for k, v in (params or {}).items())
    xml = (f'<HTTPSamplerProxy guiclass="HttpTestSampleGui" testclass="HTTPSamplerProxy" testname="{x(name)}" enabled="true">'
           + bool_prop("HTTPSampler.postBodyRaw", body is not None)
           + f'<elementProp name="HTTPsampler.Arguments" elementType="Arguments"><collectionProp name="Arguments.arguments">{args}</collectionProp></elementProp>'
           + string_prop("HTTPSampler.path", path) + string_prop("HTTPSampler.method", method)
           + bool_prop("HTTPSampler.follow_redirects", True) + bool_prop("HTTPSampler.auto_redirects", False)
           + bool_prop("HTTPSampler.use_keepalive", True)
           + bool_prop("HTTPSampler.DO_MULTIPART_POST", file_part is not None))
    if timeout:
        xml += string_prop("HTTPSampler.response_timeout", timeout)
    if file_part:
        file_path, field, mime = file_part
        xml += ('<elementProp name="HTTPsampler.Files" elementType="HTTPFileArgs"><collectionProp name="HTTPFileArgs.files">'
                '<elementProp name="" elementType="HTTPFileArg">'
                + string_prop("File.path", file_path) + string_prop("File.paramname", field)
                + string_prop("File.mimetype", mime) + "</elementProp></collectionProp></elementProp>")
    return xml + f"</HTTPSamplerProxy><hashTree>{children}</hashTree>"


def login_sampler() -> str:
    return sampler(
        "POST /api/auth/login", "POST", "/api/auth/login",
        body='{"email":"${email}","password":"${password}"}',
        children=header_manager({"Content-Type": "application/json"}) + assertion("200", "Status is 200") + token_extractor(),
    )


def auth_header() -> str:
    return header_manager({"Authorization": "Bearer ${token}"})


def thread_group(name: str, inner: str) -> str:
    return (
        f'<ThreadGroup guiclass="ThreadGroupGui" testclass="ThreadGroup" testname="{x(name)}" enabled="true">'
        + string_prop("ThreadGroup.on_sample_error", "continue")
        + '<elementProp name="ThreadGroup.main_controller" elementType="LoopController" guiclass="LoopControlPanel" '
          'testclass="LoopController" testname="Loop Controller" enabled="true">'
        + bool_prop("LoopController.continue_forever", False)
        + '<intProp name="LoopController.loops">-1</intProp></elementProp>'
        + string_prop("ThreadGroup.num_threads", "${__P(users,100)}")
        + string_prop("ThreadGroup.ramp_time", "${__P(ramp,30)}")
        + bool_prop("ThreadGroup.scheduler", True)
        + string_prop("ThreadGroup.duration", "${__P(duration,120)}")
        + string_prop("ThreadGroup.delay", "")
        + bool_prop("ThreadGroup.same_user_on_next_iteration", True)
        + f"</ThreadGroup><hashTree>{inner}</hashTree>"
    )


def only_if_signed_in(inner: str) -> str:
    """skip the request when this user's login failed (token is still NO_TOKEN), so a failed login
    shows up once as a login error instead of as hundreds of 401 errors."""
    return ('<IfController guiclass="IfControllerPanel" testclass="IfController" testname="Only if signed in" enabled="true">'
            + string_prop("IfController.condition", '${__jexl3("${token}" != "NO_TOKEN")}')
            + bool_prop("IfController.evaluateAll", False) + bool_prop("IfController.useExpression", True)
            + f"</IfController><hashTree>{inner}</hashTree>")


def once_only(inner: str) -> str:
    return ('<OnceOnlyController guiclass="OnceOnlyControllerGui" testclass="OnceOnlyController" '
            f'testname="Sign in once per user" enabled="true"/><hashTree>{inner}</hashTree>')


def test_plan(name: str, variables: dict[str, str], groups: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n<jmeterTestPlan version="1.2" properties="5.0" jmeter="5.6.3"><hashTree>'
        f'<TestPlan guiclass="TestPlanGui" testclass="TestPlan" testname="{x(name)}" enabled="true">'
        + string_prop("TestPlan.comments", "Lab 2 Part 5, Pair 16. Settings come from -J properties; see make_plans.py.")
        + bool_prop("TestPlan.functional_mode", False) + bool_prop("TestPlan.serialize_threadgroups", False)
        + arguments_block(variables) + "</TestPlan><hashTree>"
        + http_defaults() + csv_students() + groups + "</hashTree></hashTree></jmeterTestPlan>\n"
    )


# ----------------------------------------------------------------------------- the four plans
def plan_login() -> str:
    inner = login_sampler() + think_time()
    return test_plan("Login", {}, thread_group("Students logging in", inner))


def plan_job_search() -> str:
    terms = {f"term{i}": t for i, t in enumerate(["Python", "SQL", "Data", "Engineer", "Analyst"], 1)}
    search = sampler("GET /api/jobs?search=", "GET", "/api/jobs",
                     params={"search": "${__V(term${__Random(1,5)})}"}, children=auth_header() + assertion("200", "Status is 200"))
    inner = once_only(login_sampler()) + only_if_signed_in(search) + think_time()
    return test_plan("Job search", terms, thread_group("Students searching jobs", inner))


def plan_apply() -> str:
    # 201 = application created; 409 = this student already applied to that job (expected sometimes,
    # because the seed already holds 1,500 applications and students pick jobs at random)
    apply = sampler("POST /api/jobs/{id}/applications", "POST", "/api/jobs/${__Random(1,%d)}/applications" % N_JOBS,
                    file_part=("resume.pdf", "resume", "application/pdf"),
                    children=auth_header() + assertion("201|409", "Status is 201 or 409", ignore_status=True))
    inner = once_only(login_sampler()) + only_if_signed_in(apply) + think_time()
    return test_plan("Application submission", {}, thread_group("Students applying", inner))


def plan_assistant() -> str:
    prompts = {
        "p1": "Find remote jobs in Cupertino",
        "p2": "Show me virtual events next month",
        "p3": "Which internships match Python and SQL?",
        "p4": "What are my saved preferences?",
    }
    chat = sampler("POST /api/assistant/chat", "POST", "/api/assistant/chat",
                   body='{"message":"${__V(p${__Random(1,4)})}"}', timeout="${__P(timeout_ms,180000)}",
                   children=(header_manager({"Content-Type": "application/json", "Authorization": "Bearer ${token}"})
                             + assertion("200", "Status is 200")
                             + real_answer_assertion()))
    inner = once_only(login_sampler()) + only_if_signed_in(chat) + think_time()
    return test_plan("AI assistant", prompts, thread_group("Students chatting with the assistant", inner))


def tiny_pdf() -> bytes:
    """a valid one-page PDF of about 500 bytes (the backend only checks the %PDF- header and the 5 MB limit)."""
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Contents 4 0 R /Resources << >> >>",
        b"<< /Length 0 >>\nstream\n\nendstream",
    ]
    out, offsets = b"%PDF-1.4\n", []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode() + b"0000000000 65535 f \n"
    out += b"".join(f"{o:010d} 00000 n \n".encode() for o in offsets)
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return out


def main() -> None:
    plans = {"login.jmx": plan_login(), "job_search.jmx": plan_job_search(),
             "apply.jmx": plan_apply(), "assistant.jmx": plan_assistant()}
    for name, xml in plans.items():
        (HERE / name).write_text(xml, encoding="utf-8")
        print("wrote", name)
    rows = ["email,password"] + [f"student{i}@students.handshake-demo.com,{SEED_PASSWORD}" for i in range(1, N_STUDENTS + 1)]
    (HERE / "students.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")
    (HERE / "resume.pdf").write_bytes(tiny_pdf())
    print(f"wrote students.csv ({N_STUDENTS} students) and resume.pdf")


if __name__ == "__main__":
    main()
