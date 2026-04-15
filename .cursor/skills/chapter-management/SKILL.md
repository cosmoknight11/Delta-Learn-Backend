---
name: chapter-management
description: >-
  Add, update, or manage subjects and chapters in the Delta Learn backend.
  Use when adding new chapter content, creating new subjects, or updating
  existing chapter data via Django Admin, API, or fixtures.
---

# Chapter & Subject Management

## Option A: Django Admin (preferred for manual edits)

1. Go to `http://localhost:8000/admin/`
2. Log in with the superuser account
3. Navigate to **Chapters > Subjects** to add/edit subjects
4. Navigate to **Chapters > Chapters** to add/edit chapters
5. Use inline editing to add Questions and Takeaways directly on the Chapter page

## Option B: JSON Fixtures + Seed Command (bulk operations)

### Adding a new subject

1. Create `fixtures/{slug}.json` with this structure:

```json
{
  "subject": {
    "slug": "new-subject",
    "name": "New Subject",
    "description": "Description for the homepage card.",
    "accentColor": "#hexcolor",
    "order": 3
  },
  "chapters": [
    {
      "id": 1,
      "part": "Part I: Introduction",
      "title": "Chapter Title",
      "subtitle": "One-line description.",
      "questions": [],
      "takeaways": []
    }
  ]
}
```

2. Add the filename to `FIXTURE_FILES` in `chapters/management/commands/seed_data.py`
3. Run: `python manage.py seed_data`

### Adding a chapter with full content

Each chapter is an object with this shape:

```json
{
  "id": 10,
  "part": "Part III: Data",
  "title": "SQL vs NoSQL — Choosing the Right Database",
  "subtitle": "When to use each...",
  "questions": [
    {
      "question": "How do you decide between SQL and NoSQL?",
      "difficulty": "medium",
      "tldr": "Short answer summary.",
      "answer": "<p>HTML answer content</p>",
      "points": [
        "<strong>Point 1</strong> — explanation",
        "<strong>Point 2</strong> — explanation"
      ],
      "diagram": "graph LR\n  A --> B",
      "diagramCaption": "Caption for the Mermaid diagram",
      "diagram2": "",
      "diagram2Caption": "",
      "table": {
        "headers": ["Col 1", "Col 2"],
        "rows": [["cell", "cell"]]
      },
      "followup": "<p>Follow-up HTML</p>"
    }
  ],
  "takeaways": [
    "<strong>Key point</strong> — quick recall item"
  ]
}
```

### Question fields reference

| Field          | Type       | Required | Notes                          |
|---------------|------------|----------|-------------------------------|
| question      | string     | yes      | The interview question         |
| difficulty    | string     | no       | "easy", "medium", or "hard"    |
| tldr          | string     | no       | One-line summary               |
| answer        | HTML       | no       | Detailed answer                |
| points        | string[]   | no       | Bullet points (HTML allowed)   |
| diagram       | string     | no       | Mermaid diagram source         |
| diagramCaption| string     | no       | Caption below diagram          |
| diagram2      | string     | no       | Optional second diagram        |
| diagram2Caption| string    | no       | Caption for second diagram     |
| table         | object     | no       | `{headers: [], rows: [][]}`    |
| followup      | HTML       | no       | Follow-up interviewer question |

## Option C: REST API (programmatic)

Subjects and chapters are read-only via the public API. To create/update
content programmatically, use Django Admin or the seed command. The API
is designed for the frontend to consume, not for content authoring.

## Chapter content philosophy

- Every question is phrased as an interviewer would ask it
- Answers include real-world examples (Facebook, Netflix, Uber, etc.)
- Use `<mark>` tags for critical advice the reader must remember
- Mermaid diagrams must be mobile-friendly (max 6 nodes wide)
- Tables should have a "When to Use" or practical column
- Follow-ups simulate the interviewer drilling deeper
