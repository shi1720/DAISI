# Deployment boundaries

The default local server binds to loopback and uses a local SQLite store. Do not expose it as an internet service without HTTPS, secure cookies, exact origin configuration, a backup/retention plan and an operational security review. There is no email verification or password-recovery service in local mode.

Databricks mode is designed exclusively behind the authenticated Databricks Apps proxy. Its forwarded identity headers must never be trusted on a directly exposed server. The workspace app service principal can access only its designated snapshot, evaluation and plan tables. End users must not receive direct access to the plans table because application ownership is enforced by parameterized predicates, not a separate Unity Catalog row policy.

Passwords are Argon2id hashes. Browser sessions are random opaque HttpOnly cookies; only token hashes are stored. Mutating requests use CSRF tokens and origin checks. Secrets belong in platform-managed credentials/resources, never in code, saved notes, screenshots or GitHub issues.

The local application runs one process. Databricks Apps should run the configured single process; the CSRF signing key refreshes on restart, after which users refresh the page. High traffic, team sharing, distributed sessions, deletion retention, enterprise identity and disaster recovery are deployment work, not claims made by this challenge build.

Dataset snapshots contain public aggregate statistics, not personal resident records. Avoid storing names, health data or sensitive welfare details in coordinator notes. Source URLs are fixed to named HTTPS datasets; the ingestion CLI is not a general-purpose URL fetch service.

Report vulnerabilities privately to the repository owner through GitHub before publishing exploit details. No public security contact address is invented here.
