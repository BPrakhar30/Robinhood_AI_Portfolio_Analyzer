1. Frontend architecture
Recommended stack
•	Framework: Next.js 15+ with React + TypeScript 
•	Styling: Tailwind CSS 
•	Component primitives: shadcn/ui or Radix-based design system 
•	State management: Zustand for local app state, React Query/TanStack Query for server state 
•	Forms: React Hook Form + Zod 
•	Tables: TanStack Table 
•	Charts: Recharts 
•	HTTP client: fetch wrapper or Axios with interceptors 
•	Auth storage: httpOnly cookie preferred; if JWT must be stored client-side, use secure memory-first strategy and minimize localStorage usage 
•	Logging/monitoring: Sentry frontend SDK + structured console logging in development 
•	Testing: Vitest/Jest + React Testing Library + Playwright 
Suggested folder structure
src/
  app/
    (public)/
      login/
      register/
    (protected)/
      dashboard/
      brokers/
      positions/
      transactions/
      summary/
      settings/
    layout.tsx
    page.tsx
  components/
    ui/
    layout/
    auth/
    brokers/
    portfolio/
    feedback/
  features/
    auth/
      api.ts
      hooks.ts
      schemas.ts
      store.ts
      components/
    brokers/
      api.ts
      hooks.ts
      schemas.ts
      components/
    portfolio/
      api.ts
      hooks.ts
      components/
    system/
      api.ts
      hooks.ts
  lib/
    api/
      client.ts
      interceptors.ts
      types.ts
    utils/
    constants/
    logger/
    auth/
  providers/
  styles/
  tests/
This matches the modular architecture principle from your developer guidelines: single responsibility, clean boundaries, and testability.
2. UI implementation principles
Core product principles for the UI
The PRD describes a product that should feel like a portfolio copilot, not just a CRUD admin app. So the frontend should aim for:
•	clean, finance-grade layout 
•	highly legible numbers and tables 
•	prominent portfolio actions 
•	trust-building microcopy 
•	transparent errors and fallbacks 
•	explainable states 
The UI should feel:
•	simple like a modern SaaS product 
•	reliable like a fintech dashboard 
•	extensible enough for future AI workflows 
Design language
Use:
•	spacious layouts 
•	soft cards 
•	minimal but strong hierarchy 
•	concise labels 
•	human-readable finance formatting 
•	accessible colors 
•	clear danger/warning/success states 
Avoid:
•	flashy trading-app visuals 
•	excessive gradients and animation 
•	cluttered dashboards before enough data exists 
________________________________________
3. Page-by-page implementation plan
A. Public pages
1. Landing page
Purpose:
•	explain what the app does 
•	give users confidence 
•	drive sign-up or login 
Sections:
•	Hero: “Your AI Portfolio Copilot” 
•	value props: connect broker, understand holdings, ask questions, detect concentration 
•	trust section: encrypted connections, secure token handling, fallback import options 
•	CTA: Create account / Log in 
This directly reflects the core product vision in the PRD: secure connection, portfolio understanding, conversational analytics, and decision support. 
2. Register page
Fields:
•	name 
•	email 
•	password 
•	confirm password 
Requirements:
•	inline validation 
•	password strength hint 
•	loading state on submit 
•	friendly duplicate-email errors 
•	post-success redirect to onboarding/dashboard 
3. Login page
Fields:
•	email 
•	password 
Requirements:
•	remember session behavior 
•	invalid credentials state 
•	loading indicator 
•	redirect to intended protected route after login 
________________________________________
B. Protected pages
4. Dashboard page
Since backend is only up to connection/account layer, the dashboard should be a control center, not a full analytics dashboard yet.
Sections:
•	welcome header 
•	connection status cards 
•	summary card from /api/v1/broker/summary 
•	quick actions: 
o	connect Robinhood 
o	connect Plaid 
o	import CSV 
o	sync portfolio 
•	positions preview 
•	transactions preview 
•	system status widget from /health and /status 
Empty-state behavior:
•	if no broker connected, show onboarding card with 3 primary actions 
5. Broker connections page
Purpose:
•	show all linked sources and their health 
Include:
•	list of connections 
•	broker type 
•	connection status 
•	last sync time 
•	actions: 
o	sync 
o	disconnect 
o	view imported positions 
•	fallback note: “Robinhood unavailable? Use Plaid or CSV import.” 
This aligns with the fallback hierarchy described in your implementation and the guidelines’ requirement for resilient fallbacks. 
6. Connect broker flow
This should be implemented as a guided multi-step flow.
Robinhood connect
Step UI:
•	connect explanation 
•	compliance/security note 
•	credential or OAuth flow UI depending on backend implementation 
•	loading state 
•	success/failure screen 
•	fallback CTA: try Plaid or CSV 
Plaid connect
Step UI:
•	Plaid introduction 
•	“Generate Link Token” 
•	Plaid Link modal 
•	token exchange success 
•	post-connect sync action 
CSV import
Step UI:
•	download template 
•	upload file 
•	validate columns 
•	show preview 
•	import summary 
•	imported holdings count 
•	error row reporting 
Important UX rule:
CSV import must have excellent failure messaging, because fallback import is only useful if users can recover from formatting mistakes quickly.
7. Positions page
Table columns:
•	symbol 
•	name if available 
•	quantity 
•	average cost 
•	current value if available later 
•	unrealized gain/loss if available 
•	broker source 
•	last updated 
Features:
•	sorting 
•	filtering 
•	search by ticker 
•	empty state 
•	skeleton loading 
•	sticky header 
8. Transactions page
Table columns:
•	date 
•	type 
•	symbol 
•	quantity 
•	price 
•	total amount 
•	broker 
Features:
•	date filter 
•	transaction type filter 
•	pagination 
•	export later 
9. Summary page
This is the “aggregated account summary” page from your current API.
Cards:
•	total positions 
•	total brokers connected 
•	cash balance if available 
•	transaction count 
•	last sync 
•	import source mix 
This page should later evolve into the portfolio health page once analytics backend is ready.
10. Settings/account page
Include:
•	profile info 
•	logout 
•	session/device section later 
•	API/environment diagnostics for developers in non-production 
•	delete/disconnect workflows later 
________________________________________
4. Layout and navigation
App shell
Use a stable authenticated shell:
•	left sidebar on desktop 
•	top nav on mobile/tablet 
•	global user menu 
•	quick system health indicator 
•	sync button in header 
•	notification area for warnings/errors 
Sidebar items:
•	Dashboard 
•	Brokers 
•	Positions 
•	Transactions 
•	Summary 
•	Settings 
Later roadmap items can already be stubbed but disabled:
•	AI Assistant 
•	Health Score 
•	Alerts 
•	Scenarios 
That creates continuity with the PRD roadmap without misleading users that the functionality exists today. 
________________________________________
5. API integration rules for the frontend
Your backend already standardizes responses with:
•	status 
•	data 
•	error_message 
•	timestamp 
The frontend should build around that contract and never assume raw payloads. This matches the backend/API guideline document. 
API client rules
Create a shared API wrapper that:
•	injects auth token/cookie 
•	normalizes errors 
•	logs request failures 
•	retries only safe GET requests 
•	handles 401 globally 
•	supports request cancellation 
•	maps backend errors to user-friendly messages 
React Query rules
Use React Query for:
•	/me 
•	connections list 
•	positions 
•	transactions 
•	summary 
•	health/status 
Mutations for:
•	register 
•	login 
•	connect Robinhood 
•	create Plaid link token 
•	exchange Plaid token 
•	import CSV 
•	sync connection 
•	disconnect connection 
Cache strategy
•	cache summary and positions briefly 
•	invalidate positions/summary after sync 
•	optimistic updates only where safe 
•	do not optimistic-update financial values unless deterministic 
________________________________________
6. Authentication UX rules
Your current backend supports register, login, and GET /me, so the frontend auth system should be solid from day one.
Requirements
•	protected route middleware 
•	session bootstrap from /me 
•	auto-redirect unauthenticated users to login 
•	preserve return URL 
•	logout clears all cached protected data 
•	loading gate while auth status is being determined 
Security note
Prefer:
•	backend-set httpOnly secure cookies 
If current backend returns JWT in JSON and you must handle it client-side:
•	keep token handling in a dedicated auth module 
•	avoid scattering token logic 
•	minimize persistent storage 
•	never log tokens 
•	strip auth headers from error telemetry 
________________________________________
7. Error, loading, and empty-state design
This matters a lot in a fintech app.
Every page must have
•	skeleton state 
•	error state 
•	empty state 
•	partial data state 
Examples
No connections
“Connect your first account to start importing positions and transaction history.”
Sync failed
“We couldn’t refresh this account right now. Your last synced snapshot is still available.”
Robinhood connection issue
“Robinhood connection failed. You can retry, connect via Plaid, or import a CSV template instead.”
This matches the fallback-first design philosophy in the developer guidelines. 
________________________________________
8. Frontend observability and logging
The guidelines explicitly require structured logging, observability, and reliable monitoring. The frontend should reflect that too.
Include
•	Sentry for frontend errors 
•	route-level performance monitoring 
•	correlation IDs from backend if available 
•	structured logging helper in dev mode 
•	user-safe telemetry only 
Never log
•	passwords 
•	tokens 
•	Plaid public token exchange details 
•	personal financial payloads in full 
________________________________________
9. Accessibility and UX quality bar
Production-grade means accessible.
Requirements
•	keyboard navigable 
•	proper label/input association 
•	accessible tables 
•	screen-reader friendly alerts 
•	sufficient color contrast 
•	visible focus states 
•	no critical interaction hidden behind hover only 
Finance UI especially needs:
•	aligned numeric columns 
•	monospace or tabular figures for values 
•	explicit negative/positive states 
•	consistent percentage/value formatting 
________________________________________
10. Component design system
Create reusable components early.
Core UI components
•	AppShell 
•	SidebarNav 
•	Topbar 
•	PageHeader 
•	StatCard 
•	EmptyStateCard 
•	ErrorStateCard 
•	LoadingSkeleton 
•	DataTable 
•	BrokerConnectionCard 
•	SyncStatusBadge 
•	ImportDropzone 
•	ConfirmDialog 
•	SecureInfoNotice 
Form components
•	TextInput 
•	PasswordInput 
•	Select 
•	FileUploadInput 
•	SubmitButton 
•	InlineError 
•	HelperText 
Finance display components
•	CurrencyText 
•	PercentageText 
•	GainLossBadge 
•	BrokerBadge 
•	TimestampText 
This avoids duplicated formatting logic and supports the modularity requirement from the engineering document. 
________________________________________
11. Implementation instructions for later AI-ready UI
Even though AI features are not yet built in the backend, your frontend should be designed so they slot in later without refactoring the app shell.
The PRD makes AI chat, health score, allocation analysis, overlap analysis, and scenario simulation major features. 
So reserve future placeholders for:
•	AI assistant panel 
•	portfolio health card 
•	alerts panel 
•	benchmark comparison 
•	scenario simulator drawer 
•	stock detail drawer 
Do this by:
•	designing dashboard zones now 
•	using generic panel/card containers 
•	organizing features/ai, features/analytics, features/alerts folders even if initially empty 
________________________________________
12. Recommended delivery phases
Phase 1 — foundation
•	Next.js app setup 
•	auth pages 
•	protected routing 
•	layout shell 
•	API client 
•	React Query providers 
•	error boundary 
•	design system foundations 
Phase 2 — account connection layer
•	broker connections page 
•	Robinhood connect flow 
•	Plaid connect flow 
•	CSV import flow 
•	sync/disconnect actions 
•	summary page 
•	health/status widgets 
Phase 3 — portfolio visibility layer
•	positions page 
•	transactions page 
•	filters/sorting/search 
•	improved summary cards 
•	last-sync and stale-data indicators 
Phase 4 — future analytics layer
•	health score UI 
•	allocation cards 
•	AI chat surface 
•	scenario simulator 
•	alerts center 
________________________________________
13. Frontend coding standards for developers
Use these as direct implementation instructions.
Code quality
•	TypeScript strict mode enabled 
•	no any unless documented 
•	feature-based modules 
•	avoid giant page files 
•	keep business logic out of components 
•	hooks for orchestration, components for rendering 
Component rules
•	presentation components stay dumb where possible 
•	container/hooks own data fetching 
•	reusable display primitives for money, percentage, dates, and statuses 
•	all async actions must surface loading and error state 
Comments and docs
•	meaningful comments only where logic is non-obvious 
•	docstrings for shared utilities/hooks 
•	story or usage examples for complex components 
Testing
•	unit tests for helpers and formatters 
•	component tests for forms, tables, state transitions 
•	e2e flows for register, login, connect broker, upload CSV, sync, disconnect 
This is in the same spirit as the mandatory testing and documentation standards in the engineering guidelines. 
________________________________________

