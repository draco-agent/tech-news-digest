#!/bin/bash
# Quick pipeline smoke test — runs all steps with --hours 24 and validates outputs
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEFAULTS="$SCRIPT_DIR/../config/defaults"
OUTDIR=$(mktemp -d /tmp/tech-digest-test-XXXXXX)
PASSED=0
SKIPPED=0
FAILED=0

run_step() {
    local name="$1"; shift
    if "$@" 2>&1; then
        echo "✅ $name"
        PASSED=$((PASSED + 1))
    else
        echo "❌ $name (exit $?)"
        FAILED=$((FAILED + 1))
    fi
}

validate_json() {
    local file="$1" name="$2"
    if [ -f "$file" ] && python3 -c "import json,sys; json.load(open(sys.argv[1]))" "$file" 2>/dev/null; then
        echo "✅ $name JSON valid"
        PASSED=$((PASSED + 1))
    else
        echo "❌ $name JSON invalid or missing"
        FAILED=$((FAILED + 1))
    fi
}

# RSS (always)
run_step "fetch-rss" python3 "$SCRIPT_DIR/fetch-rss.py" --defaults "$DEFAULTS" --hours 24 --output "$OUTDIR/rss.json" --force
validate_json "$OUTDIR/rss.json" "rss"

# GitHub (always)
run_step "fetch-github" python3 "$SCRIPT_DIR/fetch-github.py" --defaults "$DEFAULTS" --hours 24 --output "$OUTDIR/github.json" --force
validate_json "$OUTDIR/github.json" "github"

# Twitter (skip if no token)
if [ -n "$X_BEARER_TOKEN" ]; then
    run_step "fetch-twitter" python3 "$SCRIPT_DIR/fetch-twitter.py" --defaults "$DEFAULTS" --hours 24 --output "$OUTDIR/twitter.json" --force
    validate_json "$OUTDIR/twitter.json" "twitter"
else
    echo "⏭  fetch-twitter (no X_BEARER_TOKEN)"
    SKIPPED=$((SKIPPED + 1))
fi

# Web (skip if no key)
if [ -n "$BRAVE_API_KEY" ]; then
    run_step "fetch-web" python3 "$SCRIPT_DIR/fetch-web.py" --defaults "$DEFAULTS" --freshness pd --output "$OUTDIR/web.json" --force
    validate_json "$OUTDIR/web.json" "web"
else
    echo "⏭  fetch-web (no BRAVE_API_KEY)"
    SKIPPED=$((SKIPPED + 1))
fi

# Merge
MERGE_ARGS="--output $OUTDIR/merged.json"
[ -f "$OUTDIR/rss.json" ] && MERGE_ARGS="$MERGE_ARGS --rss $OUTDIR/rss.json"
[ -f "$OUTDIR/twitter.json" ] && MERGE_ARGS="$MERGE_ARGS --twitter $OUTDIR/twitter.json"
[ -f "$OUTDIR/web.json" ] && MERGE_ARGS="$MERGE_ARGS --web $OUTDIR/web.json"
[ -f "$OUTDIR/github.json" ] && MERGE_ARGS="$MERGE_ARGS --github $OUTDIR/github.json"
run_step "merge-sources" python3 "$SCRIPT_DIR/merge-sources.py" $MERGE_ARGS
validate_json "$OUTDIR/merged.json" "merged"

# Validate merged structure
if python3 -c "
import json,sys
d=json.load(open(sys.argv[1]))
assert 'topics' in d and 'output_stats' in d
" "$OUTDIR/merged.json" 2>/dev/null; then
    echo "✅ merged structure valid"
    PASSED=$((PASSED + 1))
else
    echo "❌ merged structure invalid"
    FAILED=$((FAILED + 1))
fi

echo ""
echo "📊 Results: $PASSED passed, $FAILED failed, $SKIPPED skipped"
echo "   Output: $OUTDIR"
[ "$FAILED" -eq 0 ] && exit 0 || exit 1
