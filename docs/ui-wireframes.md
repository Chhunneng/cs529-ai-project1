# UI wireframes & critical flows (Phase 0)

Living reference for the large-data UI refactor. Layout intent only.

## Critical flows

1. **New chat** → Session tools: resume, JD, template → send message.
2. **Upload resume** → appears in library / picker.
3. **Templates** → pick in library → edit LaTeX → save.
4. **Outputs** → pick session (and optional resume) → generate PDF → download.
5. **Job postings** → paste → save → activate for session.

## Chat — sidebar “Recent chats”

```text
┌─────────────────────────────┐
│ [Search chats…]              │
├─────────────────────────────┤
│ ┌─ session row ─────────────┐ │
│ │ id + updated time         │ │
│ └──────────────────────────┘ │
│   … paginated / virtualized … │
│ [Load more]                   │
└─────────────────────────────┘
```

## Chat — context panel (Resume / JD / Template)

```text
┌ Section title ─────── [Action] ┐
│ Short description               │
├─────────────────────────────────┤
│ [Combobox: type to filter ▼]    │
│ Recent — compact rows           │
└─────────────────────────────────┘
```

## Chat — main thread

```text
┌────────────────────────────────┐
│ [Load older messages]           │
│  … bubbles …                    │
├────────────────────────────────┤
│ Composer                        │
└────────────────────────────────┘
```

## Resumes page

```text
┌ Resumes ───────────────────── [Upload] ┐
│ [Search]  [Sort: date ▼]   Showing x–y  │
├────────────────────────────────────────┤
│ virtualized rows                        │
├────────────────────────────────────────┤
│  [< Prev]  Page n  [Next >]             │
└────────────────────────────────────────┘
```

## Job postings page

```text
┌ Job postings ─────────────── [Paste] ┐
│ Session [combobox]  Filter [combobox] │
├───────────────────────────────────────┤
│ virtualized list                      │
└───────────────────────────────────────┘
```

## Templates — library column

```text
┌ Library ─────────────────── [New] ┐
│ [Search templates…]                │
│ virtualized template rows          │
└────────────────────────────────────┘
```

## Outputs

```text
┌ Generate PDF ─────────────────────┐
│ Session / Resume / Template       │
│ [comboboxes]                      │
│ [Generate]  status / download     │
└───────────────────────────────────┘
```
