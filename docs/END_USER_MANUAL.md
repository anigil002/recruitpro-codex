# RecruitPro - End User Manual

**Version:** 1.0  
**Date:** November 25, 2025  
**Audience:** Recruiters, Hiring Managers, Administrators

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [User Interface Overview](#user-interface-overview)
3. [Managing Projects](#managing-projects)
4. [Managing Positions](#managing-positions)
5. [Managing Candidates](#managing-candidates)
6. [AI-Powered Features](#ai-powered-features)
7. [Candidate Sourcing](#candidate-sourcing)
8. [Interview Management](#interview-management)
9. [Document Management](#document-management)
10. [Reports & Analytics](#reports--analytics)
11. [Settings & Configuration](#settings--configuration)
12. [Troubleshooting](#troubleshooting)

---

## Getting Started

### Creating Your Account

1. Navigate to the RecruitPro login page
2. Click **"Create Account"** or **"Register"**
3. Fill in the registration form:
   - **Email Address**: Your work email
   - **Password**: Must be at least 8 characters with uppercase, lowercase, digit, and special character
   - **Full Name**: Your name as it should appear in the system
4. Click **"Register"**
5. You'll be automatically logged in and redirected to the dashboard

**Note**: New accounts are assigned the "Recruiter" role by default. Contact your administrator for role upgrades.

### Logging In

1. Go to the RecruitPro login page
2. Enter your **Email Address** and **Password**
3. Click **"Sign In"**
4. You'll be directed to your dashboard

**Session Duration**: Sessions last 60 minutes by default. You'll need to log in again after this period.

### First-Time Setup

After logging in for the first time:

1. **Update Your Profile**:
   - Click your name in the top-right corner
   - Select "Profile Settings"
   - Update your preferences

2. **Configure Integrations** (Admin only):
   - Navigate to Settings → Integrations
   - Add API keys for:
     - Google Gemini (for AI features)
     - Google Custom Search (for LinkedIn sourcing)
     - SmartRecruiters (if applicable)

3. **Create Your First Project**:
   - Click "Projects" in the sidebar
   - Click "+ New Project"
   - Fill in project details and save

---

## User Interface Overview

### Main Navigation

**Sidebar Menu**:
- **Dashboard**: Overview of all activity, projects, and candidates
- **Projects**: Manage recruitment projects
- **Candidates**: View and manage all candidates
- **Positions**: Browse open positions across projects
- **Interviews**: Schedule and track interviews
- **Activity**: View system activity feed
- **Settings**: Configure integrations and preferences (Admin only)

### Dashboard Widgets

1. **Statistics Cards**:
   - Total Projects (with breakdown by status)
   - Open Positions
   - Total Candidates (with breakdown by status)
   - Active Sourcing Jobs

2. **Recent Projects**: Last 5 projects with position count

3. **Open Positions**: All active positions across projects

4. **Candidate Pipeline**: Visual chart showing candidates by status (New, Screening, Interviewed, Offered, Hired, Rejected)

5. **Recent Candidates**: Latest 8 candidates added

6. **Activity Feed**: Recent actions by users and AI

7. **Sourcing Summary**: Active sourcing jobs and profiles found

8. **Upcoming Interviews**: Next 5 scheduled interviews

---

## Managing Projects

### Creating a Project

1. Click **"Projects"** in the sidebar
2. Click **"+ New Project"** button
3. Fill in the project form:
   - **Project Name** (required): e.g., "Dubai Metro Blue Line Extension"
   - **Client** (required): e.g., "Roads and Transport Authority"
   - **Sector**: Select from dropdown (Infrastructure, Aviation, Rail, Energy, Buildings, Healthcare)
   - **Location/Region**: e.g., "GCC", "Middle East", "North America"
   - **Summary**: Brief description of the project
   - **Priority**: Low, Medium, High, or Urgent
   - **Target Hires**: Number of positions to fill
   - **Tags**: Custom labels (comma-separated)
4. Click **"Create Project"**

**Result**: Project is created with status "Active". You'll be redirected to the project detail page.

### Viewing Project Details

1. Click **"Projects"** in the sidebar
2. Click on any project name or **"View"** button

**Project Detail Page Shows**:
- Project summary and metadata
- Position count by status (Open, Closed, Draft)
- Candidate count by status
- Recent candidates
- Uploaded documents
- Activity feed (project-specific)
- Market research status (if requested)

### Editing a Project

1. Navigate to the project detail page
2. Click **"Edit Project"** button
3. Update any fields
4. Click **"Save Changes"**

**Editable Fields**: Name, client, sector, location, summary, priority, target hires, tags, status

### Project Status Lifecycle

- **Active**: Actively recruiting
- **On-Hold**: Temporarily paused
- **Completed**: All hires made
- **Archived**: Closed, no longer active

**To Change Status**:
1. Open project detail page
2. Click **"Edit Project"**
3. Select new status from dropdown
4. Save changes

### Uploading Project Documents

1. Navigate to project detail page
2. Scroll to **"Documents"** section
3. Click **"Upload Document"**
4. Select file (PDF, DOCX, CSV, TXT, max 50MB)
5. Click **"Upload"**

**AI Analysis**: If document contains project or position information, RecruitPro will automatically extract and suggest creating positions.

### Deleting/Archiving a Project

1. Navigate to project detail page
2. Click **"More Actions"** → **"Archive Project"** or **"Delete Project"**
3. Confirm the action

**Note**: Archiving sets status to "Archived". Deleting is permanent and cannot be undone. Positions and candidates remain accessible.

---

## Managing Positions

### Creating a Position

1. Navigate to a project detail page
2. Click **"+ Add Position"** button
3. Fill in the position form:
   - **Job Title** (required): e.g., "Senior Project Manager"
   - **Department**: e.g., "Project Management Office"
   - **Location** (required): e.g., "Dubai, UAE"
   - **Experience Level**: Entry, Mid, Senior, or Executive
   - **Description**: Detailed role description
   - **Qualifications**: Bullet list (one per line)
   - **Responsibilities**: Bullet list
   - **Requirements**: Must-have requirements (bullet list)
   - **Number of Openings**: Default 1
4. Click **"Create Position"**

**Result**: Position is created with status "Draft". It will appear in the project positions list.

### Generating Job Description with AI

1. When creating/editing a position, click **"Generate JD with AI"** button
2. Enter:
   - Job title
   - Brief context (project, sector, seniority)
3. Click **"Generate"**
4. AI generates:
   - Summary
   - Responsibilities
   - Requirements (core + nice-to-have)
   - Compensation notes
5. Review and edit as needed
6. Click **"Save Position"**

**Tip**: AI JD generation works best when you provide context about the project and seniority level.

### Viewing Position Details

1. Click **"Positions"** in sidebar OR navigate via project
2. Click on position title

**Position Detail Page Shows**:
- Job title, department, location, experience level
- Description
- Qualifications list
- Responsibilities list
- Requirements (must-have vs nice-to-have)
- Number of openings
- Applicant count
- Linked candidates

### Editing a Position

1. Navigate to position detail page
2. Click **"Edit Position"**
3. Update fields
4. Click **"Save Changes"**

### Position Status

- **Draft**: Not yet published, being prepared
- **Open**: Actively accepting applications
- **Closed**: No longer accepting applications

**To Change Status**:
1. Edit position
2. Update "Status" dropdown
3. Save

### Deleting a Position

1. Navigate to position detail page
2. Click **"More Actions"** → **"Delete Position"**
3. Confirm deletion

**Note**: Candidate associations are cleared, but screening results are preserved.

---

## Managing Candidates

### Adding a Candidate Manually

1. Click **"Candidates"** in sidebar
2. Click **"+ Add Candidate"** button
3. Fill in the form:
   - **Name** (required)
   - **Email** (required)
   - **Phone**
   - **Source**: How you found them (LinkedIn, Referral, Website, etc.)
   - **Status**: New, Sourced, Screening, Interviewed, Offered, Hired, Rejected
   - **Project**: Link to a project (optional)
   - **Position**: Link to a position (optional)
   - **Resume URL**: Link to CV (optional)
   - **Tags**: Custom labels (comma-separated)
   - **Rating**: 1-5 stars
4. Click **"Add Candidate"**

**Result**: Candidate is created and appears in the candidates list.

### Uploading Candidate Resume

1. Navigate to candidate profile page
2. Click **"Upload Resume"** button
3. Select file (PDF or DOCX, max 50MB)
4. Click **"Upload"**

**Result**: Resume is stored and linked to candidate. You can now use AI screening.

### Viewing Candidate Profile

1. Click **"Candidates"** in sidebar
2. Click on candidate name

**Candidate Profile Shows**:
- Personal information (name, email, phone)
- Source and current status
- Resume/CV link (download button)
- Associated project and position
- Tags and rating
- **AI Screening Results** (if screened):
  - Overall fit assessment
  - Recommended roles
  - Key strengths
  - Potential gaps
  - Compliance table (requirement matches)
  - Final recommendation
- Status change history
- Activity feed (candidate-specific)

### Editing Candidate Information

1. Navigate to candidate profile
2. Click **"Edit Candidate"**
3. Update fields
4. Click **"Save Changes"**

**Status Change Tracking**: When you change a candidate's status, the system automatically logs:
- Old status → New status
- Who made the change
- When it was changed

This creates an audit trail visible on the candidate profile.

### Screening a Candidate with AI

**Prerequisites**:
- Candidate must have a resume uploaded
- Candidate must be linked to a position (or you can select one during screening)

**Steps**:
1. Navigate to candidate profile
2. Click **"Screen with AI"** button
3. Select position to screen against (if not already linked)
4. Click **"Start Screening"**

**Process**:
1. System creates a background job
2. AI analyzes the entire CV (no truncation)
3. Compares against position requirements
4. Generates detailed screening report

**Results Appear in ~20-30 seconds**:
- Overall Fit: Strong Match / Potential Match / Low Match
- Recommended Roles
- Key Strengths (4 bullet points)
- Potential Gaps (2 bullet points)
- **Compliance Table**: Each requirement marked as:
  - ✅ Complying (met with evidence)
  - ❌ Not Complying (not met)
  - ⚠️ Not Mentioned (CV lacks evidence)
- Final Recommendation with detailed justification
- Final Decision: Proceed to interview / Suitable for lower role / Reject

**Tip**: Screening reports follow Egis Middle East & North America standards for construction, engineering, and infrastructure roles.

### Changing Candidate Status

**Status Options**:
- **New**: Just added to system
- **Sourced**: Found via sourcing
- **Screening**: Under CV review
- **Interviewed**: Interview conducted
- **Offered**: Job offer extended
- **Hired**: Accepted offer
- **Rejected**: Not progressing

**To Change Status**:
1. Navigate to candidate profile
2. Click current status badge OR click "Edit Candidate"
3. Select new status from dropdown
4. Save

**Result**: Status updated, history logged, project hire count recalculated (if status is "Hired").

### Bulk Candidate Operations

**Use Case**: Update multiple candidates at once

**Bulk Actions Available**:
- Change status
- Add tags
- Remove tags
- Assign to project
- Assign to position

**Steps**:
1. Go to **"Candidates"** list
2. Select multiple candidates using checkboxes
3. Click **"Bulk Actions"** dropdown
4. Choose action
5. Fill in parameters (e.g., new status)
6. Click **"Apply"**

**Result**: All selected candidates are updated simultaneously.

### Importing Candidates from CSV/Excel

1. Click **"Candidates"** in sidebar
2. Click **"Import"** button
3. Download CSV template (optional)
4. Prepare your file with columns:
   - Name
   - Email
   - Phone
   - Resume URL (optional)
   - Tags (comma-separated)
5. Click **"Choose File"** and select your CSV/XLSX
6. Click **"Import"**

**Result**: System validates each row and displays:
- Created: N candidates
- Updated: M candidates (matched by email)
- Errors: List of rows with issues

### Exporting Candidates to CSV/Excel

1. Click **"Candidates"** in sidebar
2. Apply filters if needed (project, status, etc.)
3. Click **"Export"** button
4. Choose format (CSV or Excel)
5. Click **"Download"**

**Result**: File downloads with all candidates matching your filters.

### Deleting a Candidate

1. Navigate to candidate profile
2. Click **"More Actions"** → **"Delete Candidate"**
3. Confirm deletion

**Note**: This is a "soft delete" - candidate is marked as deleted but data is retained. Administrators can restore if needed.

---

## AI-Powered Features

### CV Screening (Detailed)

**When to Use**:
- You have a candidate with a resume
- You want to assess fit against a specific position
- You need an evidence-based recommendation

**Best Practices**:
- Ensure position requirements are well-defined
- Upload complete CV (all pages)
- Review AI recommendations, but apply human judgment

**Understanding the Output**:

**Overall Fit**:
- **Strong Match**: 70%+ requirements met, proceed to interview
- **Potential Match**: 50-69% requirements met, consider for lower role or with training
- **Low Match**: <50% requirements met, likely not suitable

**Compliance Table**: Shows each requirement with:
- Requirement description
- Compliance status (✅ Met, ❌ Not Met, ⚠️ Not Mentioned)
- Evidence from CV (with page/section reference)

**Final Decision**:
- **Proceed to technical interview**: Strong candidate, worth interviewing
- **Suitable for a lower-grade role**: Skills present but not at required seniority
- **Reject**: Does not meet minimum requirements

### Job Description Generation

**When to Use**:
- Creating a new position
- Need inspiration for JD content
- Want to standardize JD format

**Steps**:
1. Click **"Generate JD with AI"** when creating/editing position
2. Provide:
   - Job title
   - Project context
   - Sector
   - Seniority level
3. Review generated JD
4. Edit as needed

**Output Includes**:
- Role summary
- Key responsibilities (bullet list)
- Requirements (core + nice-to-have)
- Compensation notes

### Market Research

**When to Use**:
- Planning a new project
- Need to understand talent availability
- Want comparable project examples
- Seeking market insights

**Steps**:
1. Navigate to project detail page
2. Click **"Request Market Research"** button
3. Confirm region and sector (pre-filled from project)
4. Click **"Generate Research"**

**Process**: Background job runs (takes 20-60 seconds)

**Output**:
- **Market Insights**: Trends, challenges, comparable projects
- **Talent Availability**: Supply/demand assessment
- **Comparable Projects**: Similar initiatives with details
- **Sources**: Citations and links

**Accessing Results**:
- Results appear on project detail page under "Market Research" section
- Click "View Report" to see full details

### Salary Benchmarking

**When to Use**:
- Determining compensation for a role
- Negotiating with candidates
- Budget planning

**Steps**:
1. Click **"Research"** in top menu
2. Select **"Salary Benchmark"**
3. Fill in the form:
   - Job Title
   - Region (GCC, Middle East, US, UK, etc.)
   - Sector (Infrastructure, Aviation, etc.)
   - Seniority (Junior, Mid, Senior, Principal, etc.)
   - Currency (USD, AED, GBP, etc.)
4. Click **"Get Benchmark"**

**Output**:
- Annual Salary Range (Min / Mid / Max)
- Rationale (calculation explanation)
- Sources (Glassdoor, PayScale, Hays, etc.)

**Caching**: Results are cached for 90 days. Identical queries return cached data instantly.

### Outreach Email Generation

**When to Use**:
- Reaching out to passive candidates
- Need a professional, personalized email
- Want to save time on email drafting

**Steps**:
1. Navigate to candidate profile
2. Click **"Generate Outreach Email"**
3. Select template:
   - **Standard**: Conversational, 15-min call request
   - **Executive**: Formal, leadership-focused
   - **Technical**: Technical pod, engineering emphasis
4. Review/edit highlights (auto-populated from position)
5. Click **"Generate"**

**Output**:
- Email subject line
- Email body (personalized with candidate name, role details)

**Next Steps**:
- Copy email to clipboard
- Paste into your email client
- Send to candidate

### Call Script Generation

**When to Use**:
- Preparing for a screening call
- Want structured conversation flow
- Need consistent screening process

**Steps**:
1. Navigate to candidate profile
2. Click **"Generate Call Script"**
3. Review generated script

**Output**:
- **Introduction**: Opening and purpose statement
- **Context**: Project/role overview
- **Motivation Questions**: Probe candidate interest
- **Technical Questions**: Assess skills and experience
- **Managerial Questions**: (for leadership roles) Delegation, feedback, team management
- **Objection Handling**: Responses to common concerns (timing, relocation, etc.)
- **Closing**: Next steps

**Tip**: Print script or keep open on second screen during call.

### Chatbot Assistant

**When to Use**:
- Quick questions about recruitment workflows
- Need to trigger sourcing or research
- Want pipeline status summary

**Accessing Chatbot**:
- Click **"Chat"** icon in bottom-right corner
- Chat window opens

**What It Can Do**:
- Summarize candidate pipeline
- Suggest sourcing strategies
- Trigger market research
- Provide salary benchmarks
- Answer recruitment questions

**Example Interactions**:
- "What's the status of my Dubai Metro project?"
- "Launch a sourcing job for Senior Civil Engineers"
- "Give me salary benchmark for Project Manager in GCC"
- "Help me with market research for aviation sector"

---

## Candidate Sourcing

### LinkedIn X-Ray Search

**Purpose**: Find passive candidates on LinkedIn using Google search

**Prerequisites**:
- Administrator must configure Google Custom Search API
- API key and Custom Search Engine ID required

**Steps**:
1. Navigate to **"Sourcing"** in top menu
2. Select **"LinkedIn X-Ray"**
3. Fill in the form:
   - **Job Title**: e.g., "Project Manager"
   - **Skills**: e.g., "PMO, Stakeholder Management, P6"
   - **Location**: e.g., "Dubai" (optional)
   - **Seniority**: e.g., "Senior" (optional)
   - **Max Results**: Default 20, max 100
4. Click **"Start Sourcing"**

**Process**:
1. System generates boolean search string
2. Creates sourcing job (status=pending)
3. Executes Google Custom Search
4. Parses LinkedIn profile URLs
5. Stores results

**Viewing Results**:
- Navigate to **"Sourcing"** → **"Overview"**
- Click on sourcing job
- View list of profiles with:
  - Name
  - Title
  - Company
  - Location
  - Profile URL (clickable)
  - Quality Score (0-100)

**Next Steps**:
- Review profiles
- Click "Convert to Candidate" to add to system
- Profile becomes a candidate with source="LinkedIn X-Ray"

### SmartRecruiters Bulk Import

**Purpose**: Import candidates from SmartRecruiters ATS

**Prerequisites**:
- SmartRecruiters account credentials
- Administrator must configure integration

**Steps**:
1. Navigate to **"Sourcing"** → **"SmartRecruiters Import"**
2. Enter:
   - Company ID
   - Filters (position, status, tags)
3. Click **"Start Import"**

**Process**:
1. System launches browser automation (Playwright)
2. Logs into SmartRecruiters
3. Navigates to candidate list
4. Scrapes candidate data
5. Maps to RecruitPro format
6. Bulk imports candidates

**Result**: Candidates are created with source="SmartRecruiters"

**Troubleshooting**:
- **Login Failure**: Check credentials in Settings
- **CAPTCHA Detected**: Manual login required (contact admin)
- **Scrape Error**: Platform may have changed; contact support

### Viewing Sourcing Jobs

**Sourcing Overview Page**:
- Lists all sourcing jobs (active and completed)
- Shows platform (LinkedIn, SmartRecruiters)
- Displays status (Pending, In Progress, Completed, Failed)
- Shows progress percentage
- Displays candidate count found

**Filtering**:
- Filter by project
- Filter by platform
- Filter by status

---

## Interview Management

### Scheduling an Interview

1. Navigate to candidate profile
2. Click **"Schedule Interview"** button
3. Fill in the form:
   - **Date & Time**: Pick from calendar
   - **Mode**: Phone, In-Person, or Virtual
   - **Location**: Office address or video link
   - **Notes**: Any preparation notes
4. Click **"Schedule"**

**Result**: Interview is created and appears on dashboard "Upcoming Interviews" widget.

**Notifications**: (Future feature) Automated email reminders to interviewers and candidates.

### Viewing Interviews

**Dashboard Widget**: Shows next 5 interviews

**Full Interview List**:
1. Click **"Interviews"** in sidebar
2. View all scheduled interviews
3. Filter by:
   - Project
   - Position
   - Candidate
   - Date range

### Updating Interview Details

1. Navigate to interview (from dashboard or interviews list)
2. Click **"Edit Interview"**
3. Update:
   - Date/time
   - Mode
   - Location
   - Notes
4. Click **"Save Changes"**

### Adding Interview Feedback

**After Interview Completion**:
1. Navigate to interview
2. Click **"Add Feedback"**
3. Enter feedback notes
4. Click **"Save Feedback"**

**Feedback Storage**: Stored in `interviews.feedback` field, visible on candidate profile.

### Canceling an Interview

1. Navigate to interview
2. Click **"More Actions"** → **"Cancel Interview"**
3. Confirm cancellation

**Result**: Interview is deleted from system.

---

## Document Management

### Uploading Documents

**Project Documents**:
1. Navigate to project detail page
2. Scroll to "Documents" section
3. Click "Upload Document"
4. Select file (PDF, DOCX, CSV, TXT)
5. Upload

**Candidate Documents** (Resumes):
1. Navigate to candidate profile
2. Click "Upload Resume"
3. Select file
4. Upload

**Supported Formats**:
- PDF (preferred for resumes)
- DOCX (Microsoft Word)
- CSV (spreadsheets)
- TXT (plain text)

**File Size Limit**: 50 MB per file

### Downloading Documents

1. Navigate to document location (project or candidate)
2. Click document filename or "Download" button
3. File downloads to your device

### Viewing Document Analysis

**If Document Contains Structured Data**:
- System automatically analyzes uploaded documents
- Extracts project information
- Extracts position listings
- Suggests creating positions

**Viewing Analysis**:
1. Upload document to project
2. Wait for analysis (10-30 seconds)
3. Review extracted information
4. Click "Create Positions" to auto-populate from document

### Deleting Documents

1. Navigate to document location
2. Click "Delete" icon next to document
3. Confirm deletion

**Note**: Deletion is permanent and cannot be undone.

---

## Reports & Analytics

### Dashboard Statistics

**Main Dashboard** provides real-time statistics:
- Total projects by status
- Open positions count
- Total candidates by status
- Active sourcing jobs
- Recent activity

### Activity Feed

**Viewing Activity**:
1. Click **"Activity"** in sidebar
2. View chronological list of all actions

**Filters**:
- Event type (login, project_created, candidate_added, etc.)
- Actor (user or AI)
- Date range
- Project, position, or candidate

**Use Cases**:
- Audit trail
- Team activity monitoring
- Compliance reporting

### Candidate Pipeline Report

**Dashboard Visualization**:
- Pie chart showing candidates by status
- Color-coded for easy reading

**Interpreting the Pipeline**:
- **New**: Candidates just added
- **Screening**: Under AI review or manual screening
- **Interviewed**: Completed initial interviews
- **Offered**: Job offer extended
- **Hired**: Accepted and joined
- **Rejected**: Not progressing

### Sourcing Effectiveness

**Sourcing Overview Page** shows:
- Total sourcing jobs run
- Profiles found by platform
- Quality score distribution
- Conversion rate (sourced → hired)

### Export Reports

**Candidate Export**:
- Go to Candidates list
- Apply filters
- Click "Export"
- Download CSV/Excel

**Use Cases**:
- Monthly recruitment reports
- Client reporting
- Data analysis in Excel/Power BI

---

## Settings & Configuration

### User Profile Settings

1. Click your name in top-right corner
2. Select "Profile Settings"
3. Update:
   - Name
   - Email (view only, cannot change)
   - Password (click "Change Password")
   - Notification preferences
   - Default filters
4. Save changes

### Integration Settings (Admin Only)

**Accessing Settings**:
1. Click **"Settings"** in sidebar
2. View integration status

**Configuring Gemini AI**:
1. Click "Configure" next to "Gemini API"
2. Enter API key (get from Google AI Studio)
3. Save

**Configuring Google Custom Search**:
1. Click "Configure" next to "Google Custom Search"
2. Enter API key
3. Enter Custom Search Engine ID
4. Save

**Configuring SmartRecruiters**:
1. Click "Configure" next to "SmartRecruiters"
2. Enter email
3. Enter password
4. Save

**Security**: All credentials are encrypted before storage.

### Managing Users (Admin Only)

1. Click **"Admin"** in top menu
2. Select **"Users"**
3. View all workspace users

**Changing User Roles**:
1. Find user in list
2. Click "Change Role"
3. Select new role (recruiter, admin, super_admin)
4. Confirm

**Deactivating Users** (Future feature):
- Click "Deactivate" next to user
- User cannot log in but data is preserved

---

## Troubleshooting

### Cannot Log In

**Symptoms**: "Invalid email or password" error

**Solutions**:
1. Verify email address is correct
2. Check Caps Lock is off (passwords are case-sensitive)
3. Try "Forgot Password" (future feature)
4. Contact administrator to verify account exists

### AI Features Not Working

**Symptoms**: "AI unavailable" or "Gemini API error"

**Solutions**:
1. Check Settings → Integrations → Gemini API is configured
2. Verify API key is valid (test in Google AI Studio)
3. Check internet connectivity
4. Contact administrator

**Note**: System has fallback logic - AI features will still work with reduced functionality.

### Sourcing Jobs Fail

**LinkedIn X-Ray Fails**:
- Verify Google Custom Search is configured
- Check API quota (free tier: 100 queries/day)
- Try reducing max_results parameter

**SmartRecruiters Import Fails**:
- Verify credentials in Settings
- Check SmartRecruiters website is accessible
- CAPTCHA may be blocking automation (contact admin)

### Uploaded Documents Not Processing

**Symptoms**: Document uploads but no analysis results

**Solutions**:
1. Check file format (PDF, DOCX only)
2. Check file size (<50 MB)
3. Verify document contains text (not scanned image)
4. Wait up to 60 seconds for background processing
5. Refresh page

### Candidate Status Not Updating

**Symptoms**: Status change doesn't save

**Solutions**:
1. Verify you have permission (own candidate or admin)
2. Check network connectivity
3. Try refreshing page and updating again
4. Contact support if persists

### Performance Issues

**Symptoms**: Slow loading, timeouts

**Solutions**:
1. Check internet connection
2. Try refreshing browser (Ctrl+F5 or Cmd+Shift+R)
3. Clear browser cache
4. Try different browser
5. Contact administrator if persistent (may indicate server issues)

### Missing Data or Features

**Symptoms**: Cannot see certain projects, candidates, or features

**Reasons**:
- **Permissions**: You may not have access (recruiter role only sees own data)
- **Filters**: Active filters may be hiding data (check filter settings)
- **Feature Flags**: Administrator may have disabled certain features

**Solutions**:
1. Check filter settings (clear all filters)
2. Verify you have appropriate role (contact admin)
3. Contact administrator to enable feature flags

---

## Best Practices

### Project Management
- Create projects at the beginning of each engagement
- Keep project summaries updated
- Use tags for cross-project tracking
- Archive completed projects to reduce clutter

### Candidate Management
- Always link candidates to projects/positions when possible
- Use AI screening for consistent assessments
- Update candidate status promptly after interviews
- Add tags for segmentation (e.g., "vip", "urgent", "relocatable")
- Maintain status history for audit trail

### AI Usage
- Review AI recommendations critically
- Use AI screening as a first pass, not final decision
- Provide context when generating JDs or market research
- Update position requirements to improve AI accuracy

### Document Organization
- Use consistent naming conventions
- Upload project briefs and SOWs to projects
- Upload resumes to candidate profiles (not projects)
- Delete obsolete documents regularly

### Sourcing
- Run sourcing jobs regularly to build pipeline
- Review sourced profiles within 24 hours
- Convert promising profiles to candidates quickly
- Track source effectiveness (LinkedIn vs SmartRecruiters)

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl/Cmd + K` | Open search |
| `Ctrl/Cmd + N` | New project (on projects page) |
| `Ctrl/Cmd + S` | Save form (when editing) |
| `Esc` | Close modal/dialog |
| `Tab` | Navigate form fields |

---

## Getting Help

### In-App Support

- **Help Icon**: Click "?" icon in top-right corner
- **Tooltips**: Hover over field labels for hints
- **Validation Messages**: Red text indicates errors

### Documentation

- **This Manual**: Comprehensive guide to all features
- **API Documentation**: For developers (available at `/docs`)
- **Release Notes**: See latest features and changes

### Contact Support

- **Email**: support@recruitpro.com
- **GitHub Issues**: https://github.com/recruitprohq/recruitpro-codex/issues
- **Administrator**: Contact your workspace admin for account or permission issues

---

## Glossary

- **ATS**: Applicant Tracking System
- **CV Screening**: AI-powered resume analysis
- **Compliance Table**: Requirement-by-requirement assessment of candidate fit
- **Gemini API**: Google's AI service powering RecruitPro features
- **JWT Token**: JSON Web Token for authentication
- **Sourcing**: Finding passive candidates via LinkedIn or other platforms
- **X-Ray Search**: Using Google to search LinkedIn profiles
- **Egis Standard**: Screening format used for construction/engineering roles
- **PMO**: Project Management Office
- **JD**: Job Description
- **GCC**: Gulf Cooperation Council (UAE, Saudi, Qatar, etc.)

---

**End of End User Manual**
