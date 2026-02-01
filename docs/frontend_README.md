# Frontend - Technical Documentation

## Overview
Next.js 16.1.1 (Turbopack) frontend with React 19, providing real-time UI for Paper Brain discovery and RAG chat with metrics visualization.

## Architecture

```
frontend/
├── app/
│   ├── layout.tsx          # Root layout, metadata
│   ├── page.tsx            # Main chat interface
│   ├── globals.css         # Tailwind styles
│   ├── about/page.tsx      # About page
│   └── logs/page.tsx       # Metrics dashboard
├── components/
│   ├── AuthGuard.tsx       # Token-based access control
│   ├── Header.tsx          # Navigation bar
│   ├── ChatMain.tsx        # Chat messages display
│   ├── BrainSidebar.tsx    # Paper search & results
│   ├── MetricsSidebar.tsx  # Real-time metrics
│   ├── PaperCard.tsx       # Paper display card
│   └── ThinkingSteps.tsx   # Agent processing status
├── contexts/
│   └── SessionContext.tsx  # Global state management
├── lib/
│   └── api.ts              # Backend API client
└── types/
    └── index.ts            # TypeScript interfaces
```

## Tech Stack

- **Framework**: Next.js 16.1.1 (App Router)
- **Bundler**: Turbopack
- **React**: 19.0.0
- **TypeScript**: 5.x
- **Styling**: Tailwind CSS 3.x
- **Icons**: lucide-react
- **HTTP**: Fetch API with CORS

## Core Components

### 1. AuthGuard (components/AuthGuard.tsx)

**Purpose**: Gate all app access behind token validation

#### State Management

```typescript
const [isAuthenticated, setIsAuthenticated] = useState(false);
const [token, setToken] = useState('');
const [error, setError] = useState('');
const [isValidating, setIsValidating] = useState(true);
const [isLoading, setIsLoading] = useState(false);
```

#### Authentication Flow

1. **On Mount**:
   - Check sessionStorage for `paperstack_validated` flag
   - Check localStorage for `paperstack_token`
   - If both exist → Skip validation, show app
   - If token exists → Validate with backend (3 retries)
   - Else → Show login modal

2. **Token Validation**:
   ```typescript
   POST /auth/validate
   Body: { token: "..." }
   Response: { valid: boolean }
   ```

3. **Retry Logic**:
   - Stored tokens: 3 retries with 1s delay
   - User-entered tokens: No retries
   - Timeout: 5 seconds per attempt

4. **Success**:
   - Save to localStorage
   - Set sessionStorage flag
   - Update state to authenticated
   - Show app

5. **Browser Close Detection**:
   ```typescript
   beforeunload → sessionStorage.setItem('paperstack_validated', 'true')
   unload → localStorage.removeItem('paperstack_token')
           sessionStorage.removeItem('paperstack_validated')
   ```

#### UI States

- **Validating**: Loading spinner ("Validating access...")
- **Not Authenticated**: Modal with token input (grayscale blurred background)
- **Authenticated**: Render children (main app)

**Input Styling**: Black text on white background (text-gray-900 bg-white)

### 2. SessionContext (contexts/SessionContext.tsx)

**Purpose**: Global state for session, messages, papers, metrics

#### State

```typescript
{
  sessionId: string | null,
  messages: Message[],
  papers: Paper[],
  loadedPapers: string[],
  isLoading: boolean,
  isSearching: boolean,
  isLoadingPapers: boolean,
  quotaStatus: QuotaStatus | null,
  thinkingSteps: ThinkingStep[],
  metrics: MetricsData | null
}
```

#### Message Persistence

**Storage Key**: `paperstack_messages_${sessionId}`

**Save**:
```typescript
localStorage.setItem(key, JSON.stringify(messages))
```

**Load**:
```typescript
const stored = localStorage.getItem(key)
if (stored) setMessages(JSON.parse(stored))
```

**Timing**: Save on every message update

#### Functions

**createSession(query)**:
- Checks for token
- Calls `/session/create`
- Sets sessionId
- Loads persisted messages (if any)

**searchPapers(query)**:
- Auto-creates session if missing
- Sets isSearching=true
- Calls `/brain/search`
- Updates papers and quotaStatus
- Sets thinkingSteps

**loadPapers(paperIds)**:
- Calls `/brain/load`
- Updates loadedPapers
- Sets thinking steps

**sendMessage(message)**:
- Adds user message
- Calls `/chat/message`
- Adds AI response with citations
- Persists messages
- Refreshes metrics

**refreshMetrics()**:
- Calls `/metrics/{sessionId}`
- Updates metrics state

#### Auto-Session Creation

**Trigger**: First searchPapers() call without session
**Delay**: 100ms after mount (allows auth completion)

### 3. Header (components/Header.tsx)

**Purpose**: Navigation bar with branding and links

**Structure**:
```tsx
PaperStack Logo
  | Chat (/)
  | Logs (/logs)
  | About (/about)
```

**Styling**: Dark background, white text, hover effects

### 4. ChatMain (components/ChatMain.tsx)

**Purpose**: Display chat messages with formatting

#### Message Types

**User Message**:
```tsx
<div className="ml-auto">
  {message.content}
</div>
```

**AI Message**:
```tsx
<div className="mr-auto">
  {formatMessage(message.content)}
  {message.citations && <CitationsList />}
</div>
```

#### Message Formatting

**formatMessage(text)**:
- **Bold**: `**text**` → `<strong>text</strong>`
- **Code**: `` `code` `` → `<code>code</code>`
- **Bullet points**: 
  - Pattern: `• text` or `- text`
  - Adds indentation
- **Numbered lists**:
  - Pattern: `1. text`
  - Preserves formatting
- **Paragraphs**: Double newline → `<br /><br />`

**Code Styling**:
```css
bg-gray-100 px-1 py-0.5 rounded text-sm font-mono
```

**Citation Display**:
```tsx
[Paper Title, Page X] → Pill-style badge
```

### 5. BrainSidebar (components/BrainSidebar.tsx)

**Purpose**: Paper search interface and results

#### Search Section

**Input**: Query text
**Button**: "Search Papers"
**Loading**: Shows thinking steps during search

**Quota Display**:
```tsx
Searches remaining: X/3
```

#### Results Section

**Paper Cards**: Scrollable list
**Selection**: Checkbox per paper
**Load Button**: "Load Selected Papers (X)"

**Empty State**: "No papers found"

#### Thinking Steps Display

```tsx
{steps.map(step => (
  <div>
    <Spinner /> {step.step}: {step.result}
  </div>
))}
```

### 6. MetricsSidebar (components/MetricsSidebar.tsx)

**Purpose**: Real-time session metrics

#### Display

**Header**: "Session Metrics"

**Stats**:
- Total Requests: X
- Total Tokens: Y,YYY
- Avg LLM Latency: Xms
- Avg Total Latency: Xms

**Empty State**: "No metrics yet"

**Refresh**: Auto-refresh after each message

### 7. PaperCard (components/PaperCard.tsx)

**Purpose**: Display single paper with metadata

**Props**:
```typescript
{
  paper: Paper,
  selected: boolean,
  onSelect: (id: string) => void,
  isLoaded: boolean
}
```

**Display**:
- Checkbox (if not loaded)
- Title (bold)
- Authors (truncated)
- Score badge
- Abstract (expandable)
- arXiv link

**States**:
- Selected: Blue border
- Loaded: "Loaded" badge, no checkbox
- Default: Gray border

### 8. ThinkingSteps (components/ThinkingSteps.tsx)

**Purpose**: Show agent processing steps

**Props**:
```typescript
{
  steps: ThinkingStep[],
  isLoading: boolean
}
```

**Step Display**:
```tsx
{status === 'in_progress' && <Spinner />}
{status === 'complete' && <CheckIcon />}
{status === 'error' && <XIcon />}
{step.step}: {step.result}
```

## Pages

### Main Chat (app/page.tsx)

**Layout**: 3-column grid

```
┌─────────────┬─────────────────┬─────────────┐
│  Brain      │   Chat Main     │  Metrics    │
│  Sidebar    │                 │  Sidebar    │
│             │                 │             │
│  Search     │   Messages      │  Stats      │
│  Papers     │   Input         │             │
│  Load       │                 │             │
└─────────────┴─────────────────┴─────────────┘
```

**Responsive**: Stacks on mobile

**State**: Uses SessionContext

**Mount Behavior**:
- Does NOT auto-create session (prevents 401 errors)
- Session created on first user action

### Logs Dashboard (app/logs/page.tsx)

**Purpose**: View all session metrics

**Data Source**: `GET /metrics/{sessionId}` from context

**Display**:
- Session summary (total tokens, latencies)
- Request list (expandable)
- Per-request: query, tokens, chunks, latency

**Empty State**: "No session active"

### About (app/about/page.tsx)

**Purpose**: Project information and features

**Content**: Static markdown-style content

## API Client (lib/api.ts)

### Configuration

```typescript
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
```

### Authentication

**Token Storage**: localStorage (`paperstack_token`)

**Header Injection**:
```typescript
headers['Authorization'] = `Bearer ${token}`
```

**401 Handling**:
```typescript
if (response.status === 401) {
  localStorage.removeItem('paperstack_token')
  window.location.reload()  // Re-trigger AuthGuard
}
```

### Functions

**createSession(initialQuery)**:
```typescript
POST /session/create
Body: { initial_query: string }
Returns: { session_id, created_at }
```

**searchPapers(sessionId, query, searchMode)**:
```typescript
POST /brain/search
Body: { session_id, query, search_mode: 'topic'|'title' }
Returns: { thinking_steps, papers, searches_remaining }
```

**loadPapers(sessionId, paperIds)**:
```typescript
POST /brain/load
Body: { session_id, paper_ids: string[] }
Returns: { thinking_steps, loaded_papers, status }
```

**sendMessage(sessionId, message)**:
```typescript
POST /chat/message
Body: { session_id, message }
Returns: { thinking_steps, answer, citations, messages_remaining }
```

**getSessionInfo(sessionId)**:
```typescript
GET /session/{session_id}/info
Returns: { session_info, logs_summary }
```

**getMetrics(sessionId)**:
```typescript
GET /metrics/{session_id}
Returns: { session_id, total_requests, total_tokens, requests[] }
```

### Error Handling

**APIError Class**:
```typescript
class APIError extends Error {
  status: number
  message: string
}
```

**404 Suppression**: Logs not shown (expected during session recovery)

**Network Errors**: Caught and wrapped in Error

## Type Definitions (types/index.ts)

```typescript
interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  citations?: Citation[]
  timestamp: Date
}

interface Paper {
  title: string
  authors: string
  abstract: string
  arxiv_id: string
  url: string
  score: number
}

interface ThinkingStep {
  step: string
  status: 'in_progress' | 'complete' | 'error'
  result?: string
}

interface QuotaStatus {
  brain: { allowed: boolean, remaining: number, limit: number }
  chat: { allowed: boolean, remaining: number, limit: number }
  api_exhausted: boolean
}

interface MetricsData {
  session_id: string
  total_requests: number
  total_tokens: number
  avg_llm_latency: number
  avg_total_latency: number
  requests: MetricsRequest[]
}
```

## State Management Flow

### Session Creation
```
User enters query
  → searchPapers()
  → createSession() [auto]
  → API: POST /session/create
  → Set sessionId in context
  → Continue with search
```

### Paper Search
```
User clicks "Search Papers"
  → searchPapers(query)
  → API: POST /brain/search
  → Update papers state
  → Update thinkingSteps
  → Update quotaStatus
```

### Paper Loading
```
User selects papers + clicks "Load"
  → loadPapers(paperIds)
  → API: POST /brain/load
  → Update loadedPapers
  → Show success
```

### Chat Message
```
User sends message
  → sendMessage(message)
  → Add user message to state
  → API: POST /chat/message
  → Add AI response to state
  → Persist to localStorage
  → Refresh metrics
```

### Metrics Refresh
```
After each message
  → refreshMetrics()
  → API: GET /metrics/{sessionId}
  → Update metrics state
  → Trigger MetricsSidebar re-render
```

## Styling

### Tailwind Configuration

**Theme**: Default Tailwind with custom extensions

**Dark Mode**: Not implemented (light theme only)

**Colors**:
- Primary: Gray-900 (dark backgrounds)
- Accent: Blue-600 (links, selections)
- Error: Red-600
- Success: Green-600

### Component Patterns

**Cards**:
```css
bg-white rounded-lg shadow-md p-4
```

**Buttons**:
```css
bg-gray-900 text-white px-4 py-2 rounded-lg hover:bg-gray-800
```

**Input**:
```css
border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-gray-900
```

**Loading Spinners**:
```css
animate-spin rounded-full h-4 w-4 border-b-2 border-white
```

## Performance Optimizations

1. **Turbopack**: Fast dev builds
2. **React 19**: Concurrent features
3. **Client Components**: All interactive components
4. **LocalStorage**: Message persistence (no re-fetch)
5. **Lazy Metrics**: Only load when tab active
6. **sessionStorage**: Skip re-validation on refresh

## Environment Variables

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**Production**: Set to deployed backend URL

## Deployment

### Build
```bash
cd frontend
npm run build
```

### Start
```bash
npm start  # Production server
# or
npm run dev  # Development with Turbopack
```

### Environment
- Set `NEXT_PUBLIC_API_URL` in production
- Update CORS in backend to include frontend domain

## Browser Compatibility

- **Modern browsers**: Chrome, Firefox, Safari, Edge
- **Requirements**: ES6+, Fetch API, localStorage, sessionStorage
- **No IE support**

## Error Handling

### Network Errors
- Display error message in UI
- Retry logic in AuthGuard
- 401 → Clear token + reload

### API Errors
- 404: Suppress logs (expected)
- 429: Show cooldown message
- 500: Display error to user

### State Errors
- Missing session: Auto-create
- Missing token: Show AuthGuard
- Lost connection: Retry with stored token

## Testing

**Development**:
```bash
npm run dev
```

**Production Build**:
```bash
npm run build
npm start
```

**Access**: http://localhost:3000

**Auth Token**: "welcometopaperstack1"
