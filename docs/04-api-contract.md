# API Contract (v1, draft)

Base path: `/api/v1`. JSON everywhere. Auth: `Authorization: Bearer <access_token>`.
Roles: S = Student, I = Instructor, A = Admin. "Own" means object-level check.

## Auth
| Method | Path | Who | Notes |
|---|---|---|---|
| POST | /auth/register | public | Creates a Student only |
| POST | /auth/login | public | Returns access and refresh tokens |
| POST | /auth/refresh | public (refresh token) | Rotates the refresh token |
| POST | /auth/logout | any | Revokes the refresh token |
| GET | /users/me | any | Current user profile |

## Admin
| Method | Path | Who | Notes |
|---|---|---|---|
| GET | /admin/users | A | List users |
| PATCH | /admin/users/{id}/role | A | Change role (audited) |
| GET | /admin/audit-logs | A | Filters: user, action, date |

## Problems
| Method | Path | Who | Notes |
|---|---|---|---|
| GET | /problems | any | Filters: difficulty, topic; paginated |
| GET | /problems/{id} | any | Hidden tests never included for S |
| POST | /problems | I, A | Author set from token |
| PUT | /problems/{id} | I (own), A | |
| DELETE | /problems/{id} | I (own), A | |
| POST | /problems/{id}/test-cases | I (own), A | |
| PUT | /test-cases/{id} | I (own), A | |
| DELETE | /test-cases/{id} | I (own), A | |
| GET | /topics | any | |

## Submissions
| Method | Path | Who | Notes |
|---|---|---|---|
| POST | /problems/{id}/run | any | Visible tests; returns 202 + submission id |
| POST | /problems/{id}/submit | any | All tests; returns 202; rate limited |
| GET | /submissions | S (own), I (own problems), A | Paginated |
| GET | /submissions/{id} | owner, I (own problem), A | Includes per-test results |
| POST | /submissions/{id}/ws-ticket | owner | Short-lived one-time ticket for WebSocket |
| WS | /ws/submissions/{id}?ticket=... | owner | Live per-test verdicts |

## AI explanations and review
| Method | Path | Who | Notes |
|---|---|---|---|
| GET | /submissions/{id}/explanations | owner (approved only), I, A | |
| GET | /review/explanations?status=PENDING | I (own problems), A | Review queue |
| PATCH | /review/explanations/{id} | I (own problems), A | Body: approve or reject |
| GET | /submissions/{id}/comments | owner, I, A | |
| POST | /submissions/{id}/comments | I (own problems), A | Body: line_number, body |

## Analytics and notifications
| Method | Path | Who | Notes |
|---|---|---|---|
| GET | /analytics/mastery | any (own) | Mastery per topic |
| GET | /analytics/progress | any (own) | Time series for the dashboard |
| GET | /notifications | any (own) | |
| PATCH | /notifications/{id}/read | any (own) | |

## System
| Method | Path | Who |
|---|---|---|
| GET | /health | public |

## Conventions
- Error body: `{"error": {"code": "FORBIDDEN", "message": "..."}}`.
- Status codes: 200, 201, 202 (queued), 400, 401 (not logged in), 403 (not allowed), 404, 422 (validation), 429 (rate limited).
- Return 404 instead of 403 when revealing that an object exists would leak information.
- Paging: `?page=1&page_size=20`.
- Verdict values: ACCEPTED, WRONG_ANSWER, TIME_LIMIT, MEMORY_LIMIT, RUNTIME_ERROR, COMPILE_ERROR.
- WebSocket message: `{"test_case_position": 2, "verdict": "ACCEPTED", "time_ms": 18}`, then a final `{"done": true, "final_verdict": "..."}`.