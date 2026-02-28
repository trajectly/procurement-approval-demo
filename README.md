# Procurement Approval Demo for Trajectly

Standalone Trajectly demo that shows procurement governance regressions.

You will record a baseline, run an intentionally regressed variant, and confirm
that Trajectly fails deterministically when `unsafe_direct_award` bypasses
`route_for_approval`.

## 1. Setup

```bash
git clone https://github.com/trajectly/procurement-approval-demo.git
cd procurement-approval-demo

python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 2. Record baseline and verify PASS

```bash
python -m trajectly init
python -m trajectly record specs/trt-procurement-agent-baseline.agent.yaml --project-root .
python -m trajectly run specs/trt-procurement-agent-baseline.agent.yaml --project-root .
```

Expected: `PASS` (exit code `0`).

## 3. Run regression and verify FAIL

```bash
python -m trajectly run specs/trt-procurement-agent-regression.agent.yaml --project-root .
```

Expected: `FAIL` (exit code `1`).

Use investigation commands:

```bash
python -m trajectly report
python -m trajectly repro
python -m trajectly shrink
```

The failure should include `CONTRACT_TOOL_DENIED` for `unsafe_direct_award`
and refinement/sequence violations.

## 4. CI behavior

`.github/workflows/trajectly.yml` runs baseline spec replay on every push/PR.
Any behavioral regression in `agents/procurement_agent.py` turns CI red.

See [TUTORIAL.md](TUTORIAL.md) for a full fail/fix loop.
