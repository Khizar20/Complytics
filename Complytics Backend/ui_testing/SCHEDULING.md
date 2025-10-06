## UI Testing — Scheduling Architecture and Operations

This document explains how scheduled UI scans are implemented and operated across the backend and frontend. It covers endpoints, data flow, permissions, lifecycle, and known limitations.

### Overview
- Backend service: FastAPI (`Complytics Backend/routes/ui_testing.py`)
- Scheduler: APScheduler `AsyncIOScheduler` with `DateTrigger` (in‑process)
- Storage: MongoDB collections `scheduled_scans` (schedules) and `ui_testing_results` (scan results)
- Frontend: React component `src/components/team/ScheduleScan.jsx` to create/list/cancel schedules; `UserDashboard.jsx` polls latest results

### Key Concepts
- Scheduled jobs are stored in MongoDB (`scheduled_scans`) and also registered in an in‑process APScheduler.
- On application startup, pending future schedules are rehydrated (registered again) from MongoDB.
- When a schedule fires, the backend reuses the last scanned URL for the organization and runs a full scan (`mode=all`).
- On completion, the result is persisted to `ui_testing_results` and a simple HTML email is sent (if the user has an email on file).

## API Endpoints

All endpoints require authentication. Organization scoping is enforced in handlers.

### POST /api/ui/schedule
Create a one‑time scheduled scan for the current organization.

Request body:
```json
{ "run_at_iso": "2025-10-01T14:30:00Z" }
```

Notes:
- `run_at_iso`: ISO‑8601 datetime. If timezone is omitted, it is treated as UTC.
- Authorization: role must be one of `compliance_team`, `admin`, `superadmin`.
- The schedule stores only the run time; the URL to scan is taken from the organization’s most recent UI test result at execution time.

Response:
```json
{ "id": "<schedule_id>", "scheduled_for": 1730394600, "status": "scheduled" }
```

### GET /api/ui/schedules
List all schedules for the current organization (sorted by `scheduled_for`). The frontend typically filters out past schedules client‑side.

Response:
```json
{ "schedules": [ { "_id": "...", "organization_id": "...", "scheduled_for": 1730394600, "status": "scheduled", ... } ] }
```

### DELETE /api/ui/schedules/{id}
Cancel a future schedule. If the schedule is already `completed` or `failed`, the call is a no‑op and returns the current status. When cancellation succeeds, the APScheduler job (if present) is also removed in‑process.

Response:
```json
{ "id": "<schedule_id>", "status": "cancelled" }
```

### POST /api/ui/scan-now
Run an immediate full scan for the last URL used by the current organization. Returns a message, URL, and the result payload. Useful for ad‑hoc reruns outside of scheduling.

### POST /api/ui/scan
Run a full or partial scan immediately for a specific URL. Used by the main UI Testing page and the modal in the scheduling screen for one‑off scans.

## Data Model

### scheduled_scans (MongoDB)
Documents are created at schedule time:
```json
{
  "_id": ObjectId,
  "organization_id": "<org_id>",
  "scheduled_by": "<user_id>",
  "email": "<user_email_or_null>",
  "scheduled_for": <epoch_seconds_utc>,
  "status": "scheduled" | "running" | "completed" | "failed" | "cancelled",
  "error": "<optional_error_text>",
  "created_at": <epoch_seconds>,
  "updated_at": <epoch_seconds>
}
```

Notes:
- Collection creation is implicit (no explicit initializer); it is created on first insert.
- Jobs are keyed in APScheduler by the schedule document’s string `_id`.

### ui_testing_results (MongoDB)
Persisted on every successful scan (manual or scheduled). Indexed by `(organization_id, created_at)` for fast retrieval of the latest result.

## Lifecycle

1) Schedule creation
   - Validate role and organization.
   - Parse `run_at_iso` to UTC; reject past times.
   - Insert schedule document in `scheduled_scans` with `status="scheduled"`.
   - Register APScheduler job with `DateTrigger(run_date=<scheduled_for UTC>)` and `id=<schedule_id>`.

2) Application startup
   - Configure AI (Gemini) and start `AsyncIOScheduler`.
   - Rehydrate: query `scheduled_scans` where `status="scheduled"` and `scheduled_for >= now` and add jobs that aren’t already present in memory.

3) Execution (when trigger fires)
   - Load schedule doc by `_id` and ensure `status="scheduled"`.
   - Set `status="running"`.
   - Find the organization’s last scanned URL from `ui_testing_results`; if none exists, mark `failed` with an error (`No previous scan URL found`).
   - Otherwise, run a full scan (`mode=all`) via the existing scan pipeline and persist results.
   - Email a brief HTML summary (WCAG severity counts + AI recommendations) to the stored `email` if present.
   - Set `status="completed"` (or `failed` with error on exception).

4) Frontend visibility
   - `ScheduleScan.jsx` shows upcoming schedules (filters out past items client‑side) and allows cancellation.
   - `UserDashboard.jsx` polls `GET /api/ui/latest` every 60s and on tab visibility to reflect new scheduled results.

## Permissions & Auth
- All routes require auth via bearer token.
- `POST /api/ui/schedule` is restricted to `compliance_team`, `admin`, or `superadmin` roles.
- Listing and cancelling are scoped to the caller’s `organization_id`.

## Time Handling
- The backend accepts ISO‑8601 strings and converts them via `datetime.fromisoformat`.
- If no timezone is provided, it is treated as UTC.
- The frontend date‑time picker uses the local time and sends `toISOString()` (UTC), ensuring consistent scheduling.

## Status Transitions

| From        | To          | Trigger                                      |
|-------------|-------------|----------------------------------------------|
| scheduled   | running     | Job fires (APScheduler)                      |
| running     | completed   | Scan completes successfully                  |
| running     | failed      | Any exception during execution               |
| scheduled   | cancelled   | DELETE /api/ui/schedules/{id}                |
| scheduled   | failed      | No previous scan URL found at execution time |

Notes:
- Email delivery failures do not mark the job `failed`; they are logged and ignored.

## Failure Modes & Behavior
- Database unavailable: listing/creating/cancelling schedules returns HTTP 500; execution early‑returns.
- No previous scan URL: schedule is marked `failed` with an explanatory error.
- Email failure: ignored; job completes normally.
- Scan pipeline errors: schedule marked `failed` with the exception string.

## Concurrency & Deployment Considerations
- The scheduler is in‑process and uses the default memory job store. In multi‑instance deployments, each instance will rehydrate and run its own copy of pending jobs, which can lead to duplicate executions.
- Current `running` transition uses a simple `update_one` by `_id`; it is not a compare‑and‑set on the prior status. Two instances may race and both run the same job.
- Recommended production hardening:
  - Use a persistent APScheduler job store (e.g., MongoDB/Redis) or single‑instance scheduling.
  - Add an atomic status transition (e.g., update with `{_id, status: 'scheduled'}` to set `running`) and verify the matched count.
  - Introduce a short execution lock (e.g., `locked_at`/`locked_by` TTL) to prevent duplicates.

## Email Summary
- Subject: "Complytics: Scheduled UI Compliance Scan Completed".
- Body includes the URL, UTC timestamp, counts of WCAG violations by impact, and the AI recommendations text.

## Example Requests

Create a schedule (run in 15 minutes):
```bash
curl -X POST http://localhost:8000/api/ui/schedule \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"run_at_iso":"'"$(date -u -d "+15 minutes" +%Y-%m-%dT%H:%M:%SZ)'"'}'
```

List schedules:
```bash
curl -H "Authorization: Bearer <TOKEN>" http://localhost:8000/api/ui/schedules
```

Cancel a schedule:
```bash
curl -X DELETE -H "Authorization: Bearer <TOKEN>" http://localhost:8000/api/ui/schedules/<id>
```

Run now with last URL:
```bash
curl -X POST -H "Authorization: Bearer <TOKEN>" http://localhost:8000/api/ui/scan-now
```

## Operational Notes
- Scheduler rehydration occurs at process startup; ensure `init_db` runs and MongoDB is reachable.
- Time is stored and compared in epoch seconds (UTC) for scheduling.
- Results caching (`SCAN_CACHE`, 5‑minute TTL) avoids re‑running scans immediately for exports and does not affect scheduled execution.

## Known Limitations & Future Improvements
- Multi‑instance duplication risk without a distributed job store/lock.
- One‑time schedules only (no cron/interval UI); could be extended.
- Schedules reuse the last URL; adding a URL field per schedule would remove this implicit dependency.
- No retry policy for transient scan failures; consider limited automatic retries.


