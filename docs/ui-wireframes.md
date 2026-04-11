# UI map and flows

High-level map of the **Next.js** app: primary routes match [`frontend/src/components/layout/app-nav.ts`](../frontend/src/components/layout/app-nav.ts). Layout intent only (not pixel-perfect). To run the stack locally, see [README.md](../README.md).

## Routes (sidebar)

| Label (UI) | Path |
|------------|------|
| Chat | `/` |
| Resumes | `/resumes` |
| Jobs | `/job-descriptions` |
| Templates | `/templates` |
| PDF exports | `/outputs` |

## Critical flows

1. **Chat**: Open or create a session from the sidebar → optional **Resume**, **Job**, **Template** picks in the context panel → type message → **Send** → assistant streams over **SSE**; PDF preview updates when an artifact exists.
2. **Resumes**: **Upload** a file → row appears in the list → open/download; parsing runs in the background until `parsed_json` is ready.
3. **Jobs**: **Paste** (or add) a job description → save to the shared library → in **Chat**, pick that job or **Activate** from a session-scoped flow so the session uses it.
4. **Templates**: Browse library → **New** or select a row → edit LaTeX → **Save**; **Preview** compiles via the backend.
5. **PDF exports**: Choose **session** (optional), **resume**, **template** → **Generate** → wait for status → **Download** when the worker has produced the PDF.

## Chat — shell

The chat experience uses a full-height shell ([`AppShell`](../frontend/src/components/chat/app-shell.tsx)): **sidebar** (sessions) + **main** (thread + composer) + **context** strip/panel for resources; mobile uses a bottom nav for primary routes.

```text
┌──────────────┬──────────────────────────────────────────┐
│ Sidebar      │  Main column                             │
│ (sessions)   │  [Context: Resume | Jobs | Template]      │
│              ├──────────────────────────────────────────┤
│ [New chat]   │  PDF preview (when artifact) + thread    │
│ [Search…]    │  [Load older] … messages …               │
│  rows…       ├──────────────────────────────────────────┤
│ [Load more]  │  Composer + Send                         │
└──────────────┴──────────────────────────────────────────┘
```

## Chat — session list (sidebar)

```text
┌─────────────────────────────┐
│ [New chat]                   │
│ [Search sessions…]           │
├─────────────────────────────┤
│  session row (title / time)   │
│  … virtualized …             │
│ [Load more]                  │
└─────────────────────────────┘
```

## Chat — context panel (Resume / Jobs / Template)

```text
┌ Section title ─────── [action] ┐
│ Short hint text                 │
├─────────────────────────────────┤
│ [Searchable combobox ▼]         │
│ Recent items as compact rows    │
└─────────────────────────────────┘
```

## Chat — message thread + composer

```text
┌────────────────────────────────┐
│ [Load older messages]           │
│  user / assistant bubbles       │
├────────────────────────────────┤
│  Composer + Send                 │
└────────────────────────────────┘
```

## Resumes (`/resumes`)

```text
┌ Resumes ───────────────────── [Upload] ┐
│ [Search]   sort / pagination hints      │
├──────────────────────────────────────────┤
│  virtualized list of resume cards/rows   │
├──────────────────────────────────────────┤
│  paging controls                         │
└──────────────────────────────────────────┘
```

## Jobs (`/job-descriptions`)

```text
┌ Jobs ─────────────────────── [Paste] ┐
│ [Search]   filters / session scope      │
├──────────────────────────────────────────┤
│  virtualized job description rows        │
└──────────────────────────────────────────┘
```

## Templates (`/templates`)

```text
┌ Library ───────────────────── [New] ┐
│ [Search templates…]                 │
│  virtualized template rows          │
├─────────────────────────────────────┤
│  Editor / preview (sheet or split)   │
│  LaTeX source + Save + Preview PDF   │
└─────────────────────────────────────┘
```

## PDF exports (`/outputs`)

```text
┌ PDF exports ─────────────────────────┐
│ Session (optional) / Resume / Template│
│ [comboboxes]          [Generate]      │
│  status text + download when ready    │
└───────────────────────────────────────┘
```
