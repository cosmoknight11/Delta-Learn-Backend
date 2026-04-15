---
name: chapter-management
description: >-
  Manage subjects, chapters, questions, and takeaways in the Delta Learn backend.
  Covers Django Admin, MCP tools, REST API, and DeltaMails commands.
---

# Chapter & Subject Management

## Full Chapter via MCP (preferred)

```
stage_chapter(chapter_id, questions=[...], takeaways=[...])
```
Creates one staged request. Admin sees rich preview → approves → all content applied atomically.

## Individual Items via MCP

- `create_question(chapter_id, ...)` / `create_takeaway(chapter_id, ...)` → staged
- `update_chapter` / `update_question` → staged
- `delete_question` / `delete_takeaway` → staged
- `list_staged_requests` / `get_staged_request` → check status

## Django Admin

1. Log in at `/admin/`
2. Chapters: inline Questions + Takeaways, Preview button
3. Staged Requests: rich HTML preview, default pending filter, bulk approve/reject

## REST API

- Direct CRUD: `/api/manage/{model}/` (IsAdminUser)
- Bulk stage: `POST /api/manage/chapters/{id}/stage-populate/` (staged)
- Staged: `POST /api/staged/` → `POST /api/staged/{id}/approve/`

## Setup Commands

| Command | Purpose |
|---------|---------|
| `python manage.py migrate` | Apply migrations |
| `python manage.py seed_data` | Load fixtures (subjects, chapters, questions, takeaways) |
| `python manage.py createsuperuser` | Create admin account |

## DeltaMails Commands

| Command | Purpose | Run |
|---------|---------|-----|
| `seed_topics` | Seed EmailTopic from chapters | One-time |
| `refresh_topics` | AI discovers new topics | `--subject`, `--count`, `--dry-run` |
| `send_deltamails` | Send to active subscribers | `--emails user@...`, `--dry-run` |
| `crontab show/add/remove` | Manage cron jobs | django-crontab |

## Question Fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| question | str | yes | Interview voice |
| difficulty | str | no | easy / medium / hard |
| tldr | str | no | One-line summary |
| answer | HTML | no | Full answer |
| points | str[] | no | Bullets with `<strong>`, `<mark>` |
| diagram | str | no | Mermaid code (max 6 nodes wide) |
| diagram_caption | str | no | Caption |
| diagram2 / diagram2_caption | str | no | Second diagram |
| table_data | obj | no | `{headers: [], rows: [[]]}` |
| followup | HTML | no | Interviewer follow-up |
