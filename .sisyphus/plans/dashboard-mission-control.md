# Plan: Rebuild InkosAI Dashboard as "Mission Control"

**Scope:** The Dashboard page (`src/app/page.tsx`) only. Shared shell components (navbar, layout, globals.css) get the **minimum** changes required to support the new dashboard. Other pages (Prime, Tape, Proposals, etc.) remain untouched.

**Reference mockup:** `/tmp/aetheros-mocks/v1-mission-control.html` + screenshot `/tmp/aetheros-mocks/v1-shot.png`

**Success criterion:** When the user opens `http://localhost:3000/`, they see a dense, operator-cockpit-style dashboard matching the V1 mockup, with live data from the existing hooks (`useSystemSnapshot`, `useRecentTape`, `useProposals`, `useSimulations`) and a polished empty/disconnected state when the backend is offline.

---

## Design deltas from current dashboard

| Aspect | Current | Mission Control |
|---|---|---|
| Layout | `max-w-7xl` centered, stacked sections, ~60% empty viewport | Edge-to-edge 2-column (left rail + main), 5-zone fixed layout, dense |
| Navigation | Top nav with 10 text+icon tabs | 64px left icon rail (icon-only with tooltips) |
| Top bar | Brand + search + settings + avatar | 32px status strip with **persistent CONNECTED pill**, alert chips, breadcrumb |
| Hero | 4 stat cards (large, sparse) | 6-metric strip (compact, includes sparklines + delta indicators) |
| Primary content | Recent Tape list (8 rows) + System Health (5 key=val rows) | Dense Tape table (15+ rows, 4 columns, monospace) + Proposals queue tabs |
| Bottom content | Optional pending proposals / running sims | **Agents matrix** (horizontal scroll of 7 cards) + **Domains strip** + **Health sparklines** |
| Typography | Single sans (Geist), no mono for data | Sans (Space Grotesk) + Mono (IBM Plex Mono) — mono for all numbers, IDs, timestamps |
| Accent use | Cyan glow on cards, gradient "InkosAI" H1 | Cyan used surgically (active nav, key metrics, borders). **No gradient text.** |
| Glass effect | Heavy backdrop-filter glassmorphism | Flat surfaces, subtle borders, optional faint grid texture |

---

## File-by-file changes

### NEW FILE: `src/components/dashboard/metric-tile.tsx`
Compact metric tile for the 6-metric hero strip.
Props: `label`, `value`, `delta` (optional: `+2`, `-1`, `0`), `accent` ('text'|'cyan'|'emerald'|'amber'|'red'), `sparklineData` (array of numbers, optional).
Renders: small uppercase label (10px, text-dim), big mono number (30-32px, tabular-nums), tiny delta indicator (emerald for +, amber for -, dim for 0), inline SVG sparkline (60×16) below.
Replaces: the big `<StatCard>` — but do NOT delete `StatCard` yet; it may be used elsewhere.

### NEW FILE: `src/components/dashboard/sparkline.tsx`
Tiny SVG polyline component.
Props: `data: number[]`, `width` (default 60), `height` (default 16), `color` (default 'cyan'), `strokeWidth` (default 1.5).
Pure SVG, no external libs. Normalizes data to viewBox. Returns `null` gracefully if data is empty or has <2 points.
Unit test mentally: given `[1,2,3,4,5]` → polyline from bottom-left to top-right.

### NEW FILE: `src/components/dashboard/agent-card.tsx`
Compact 170×100 agent card used in the horizontal agents matrix.
Props: `agent: AgentDescriptor`, `currentTask?: string` (optional — derived from recent tape).
Renders:
- Row 1: 8px status dot (emerald=active, amber=idle, text-dim=offline/unknown) + agent name in mono
- Row 2: 2 capability chips (tiny, 9px, in surface-3 bg)
- Bottom: "Last seen: Xs ago" + "Running: <task>" OR "Idle: Xm" depending on status
- If offline: `opacity-60` on the whole card
- Handles `null` / missing `last_seen` (show "—")

### NEW FILE: `src/components/dashboard/tape-table.tsx`
Dense table view of recent tape entries.
Props: `entries: TapeEntry[]`, `isLoading: boolean`, `isEmpty: boolean` (derived but passed for clarity).
Renders:
- Sticky header (4 cols): TIME, TYPE, AGENT, PAYLOAD — uppercase 10px text-dim
- Body rows: mono 11px, alternating subtle row bg (every 2nd row gets `surface-2/30`)
- TIME: formatted as `HH:MM:SS.SSS` from `entry.timestamp` (use `date-fns` `format`)
- TYPE: pill with border, color by event_type family:
  - `prime.*` → cyan
  - `prime.skill_evolution*` → violet
  - `simulation.*` → cyan (but "simulation.failed"/"simulation.timeout" → red, "simulation.completed" → emerald)
  - `prime.proposal_approved` → emerald
  - `prime.proposal_rejected` → red
  - default → text-dim
- AGENT: `entry.agent_id ?? 'system'` truncated
- PAYLOAD: `JSON.stringify(entry.payload)` stripped of braces/quotes, truncated with ellipsis, max ~300px
- Row hover: `surface-2/50`
- Empty: centered "No events yet — awaiting backend connection" with subtle icon
- Loading: 8 skeleton rows

### NEW FILE: `src/components/dashboard/queue-sidebar.tsx`
The right-side tabbed sidebar showing Pending Proposals / Running Simulations.
Props: `proposals: Proposal[]`, `simulations: SimulationRun[]`, `isLoading: boolean`.
State: tab `'pending' | 'running'` via `useState`.
Renders:
- Tab strip: "Pending (N)" | "Running (N)" — active tab has surface-3 bg
- Pending tab body: cards for each pending proposal with title, risk pill, confidence bar (color by bucket: <0.5 red, <0.7 amber, ≥0.7 emerald), and inline Approve/Reject buttons that call the existing `useApproveProposal`/`useRejectProposal` hooks
- Running tab body: one card per running sim with scenario name, progress bar (cyan, animated), ETA (derived from `timeout_seconds` - elapsed)
- Empty state for each tab: centered small text + icon (distinct copy per tab)

### NEW FILE: `src/components/dashboard/status-strip.tsx`
The 32px top status strip.
Props: no props (self-contained using hooks).
Uses: `useSystemSnapshot` for connection state, `useProposals` to derive alert chips.
Renders:
- Left: `InkosAI › Dashboard` breadcrumb
- Center: rounded-full pill containing:
  - Pulsing 8px dot (emerald if connected, red if not, amber if loading)
  - Label: "CONNECTED" / "DISCONNECTED" / "CHECKING..."
  - Separator
  - Latency ms (mock for now — use `snapshot.system_info.latency_ms ?? '—'`)
  - Separator
  - Uptime (parse from `snapshot.system_info.uptime` or show "—")
  - Separator
  - Alert count chip (amber text, count derived from pending+idle+low-conf)
- Right: inline alert chips (see below) + search icon + bell icon + small AK avatar
- Alert chips derived:
  - `idle_agents` count (if >0): "N idle agents" amber
  - `pending_proposals` count (if >0): "N pending" amber
  - `low_conf_proposals` count (proposals with confidence < 0.5): "N low-conf" amber
  - Suppress if count is 0
- Bell icon: no behavior yet (placeholder). Search icon: dispatches existing `⌘K` keyboard event (same trick the navbar uses).

### NEW FILE: `src/components/dashboard/left-rail.tsx`
Dashboard-local 64px left icon rail navigation. **This is a dashboard-scoped rail, NOT a replacement for the global Navbar** (other pages keep using the current top nav for now).
Props: none. Uses: `usePathname`.
Renders:
- Top: InkosAI brain-shaped SVG logo (24px, cyan) in a 48px header cell
- Nav: 10 icon buttons, each 40×40, tooltip-on-hover via CSS `::after` (pure CSS, no Tooltip component):
  - Dashboard (LayoutDashboard), Prime (Cpu), Tape (ScrollText), Proposals (FileCheck), Simulations (FlaskConical), Explain (MessageSquare), Planning (GitBranch), Profile (User), Knowledge (BookOpen), Domains (Globe)
  - Active route: 3px cyan vertical pill on the left edge + cyan icon; inactive: text-dim icon, hover → text-muted
- Bottom: Settings icon (opens existing settings dialog via `open-settings` CustomEvent) + AK avatar circle

### NEW FILE: `src/components/dashboard/domains-strip.tsx`
Horizontal 3-pill domain strip.
Props: `domains: DomainDescriptor[]`, `skillsByDomain?: Record<string, number>` (optional, falls back to showing just agent count).
Each pill: flex-1 minimal card showing domain name (mono cyan), agent count, skill count, and a tiny sparkline (randomized mock activity if no real data).

### NEW FILE: `src/components/dashboard/health-sparklines.tsx`
Right-side card with 3 stacked tiny line charts.
Props: `tapeEntries: TapeEntry[]`.
Derives:
- Event rate: bucket entries by minute for last 10 min → 10 data points
- Approval rate: `proposal_approved / (proposal_approved + proposal_rejected)` rolling
- Sim success rate: `simulation.completed / (completed + failed + timeout)` rolling
- All 3 use the shared `<Sparkline />` component at 100×16.
- If no entries yet, show flat lines at center (data=`[0.5,0.5,0.5,0.5,0.5]`).

### MODIFIED: `src/app/page.tsx`
Complete rewrite to compose the above components into the 5-zone layout from the mockup.
Structure:
```tsx
<div className="flex h-screen w-screen overflow-hidden">
  <LeftRail />
  <main className="flex-1 flex flex-col overflow-hidden">
    <StatusStrip />
    <div className="flex-1 flex flex-col overflow-hidden">
      <HeroMetrics />       {/* 6 MetricTiles in a row, fixed 110px height */}
      <div className="flex-1 flex overflow-hidden">
        <TapeTable />       {/* flex-1 */}
        <QueueSidebar />    {/* w-[380px] */}
      </div>
      <BottomRow>           {/* fixed 180px height */}
        <AgentsMatrix />    {/* flex-1, horizontal scroll */}
        <DomainsAndHealth /> {/* w-[320px]: DomainsStrip + HealthSparklines stacked */}
      </BottomRow>
    </div>
  </main>
</div>
```
- All Framer Motion removed from this page. Motion is not part of the Mission Control aesthetic — dense operator consoles don't animate. Load states are managed by individual components' skeletons only.
- Wrap each section that needs real-time data in the existing hooks (`useSystemSnapshot`, `useRecentTape(50)`, `useProposals`, `useSimulations`).

### MODIFIED: `src/app/layout.tsx`
Small but important changes:
- Add IBM Plex Mono + Space Grotesk Google Fonts via `next/font/google` (keep Geist as fallback so existing pages don't break).
- Export `--font-plex-mono` and `--font-space-grotesk` CSS variables in addition to the current Geist ones.
- **Conditional shell rendering:** the dashboard route will render its own shell (LeftRail + StatusStrip), so we need to hide the global Navbar when on `/`. Use a `ConditionalNav` client component that reads `usePathname()` and returns `null` for `/` (else `<Navbar />`).
  - OR simpler: make Dashboard set `min-h-full bg-background` by itself and keep Navbar visible. **Decision: hide Navbar on `/` only** — the LeftRail replaces it. This matches the mockup exactly.
- Remove `page-transition` animation wrapping only for dashboard (it conflicts with the fixed-height layout). Easiest: keep the wrapper, but let Dashboard override with `h-full`.
- The `<body>` class updates from `flex flex-col` to `flex flex-col` but children need full viewport height. The dashboard page itself uses `h-screen` — make sure this doesn't break OTHER pages which currently assume a scrollable main area.

**Note:** If hiding the Navbar on `/` turns out to cause layout drift on other pages, fall back to Plan B: keep Navbar visible everywhere, but Dashboard uses `calc(100vh - 56px)` for its own shell. Try Plan A first.

### MODIFIED: `src/app/globals.css`
Additions (do NOT remove existing tokens — other pages depend on them):
```css
@theme inline {
  /* New: font variables for dashboard */
  --font-plex-mono: var(--font-ibm-plex-mono);
  --font-space-grotesk: var(--font-space-grotesk);
}

/* New: very faint grid texture for hero area */
.grid-texture {
  background-image:
    linear-gradient(rgba(34, 211, 238, 0.02) 1px, transparent 1px),
    linear-gradient(90deg, rgba(34, 211, 238, 0.02) 1px, transparent 1px);
  background-size: 24px 24px;
}

/* New: tooltip utility used by LeftRail */
.tooltip-right { position: relative; }
.tooltip-right::after {
  content: attr(data-tooltip);
  position: absolute;
  left: 100%;
  top: 50%;
  transform: translateY(-50%);
  margin-left: 8px;
  padding: 4px 8px;
  background: rgba(26, 34, 64, 0.95);
  border: 1px solid rgba(34, 211, 238, 0.18);
  color: #E8ECF4;
  font-size: 11px;
  white-space: nowrap;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.15s;
  z-index: 100;
  border-radius: 4px;
}
.tooltip-right:hover::after { opacity: 1; }

/* New: pulse dot for status indicators */
@keyframes pulse-dot-soft {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
.pulse-dot-soft { animation: pulse-dot-soft 2s ease-in-out infinite; }
```

---

## What does NOT change

- Other pages: Prime, Tape, Proposals, Simulations, Explain, Planning, Profile, Knowledge, Domains — **untouched**. Their current aesthetic stays.
- `src/components/navbar.tsx` — **untouched**. Still used by all non-dashboard pages.
- `src/components/command-palette.tsx`, `src/components/settings-dialog.tsx`, `src/components/global-shortcuts.tsx` — **untouched**.
- `src/components/stat-card.tsx` — **NOT deleted** (may be used later). It's orphaned from dashboard but stays in the codebase.
- All hooks (`src/hooks/*`), API layer (`src/lib/api.ts`), types (`src/types/index.ts`) — **untouched**.
- `package.json` — **no new dependencies**. All needed tooling (lucide-react, date-fns, tailwind) already present.

---

## Verification plan

After implementation, run in this order:

1. **TypeScript check**: `lsp_diagnostics` on each new file + `src/app/page.tsx` + `src/app/layout.tsx` + `src/app/globals.css`. Zero errors required.
2. **Build check**: `npx next build` completes without errors. (Or at minimum `next dev` starts clean — full build may hit unrelated issues.)
3. **Dev server visual verification**:
   - Start `npm run dev` (with backend OFFLINE — this is how most users will first see it)
   - Navigate to `http://localhost:3000/` (viewport 1440×900)
   - Screenshot → compare side-by-side with `/tmp/aetheros-mocks/v1-shot.png`
   - Verify: LeftRail renders with 10 icons, Dashboard icon shows cyan pill indicator, StatusStrip shows "DISCONNECTED" (not crashed), HeroMetrics shows all 6 tiles with "—" for data, TapeTable shows empty state, QueueSidebar shows tabs with "(0)" counts + empty copy, AgentsMatrix empty state, Domains/Health components gracefully empty.
4. **Navigate away and back**: click "Prime" in left rail → confirm it navigates to `/prime` AND that the old Navbar appears there (since Dashboard-only rail is hidden off-dashboard). Click "Dashboard" icon from Prime's top nav → back on Dashboard with left rail.
5. **Responsive sanity**: at 1280px viewport width, dashboard should still fit (AgentsMatrix horizontal scroll absorbs overflow). At 1024px the layout may break — acceptable for v1, mobile is out of scope.
6. **Alert chip behavior** (with mock or real data): if any alert counts are >0 they appear in the status strip; if all 0 they collapse away without leaving an empty area.

Screenshot destination: `/tmp/aetheros-screens/dashboard-v2.png` — save and compare with `/tmp/aetheros-mocks/v1-shot.png`.

---

## Risks / open questions

1. **Navbar-hiding strategy on `/` may cause layout regression on other routes.** If after implementation the Prime/Tape/etc pages shift because of `<html>` height changes, revert to Plan B: keep Navbar visible everywhere, Dashboard uses `calc(100vh - 56px)` shell. This is a 2-line change.
2. **Sparkline data is currently mocked for some metrics** (DOMAINS, SKILLS don't have historical data in the API). Using flat placeholder lines. Flagging explicitly in code comments so it's not forgotten.
3. **Agent `last_seen` is optional** in the API type. When missing, show "—" not "NaN ago".
4. **Empty states when backend is offline** are the most important visual path for this change. Every component must render cleanly with `undefined`/`[]` data — no crashes, no flickering "Loading..." forever.
5. **Keyboard navigation of LeftRail**: icons are currently `<div>`. They should be `<Link>` from next/link to be keyboard accessible. Confirmed via Radix/a11y guidance — change before ship.
6. **Accessibility**: color-only status encoding in the Tape table fails WCAG. Pair color with text (the event_type itself is the text, so this is fine). Tooltips on LeftRail: since icons are keyboard-focusable, add `aria-label` in addition to `data-tooltip`.

---

## Execution order (recommended)

Build foundation first, then compose:

1. `globals.css` additions (safe, additive only)
2. `layout.tsx` font additions + ConditionalNav component
3. `components/dashboard/sparkline.tsx` (tiny, shared)
4. `components/dashboard/metric-tile.tsx` (uses sparkline)
5. `components/dashboard/agent-card.tsx`
6. `components/dashboard/tape-table.tsx`
7. `components/dashboard/queue-sidebar.tsx`
8. `components/dashboard/status-strip.tsx`
9. `components/dashboard/left-rail.tsx`
10. `components/dashboard/domains-strip.tsx`
11. `components/dashboard/health-sparklines.tsx`
12. `app/page.tsx` rewrite composing all of the above
13. Run dev + screenshot + iterate until visually matching the mockup

Each step verifiable independently (diagnostics after each file).

---

## Out of scope (future plans)

- Other pages getting the same treatment (separate plans per page).
- Real websocket-driven live updates (the existing `use-websocket.ts` hook exists but isn't wired in anywhere visible — confirm later).
- Mobile/tablet responsive layout for Dashboard (Mission Control is desktop-first).
- Keyboard shortcuts for approving/rejecting proposals inline (nice-to-have).
- Dark/light mode toggle (app is dark-only today, keep it that way).
