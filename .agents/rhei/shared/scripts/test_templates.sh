#!/usr/bin/env bash
# Instantiate, validate, and dry-run every paper-pipeline template.
#
# Run from the repository root:  .agents/rhei/shared/scripts/test_templates.sh
#
# Each template is rendered into a scratch directory, checked with `rhei
# validate`, and executed with `rhei run --dry-run` so orchestrator-shape errors
# surface without spawning agents. Non-scalar inputs are exercised through
# --values, which is the only path that tests typed structures.

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
SHARED="$ROOT/.agents/rhei/shared"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

pass=0
fail=0
ok()  { pass=$((pass+1)); printf '  \033[32mok\033[0m   %s\n' "$1"; }
bad() { fail=$((fail+1)); printf '  \033[31mFAIL\033[0m %s\n' "$1"; [ -n "${2:-}" ] && echo "$2" | sed 's/^/         /'; }

cd "$ROOT"

check() {
  local name="$1"; shift
  local out
  rm -rf "$WORK/$name"
  if ! out=$(rhei instantiate "$name" "$@" --output "$WORK/$name" --keep-on-error 2>&1); then
    bad "$name: instantiate" "$(echo "$out" | tail -6)"; return
  fi
  if ! out=$(rhei validate "$WORK/$name" 2>&1); then
    bad "$name: validate" "$(echo "$out" | tail -6)"; return
  fi
  if ! out=$(rhei run "$WORK/$name" --dry-run 2>&1); then
    bad "$name: run --dry-run" "$(echo "$out" | tail -6)"; return
  fi
  # A bundled settings.json must render as valid JSON.
  if [ -f "$WORK/$name/.agents/rhei/settings.json" ]; then
    if ! python3 -c "import json,sys; json.load(open(sys.argv[1]))" "$WORK/$name/.agents/rhei/settings.json" 2>/dev/null; then
      bad "$name: settings.json is not valid JSON"; return
    fi
  fi
  ok "$name: instantiate + validate + dry-run"
}

echo "== every template renders, validates, and dry-runs =="
check paper-ingest     --set paper=inputs/submission-42.pdf --set paper_id=submission-42
check venue-intake     --set conference=https://example.org/venue
check reviewer-match   --set paper_id=submission-42
check pc-citation-scan --set paper_id=submission-42
check related-work     --set paper_id=submission-42
check overall-review   --set paper_id=submission-42
check section-review   --set paper_id=submission-42
check pc-member-review --set paper_id=submission-42

echo
echo "== input branches =="

# LaTeX ingest path
check paper-ingest --set paper=paper/main.tex --set source_kind=latex --set paper_id=tex-submission

# Venue intake with supplied guidelines and no PC harvesting
printf 'Reviewers must justify every score.\n' > "$WORK/guidelines.md"
rm -rf "$WORK/vi-branch"
if rhei instantiate venue-intake --set conference=OOPSLA --set harvest_pc=false \
     --set-file guidelines="$WORK/guidelines.md" --output "$WORK/vi-branch" >/dev/null 2>&1 \
   && rhei validate "$WORK/vi-branch" >/dev/null 2>&1 \
   && grep -q "Reviewers must justify every score" "$WORK/vi-branch/venue/guidelines.md"; then
  ok "venue-intake: supplied guidelines land verbatim, harvest_pc=false"
else
  bad "venue-intake: guidelines/harvest_pc branch"
fi

# A completely different agent, declared through agents_json
cat > "$WORK/agents.json" <<'JSON'
{
  "gemini": {
    "command": ["gemini"],
    "model_flag": "--model",
    "stdin_prompt": true,
    "modes": { "yolo": ["--yolo"], "deep": ["--yolo", "--thinking", "high"] }
  }
}
JSON
cat > "$WORK/personalities.yaml" <<'YAML'
personalities:
  - id: deep-critic
    label: Deep critic
    selector: gemini[deep]:google:gemini-3.1-pro
    stance: You are an exacting critic. Attack the weakest claim first.
  - id: pragmatist
    label: Pragmatist
    selector: gemini[yolo]:google:gemini-3.1-pro
    stance: You judge whether this would survive contact with production.
YAML
rm -rf "$WORK/or-gemini"
if rhei instantiate overall-review --values "$WORK/personalities.yaml" \
     --set-file agents_json="$WORK/agents.json" \
     --set merge_target='gemini[deep]:google:gemini-3.1-pro' \
     --set repair_target='gemini[yolo]:google:gemini-3.1-pro' \
     --output "$WORK/or-gemini" >/dev/null 2>&1 \
   && rhei validate "$WORK/or-gemini" >/dev/null 2>&1; then
  ok "overall-review: arbitrary agent via agents_json (gemini, custom modes)"
else
  bad "overall-review: custom agent declaration"
fi

# Optional upstream artifacts wired in
rm -rf "$WORK/pmr-full"
if rhei instantiate pc-member-review --set paper_id=submission-42 \
     --set related_work=../related-work/related/related-work.json \
     --set pc_citations=../pc-citation-scan/citations/pc-citations.json \
     --output "$WORK/pmr-full" >/dev/null 2>&1 \
   && rhei validate "$WORK/pmr-full" >/dev/null 2>&1 \
   && grep -q "pc-citations" "$WORK/pmr-full/states.yaml"; then
  ok "pc-member-review: optional related-work and pc-citations wired in"
else
  bad "pc-member-review: optional inputs branch"
fi

echo
echo "== parallel fan-out actually schedules concurrently =="
rm -rf "$WORK/or-par"
rhei instantiate overall-review --set paper_id=p --output "$WORK/or-par" >/dev/null 2>&1
python3 "$SHARED/scripts/import_artifact.py" --schema-dir "$WORK/or-par/schemas" \
  --source "$SHARED/examples/paper.json" --dest "$WORK/or-par/inputs/paper.json" \
  --expect-artifact paper >/dev/null 2>&1
python3 "$SHARED/scripts/import_artifact.py" --schema-dir "$WORK/or-par/schemas" \
  --source "$SHARED/examples/venue.json" --dest "$WORK/or-par/inputs/venue.json" \
  --expect-artifact venue >/dev/null 2>&1
(cd "$WORK/or-par" && rhei transition import --from import-inputs --to completed >/dev/null 2>&1)
ready=$(rhei run "$WORK/or-par" --parallel 4 --dry-run 2>&1 | grep -c "would transition: .*review-overall-")
if [ "$ready" -ge 3 ]; then
  ok "overall-review: $ready personality tasks scheduled in one pass"
else
  bad "overall-review: expected >=3 concurrent personality tasks, got $ready"
fi

echo
echo "-------------------------------------------"
printf '%d passed, %d failed\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
