# Release Readiness

## Current verification

- Date: 2026-09-28 (Asia/Jakarta).
- Imported repository base: `ff37ae0`.
- Backend target: Python 3.11; local verification used Python 3.12 because 3.11 is not installed on this VM.
- Frontend: Node 24.19.0 and npm 11.17.0.
- Docker CLI/Compose are installed, but the current VM user cannot access `/var/run/docker.sock` because it is not a member of the `docker` group.

## Results

| Check | Result | Evidence |
|---|---|---|
| Python compilation | PASS | `python3 -m compileall -q app tests` |
| Backend test suite | PASS | all collected service and end-to-end tests passed under Python 3.12 |
| Frontend ESLint | PASS with one warning | no errors; existing `window.location.href` navigation warning in `src/lib/auth.ts` |
| Frontend TypeScript | PASS | `tsc --noEmit` |
| Frontend production build | PASS | Next.js generated 29 routes |
| Frontend unit tests | FAIL, 9/10 pass | stale logo assertion expects `/logo-mark.png`; component uses `/globe.svg`; supplied archive contains no `logo-mark.png` |
| Markdown whitespace | PASS | `git diff --check` |
| Docker build/smoke | NOT RUN | current user lacks Docker socket permission |
| Secret scan | PASS for imported tree | no real `.env` file or copied Cloudflare token; historical archive still requires rotation/history cleanup |

## Verified behavior covered by backend tests

- JWT, bcrypt, malformed subject rejection, and payer pseudonymization.
- HMAC callback signatures, invalid signature rejection, and replay rejection.
- Critical score floors, score range, and cross-region non-escalation.
- Rule/graph fallback when model artifacts are absent.
- Merchant ownership isolation and role-based access.
- Provider-only paid state and analyst/admin-only alert resolution.
- Adaptive-label readiness, graph truncation, and closed edges.
- FedAvg weighted aggregation.
- Server-side pagination and stable ordering.
- Admin activity monitoring and role/period filters.
- Impact dashboard over more than 100 rows.
- Subscription entitlement behavior.
- Idempotent demo seed.

## Known source issue

`frontend/tests/presentation.test.ts` expects `AppLogo` to contain `/logo-mark.png`. The supplied archive does not include that bitmap, and `AppLogo` currently renders `/globe.svg`. `frontend/public/logo.svg` also references the missing bitmap. The application build succeeds, but official logo consistency remains unresolved. Do not claim a fully green frontend test suite until the intended asset is restored or the expectation is deliberately changed.

## Security action

The original tracked `backups.zip` included environment secrets and a Cloudflare service token. It has been removed from the current snapshot, but remains in old commits. Follow [`SECURITY_ACTION_REQUIRED.md`](../SECURITY_ACTION_REQUIRED.md) before reusing any credential.

## Docker recheck after fixing VM permission

Log out and back in after adding the user to the `docker` group, then run:

```bash
docker version
docker compose version
cp .env.demo.example .env
make docker-config
make docker-build
make docker-up
make seed-demo
make smoke
docker compose --env-file .env \
  -f docker-compose.yml -f docker-compose.demo.yml ps
```

Never run `docker compose down -v` against a deployment with data.

## Verdict

**MVP source and documentation are usable, with two open verification items:** restore or decide the official logo asset and rerun Docker build/smoke after granting Docker socket access. This remains a simulated hackathon MVP, not production financial infrastructure.
