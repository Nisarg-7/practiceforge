# Workflow Diagrams

## 1. Submit flow (end to end)

```mermaid
sequenceDiagram
    participant B as Browser (React)
    participant A as API (FastAPI)
    participant DB as PostgreSQL
    participant R as Redis queue
    participant W as Worker
    participant S as Sandbox container
    participant AI as AI layer

    B->>A: POST /problems/{id}/submit (JWT)
    A->>A: check auth, role, rate limit
    A->>DB: insert submission (QUEUED)
    A->>R: enqueue job(submission_id)
    A-->>B: 202 Accepted + submission_id
    B->>A: open WebSocket with short-lived ticket
    W->>R: take job
    W->>DB: mark RUNNING
    loop each test case
        W->>S: start fresh container, run code on test
        S-->>W: stdout, exit code, time, memory
        W->>W: compare to expected, decide verdict
        W->>DB: save test result
        W-->>B: live verdict (via Redis pub/sub and API WebSocket)
        W->>S: destroy container
    end
    W->>DB: save final verdict, mark DONE
    alt a test failed
        W->>AI: code + failed test + error
        AI-->>W: structured explanation or failure
        W->>W: validate with Pydantic, else use fallback diff
        W->>DB: store explanation (PENDING review)
    end
    W->>DB: update topic mastery, create notification
```

## 2. Job lifecycle and crash recovery

```mermaid
stateDiagram-v2
    [*] --> QUEUED
    QUEUED --> RUNNING: worker picks job
    RUNNING --> DONE: all tests graded
    RUNNING --> QUEUED: worker crash or timeout (retry, max 3)
    RUNNING --> FAILED_INTERNAL: retries exhausted
    DONE --> [*]
    FAILED_INTERNAL --> [*]
```

## 3. Trust boundaries
- Browser is untrusted: the API re-checks everything.
- User code is hostile: it runs only inside the sandbox.
- AI output is untrusted: it is validated, reviewable and can never alter a verdict.