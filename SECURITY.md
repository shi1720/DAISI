# Deployment boundaries

The default local server binds to loopback and uses a single-process SQLite store. Local passwords use Argon2id and opaque HttpOnly sessions; there is no email verification or password recovery in local mode. Use the documented deployment mode for public access.

## Public Firebase service

The public release uses Firebase Authentication and private Cloud Firestore through a dedicated Cloud Run runtime identity. Firebase manages password credentials. Server-verified, revocation-checked `__session` cookies are Secure, HttpOnly and SameSite=Lax. Mutations require an exact allowed origin and a session-bound CSRF token. Shared Firestore state preserves throttling and revocation across instances. Password reset uses Firebase's recovery flow and returns a generic response.

The Cloud Run endpoint is publicly invokable so Firebase Hosting can route requests. Private application endpoints still require authenticated identity. Arbitrary forwarding headers are not trusted as a visitor or user identity. Firestore browser rules deny direct access; server queries scope proposals to a hash of the authenticated UID. Updates require the loaded revision, and stale edits fail with 409 rather than overwriting a newer review. Immutable compressed plan payloads are size bounded and validated on decode.

Guest records have a seven-day ceiling and are removed on guest logout. An hourly bounded job deletes expired guest work and expired throttle/revocation records. Named-account deletion uses a resumable tombstone, revokes access and removes that account's workspace. Inactive named accounts are not aged out. Signing into a named account does not migrate guest proposals. See [deployment and retention controls](docs/firebase-deployment.md) and [actual retention verification](docs/firebase-retention-verification.json).

Runtime credentials use managed service identities. No service-account key or OpenAI key is shipped to the browser or container. Build-context allowlists exclude private state, credentials and unrelated folders. Static HTML revalidates; API responses are private/no-store; versioned assets are immutable.

## Databricks service

Databricks mode belongs exclusively behind the authenticated Databricks Apps proxy. Forwarded platform identity must never be trusted on a directly exposed server. The app service principal is limited to its designated published snapshot, evaluation and plan tables. Ordinary users must not receive direct access to the plan table: application ownership is enforced by parameterized predicates, not a separate Unity Catalog row policy. Concurrent Delta conflicts are reported without overwriting the winning revision.

The configured Databricks app runs one process; its CSRF signing key refreshes on restart, after which users refresh the page. Workspace identity, publication checks and actual SQL/MLflow execution are documented separately from public Firebase acceptance. Databricks Free Edition is the challenge environment, not a commercial production SLA.

## Data and operations

Snapshots contain public aggregate statistics, not individual resident records. Do not store names, health information or sensitive welfare case notes. Source URLs are fixed to named HTTPS datasets; ingestion is not a general-purpose URL-fetch service. Secrets belong in platform-managed credentials, never in code, notes, screenshots or GitHub issues.

The verified release supports isolated workspaces, not shared team permissions. A commercial service still needs operator validation, appropriate licensed infrastructure, restore exercises, support ownership and monitoring at its intended load. No penetration-test certification or production availability guarantee is claimed.

Report vulnerabilities privately to the repository owner through GitHub before publishing exploit details. No unverified contact address is invented here.
