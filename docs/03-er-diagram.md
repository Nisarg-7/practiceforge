# ER Diagram

```mermaid
erDiagram
    USERS ||--o{ REFRESH_TOKENS : has
    USERS ||--o{ PROBLEMS : authors
    USERS ||--o{ SUBMISSIONS : makes
    PROBLEMS ||--o{ TEST_CASES : has
    PROBLEMS ||--o{ PROBLEM_TOPICS : tagged
    TOPICS ||--o{ PROBLEM_TOPICS : tags
    PROBLEMS ||--o{ SUBMISSIONS : receives
    SUBMISSIONS ||--o{ TEST_RESULTS : produces
    TEST_CASES ||--o{ TEST_RESULTS : checked_by
    TEST_RESULTS ||--o| AI_EXPLANATIONS : explained_by
    SUBMISSIONS ||--o{ REVIEW_COMMENTS : receives
    USERS ||--o{ REVIEW_COMMENTS : writes
    USERS ||--o{ TOPIC_MASTERY : has
    TOPICS ||--o{ TOPIC_MASTERY : measured_in
    USERS ||--o{ NOTIFICATIONS : receives
    USERS ||--o{ AUDIT_LOGS : performs

    USERS {
        uuid id PK
        string email UK
        string password_hash
        string role "STUDENT, INSTRUCTOR, ADMIN"
        boolean is_active
        timestamp created_at
    }
    REFRESH_TOKENS {
        uuid id PK
        uuid user_id FK
        string token_hash
        timestamp expires_at
        timestamp revoked_at
    }
    PROBLEMS {
        uuid id PK
        uuid author_id FK
        string title
        text statement_md
        string difficulty "EASY, MEDIUM, HARD"
        int time_limit_ms
        int memory_limit_mb
        boolean is_published
        timestamp created_at
    }
    TOPICS {
        uuid id PK
        string name UK
    }
    PROBLEM_TOPICS {
        uuid problem_id FK
        uuid topic_id FK
    }
    TEST_CASES {
        uuid id PK
        uuid problem_id FK
        text input_data
        text expected_output
        boolean is_hidden
        int position
    }
    SUBMISSIONS {
        uuid id PK
        uuid user_id FK
        uuid problem_id FK
        text code
        string kind "RUN, SUBMIT"
        string status "QUEUED, RUNNING, DONE, FAILED_INTERNAL"
        string final_verdict
        int attempts
        timestamp created_at
        timestamp finished_at
    }
    TEST_RESULTS {
        uuid id PK
        uuid submission_id FK
        uuid test_case_id FK
        string verdict "ACCEPTED, WRONG_ANSWER, TIME_LIMIT, MEMORY_LIMIT, RUNTIME_ERROR, COMPILE_ERROR"
        text actual_output
        text error_output
        int time_ms
        int memory_kb
    }
    AI_EXPLANATIONS {
        uuid id PK
        uuid test_result_id FK
        string source "AI, FALLBACK"
        string model_name
        string model_version
        text explanation
        text hint
        float confidence
        string review_status "PENDING, APPROVED, REJECTED"
        uuid reviewed_by FK
        timestamp reviewed_at
    }
    REVIEW_COMMENTS {
        uuid id PK
        uuid submission_id FK
        uuid author_id FK
        int line_number
        text body
        timestamp created_at
    }
    TOPIC_MASTERY {
        uuid user_id FK
        uuid topic_id FK
        int attempts
        int failures
        float mastery_score
        timestamp updated_at
    }
    NOTIFICATIONS {
        uuid id PK
        uuid user_id FK
        string type
        text message
        timestamp read_at
        timestamp created_at
    }
    AUDIT_LOGS {
        uuid id PK
        uuid user_id FK
        string action
        string target_type
        string target_id
        string outcome "ALLOWED, DENIED"
        string ip_address
        timestamp created_at
    }
```

## Design notes
- UUID primary keys: ids cannot be guessed, which helps object-level authorization.
- `test_results` is one row per test, which gives live updates and per-topic analytics.
- Only hashes of refresh tokens are stored, so a database leak cannot be replayed.
- `ai_explanations` is separate from verdicts, so AI can never overwrite a grade.
- `TOPIC_MASTERY` has a composite key (`user_id`, `topic_id`); indexes will be added with the analytics queries in Phase 6.