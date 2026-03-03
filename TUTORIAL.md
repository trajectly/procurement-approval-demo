# Tutorial: End-to-End Trajectly PR Regression Workflow (Procurement, Declarative Graph)

This tutorial walks through the full regression lifecycle using the declarative graph SDK (`trajectly.App`) in a procurement approval workflow.

You will:
1. run baseline (PASS)
2. run intentional regression (FAIL)
3. triage with report/repro/shrink
4. run determinism break/fix
5. simulate a risky PR-style graph change and restore green

## Step 0: Setup

```bash
git clone https://github.com/trajectly/procurement-approval-demo.git
cd procurement-approval-demo

python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Optional dashboard setup

```bash
cd ..
git clone https://github.com/trajectly/trajectly-dashboard-local.git
cd trajectly-dashboard-local
npm install
printf "VITE_DATA_DIR=%s/.trajectly/reports\n" "$(pwd)/../procurement-approval-demo" > .env.local
npm run dev &
cd ../procurement-approval-demo
```

Dashboard URL: <http://localhost:5173/dashboard>

## Step 1: Understand the graph layout

Core graph module:
- `agents/procurement_graph.py`

Spec entrypoints:
- baseline -> `agents/procurement_agent.py`
- regression -> `agents/procurement_agent_regression.py`
- determinism break -> `agents/procurement_agent_determinism_break.py`
- determinism fix -> `agents/procurement_agent_determinism_fix.py`

## Step 2: Initialize and record baseline

```bash
python -m trajectly init
python -m trajectly record specs/trt-procurement-agent-baseline.agent.yaml --project-root .
python -m trajectly run specs/trt-procurement-agent-baseline.agent.yaml --project-root .
```

Expected: PASS (`0`).

## Step 3: Run intentional regression variant

```bash
python -m trajectly run specs/trt-procurement-agent-regression.agent.yaml --project-root .
```

Expected: FAIL (`1`).

Expected failure includes denied/forbidden direct-award path and missing required approval path.

## Step 4: Triage from CLI

```bash
python -m trajectly report
python -m trajectly repro
python -m trajectly shrink
```

Expected exit behavior:
- `report` -> `0`
- `repro` -> `1`
- `shrink` -> `0`

## Step 5: Determinism break and fix

### 5.1 Determinism break (expected fail)

```bash
python -m trajectly record specs/trt-procurement-agent-determinism-break.agent.yaml --project-root .
python -m trajectly run specs/trt-procurement-agent-determinism-break.agent.yaml --project-root .
```

Expected: FAIL (`1`).

### 5.2 Determinism fix (expected pass)

```bash
python -m trajectly record specs/trt-procurement-agent-determinism-fix.agent.yaml --project-root .
python -m trajectly run specs/trt-procurement-agent-determinism-fix.agent.yaml --project-root .
```

Expected: PASS (`0`).

## Step 6: Simulate risky PR change in graph baseline logic

Edit `agents/procurement_graph.py`.

Find `choose_procurement_action_node(...)` and temporarily add:

```python
if int(requisition["amount_usd"]) <= 200000:
    decision["action"] = "direct_award"
    decision["vendor_id"] = "vendor-b"
```

Now run baseline spec:

```bash
python -m trajectly run specs/trt-procurement-agent-baseline.agent.yaml --project-root .
```

Expected: FAIL (`1`).

This mirrors a subtle policy bypass that may look like a throughput optimization in review.

## Step 7: Revert and confirm green

Remove the override added in Step 6, then run:

```bash
python -m trajectly run specs/trt-procurement-agent-baseline.agent.yaml --project-root .
```

Expected: PASS (`0`).

## Step 8: Baseline lifecycle commands (intentional behavior changes)

Use only for approved intentional behavior changes:

```bash
python -m trajectly baseline create --name v2 specs/trt-procurement-agent-baseline.agent.yaml --project-root .
python -m trajectly baseline diff trt-procurement-agent v1 v2 --project-root . --json
python -m trajectly baseline promote v2 specs/trt-procurement-agent-baseline.agent.yaml --project-root .
```

## Step 9: CI/PR loop

Workflow file: `.github/workflows/trajectly.yml`

The workflow verifies scenarios, runs baseline replay gate, posts PR report comment, uploads artifacts, and fails on regression.

To replicate CI locally:

```bash
bash scripts/verify_demo.sh
```

## Step 10: Optional live OpenAI recording

Default demo mode is deterministic mock LLM.

For live OpenAI recording:

```bash
export OPENAI_API_KEY="sk-..."
export TRAJECTLY_DEMO_USE_OPENAI=1
python -m trajectly record specs/trt-procurement-agent-baseline.agent.yaml --project-root .
```

Replay remains fixture-based and deterministic.
