"""Generate SOLUTION_DESIGN.docx from SOLUTION_DESIGN.md content."""

from docx import Document
from docx.shared import Pt, RGBColor, Inches, Emu
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import re

doc = Document()

# ── Page margins ─────────────────────────────────────────────────────────────
for section in doc.sections:
    section.top_margin    = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin   = Inches(1.15)
    section.right_margin  = Inches(1.15)

# ── Colour palette ───────────────────────────────────────────────────────────
BLUE_DARK   = RGBColor(0x1A, 0x37, 0x6B)   # headings
BLUE_MID    = RGBColor(0x2E, 0x5E, 0xAD)   # h2 / h3
BLUE_LIGHT  = RGBColor(0xDE, 0xE8, 0xF7)   # table header bg
GREY_TEXT   = RGBColor(0x33, 0x33, 0x33)
GREY_CODE   = RGBColor(0xF4, 0xF4, 0xF4)
CODE_TEXT   = RGBColor(0x1E, 0x1E, 0x1E)

def _rgb_hex(rgb: RGBColor) -> str:
    # RGBColor is a subclass of int; str() yields the 6-char hex string
    return str(rgb).upper()

def set_cell_bg(cell, rgb: RGBColor):
    tc   = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd  = OxmlElement('w:shd')
    shd.set(qn('w:val'),   'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'),  _rgb_hex(rgb))
    tcPr.append(shd)

def set_para_bg(para, rgb: RGBColor):
    pPr  = para._p.get_or_add_pPr()
    shd  = OxmlElement('w:shd')
    shd.set(qn('w:val'),   'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'),  _rgb_hex(rgb))
    pPr.append(shd)

def add_horizontal_rule(doc):
    para   = doc.add_paragraph()
    pPr    = para._p.get_or_add_pPr()
    pBdr   = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'),   'single')
    bottom.set(qn('w:sz'),    '6')
    bottom.set(qn('w:space'), '1')
    bottom.set(qn('w:color'), '2E5EAD')
    pBdr.append(bottom)
    pPr.append(pBdr)
    para.paragraph_format.space_after = Pt(4)
    return para

def style_run(run, bold=False, italic=False, color=None, size=None, font='Calibri'):
    run.font.name  = font
    run.font.bold  = bold
    run.font.italic = italic
    if color: run.font.color.rgb = color
    if size:  run.font.size = Pt(size)

def add_h1(doc, text):
    add_horizontal_rule(doc)
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after  = Pt(6)
    run = p.add_run(text)
    style_run(run, bold=True, color=BLUE_DARK, size=18, font='Calibri Light')
    return p

def add_h2(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after  = Pt(4)
    run = p.add_run(text)
    style_run(run, bold=True, color=BLUE_MID, size=14, font='Calibri Light')
    return p

def add_h3(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after  = Pt(3)
    run = p.add_run(text)
    style_run(run, bold=True, color=BLUE_MID, size=12)
    return p

def add_h4(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after  = Pt(2)
    run = p.add_run(text)
    style_run(run, bold=True, italic=True, color=GREY_TEXT, size=11)
    return p

def add_body(doc, text, indent=0):
    """Add a paragraph, rendering inline **bold** and `code` spans."""
    p = doc.add_paragraph()
    p.paragraph_format.space_after  = Pt(4)
    p.paragraph_format.space_before = Pt(2)
    if indent:
        p.paragraph_format.left_indent = Inches(indent * 0.3)
    _add_inline(p, text)
    return p

def _add_inline(para, text):
    """Render inline markdown (bold, inline-code) into a paragraph."""
    tokens = re.split(r'(\*\*[^*]+\*\*|`[^`]+`)', text)
    for tok in tokens:
        if tok.startswith('**') and tok.endswith('**'):
            r = para.add_run(tok[2:-2])
            style_run(r, bold=True, color=GREY_TEXT, size=10)
        elif tok.startswith('`') and tok.endswith('`'):
            r = para.add_run(tok[1:-1])
            r.font.name  = 'Courier New'
            r.font.size  = Pt(9)
            r.font.color.rgb = RGBColor(0xC0, 0x39, 0x2B)
        else:
            if tok:
                r = para.add_run(tok)
                style_run(r, color=GREY_TEXT, size=10)

def add_bullet(doc, text, level=0):
    p = doc.add_paragraph(style='List Bullet')
    p.paragraph_format.space_after  = Pt(2)
    p.paragraph_format.space_before = Pt(1)
    if level:
        p.paragraph_format.left_indent = Inches(0.25 + level * 0.25)
    _add_inline(p, text)
    return p

def add_code_block(doc, text):
    lines = text.strip().split('\n')
    for line in lines:
        p = doc.add_paragraph()
        p.paragraph_format.space_after  = Pt(0)
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.left_indent  = Inches(0.2)
        p.paragraph_format.right_indent = Inches(0.2)
        set_para_bg(p, RGBColor(0xF4, 0xF4, 0xF4))
        run = p.add_run(line if line else ' ')
        run.font.name  = 'Courier New'
        run.font.size  = Pt(8.5)
        run.font.color.rgb = CODE_TEXT
    doc.add_paragraph().paragraph_format.space_after = Pt(4)

def add_table(doc, header_row, data_rows):
    cols = len(header_row)
    tbl  = doc.add_table(rows=1 + len(data_rows), cols=cols)
    tbl.style = 'Table Grid'
    tbl.alignment = WD_TABLE_ALIGNMENT.LEFT

    # Header
    hdr = tbl.rows[0]
    for i, cell_text in enumerate(header_row):
        c = hdr.cells[i]
        set_cell_bg(c, BLUE_LIGHT)
        p  = c.paragraphs[0]
        r  = p.add_run(cell_text)
        style_run(r, bold=True, color=BLUE_DARK, size=9)
        p.paragraph_format.space_after  = Pt(2)
        p.paragraph_format.space_before = Pt(2)

    # Data rows
    for ri, row_data in enumerate(data_rows):
        row = tbl.rows[ri + 1]
        bg  = RGBColor(0xFF, 0xFF, 0xFF) if ri % 2 == 0 else RGBColor(0xF8, 0xF9, 0xFB)
        for ci, cell_text in enumerate(row_data):
            c = row.cells[ci]
            set_cell_bg(c, bg)
            p = c.paragraphs[0]
            _add_inline(p, cell_text)
            for run in p.runs:
                run.font.size = Pt(9)
            p.paragraph_format.space_after  = Pt(2)
            p.paragraph_format.space_before = Pt(2)

    doc.add_paragraph().paragraph_format.space_after = Pt(6)
    return tbl

# ═══════════════════════════════════════════════════════════════════════════
#  COVER PAGE
# ═══════════════════════════════════════════════════════════════════════════
cover = doc.add_paragraph()
cover.paragraph_format.space_before = Pt(60)
cover.paragraph_format.space_after  = Pt(4)
cover.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = cover.add_run('CXeller8')
r.font.name  = 'Calibri Light'
r.font.size  = Pt(36)
r.font.bold  = True
r.font.color.rgb = BLUE_DARK

sub = doc.add_paragraph()
sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
sub.paragraph_format.space_after = Pt(2)
r2 = sub.add_run('Solution Design Document')
r2.font.name  = 'Calibri Light'
r2.font.size  = Pt(20)
r2.font.color.rgb = BLUE_MID

meta_items = [
    ('Version', '1.0'),
    ('Date', '2026-06-16'),
    ('Status', 'Active'),
]
doc.add_paragraph()
for label, val in meta_items:
    mp = doc.add_paragraph()
    mp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    mp.paragraph_format.space_after = Pt(2)
    rl = mp.add_run(f'{label}:  ')
    rl.font.bold = True
    rl.font.size = Pt(11)
    rl.font.color.rgb = GREY_TEXT
    rv = mp.add_run(val)
    rv.font.size = Pt(11)
    rv.font.color.rgb = GREY_TEXT

doc.add_page_break()

# ═══════════════════════════════════════════════════════════════════════════
#  TABLE OF CONTENTS (static)
# ═══════════════════════════════════════════════════════════════════════════
add_h1(doc, 'Table of Contents')
toc_entries = [
    ('1.', 'Executive Summary'),
    ('2.', 'Scope & Objectives'),
    ('3.', 'Architecture Overview'),
    ('4.', 'System Components'),
    ('   4.1', 'Backend Server'),
    ('   4.2', 'Frontend Applications'),
    ('   4.3', 'Database Layer'),
    ('   4.4', 'AI / RAG Component'),
    ('5.', 'Data Design'),
    ('6.', 'API Design'),
    ('7.', 'Real-time Communication Design'),
    ('8.', 'WebRTC Architecture'),
    ('9.', 'Security Design'),
    ('10.', 'Deployment Architecture'),
    ('11.', 'Performance & Scalability Considerations'),
    ('12.', 'Risks & Mitigations'),
    ('13.', 'Future Roadmap'),
]
for num, title in toc_entries:
    tp = doc.add_paragraph()
    tp.paragraph_format.space_after = Pt(3)
    indent = 0.4 if num.startswith('   ') else 0
    tp.paragraph_format.left_indent = Inches(indent)
    rn = tp.add_run(num.strip() + '  ')
    rn.font.bold = True
    rn.font.size = Pt(10)
    rn.font.color.rgb = BLUE_MID
    rt = tp.add_run(title)
    rt.font.size = Pt(10)
    rt.font.color.rgb = GREY_TEXT

doc.add_page_break()

# ═══════════════════════════════════════════════════════════════════════════
#  1. EXECUTIVE SUMMARY
# ═══════════════════════════════════════════════════════════════════════════
add_h1(doc, '1. Executive Summary')
add_body(doc, (
    'CXeller8 is a browser-based AI-augmented contact centre platform that enables real-time voice '
    'and text support between customers and agents. The platform is built on Node.js with WebRTC '
    'for peer-to-peer audio, Socket.IO for real-time signalling, a Turso cloud SQLite database for '
    'persistence, and a Groq-powered RAG chatbot ("Nikki") that deflects routine enquiries before '
    'connecting customers to a live agent.'
))
add_body(doc, (
    'The system serves three distinct user roles — **Customer**, **Agent**, and **Supervisor** — '
    'each with a dedicated single-page web interface. All three interfaces communicate with a single '
    'Node.js process, keeping operational complexity low while meeting the latency requirements of '
    'real-time voice.'
))

# ═══════════════════════════════════════════════════════════════════════════
#  2. SCOPE & OBJECTIVES
# ═══════════════════════════════════════════════════════════════════════════
add_h1(doc, '2. Scope & Objectives')

add_h2(doc, '2.1  In Scope')
add_table(doc,
    ['Capability', 'Description'],
    [
        ['Voice calls', 'Browser-to-browser audio via WebRTC, routed through Socket.IO signalling'],
        ['Live chat', 'Text chat with file attachment support'],
        ['Screen sharing', 'Agent or customer can share a browser tab during a call'],
        ['AI chatbot', 'Nikki — a RAG-powered first-line support bot backed by an uploadable knowledge base'],
        ['Agent workspace', 'Call queue, call controls, transfer, escalation, notes, dispositions, history'],
        ['Supervisor dashboard', 'Live monitoring, agent management, escalation inbox, 30-day analytics'],
        ['Authentication', 'JWT-based login for agents and supervisors'],
        ['Persistent records', 'All calls, chats, notes, dispositions, ratings, and KB documents stored in Turso'],
    ]
)

add_h2(doc, '2.2  Out of Scope (v1.0)')
for item in [
    'PSTN / SIP gateway integration',
    'Mobile native applications',
    'Customer-side login / user accounts',
    'End-to-end encrypted call recordings stored in cloud storage',
    'Multi-tenant / multi-organisation support',
]:
    add_bullet(doc, item)

add_h2(doc, '2.3  Key Goals')
for item in [
    'Sub-second call setup from queue accept to active call.',
    'Zero-infrastructure-cost hosting on Render free tier + Turso free tier.',
    'AI deflection rate high enough to reduce agent load without degrading customer satisfaction.',
    'Supervisor visibility of every active call and queue position in real time.',
]:
    add_bullet(doc, item)

# ═══════════════════════════════════════════════════════════════════════════
#  3. ARCHITECTURE OVERVIEW
# ═══════════════════════════════════════════════════════════════════════════
add_h1(doc, '3. Architecture Overview')
add_code_block(doc, """\
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
└──────────────────┘     └──────────────────────┘""")

add_h2(doc, 'Design Principles')
principles = [
    ('Single-process simplicity', 'All real-time state lives in the Node.js process memory, eliminating the need for Redis or a message broker at current scale.'),
    ('No frontend framework', 'Vanilla HTML/CSS/JS minimises bundle size, eliminates build tooling, and ensures the SPAs load instantly even on low-bandwidth connections.'),
    ('Serverless database', 'Turso provides a persistent, SQL-queryable store with near-zero operational overhead and an HTTP-compatible edge-friendly driver.'),
    ('AI as deflection', 'The Nikki chatbot is offered first; customers escalate to a live agent when needed.'),
]
for title, desc in principles:
    bp = doc.add_paragraph()
    bp.paragraph_format.space_after = Pt(3)
    bp.paragraph_format.left_indent = Inches(0.2)
    rb = bp.add_run(title + ': ')
    rb.font.bold = True
    rb.font.size = Pt(10)
    rb.font.color.rgb = BLUE_MID
    rd = bp.add_run(desc)
    rd.font.size = Pt(10)
    rd.font.color.rgb = GREY_TEXT

# ═══════════════════════════════════════════════════════════════════════════
#  4. SYSTEM COMPONENTS
# ═══════════════════════════════════════════════════════════════════════════
add_h1(doc, '4. System Components')

add_h2(doc, '4.1  Backend Server')
add_body(doc, '**File:** `server.js` (~617 lines)')
add_body(doc, (
    'The server combines Express (HTTP/REST) and Socket.IO (WebSocket) on a single port. '
    'On startup it creates/migrates all database tables, registers REST routes under `/api/`, '
    'registers Socket.IO event handlers for the entire call/chat lifecycle, and serves the '
    'three static SPAs from the `public/` directory.'
))
add_h3(doc, 'In-memory state objects (non-persistent, reset on process restart)')
add_table(doc,
    ['Object', 'Contents'],
    [
        ['`connectedAgents`', 'Map of agentId → { socketId, name, email, status, currentCall }'],
        ['`callQueue`', 'Array of pending customer call requests with join timestamp'],
        ['`activeCalls`', 'Map of callId → { customerId, agentId, startTime, … }'],
        ['`activeChats`', 'Map of chatId → { customerId, agentId, … }'],
        ['`escalations`', 'Map of callId → { agentId, supervisorId, reason, status }'],
    ]
)

add_h2(doc, '4.2  Frontend Applications')
add_body(doc, (
    'All three SPAs are served as static files from `public/`. They share no build step; each is a '
    'self-contained `index.html` file with inline `<style>` and `<script>` sections.'
))

add_h3(doc, 'Customer Interface  (public/customer/index.html)')
add_body(doc, 'Entry point for end customers. Presents:')
for item in [
    '**Nikki chatbot** — auto-opened on load; powered by the `/api/nikki/chat` endpoint.',
    '**Call / Chat choice** — customer can request a voice call or text chat at any time.',
    '**Active call UI** — once an agent accepts, WebRTC audio starts; controls: mute, hold indicator, speaker, screen-share viewer, volume, quality indicator, timer.',
    '**Post-call rating** — 1–5 star widget persisted to the database.',
]:
    add_bullet(doc, item)

add_h3(doc, 'Agent Dashboard  (public/agent/index.html)')
add_body(doc, 'Requires JWT login. Divided into three panels:')
for item in [
    '**Left panel:** incoming call alert, active call controls (mute, hold, transfer, escalate, record, screen-share), chat window, call notes, disposition selector.',
    '**Centre panel:** call queue view, agent availability toggle.',
    '**Right panel:** daily stats, 7-day trend chart, available-agents list for transfer, call history.',
]:
    add_bullet(doc, item)
add_body(doc, 'Keyboard shortcuts: `M` mute · `H` hold · `E` escalate · `A` accept call.')

add_h3(doc, 'Supervisor Dashboard  (public/supervisor/index.html)')
add_body(doc, 'Requires JWT login. Contains:')
for item in [
    'Live call tiles (customer name, agent, duration, status).',
    'Queue panel with wait times per position.',
    'Agent status board.',
    'Escalation inbox with accept/decline buttons.',
    'Agent management (add/remove accounts).',
    'Analytics section with Chart.js visualisations: 30-day call volume, average rating trend, disposition pie, per-agent performance table.',
]:
    add_bullet(doc, item)

add_h2(doc, '4.3  Database Layer')
add_body(doc, '**File:** `db.js` (~430 lines)')
add_body(doc, (
    'Wraps the `@libsql/client` Turso driver. Responsibilities: schema creation and idempotent '
    '`CREATE TABLE IF NOT EXISTS` migrations on startup; all SQL queries via raw parameterised SQL; '
    'per-agent daily statistics upsert pattern; and knowledge-base document chunking storage and retrieval.'
))

add_h2(doc, '4.4  AI / RAG Component')
add_body(doc, '**File:** `rag.js` (~116 lines)')
add_body(doc, 'The Nikki chatbot uses a lightweight two-stage pipeline:')

add_h3(doc, 'Stage 1 — Retrieval (TF-IDF keyword matching)')
add_code_block(doc, """\
User query
    │
    ▼
Tokenise + remove stopwords
    │
    ▼
Score each KB chunk (term overlap / IDF weighting)
    │
    ▼
Return top-N chunks as context""")
for item in [
    'Chunk size: 400 words with 60-word overlap to preserve sentence context across boundaries.',
    'No vector embeddings or external embedding API; retrieval is computed in-process.',
]:
    add_bullet(doc, item)

add_h3(doc, 'Stage 2 — Generation (Groq LLM)')
add_body(doc, (
    'The top chunks are concatenated into a system prompt alongside a persona instruction for Nikki, '
    'then sent to the Groq API (`llama-3.3-70b-versatile`). The response is streamed back to the '
    'customer browser via the REST endpoint.'
))

add_h3(doc, 'Knowledge base ingestion')
add_table(doc,
    ['Format', 'Parser'],
    [
        ['.pdf', 'pdf-parse'],
        ['.docx / .doc', 'mammoth'],
        ['.txt', 'Node built-in fs'],
    ]
)

# ═══════════════════════════════════════════════════════════════════════════
#  5. DATA DESIGN
# ═══════════════════════════════════════════════════════════════════════════
add_h1(doc, '5. Data Design')

add_h2(doc, '5.1  Entity-Relationship Summary')
add_code_block(doc, """\
agents ─────< calls (agent_id)
agents ─────< daily_stats (agent_id)
agents ─────< call_notes (agent_id)
calls ──────< recordings (call_id)
calls ──────< call_notes (call_id)
calls ──────< escalations (call_id)
chats ──────< messages (chat_id)
kb_documents ─< kb_chunks (document_id)""")

add_h2(doc, '5.2  Table Definitions')

tables_def = [
    ('agents', ['Column', 'Type', 'Notes'], [
        ['id', 'TEXT PK', 'UUID'],
        ['name', 'TEXT', 'Display name'],
        ['email', 'TEXT UNIQUE', 'Login identifier'],
        ['password_hash', 'TEXT', 'bcrypt hash'],
        ['role', 'TEXT', '`agent` or `supervisor`'],
        ['created_at', 'DATETIME', 'ISO 8601'],
    ]),
    ('calls', ['Column', 'Type', 'Notes'], [
        ['id', 'TEXT PK', 'UUID'],
        ['customer_id', 'TEXT', 'Socket ID at time of call'],
        ['customer_name', 'TEXT', 'Self-reported by customer'],
        ['agent_id', 'TEXT FK→agents', 'Handling agent'],
        ['started_at', 'DATETIME', ''],
        ['ended_at', 'DATETIME', 'NULL while active'],
        ['duration_seconds', 'INTEGER', ''],
        ['rating', 'INTEGER', '1–5, NULL if not rated'],
        ['disposition', 'TEXT', '`resolved`, `escalated`, `dropped`'],
        ['notes', 'TEXT', 'Agent post-call notes'],
        ['recorded', 'INTEGER', '0/1 boolean'],
    ]),
    ('chats', ['Column', 'Type', 'Notes'], [
        ['id', 'TEXT PK', 'UUID'],
        ['customer_id', 'TEXT', 'Socket ID'],
        ['customer_name', 'TEXT', ''],
        ['agent_id', 'TEXT FK→agents', ''],
        ['started_at', 'DATETIME', ''],
        ['ended_at', 'DATETIME', ''],
    ]),
    ('messages', ['Column', 'Type', 'Notes'], [
        ['id', 'TEXT PK', 'UUID'],
        ['chat_id', 'TEXT FK→chats', ''],
        ['sender', 'TEXT', '`customer` or `agent`'],
        ['content', 'TEXT', 'Message body'],
        ['file_url', 'TEXT', 'Optional attachment URL'],
        ['sent_at', 'DATETIME', ''],
    ]),
    ('daily_stats', ['Column', 'Type', 'Notes'], [
        ['agent_id', 'TEXT FK→agents', 'Composite PK with `date`'],
        ['date', 'TEXT', 'YYYY-MM-DD'],
        ['calls_received', 'INTEGER', ''],
        ['calls_handled', 'INTEGER', ''],
        ['calls_missed', 'INTEGER', ''],
        ['total_duration', 'INTEGER', 'Seconds'],
        ['avg_rating', 'REAL', ''],
    ]),
    ('escalations', ['Column', 'Type', 'Notes'], [
        ['id', 'TEXT PK', 'UUID'],
        ['call_id', 'TEXT FK→calls', ''],
        ['agent_id', 'TEXT FK→agents', 'Escalating agent'],
        ['supervisor_id', 'TEXT FK→agents', 'Accepting supervisor'],
        ['reason', 'TEXT', 'Agent-entered reason'],
        ['status', 'TEXT', '`pending`, `accepted`, `declined`'],
        ['created_at', 'DATETIME', ''],
    ]),
    ('recordings', ['Column', 'Type', 'Notes'], [
        ['id', 'TEXT PK', 'UUID'],
        ['call_id', 'TEXT FK→calls', ''],
        ['agent_id', 'TEXT FK→agents', ''],
        ['url', 'TEXT', 'Storage URL'],
        ['duration_seconds', 'INTEGER', ''],
        ['created_at', 'DATETIME', ''],
    ]),
    ('call_notes', ['Column', 'Type', 'Notes'], [
        ['id', 'TEXT PK', 'UUID'],
        ['call_id', 'TEXT FK→calls', ''],
        ['agent_id', 'TEXT FK→agents', ''],
        ['content', 'TEXT', ''],
        ['created_at', 'DATETIME', ''],
    ]),
    ('kb_documents', ['Column', 'Type', 'Notes'], [
        ['id', 'TEXT PK', 'UUID'],
        ['filename', 'TEXT', 'Original file name'],
        ['file_type', 'TEXT', '`pdf`, `docx`, `txt`'],
        ['chunk_count', 'INTEGER', 'Number of chunks produced'],
        ['uploaded_at', 'DATETIME', ''],
        ['uploaded_by', 'TEXT FK→agents', ''],
    ]),
    ('kb_chunks', ['Column', 'Type', 'Notes'], [
        ['id', 'TEXT PK', 'UUID'],
        ['document_id', 'TEXT FK→kb_documents', ''],
        ['chunk_index', 'INTEGER', 'Position within document'],
        ['content', 'TEXT', '400-word text window'],
    ]),
]

for tname, headers, rows in tables_def:
    add_h3(doc, f'`{tname}`')
    add_table(doc, headers, rows)

# ═══════════════════════════════════════════════════════════════════════════
#  6. API DESIGN
# ═══════════════════════════════════════════════════════════════════════════
add_h1(doc, '6. API Design')
add_body(doc, 'All REST endpoints are prefixed `/api/`. Endpoints marked **[auth]** require a valid JWT Bearer token.')

api_sections = [
    ('6.1  Authentication', ['Method', 'Path', 'Description'], [
        ['POST', '/api/login', 'Accepts { email, password }, returns { token, agent }'],
    ]),
    ('6.2  Agent', ['Method', 'Path', 'Auth', 'Description'], [
        ['GET', '/api/agent/history', '[auth]', 'Paginated call history for the current agent'],
        ['GET', '/api/agent/stats',   '[auth]', 'Daily stats + 7-day trend for the current agent'],
    ]),
    ('6.3  Supervisor', ['Method', 'Path', 'Auth', 'Description'], [
        ['GET',    '/api/supervisor/agents',    '[auth]', 'List all agents'],
        ['POST',   '/api/supervisor/agents',    '[auth]', 'Create a new agent account'],
        ['DELETE', '/api/supervisor/agents/:id','[auth]', 'Remove an agent account'],
        ['GET',    '/api/supervisor/overview',  '[auth]', "Today's stats + 30-day trend + per-agent table"],
    ]),
    ('6.4  Knowledge Base', ['Method', 'Path', 'Auth', 'Description'], [
        ['POST',   '/api/kb/upload',          '[auth]', 'Upload a document (multipart/form-data)'],
        ['GET',    '/api/kb/documents',       '[auth]', 'List all KB documents'],
        ['DELETE', '/api/kb/documents/:id',   '[auth]', 'Remove a document and its chunks'],
    ]),
    ('6.5  Chatbot', ['Method', 'Path', 'Auth', 'Description'], [
        ['POST', '/api/nikki/chat', 'Public', "Send { message, history[] } → returns Nikki's reply"],
    ]),
    ('6.6  Recordings & Notes', ['Method', 'Path', 'Auth', 'Description'], [
        ['GET',  '/api/recordings', '[auth]', 'List recordings for the current agent'],
        ['POST', '/api/notes',      '[auth]', 'Save post-call notes { callId, content }'],
    ]),
    ('6.7  Health', ['Method', 'Path', 'Auth', 'Description'], [
        ['GET', '/api/health/groq',  'Public', 'Test Groq API connectivity'],
        ['GET', '/api/health/turso', 'Public', 'Test Turso DB connectivity'],
        ['GET', '/api/health/info',  'Public', 'Server uptime and version'],
    ]),
]

for section_title, headers, rows in api_sections:
    add_h2(doc, section_title)
    add_table(doc, headers, rows)

add_h2(doc, '6.8  Error Responses')
add_body(doc, 'All endpoints return JSON errors in the form:')
add_code_block(doc, '{ "error": "Human-readable message" }')
add_body(doc, 'HTTP status codes used: `200`, `201`, `400`, `401`, `403`, `404`, `500`.')

# ═══════════════════════════════════════════════════════════════════════════
#  7. REAL-TIME COMMUNICATION
# ═══════════════════════════════════════════════════════════════════════════
add_h1(doc, '7. Real-time Communication Design')
add_body(doc, (
    'Socket.IO carries all real-time events over a persistent WebSocket connection. '
    'The server acts as an event relay; browsers never communicate directly via Socket.IO.'
))

add_h2(doc, '7.1  Agent Lifecycle Events')
add_table(doc,
    ['Event', 'Direction', 'Payload', 'Description'],
    [
        ['`agent-join`',       'Client → Server', '{ token }',  'Agent authenticates socket after login'],
        ['`agent-set-status`', 'Client → Server', '{ status }', 'Toggle available / busy / offline'],
        ['`agents-updated`',   'Server → All agents', '[agentList]', 'Broadcast updated agent state after any change'],
    ]
)

add_h2(doc, '7.2  Call Flow')
add_code_block(doc, """\
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
   │── customer-rating ───────►│                          │""")

add_h2(doc, '7.3  Call Control Events')
add_table(doc,
    ['Event', 'Sender', 'Recipients', 'Description'],
    [
        ['`agent-hold`',        'Agent',    'Customer', 'Places call on hold'],
        ['`agent-mute`',        'Agent',    'Customer', 'Notifies customer of agent mute state'],
        ['`customer-mute`',     'Customer', 'Agent',    'Notifies agent of customer mute state'],
        ['`screen-share-start`','Either',   'Other party','Screen share has begun'],
        ['`screen-share-stop`', 'Either',   'Other party','Screen share ended'],
    ]
)

add_h2(doc, '7.4  Transfer & Escalation Events')
add_table(doc,
    ['Event', 'Description'],
    [
        ['`agent-transfer`',             'Agent requests handoff to another agent; customer rejoins queue at front'],
        ['`agent-escalate`',             'Agent escalates live call to supervisor queue'],
        ['`supervisor-accept-escalation`','Supervisor joins the call; original agent may drop'],
    ]
)

add_h2(doc, '7.5  Chat Events')
add_table(doc,
    ['Event', 'Direction', 'Description'],
    [
        ['`customer-chat-request`','Customer → Server',      'Initiate a chat'],
        ['`chat-accept`',          'Server → Agent',         'Agent assigned to chat'],
        ['`chat-message`',         'Either → Server → Other','Individual message (text or file)'],
        ['`chat-file`',            'Either → Server → Other','Binary file transfer metadata'],
        ['`chat-end`',             'Either',                 'Close chat session'],
    ]
)

# ═══════════════════════════════════════════════════════════════════════════
#  8. WEBRTC ARCHITECTURE
# ═══════════════════════════════════════════════════════════════════════════
add_h1(doc, '8. WebRTC Architecture')
add_body(doc, (
    'WebRTC establishes a peer-to-peer media channel directly between the customer\'s and agent\'s '
    'browsers. The Node.js server acts only as a **signalling relay** — it never handles media.'
))

add_h2(doc, '8.1  Signalling Flow')
add_code_block(doc, """\
1. Agent accepts call  → server emits `call-accepted` to both parties.
2. Agent creates RTCPeerConnection and generates an SDP offer.
3. Agent emits `webrtc-offer` with SDP → server relays to customer.
4. Customer sets remote description, generates SDP answer.
5. Customer emits `webrtc-answer` → server relays to agent.
6. Both sides exchange ICE candidates via `webrtc-ice` events.
7. ICE completes → DTLS handshake → media flows peer-to-peer.""")

add_h2(doc, '8.2  ICE Configuration')
add_body(doc, (
    'The current implementation uses the browser\'s default STUN servers '
    '(`stun:stun.l.google.com:19302`). For environments where NAT traversal fails '
    '(symmetric NAT, corporate firewalls), a TURN relay server would need to be provisioned.'
))

add_h2(doc, '8.3  Media Tracks')
add_table(doc,
    ['Track', 'Codec (browser default)', 'Notes'],
    [
        ['Audio',        'Opus',        'Stereo, 48 kHz'],
        ['Screen video', 'VP8 / H.264', 'Only when screen share is active'],
    ]
)

# ═══════════════════════════════════════════════════════════════════════════
#  9. SECURITY DESIGN
# ═══════════════════════════════════════════════════════════════════════════
add_h1(doc, '9. Security Design')

add_h2(doc, '9.1  Authentication & Authorisation')
for item in [
    'Passwords are hashed with **bcrypt** (salt rounds = 10).',
    'Login returns a **JWT** signed with `JWT_SECRET`; default expiry is 24 hours.',
    'Every protected REST endpoint and the `agent-join` Socket.IO event verify the JWT before processing.',
    'Role-based access: supervisor-only routes (`/api/supervisor/*`) reject tokens with `role = agent`.',
]:
    add_bullet(doc, item)

add_h2(doc, '9.2  Input Validation')
for item in [
    'File uploads are restricted to known MIME types (PDF, DOCX, TXT).',
    'All SQL queries use parameterised statements — no string interpolation.',
    'Chat messages and call notes are stored as plain text with no HTML execution surface (rendered via `textContent` in the SPA, not `innerHTML`).',
]:
    add_bullet(doc, item)

add_h2(doc, '9.3  Transport Security')
for item in [
    'All traffic travels over HTTPS/WSS in production (enforced by Render\'s TLS termination).',
    'WebRTC media is encrypted with **DTLS-SRTP** by the browser, regardless of signalling channel security.',
]:
    add_bullet(doc, item)

add_h2(doc, '9.4  Known Limitations (v1.0)')
add_table(doc,
    ['Limitation', 'Risk', 'Recommended Mitigation'],
    [
        ['In-memory session state',            'Lost on process restart; agents are disconnected', 'Persist active-session state to Turso or introduce Redis'],
        ['No rate limiting on /api/nikki/chat','Groq API quota exhaustion from public endpoint',   'Add express-rate-limit middleware'],
        ['Default supervisor credentials',     'Credential exposure if .env is misconfigured',     'Require password reset on first login; remove hardcoded fallback'],
        ['No TURN server configured',          'Calls may fail behind restrictive NAT',            'Provision a TURN server (e.g. Coturn) and pass ICE config via API'],
    ]
)

# ═══════════════════════════════════════════════════════════════════════════
#  10. DEPLOYMENT ARCHITECTURE
# ═══════════════════════════════════════════════════════════════════════════
add_h1(doc, '10. Deployment Architecture')

add_h2(doc, '10.1  Production Topology')
add_code_block(doc, """\
Internet
    │  HTTPS / WSS
    ▼
Render Web Service  (Node.js, 1 instance, free tier)
    │
    ├──► Turso database  (libsql over HTTPS, AWS ap-south-1)
    └──► Groq API        (HTTPS, LLM inference)""")
add_body(doc, 'All three tiers are managed SaaS — there are no VMs, containers, or databases to operate.')

add_h2(doc, '10.2  Environment Variables')
add_table(doc,
    ['Variable', 'Required', 'Description'],
    [
        ['TURSO_URL',      'Yes',       'libsql connection URL, e.g. libsql://db.turso.io'],
        ['TURSO_TOKEN',    'Yes',       'Turso authentication token'],
        ['JWT_SECRET',     'Yes',       'Long random string for JWT signing'],
        ['PORT',           'No',        'Server port (defaults to 3000)'],
        ['GROQ_API_KEY',   'Yes (Nikki)','Groq API key'],
    ]
)

add_h2(doc, '10.3  Render Configuration (render.yaml)')
add_code_block(doc, """\
services:
  - type: web
    name: cxeller8
    runtime: node
    buildCommand: npm install
    startCommand: node server.js
    plan: free
    envVars:
      - key: NODE_ENV
        value: production""")

add_h2(doc, '10.4  Database Initialisation')
add_body(doc, (
    'On every server start, `db.js` executes `CREATE TABLE IF NOT EXISTS` for all tables. '
    'Migrations are additive — new columns require manual `ALTER TABLE` or a dedicated migration script.'
))

# ═══════════════════════════════════════════════════════════════════════════
#  11. PERFORMANCE & SCALABILITY
# ═══════════════════════════════════════════════════════════════════════════
add_h1(doc, '11. Performance & Scalability Considerations')

add_h2(doc, '11.1  Current Bottlenecks')
add_table(doc,
    ['Bottleneck', 'Impact', 'Notes'],
    [
        ['Single Node.js process',        'All Socket.IO events serialised',         'Acceptable up to ~500 concurrent connections on a modest VM'],
        ['In-memory call state',          'Not shared across instances',              'Prevents horizontal scaling without sticky sessions + external state store'],
        ['TF-IDF retrieval scans all chunks', 'Latency grows linearly with KB size', 'Acceptable for small KBs (<1,000 chunks); index needed beyond that'],
        ['Turso free tier limits',        '1 GB storage, 8 GB transfer/month',        'Upgrade tier when storage exceeds 800 MB'],
    ]
)

add_h2(doc, '11.2  Scaling Path')
add_body(doc, 'For growth beyond free-tier limits:')
for item in [
    '**Add Redis** for session state (`connectedAgents`, `callQueue`, `activeCalls`) to allow multiple Node.js instances behind a load balancer.',
    '**Sticky sessions** on the load balancer for Socket.IO (or migrate to Socket.IO Redis adapter).',
    '**Replace TF-IDF with semantic embeddings** (e.g. `@xenova/transformers` in-process, or an external embedding API) for KB sizes above ~5,000 chunks.',
    '**Turso scaler plan** for higher storage/transfer or point-in-time recovery.',
]:
    add_bullet(doc, item)

# ═══════════════════════════════════════════════════════════════════════════
#  12. RISKS & MITIGATIONS
# ═══════════════════════════════════════════════════════════════════════════
add_h1(doc, '12. Risks & Mitigations')
add_table(doc,
    ['#', 'Risk', 'Probability', 'Impact', 'Mitigation'],
    [
        ['R1', 'Render free-tier process sleeps after 15 min inactivity, dropping all WebSockets', 'High',   'High',   'Upgrade to paid Render plan, or implement a self-ping keep-alive'],
        ['R2', 'Groq API unavailable / rate-limited',                                              'Medium', 'Medium', 'Graceful fallback message to customer; health endpoint exposed for monitoring'],
        ['R3', 'WebRTC call failure behind symmetric NAT',                                         'Medium', 'High',   'Provision TURN server; surface ICE failure diagnostics to agent'],
        ['R4', 'Customer data loss if server restarts mid-call',                                   'Low',    'Medium', 'Persist active call start time to DB immediately on accept; reconcile orphaned rows on startup'],
        ['R5', 'JWT secret rotation requires all agents to re-login',                              'Low',    'Low',    'Document the procedure; short-lived tokens reduce blast radius'],
        ['R6', 'KB documents contain sensitive data accessible via Nikki',                         'Low',    'High',   'Restrict KB upload/delete to supervisors only; audit document content before upload'],
    ]
)

# ═══════════════════════════════════════════════════════════════════════════
#  13. FUTURE ROADMAP
# ═══════════════════════════════════════════════════════════════════════════
add_h1(doc, '13. Future Roadmap')

add_h2(doc, 'Phase 2 — Reliability & Operations')
for item in [
    'TURN server integration for reliable WebRTC behind restrictive NAT.',
    'Rate limiting on all public endpoints.',
    'Structured logging (Winston / Pino) with log forwarding to an observability platform.',
    'Health check dashboard integrated with uptime monitoring (e.g. Betterstack).',
    'Graceful shutdown: drain active calls before process exit.',
]:
    add_bullet(doc, item)

add_h2(doc, 'Phase 3 — Feature Expansion')
for item in [
    '**Call recording storage** — upload recorded blobs to S3/R2 and store signed URLs.',
    '**Customer accounts** — allow returning customers to view their own history.',
    '**Canned responses** — agent shortcut library for common replies.',
    '**SLA alerting** — notify supervisors when queue wait time exceeds threshold.',
    '**Semantic KB search** — replace TF-IDF with vector embeddings for higher recall.',
]:
    add_bullet(doc, item)

add_h2(doc, 'Phase 4 — Scale & Multi-tenancy')
for item in [
    'Redis-backed Socket.IO adapter for multi-instance deployments.',
    'Tenant isolation at the database level (organisation ID on all tables).',
    'SSO / OAuth2 login for enterprise agents.',
    'Webhook delivery for call events to external CRM systems.',
]:
    add_bullet(doc, item)

# ── Final spacing paragraph ───────────────────────────────────────────────
doc.add_paragraph()
end = doc.add_paragraph()
end.alignment = WD_ALIGN_PARAGRAPH.CENTER
er = end.add_run('— End of Document —')
er.font.italic = True
er.font.size   = Pt(9)
er.font.color.rgb = RGBColor(0x99, 0x99, 0x99)

# ── Save ──────────────────────────────────────────────────────────────────
output_path = '/home/user/cxeller8/SOLUTION_DESIGN.docx'
doc.save(output_path)
print(f'Saved: {output_path}')
