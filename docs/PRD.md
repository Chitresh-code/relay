# PRD — Relay

Status: Draft v1 · Owner: Chitresh Gyanani · Last updated: 2026-08-02

## 1. Problem & Goal

Recruiters skim resumes for 6-10 seconds. A conversational agent on a personal subdomain lets them ask
direct questions ("does he have Kubernetes experience?", "is he open to contract work?") and get
answers grounded in Chitresh's actual profile, instead of re-reading a PDF. When the agent can't
answer confidently, or the recruiter clearly wants to talk to a human, it should hand off to Chitresh
directly rather than making something up or dead-ending.

**Primary goal:** let a recruiter self-serve 80% of screening questions, and cleanly escalate the
other 20% with enough context that Chitresh can respond without back-and-forth.

## 2. Users

- **Recruiter / hiring manager** (primary): lands on the subdomain, asks questions, may leave contact
  info if the agent can't fully answer.
- **Chitresh (admin)**: interacts entirely through Telegram — receives escalations, replies to them,
  gets usage stats and weekly digests. No separate admin web dashboard in v1 (Telegram *is* the
  admin interface — see [[ARCHITECTURE.md]]).

## 3. Core Features

### 3.1 Public chat agent
- Built on the OpenAI Agents SDK.
- Knowledge base: resume content, a curated bio/FAQ doc, and public GitHub activity. LinkedIn is
  **not** live-integrated (see §6, Constraints) — relevant LinkedIn content is folded into the curated
  bio doc manually.
- Answers only from that knowledge base. Never invents experience, dates, or claims not present in
  the source material.
- Rate-limited per session/IP to control cost and abuse (see [[ARCHITECTURE.md]]).

### 3.2 Structured, component-based responses
Every agent reply is a structured object, not just prose, so the frontend can render rich UI instead
of a wall of text:

```json
{
  "message": "Here's his recent backend work:",
  "component": "cards",
  "content": [
    { "title": "Payments platform", "subtitle": "Company X, 2023-2025",
      "description": "...", "tags": ["Python", "Kafka"], "link": null }
  ]
}
```

Component set (deliberately small — extend later only if a real reply doesn't fit):
| component | use |
|---|---|
| `text` | plain conversational reply |
| `list` | skills, tools, short bullet facts |
| `cards` | experience, projects, achievements |
| `link` | single CTA (GitHub repo, portfolio, PDF resume) |
| `contact_form` | prompts the user to leave an email — used by the escalation flow |

### 3.3 Human escalation (fallback to Telegram)
The agent has an `escalate` tool it calls when: the question is outside the knowledge base, the
recruiter explicitly asks to talk to Chitresh, or there's clear hiring intent worth a personal
response. On escalation:
1. Agent tells the user it's looping Chitresh in, and renders `contact_form` to collect an email
   (optional but encouraged — without it, Chitresh can't respond back).
2. A message is sent to Chitresh's Telegram with the question, conversation context, and contact info
   if given.
3. Chitresh can reply from Telegram; if the user left an email, the reply is sent to them (via Resend).

### 3.4 Telegram as admin interface
Chitresh's Telegram bot (a *second*, private bot — the user-facing web widget is not on Telegram) is
the control plane:
- Real-time escalation alerts with full thread context.
- `/stats` — today's traffic, sessions, token/cost usage.
- `/weekly` — on-demand weekly digest; also pushed automatically every Monday.
- Weekly digest includes: traffic summary, top question topics, LLM cost, and a summarized recap of
  the week's conversations (see §4, conversation storage).

### 3.5 Observability & governance
- **Conversations are stored** (resolved: see decision below) in Postgres with a disclosed retention
  window, so Telegram-based summaries and digests are possible.
- Aggregate usage stats (requests, tokens, estimated cost, unique sessions/day) tracked regardless,
  independent of raw transcript retention.
- A visible privacy notice on the widget explaining what's stored and for how long.
- No third-party sharing/selling of conversation data.

> **Decision (resolved during scoping):** conversations *are* stored in full (not just metadata), with
> an auto-delete retention window (default 90 days), disclosed in the widget's privacy notice. This
> is what makes `/weekly` summaries and per-conversation Telegram summaries possible. If you want
> stricter handling later, this is a config change (retention days), not an architecture change.

## 4. Data Retention

| Data | Retention | Notes |
|---|---|---|
| Conversation transcripts | 90 days, then hard-deleted | nightly purge job |
| Escalation + contact info (leads) | Kept indefinitely (it's a lead, not a transcript) | separate table, only populated if user opts in by leaving contact |
| Aggregate usage stats (counts, tokens, cost) | Kept indefinitely | no PII, needed for trend reporting |

## 5. "Anything else good" — additions beyond the ask

- **Cost/abuse protection**: per-IP/session rate limiting on the public endpoint — a public LLM
  endpoint you're personally paying for needs a ceiling.
- **Lead capture separate from transcripts**: recruiters who leave an email become a durable "leads"
  record even after the transcript retention window expires, so you don't lose the contact.
- **Confidence-aware answers**: agent explicitly says "I'm not sure, let me get Chitresh" rather than
  guessing — this is what makes escalation trustworthy instead of just a catch-all.
- **Weekly digest is push, not just pull**: sent automatically every Monday rather than requiring you
  to remember to ask.
- **Basic input hygiene**: light scrub for things like pasted card numbers before storage — not a
  legal requirement here, just cheap insurance.

## 6. Constraints / explicit non-goals (v1)

- **LinkedIn**: no official public API for this use case (their Profile API requires a partner
  agreement). We will *not* build live LinkedIn scraping/integration — content is manually curated
  into the bio doc instead. Revisit only if LinkedIn opens relevant API access.
- **No vector DB / RAG**: knowledge base (resume + bio + GitHub summary) is small enough to fit
  directly in context. Adding embeddings/a vector store now would be solving a scale problem that
  doesn't exist yet — see [[ARCHITECTURE.md]] for the upgrade path if the knowledge base grows.
- **No separate admin web dashboard**: Telegram is the entire admin surface in v1.
- **No user accounts / auth** on the public widget — it's anonymous, session-based.

## 7. Success Metrics

- % of conversations resolved without escalation.
- Escalations that include a contact email (i.e., usable leads) vs. dead-end escalations.
- Weekly active recruiters (unique sessions).
- LLM cost per conversation (cost control check).

## 8. Naming

Finalized: **Relay**, at relay.chitreshgyanani.com — see [[ARCHITECTURE.md]] §8 for reasoning and the
Telegram `@handle` note.
