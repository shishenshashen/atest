---
name: kanban
description: Hermes Kanban multi-agent system — orchestrate tasks across specialist profiles, run a worker card, or delegate implementation to a Codex lane. Use when the user wants the Hermes Kanban board, multi-profile task routing, persistent cross-restart work, or to spawn a Codex lane inside a worker run. This is the umbrella for the former kanban-orchestrator, kanban-worker, and kanban-codex-lane skills (see Changelog).
version: 4.0.0
author: Hermes Agent (with codex-lane work by Teknium)
license: MIT
platforms: [linux, macos, windows]
environments: [kanban]
metadata:
  hermes:
    tags: [kanban, multi-agent, orchestration, worker, codex-lane, routing, persistence, worktrees]
    category: devops
    related_skills: [codex, hermes-agent, subagent-driven-development]

## Changelog

- **4.0.0** — Umbrella consolidation. Absorbed `kanban-orchestrator`, `kanban-worker`, and `kanban-codex-lane`. The Kanban system is one class with three roles; split skills made the orchestrator/worker/codex-lane relationship harder to discover than a single umbrella with labeled sections.
- **3.0.0** — `kanban-orchestrator` standalone (decomposition playbook).
- **2.0.0** — `kanban-worker` standalone (pitfalls + handoff shapes).
- **1.0.0** — `kanban-codex-lane` standalone (Codex as input lane).

# Hermes Kanban — Multi-Agent Task System

The Kanban system is how Hermes dispatches durable work across specialist profiles. Three roles participate; this skill covers all three. **The basic lifecycle (orient → work → heartbeat → block/complete) is auto-injected into every kanban worker's system prompt as `KANBAN_GUIDANCE`.** This umbrella is the deeper detail for each role.

## Which section do you need?

| If you are… | Read this section |
|---|---|
| A profile whose job is to route work, decompose requests, and never do the work itself | **Section A — Orchestrator** |
| A specialist profile that was just assigned a card and needs to execute it | **Section B — Worker** |
| A worker that wants to use Codex CLI as a bounded implementation lane | **Section C — Codex lane (optional)** |

Profiles are user-configured — there is no fixed roster. **Run `hermes profile list` first** so you know which profiles exist on this machine. The dispatcher silently fails on unknown assignee names; the card just sits in `ready` forever.

---

## Section A — Orchestrator

Your job description is "route, don't execute." A typical orchestrator profile has a restricted toolset (no terminal/file/code/web for implementation). The rules that enforce that:

- **Do not execute the work yourself.** If you find yourself "just fixing this quickly" — stop and create a task for the right specialist.
- **For any concrete task, create a Kanban task and assign it.** Every single time.
- **Split multi-lane requests before creating cards.** A user prompt can contain several independent workstreams. Extract those lanes first, then create one card per lane instead of bundling unrelated work into a single implementer card.
- **Run independent lanes in parallel.** If two cards do not need each other's output, leave them unlinked so the dispatcher can fan them out. Link only true data dependencies.
- **Never create dependent work as independent ready cards.** If a card must wait for another card, pass `parents=[...]` in the original `kanban_create` call.
- **If no specialist fits the available profiles, ask the user which profile to create or which existing profile to use.** Do not invent profile names; the dispatcher will silently drop unknown assignees.
- **Decompose, route, and summarize — that's the whole job.**

### When to use the board (vs. just doing the work)

Create Kanban tasks when any of these are true:

1. **Multiple specialists are needed.** Research + analysis + writing is three profiles.
2. **The work should survive a crash or restart.** Long-running, recurring, or important.
3. **The user might want to interject.** Human-in-the-loop at any step.
4. **Multiple subtasks can run in parallel.** Fan-out for speed.
5. **Review / iteration is expected.** A reviewer profile loops on drafter output.
6. **The audit trail matters.** Board rows persist in SQLite forever.

If *none* of those apply — it's a small one-shot reasoning task — use `delegate_task` instead or answer the user directly.

### Decomposition playbook

**Step 1 — Understand the goal.** Ask clarifying questions if the goal is ambiguous. Cheap to ask; expensive to spawn the wrong fleet.

**Step 2 — Sketch the task graph.** Before creating anything, draft the graph out loud (in your response to the user). Treat every concrete workstream as a candidate card:

1. Extract the lanes from the request.
2. Map each lane to one of the profiles you discovered earlier. If a lane doesn't fit any existing profile, ask the user which to use or create.
3. Decide whether each lane is independent or gated by another lane.
4. Create independent lanes as parallel cards with no parent links.
5. Create synthesis/review/integration cards with parent links to the lanes they depend on. A child created with unfinished parents starts in `todo`; the dispatcher promotes it to `ready` only after every parent is done.

Examples of prompts that should fan out (using placeholder profile names — substitute whatever exists on the user's setup):

- "Build an app" → one card to a design-oriented profile for product/UI direction, one or two cards to engineering profiles for implementation, plus a later integration/review card if the user has a reviewer profile.
- "Fix blockers and check model variants" → one implementation card for the blocker fixes plus one discovery/research card for config/source verification. A final reviewer card can depend on both.
- "Research docs and implement" → a docs-research card can run in parallel with a codebase-discovery card; implementation waits only if it truly needs those findings.
- "Analyze this screenshot and find the related code" → one card to a vision-capable profile for the visual analysis while another searches the codebase.

Words like "also," "finally," or "and" do not automatically imply a dependency. They often mean "make sure this is covered before reporting back." Only link tasks when one card cannot start until another card's output exists.

Show the graph to the user before creating cards. Let them correct it — including which actual profile name should own each lane.

**Step 3 — Create tasks and link.** Use the profile names from Step 0. The example below uses placeholders `<profile-A>`, `<profile-B>`, `<profile-C>` — replace them with what the user actually has.

```python
t1 = kanban_create(
    title="research: Postgres cost vs current",
    assignee="<profile-A>",
    body="Compare estimated infrastructure costs, migration costs, and ongoing ops costs over a 3-year window.",
    tenant=os.environ.get("HERMES_TENANT"),
)["task_id"]

t2 = kanban_create(
    title="research: Postgres performance vs current",
    assignee="<profile-A>",
    body="Compare query latency, throughput, and scaling at our expected volume (~500GB, 10k QPS peak).",
)["task_id"]

t3 = kanban_create(
    title="synthesize migration recommendation",
    assignee="<profile-B>",
    body="Read the findings from T1 (cost) and T2 (performance). Produce a 1-page recommendation with explicit trade-offs.",
    parents=[t1, t2],
)["task_id"]

t4 = kanban_create(
    title="draft decision memo",
    assignee="<profile-C>",
    body="Turn the analyst's recommendation into a 2-page memo for the CTO. Match prior decision memos.",
    parents=[t3],
)["task_id"]
```

`parents=[...]` gates promotion — children stay in `todo` until every parent reaches `done`, then auto-promote to `ready`. No manual coordination needed.

If the task graph has dependencies, create the parent cards first, capture their returned ids, and include those ids in the child card's `parents` list during the child `kanban_create` call. Avoid creating all cards in parallel and linking them afterward; that creates a window where the dispatcher can claim a child before its inputs exist.

**Step 4 — Complete your own task.** If you were spawned as a task yourself (e.g. a planner profile was assigned `T0: "investigate Postgres migration"`), mark it done with a summary of what you created:

```python
kanban_complete(
    summary="decomposed into T1-T4: 2 research lanes in parallel, 1 synthesis on their outputs, 1 prose draft on the recommendation",
    metadata={
        "task_graph": {
            "T1": {"assignee": "<profile-A>", "parents": []},
            "T2": {"assignee": "<profile-A>", "parents": []},
            "T3": {"assignee": "<profile-B>", "parents": ["T1", "T2"]},
            "T4": {"assignee": "<profile-C>", "parents": ["T3"]},
        },
    },
)
```

**Step 5 — Report back to the user.** Tell them what you created in plain prose, naming the actual profiles you used:

> I've queued 4 tasks:
> - **T1** (`<profile-A>`): cost comparison
> - **T2** (`<profile-A>`): performance comparison, in parallel with T1
> - **T3** (`<profile-B>`): synthesizes T1 + T2 into a recommendation
> - **T4** (`<profile-C>`): turns T3 into a CTO memo
>
> The dispatcher will pick up T1 and T2 now. T3 starts when both finish. You'll get a gateway ping when T4 completes. Use the dashboard or `hermes kanban tail <id>` to follow along.

### Common patterns

- **Fan-out + fan-in (research → synthesize):** N research-style cards with no parents, one synthesis card with all of them as parents.
- **Parallel implementation + validation:** one implementer card makes the change while one explorer/researcher card verifies config, docs, or source mapping. A reviewer card can depend on both. Do not make the implementer own unrelated verification just because the user mentioned both in one sentence.
- **Pipeline with gates:** `planner → implementer → reviewer`. Each stage's `parents=[previous_task]`. Reviewer blocks or completes; if reviewer blocks, the operator unblocks with feedback and respawns.
- **Same-profile queue:** N tasks, all assigned to the same profile, no dependencies between them. Dispatcher serializes — that profile processes them in priority order, accumulating experience in its own memory.
- **Human-in-the-loop:** Any task can `kanban_block()` to wait for input. Dispatcher respawns after `/unblock`. The comment thread carries the full context.

### Pitfalls

- **Inventing profile names that don't exist.** The dispatcher silently fails to spawn unknown assignees — the card just sits in `ready` forever. Always assign to a profile from your discovery; ask the user if you're unsure.
- **Bundling independent lanes into one card.** If the user asks for two independent outcomes, create two cards.
- **Over-linking because of wording.** "Finally check X" may still be parallel with implementation if X is static config, docs, or source discovery. Link it after implementation only when the check depends on the implementation result.
- **Forgetting dependency links.** If the task graph says `research -> implement -> review`, do not create all tasks as independent ready cards. Use parent links so implement/review cannot run before their inputs exist.
- **Reassignment vs. new task.** If a reviewer blocks with "needs changes," create a NEW task linked from the reviewer's task — don't re-run the same task with a stern look. The new task is assigned to the original implementer profile.
- **Argument order for links.** `kanban_link(parent_id=..., child_id=...)` — parent first. Mixing them up demotes the wrong task to `todo`.
- **Don't pre-create the whole graph if the shape depends on intermediate findings.** If T3's structure depends on what T1 and T2 find, let T3 exist as a "synthesize findings" task whose own first step is to read parent handoffs and plan the rest. Orchestrators can spawn orchestrators.
- **Tenant inheritance.** If `HERMES_TENANT` is set in your env, pass `tenant=os.environ.get("HERMES_TENANT")` on every `kanban_create` call so child tasks stay in the same namespace.

### Goal-mode cards (persistent workers)

By default a dispatched worker gets **one shot** at its card. For open-ended cards where one turn rarely finishes the job, pass `goal_mode=True` to wrap that worker in a Ralph-style goal loop — the same engine behind the `/goal` slash command:

```python
kanban_create(
    title="Translate the full docs site to French",
    body="Acceptance: every page translated, no English left, links intact.",
    assignee="<translator-profile>",
    goal_mode=True,        # judge re-checks the card after each turn
    goal_max_turns=15,     # optional budget (default 20)
)["task_id"]
```

How it behaves:

- After each worker turn, an auxiliary judge evaluates the worker's response against the card's **title + body** (treated as acceptance criteria).
- Not done + budget remains → the worker keeps going **in the same session** (full context retained — not a fresh respawn).
- Worker calls `kanban_complete`/`kanban_block` itself → loop stops, normal lifecycle.
- Budget exhausted without completion → the card is **blocked** for human review (sticky), never a silent exit.

When to use it: long, multi-step, or "keep going until X is true" cards. When NOT to: cheap one-shot cards (translation of a single string, a quick lookup) — the judge overhead isn't worth it, and the dispatcher's existing retry/circuit-breaker already handles transient worker failures.

Write the body as **explicit acceptance criteria** — the judge is only as good as the goal text.

### Recovering stuck workers

When a worker profile keeps crashing, hallucinating, or getting blocked by its own mistakes, the kanban dashboard flags the task with a ⚠ badge and opens a **Recovery** section in the drawer. Three primary actions:

1. **Reclaim** (or `hermes kanban reclaim <task_id>`) — abort the running worker immediately and reset the task to `ready`. Existing claim TTL is ~15 min; this is the fast path out.
2. **Reassign** (or `hermes kanban reassign <task_id> <new-profile> --reclaim`) — switch the task to a different profile (one that exists on this setup) and let the dispatcher pick it up with a fresh worker.
3. **Change profile model** — the dashboard prints a copy-paste hint for `hermes -p <profile> model` since profile config lives on disk; edit it in a terminal, then Reclaim to retry with the new model.

Hallucination warnings appear on tasks where a worker's `kanban_complete(created_cards=[...])` claim included card ids that don't exist or weren't created by the worker's profile (the gate blocks the completion), or where the free-form summary references `t_<hex>` ids that don't resolve (advisory prose scan, non-blocking). Both produce audit events that persist even after recovery actions.

---

## Section B — Worker

You are seeing this section because the Hermes Kanban dispatcher spawned you as a worker. The **lifecycle** (6 steps: orient → work → heartbeat → block/complete) also lives in the `KANBAN_GUIDANCE` block that's auto-injected into your system prompt. This section is the deeper detail.

### Workspace handling

Your workspace kind determines how you should behave inside `$HERMES_KANBAN_WORKSPACE`:

| Kind | What it is | How to work |
|---|---|---|
| `scratch` | Fresh tmp dir, yours alone | Read/write freely; it gets GC'd when the task is archived. |
| `dir:<path>` | Shared persistent directory | Other runs will read what you write. Treat it like long-lived state. Path is guaranteed absolute (the kernel rejects relative paths). |
| `worktree` | Git worktree at the resolved path | If `.git` doesn't exist, run `git worktree add <path> ${HERMES_KANBAN_BRANCH:-wt/$HERMES_KANBAN_TASK}` from the main repo first, then cd and work normally. Commit work here. |

### Tenant isolation

If `$HERMES_TENANT` is set, the task belongs to a tenant namespace. When reading or writing persistent memory, prefix memory entries with the tenant so context doesn't leak across tenants:

- Good: `business-a: Acme is our biggest customer`
- Bad (leaks): `Acme is our biggest customer`

### Good summary + metadata shapes

The `kanban_complete(summary=..., metadata=...)` handoff is how downstream workers read what you did. Patterns that work:

**Coding task:**
```python
kanban_complete(
    summary="shipped rate limiter — token bucket, keys on user_id with IP fallback, 14 tests pass",
    metadata={
        "changed_files": ["rate_limiter.py", "tests/test_rate_limiter.py"],
        "tests_run": 14,
        "tests_passed": 14,
        "decisions": ["user_id primary, IP fallback for unauthenticated requests"],
    },
)
```

**Coding task that needs human review (review-required):**

For most code-changing tasks, the work isn't truly *done* until a human reviewer has eyes on it. Block instead of complete, with `reason` prefixed `review-required: ` so the dashboard surfaces the row as needing review. Drop the structured metadata (changed files, test counts, diff/PR url) into a comment first, since `kanban_block` only carries the human-readable reason — comments are the durable annotation channel. Reviewer either approves and runs `hermes kanban unblock <id>` (which re-spawns you with the comment thread for any follow-ups) or asks for changes via another comment.

```python
import json

kanban_comment(
    body="review-required handoff:\n" + json.dumps({
        "changed_files": ["rate_limiter.py", "tests/test_rate_limiter.py"],
        "tests_run": 14,
        "tests_passed": 14,
        "diff_path": "/path/to/worktree",
        "decisions": ["user_id primary, IP fallback for unauthenticated requests"],
    }, indent=2),
)
kanban_block(
    reason="review-required: rate limiter shipped, 14/14 tests pass — needs eyes on the user_id/IP fallback choice before merging",
)
```

Use `kanban_complete` only when the task is genuinely terminal — e.g. a one-line typo fix, a docs change with no functional consequences, or a research task where the artifact IS the writeup itself.

**Research task:**
```python
kanban_complete(
    summary="3 competing libraries reviewed; vLLM wins on throughput, SGLang on latency, Tensorrt-LLM on memory efficiency",
    metadata={
        "sources_read": 12,
        "recommendation": "vLLM",
        "benchmarks": {"vllm": 1.0, "sglang": 0.87, "trtllm": 0.72},
    },
)
```

**Review task:**
```python
kanban_complete(
    summary="reviewed PR #123; 2 blocking issues found (SQL injection in /search, missing CSRF on /settings)",
    metadata={
        "pr_number": 123,
        "findings": [
            {"severity": "critical", "file": "api/search.py", "line": 42, "issue": "raw SQL concat"},
            {"severity": "high", "file": "api/settings.py", "issue": "missing CSRF middleware"},
        ],
        "approved": False,
    },
)
```

Shape `metadata` so downstream parsers (reviewers, aggregators, schedulers) can use it without re-reading your prose.

### Claiming cards you actually created

If your run produced new kanban tasks (via `kanban_create`), pass the ids in `created_cards` on `kanban_complete`. The kernel verifies each id exists and was created by your profile; any phantom id blocks the completion with an error listing what went wrong, and the rejected attempt is permanently recorded on the task's event log. **Only list ids you captured from a successful `kanban_create` return value — never invent ids from prose, never paste ids from earlier runs, never claim cards another worker created.**

```python
# GOOD — capture return values, then claim them.
c1 = kanban_create(title="remediate SQL injection", assignee="security-worker")
c2 = kanban_create(title="fix CSRF middleware", assignee="web-worker")

kanban_complete(
    summary="Review done; spawned remediations for both findings.",
    metadata={"pr_number": 123, "approved": False},
    created_cards=[c1["task_id"], c2["task_id"]],
)
```

```python
# BAD — claiming ids you don't have captured return values for.
kanban_complete(
    summary="Created remediation cards t_a1b2c3d4, t_deadbeef",  # hallucinated
    created_cards=["t_a1b2c3d4", "t_deadbeef"],                   # → gate rejects
)
```

If a `kanban_create` call fails (exception, tool_error), the card was NOT created — do not include a phantom id for it. Retry the create, or omit the id and mention the failure in your summary. The prose-scan pass also catches `t_<hex>` references in your free-form summary that don't resolve; these don't block the completion but show up as advisory warnings on the task in the dashboard.

### Block reasons that get answered fast

Bad: `"stuck"` — the human has no context.

Good: one sentence naming the specific decision you need. Leave longer context as a comment instead.

```python
kanban_comment(
    task_id=os.environ["HERMES_KANBAN_TASK"],
    body="Full context: I have user IPs from Cloudflare headers but some users are behind NATs with thousands of peers. Keying on IP alone causes false positives.",
)
kanban_block(reason="Rate limit key choice: IP (simple, NAT-unsafe) or user_id (requires auth, skips anonymous endpoints)?")
```

The block message is what appears in the dashboard / gateway notifier. The comment is the deeper context a human reads when they open the task.

### Heartbeats worth sending

Good heartbeats name progress: `"epoch 12/50, loss 0.31"`, `"scanned 1.2M/2.4M rows"`, `"uploaded 47/120 videos"`.
Bad heartbeats: `"still working"`, empty notes, sub-second intervals. Every few minutes max; skip entirely for tasks under ~2 minutes.

### Retry scenarios

If you open the task and `kanban_show` returns `runs: [...]` with one or more closed runs, you're a retry. The prior runs' `outcome` / `summary` / `error` tell you what didn't work. Don't repeat that path. Typical retry diagnostics:

- `outcome: "timed_out"` — the previous attempt hit `max_runtime_seconds`. You may need to chunk the work or shorten it.
- `outcome: "crashed"` — OOM or segfault. Reduce memory footprint.
- `outcome: "spawn_failed"` + `error: "..."` — usually a profile config issue (missing credential, bad PATH). Ask the human via `kanban_block` instead of retrying blindly.
- `outcome: "reclaimed"` + `summary: "task archived..."` — operator archived the task out from under the previous run; you probably shouldn't be running at all, check status carefully.
- `outcome: "blocked"` — a previous attempt blocked; the unblock comment should be in the thread by now.

### Notification routing

You can configure the gateway to receive cross-profile Kanban task notifications by adding `notification_sources` to `~/.hermes/config.yaml`.

- `notification_sources: ['*']` accepts subscriptions from all profiles.
- `notification_sources: ['default', 'zilor-ppt']` or `"default,zilor-ppt"` restricts subscriptions to specified profiles.
- Omitting the key keeps the default behavior (profile isolation).

### Do NOT

- Call `delegate_task` as a substitute for `kanban_create`. `delegate_task` is for short reasoning subtasks inside YOUR run; `kanban_create` is for cross-agent handoffs that outlive one API loop.
- Call `clarify` to ask the human a question. You are running headless — there is no live user to answer. The call will time out (default ~120s) and the task will sit silently in `running` with no signal that it needs input. Use `kanban_comment` (context) + `kanban_block(reason=...)` (decision needed) instead.
- Modify files outside `$HERMES_KANBAN_WORKSPACE` unless the task body says to.
- Create follow-up tasks assigned to yourself — assign to the right specialist.
- Complete a task you didn't actually finish. Block it instead.

### Pitfalls

- **Task state can change between dispatch and your startup.** Between when the dispatcher claimed and when your process actually booted, the task may have been blocked, reassigned, or archived. Always `kanban_show` first. If it reports `blocked` or `archived`, stop — you shouldn't be running.
- **Workspace may have stale artifacts.** Especially `dir:` and `worktree` workspaces can have files from previous runs. Read the comment thread — it usually explains why you're running again and what state the workspace is in.
- **Don't rely on the CLI when the guidance is available.** The `kanban_*` tools work across all terminal backends (Docker, Modal, SSH). `hermes kanban <verb>` from your terminal tool will fail in containerized backends because the CLI isn't installed there. When in doubt, use the tool.

### CLI fallback (for scripting)

Every tool has a CLI equivalent for human operators and scripts:

- `kanban_show` ↔ `hermes kanban show <id> --json`
- `kanban_complete` ↔ `hermes kanban complete <id> --summary "..." --metadata '{...}'`
- `kanban_block` ↔ `hermes kanban block <id> "reason"`
- `kanban_create` ↔ `hermes kanban create "title" --assignee <profile> [--parent <id>]`
- etc.

Use the tools from inside an agent; the CLI exists for the human at the terminal.

---

## Section C — Codex lane (optional)

Use when a Hermes Kanban worker wants to run Codex CLI as an isolated implementation lane while Hermes keeps ownership of task lifecycle, reconciliation, testing, and handoff. **Hermes is always the task owner.** Codex is an input lane only.

### When to use the Codex lane

Use the Codex lane when ALL of these are true:

- The Kanban task is a coding, refactor, documentation, test, or mechanical migration task with clear acceptance criteria.
- A bounded diff can be evaluated by Hermes in one run.
- The repo can be copied or checked out in an isolated git worktree/branch.
- Hermes can run the relevant tests itself after Codex exits.
- The prompt can state all safety constraints and files that must not change.

Do not use the Codex lane when any of these are true:

- The task requires human judgment that is not already captured in the Kanban body.
- The worker lacks repo access, Codex auth, or time to reconcile the result.
- The change touches secrets, credential stores, private user data, or production order-entry systems.
- A small direct edit is faster and safer than spawning another agent.
- The task is research-only and should produce a written handoff rather than a diff.
- The worker would be tempted to mark Done based only on Codex self-report.

### Ownership Rules

1. **Hermes owns the Kanban lifecycle.** Codex must never call `kanban_complete`, `kanban_block`, `kanban_create`, gateway messaging, or any Hermes board CLI as a substitute for the worker.
2. **Hermes owns final acceptance.** Treat Codex commits/diffs as untrusted patches until reviewed and verified.
3. **Hermes owns test execution.** Codex may run tests, but those runs are advisory; repeat required verification from Hermes with the repo's canonical wrapper.
4. **Hermes owns safety.** If Codex changes safety boundaries, risk gates, live trading behavior, or secrets handling, reject the lane even if tests pass.
5. **Hermes owns cleanup.** Kill stuck Codex processes and remove temporary worktrees when they are no longer needed.

### Required Worktree and Branch Pattern

Never run Codex directly in a shared dirty checkout. Use a branch/worktree name that ties the lane to the Kanban task and keeps untrusted edits isolated.

Recommended variables:

```bash
TASK_ID="${HERMES_KANBAN_TASK:-t_manual}"
REPO="/path/to/repo"
BASE="$(git -C "$REPO" rev-parse --abbrev-ref HEAD)"
SAFE_TASK="$(printf '%s' "$TASK_ID" | tr -cd '[:alnum:]_-')"
BRANCH="codex/${SAFE_TASK}/$(date -u +%Y%m%d%H%M%S)"
WORKTREE="/tmp/${SAFE_TASK}-codex-lane"
```

Create the isolated lane:

```bash
git -C "$REPO" fetch --all --prune
git -C "$REPO" worktree add -b "$BRANCH" "$WORKTREE" "$BASE"
git -C "$WORKTREE" status --short --branch
```

If the current Kanban workspace is already an isolated git worktree created for this task, you may create a sibling Codex branch inside it only if `git status --short` is clean except for intentional Hermes edits. Otherwise create a separate temporary worktree and cherry-pick or copy accepted commits back after reconciliation.

Cleanup after reconciliation:

```bash
git -C "$REPO" worktree remove "$WORKTREE"
git -C "$REPO" branch -D "$BRANCH"  # only after accepted commits were copied/cherry-picked or intentionally rejected
```

Keep the worktree if it is needed as an artifact for review; record it in `codex_lane.artifacts` and mention it in the handoff.

### Codex Capability Checks

Run these before spawning Codex. Missing Codex is a normal reason to skip the lane, not a task blocker if Hermes can do the task directly.

```bash
command -v codex
codex --version
codex features list | grep -i goals || true
```

If `/goal` support is required, enable or launch with the feature flag only after checking availability:

```bash
codex features enable goals || true
codex --enable goals --version
```

Authentication can be via `OPENAI_API_KEY` or the Codex CLI OAuth state (often `~/.codex/auth.json`). Do not print token files. A missing `OPENAI_API_KEY` is not proof that auth is unavailable.

### Mode Selection

Use `codex exec` for bounded one-shot edits where Codex should exit on its own:

```python
terminal(
    command="codex exec --full-auto '$(cat /tmp/codex_prompt.md)'",
    workdir=WORKTREE,
    background=True,
    pty=True,
    notify_on_complete=True,
)
```

Use Codex `/goal` only for broader multi-step work that benefits from durable objective tracking. Launch interactively in a PTY/tmux session or with `codex --enable goals` if the feature is disabled by default.

Do not use `--yolo` for prediction-market-bot or safety-sensitive repos. Prefer `--full-auto` inside the isolated worktree, then rely on Hermes reconciliation.

### Prompt Construction

Use the linked template at `templates/pmb-codex-lane-prompt.md` for prediction-market-bot work. For other repos, keep the same structure and replace the PMB-specific safety block with repo-specific invariants.

Every Codex prompt must include:

- `task_id`, title, and full Kanban acceptance criteria.
- Repo path, worktree path, branch name, and allowed file scope.
- Explicit statement: Hermes owns Kanban lifecycle; Codex is an input lane only.
- Required output: concise summary, files changed, commits, tests run, and known risks.
- Prohibited actions: secrets access, external messaging, board mutation, unrelated refactors, dependency upgrades unless required.
- Verification commands Codex may run and commands Hermes will run afterward.

For PMB, include the mandatory safety constraints verbatim (see the template).

### Monitoring, Timeout, and Kill Behavior

Start long Codex lanes in the background with PTY and completion notification:

```python
result = terminal(
    command="codex exec --full-auto '$(cat /tmp/codex_prompt.md)'",
    workdir=WORKTREE,
    background=True,
    pty=True,
    notify_on_complete=True,
)
session_id = result["session_id"]
```

Monitor without interfering:

```python
process(action="poll", session_id=session_id)
process(action="log", session_id=session_id, limit=200)
process(action="wait", session_id=session_id, timeout=300)
```

Send a Kanban heartbeat every few minutes for lanes longer than two minutes, e.g. `kanban_heartbeat(note="Codex lane running in <WORKTREE>; waiting for tests/diff")`.

Kill conditions:

- No useful output for the task's remaining runtime budget.
- Codex requests secrets, production credentials, or external permissions.
- Codex attempts to modify files outside the worktree.
- Codex starts unrelated rewrites or dependency churn.
- Codex is still running near the worker timeout and no safe partial artifact exists.

Kill command:

```python
process(action="kill", session_id=session_id)
```

After kill, inspect `git status --short`, preserve useful patches only if safe, and record `codex_lane.result: timed_out` or `rejected` with a concrete `rejected_reason`.

### Reconciliation Checklist

Hermes must perform this checklist before accepting any Codex lane result:

- [ ] `git -C <WORKTREE> status --short --branch` shows only expected files.
- [ ] `git -C <WORKTREE> diff --stat` and `git diff` were reviewed by Hermes.
- [ ] No secrets, credentials, generated caches, unrelated data, or local artifacts are included.
- [ ] PMB safety constraints were preserved: no live REST order entry, no market orders, no execution crossing, no fake passive fills/PnL, no risk-gate weakening, no secrets.
- [ ] Codex commits are small enough to cherry-pick or squash cleanly.
- [ ] Hermes ran the canonical tests itself, using `scripts/run_tests.sh` for Hermes Agent or the repo's documented wrapper for other repos.
- [ ] Any Codex-run tests are listed separately from Hermes-run tests.
- [ ] Accepted commits/diffs were applied to the Hermes-owned workspace/branch.
- [ ] Rejected or partial work has a concrete reason and artifact path if useful.

Acceptance outcomes:

- `accepted`: Codex diff/commits were reviewed, applied, and verified.
- `partial`: Some Codex work was accepted after edits or cherry-picks; rejected parts are documented.
- `rejected`: No Codex changes were accepted; reason is documented.
- `timed_out`: Codex exceeded the lane budget; useful artifacts may or may not exist.

### kanban_complete Metadata Schema

Include this object under `metadata.codex_lane` for every task where the lane was considered. If Codex was not used, set `used: false` and explain why in `rejected_reason` or a sibling `notes` field.

```json
{
  "codex_lane": {
    "used": true,
    "mode": "exec | goal | skipped",
    "worktree": "/absolute/path/to/codex/worktree",
    "branch": "codex/t_caa69668/20260508100000",
    "command": "codex exec --full-auto ...",
    "result": "accepted | rejected | partial | timed_out",
    "accepted_commits": ["<sha1>", "<sha2>"],
    "rejected_reason": "empty when fully accepted; otherwise concrete reason",
    "tests_run": [
      {"command": "scripts/run_tests.sh tests/tools/test_x.py", "exit_code": 0, "owner": "hermes"},
      {"command": "codex-reported: npm test", "exit_code": 0, "owner": "codex"}
    ],
    "artifacts": ["/absolute/path/to/log-or-patch"]
  }
}
```

For tasks that intentionally skip Codex:

```json
{
  "codex_lane": {
    "used": false,
    "mode": "skipped",
    "worktree": null,
    "branch": null,
    "command": null,
    "result": "rejected",
    "accepted_commits": [],
    "rejected_reason": "Direct Hermes edit was smaller and safer than spawning Codex.",
    "tests_run": [],
    "artifacts": []
  }
}
```

### Common Pitfalls

1. Treating Codex self-report as verification. Always inspect the diff and rerun tests from Hermes.
2. Running Codex in the user's dirty main checkout. Always isolate in a worktree/branch.
3. Letting Codex own Kanban. Codex may summarize progress, but Hermes writes board state.
4. Forgetting PMB safety invariants in the prompt. Missing safety text is a lane setup failure.
5. Using `/goal` for quick edits. Prefer `codex exec` unless durable multi-step continuation is needed.
6. Killing a stuck lane without recording why. `rejected_reason` must explain the decision.
7. Accepting broad unrelated cleanup because tests pass. Reject or cherry-pick only the scoped changes.

### Verification Checklist

- [ ] Codex was skipped or started only after `command -v codex`, `codex --version`, and optional goals feature checks.
- [ ] Codex ran only in an isolated worktree/branch.
- [ ] Prompt included task scope, ownership rules, PMB safety constraints when applicable, and verification commands.
- [ ] Hermes reviewed `git diff` and safety-sensitive files.
- [ ] Hermes ran canonical tests independently.
- [ ] `kanban_complete.metadata.codex_lane` follows the schema above.
- [ ] Temporary processes and unnecessary worktrees were cleaned up.

---

## Templates

- [`templates/pmb-codex-lane-prompt.md`](templates/pmb-codex-lane-prompt.md) — Codex prompt template for prediction-market-bot tasks (mandatory PMB safety block). Copy and fill every bracketed field before launching Codex.