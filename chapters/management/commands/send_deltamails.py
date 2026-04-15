import json
import random
import re
import subprocess
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.html import escape as html_escape

from chapters.models import Subscription, Chapter, Question, Highlight, Note


# Mirrors the exact JSON shape from QuestionReadSerializer + real fixture data.
EXAMPLE_JSON = r'''{
  "intro": "Caching is the single most common topic in system design interviews. Every interviewer expects you to know when to cache, where to cache, and what breaks when the cache fails.",
  "questions": [
    {
      "question": "Walk me through the cache-aside pattern. Why is it the default choice, and when does it break down?",
      "difficulty": "medium",
      "tldr": "App checks cache first, falls back to DB on miss, then populates cache — simple but risks stale reads.",
      "answer": "<p>In cache-aside (also called <strong>lazy loading</strong>), the application owns the caching logic. On a read, it checks the cache first. On a miss, it queries the database, writes the result to cache with a TTL, and returns. <mark>The key trade-off: simplicity vs. staleness.</mark> The cache can serve stale data until the TTL expires or the app explicitly invalidates.</p><p>This is the pattern behind virtually every Redis deployment at companies like <strong>Twitter, GitHub, and Shopify</strong>. It works because most workloads are read-heavy (90%+ reads) and can tolerate a few seconds of staleness.</p>",
      "points": [
        "<strong>Cache hit</strong> — return from Redis in ~0.1ms, DB never touched",
        "<strong>Cache miss</strong> — query DB (~5ms), write to cache with TTL, return to client",
        "<strong>Staleness window</strong> — between a DB write and cache TTL expiry, reads return old data. <mark>Acceptable for feeds, profiles; dangerous for payments, inventory.</mark>",
        "<strong>Thundering herd</strong> — if a popular key expires, hundreds of requests simultaneously hit the DB. Mitigate with request coalescing or early refresh.",
        "<strong>Cold start</strong> — after a cache flush, every request is a miss. Pre-warm the cache with the top-N hot keys."
      ],
      "diagram": "sequenceDiagram\n  participant App\n  participant Redis as Cache (Redis)\n  participant DB as Database\n  App->>Redis: GET user:42\n  alt HIT\n    Redis-->>App: Return data (0.1ms)\n  else MISS\n    Redis-->>App: null\n    App->>DB: SELECT * FROM users WHERE id=42\n    DB-->>App: Row data (5ms)\n    App->>Redis: SET user:42 (TTL 5min)\n  end",
      "diagramCaption": "Cache-aside pattern — the most common caching strategy in production",
      "diagram2": "",
      "diagram2Caption": "",
      "table": {
        "headers": ["Strategy", "How It Works", "When to Use"],
        "rows": [
          ["Cache-Aside", "App manages cache reads/writes", "Read-heavy, tolerates short staleness"],
          ["Write-Through", "Write to cache + DB on every write", "Strong consistency needed, write volume manageable"],
          ["Write-Behind", "Write to cache, async flush to DB", "High write throughput, can tolerate async lag"],
          ["Read-Through", "Cache itself fetches from DB on miss", "Simpler app code, cache library supports it"]
        ]
      },
      "followup": "<p><strong>\"What if your Redis instance goes down — what happens to your application?\"</strong></p>\n<p>If Redis is down, every request becomes a cache miss and hits the database directly. For most apps this means a sudden 10-50x increase in DB load. <mark>Design for graceful degradation:</mark> use circuit breakers, fall back to DB with rate limiting, and ensure your DB can handle the burst for the 30-60 seconds it takes Redis to recover.</p>"
    }
  ],
  "tip": "<strong>In interviews, always mention the TTL.</strong> When you propose caching, immediately say the TTL value and why you chose it. This shows you understand staleness trade-offs, not just \"put a cache in front of it.\"",
  "takeaways": [
    "<strong>Cache-aside</strong> is the default — app checks cache, falls back to DB, populates on miss. <mark>Know the sequence cold.</mark>",
    "<strong>TTL is your consistency knob</strong> — short TTL = fresher data + more DB load; long TTL = stale data + less DB load.",
    "<strong>Thundering herd</strong> — use request coalescing or mutex locks to prevent cache stampedes on popular keys.",
    "<strong>Write-through vs write-behind</strong> — through is consistent but slower; behind is fast but risks data loss on crash."
  ],
  "closing": "Caching questions separate the junior from senior candidates. Master the patterns, know the trade-offs, and always mention what breaks."
}'''


class Command(BaseCommand):
    help = 'Send daily DeltaMail emails to active subscribers'

    def add_arguments(self, parser):
        parser.add_argument(
            '--emails', nargs='+', type=str,
            help='Limit to specific email addresses (for testing)',
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Print emails to stdout instead of sending',
        )

    def handle(self, *args, **options):
        filter_emails = options.get('emails')
        dry_run = options.get('dry_run', False)

        qs = Subscription.objects.filter(is_active=True).select_related(
            'subject', 'last_chapter_sent', 'user',
        )
        if filter_emails:
            qs = qs.filter(email__in=filter_emails)

        if not qs.exists():
            self.stdout.write('No active subscriptions found.')
            return

        grouped = {}
        for sub in qs:
            grouped.setdefault(sub.email, []).append(sub)

        sent_count = 0
        for email, subs in grouped.items():
            for sub in subs:
                chapter = self._pick_chapter(sub)
                if not chapter:
                    self.stdout.write(f'  No chapters for {sub.subject.slug}, skipping.')
                    continue

                body_html = self._generate_email(sub, chapter)
                subject_line = (
                    f'DeltaMail: {chapter.title} — {sub.subject.name}'
                )

                if dry_run:
                    self.stdout.write(f'\n--- DRY RUN: {email} ({sub.subject.slug}) ---')
                    self.stdout.write(f'Subject: {subject_line}')
                    self.stdout.write(body_html[:500] + '...')
                else:
                    try:
                        send_mail(
                            subject=subject_line,
                            message='',
                            html_message=body_html,
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[email],
                            fail_silently=False,
                        )
                        sub.last_sent_at = timezone.now()
                        sub.last_chapter_sent = chapter
                        sub.save(update_fields=['last_sent_at', 'last_chapter_sent'])
                        sent_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(f'  Sent to {email}: {chapter.title}')
                        )
                    except Exception as exc:
                        self.stderr.write(
                            self.style.ERROR(f'  Failed {email}: {exc}')
                        )

        self.stdout.write(self.style.SUCCESS(f'\nDone. {sent_count} email(s) sent.'))

    # ── chapter selection (focus-scored) ───────────────

    def _pick_chapter(self, sub):
        chapters = list(
            Chapter.objects.filter(subject=sub.subject).order_by('chapter_number')
        )
        if not chapters:
            return None

        sent_ids = set()
        if sub.last_chapter_sent:
            sent_ids.add(sub.last_chapter_sent.pk)

        unsent = [c for c in chapters if c.pk not in sent_ids]
        pool = unsent if unsent else chapters

        if sub.custom_prompt and sub.custom_prompt.strip():
            stop_words = {
                'the', 'and', 'for', 'with', 'that', 'this', 'from', 'are',
                'was', 'were', 'been', 'have', 'has', 'had', 'will', 'would',
                'could', 'should', 'may', 'might', 'can', 'how', 'what',
                'when', 'where', 'why', 'who', 'which', 'about', 'into',
                'like', 'more', 'also', 'use', 'using', 'used', 'focus',
                'explain', 'cover', 'include', 'want', 'need', 'make',
            }
            focus = sub.custom_prompt.lower()
            focus_words = [
                w for w in re.split(r'[\s,;/\-]+', focus)
                if len(w) >= 3 and w not in stop_words
            ]
            scored = []
            for ch in pool:
                haystack_title = ch.title.lower()
                haystack_sub = (ch.subtitle or '').lower()
                haystack_part = (ch.part or '').lower()
                score = 0
                for word in focus_words:
                    if word in haystack_title:
                        score += 5
                    elif len(word) >= 4 and word[:4] in haystack_title:
                        score += 3
                    if word in haystack_sub:
                        score += 3
                    elif len(word) >= 4 and word[:4] in haystack_sub:
                        score += 1
                    if word in haystack_part:
                        score += 1
                scored.append((score, ch))

            scored.sort(key=lambda x: x[0], reverse=True)
            if scored[0][0] > 0:
                best_score = scored[0][0]
                top = [ch for s, ch in scored if s == best_score]
                return random.choice(top)

        if unsent:
            return unsent[0]
        return random.choice(chapters)

    # ── email generation ──────────────────────────────

    def _generate_email(self, sub, chapter):
        accent = sub.subject.accent_color or '#0a84ff'

        questions = list(
            Question.objects.filter(chapter=chapter).order_by('order')
        )

        user_context = ''
        if sub.user:
            highlights = list(
                Highlight.objects.filter(
                    user=sub.user, chapter=chapter,
                ).values_list('text', flat=True)[:10]
            )
            notes = list(
                Note.objects.filter(
                    user=sub.user, subject=sub.subject,
                ).values_list('content', flat=True)[:5]
            )
            if highlights:
                user_context += f'\nUser highlights: {"; ".join(highlights[:5])}'
            if notes:
                user_context += f'\nUser notes: {"; ".join(notes[:3])}'

        prompt = self._build_prompt(sub, chapter, questions, accent, user_context)
        raw = self._call_gemma(prompt)
        data = self._parse_ai_response(raw)

        return self._render_html(sub, chapter, accent, data)

    # ── AI prompt (philosophy + frontend schema) ──────

    def _build_prompt(self, sub, chapter, questions, accent, user_context):
        difficulty_guide = {
            'easy': 'Use simple language, analogies, beginner-friendly explanations. Avoid jargon.',
            'medium': 'Assume working knowledge of software engineering fundamentals.',
            'hard': 'Go deep: trade-offs, edge cases, failure modes, production-grade patterns.',
            'mixed': 'Start simple, then escalate to advanced trade-offs.',
        }

        q_text = '\n'.join(
            f'Q{i+1}: {q.question}\n   TLDR: {q.tldr}'
            f'\n   Answer excerpt: {q.answer[:150]}...' if q.answer else ''
            f'\n   Diagram: {"Yes (Mermaid)" if q.diagram else "None"}'
            f'\n   Table: {"Yes" if q.table_data else "None"}'
            for i, q in enumerate(questions[:6])
        )

        custom_block = ''
        if sub.custom_prompt and sub.custom_prompt.strip():
            custom_block = f'''
━━━ USER FOCUS AREA (CRITICAL — READ CAREFULLY) ━━━
The user specifically asked to focus on: "{sub.custom_prompt}"
This MUST shape your output:
  - Angle every question toward this focus area.
  - If the focus is a sub-topic (e.g. "caching", "load balancing"), frame all
    questions around how that sub-topic relates to the chapter topic.
  - If the focus is a style preference (e.g. "explain like I am 5", "use
    analogies"), adapt your language and explanations accordingly.
  - The intro, tip, and closing should all reference this focus.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'''

        return f'''You are DeltaMails — a daily interview-prep email for "{sub.subject.name}".

Topic: "{chapter.title}" (Chapter {chapter.chapter_number})
Difficulty: {sub.difficulty} — {difficulty_guide.get(sub.difficulty, "")}
{custom_block}
{f"Personalization context (user highlights & notes): {user_context}" if user_context else ""}

Reference questions from this chapter (use as inspiration, generate NEW questions):
{q_text}

━━━ DELTA LEARN CONTENT PHILOSOPHY ━━━
You write like a senior engineer who has run 1000+ interviews. Follow these rules EXACTLY:

VOICE:
- Phrase questions as an interviewer: "Walk me through...", "How would you handle...",
  "What happens when...", "Compare X vs Y for...", "Design a system that..."
- NEVER write textbook definitions like "What is X?". Always test application.
- Each question tests understanding and trade-off awareness, not memorization.

ANSWERS:
- Answer as a strong candidate: structured, concise, trade-off aware.
- Lead with the core insight in 1-2 sentences, then elaborate with 2-3 more paragraphs.
- Reference REAL companies and systems by name (Facebook TAO, Netflix Zuul, Twitter
  Snowflake, Uber Ringpop, DynamoDB, Kafka, Redis, Cassandra, etc.).
- Use <strong> for key terms. Use <mark> for critical must-remember advice.
- Always discuss trade-offs: latency vs throughput, consistency vs availability.

POINTS (3-6 per question):
- Format: "<strong>Key Term</strong> — one crisp engineering explanation"
- Use <mark> for critical advice within points when appropriate.

DIAGRAMS (Mermaid syntax — at least 2 questions should have diagrams):
- Use Mermaid flowchart or sequence diagram syntax.
- Flowcharts: "graph LR" (horizontal) or "graph TD" (vertical).
- Max 6 nodes wide. Use <br/> inside node labels for multi-line text.
- Show real architecture: Load Balancer, Cache, DB, Queue, Worker, CDN, etc.
- Example: "graph LR\\n  A[Client] --> B[Load Balancer]\\n  B --> C[App Server]\\n  C --> D[(Database)]"
- Example: "sequenceDiagram\\n  participant App\\n  participant Cache\\n  App->>Cache: GET key\\n  Cache-->>App: HIT or MISS"

TABLES (at least 1 question should have a table):
- Use for comparisons that come up in interviews.
- MUST include a practical "When to Use" column.
- Format: {{"headers": ["X", "Y", "When to Use"], "rows": [["...", "...", "..."]]}}

FOLLOW-UPS:
- Every question MUST have a follow-up as HTML.
- Format: "<p><strong>\\"Follow-up question here\\"</strong></p>\\n<p>Answer...</p>"
- Go one level deeper: failure modes, 10x scale, monitoring, edge cases.

TAKEAWAYS (3-5 items):
- One-sentence rapid-recall items.
- Format: "<strong>Key phrase</strong> — explanation. <mark>Must-know part.</mark>"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RESPOND WITH ONLY A VALID JSON OBJECT. No markdown fences, no explanation outside JSON.

Schema (matches our frontend QuestionReadSerializer exactly):
{{
  "intro": "2-3 sentence hook setting the interview context",
  "questions": [
    {{
      "question": "Interview question — phrased exactly as interviewer would ask",
      "difficulty": "easy|medium|hard",
      "tldr": "One scannable sentence a strong candidate says first",
      "answer": "<p>HTML answer. 2-4 paragraphs. <strong>key terms</strong>. <mark>must-know</mark>. Real companies.</p>",
      "points": [
        "<strong>Term</strong> — explanation. <mark>Critical advice if applicable.</mark>"
      ],
      "diagram": "graph LR\\n  A[Node] --> B[Node]  (Mermaid syntax string, or empty string)",
      "diagramCaption": "Short caption (or empty string)",
      "diagram2": "optional second Mermaid diagram (or empty string)",
      "diagram2Caption": "optional caption (or empty string)",
      "table": {{"headers": ["Col1","Col2","When to Use"], "rows": [["...","...","..."]]}} or null,
      "followup": "<p><strong>\\"Follow-up question\\"</strong></p>\\n<p>Answer with trade-offs.</p>"
    }}
  ],
  "tip": "<strong>Interview signal</strong> — what to say, what to avoid. Use <mark> for key advice.",
  "takeaways": [
    "<strong>Key phrase</strong> — recall item. <mark>Must-know.</mark>"
  ],
  "closing": "One motivational closing sentence"
}}

Rules:
- Generate 3-4 questions.
- At least 2 questions with Mermaid diagrams (graph LR/TD or sequenceDiagram).
- At least 1 question with a comparison table including "When to Use" column.
- Every question MUST have: question, difficulty, tldr, answer, points (3-6), followup.
- Use \\n for newlines inside Mermaid diagram strings.
- Keep total content under 1000 words.

Example of valid output (use as formatting reference only — generate NEW content):
{EXAMPLE_JSON}

Now generate the JSON for "{chapter.title}".'''

    # ── AI call ───────────────────────────────────────

    def _call_gemma(self, prompt):
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            return '{}'

        try:
            from google import genai

            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model='gemma-3-27b-it',
                contents=prompt,
            )
            return response.text or '{}'
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f'  AI call failed: {exc}'))
            return '{}'

    # ── parse AI response ─────────────────────────────

    def _parse_ai_response(self, raw):
        cleaned = raw.strip()
        if cleaned.startswith('```'):
            cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
            cleaned = re.sub(r'\s*```$', '', cleaned)

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r'\{[\s\S]*\}', cleaned)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            return {
                'intro': cleaned[:300] if cleaned else 'Content generation failed.',
                'questions': [],
                'tip': '',
                'takeaways': [],
                'closing': '',
            }

    # ── Mermaid → SVG (with code-block fallback) ──────

    def _mermaid_to_svg(self, mermaid_src):
        """Try mmdc CLI; fall back to a styled code block."""
        if not mermaid_src or not mermaid_src.strip():
            return ''

        try:
            with tempfile.NamedTemporaryFile(
                mode='w', suffix='.mmd', delete=False
            ) as src_file:
                src_file.write(mermaid_src)
                src_path = src_file.name

            out_path = src_path.replace('.mmd', '.svg')

            result = subprocess.run(
                [
                    'mmdc', '-i', src_path, '-o', out_path,
                    '-t', 'dark',
                    '-b', 'transparent',
                    '--configFile', '/dev/null',
                ],
                capture_output=True, text=True, timeout=20,
            )

            svg_file = Path(out_path)
            if result.returncode == 0 and svg_file.exists():
                svg_content = svg_file.read_text()
                svg_file.unlink(missing_ok=True)
                Path(src_path).unlink(missing_ok=True)
                import re as _re
                svg_content = _re.sub(
                    r'style="[^"]*max-width:\s*[\d.]+px[^"]*"',
                    'style="max-width:100%;height:auto"',
                    svg_content, count=1,
                )
                return svg_content

        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            pass

        return self._mermaid_code_block(mermaid_src)

    def _mermaid_code_block(self, mermaid_src):
        """Render Mermaid source as a styled monospace code block for email."""
        escaped = html_escape(mermaid_src)
        lines = escaped.split('\n')
        formatted = '<br>'.join(
            f'&nbsp;&nbsp;{line}' if line.startswith('  ') else line
            for line in lines
        )
        return (
            '<div style="font-family:\'SF Mono\',SFMono-Regular,ui-monospace,'
            'Menlo,Monaco,Consolas,monospace;font-size:11px;line-height:1.7;'
            'color:#a1a1a6;white-space:pre-wrap;word-break:break-word;'
            'padding:4px 0">'
            f'{formatted}</div>'
        )

    # ── HTML rendering (mirrors frontend App.css) ─────

    def _render_html(self, sub, chapter, accent, data):
        # Derived colors matching frontend tokens
        accent_subtle = self._hex_to_rgba(accent, 0.10)
        accent_glow = self._hex_to_rgba(accent, 0.08)

        diff_colors = {
            'easy': ('#30d158', 'rgba(48,209,88,0.12)'),
            'medium': ('#ff9f0a', 'rgba(255,159,10,0.12)'),
            'hard': ('#ff453a', 'rgba(255,69,58,0.12)'),
        }

        questions_html = ''
        q_list = data.get('questions', [])
        total = len(q_list)

        for i, q in enumerate(q_list):
            d = q.get('difficulty', 'medium')
            d_color, d_bg = diff_colors.get(d, diff_colors['medium'])
            num = f'{i+1:02d}/{total:02d}'

            # ── Points (matches .qa-points / .qa-point / .qa-point-marker)
            points_html = ''
            for pt in (q.get('points') or []):
                points_html += f'''
                <tr>
                  <td style="width:18px;vertical-align:top;padding:5px 0">
                    <div style="width:6px;height:6px;border-radius:50%;background:{accent};margin-top:8px;flex-shrink:0"></div>
                  </td>
                  <td style="padding:5px 0 5px 12px;font-size:14px;line-height:1.6;color:#f5f5f7">{pt}</td>
                </tr>'''

            # ── Diagram 1 (matches .mermaid-wrap / .mermaid-caption)
            diagram1_html = self._render_diagram(
                q.get('diagram', ''), q.get('diagramCaption', ''),
            )

            # ── Diagram 2
            diagram2_html = self._render_diagram(
                q.get('diagram2', ''), q.get('diagram2Caption', ''),
            )

            # ── Table (matches .qa-table-wrap / .qa-table)
            table_html = ''
            tbl = q.get('table')
            if tbl and tbl.get('headers') and tbl.get('rows'):
                headers = ''.join(
                    f'<th style="text-align:left;padding:10px 14px;font-weight:600;'
                    f'font-size:11px;letter-spacing:0.04em;text-transform:uppercase;'
                    f'color:#86868b;background:#141414;'
                    f'border-bottom:1px solid rgba(255,255,255,0.12)">{h}</th>'
                    for h in tbl['headers']
                )
                rows = ''
                for ri, row in enumerate(tbl['rows']):
                    is_last = ri == len(tbl['rows']) - 1
                    border = 'border-bottom:none' if is_last else 'border-bottom:1px solid rgba(255,255,255,0.06)'
                    cells = ''.join(
                        f'<td style="padding:9px 14px;{border};color:#f5f5f7;font-size:13px;line-height:1.5">{c}</td>'
                        for c in row
                    )
                    rows += f'<tr>{cells}</tr>'
                table_html = f'''
              <div style="margin:20px 0;border:1px solid rgba(255,255,255,0.06);border-radius:8px;overflow:hidden">
                <table style="width:100%;border-collapse:collapse" cellpadding="0" cellspacing="0">
                  <thead><tr>{headers}</tr></thead>
                  <tbody>{rows}</tbody>
                </table>
              </div>'''

            # ── Follow-up (matches .qa-followup with purple theme)
            followup_html = ''
            if q.get('followup'):
                followup_html = f'''
              <div style="margin-top:24px;padding:16px 18px;border-radius:8px;background:rgba(191,90,242,0.06);border:1px solid rgba(191,90,242,0.12);font-size:14px;line-height:1.65;color:#f5f5f7">
                <div style="font-size:10px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:#bf5af2;margin-bottom:8px">Follow-up the interviewer will ask</div>
                <div>{q['followup']}</div>
              </div>'''

            # ── Full QA section (matches .qa)
            is_last_q = i == total - 1
            q_border = 'border-bottom:none' if is_last_q else 'border-bottom:1px solid rgba(255,255,255,0.06)'
            questions_html += f'''
          <div style="padding:40px 0;{q_border}">
            <!-- qa-header -->
            <table cellpadding="0" cellspacing="0" style="border-spacing:0;margin-bottom:12px"><tr>
              <td style="font-family:'SF Mono',SFMono-Regular,ui-monospace,Menlo,Monaco,Consolas,monospace;font-size:10px;font-weight:600;color:#58585d;letter-spacing:0.02em;padding-right:10px">{num}</td>
              <td><span style="font-size:10px;font-weight:700;letter-spacing:0.06em;text-transform:uppercase;padding:2px 8px;border-radius:4px;background:{d_bg};color:{d_color}">{d}</span></td>
            </tr></table>
            <!-- qa-question -->
            <h3 style="font-size:20px;font-weight:600;letter-spacing:-0.02em;line-height:1.3;color:#f5f5f7;margin:0 0 20px">{q.get('question', '')}</h3>
            <!-- qa-tldr -->
            <div style="font-size:14px;font-weight:500;color:{accent};line-height:1.5;margin-bottom:20px;padding:12px 16px;background:{accent_subtle};border-radius:8px;border-left:3px solid {accent}">{q.get('tldr', '')}</div>
            <!-- qa-answer -->
            <div style="font-size:14px;line-height:1.75;color:#f5f5f7;margin-bottom:16px">{q.get('answer', '')}</div>
            <!-- diagram 1 -->
            {diagram1_html}
            <!-- qa-points -->
            {f'<table style="border-spacing:0;margin:20px 0" cellpadding="0" cellspacing="0">{points_html}</table>' if points_html else ''}
            <!-- qa-table -->
            {table_html}
            <!-- diagram 2 -->
            {diagram2_html}
            <!-- qa-followup -->
            {followup_html}
          </div>'''

        # ── Takeaways (matches .takeaways / .takeaway-item)
        takeaways_html = ''
        if data.get('takeaways'):
            items = ''
            for t in data['takeaways']:
                items += f'''
              <div style="font-size:14px;line-height:1.55;color:#f5f5f7;padding:8px 12px;border-radius:8px;background:rgba(48,209,88,0.04);border-left:2px solid rgba(48,209,88,0.25);margin-bottom:8px">{t}</div>'''
            takeaways_html = f'''
          <div style="margin-top:48px;padding:28px;border-radius:12px;background:rgba(48,209,88,0.04);border:1px solid rgba(48,209,88,0.10)">
            <div style="font-size:10px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#30d158;margin-bottom:18px">Rapid Recall</div>
            {items}
          </div>'''

        # ── Tip (interview signal)
        tip_html = ''
        if data.get('tip'):
            tip_html = f'''
          <div style="margin-top:24px;padding:16px 20px;border-radius:12px;background:{accent_glow};border:1px solid {accent_subtle}">
            <div style="font-size:10px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:{accent};margin-bottom:6px">
              &#9889; Interview Signal
            </div>
            <div style="font-size:14px;line-height:1.6;color:#f5f5f7">{data['tip']}</div>
          </div>'''

        closing = data.get('closing', '')

        # ── Full HTML document — full-bleed Apple-inspired layout
        return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="color-scheme" content="dark">
  <title>DeltaMail — {chapter.title}</title>
</head>
<body style="margin:0;padding:0;background:#1c1c1e;font-family:-apple-system,BlinkMacSystemFont,'SF Pro Display','SF Pro Text','Helvetica Neue',Helvetica,Arial,sans-serif;-webkit-font-smoothing:antialiased;-moz-osx-font-smoothing:grayscale;color:#f5f5f7;line-height:1.55">

    <!-- accent bar — thin, full-width, Apple-style -->
    <div style="background:{accent};height:4px;width:100%"></div>

    <!-- header -->
    <div style="padding:32px 40px 28px;border-bottom:1px solid rgba(255,255,255,0.06)">
      <table style="width:100%;border-spacing:0" cellpadding="0" cellspacing="0">
        <tr>
          <td>
            <h1 style="margin:0;font-size:20px;font-weight:700;color:#f5f5f7;letter-spacing:-0.02em">DeltaMails</h1>
            <p style="margin:4px 0 0;font-size:12px;color:#86868b;line-height:1.4;letter-spacing:0.01em">
              {sub.subject.name} &middot; Chapter {chapter.chapter_number} &middot; {sub.difficulty.title()}
            </p>
          </td>
          <td style="text-align:right;vertical-align:middle">
            <div style="display:inline-block;background:{accent_subtle};border:1px solid {accent};border-radius:6px;padding:4px 12px">
              <span style="font-size:10px;font-weight:700;color:{accent};letter-spacing:0.06em;text-transform:uppercase">{sub.difficulty}</span>
            </div>
          </td>
        </tr>
      </table>
    </div>

    <!-- chapter header -->
    <div style="padding:40px 40px 0">
      <div style="margin-bottom:48px;padding-bottom:32px;border-bottom:1px solid rgba(255,255,255,0.06)">
        {f'<div style="display:inline-block;padding:3px 10px;border-radius:980px;font-size:10px;font-weight:600;letter-spacing:0.05em;text-transform:uppercase;background:{accent_subtle};color:{accent};margin-bottom:14px">{chapter.part}</div><br>' if chapter.part else ''}
        <h2 style="margin:0 0 10px;font-size:28px;font-weight:700;color:#f5f5f7;letter-spacing:-0.03em;line-height:1.15">{chapter.title}</h2>
        {f'<p style="margin:0 0 12px;font-size:15px;color:#86868b;line-height:1.55">{chapter.subtitle}</p>' if chapter.subtitle else ''}
        {f'<div style="font-family:\'SF Mono\',SFMono-Regular,ui-monospace,Menlo,monospace;font-size:11px;color:#58585d;letter-spacing:0.02em">{total} questions covering the full topic</div>' if total else ''}
      </div>
    </div>

    <!-- content area -->
    <div style="padding:0 40px">

      <!-- intro -->
      <div style="font-size:15px;line-height:1.7;color:#e5e5e7;margin-bottom:16px">
        {data.get('intro', '')}
      </div>

      <!-- questions -->
      {questions_html}

      <!-- tip -->
      {tip_html}

      <!-- takeaways -->
      {takeaways_html}

      <!-- closing -->
      {f'<p style="margin-top:32px;font-size:14px;color:#86868b;text-align:center;font-style:italic;line-height:1.5">{closing}</p>' if closing else ''}

    </div>

    <!-- footer — separated by full-width border -->
    <div style="margin-top:48px;border-top:1px solid rgba(255,255,255,0.06);padding:24px 40px 32px;text-align:center">
      <p style="font-size:11px;color:#58585d;line-height:1.7;margin:0">
        You received this because you subscribed to DeltaMails for {sub.subject.name}.<br>
        <a href="https://deltalearn.app/" style="color:{accent};text-decoration:none">Visit Delta Learn</a> &middot;
        <a href="https://deltalearn.app/" style="color:{accent};text-decoration:none">Unsubscribe</a>
      </p>
      <p style="font-size:10px;color:#3a3a3c;margin:10px 0 0">
        &copy; Delta Learn
      </p>
    </div>

</body>
</html>'''

    # ── diagram rendering helper ──────────────────────

    def _render_diagram(self, mermaid_src, caption):
        """Render a Mermaid diagram for email (matches .mermaid-wrap)."""
        if not mermaid_src or not mermaid_src.strip():
            return ''

        svg_or_code = self._mermaid_to_svg(mermaid_src)

        caption_html = ''
        if caption:
            caption_html = (
                f'<p style="font-size:11px;color:#86868b;font-style:italic;'
                f'margin:10px 0 0;text-align:center;letter-spacing:0.01em">'
                f'{caption}</p>'
            )

        return f'''
              <div style="margin:24px 0;padding:20px 0;text-align:center">
                <div style="padding:20px 16px;background:#141414;border-radius:10px;border:1px solid rgba(255,255,255,0.04);overflow:auto">{svg_or_code}</div>
                {caption_html}
              </div>'''

    # ── utility ───────────────────────────────────────

    @staticmethod
    def _hex_to_rgba(hex_color, alpha):
        """Convert #RRGGBB to rgba(r,g,b,alpha)."""
        h = hex_color.lstrip('#')
        if len(h) == 3:
            h = ''.join(c * 2 for c in h)
        try:
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            return f'rgba({r},{g},{b},{alpha})'
        except (ValueError, IndexError):
            return f'rgba(10,132,255,{alpha})'
