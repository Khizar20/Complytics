# Schedule Scan Module - Roman Urdu Documentation

## Module Ka Naam
**Schedule Scan Module** - Ye module UI testing scans ko schedule karne ki facility deta hai. Users future dates par scans schedule kar sakte hain aur email notifications receive kar sakte hain.

## Module Ka Kaam Kya Hai?

Ye module:
- Future dates par scans schedule karne ki facility deta hai
- Scheduled scans ko automatically execute karta hai
- Scan results ko email karta hai
- Schedule management provide karta hai (list, cancel)
- Whole-site scans ko schedule karta hai
- Previous scan URLs ko reuse karta hai

## Flow Kaise Kaam Karta Hai?

### 1. Schedule Creation
- User schedule scan page par jata hai
- Date aur time select karta hai (future date honi chahiye)
- URL provide kar sakta hai ya previous URL use kar sakta hai
- Schedule create karta hai

### 2. Schedule Storage
- Schedule database mein store hota hai (`scheduled_scans` collection)
- Schedule details include:
  - Organization ID
  - Scheduled by (user ID)
  - Email address
  - Scheduled for (timestamp)
  - URL (optional)
  - Status (scheduled/running/completed/failed/cancelled)

### 3. Job Scheduling
- APScheduler use karke job schedule hoti hai
- Job specific date/time par trigger hoti hai
- Job ID schedule ID se match hota hai

### 4. Job Execution
- Scheduled time par job automatically execute hoti hai
- Status "scheduled" se "running" mein change hota hai
- URL determine hoti hai:
  - Agar schedule mein URL hai, wo use hoti hai
  - Agar nahi hai, last scanned URL use hoti hai
  - Agar koi previous scan nahi hai, error return hota hai

### 5. Scan Execution
- Whole-site scan execute hoti hai
- `scan_whole_site()` function call hota hai
- Scan parameters:
  - max_pages: 50
  - max_depth: 3
  - scan_mode: "all"
  - parallel_scans: 3

### 6. Result Processing
- Scan results collect hote hain
- AI recommendations generate hote hain
- Results database mein store hote hain (`ui_testing_site_results`)

### 7. Email Notification
- Scan complete hone par email send hoti hai
- Email mein include hota hai:
  - Scan summary
  - Accessibility score
  - Security score
  - Key findings
  - Recommendations
  - Link to detailed report

### 8. Status Update
- Status "running" se "completed" mein change hota hai
- Agar error aaye, status "failed" ho jata hai
- Error message store hota hai

## Technical Working

### Scheduler Setup
1. **APScheduler**: AsyncIOScheduler use hota hai
2. **Job Storage**: In-memory job storage
3. **Job Rehydration**: Server restart par jobs rehydrate hote hain database se

### Job Execution Flow
1. **Trigger**: DateTrigger use hota hai specific date/time ke liye
2. **Function Call**: `_execute_scheduled_scan()` function call hoti hai
3. **Error Handling**: Try-catch blocks use hote hain
4. **Status Updates**: Database mein status updates hote hain

### URL Resolution
1. **Stored URL**: Agar schedule mein URL hai, wo use hoti hai
2. **Last Scan URL**: Agar nahi hai, last whole-site scan URL use hoti hai
3. **Fallback**: Agar wo bhi nahi hai, last single-page scan URL use hoti hai
4. **Error**: Agar koi URL nahi milti, error return hota hai

### Email Generation
1. **Template**: HTML email template use hota hai
2. **Data Formatting**: Scan results ko format kiya jata hai
3. **Email Sending**: `send_simple_email()` function use hoti hai
4. **Error Handling**: Email failure par log hota hai, scan fail nahi hota

## Files Jahan Code Present Hai

### Backend Files (Python)

1. **`Complytics Backend/routes/ui_testing.py`**
   - Main schedule scan endpoints
   - `schedule_scan()` - Schedule creation endpoint
   - `list_schedules()` - List schedules endpoint
   - `cancel_schedule()` - Cancel schedule endpoint
   - `_execute_scheduled_scan()` - Job execution function
   - `_run_scan_and_persist()` - Scan execution helper
   - Scheduler initialization
   - Job rehydration logic

2. **`Complytics Backend/ui_testing/scanners/site_scanner.py`**
   - `scan_whole_site()` - Whole-site scan function
   - `SiteScanOrchestrator` class - Scan orchestration

3. **`Complytics Backend/ui_testing/ai/recommendations.py`**
   - `generate_findings_and_recommendations()` - AI recommendations

4. **`Complytics Backend/utils/security.py`**
   - `send_simple_email()` - Email sending function

5. **`Complytics Backend/db.py`**
   - Database connection
   - MongoDB operations

### Frontend Files (React/JSX)

1. **`src/components/team/ScheduleScan.jsx`**
   - Main schedule scan UI component
   - Date/time picker
   - URL input (optional)
   - Previous URL option
   - Schedule list display
   - Cancel schedule functionality
   - Scan now modal

2. **`src/lib/api.js`**
   - API utility functions

### Database Collections

1. **`scheduled_scans`** - Schedule storage
   - Fields:
     - `_id` - Schedule ID
     - `organization_id` - Organization ID
     - `scheduled_by` - User ID
     - `email` - Email address
     - `url` - URL (optional)
     - `scheduled_for` - Timestamp
     - `status` - Status (scheduled/running/completed/failed/cancelled)
     - `created_at` - Creation timestamp
     - `updated_at` - Update timestamp
     - `error` - Error message (if failed)

2. **`ui_testing_site_results`** - Scan results storage

## Key Functions

### Main Functions in `ui_testing.py`:

1. **`schedule_scan()`**
   - Schedule creation endpoint
   - Date validation
   - Database storage
   - Job scheduling

2. **`_execute_scheduled_scan()`**
   - Job execution function
   - URL resolution
   - Scan execution
   - Result processing
   - Email sending
   - Status updates

3. **`list_schedules()`**
   - List all schedules for organization
   - Filter by status
   - Sort by scheduled_for

4. **`cancel_schedule()`**
   - Cancel scheduled scan
   - Remove job from scheduler
   - Update database status

5. **`_run_scan_and_persist()`**
   - Helper function for scan execution
   - Result persistence

### Scheduler Functions:

1. **Scheduler Initialization**
   - `AsyncIOScheduler()` create hota hai
   - Scheduler start hota hai
   - Global variable mein store hota hai

2. **Job Rehydration**
   - Server startup par jobs rehydrate hote hain
   - Database se pending schedules load hote hain
   - Jobs re-schedule hote hain

## API Endpoints

- `POST /api/ui/schedule` - Create schedule
  - Request body:
    - `run_at_iso` - ISO format datetime (required)
    - `url` - URL (optional)
  - Response:
    - `id` - Schedule ID
    - `scheduled_for` - Timestamp
    - `status` - Status

- `GET /api/ui/schedules` - List schedules
  - Response:
    - `schedules` - Array of schedules

- `DELETE /api/ui/schedule/{id}` - Cancel schedule
  - Response:
    - `message` - Success message

## Schedule Statuses

1. **scheduled** - Scan scheduled hai, abhi execute nahi hua
2. **running** - Scan currently execute ho rahi hai
3. **completed** - Scan successfully complete ho gayi
4. **failed** - Scan fail ho gayi (error message available)
5. **cancelled** - Schedule cancel kar di gayi

## URL Resolution Logic

1. **Priority 1**: Schedule mein stored URL
2. **Priority 2**: Last whole-site scan URL (`ui_testing_site_results`)
3. **Priority 3**: Last single-page scan URL (`ui_testing_results`)
4. **Error**: Agar koi URL nahi milti, scan fail ho jati hai

## Email Notification

Email mein include hota hai:
- Scan completion message
- Website URL
- Scan summary
- Accessibility score
- Security score
- Total pages scanned
- Key findings
- Recommendations
- Link to detailed report

## Permissions

- Sirf **compliance_team**, **admin**, aur **superadmin** roles schedule kar sakte hain
- Other roles ko 403 error milta hai

## Dependencies

- **APScheduler** - Task scheduling
- **FastAPI** - Web framework
- **MongoDB** - Database
- **AsyncIO** - Async operations

## Error Handling

1. **Invalid Date**: Agar past date hai, error return hota hai
2. **No URL**: Agar koi URL nahi milti, scan fail ho jati hai
3. **Scan Failure**: Agar scan fail hoti hai, status "failed" ho jata hai
4. **Email Failure**: Email failure par log hota hai, scan fail nahi hoti

## Summary

Ye module scan scheduling ki complete facility provide karta hai:
- Future dates par scans schedule karna
- Automatic execution
- Email notifications
- Schedule management
- URL reuse functionality
- Error handling
- Status tracking

Sab kuch APScheduler aur async operations ke combination se kaam karta hai.

