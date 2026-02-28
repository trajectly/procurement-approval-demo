# Tutorial: End-to-End Trajectly PR Regression Workflow (Procurement)

This tutorial walks through every Trajectly feature using a procurement approval
agent. By the end you will have:

- Recorded a behavioral baseline
- Viewed it in the local dashboard
- Introduced a subtle regression and watched Trajectly catch it
- Used report/repro/shrink to debug and minimize the failure
- Simulated the exact PR workflow that Trajectly gates in CI
- Fixed the regression and turned CI green

## What Trajectly does under the hood

For each run, Trajectly:

1. Captures normalized trace events (`tool_called`, `llm_called`, etc.).
2. Extracts the tool-call skeleton (ordered list of tool names).
3. Checks contracts (allow/deny lists, required sequences, budget limits).
4. Checks behavioral refinement against the recorded baseline.
5. Returns PASS/FAIL with witness step and deterministic artifacts.

---

## Step 0: Environment and dashboard setup

### 0.1 Python environment

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 0.2 Local dashboard

Set up the dashboard now so you can visualize results throughout the tutorial.

```bash
cd ..
git clone https://github.com/trajectly/trajectly-dashboard-local.git
cd trajectly-dashboard-local
npm install
cd ../procurement-approval-demo
```

You now have two sibling directories. Configure the dashboard once:

```bash
printf "VITE_DATA_DIR=%s/.trajectly/reports\n" "$(pwd)" > ../trajectly-dashboard-local/.env.local
```

---

## Step 1: Initialize and record baseline

```bash
python -m trajectly init
python -m trajectly record specs/trt-procurement-agent-baseline.agent.yaml --project-root .
```

This executes `agents/procurement_agent.py`, captures tool/LLM behavior, and
stores baseline + fixtures under `.trajectly/`.

### Verify baseline passes

```bash
python -m trajectly run specs/trt-procurement-agent-baseline.agent.yaml --project-root .
```

Expected: `PASS` (exit code `0`).

---

## Step 2: View baseline in dashboard

Start the dashboard:

```bash
cd ../trajectly-dashboard-local && npm run dev &
sleep 2
cd ../procurement-approval-demo
```

Open **http://localhost:5173/dashboard**.

What you should see:

- **Procurement Approval Agent** -- status **PASS**
- Tool flow includes `fetch_requisition` -> `fetch_vendor_quotes` -> `route_for_approval` -> `create_purchase_order`
- Trace timeline with ordered events and timing
- Contract summary passing

---

## Step 3: Run the intentionally regressed variant

The repo includes `agents/procurement_agent_regression.py`, which adds a
fast-track override that bypasses approval routing:

```python
if requisition["amount_usd"] <= 200000:
    decision["action"] = "direct_award"
    decision["vendor_id"] = "vendor-b"
```

Run it:

```bash
python -m trajectly run specs/trt-procurement-agent-regression.agent.yaml --project-root .
```

Expected: `FAIL` (exit code `1`).

At the witness step, violations include:

- `CONTRACT_TOOL_DENIED` (`unsafe_direct_award`)
- `CONTRACT_TOOL_NOT_ALLOWED` (`unsafe_direct_award`)
- `REFINEMENT_BASELINE_CALL_MISSING` (`route_for_approval`)
- `REFINEMENT_EXTRA_TOOL_CALL` / `REFINEMENT_NEW_TOOL_NAME_FORBIDDEN`

---

## Step 4: View the regression in dashboard

Refresh **http://localhost:5173/dashboard**.

What changed:

- **Status: FAIL** with witness index
- Agent flow now shows the missing approval path and denied direct-award call
- Violation section lists witness-step refinement + contract failures

---

## Step 5: CLI deep dive -- report, repro, shrink

### report

```bash
python -m trajectly report
```

Shows failing spec, witness index, violations, and repro command.

### repro

```bash
python -m trajectly repro
```

Replays the exact failing trace deterministically from fixtures.

### shrink

```bash
python -m trajectly shrink
```

Minimizes the trace to the shortest reproducing prefix.

### Generated files reference

| File | Contents |
|------|----------|
| `.trajectly/reports/latest.json` | Latest run roll-up |
| `.trajectly/reports/trt-procurement-agent.json` | Full TRT report |
| `.trajectly/reports/trt-procurement-agent.md` | Human-readable report |
| `.trajectly/baselines/trt-procurement-agent.jsonl` | Recorded baseline trace |
| `.trajectly/fixtures/trt-procurement-agent.json` | Fixture replay data |

---

## Step 6: Simulate regression on baseline code (the PR scenario)

In CI, the baseline spec (`specs/trt-procurement-agent-baseline.agent.yaml`) is
always executed. To simulate a risky PR, edit the baseline agent code.

Open `agents/procurement_agent.py`. Find:

```python
    decision = choose_procurement_action(recommendation, default_vendor="vendor-c")

    if decision["action"] == "route_approval":
```

Replace with:

```python
    decision = choose_procurement_action(recommendation, default_vendor="vendor-c")

    # Fast-track: bypass approval for <= 200k requests
    if requisition["amount_usd"] <= 200000:
        decision["action"] = "direct_award"
        decision["vendor_id"] = "vendor-b"

    if decision["action"] == "route_approval":
```

Now run baseline spec again:

```bash
python -m trajectly run specs/trt-procurement-agent-baseline.agent.yaml --project-root .
```

Expected: `FAIL` (exit code `1`).

Refresh dashboard and confirm FAIL is visible.

---

## Step 7: Fix via Trajectly loop

Remove the 3-line fast-track override from `agents/procurement_agent.py`, then:

```bash
python -m trajectly run specs/trt-procurement-agent-baseline.agent.yaml --project-root .
```

Expected: `PASS` (exit code `0`).

Refresh dashboard and confirm it returns to green.

---

## Step 8: Intentional behavior changes

If behavior changes are intentional and approved, update baseline explicitly:

```bash
python -m trajectly baseline update specs/trt-procurement-agent-baseline.agent.yaml
```

Use this only with explicit review sign-off.

---

## Step 9: CI/PR loop on GitHub

### 9.1 Publish your own copy

If you cloned this demo, do not `git init` again. Create a private copy:

```bash
gh auth status
git remote rename origin upstream
gh repo create <your-org>/procurement-approval-demo --private --source=. --remote=origin --push
gh repo set-default <your-org>/procurement-approval-demo
```

### 9.2 Create a subtle regression PR

```bash
REGRESSION_BRANCH="feat/pr-procurement-regression-$(whoami)"
git checkout -b "$REGRESSION_BRANCH"
```

Inject the fast-track override from Step 6 into `agents/procurement_agent.py`.

Before pushing, confirm local failure:

```bash
python -m trajectly run specs/trt-procurement-agent-baseline.agent.yaml --project-root .
```

Commit and push:

```bash
git add agents/procurement_agent.py
git commit -m "perf: fast-track low-value procurement routing"
git push -u origin "$REGRESSION_BRANCH"

gh pr create \
  --title "perf: fast-track low-value procurement routing" \
  --body "Optimize procurement cycle time for smaller requests."

sleep 8
gh pr checks --watch
```

Expected: **Trajectly Agent Regression Tests** fails.

### 9.3 Fix and verify green

Remove the override, then:

```bash
python -m trajectly run specs/trt-procurement-agent-baseline.agent.yaml --project-root .
git add agents/procurement_agent.py
git commit -m "fix: restore approval routing policy"
git push
sleep 8
gh pr checks --watch
```

Expected: CI turns green.

### 9.4 Enforce merge blocking (required for real gating)

To ensure failing checks block merge:

1. Go to `Settings` -> `Branches`.
2. Add/edit branch protection rule for `main`.
3. Enable **Require status checks to pass before merging**.
4. Select **Trajectly Agent Regression Tests** as a required check.
5. Save changes.

If required checks are not available in your private repo plan, validate check
status manually before merge.

---

## CI workflow reference

`.github/workflows/trajectly.yml`:

1. Installs dependencies
2. Runs `python -m trajectly init` + baseline spec replay
3. Builds PR comment markdown from `python -m trajectly report --pr-comment`
4. Uploads `.trajectly/**` artifacts
5. Fails on regression verdict
