# Public Firebase deployment

HawkerBridge uses Firebase Hosting for the React interface and a same-origin `/api/**` rewrite to the Python API in Cloud Run, Singapore (`asia-southeast1`). Firebase Authentication owns passwords and sessions. Cloud Firestore owns private saved proposals. The container includes an immutable, versioned public-data snapshot and its matching evaluation.

The public service is separate from the Databricks data pipeline. A Databricks publication is promoted into the container only after its source fingerprint, quality gates and evaluation are verified. Serving a website through Firebase does not, by itself, demonstrate Databricks execution.

## Project isolation

The initial release uses a dedicated identity/data project, `hawkerbridge`, and site `hawkerbridge-sg`. The existing shared compute project, `gen-lang-client-0444960702`, supplies billing for an isolated `hawkerbridge-api` Cloud Run service and `hawkerbridge` image repository. The account's five-project billing quota prevented linking billing to the new project. No existing application, service account or database was replaced.

For a fresh installation with billing available, all components can instead use one dedicated project. Change the Hosting site in `firebase.json` and supply that project to both deployment arguments.

## One-time provisioning

Use authenticated official `gcloud` and `firebase-tools` CLIs. Version 15.30.2 of Firebase CLI was used for this release. A keyfile is not needed. Do not put an OpenAI key in the application: planning and briefs do not depend on one.

1. Create a Firebase identity project. Enable `firestore.googleapis.com` and `identitytoolkit.googleapis.com`. Create its native Firestore database in `asia-southeast1` and a Firebase Web App.
2. Deploy `firebase-data.json` against the identity project. This enables email/password and anonymous sign-in, and publishes deny-all browser Firestore rules. Keep improved email privacy enabled and add the actual site domains to Firebase Auth's authorised domains.
3. Restrict the Firebase Web App key to `identitytoolkit.googleapis.com` and `securetoken.googleapis.com`. This is a public service identifier, not an Admin credential. The server proxy uses it for sign-in; Admin access uses the runtime service account.
4. In the billing-enabled compute project, enable Cloud Run, Cloud Build and Artifact Registry. Create a Docker repository named `hawkerbridge` in `asia-southeast1`, a Hosting site, and a service account named `hawkerbridge-runtime`.
5. Grant that specific runtime service account `roles/datastore.user` and `roles/firebaseauth.admin` in the identity project only. Do not use the project's broad default compute identity for the API. Cloud Build's build identity needs the normal image-push permissions in the compute project.

The deployment command below intentionally does not create projects, link billing, change unrelated IAM, or guess which account to use.

## Repeatable release

Run from the repository root with the exact existing Web App ID:

```sh
uv sync --frozen --extra dev --python 3.12
uv run python scripts/deploy_firebase.py \
  --project gen-lang-client-0444960702 \
  --identity-project hawkerbridge \
  --web-app-id YOUR_EXISTING_WEB_APP_ID \
  --site hawkerbridge-sg \
  --firebase-cli .tools/firebase/node_modules/.bin/firebase
uv run python scripts/smoke_hosted.py \
  --url https://hawkerbridge-sg.web.app \
  --retain-state tmp/hosted-restart-check.json
```

The script builds the UI, uploads only the whitelisted container inputs, builds a dated image, deploys an unprivileged container and pins the Hosting rewrite to its release. It keeps runtime configuration in a private temporary file and removes it after deployment. Cloud Run is bounded to two instances, one CPU and 1 GiB each, with zero warm minimum instances and a 60-second request timeout. These are capacity bounds, not a guaranteed spending cap. Review actual billing and quotas before opening a large pilot.

Roll out the next release, then prove persistence and remove the synthetic account:

```sh
uv run python scripts/smoke_hosted.py \
  --url https://hawkerbridge-sg.web.app \
  --resume tmp/hosted-restart-check.json \
  --report output/hosted-restart-smoke.json
```

Use the GitHub Actions `Verify HawkerBridge` manual workflow with `base_url=https://hawkerbridge-sg.web.app`. Set `record_demo=true` only when collecting actual release footage. These browser tests run in an isolated remote runner. Synthetic test accounts use the reserved `.test` domain and are deleted; no reset email is sent.

## Session and data boundaries

Firebase Hosting forwards only the `__session` cookie. Hosted mode uses that name with Secure, HttpOnly and SameSite=Lax settings. Mutations require the session's CSRF token and an allowed origin. API responses are private and not cacheable. Cloud Run instances share durable authentication, session revocation and throttling state.

Plans are keyed by a hash of the authenticated Firebase user ID. Compressed immutable plan payloads are bounded below Firestore's 1 MiB document limit; listings read metadata rather than every full proposal. Browser Firestore rules deny every direct read/write. Account deletion removes that user's records. Guest sessions are temporary, with a seven-day ceiling; logout removes their plans. Signing in to a named account does not transfer guest plans. It revokes that guest session; abandoned guest records are removed by expiry cleanup.

## Guest and throttle cleanup

Firestore's free project does not provide free TTL deletion. Run `uv run python scripts/configure_retention.py --project gen-lang-client-0444960702` after deploying the API. It configures and executes the deletion worker, then schedules an hourly Cloud Run Job with the same runtime identity and project settings. A separate scheduler identity may invoke only that job. Once provisioned, add `--dry-run` to inspect eligible records through an execution-time argument override. Dry inspection never changes the saved deletion command or its schedule. Each run handles at most 1,000 workspaces. It removes expired guest accounts and expired throttle/revocation entries. The API rejects expired guests before cleanup, and the cleanup is idempotent. No named account is removed merely because it is inactive.

Authentication limits are shared service budgets rather than per-visitor IP claims: 120 sign-in attempts per five minutes, 120 new guest sessions per hour and 30 password resets per hour, with narrower per-email limits and authenticated user limits. Configure the bounded environment variables in `backend/hawkerbridge/config.py` before a larger pilot. Arbitrary forwarding headers are not trusted as visitor identity.

HTML and SPA routes revalidate on every visit; hashed assets are cached immutably. The hosted smoke checks these headers after deployment.

## Rollback and inspection

Firebase Hosting keeps release history. Roll back the Hosting release to restore its pinned API revision and matching static bundle, then rerun the hosted smoke test. Do not roll back Firestore data by deleting it. Inspect Cloud Run request/error logs, Firebase Auth errors, Firestore quotas and the source fingerprint in `/api/health` when diagnosing a release.

Official references: [Cloud Run integration](https://firebase.google.com/docs/hosting/cloud-run), [Hosting cookie and cache behaviour](https://firebase.google.com/docs/hosting/manage-cache), [session cookies](https://firebase.google.com/docs/auth/admin/manage-cookies), [Auth provider configuration](https://firebase.google.com/docs/auth/configure-providers-cli), [Firestore quotas](https://firebase.google.com/docs/firestore/quotas).
