# Curator run — 2026-06-16T07:32:16.259220+00:00

Model: `MiniMax-M3` via `minimax-cn`  ·  Duration: 53m 9s  ·  Agent-created skills: 74 → 73 (-1)

## Auto-transitions (pure, no LLM)

- checked: 74
- marked stale: 0
- archived (no LLM, pure time-based staleness): 0
- reactivated: 0

## LLM consolidation pass

- tool calls: **171** (by name: patch=7, read_file=11, search_files=1, skill_view=1, terminal=148, todo=3)
- consolidated into umbrellas: **0**
- pruned (archived for staleness): **1**
- new skills this run: **0**
- state transitions (active ↔ stale ↔ archived): **0**

### Pruned — archived for staleness (1)

_These skills were archived without being merged into an umbrella (e.g. stale, unused, or judged irrelevant). Directories live under `~/.hermes/skills/.archive/`. Restore any via `hermes curator restore <name>`._

- `nano-pdf`

## LLM final summary

Most are at v1.0.0. Nothing indicates obsolescence. The library is just fresh.

Let me also look at the description fields one more time to confirm none look like salvage/audit artifacts:

## Recovery

- Restore an archived skill: `hermes curator restore <name>`
- All archives live under `~/.hermes/skills/.archive/` and are recoverable by `mv`
- See `run.json` in this directory for the full machine-readable record.
