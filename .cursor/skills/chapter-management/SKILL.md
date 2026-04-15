---
name: chapter-management
description: >-
  Add, update, or manage subjects and chapters in the Delta Learn backend.
  Use when adding new chapter content, creating new subjects, or updating
  existing chapter data via Django Admin, API, MCP, or fixtures.
---

# Chapter & Subject Management

## Option A: Django Admin (preferred for manual edits)

1. Go to `http://localhost:8000/admin/`
2. Log in with the superuser account (`cosmoknight11` / `helloDelta123`)
3. Navigate to **Chapters > Subjects** to add/edit subjects
4. Navigate to **Chapters > Chapters** to add/edit chapters
5. Use inline editing to add Questions and Takeaways directly on the Chapter page
6. Use the **Preview** link on any chapter to see it rendered as it appears on the frontend

## Option B: MCP Server (AI-assisted authoring)

The Delta Learn MCP server provides tools for content management with a staged review workflow.

### How it works
1. AI agent calls write tools (e.g., `create_chapter`, `create_question`)
2. Each write creates a **staged request** (not a direct DB change)
3. Admin reviews staged requests in Django Admin (Chapters > Staged Requests)
4. Admin approves → change is applied to the database
5. Admin rejects → change is discarded with an optional note

### Available MCP tools
- `list_subjects` / `get_subject` / `get_chapter` — read content directly
- `create_subject` / `create_chapter` / `create_question` / `create_takeaway` — propose new content
- `update_chapter` / `update_question` — propose edits
- `delete_question` / `delete_takeaway` — propose deletions
- `list_staged_requests` / `get_staged_request` — check status of proposals

### Available MCP prompts
- `write_chapter` — guided workflow for writing a complete chapter
- `write_question` — guided workflow for a single question
- `review_chapter` — quality checklist for existing content

## Option C: REST API (programmatic)

### Direct CRUD (admin only)
- `POST /api/manage/chapters/` — create chapter directly
- `POST /api/manage/questions/` — create question directly
- Full CRUD on all content models at `/api/manage/`

### Staged requests (any authenticated user)
- `POST /api/staged/` — create a staged request
- `POST /api/staged/{id}/approve/` — admin approves (applies change)
- `POST /api/staged/{id}/reject/` — admin rejects

## Option D: JSON Fixtures + Seed Command (bulk operations)

1. Create `fixtures/{slug}.json` with subject + chapters data
2. Run: `python manage.py seed_data`

## Chapter content philosophy

- Every question is phrased as an interviewer would ask it
- Answers include real-world examples (Facebook, Netflix, Uber, etc.)
- Use `<mark>` tags for critical advice the reader must remember
- Mermaid diagrams must be mobile-friendly (max 6 nodes wide)
- Tables should have a "When to Use" or practical column
- Follow-ups simulate the interviewer drilling deeper
- Takeaways are rapid-recall items (3-7 per chapter)

## DeltaMails Management

### Topic Pool
- `python manage.py seed_topics` — populate EmailTopic from existing Chapters (one-time)
- `python manage.py refresh_topics` — AI discovers new interview topics via Gemma (weekly cron)
- `python manage.py refresh_topics --subject system-design --count 30` — targeted refresh
- `python manage.py refresh_topics --dry-run` — preview without saving

### Sending Emails
- `python manage.py send_deltamails` — send to all active subscribers (daily cron)
- `python manage.py send_deltamails --emails user@example.com` — test specific user
- `python manage.py send_deltamails --dry-run` — preview without sending

### Cron Jobs (django-crontab)
- `python manage.py crontab show` — list active jobs
- `python manage.py crontab add` — install cron jobs from settings
- `python manage.py crontab remove` — uninstall all jobs

## Question fields reference

| Field            | Type       | Required | Notes                          |
|------------------|------------|----------|-------------------------------|
| question         | string     | yes      | Phrased in interviewer voice   |
| difficulty       | string     | no       | "easy", "medium", or "hard"    |
| tldr             | string     | no       | One-line summary               |
| answer           | HTML       | no       | Detailed answer                |
| points           | string[]   | no       | Bullet points (HTML allowed)   |
| diagram          | string     | no       | Mermaid diagram source         |
| diagram_caption  | string     | no       | Caption below diagram          |
| diagram2         | string     | no       | Optional second diagram        |
| diagram2_caption | string     | no       | Caption for second diagram     |
| table_data       | object     | no       | `{headers: [], rows: [][]}`    |
| followup         | HTML       | no       | Follow-up interviewer question |
