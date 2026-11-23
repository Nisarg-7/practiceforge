# Requirements and User Stories

## 1. Purpose
A platform where I practise coding problems for interview prep. A sandboxed
judge produces deterministic verdicts. AI only explains failures; it can never
change a verdict. Analytics show my weak topics over time.

## 2. Roles and permissions

| Action | Student | Instructor | Admin |
|---|---|---|---|
| Register (self-service) | yes (always Student) | no | no |
| Browse problems, see visible tests | yes | yes | yes |
| See hidden test inputs/outputs | no | own problems | yes |
| Create/edit problems and tests | no | own problems only | all |
| Run / Submit code | yes | yes | yes |
| View submissions | own only | all submissions on own problems | all |
| Comment on a submission | no | yes (own problems) | yes |
| Approve/reject AI explanations | no | yes (own problems) | yes |
| See own mastery and analytics | yes | yes | yes |
| Manage users and roles | no | no | yes |
| View audit log | no | no | yes |

Security rules:
- Registration creates Students only. Roles are changed only by an Admin.
- Every endpoint checks role (RBAC) and object ownership (object-level authorization).
- Hidden test data is never sent to a Student.

## 3. Functional requirements (core)
1. Auth: register, login, JWT access token (short expiry) plus refresh token, hashed passwords, protected routes.
2. Problem bank: title, markdown statement, difficulty, topic tags, visible and hidden tests, time and memory limits. Python only.
3. Monaco editor with Run (visible tests) and Submit (all tests).
4. Sandboxed execution: fresh Docker container per run, no network, CPU/memory/process limits, read-only filesystem, non-root user, dropped capabilities, hard timeout, container destroyed afterwards.
5. Deterministic grading with per-test verdicts: Accepted, Wrong Answer, Time Limit, Memory Limit, Runtime Error, Compile Error.
6. Async queue (Redis plus a separate worker) with bounded retries and recovery of stuck jobs.
7. Live per-test verdict updates over WebSockets.
8. AI explanations after failures: structured, validated, untrusted output; model name and version stored; instructor approve/reject; template fallback (expected vs actual diff) when AI is unavailable, slow, malformed or low confidence.
9. Instructor review: approve/reject AI explanations, inline comments on submissions.
10. Weakness tracking: failures tagged by topic, mastery score per topic, progress dashboard, SQL analytics.
11. Notifications, audit log (including denied access), rate limiting on submissions and AI calls.
12. Seed data, tests (normal, invalid, unauthorized, timeout), README, ER diagram, API docs, demo script, walkthrough video.

## 4. Non-functional requirements
- Security first: no secrets in Git, least privilege, untrusted code never runs outside the sandbox.
- Determinism: same code plus same tests gives the same verdict.
- Reproducible local setup with docker-compose.
- Free to run and host.

## 5. Out of scope
Languages other than Python, contests/leaderboards, payments, email delivery, mobile app.

## 6. User stories and acceptance criteria

| ID | Story | Acceptance criteria |
|---|---|---|
| US-01 | As a visitor, I register an account. | Email unique, password at least 8 chars, stored hashed, role is Student. |
| US-02 | As a user, I log in and stay logged in. | Login returns access and refresh tokens; expired access token can be refreshed; logout revokes the refresh token. |
| US-03 | As an Admin, I change a user's role. | Only Admin can call it; the change is written to the audit log. |
| US-04 | As a Student, I browse and filter problems. | Filter by difficulty and topic; hidden tests never shown. |
| US-05 | As an Instructor, I create a problem with tests. | Visible and hidden tests, limits validated, I am recorded as author. |
| US-06 | As an Instructor, I cannot edit another instructor's problem. | Request returns 403 and an audit entry is written. |
| US-07 | As a Student, I Run code against visible tests. | Result arrives per test; nothing counts toward mastery. |
| US-08 | As a Student, I Submit code against all tests. | Submission is queued; verdicts stream live; final verdict saved. |
| US-09 | As a Student, malicious code cannot harm the host. | Infinite loop, memory bomb, fork bomb, network and file writes all end in a safe verdict. |
| US-10 | As a Student, I get an explanation after a failure. | AI explanation or fallback diff; shown only as help, never changes the verdict. |
| US-11 | As an Instructor, I approve or reject AI explanations. | Status changes to approved/rejected; rejected ones are hidden from Students. |
| US-12 | As an Instructor, I comment on a submission's lines. | Comment tied to a line number; the Student is notified. |
| US-13 | As a Student, I see my weak topics. | Mastery per topic and a progress chart over time. |
| US-14 | As a Student, I am rate-limited. | Too many submissions return 429 with a retry hint. |
| US-15 | As an Admin, I read the audit log. | Filter by user, action and date; security events included. |