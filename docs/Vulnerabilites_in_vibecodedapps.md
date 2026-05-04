This checklist is exhaustive by design and covers every use case — from simple internal tools to fintech and healthcare apps. Not every item applies to every project. Read through all categories first, then apply items relevant to your application's risk profile, user-facing nature, data sensitivity, and compliance requirements. Items marked critical are commonly missed in AI-generated codebases and have caused real-world production failures. Items marked high are near-universally applicable. medium items are situational but important at scale.
Security – Authentication and Authorization
1. No hardcoded credentials or secrets in source code - critical
AI frequently embeds JWT secrets, API keys, DB passwords, and OAuth tokens directly in code. Every secret must live in environment variables, never in files committed to version control.
2. Authorization checks on every protected endpoint - critical
AI generates authentication (is the user logged in?) but routinely omits authorization (can this user access THIS resource?). Verify every route has both. IDOR vulnerabilities are the #1 missed check.
3. Rate limiting on all auth and sensitive endpoints - critical
AI almost never adds rate limiting by default. Login, registration, password reset, OTP, and payment endpoints must all have rate limits to prevent brute force and credential stuffing attacks.
4. Server-side access control — not client-side only - critical
A real-world startup shutdown after users toggled a single browser console value to bypass all paywalls. Business logic, permissions, and feature flags must be enforced server-side, always.
5. Session management: token entropy, expiry, revocation - high
Verify JWT/session tokens have strong entropy, proper expiry, and a revocation mechanism. Check what happens on logout — tokens should be invalidated, not just deleted from localStorage.
6. Password hashing using modern algorithms (bcrypt, Argon2) - high
AI frequently uses MD5 or SHA-1 for password hashing. Only bcrypt, Argon2, or PBKDF2 are acceptable. Check hashing cost factors are not set to trivially low values.
7. Timing-safe comparisons for secrets and tokens - high
String equality checks on tokens/passwords are vulnerable to timing attacks. Use constant-time comparison functions (e.g., crypto.timingSafeEqual in Node.js).
8. Multi-factor authentication for sensitive actions - high
AI rarely includes MFA. For apps handling payments, health data, or admin actions, MFA must be implemented and enforced, not optional.
9. Account lockout or progressive delays after failed attempts - medium
Combine with rate limiting. Lock accounts or introduce exponential backoff after repeated failed logins, with a recovery path that doesn't open new attack vectors.
10. Generic auth error messages (no username/email enumeration) - medium
Responses like "incorrect password" reveal valid usernames. All auth errors must return identical, generic messages.
Security – Injection and Input validation
11. Parameterized queries / ORM — no raw SQL string interpolation - critical
SQL injection remains the most common AI-introduced vulnerability. Grep the codebase for any query string using template literals or string concatenation with user input.
12. Input sanitization and output encoding to prevent XSS - critical
AI skips input sanitization by default. Validate and sanitize all user input on the server. Encode output properly based on context (HTML, JS, URL, CSS) to prevent reflected/stored XSS.
13. No Server-Side Request Forgery (SSRF) vectors - critical
AI-generated code that fetches user-supplied URLs is a common SSRF source. Validate and whitelist URLs, block internal IP ranges, and never proxy arbitrary user-supplied addresses.
14. File upload validation: type, size, content, and storage - high
AI file upload handlers rarely check beyond file extension. Verify MIME type from file content (magic bytes), enforce size limits, rename all uploaded files, and never serve uploaded files from a path with execute permissions.
15. Command injection prevention in shell/exec calls - high
Any use of exec(), system(), or similar functions with user-controlled input is critical. Either eliminate shell calls or strictly whitelist allowable inputs.
16. XML/JSON schema validation on all external inputs - high
Validate all incoming payloads against a strict schema. AI-generated handlers tend to process whatever arrives without validation.
17. Path traversal prevention in file system operations - medium
Check for "../" patterns in any file path derived from user input. Use path.resolve() or equivalent and verify the resolved path stays within the intended directory.
Security – Secrets and Configuration
18. Secrets management: env vars, vault, or secrets manager - critical
No secrets in .env files committed to git, no secrets in Docker images, no secrets in CI/CD logs. Use a secrets manager (AWS Secrets Manager, Vault, Doppler) for production.
19. CORS policy: not wildcard (*) in production - critical
AI defaults to Access-Control-Allow-Origin: * in 70%+ of codebases. Set explicit allowed origins matching your actual domains. Never use wildcard with credentials.
20. Debug mode disabled and error details hidden in production - critical
AI frequently generates dev-mode configs. Stack traces, internal paths, and DB schema details must never reach end users. Configure generic error pages for production.
21. All default admin credentials changed - high
AI scaffolding often includes admin@example.com:password123 as default credentials. Audit every default credential and enforce change on first deploy.
22. HTTPS enforced everywhere, HTTP redirects to HTTPS - high
Verify TLS is not disabled anywhere in the stack. Check for any self-signed cert bypass flags left in AI-generated code (e.g. NODE_TLS_REJECT_UNAUTHORIZED=0).
23. Security headers configured (CSP, HSTS, X-Frame-Options, etc.) - high
AI never adds security headers. Implement Content-Security-Policy, HTTP Strict Transport Security, X-Content-Type-Options, X-Frame-Options, and Referrer-Policy.
24. .env files in .gitignore, no secrets in git history - medium
Run git log and git grep to confirm secrets were never committed. If they were, treat them as compromised and rotate immediately.
Dependencies and Supply Chain
25. Dependency audit: no known CVEs in installed packages - critical
AI installs packages without checking maintenance status or CVEs — sometimes referencing packages that don't exist (hallucinated deps, a supply chain attack vector). Run npm audit, pip-audit, or Snyk before any production deploy.
26. No abandoned or unmaintained packages - high
AI training data includes deprecated packages. Check the last publish date and download trend for every dependency. Replace anything unmaintained.
27. Dependency lockfile committed and used in CI/CD - high
Ensure package-lock.json or yarn.lock is committed and that CI installs use --frozen-lockfile to prevent unexpected version resolution.
28. Minimal dependency footprint — no unnecessary packages - high
AI installs libraries for convenience without considering bundle size or attack surface. Audit and remove every package that isn't actively needed.
29. Subresource Integrity (SRI) on any CDN-loaded scripts - medium
If the frontend loads scripts from CDNs, add SRI hashes to detect tampering.
Data Handling and Privacy
30. PII never logged in plaintext - critical
AI debug/error handlers commonly log full request bodies including passwords, tokens, credit card numbers, and PII. Audit every logging call and add PII redaction before shipping.
31. Sensitive data encrypted at rest and in transit - critical
Verify database fields containing PII, health data, or financial data use encryption at rest. TLS must cover all network hops including internal service communication.
32. Data minimization: collect only what is needed - high
AI often stores more data than necessary. Review every model/schema field and remove or anonymize anything not essential to core functionality.
33. Database Row Level Security (RLS) policies reviewed - high
In Supabase/Postgres setups, AI generates RLS policies that are commonly misconfigured. Manually verify every policy — most vibe-coded apps have policies that allow any authenticated user to read all rows.
34. Backup strategy: automated, tested, and encrypted - high
AI never provisions backups. Verify automated database backups exist, are tested for restoration, and are encrypted.
35. Data retention and deletion policies implemented - high
GDPR/CCPA require the ability to delete user data on request. Confirm a deletion workflow exists and that it cascades correctly through all related tables.
36. Cookie attributes: Secure, HttpOnly, SameSite set correctly - medium
AI-generated cookie code often omits these flags. Verify all session and auth cookies have Secure, HttpOnly, and an appropriate SameSite value.
Error Handling and Resilience
37. No unhandled promise rejections or uncaught exceptions - critical
AI generates happy-path code. Unhandled async errors crash Node.js processes silently or cause undefined behavior. Every async operation needs explicit error handling.
38. Graceful degradation when external services fail - high
AI code calls third-party APIs without timeouts, retries, or fallbacks. Add circuit breakers, sensible timeouts, and fallback states for every external dependency.
39. Retry logic with exponential backoff and jitter - high
AI omits retry logic. Network calls to databases, queues, and APIs need retries with exponential backoff to avoid thundering herd problems.
40. Request timeouts set on all outbound HTTP calls - high
Missing timeouts cause threads/connections to hang indefinitely, eventually exhausting the connection pool and taking down the whole service.
41. Database connection pool limits configured correctly - high
AI database configs often lack connection pool settings. Misconfigured pools are among the most common causes of production crashes at moderate traffic.
42. Memory leak checks: no unbounded caches or event listeners - medium
AI commonly creates in-memory caches or event listener registrations inside request handlers, causing gradual memory leaks that only appear under real traffic.
43. Idempotency on payment and critical mutation endpoints - medium
Without idempotency keys, network retries on payment or order endpoints can cause double charges. Implement idempotency for any non-idempotent financial operation.
Logging, monitoring and observability
44. Security event logging: failed logins, auth denials, anomalies - critical
The most consistently absent element in AI-generated code. Failed auth, permission denials, and unusual access patterns must be logged for incident response. AI never adds this unless explicitly asked.
45. Structured logging with correlation IDs across requests - high
AI logging is typically unstructured console.log calls. Replace with structured logging (JSON) including trace/request IDs to enable cross-service debugging.
46. Uptime and error rate alerts configured - high
AI deploys an app but sets up no alerting. Configure alerts for error rate spikes, latency increases, and availability drops before going live.
47. Performance monitoring: slow query detection, APM - high
AI generates no performance instrumentation. Add APM tooling to detect N+1 queries, slow endpoints, and memory growth before users notice.
48. Audit trail for data mutations (who changed what, when) - high
For any app handling business-critical or regulated data, a tamper-evident audit log of all create/update/delete operations is required for both debugging and compliance.
49. Log aggregation and retention policy in place - medium
Logs need to ship to a centralized store (not just stdout) with a retention policy. Logs sitting only on ephemeral container storage are lost on restart.
Infrastructure and Deployment 
50. No development/test credentials or endpoints in production build - critical
Audit env configs, feature flags, and database connection strings for any test/staging values that slipped into the production build.
51. Principle of least privilege on all IAM roles and service accounts - high
AI generates IAM policies with wildcard permissions (*:*) by default. Every service account and role must have the minimum permissions required for its specific task.
52. CI/CD pipeline includes automated security scanning - high
Add SAST (Semgrep, Bandit, ESLint Security), dependency audit, and container scanning to CI so vulnerabilities are caught before merge.
53. Container images hardened: non-root user, minimal base image - high
AI Dockerfiles often run as root. Use a minimal base image, run as a non-root user, and verify no unnecessary tools or files are in the image.
54. Staging environment exists and is used before every production deploy - high
Many vibe-coded projects go directly from local dev to production. A staging environment that mirrors production is non-negotiable.
55. Rollback procedure tested and documented - high
A deployment procedure that doesn't include a tested rollback is incomplete. Verify rollbacks work before you need them.
56. Infrastructure as Code (IaC) reviewed for security misconfigs - medium
AI-generated Terraform/CloudFormation/Pulumi commonly creates publicly accessible S3 buckets, unrestricted security groups, and unencrypted storage. Run a cloud security posture tool.
57. Exposed ports minimized, firewall rules reviewed - medium
Audit which ports are open to the public internet. Databases and internal services should never be directly reachable from outside.
Architecture and Code Quality
58. Business logic not scattered across UI components - critical
AI weaves pricing, approval, and discount logic into React components. These must be extracted to the backend/service layer where they cannot be bypassed by frontend manipulation.
59. No N+1 database query patterns - high
AI generates N+1 queries routinely — loading a list then querying each item individually. Identify and replace with batch queries or joins before production traffic exposes the problem.
60. No duplicate business logic across codebase - high
Multiple AI prompting sessions create contradictory implementations of the same logic in different files. Audit for duplication and consolidate into single sources of truth.
61. API versioning strategy in place - high
AI rarely includes API versioning. Adding /v1/ prefixes before launch avoids costly breaking changes for existing clients later.
62. Database migrations are versioned and reproducible - high
Verify the database schema is managed through versioned migrations (not ad-hoc ALTER statements) and that migrations can be run cleanly on a fresh database.
63. Separation of concerns: UI, business logic, data access layers distinct - medium
AI creates monolithic files with no layering. Establish clear boundaries between presentation, business logic, and data access to enable future maintenance.
64. Environment-specific configuration externalized - medium
Magic numbers, feature flags, and environment-dependent URLs should be in config files or env vars — not hardcoded in the middle of business logic.
Performance and Scalability
65. Database queries indexed for production query patterns - high
AI generates schemas without indexes. Analyze the queries your app will run most frequently and verify appropriate indexes exist. Missing indexes are invisible in dev (small data) and catastrophic in prod.
66. Caching strategy for expensive or repeated computations - high
AI code hits the database on every request for data that rarely changes. Add caching (Redis, in-memory, CDN) for appropriate data with proper cache invalidation.
67. Pagination on all list/query endpoints - high
AI returns entire tables. Any endpoint that returns a list must have pagination. Returning unbounded results exhausts memory and crashes the server.
68. Large file/media handling via object storage, not app server - high
AI often handles file uploads by storing directly on the app server's filesystem. Use S3/GCS/Blob storage with direct upload or signed URLs.
69. Background jobs for long-running operations - medium
AI runs everything synchronously in request handlers. Tasks taking more than ~500ms (email sending, PDF generation, webhooks) should be offloaded to a job queue.
70. Frontend bundle size optimized (code splitting, lazy loading) - medium
AI generates frontend code without code splitting. Large initial bundle sizes cause slow first loads. Implement lazy loading for routes and heavy components.
71. Load testing performed before launch - medium
AI-generated code has never been tested under realistic concurrent load. A basic load test revealing connection pool exhaustion or memory leaks is mandatory before public launch.
Testing
72. AI-generated tests audited — not just asserting the same mistake - critical
AI tests frequently restate the production logic in the test, creating tests that pass even when the logic is wrong. Every test must verify behavior against independently reasoned expectations.
73. Critical path covered by integration tests - high
Unit tests alone don't catch integration failures. The most-used user journeys (auth, payment, core feature) must have end-to-end integration test coverage.
74. Edge cases and failure paths tested, not just happy paths - high
AI tests only the happy path. Tests for malformed input, network failures, permission denials, empty states, and concurrent operations are the ones that matter in production.
75. Tests run in CI on every pull request - high
Tests that don't run automatically don't get run. CI must fail the build if any test fails.
76. Security-specific tests: auth bypass, injection, access control - medium
Write explicit tests that try to bypass authentication, inject SQL, and access other users' data. If the tests fail, you have a vulnerability. If they pass, you've verified your defenses.
UX, Accessibility and Missing Features
77. Email delivery configured and tested (transactional emails) - high
AI generates email-sending code but almost never configures a real email provider. Verify verification emails, password resets, and notifications actually deliver. This is routinely skipped entirely.
78. Password reset flow is complete and secure - high
AI frequently omits the password reset flow entirely or implements it insecurely. Tokens must be single-use, time-limited, and invalidated after use.
79. Loading states, empty states, and error states implemented - high
AI builds the success state of every UI component. Loading spinners, empty list messages, and error states with recovery options are consistently missing.
80. Form validation with clear, accessible error messages - high
AI adds basic validation but inconsistently. Verify client-side and server-side validation exist for all forms, with meaningful error messages users can act on.
81. 404, 500, and other error pages are user-friendly - high
AI leaves the default framework error pages which often expose stack traces. Implement custom error pages that are helpful and reveal nothing sensitive.
82. Responsive design tested across device sizes - medium
AI sometimes generates desktop-only layouts. Test on mobile viewports. Many vibe-coded apps break entirely below 768px.
83. Basic WCAG accessibility: keyboard navigation, screen reader labels - medium
AI generates no accessibility attributes. Add aria-labels, alt text, focus management, and verify core flows work with keyboard-only navigation.
84. User feedback mechanisms: onboarding, tooltips, success confirmations - medium
AI builds functional features but often misses the micro-UX: confirmation dialogs on destructive actions, success toasts, onboarding flows for new users.
85. Terms of service and privacy policy pages exist and link correctly - medium
Required for most apps handling user data. AI never generates these or links them properly to the sign-up flow.
Compliance and Regulatory 
86. GDPR/CCPA consent and data rights implemented if applicable - critical
If users are in the EU or California, explicit consent for data collection, a cookie banner, and data subject rights (access, deletion, portability) are legally required.
87. PCI-DSS compliance if handling card data - critical
Card numbers must never touch your servers. Use Stripe Elements, Braintree Drop-in, or equivalent tokenization so raw card data is processed entirely by the payment provider.
88. HIPAA safeguards if handling health data (US) - critical
PHI requires encryption, audit logs, access controls, BAAs with vendors, and breach notification procedures. AI generates none of these.
89. Audit trail for compliance-sensitive operations - high
Financial, medical, and legal applications require tamper-evident logs of all data access and mutations with timestamps and user attribution.
90. Age verification if app is restricted to adults - medium
If your app serves age-restricted content, a compliant age verification mechanism is required, not just a checkbox.
Documentation and Maintainability
91. README covers setup, environment variables, and deployment - high
AI-generated projects often have no README or one that doesn't match the actual codebase. Document every required environment variable and the steps to run the app locally and deploy it.
92. API documentation generated or written - high
All public or internal API endpoints must be documented with their inputs, outputs, auth requirements, and error codes. Undocumented APIs become unmaintainable.
93. Business logic has inline comments explaining intent - medium
AI business logic is traceable only if it's documented. Compliance and future developers both need to know why decisions were made, not just what the code does.
94. Incident response runbook exists - medium
What happens when the app goes down? Who is alerted? What are the steps? This doesn't need to be long but must exist before launch.
95. Architecture decision records (ADRs) for major design choices - medium
Vibe-coded apps have no record of why a framework, database, or approach was chosen. Document the key decisions so future maintainers understand the system's assumptions.

