# Procurement Approval Demo for Trajectly (Declarative Graph)

This demo shows a procurement workflow built with `trajectly.App` and validated with deterministic replay.

## What the agent does and why Trajectly is used

1. The agent processes one procurement request by fetching requisition data and vendor quotes, then selecting an execution path.
2. The safe path routes for approval and creates a purchase order; the regression variant intentionally takes an unsafe direct-award path.
3. Trajectly is used to record baseline behavior and replay it as a deterministic gate so behavior changes are caught with a reproducible witness.

## What this demonstrates

1. Baseline behavior passes.
2. Intentional regression fails deterministically.
3. `report`, `repro`, and `shrink` give triage-ready outputs.
4. Determinism break fails and determinism fix passes.

## Setup

```bash
git clone https://github.com/trajectly/procurement-approval-demo.git
cd procurement-approval-demo

python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Validated on: March 5, 2026 (clean run).

## End-to-end Commands With Observed Outputs

### 1) Initialize workspace

Command:

```bash
python -m trajectly init
```

Observed output:

```text
Initialized Trajectly workspace at $PROJECT_ROOT
```

What this means:

1. `.trajectly/` workspace metadata is ready.

### 2) Record and run baseline

Commands:

```bash
python -m trajectly record specs/trt-procurement-agent-baseline.agent.yaml --project-root .
python -m trajectly run specs/trt-procurement-agent-baseline.agent.yaml --project-root .
```

Observed output excerpts:

```text
Recorded 1 spec(s) successfully

- `trt-procurement-agent`: clean
  - trt: `PASS`
```

What this means:

1. Baseline trace exists.
2. Baseline replay is clean.

### 3) Run intentional regression

Command:

```bash
python -m trajectly run specs/trt-procurement-agent-regression.agent.yaml --project-root .
```

Observed output excerpt:

```text
- `trt-procurement-agent`: regression
  - trt: `FAIL` (witness=10)
```

What this means:

1. Regression is detected.
2. This step is expected to exit non-zero.

### 4) Triage with report, repro, shrink

Commands:

```bash
python -m trajectly report
python -m trajectly repro
python -m trajectly shrink
```

Observed output excerpts:

```text
# report
- `trt-procurement-agent`: regression
  - trt: `FAIL` (witness=10)

# repro
Repro command: python -m trajectly run "$PROJECT_ROOT/specs/trt-procurement-agent-regression.agent.yaml" --project-root "$PROJECT_ROOT"
- `trt-procurement-agent`: regression
  - trt: `FAIL` (witness=10)

# shrink
Shrink completed and report updated with shrink stats.
```

What this means:

1. `report` summarizes current failure.
2. `repro` replays the same failing case.
3. `shrink` produces a smaller failing counterexample.

### 5) Inspect JSON after shrink

Command:

```bash
python -m trajectly report --json
```

Observed output excerpt:

```json
{
  "regressions": 1,
  "reports": [
    {
      "trt_failure_class": "REFINEMENT",
      "trt_primary_violation": {
        "code": "REFINEMENT_BASELINE_CALL_MISSING",
        "expected": "fetch_requisition",
        "observed": ["unsafe_direct_award"]
      },
      "trt_shrink_stats": {
        "original_len": 11,
        "reduced_len": 1
      },
      "trt_status": "FAIL"
    }
  ]
}
```

What this means:

1. Failure class is explicit (`REFINEMENT_BASELINE_CALL_MISSING`).
2. Shrink reduced the failing trace.

### 6) Determinism break and fix

Commands:

```bash
python -m trajectly record specs/trt-procurement-agent-determinism-break.agent.yaml --project-root .
python -m trajectly run specs/trt-procurement-agent-determinism-break.agent.yaml --project-root .

python -m trajectly record specs/trt-procurement-agent-determinism-fix.agent.yaml --project-root .
python -m trajectly run specs/trt-procurement-agent-determinism-fix.agent.yaml --project-root .
```

Observed output excerpts:

```text
# determinism break
- `trt-procurement-agent-determinism-break`: regression
  - trt: `FAIL` (witness=4)

# determinism fix
- `trt-procurement-agent-determinism-fix`: clean
  - trt: `PASS`
```

What this means:

1. Non-deterministic behavior is catchable.
2. Determinism fix restores clean replay.

## What success looks like

From the validated run:

1. Baseline run: exit `0`, `PASS`.
2. Regression run: exit `1`, `FAIL` with witness.
3. `report`: exit `0`.
4. `repro`: exit `1` (expected).
5. `shrink`: exit `0`.
6. Determinism break run: exit `1`.
7. Determinism fix run: exit `0`.

## One-command local verification

```bash
bash scripts/verify_demo.sh
```

## CI workflow (canonical action)

This demo uses a hybrid CI gate:

1. `bash scripts/verify_demo.sh` validates the full local regression/determinism flow.
2. `trajectly/trajectly-action@v1` runs baseline replay, publishes artifacts, and posts PR comments.

Workflow snippet:

```yaml
jobs:
  trajectly:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: |
          python -m pip install --upgrade pip
          python -m pip install -r requirements.txt
      - id: verify_demo
        continue-on-error: true
        run: bash scripts/verify_demo.sh
      - id: trt_action
        continue-on-error: true
        uses: trajectly/trajectly-action@v1
        with:
          spec_glob: "specs/trt-procurement-agent-baseline.agent.yaml"
          project_root: "."
          comment_pr: "true"
          upload_artifacts: "true"
```

What to expect:

1. CI fails if either the script gate or action gate fails.
2. PRs get a `<!-- trajectly-report -->` comment marker when comment posting is enabled.
3. `.trajectly/**` artifacts are uploaded by the action step.

## Repository structure

1. `agents/procurement_graph.py`: graph logic and policy routing.
2. `agents/procurement_agent*.py`: spec entry modules.
3. `specs/*.agent.yaml`: baseline/regression/determinism specs.
4. `scripts/verify_demo.sh`: CI-equivalent local check.
5. `.github/workflows/trajectly.yml`: hybrid CI workflow using `trajectly/trajectly-action@v1`.

For the full walkthrough including PR drill and cleanup, see [TUTORIAL.md](TUTORIAL.md).
