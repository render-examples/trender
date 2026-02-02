# Dashboard

Next.js 14 dashboard for visualizing GitHub trending analytics with real-time data from PostgreSQL.

## Overview

Server-side rendered (SSR) dashboard that displays:
- Top trending repositories across Python, TypeScript, Go
- Render ecosystem projects spotlight
- Momentum scores and analytics
- Historical trends and rankings
- Workflow execution traces

## Architecture

```
app/                    # Next.js App Router
├── page.tsx            # Home page (server component)
├── layout.tsx          # Root layout
├── globals.css         # Global styles + animations
└── api/
    └── workflow-status/
        └── route.ts    # API endpoint for workflow traces

components/             # React components
├── HomeClient.tsx      # Client wrapper with state management
├── RepoCard.tsx        # Repository card with metadata
├── ScrollableRow.tsx   # Horizontal scrolling container
├── TaskTimeline.tsx    # Workflow execution timeline
├── TaskTree.tsx        # Hierarchical task visualization
├── WorkflowPanel.tsx   # Workflow trace viewer
├── ReadmePanel.tsx     # Markdown README viewer
├── Header.tsx          # Site header
├── TypingTagline.tsx   # Animated typing effect
└── LoadingSkeleton.tsx # Loading states

lib/                    # Utilities
├── db.ts               # PostgreSQL connection & queries
├── formatters.ts       # Data formatting helpers
├── content.ts          # Copy text content
└── markdown.ts         # Markdown rendering (marked.js)
```

## Key features

### 1. Server-side rendering
- Data fetched on server via PostgreSQL queries
- Fast initial page load with pre-rendered content
- Automatic revalidation on navigation

### 2. Repository cards
- Language-specific icons (Python, TypeScript, Go, Render)
- Star counts with formatting (1.2k, 3.4M)
- Momentum scores with visual indicators
- README previews with markdown rendering

### 3. Workflow visualization
- Real-time workflow status polling
- Interactive task tree with expand/collapse
- Execution timeline with color-coded states
- Duration calculations and status badges

### 4. Responsive design
- Horizontal scrolling for repo lists
- Mobile-optimized layouts
- Smooth animations (Framer Motion)
- Loading skeletons for better UX

## Data sources

### PostgreSQL views

The dashboard queries these analytics views:

| View | Purpose |
|------|---------|
| `analytics_trending_repos_current` | Top repos across all languages |
| `analytics_render_showcase` | Render ecosystem projects |
| `analytics_language_rankings` | Per-language leaderboards |
| `analytics_language_trends` | Aggregate statistics |
| `fact_workflow_runs` | Workflow execution traces |

### Example query (lib/db.ts)

```typescript
const repos = await pool.query(`
  SELECT 
    repo_full_name,
    language,
    stars,
    momentum_score,
    description,
    readme_content
  FROM analytics_trending_repos_current
  ORDER BY momentum_score DESC
  LIMIT 25
`);
```

## Components

### HomeClient.tsx
**Client component** - Manages UI state and interactions.

**Features:**
- Repository filtering by language
- README panel toggle
- Workflow trace panel toggle
- Local state management

### RepoCard.tsx
**Display component** - Shows repository metadata.

**Props:**
```typescript
{
  repo: Repository;
  onClick?: () => void;
  rank?: number;
  showLanguage?: boolean;
}
```

**Displays:**
- Language icon
- Repo name (owner/name split)
- Description (truncated)
- Stars + momentum score
- Creation date

### WorkflowPanel.tsx
**Interactive component** - Visualizes workflow execution.

**Features:**
- Fetches latest workflow run from `/api/workflow-status`
- Polls every 3 seconds if workflow is running
- Displays task tree with expand/collapse
- Shows execution timeline

**States:**
- Loading: Fetching workflow data
- Running: Active execution with live updates
- Completed: Final results with duration
- Failed: Error message and trace

### ReadmePanel.tsx
**Modal component** - Renders markdown README content.

**Features:**
- Markdown rendering via marked.js
- Syntax highlighting (if configured)
- Sanitized HTML output (DOMPurify)
- Smooth slide-in animation
- Click outside to close

### TaskTimeline.tsx
**Visualization component** - Horizontal timeline of task execution.

**Props:**
```typescript
{
  tasks: Task[];
  startTime: Date;
  endTime: Date;
}
```

**Features:**
- Color-coded status bars (green=completed, yellow=running, red=failed)
- Duration labels
- Proportional widths based on execution time

### TaskTree.tsx
**Hierarchical component** - Recursive task tree visualization.

**Props:**
```typescript
{
  task: TaskNode;
  level?: number;
}
```

**Features:**
- Expand/collapse nested tasks
- Status badges with colors
- Indentation for hierarchy
- Duration display

## Styling

### Tailwind CSS
- Utility-first styling
- Responsive breakpoints
- Custom color palette (purple accents)

### Custom animations (globals.css)
```css
@keyframes fade-in-up
@keyframes pulse-slow
@keyframes shimmer
@keyframes gradient-shift
```

**Usage examples:**
- `animate-fade-in-up`: Card entrance animations
- `animate-pulse-slow`: Loading states
- `animate-shimmer`: Skeleton loaders
- `animate-gradient-shift`: Background effects

## Environment variables

```bash
# Required
DATABASE_URL=postgresql://...

# Optional
NEXT_PUBLIC_API_URL=https://trender-dashboard.onrender.com
NODE_ENV=production
```

## Running locally

```bash
cd dashboard
npm install
npm run dev
# Visit http://localhost:3000
```

**Hot reload**: Changes auto-refresh in browser

## Building for production

```bash
npm run build
npm start
```

**Optimizations:**
- Static page generation where possible
- Image optimization
- CSS minification
- JavaScript tree-shaking

## API routes

### GET /api/workflow-status

**Returns:**
```json
{
  "run_id": "wfr_abc123",
  "status": "completed",
  "started_at": "2026-02-02T12:00:00Z",
  "completed_at": "2026-02-02T12:00:15Z",
  "task_tree": { ... },
  "repos_processed": 150,
  "execution_time_seconds": 15.2
}
```

**Error handling:**
- Returns latest run, or empty object if none found
- Logs database errors to console
- Never crashes (graceful degradation)

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Cannot connect to database" | Check `DATABASE_URL` in `.env` |
| No data displayed | Ensure workflow has run at least once |
| Styles not loading | Run `npm install` to install Tailwind |
| API errors in console | Verify PostgreSQL views exist |
| Slow page loads | Check database query performance |

## Performance optimization

1. **Server components**: Use by default for data fetching
2. **Client components**: Only for interactivity (marked with 'use client')
3. **Image optimization**: Use Next.js `<Image>` component
4. **Code splitting**: Automatic via Next.js App Router
5. **Database indexes**: Ensure indexes on frequently queried columns

## Dependencies

See `package.json`:

**Core:**
- `next`: Framework
- `react`, `react-dom`: UI library
- `pg`: PostgreSQL client
- `typescript`: Type safety

**UI/styling:**
- `tailwindcss`: Utility CSS
- `framer-motion`: Animations
- `recharts`: Charts (if used)

**Markdown:**
- `marked`: Markdown parser
- `dompurify`: HTML sanitization

## Contributing

1. Create feature branch
2. Test locally: `npm run dev`
3. Build check: `npm run build`
4. Deploy: Push to GitHub (auto-deploy)
5. Monitor: Check dashboard.onrender.com

