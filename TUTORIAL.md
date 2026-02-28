# Tutorial: Procurement Approval Regression Loop

## Step 0: Environment

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Step 1: Record baseline

```bash
python -m trajectly init
python -m trajectly record specs/trt-procurement-agent-baseline.agent.yaml --project-root .
python -m trajectly run specs/trt-procurement-agent-baseline.agent.yaml --project-root .
```

Expected: `PASS`.

## Step 2: Run regressed variant

```bash
python -m trajectly run specs/trt-procurement-agent-regression.agent.yaml --project-root .
```

Expected: `FAIL` with denied-tool/sequence/refinement violations.

## Step 3: Investigate

```bash
python -m trajectly report
python -m trajectly repro
python -m trajectly shrink
```

Checkpoint:
- Primary witness pinpoints procurement policy divergence.
- Violation set includes `CONTRACT_TOOL_DENIED` for `unsafe_direct_award`.

## Step 4: Simulate PR regression on baseline file

Edit `agents/procurement_agent.py` and add this override after `decision` is computed:

```python
if requisition["amount_usd"] <= 200000:
    decision["action"] = "direct_award"
    decision["vendor_id"] = "vendor-b"
```

Then run baseline spec again:

```bash
python -m trajectly run specs/trt-procurement-agent-baseline.agent.yaml --project-root .
```

Expected: `FAIL`.

## Step 5: Fix and verify green

Remove the override block from `agents/procurement_agent.py`, then run:

```bash
python -m trajectly run specs/trt-procurement-agent-baseline.agent.yaml --project-root .
```

Expected: `PASS`.
