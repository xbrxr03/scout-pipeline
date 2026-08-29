#!/bin/bash
# SCOUT Batch Apply — Runs scout_apply.py N times
# Each run uses a different search URL (rotated via --run flag)
# Waits 60 seconds between runs to avoid detection.

COUNT="${1:-10}"
DELAY="${2:-60}"

echo "🚀 SCOUT Batch Apply: $COUNT jobs, ${DELAY}s delay between runs"
echo "============================================================"

APPLIED=0
FAILED=0

for i in $(seq 1 "$COUNT"); do
    echo ""
    echo "📋 Run $i/$COUNT — $(date)"
    
    # Clean Chrome lock files
    rm -f ~/.browser-use-profiles/job-hunter/SingletonLock ~/.browser-use-profiles/job-hunter/SingletonSocket ~/.browser-use-profiles/job-hunter/SingletonCookie 2>/dev/null
    
    # Kill any leftover browser processes
    pkill -9 -f "Chrome for Testing" 2>/dev/null
    pkill -9 -f "chromium-1234" 2>/dev/null
    sleep 3
    
    # Run the apply script with --run flag to rotate search URLs
    cd ~/Projects/auto-apply && source ~/Projects/ApplyPilot/.venv/bin/activate && \
    OLLAMA_API_KEY="0b35e4faf4f4421b952cfd3cad2622c0.iSCe8Sec0pMAiRvO6MeyVMyV" \
    timeout 900 python3 scout_apply.py --category internship --run $((i-1)) 2>&1 | tail -10
    
    EXIT_CODE=$?
    
    if [ $EXIT_CODE -eq 0 ]; then
        echo "✅ Run $i completed successfully"
        APPLIED=$((APPLIED + 1))
    else
        echo "❌ Run $i failed or timed out (exit code: $EXIT_CODE)"
        FAILED=$((FAILED + 1))
    fi
    
    echo "📊 Progress: $APPLIED applied, $FAILED failed out of $i runs"
    
    # Don't wait after the last run
    if [ "$i" -lt "$COUNT" ]; then
        echo "⏳ Waiting ${DELAY}s before next run..."
        sleep "$DELAY"
    fi
done

echo ""
echo "============================================================"
echo "🎯 Batch Complete: $APPLIED applied, $FAILED failed out of $COUNT runs"
echo "============================================================"

# Show what was applied to
echo ""
echo "📋 Applications logged in SCOUT DB:"
cd ~/Projects/auto-apply && source ~/Projects/ApplyPilot/.venv/bin/activate && \
python3 -c "
import sqlite3
conn = sqlite3.connect('$HOME/.applypilot/scout_jobs.db')
try:
    rows = conn.execute('SELECT date, url, category, status, source FROM swe_applications ORDER BY id DESC LIMIT 20').fetchall()
    for r in rows:
        print(f'  {r[0][:19]} | {r[2]} | {r[3]} | {r[4]} | {r[1][:60]}')
except:
    print('  No swe_applications table yet')
conn.close()
"