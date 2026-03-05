# Tutorial: End-to-End Trajectly PR Regression Workflow (Procurement)

This walkthrough uses real validated outputs from March 5, 2026.

## What the agent does and why Trajectly is used

1. The procurement agent fetches requisition and quote data, then executes either an approval flow or a direct-award flow.
2. The baseline path is approval-first; the regression path is intentionally unsafe so the guard can fail.
3. The goal with Trajectly is to turn that behavior into a replayable contract, then use `run`, `report`, `repro`, and `shrink` for fast triage.

Path placeholders:

1. `$PROJECT_ROOT` = local repo path
2. `$VALIDATION_BRANCH` = `validation/docs-e2e-procurement-approval-demo-202603051852`

## Step 0: Setup

```bash
git clone https://github.com/trajectly/procurement-approval-demo.git
cd procurement-approval-demo

python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Step 1: Initialize and baseline

Commands:

```bash
python -m trajectly init
python -m trajectly record specs/trt-procurement-agent-baseline.agent.yaml --project-root .
python -m trajectly run specs/trt-procurement-agent-baseline.agent.yaml --project-root .
```

Observed output excerpts:

```text
Initialized Trajectly workspace at $PROJECT_ROOT
Recorded 1 spec(s) successfully
- `trt-procurement-agent`: clean
  - trt: `PASS`
```

## Step 2: Intentional regression

Command:

```bash
python -m trajectly run specs/trt-procurement-agent-regression.agent.yaml --project-root .
```

Observed output excerpt:

```text
- `trt-procurement-agent`: regression
  - trt: `FAIL` (witness=10)
```

Observed exit code:

```text
13_run_regression=1
```

## Step 3: Triage commands

Commands:

```bash
python -m trajectly report
python -m trajectly repro
python -m trajectly shrink
python -m trajectly report --json
python -m trajectly report
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

# report --json excerpt
"trt_failure_class": "REFINEMENT"
"code": "REFINEMENT_BASELINE_CALL_MISSING"
"expected": "fetch_requisition"
"observed": ["unsafe_direct_award"]
"trt_shrink_stats": { "original_len": 11, "reduced_len": 1 }

# report (markdown)
- `trt-procurement-agent`: regression
  - trt: `FAIL` (witness=0)
```

Observed exit behavior:

```text
14_report_after_regression=0
15_repro=1
16_shrink=0
17_report_after_shrink_json=0
18_report_after_shrink_md=0
```

## Step 4: Determinism break and fix

Commands:

```bash
python -m trajectly record specs/trt-procurement-agent-determinism-break.agent.yaml --project-root .
python -m trajectly run specs/trt-procurement-agent-determinism-break.agent.yaml --project-root .

python -m trajectly record specs/trt-procurement-agent-determinism-fix.agent.yaml --project-root .
python -m trajectly run specs/trt-procurement-agent-determinism-fix.agent.yaml --project-root .
```

Observed output excerpts:

```text
# break
- `trt-procurement-agent-determinism-break`: regression
  - trt: `FAIL` (witness=4)

# fix
- `trt-procurement-agent-determinism-fix`: clean
  - trt: `PASS`
```

Observed exit behavior:

```text
20_record_det_break=0
21_run_det_break=1
22_record_det_fix=0
23_run_det_fix=0
```

## Step 5: PR drill (risky change)

Create branch:

```bash
git checkout -b $VALIDATION_BRANCH
```

Inject risky change into `agents/procurement_graph.py`:

```bash
python - <<'PY'
from pathlib import Path

path = Path("agents/procurement_graph.py")
text = path.read_text(encoding="utf-8")
needle = '        decision = choose_procurement_action(summary, default_vendor="vendor-c")\n'
inject = (
    '        decision = choose_procurement_action(summary, default_vendor="vendor-c")\n'
    '        if int(requisition["amount_usd"]) <= 200000:\n'
    '            decision["action"] = "direct_award"\n'
    '            decision["vendor_id"] = "vendor-b"\n'
)
if inject not in text:
    text = text.replace(needle, inject, 1)
path.write_text(text, encoding="utf-8")
PY
```

Commit risky change:

```bash
git add agents/procurement_graph.py
git commit -m "test: inject risky direct-award bypass to rehearse failing PR"
```

Observed output:

```text
[validation/docs-e2e-procurement-approval-demo-202603051852 ...] test: inject risky direct-award bypass to rehearse failing PR
 1 file changed, 3 insertions(+)
```

Run baseline gate (should fail):

```bash
python -m trajectly init
python -m trajectly run specs/trt-procurement-agent-baseline.agent.yaml --project-root .
python -m trajectly report
```

Observed output excerpt:

```text
- `trt-procurement-agent`: regression
  - trt: `FAIL` (witness=10)
```

Observed exit behavior:

```text
pr_init_after_risky=0
pr_run_baseline_after_risky=1
pr_report_after_risky=0
```

## Step 6: PR drill (fix commit)

Restore safe behavior and commit fix:

```bash
git checkout origin/main -- agents/procurement_graph.py
git add agents/procurement_graph.py
git commit -m "fix: restore required approval routing behavior"
```

Observed output:

```text
[validation/docs-e2e-procurement-approval-demo-202603051852 ...] fix: restore required approval routing behavior
 1 file changed, 3 deletions(-)
```

Re-run baseline gate:

```bash
python -m trajectly init
python -m trajectly run specs/trt-procurement-agent-baseline.agent.yaml --project-root .
```

Observed output excerpt:

```text
- `trt-procurement-agent`: clean
  - trt: `PASS`
```

Observed exit behavior:

```text
pr_init_after_fix=0
pr_run_baseline_after_fix=0
```

## Step 7: Push branch and create PR

Commands:

```bash
git push -u origin $VALIDATION_BRANCH
gh pr create --base main --head $VALIDATION_BRANCH --title "docs-validation: procurement e2e capture" --body "Temporary PR for tutorial output capture. Will close unmerged."
```

Observed output:

```text
Branch '$VALIDATION_BRANCH' set up to track remote branch '$VALIDATION_BRANCH' from 'origin'.
https://github.com/trajectly/procurement-approval-demo/pull/5
```

## Step 8: Cleanup (temporary validation branch/PR)

Commands:

```bash
gh pr close 5 --delete-branch --comment "Closing temporary docs-validation PR used to capture tutorial outputs."
git checkout main
git branch -D $VALIDATION_BRANCH
```

Observed output:

```text
✓ Closed pull request trajectly/procurement-approval-demo#5 (docs-validation: procurement e2e capture)
✓ Deleted branch validation/docs-e2e-procurement-approval-demo-202603051852
Deleted branch validation/docs-e2e-procurement-approval-demo-202603051852 (was 301046d).
```

## Final expected verdicts

1. Baseline: pass.
2. Regression: fail with witness.
3. Repro: fail (expected).
4. Shrink: success.
5. Determinism break: fail.
6. Determinism fix: pass.
7. PR drill risky commit: fail.
8. PR drill fix commit: pass.
