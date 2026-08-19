#!/usr/bin/env bash
# Test the paper-pipeline artifact contracts.
#
# Run from anywhere:  .agents/rhei/shared/scripts/test_contracts.sh
#
# Covers: the validator's own semantics, that every schema uses only supported
# keywords and resolves its refs, that every checked-in example is valid, that
# representative corruptions are caught, and that a wrong artifact wired into
# the wrong input is refused.

set -uo pipefail

SHARED="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VALIDATE="python3 $SHARED/scripts/validate_artifact.py"
SCHEMAS="$SHARED/schemas"
EXAMPLES="$SHARED/examples"

pass=0
fail=0

ok()   { pass=$((pass+1)); printf '  \033[32mok\033[0m   %s\n' "$1"; }
bad()  { fail=$((fail+1)); printf '  \033[31mFAIL\033[0m %s\n' "$1"; [ -n "${2:-}" ] && echo "$2" | sed 's/^/         /'; }

echo "== validator self-test =="
if out=$($VALIDATE --self-test 2>&1); then
  ok "$(echo "$out" | tail -1)"
else
  bad "validator self-test" "$out"
fi

echo
echo "== schemas are well-formed and use only supported keywords =="
for s in "$SCHEMAS"/*.schema.json; do
  name=$(basename "$s")
  if out=$(python3 - "$s" <<'PY' 2>&1
import json, sys, pathlib
sys.path.insert(0, str(pathlib.Path(sys.argv[0]).parent))
PY
  ); then :; fi
  # Validating an empty object exercises every keyword and every $ref.
  if out=$(python3 -c "
import json,sys
sys.path.insert(0,'$SHARED/scripts')
from validate_artifact import validate
validate({}, json.load(open('$s')))
" 2>&1); then
    ok "$name"
  else
    bad "$name" "$out"
  fi
done

echo
echo "== every example validates against its schema =="
for f in "$EXAMPLES"/*.json; do
  name=$(basename "$f")
  if out=$($VALIDATE --schema-dir "$SCHEMAS" --instance "$f" 2>&1); then
    ok "$name"
  else
    bad "$name" "$out"
  fi
done

echo
echo "== corruptions are caught =="
corrupt() {
  local label="$1" src="$2" mutation="$3"
  python3 -c "
import json,sys
inst=json.load(open('$EXAMPLES/$src'))
$mutation
json.dump(inst, open('/tmp/pipeline-corrupt.json','w'))
"
  if $VALIDATE --schema-dir "$SCHEMAS" --instance /tmp/pipeline-corrupt.json >/dev/null 2>&1; then
    bad "$label (not caught)"
  else
    ok "$label"
  fi
}

corrupt "paper: missing title"                paper.json              "del inst['title']"
corrupt "paper: bad section kind"             paper.json              "inst['sections'][0]['kind']='maybe'"
corrupt "paper: bad section id"               paper.json              "inst['sections'][0]['id']='sec-1'"
corrupt "paper: unknown source_kind"          paper.json              "inst['source_kind']='docx'"
corrupt "paper: extra property"               paper.json              "inst['bogus']=1"
corrupt "venue: empty review form"            venue.json              "inst['review_form']['fields']=[]"
corrupt "venue: no double_blind"              venue.json              "del inst['review_process']['double_blind']"
corrupt "pc: id not a slug"                   program-committee.json  "inst['members'][0]['id']='A Chair'"
corrupt "pc: invalid role"                    program-committee.json  "inst['members'][0]['role']='reviewer'"
corrupt "matches: likelihood out of range"    reviewer-matches.json   "inst['matches'][0]['likelihood']=1.4"
corrupt "matches: invalid band"               reviewer-matches.json   "inst['matches'][0]['band']='certain'"
corrupt "related-work: bad id"                related-work.json       "inst['entries'][0]['id']='1'"
corrupt "related-work: unknown relation"      related-work.json       "inst['entries'][0]['relation']='similar'"
corrupt "overall: bad recommendation"         overall-reviews.json    "inst['reviews'][0]['recommendation']='maybe'"
corrupt "overall: no reviews"                 overall-reviews.json    "inst['reviews']=[]"
corrupt "section: finding without severity"   section-reviews.json    "del inst['reviews'][0]['findings'][0]['severity']"
corrupt "points: malformed id"                review-points.json      "inst['points'][0]['id']='P-1'"
corrupt "points: point without sources"       review-points.json      "inst['points'][0]['sources']=[]"
corrupt "points: invalid verdict"             review-points.json      "inst['points'][0]['verdict']='maybe'"

echo
echo "== cross-wiring guard =="
if $VALIDATE --schema-dir "$SCHEMAS" --instance "$EXAMPLES/venue.json" --expect-artifact paper >/dev/null 2>&1; then
  bad "venue.json accepted where paper expected"
else
  ok "wrong artifact into wrong input is refused"
fi
if $VALIDATE --schema-dir "$SCHEMAS" --instance "$EXAMPLES/paper.json" --expect-artifact paper >/dev/null 2>&1; then
  ok "correct artifact accepted"
else
  bad "paper.json refused where paper expected"
fi

echo
echo "== malformed JSON is a usage error, not a validation failure =="
printf '{"artifact": "paper",' > /tmp/pipeline-broken.json
$VALIDATE --schema-dir "$SCHEMAS" --instance /tmp/pipeline-broken.json >/dev/null 2>&1
if [ $? -eq 2 ]; then ok "unparseable instance exits 2"; else bad "unparseable instance should exit 2"; fi

rm -f /tmp/pipeline-corrupt.json /tmp/pipeline-broken.json

echo
echo "-------------------------------------------"
printf '%d passed, %d failed\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
