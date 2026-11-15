# Team server

This guide covers deployment, identity configuration, security architecture, and ongoing operations for running Zyn in **team server mode**.

> **Tested in a container, not yet at a company.** On every change to the server or container files, GitHub builds the image on a clean Linux machine, starts the trial compose (PostgreSQL, schema upgrade, Keycloak and Zyn), signs in as a trial user through Keycloak, and checks the person, project and role the server reports. The first run passed on 15 November 2026. It has not yet run behind a company's own sign-in, network or database, so try it on a test host first.

---

## 1. Architecture and system requirements

Zyn runs as a containerized web service backed by PostgreSQL and your enterprise OpenID Connect (OIDC) identity provider.

- **Operating system:** Linux container host (Ubuntu 22.04 LTS, RHEL 9+, Debian 12) with Docker Engine 24+ and Docker Compose v2.
- **Database:** PostgreSQL 16+ (self-hosted, Amazon RDS, Azure Database for PostgreSQL, or Cloud SQL).
- **Identity provider (IdP):** Any standard OIDC provider (Microsoft Entra ID, Okta, Keycloak, Ping Identity).
- **Hardware resources:**
  - Minimum: 2 vCPU, 4 GB RAM, 20 GB disk (for temporary uploads and logs).
  - Recommended: 4 vCPU, 8 GB RAM, 50 GB disk.
- **Network egress:** HTTPS (port 443) to your allowed model endpoints: the Anthropic API, or an internal Ollama server. Connectors for AWS Bedrock, Azure OpenAI, Google Cloud Vertex AI, and OpenAI-compatible endpoints (such as private vLLM) are built, not tried against live endpoints. No telemetry or tracking traffic leaves the host.
- **Optional dependencies:** The team container image includes the core and team server dependencies. For deployments using AWS Bedrock or Google Vertex AI, install the optional dependencies (`pip install 'zyn-harness[bedrock,vertex]'`) or build a derived container image.

---

## 2. Quickstart with Docker compose

1. Clone or extract the Zyn team package onto your server.
2. Copy `deploy/team.example.yaml` to `deploy/team.yaml` (which is mounted into the container at `/data/config.yaml:ro`) and customize it for your environment.
3. Set the required secrets in your `.env` file:
   - `ZYN_DATABASE_ADMIN_PASSWORD`
   - `ZYN_DATABASE_PASSWORD`
   - `ZYN_SESSION_SECRET`
   - `ZYN_OIDC_CLIENT_SECRET`
4. Launch with Docker compose:
   ```bash
   docker compose up -d
   ```
5. Check health status:
   ```bash
   curl http://localhost:8600/api/health
   ```

### Trial mode (local evaluation without corporate IT)

To evaluate the team server without configuring your corporate IdP, use the self-contained trial compose file which spins up a full environment including Keycloak with pre-configured users (`alice` as approver, `bob` as engineer):
```bash
docker compose -f compose.trial.yaml up -d
```
Access the review screen at `http://localhost:8600`. The trial configuration enables `allow_insecure_http: true` and connects to Keycloak at `http://localhost:8080/realms/zyn-trial`.

To run an automated test of the trial containers, database migrations, and Keycloak realm on a Docker host:
```bash
./scripts/verify-trial-docker.sh
```

---

## 3. Database architecture and dual-user security model

The audit trail requires strict write-once integrity. Zyn enforces this using PostgreSQL table permissions and append-only database triggers across two distinct database users:

1. **Migration and admin user (`zyn_admin`):**
   - Owns the database schema.
   - Applies migrations via `zyn upgrade --admin-url postgresql://...`.
   - Creates append-only triggers that forbid `UPDATE`, `DELETE`, and `TRUNCATE` on audit tables (`runs`, `items`, `events`, `tokens`, `schema_versions`).
   - Used **only** during initial installation and schema upgrades.

2. **Application user (`zyn`):**
   - Used by the running Zyn service container.
   - Granted only `SELECT`, `INSERT` on tables, and `USAGE` on sequences.
   - Hard-blocked by PostgreSQL permissions and triggers from altering or removing audit history.

To apply database migrations:
```bash
zyn upgrade --admin-url postgresql://zyn_admin:${ZYN_DATABASE_ADMIN_PASSWORD}@db:5432/zyn --app-user zyn
```

---

## 4. Single sign-on (OIDC) configuration

Zyn delegates all authentication to your corporate identity provider using authorization code flow with PKCE (`S256` code challenge) and signed session cookies.

### Sessions and token lifecycle
- **Signed session cookies:** Authenticated user sessions are stored in HTTP-only signed cookies. Each session enforces an absolute expiration limit of `session_hours` (default 12 hours) calculated from `signed_in_at`; sessions cannot be refreshed indefinitely.
- **Personal access tokens:** Named persons can mint access tokens (capped at 90 days) for scripts and automated workflows. Note that tokens retain the owner's project roles and groups as captured at token creation. If an employee changes roles or leaves the organization and is removed from IdP groups, previously minted tokens remain valid until expiration or explicit revocation. Use `zyn revoke-person <person_id> --as <admin_name>` to immediately revoke all tokens and sessions for that person.

### Common parameters
- **Redirect URI:** `<public_url>/auth/callback` (e.g. `https://zyn.corp.internal/auth/callback`)
- **Required scopes:** `openid`, `profile`, `email`, `groups`

### Microsoft Entra ID (Azure AD)
1. In Azure Portal, register an application: **Zyn Team Server**.
2. Under **Authentication**, add a Web platform with Redirect URI: `https://<your-host>/auth/callback`.
3. Under **Certificates & secrets**, generate a client secret and store it securely.
4. Under **Token configuration**, add group claims (`Security groups` or `All groups`).
5. Configure in `config.yaml`:
   ```yaml
   team:
     oidc:
       issuer: https://login.microsoftonline.com/<Tenant-ID>/v2.0
       client_id: <Application-ID>
       client_secret: ${ZYN_OIDC_CLIENT_SECRET}
   ```

### Okta
1. In Okta Admin Console, create an **OIDC - Web Application**.
2. Set Sign-in redirect URI: `https://<your-host>/auth/callback`.
3. Under Assignments, assign developer and review groups.
4. In the application settings, configure a `groups` claim filter (e.g. regex `.*`).

### Keycloak
1. Create a client with client authentication enabled.
2. Add redirect URI `https://<your-host>/auth/callback`.
3. Ensure client scopes include `groups` mapped via `oidc-group-membership-mapper` with `full.path` set to `false`.

---

## 5. Reverse proxy and HTTPS configuration

Zyn must run behind a reverse proxy terminating TLS (Nginx, Traefik, AWS ALB, or Envoy).

### Forwarded headers and cookie security
When `public_url` starts with `https://`, session cookies are automatically marked with `Secure; HttpOnly; SameSite=Lax`. Ensure the proxy sets standard forwarding headers.

**Example Nginx configuration:**
If Nginx runs on the host network, proxy to `http://127.0.0.1:8600`. If Nginx runs in a Docker container on the same network, proxy to `http://zyn:8600`:
```nginx
server {
    listen 443 ssl http2;
    server_name zyn.corp.internal;

    ssl_certificate /etc/ssl/certs/zyn.crt;
    ssl_certificate_key /etc/ssl/private/zyn.key;

    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:8600;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_read_timeout 300s;
    }
}
```

---

## 6. Access logging and SIEM integration

In team mode, Zyn outputs structured JSON logs for every request to `stderr` (leaving `stdout` clean for command piping):
```json
{
  "ts": "2026-11-14T05:35:18.123Z",
  "method": "POST",
  "path": "/api/decide",
  "status": 200,
  "duration_ms": 14.2,
  "principal_id": "oidc:tenant#user-id",
  "project": "bcm"
}
```
**Security properties:**
- Request bodies, passwords, tokens, and engineering file contents are **never** logged.
- On unauthenticated requests resulting in status code `401`, `principal_id` is recorded as `null`.
- On permission violations or four-eyes blocks resulting in status code `403`, the authenticated principal and the resolved project identifier (or `null` if the request was blocked before project resolution) are recorded.
- Container log shippers (Splunk Universal Forwarder, Datadog Agent, Fluentbit, Vector) can forward `stderr` directly to your SIEM.

---

## 7. Data sovereignty and the data rule

- **Zero phone home:** Zyn contains no vendor telemetry, license verification calls, or analytics beacons.
- **The data rule:** Model calls are restricted exclusively to rule profiles declared in `team.allowed_models`. Any stage requesting an unauthorized profile is blocked and rejected with an audit log event.
- **On-premise and air-gap option:** For air-gapped environments, set `offline: true`. When offline mode is active, only local models are permitted:
  - Local Ollama instances running on loopback, private network addresses (RFC 1918, fc00::/7), or non-metadata link-local addresses (`fe80::/10`, `169.254.0.0/16` excluding the cloud metadata address `169.254.169.254`). Ollama cloud models (such as `-cloud` models) are refused.
  - OpenAI-compatible endpoints (such as self-hosted vLLM) configured with `local: true` whose `base_url` resolves to loopback, private network addresses, non-metadata link-local addresses, or an entry in `offline_allowed_hosts`.
  - All other cloud providers (Anthropic, AWS Bedrock, Azure OpenAI, Google Vertex AI) are refused before any network call, and the refusal is recorded in the audit log.

---

## 8. Backup, restore and disaster recovery

The structured audit log is stored in PostgreSQL. In addition, evidence exports and cryptographic hash chains live as files on the `/data` volume (under `runs/exports/`). A complete backup requires dumping the PostgreSQL database alongside the `/data` volume:

### Backup
```bash
# 1. Back up database
pg_dump -U zyn_admin -d zyn -Fc -f zyn_audit_$(date +%Y%m%d).dump

# 2. Back up data directory (contains export hash chains, synthetic datasets, and rules)
tar -czf zyn_data_$(date +%Y%m%d).tar.gz -C /data .
```

### Restore
```bash
# 1. Restore database
pg_restore -U zyn_admin -d zyn --clean --if-exists zyn_audit_YYYYMMDD.dump

# 2. Restore data directory
tar -xzf zyn_data_YYYYMMDD.tar.gz -C /data
```

Hash chains generated during individual run exports can be verified independently using `zyn evidence verify <audit_chain.json>`.

---

## 9. Upgrades and schema migrations

When upgrading to a new Zyn release:

1. **Back up the database and data volume:**
   ```bash
   pg_dump -U zyn_admin -d zyn -Fc -f zyn_pre_upgrade.dump
   tar -czf zyn_data_pre_upgrade.tar.gz -C /data .
   ```
2. **Pull or build the updated image:**
   ```bash
   docker compose pull
   # or when building from source:
   docker compose build
   ```
3. **Run database migrations as admin:**
   ```bash
   docker compose run --rm upgrade
   ```
4. **Restart the application service:**
   ```bash
   docker compose up -d zyn
   ```
5. **Verify health check:**
   ```bash
   curl -f http://localhost:8600/api/health
   ```

---

## 10. Test status

> **Tested in a container, not yet at a company.** `.github/workflows/docker-trial.yml` runs `scripts/verify-trial-docker.sh` on a clean Linux machine: it builds the image, starts the trial compose, waits for every service, signs in end to end through Keycloak with PKCE, and checks that the signed-in person has the approver role on project `bcm`. You can run the same script on your own test host. It has not yet run against a real company identity provider, network or database.
