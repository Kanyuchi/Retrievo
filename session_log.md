# Session Log

## 2026-09-01 — Project state audit after ~3.5-month gap; humbowo.com migration kickoff
- Read repo + git history to reconstruct state (last commit was 2026-05-18; 146 commits total since 2026-01-24)
- Pushed the one unpushed docs commit (`d972533`) to origin/main
- Audited every domain/host/IP reference in the repo (nginx, TLS scripts, CORS, OAuth, cookies, frontend API base) in preparation for moving to humbowo.com
- Verified humbowo.com is registered (GoDaddy, 2026-09-01) with GoDaddy DNS — currently parked
- **Discovered production is down**: old Lightsail server 13.49.191.201 unreachable on 22/80/443, and `.keys/lightsail.pem` missing locally; old AWS account (Nguks') presumed inaccessible → new hosting + new database required
- Created living documentation files (project_state.md, session_log.md, whats_next.md)
