# PRD — Relay

Status: Draft v1 · Owner: the deployer (this doc is a template — it describes a specific instance,
swap the specifics for your own) · Last updated: 2026-08-02

## 1. Problem & Goal

Recruiters skim resumes for 6-10 seconds. A conversational agent on a personal subdomain lets them ask
direct questions ("do they have Kubernetes experience?", "are they open to contract work?") and get
answers grounded in the profile owner's actual profile, instead of re-reading a PDF. When the agent
can't answer confidently, or the recruiter clearly wants to talk to a human, it should hand off to the
profile owner directly rather than making something up or dead-ending.

**Primary goal:** let a recruiter self-serve 80% of screening questions, and cleanly escalate the
other 20% with enough context that the profile owner can respond without back-and-forth.

## 2. Users

- **Recruiter / hiring manager** (primary): lands on the subdomain, asks questions, may leave contact
  info if the agent can't fully answer.
- **Profile owner (admin)**: interacts entirely through Telegram — receives escalations, replies to
  them, gets usage stats and weekly digests. No separate admin web dashboard in v1 (Telegram *is* the
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
Every agent reply is plain streamed text, plus an optional rich UI card triggered by a tool call
(experience, skills, projects, resume, etc.) rather than one monolithic structured-output object —
see [[ARCHITECTURE.md]] §3 for why, and the current tool/component table (the original
`{text, list, cards, link, contact_form}` sketch below was the pre-build placeholder; it's superseded,
kept here only as the original ask for context).

```json
{
  "message": "Here's their recent backend work:",
  "component": "cards",
  "content": [
    { "title": "Payments platform", "subtitle": "Company X, 2023-2025",
      "description": "...", "tags": ["Python", "Kafka"], "link": null }
  ]
}
```

### 3.3 Human escalation (fallback to Telegram)
**Status: shipped**, full loop. See [[ROADMAP.md]].

The agent calls `request_contact` when: the question is outside the knowledge base, the recruiter
explicitly asks to talk to the profile owner, or there's clear hiring intent worth a personal
response. There's no separate `escalate` tool — `request_contact` renders the card, and submitting
it is what actually escalates:
1. Agent tells the user it's looping the profile owner in, and renders `request_contact` to collect
   a name and email (both optional but encouraged — without an email, the profile owner can't
   respond back).
2. Submitting the form (`POST /contact`) sends the admin a Telegram alert with an LLM-generated
   summary of what the recruiter actually wants (role/opportunity, their question, why it needed a
   human — not the raw transcript), the `session_id` (so the admin can pull the full transcript via
   the admin agent's `get_session_history` tool, §3.4), and name/contact info if given; if an email
   was left, the recruiter gets an immediate receipt via Resend — personally worded and signed (not
   template-y), with the resume PDF attached.
3. The admin replies to that Telegram alert, and the reply is forwarded to the recruiter's email
   (also resume-attached) as the actual personal response — the admin's own words, not a canned
   template. The Telegram message ID of the alert is remembered against the lead so a reply to it
   can be matched back to the right recruiter (`leads.telegram_message_id`).

### 3.4 Telegram as admin interface
The admin's Telegram bot (a *second*, private bot — the user-facing web widget is not on Telegram) is
the control plane. **Status: partially built** — see [[ROADMAP.md]] for what's shipped vs. planned.
- **Shipped**: admin-only auth (single `chat_id`), real-time escalation alerts (§3.3), and a private
  admin agent (`app/admin_agent.py`) the admin chats with directly — it can save notes (retrieved by
  the public agent via `search_context`), look up any recruiter session's full transcript
  (`get_session_history`), and draft/send outreach or follow-up emails (`send_email`, resume
  attached automatically).
- **Shipped**: `/health`, `/stats` (today's traffic, sessions, token/cost usage), `/weekly` (on-demand
  digest; also auto-pushed every Monday via GitHub Actions — traffic summary, top question topics,
  LLM cost, a conversation recap).

### 3.5 Observability & governance
**Status: shipped** — see [[ROADMAP.md]].
- Conversations are stored in Postgres (`app/sessions.py`), plus escalations and leads (§4).
  Retention window below is enforced by a `pg_cron` purge job (one-time setup script,
  `backend/scripts/retention_purge.sql`), and disclosed via a privacy notice line on the widget.
- Aggregate usage stats (requests, tokens, estimated cost — `app/usage_stats.py`), independent of
  raw transcript retention — backs `/weekly`/`/stats` (§3.4).
- No third-party sharing/selling of conversation data.

> **Decision (resolved during scoping):** conversations *are* stored in full (not just metadata), with
> an auto-delete retention window (default 90 days), disclosed in the widget's privacy notice. This
> is what makes `/weekly` summaries and per-conversation Telegram summaries possible. If you want
> stricter handling later, this is a config change (retention days), not an architecture change.

## 4. Data Retention

| Data | Retention | Notes |
|---|---|---|
| Conversation transcripts | 90 days, then hard-deleted | nightly `pg_cron` purge job |
| Escalation + contact info (leads) | Kept indefinitely (it's a lead, not a transcript) | separate table, only populated if user opts in by leaving contact |
| Aggregate usage stats (counts, tokens, cost) | Kept indefinitely | no PII, needed for trend reporting |

## 5. "Anything else good" — additions beyond the ask

- **Cost/abuse protection**: per-IP/session rate limiting on the public endpoint — a public LLM
  endpoint you're personally paying for needs a ceiling.
- **Lead capture separate from transcripts**: recruiters who leave an email become a durable "leads"
  record even after the transcript retention window expires, so you don't lose the contact.
- **Confidence-aware answers**: agent explicitly says "I'm not sure, let me loop in the profile owner"
  rather than guessing — this is what makes escalation trustworthy instead of just a catch-all.
- **Weekly digest is push, not just pull**: sent automatically every Monday rather than requiring you
  to remember to ask.
- **Basic input hygiene**: light scrub for things like pasted card numbers before storage — not a
  legal requirement here, just cheap insurance.

## 6. Constraints / explicit non-goals (v1)

- **LinkedIn**: no official public API for this use case (their Profile API requires a partner
  agreement). We will *not* build live LinkedIn scraping/integration — content is manually curated
  into the bio doc instead. Revisit only if LinkedIn opens relevant API access.
- **No RAG over the static knowledge base**: resume + bio + GitHub summary is small enough to fit
  directly in context — adding embeddings/a vector store for *that* corpus would solve a scale problem
  that doesn't exist. A separate, small RAG layer *was* added, but for a different purpose: retrieving
  admin-added notes that change faster than the static profile gets rewritten (see [[ARCHITECTURE.md]]
  §6, `search_context`) — not for the core knowledge base itself.
- **No separate admin web dashboard**: Telegram is the entire admin surface in v1.
- **No user accounts / auth** on the public widget — it's anonymous, session-based.

## 7. Success Metrics

- % of conversations resolved without escalation.
- Escalations that include a contact email (i.e., usable leads) vs. dead-end escalations.
- Weekly active recruiters (unique sessions).
- LLM cost per conversation (cost control check).

## 8. Naming

Finalized: **Relay** — a chat agent name that reads fine as both a product name and a Telegram display
name, and ties into the escalation feature (the agent *relays* to the admin when it can't answer).
Deploy it at whatever personal subdomain you own, e.g. `relay.yourdomain.com` — see
[[ARCHITECTURE.md]] §10 for the Telegram `@handle` note.
