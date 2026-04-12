# Deployment And Ops

## Purpose
- Define the container runtime, Compose deployment shape, and GitHub Actions deployment path.

## Main Files And Directories
- `Dockerfile`
- `docker-compose.yml`
- `.github/workflows/deploy.yaml`
- `requirements.txt`

## Entry Points
- Docker runtime command: `python -m src.main`
- GitHub Actions triggers: push to `main` and `workflow_dispatch`
- Compose service: `te-leet-bot`

## Key Symbols
- `Dockerfile CMD`
- `docker-compose service te-leet-bot`
- `CI/CD (GHCR + Tailscale OAuth)` workflow

## Dependencies
- GHCR image publishing
- Tailscale GitHub Action and Tailscale SSH
- Host bind mounts for persistent SQLite data

## Invariants
- The image installs Python dependencies from `requirements.txt` and runs as non-root `appuser`.
- Compose mounts `./data/bot.db` to `/app/bot.db`; container-local writes must still target `/app/bot.db`.
- The deploy workflow builds and pushes `ghcr.io/<owner>/teleetbot:main`, then SSHes to `/srv/apps/teleetbot` and recreates the Compose service.
- The container health check only verifies Telegram reachability and `BOT_TOKEN`; it does not check Discord readiness.

## Common Tasks
- Change environment variables or secrets used at runtime
- Change the image tag, registry path, or deploy host
- Adjust mounts for persistent data
- Investigate CI or deployment failures

## Related Flows
- [startup-and-runtime](../flows/startup-and-runtime.md)
