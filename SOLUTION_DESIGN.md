# CXeller8 — Solution Design Document

**Version:** 1.0  
**Date:** 2026-06-16  
**Status:** Active  

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Scope & Objectives](#2-scope--objectives)
3. [Architecture Overview](#3-architecture-overview)
4. [System Components](#4-system-components)
   - 4.1 [Backend Server](#41-backend-server)
   - 4.2 [Frontend Applications](#42-frontend-applications)
   - 4.3 [Database Layer](#43-database-layer)
   - 4.4 [AI / RAG Component](#44-ai--rag-component)
5. [Data Design](#5-data-design)
6. [API Design](#6-api-design)
7. [Real-time Communication Design](#7-real-time-communication-design)
8. [WebRTC Architecture](#8-webrtc-architecture)
9. [Security Design](#9-security-design)
10. [Deployment Architecture](#10-deployment-architecture)
11. [Performance & Scalability Considerations](#11-performance--scalability-considerations)
12. [Risks & Mitigations](#12-risks--mitigations)
13. [Future Roadmap](#13-future-roadmap)

---

## 1. Executive Summary

CXeller8 is a browser-based AI-augmented contact centre platform that enables real-time voice and text support between customers and agents. The platform is built on Node.js with WebRTC for peer-to-peer audio, Socket.IO for real-time signalling, a Turso cloud SQLite database for persistence, and a Groq-powered RAG chatbot ("Nikki") that deflects routine enquiries before connecting customers to a live agent.

The system serves three distinct user roles — **Customer**, **Agent**, and **Supervisor** — each with a dedicated, single-page web interface. All three interfaces communicate with a single Node.js process, keeping operational complexity low while meeting the latency requirements of real-time voice.

---

## 2. Scope & Objectives

### 2.1 In Scope

| Capability | Description |
|---|---|
| Voice calls | Browser-to-browser audio via WebRTC, routed through Socket.IO signalling |
| Live chat | Text chat with file attachment support |
| Screen sharing | Agent or customer can share a browser tab during a call |
| AI chatbot | Nikki — a RAG-powered first-line support bot backed by an uploadable knowledge base |
| Agent workspace | Call queue, call controls, transfer, escalation, notes, dispositions, history |
| Supervisor dashboard | Live monitoring, agent management, escalation inbox, 30-day analytics |
| Authentication | JWT-based login for agents and supervisors |
| Persistent records | All calls, chats, notes, dispositions, ratings, and KB documents stored in Turso |

### 2.2 Out of Scope (v1.0)

- PSTN / SIP gateway integration
- Mobile native applications
- Customer-side login / user accounts
- End-to-end encrypted call recordings stored in cloud storage
- Multi-tenant / multi-organisation support

### 2.3 Key Goals

1. Sub-second call setup from queue accept to active call.
2. Zero-infrastructure-cost hosting on Render free tier + Turso free tier.
3. AI deflection rate high enough to reduce agent load without degrading customer satisfaction.
4. Supervisor visibility of every active call and queue position in real time.

---

## 3. Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Browser Clients                      │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   Customer   │  │    Agent     │  │    Supervisor    │  │
│  │  (public/)   │  │  (agent/)    │  │  (supervisor/)   │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │
│         │   WebSocket (Socket.IO) + HTTPS      │            │
└─────────┼───────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│                    Node.js Server                           │
│                 Express  +  Socket.IO                       │
│                                                             │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │  REST API   │  │  WebRTC      │  │  In-memory state │   │
│  │  (/api/*)   │  │  Signalling  │  │  (agents, calls, │   │
│  │             │  │  relay       │  │   queue, chats)  │   │
│  └──────┬──────┘  └──────────────┘  └──────────────────┘   │
│         │                                                   │
└─────────┼───────────────────────────────────────────────────┘
          │                        │
          ▼                        ▼
┌──────────────────┐     ┌──────────────────────┐
│  Turso (SQLite)  │     │  Groq API            │
│  Cloud Database  │     │  (LLM inference)     │
│                  │     │  llama-3.3-70b       │
└──────────────────┘     └──────────────────────┘
```

### Design Principles

- **Single-process simplicity.** All real-time state lives in the Node.js process memory. This eliminates the need for Redis or a message broker at current scale.
- **No frontend framework.** Vanilla HTML/CSS/JS minimises bundle size, eliminates build tooling, and ensures the three single-page apps load instantly even on low-bandwidth connections.
- **Serverless database.** Turso provides a persistent, SQL-queryable store with near-zero operational overhead and an HTTP-compatible edge-friendly driver.
- **AI as deflection, not replacement.** The Nikki chatbot is offered first; customers escalate to a live agent when needed.

---

## 4. System Components

### 4.1 Backend Server

**File:** `server.js` (~617 lines)

The server combines Express (HTTP/REST) and Socket.IO (WebSocket) on a single port. On startup it:

1. Creates/migrates all database tables via `db.js`.
2. Registers REST routes under `/api/`.
3. Registers Socket.IO event handlers for the entire call/chat lifecycle.
4. Serves the three static SPAs from the `public/` directory.

**In-memory state objects (non-persistent, reset on process restart):**

| Object | Contents |
|---|---|
| `connectedAgents` | Map of `agentId → { socketId, name, email, status, currentCall }` |
| `callQueue` | Array of pending customer call requests with join timestamp |
| `activeCalls` | Map of `callId → { customerId, agentId, startTime, ... }` |
| `activeChats` | Map of `chatId → { customerId, agentId, ... }` |
| `escalations` | Map of `callId → { agentId, supervisorId, reason, status }` |

These are synchronised to all connected clients via targeted Socket.IO emissions whenever state changes.

### 4.2 Frontend Applications

All three SPAs are served as static files from `public/`. They share no build step; each is a self-contained `index.html` file with inline `<style>` and `<script>` sections.

#### Customer Interface (`public/customer/index.html`)

Entry point for end customers. Presents:

1. **Nikki chatbot** — auto-opened on load; powered by the `/api/nikki/chat` endpoint.
2. **Call / Chat choice** — customer can request a voice call or text chat at any time.
3. **Active call UI** — once an agent accepts, WebRTC audio starts; controls shown: mute, hold indicator, speaker, screen-share viewer, volume, quality indicator, timer.
4. **Post-call rating** — 1–5 star widget persisted to the database.

State machine (customer call flow):

```
idle → waiting (in queue) → ringing (agent accepted) → active call → ended → rated
```

#### Agent Dashboard (`public/agent/index.html`)

Requires JWT login. Divided into three panels:

- **Left panel:** incoming call alert, active call controls (mute, hold, transfer, escalate, record, screen-share), chat window, call notes, disposition selector.
- **Centre panel:** call queue view, agent availability toggle.
- **Right panel:** daily stats, 7-day trend chart, available-agents list for transfer, call history.

Keyboard shortcuts: `M` mute · `H` hold · `E` escalate · `A` accept call.

#### Supervisor Dashboard (`public/supervisor/index.html`)

Requires JWT login. Contains:

- Live call tiles (customer name, agent, duration, status).
- Queue panel with wait times per position.
- Agent status board.
- Escalation inbox with accept/decline buttons.
- Agent management (add/remove accounts).
- Analytics section with Chart.js visualisations: 30-day call volume, average rating trend, disposition pie, per-agent performance table.

### 4.3 Database Layer

**File:** `db.js` (~430 lines)

Wraps the `@libsql/client` Turso driver. Responsibilities:

- Schema creation and idempotent `CREATE TABLE IF NOT EXISTS` migrations on startup.
- All SQL queries; no ORM — raw parameterised SQL to keep the dependency surface minimal.
- Per-agent daily statistics upsert pattern (`INSERT OR REPLACE INTO daily_stats`).
- Knowledge-base document chunking storage and retrieval.

See [Section 5](#5-data-design) for the full schema.

### 4.4 AI / RAG Component

**File:** `rag.js` (~116 lines)

The Nikki chatbot uses a lightweight two-stage pipeline:

**Stage 1 — Retrieval (TF-IDF keyword matching)**

```
User query
    │
    ▼
Tokenise + remove stopwords
    │
    ▼
Score each KB chunk (term overlap / IDF weighting)
    │
    ▼
Return top-N chunks as context
```

- Chunk size: 400 words with 60-word overlap to preserve sentence context across boundaries.
- No vector embeddings or external embedding API; retrieval is computed in-process.

**Stage 2 — Generation (Groq LLM)**

The top chunks are concatenated into a system prompt alongside a persona instruction for Nikki, then sent to the Groq API (`llama-3.3-70b-versatile`). The response is streamed back to the customer browser via the REST endpoint.

**Knowledge base ingestion:**

| Format | Parser |
|---|---|
| `.pdf` | `pdf-parse` |
| `.docx` / `.doc` | `mammoth` |
| `.txt` | Node built-in `fs` |

Uploaded files are parsed on the server, chunked, and stored in `kb_chunks`. Documents are listed and deletable via the supervisor KB management UI.

---

## 5. Data Design

### 5.1 Entity-Relationship Summary

```
agents ─────< calls (agent_id)
agents ─────< daily_stats (agent_id)
agents ─────< call_notes (agent_id)
calls ──────< recordings (call_id)
calls ──────< call_notes (call_id)
calls ──────< escalations (call_id)
chats ──────< messages (chat_id)
kb_documents ─< kb_chunks (document_id)
```

### 5.2 Table Definitions

#### `agents`

| Column | Type | Notes |
|---|---|---|
| `id` | TEXT PK | UUID |
| `name` | TEXT | Display name |
| `email` | TEXT UNIQUE | Login identifier |
| `password_hash` | TEXT | bcrypt hash |
| `role` | TEXT | `agent` or `supervisor` |
| `created_at` | DATETIME | ISO 8601 |

#### `calls`

| Column | Type | Notes |
|---|---|---|
| `id` | TEXT PK | UUID |
| `customer_id` | TEXT | Socket ID at time of call |
| `customer_name` | TEXT | Self-reported by customer |
| `agent_id` | TEXT FK→agents | Handling agent |
| `started_at` | DATETIME | |
| `ended_at` | DATETIME | NULL while active |
| `duration_seconds` | INTEGER | |
| `rating` | INTEGER | 1–5, NULL if not rated |
| `disposition` | TEXT | `resolved`, `escalated`, `dropped` |
| `notes` | TEXT | Agent post-call notes |
| `recorded` | INTEGER | 0/1 boolean |

#### `chats`

| Column | Type | Notes |
|---|---|---|
| `id` | TEXT PK | UUID |
| `customer_id` | TEXT | Socket ID |
| `customer_name` | TEXT | |
| `agent_id` | TEXT FK→agents | |
| `started_at` | DATETIME | |
| `ended_at` | DATETIME | |

#### `messages`

| Column | Type | Notes |
|---|---|---|
| `id` | TEXT PK | UUID |
| `chat_id` | TEXT FK→chats | |
| `sender` | TEXT | `customer` or `agent` |
| `content` | TEXT | Message body |
| `file_url` | TEXT | Optional attachment URL |
| `sent_at` | DATETIME | |

#### `daily_stats`

| Column | Type | Notes |
|---|---|---|
| `agent_id` | TEXT FK→agents | Composite PK with `date` |
| `date` | TEXT | YYYY-MM-DD |
| `calls_received` | INTEGER | |
| `calls_handled` | INTEGER | |
| `calls_missed` | INTEGER | |
| `total_duration` | INTEGER | Seconds |
| `avg_rating` | REAL | |

#### `escalations`

| Column | Type | Notes |
|---|---|---|
| `id` | TEXT PK | UUID |
| `call_id` | TEXT FK→calls | |
| `agent_id` | TEXT FK→agents | Escalating agent |
| `supervisor_id` | TEXT FK→agents | Accepting supervisor |
| `reason` | TEXT | Agent-entered reason |
| `status` | TEXT | `pending`, `accepted`, `declined` |
| `created_at` | DATETIME | |

#### `recordings`

| Column | Type | Notes |
|---|---|---|
| `id` | TEXT PK | UUID |
| `call_id` | TEXT FK→calls | |
| `agent_id` | TEXT FK→agents | |
| `url` | TEXT | Storage URL |
| `duration_seconds` | INTEGER | |
| `created_at` | DATETIME | |

#### `call_notes`

| Column | Type | Notes |
|---|---|---|
| `id` | TEXT PK | UUID |
| `call_id` | TEXT FK→calls | |
| `agent_id` | TEXT FK→agents | |
| `content` | TEXT | |
| `created_at` | DATETIME | |

#### `kb_documents`

| Column | Type | Notes |
|---|---|---|
| `id` | TEXT PK | UUID |
| `filename` | TEXT | Original file name |
| `file_type` | TEXT | `pdf`, `docx`, `txt` |
| `chunk_count` | INTEGER | Number of chunks produced |
| `uploaded_at` | DATETIME | |
| `uploaded_by` | TEXT FK→agents | |

#### `kb_chunks`

| Column | Type | Notes |
|---|---|---|
| `id` | TEXT PK | UUID |
| `document_id` | TEXT FK→kb_documents | |
| `chunk_index` | INTEGER | Position within document |
| `content` | TEXT | 400-word text window |

---

## 6. API Design

All REST endpoints are prefixed `/api/`. Endpoints marked **[auth]** require a valid JWT Bearer token.

### 6.1 Authentication

| Method | Path | Description |
|---|---|---|
| POST | `/api/login` | Accepts `{ email, password }`, returns `{ token, agent }` |

### 6.2 Agent

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/agent/history` | [auth] | Paginated call history for the current agent |
| GET | `/api/agent/stats` | [auth] | Daily stats + 7-day trend for the current agent |

### 6.3 Supervisor

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/supervisor/agents` | [auth] | List all agents |
| POST | `/api/supervisor/agents` | [auth] | Create a new agent account |
| DELETE | `/api/supervisor/agents/:id` | [auth] | Remove an agent account |
| GET | `/api/supervisor/overview` | [auth] | Today's stats + 30-day trend + per-agent table |

### 6.4 Knowledge Base

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/kb/upload` | [auth] | Upload a document (multipart/form-data) |
| GET | `/api/kb/documents` | [auth] | List all KB documents |
| DELETE | `/api/kb/documents/:id` | [auth] | Remove a document and its chunks |

### 6.5 Chatbot

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/nikki/chat` | Public | Send `{ message, history[] }` → returns Nikki's reply |

### 6.6 Recordings & Notes

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/recordings` | [auth] | List recordings for the current agent |
| POST | `/api/notes` | [auth] | Save post-call notes `{ callId, content }` |

### 6.7 Health

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/health/groq` | Public | Test Groq API connectivity |
| GET | `/api/health/turso` | Public | Test Turso DB connectivity |
| GET | `/api/health/info` | Public | Server uptime and version |

### 6.8 Error Responses

All endpoints return JSON errors in the form:

```json
{ "error": "Human-readable message" }
```

HTTP status codes used: `200`, `201`, `400`, `401`, `403`, `404`, `500`.

---

## 7. Real-time Communication Design

Socket.IO carries all real-time events over a persistent WebSocket connection. The server acts as an event relay; browsers never communicate directly via Socket.IO.

### 7.1 Agent Lifecycle Events

| Event | Direction | Payload | Description |
|---|---|---|---|
| `agent-join` | Client → Server | `{ token }` | Agent authenticates socket after login |
| `agent-set-status` | Client → Server | `{ status }` | Toggle `available` / `busy` / `offline` |
| `agents-updated` | Server → All agents | `[agentList]` | Broadcast updated agent state after any change |

### 7.2 Call Flow Events

```
Customer                   Server                     Agent
   │                          │                          │
   │── customer-call-request ─►│                          │
   │                          │── call-queue-update ─────►│ (all agents)
   │                          │                          │
   │                          │◄─ agent-accept-call ──────│
   │◄──── call-accepted ───── │── call-accepted ─────────►│
   │                          │                          │
   │  ◄═══ WebRTC Signalling (webrtc-offer/answer/ice) ═══►│
   │                          │                          │
   │── end-call ─────────────►│── end-call ─────────────►│
   │◄──── call-ended ─────────│◄──── call-ended ──────────│
   │                          │                          │
   │── customer-rating ───────►│                          │
```

### 7.3 Call Control Events

| Event | Sender | Recipients | Description |
|---|---|---|---|
| `agent-hold` | Agent | Customer | Places call on hold |
| `agent-mute` | Agent | Customer | Notifies customer of agent mute state |
| `customer-mute` | Customer | Agent | Notifies agent of customer mute state |
| `screen-share-start` | Either | Other party | Screen share has begun |
| `screen-share-stop` | Either | Other party | Screen share ended |

### 7.4 Transfer & Escalation Events

| Event | Description |
|---|---|
| `agent-transfer` | Agent requests handoff to another agent; customer rejoins queue at front |
| `agent-escalate` | Agent escalates live call to supervisor queue |
| `supervisor-accept-escalation` | Supervisor joins the call; original agent may drop |

### 7.5 Chat Events

| Event | Direction | Description |
|---|---|---|
| `customer-chat-request` | Customer → Server | Initiate a chat |
| `chat-accept` | Server → Agent | Agent assigned to chat |
| `chat-message` | Either → Server → Other | Individual message (text or file) |
| `chat-file` | Either → Server → Other | Binary file transfer metadata |
| `chat-end` | Either | Close chat session |

---

## 8. WebRTC Architecture

WebRTC establishes a peer-to-peer media channel directly between the customer's and agent's browsers. The Node.js server acts only as a **signalling relay** — it never handles media.

### 8.1 Signalling Flow

```
1. Agent accepts call  → server emits `call-accepted` to both parties.
2. Agent creates RTCPeerConnection and generates an SDP offer.
3. Agent emits `webrtc-offer` with SDP → server relays to customer.
4. Customer sets remote description, generates SDP answer.
5. Customer emits `webrtc-answer` → server relays to agent.
6. Both sides exchange ICE candidates via `webrtc-ice` events.
7. ICE completes → DTLS handshake → media flows peer-to-peer.
```

### 8.2 ICE Configuration

The current implementation uses the browser's default STUN servers (`stun:stun.l.google.com:19302`). For environments where NAT traversal fails (symmetric NAT, corporate firewalls), a TURN relay server would need to be provisioned.

### 8.3 Media Tracks

| Track | Codec (browser default) | Notes |
|---|---|---|
| Audio | Opus | Stereo, 48 kHz |
| Screen video | VP8 / H.264 | Only when screen share is active |

---

## 9. Security Design

### 9.1 Authentication & Authorisation

- Passwords are hashed with **bcrypt** (salt rounds = 10).
- Login returns a **JWT** signed with `JWT_SECRET`; default expiry is 24 hours.
- Every protected REST endpoint and the `agent-join` Socket.IO event verify the JWT before processing.
- Role-based access: supervisor-only routes (`/api/supervisor/*`) reject tokens with `role = agent`.

### 9.2 Input Validation

- File uploads are restricted to known MIME types (`application/pdf`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document`, `text/plain`).
- All SQL queries use parameterised statements — no string interpolation.
- Chat messages and call notes are stored as plain text with no HTML execution surface (rendered via `textContent` in the SPA, not `innerHTML`).

### 9.3 Transport Security

- All traffic travels over HTTPS/WSS in production (enforced by Render's TLS termination).
- WebRTC media is encrypted with **DTLS-SRTP** by the browser, regardless of signalling channel security.

### 9.4 Known Limitations (v1.0)

| Limitation | Risk | Recommended Mitigation |
|---|---|---|
| In-memory session state | Lost on process restart; agents are disconnected | Persist active-session state to Turso or introduce Redis |
| No rate limiting on `/api/nikki/chat` | Groq API quota exhaustion from public endpoint | Add `express-rate-limit` middleware |
| Default supervisor credentials in codebase | Credential exposure if `.env` is misconfigured | Require password reset on first login; remove hardcoded fallback |
| No TURN server configured | Calls may fail for customers behind restrictive NAT | Provision a TURN server (e.g., Coturn) and pass ICE config via API |

---

## 10. Deployment Architecture

### 10.1 Production Topology

```
Internet
    │  HTTPS / WSS
    ▼
Render Web Service  (Node.js, 1 instance, free tier)
    │
    ├──► Turso database  (libsql over HTTPS, AWS ap-south-1)
    └──► Groq API        (HTTPS, LLM inference)
```

All three tiers are managed SaaS — there are no VMs, containers, or databases to operate.

### 10.2 Environment Variables

| Variable | Required | Description |
|---|---|---|
| `TURSO_URL` | Yes | libsql connection URL, e.g. `libsql://db.turso.io` |
| `TURSO_TOKEN` | Yes | Turso authentication token |
| `JWT_SECRET` | Yes | Long random string for JWT signing |
| `PORT` | No | Server port (defaults to `3000`) |
| `GROQ_API_KEY` | Yes (for Nikki) | Groq API key |

### 10.3 Render Configuration (`render.yaml`)

```yaml
services:
  - type: web
    name: cxeller8
    runtime: node
    buildCommand: npm install
    startCommand: node server.js
    plan: free
    envVars:
      - key: NODE_ENV
        value: production
```

### 10.4 Database Initialisation

On every server start, `db.js` executes `CREATE TABLE IF NOT EXISTS` for all tables. Migrations are additive — new columns require manual `ALTER TABLE` or a migration script.

---

## 11. Performance & Scalability Considerations

### 11.1 Current Bottlenecks

| Bottleneck | Impact | Notes |
|---|---|---|
| Single Node.js process | All Socket.IO events serialised | Acceptable up to ~500 concurrent connections on a modest VM |
| In-memory call state | Not shared across instances | Prevents horizontal scaling without sticky sessions + external state store |
| TF-IDF retrieval scans all chunks on every query | Latency grows linearly with KB size | Acceptable for small KBs (<1,000 chunks); index needed beyond |
| Turso free tier: 1 GB storage, 8 GB transfer/month | Hard ceiling for stored recordings metadata | Upgrade tier when storage exceeds 800 MB |

### 11.2 Scaling Path

For growth beyond free-tier limits:

1. **Add Redis** for session state (`connectedAgents`, `callQueue`, `activeCalls`) to allow multiple Node.js instances behind a load balancer.
2. **Sticky sessions** on the load balancer for Socket.IO (or migrate to Socket.IO Redis adapter).
3. **Replace TF-IDF with semantic embeddings** (e.g., `@xenova/transformers` in-process, or an external embedding API) for KB sizes above ~5,000 chunks.
4. **Turso scaler plan** for higher storage/transfer or point-in-time recovery.

---

## 12. Risks & Mitigations

| # | Risk | Probability | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Render free-tier process sleeps after 15 min inactivity, dropping all WebSockets | High | High | Upgrade to paid Render plan, or implement a self-ping keep-alive |
| R2 | Groq API unavailable / rate-limited | Medium | Medium | Graceful fallback message to customer; health endpoint exposed for monitoring |
| R3 | WebRTC call failure behind symmetric NAT | Medium | High | Provision TURN server; surface ICE failure diagnostics to agent |
| R4 | Customer data loss if server restarts mid-call | Low | Medium | Persist active call start time to DB immediately on accept; reconcile orphaned rows on startup |
| R5 | JWT secret rotation requires all agents to re-login | Low | Low | Document the procedure; short-lived tokens reduce blast radius |
| R6 | KB documents contain sensitive data accessible via Nikki | Low | High | Restrict KB upload/delete to supervisors only; audit document content before upload |

---

## 13. Future Roadmap

### Phase 2 — Reliability & Operations

- TURN server integration for reliable WebRTC behind restrictive NAT.
- Rate limiting on all public endpoints.
- Structured logging (Winston / Pino) with log forwarding to an observability platform.
- Health check dashboard integrated with uptime monitoring (e.g., Betterstack).
- Graceful shutdown: drain active calls before process exit.

### Phase 3 — Feature Expansion

- **Call recording storage** — upload recorded blobs to S3/R2 and store signed URLs.
- **Customer accounts** — allow returning customers to view their own history.
- **Canned responses** — agent shortcut library for common replies.
- **SLA alerting** — notify supervisors when queue wait time exceeds threshold.
- **Semantic KB search** — replace TF-IDF with vector embeddings for higher recall.

### Phase 4 — Scale & Multi-tenancy

- Redis-backed Socket.IO adapter for multi-instance deployments.
- Tenant isolation at the database level (organisation ID on all tables).
- SSO / OAuth2 login for enterprise agents.
- Webhook delivery for call events to external CRM systems.

---

*End of document.*
