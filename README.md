# Procurement Approval Demo for Trajectly (Declarative Graph)

This demo shows how a procurement workflow built with `trajectly.App` can be regression-tested with deterministic replay and CI gating.

You will:
- run baseline graph behavior
- run intentional policy regression
- run determinism break/fix variants
- inspect report/repro/shrink and CI artifacts

## Dependency note

`requirements.txt` installs Trajectly directly from PyPI (`trajectly==0.4.1`).
This release includes declarative graph SDK support (`trajectly.App`, `trajectly.sdk.graph`).

## Setup

```bash
git clone https://github.com/trajectly/procurement-approval-demo.git
cd procurement-approval-demo

python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Graph architecture in this demo

Main graph builder:
- `agents/procurement_graph.py`

Thin entry modules used by specs:
- `agents/procurement_agent.py` -> baseline mode
- `agents/procurement_agent_regression.py` -> regression mode
- `agents/procurement_agent_determinism_break.py` -> determinism-break mode
- `agents/procurement_agent_determinism_fix.py` -> determinism-fix mode

The graph preserves contract-relevant tool names:
- `fetch_requisition`
- `fetch_vendor_quotes`
- `route_for_approval`
- `create_purchase_order`
- `unsafe_direct_award`
- `sample_random_score` (determinism-fix)

## Run baseline

```bash
python -m trajectly init
python -m trajectly record specs/trt-procurement-agent-baseline.agent.yaml --project-root .
python -m trajectly run specs/trt-procurement-agent-baseline.agent.yaml --project-root .
```

Expected: `PASS` (exit code `0`).

## Run intentional regression

```bash
python -m trajectly run specs/trt-procurement-agent-regression.agent.yaml --project-root .
```

Expected: `FAIL` (exit code `1`).

## Determinism scenarios

Break (expected fail):

```bash
python -m trajectly record specs/trt-procurement-agent-determinism-break.agent.yaml --project-root .
python -m trajectly run specs/trt-procurement-agent-determinism-break.agent.yaml --project-root .
```

Fix (expected pass):

```bash
python -m trajectly record specs/trt-procurement-agent-determinism-fix.agent.yaml --project-root .
python -m trajectly run specs/trt-procurement-agent-determinism-fix.agent.yaml --project-root .
```

## Triage commands

```bash
python -m trajectly report
python -m trajectly repro
python -m trajectly shrink
```

## CI workflow

`.github/workflows/trajectly.yml` runs:
1. `bash scripts/verify_demo.sh`
2. baseline replay gate
3. report generation + PR comment
4. artifact upload
5. fail job on regression

## One-command local verification

```bash
bash scripts/verify_demo.sh
```

## Optional live OpenAI recording

Default mode uses deterministic mock LLM responses.

For live OpenAI recording:

```bash
export OPENAI_API_KEY="sk-..."
export TRAJECTLY_DEMO_USE_OPENAI=1
python -m trajectly record specs/trt-procurement-agent-baseline.agent.yaml --project-root .
```

Replay remains fixture-based and deterministic.

For the full end-to-end walkthrough (including PR fail/fix loop), see [TUTORIAL.md](TUTORIAL.md).
