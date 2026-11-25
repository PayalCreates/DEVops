# ADR-0003: Stateless JWT authentication with RBAC

**Status:** Accepted

## Context
The API must authenticate users and authorise actions for three roles. It runs as
multiple replicas in two colours (blue and green) at the same time.

## Decision
- Short-lived (60 min; 30 in production) **HS256 JWT** with `sub`, `role`, `iat`, `exp` and `iss`. The secret is injected from a Kubernetes Secret. `alg=none` and other algorithms are rejected.
- The **role is re-read from the database on every request**, not trusted from the token, so a demotion or deactivation takes effect immediately.
- Roles: `user` (own tasks), `manager` (read all tasks and users), `admin` (manage roles and activation). Self-registration always creates `user`.
- Passwords: bcrypt cost 12; login timing is equalised for unknown emails; per-IP+email rate limit in the app plus a per-IP limit at the ingress.
- SPA stores the token in **sessionStorage**.

## Alternatives considered
- **Server-side sessions:** these need a shared session store (Redis) across replicas and colours, which costs extra RAM on a laptop.
- **httpOnly cookie:** better XSS resistance but requires CSRF protection. We mitigate XSS with a strict CSP (`script-src 'self'`, no inline scripts) and a lint rule banning `dangerouslySetInnerHTML`. This is documented as a known trade-off in the threat model.
- **OAuth2/OIDC provider (Keycloak):** the right answer in a company, but about 500 MB of RAM and out of scope.

## Consequences
+ Any replica of either colour can validate any token, which is essential for blue-green.
− Tokens cannot be revoked before expiry, except by deactivating the user (checked per request) or rotating the secret.
