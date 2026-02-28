# Procurement Approval Demo for Trajectly

This demo shows why Trajectly belongs in CI for procurement agents.

You will record a baseline, introduce a subtle "looks safe" code change that
silently bypasses mandatory approval routing, and watch Trajectly catch it --
locally, in CI, and in the local dashboard with deterministic repro artifacts.

## 1. Setup

```bash
git clone https://github.com/trajectly/procurement-approval-demo.git
cd procurement-approval-demo

python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 2. Set up the local dashboard

Set up the dashboard now so you can visualize every step that follows.

```bash
cd ..
git clone https://github.com/trajectly/trajectly-dashboard-local.git
cd trajectly-dashboard-local
npm install
cd ../procurement-approval-demo
```

You now have two sibling directories: `procurement-approval-demo/` and
`trajectly-dashboard-local/`. The dashboard reads report JSON directly from
this repo -- no cloud services and no login.

Configure the dashboard once:

```bash
printf "VITE_DATA_DIR=%s/.trajectly/reports\n" "$(pwd)" > ../trajectly-dashboard-local/.env.local
```

## 3. Record baseline and view in dashboard

```bash
python -m trajectly init
python -m trajectly record specs/trt-procurement-agent-baseline.agent.yaml --project-root .
python -m trajectly run specs/trt-procurement-agent-baseline.agent.yaml --project-root .
```

Expected: `PASS` (exit code `0`).

Start the dashboard:

```bash
cd ../trajectly-dashboard-local
nohup npm run dev -- --host 127.0.0.1 >/tmp/trajectly-dashboard.log 2>&1 &
cd ../procurement-approval-demo
```

Open **http://localhost:5173/dashboard**. You should see:

- **Procurement Approval Agent** with status **PASS**
- **Agent Flow Graph** includes: `fetch_requisition` -> `fetch_vendor_quotes` -> `route_for_approval` -> `create_purchase_order`
- The trace timeline shows ordered event execution
- Contract summary shows all checks passed

## 4. Introduce regression and see what Trajectly catches

```bash
python -m trajectly run specs/trt-procurement-agent-regression.agent.yaml --project-root .
```

Expected: `FAIL` (exit code `1`).

Refresh **http://localhost:5173/dashboard**. You should now see a failed run.

At the witness step, violation details should include:

- `CONTRACT_TOOL_DENIED` for `unsafe_direct_award`
- `REFINEMENT_BASELINE_CALL_MISSING` for `route_for_approval`
- `REFINEMENT_EXTRA_TOOL_CALL` / `REFINEMENT_NEW_TOOL_NAME_FORBIDDEN`

This mirrors a realistic procurement regression: a fast-track optimization that
looks operationally beneficial but bypasses mandatory approval controls.

## 5. CLI deep dive: report, repro, shrink

```bash
python -m trajectly report
```

Shows failing spec, witness index, and repro command.

```bash
python -m trajectly repro
```

Replays the exact failing trace deterministically from fixtures.

```bash
python -m trajectly shrink
```

Minimizes the failing trace to the shortest reproducing prefix.

### Generated files

Trajectly writes artifacts under `.trajectly/reports/`:

| File | What it contains |
|------|------------------|
| `latest.json` | Machine-readable roll-up of latest run |
| `trt-procurement-agent.json` | Full TRT report, witness, violations, repro command |
| `trt-procurement-agent.md` | Human-readable markdown report |
| `latest.md` | Human-readable summary for all processed specs |

Useful JSON fields include:

- `baseline_skeleton` / `current_skeleton`
- `all_violations_at_witness[]`
- `primary_violation`
- `repro_command`

## 6. CI integration

The included `.github/workflows/trajectly.yml` runs on pushes to `main` and PRs
targeting `main`. It:

1. Installs dependencies
2. Runs `python -m trajectly init` + baseline replay
3. Generates a PR comment via `python -m trajectly report --pr-comment`
4. Uploads `.trajectly/` artifacts
5. Fails CI if a regression is detected

See [TUTORIAL.md](TUTORIAL.md) for the full branch/PR fail-and-fix workflow.

## Repo layout

```text
agents/
  procurement_agent.py             # baseline behavior
  procurement_agent_regression.py  # intentionally regressed variant
  procurement_tools.py             # tools + LLM wrapper
specs/
  trt-procurement-agent-baseline.agent.yaml
  trt-procurement-agent-regression.agent.yaml
.github/workflows/trajectly.yml
TUTORIAL.md
```

## Optional: live OpenAI recording

The demo works fully offline with deterministic mock LLM fixtures. To record
with live OpenAI responses:

```bash
export OPENAI_API_KEY="sk-..."
export TRAJECTLY_DEMO_USE_OPENAI=1
python -m trajectly record specs/trt-procurement-agent-baseline.agent.yaml --project-root .
```

After recording, subsequent `python -m trajectly run` calls replay from
fixtures, fully offline and deterministic.
