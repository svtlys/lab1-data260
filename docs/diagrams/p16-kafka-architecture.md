# Pair 16 Kafka architecture

```mermaid
flowchart LR
    subgraph APIs[Pair 16 API services]
        Student[student API]
        Company[company API]
        Events[event API]
        Jobs[job API]
        Applications[application API]
        Assistant[assistant API]
    end

    MySQL[(MySQL p16_handshake)]
    Mongo[(MongoDB p16_handshake)]
    Kafka[(Kafka p16-kafka:9092)]

    Student -->|auth/profile writes| MySQL
    Company -->|company/job/event/application writes| MySQL
    Events -->|registration writes| MySQL
    Jobs -->|job writes| MySQL
    Applications -->|application/status writes| MySQL
    Assistant -->|assistant persistence and reads| MySQL

    Student -.->|profile/job/event reads when enabled| Mongo
    Company -.->|company/profile reads when enabled| Mongo
    Jobs -.->|job reads when enabled| Mongo
    Applications -.->|application reads when enabled| Mongo
    Assistant -.->|assistant memory and conversations| Mongo

    Applications -->|application.created| AC[p16.application.created]
    Applications -->|application.updated| AU[p16.application.updated]
    Applications -->|application.status_changed| AS[p16.application.status_changed]
    Events -->|event.registration_created| ER[p16.event.registration_created]
    Jobs -->|job.created| JC[p16.job.created]
    Assistant -->|memory.consolidate| MC[p16.memory.consolidate]

    AC --> AppWorker[application worker\np16-application-worker]
    AU --> AppWorker
    AS --> NotifyWorker[notification worker\np16-notification-worker]
    ER --> EventWorker[event worker\np16-event-worker]
    JC --> JobWorker[job worker\np16-job-worker]
    MC --> MemoryWorker[memory worker\np16-memory-worker]

    Envelope[event envelope\nevent_id, event_type, occurred_at, trace_id, actor, payload]
    AC -.-> Envelope
    AU -.-> Envelope
    AS -.-> Envelope
    ER -.-> Envelope
    JC -.-> Envelope
    MC -.-> Envelope

    Envelope --> Reliability[shared consumer reliability\nmanual offset commit\nmax 3 attempts]
    Reliability --> Idempotency{processed_events\n(event_id lookup)}
    Idempotency -->|new event| AppWorker
    Idempotency -->|new event| NotifyWorker
    Idempotency -->|new event| EventWorker
    Idempotency -->|new event| JobWorker
    Idempotency -->|new event| MemoryWorker
    Idempotency -->|duplicate| CommitDuplicate[commit duplicate offset]

    AppWorker --> Activity[activity_logs]
    NotifyWorker --> Activity
    EventWorker --> Activity
    JobWorker --> Activity
    MemoryWorker --> MemoryData[assistant_rules\nstudent_memory\nconversations]
    Activity --> Record[record processed_events\nafter successful handler/database work]
    MemoryData --> Record
    Record --> Commit[commit Kafka offset]

    Reliability -->|third failure| DLQ[p16.dlq]
    DLQ --> CommitDLQ[commit only after DLQ publish]
    Reliability -->|DLQ publish failure| Uncommitted[leave offset uncommitted]

    Envelope -.->|same trace_id in logs, retries, and DLQ envelope| Reliability
```

The API services retain MySQL as the active source of truth for current Lab 1
write behavior. MongoDB is used for the implemented read/memory and worker
paths, while every Kafka envelope carries the same trace identifier through
processing and failure handling.
