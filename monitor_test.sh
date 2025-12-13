#!/bin/bash
# Monitor full test progress

LOG_FILE="test_full_final.log"
CHECK_INTERVAL=30

echo "=" | head -c 70 && echo ""
echo "MONITORING FULL TEST PROGRESS"
echo "=" | head -c 70 && echo ""
echo ""
echo "Log file: $LOG_FILE"
echo "Check interval: ${CHECK_INTERVAL}s"
echo ""
echo "Press Ctrl+C to stop monitoring"
echo ""

while true; do
    if [ -f "$LOG_FILE" ]; then
        # Get file size
        SIZE=$(wc -c < "$LOG_FILE" 2>/dev/null || echo "0")
        
        # Check for key events
        STAGE_4=$(grep -c "Stage 4" "$LOG_FILE" 2>/dev/null || echo "0")
        STAGE_4_FAILED=$(grep -c "Stage 4 failed" "$LOG_FILE" 2>/dev/null || echo "0")
        STAGE_4_COMPLETE=$(grep -c "Stage 4.*completed\|Citations.*completed" "$LOG_FILE" 2>/dev/null || echo "0")
        ENHANCED=$(grep -c "Enhanced.*citations\|domain-only.*ENHANCE" "$LOG_FILE" 2>/dev/null || echo "0")
        FINAL_SUMMARY=$(grep -c "FINAL SUMMARY" "$LOG_FILE" 2>/dev/null || echo "0")
        
        echo "[$(date +%H:%M:%S)] Log: ${SIZE} bytes | Stage 4: ${STAGE_4} mentions"
        
        if [ "$STAGE_4_FAILED" -gt "0" ]; then
            echo "  ⚠️  Stage 4 has failed!"
            grep "Stage 4 failed" "$LOG_FILE" | tail -1
        elif [ "$STAGE_4_COMPLETE" -gt "0" ]; then
            echo "  ✅ Stage 4 completed successfully!"
        elif [ "$STAGE_4" -gt "0" ]; then
            echo "  ⏳ Stage 4 in progress..."
        fi
        
        if [ "$ENHANCED" -gt "0" ]; then
            echo "  ✅ Domain-only enhancement detected"
        fi
        
        if [ "$FINAL_SUMMARY" -gt "0" ]; then
            echo ""
            echo "  🎉 TEST COMPLETED!"
            echo ""
            tail -30 "$LOG_FILE" | grep -E "PASSED|FAILED|Summary|Results"
            break
        fi
        
        # Show latest stage
        LATEST_STAGE=$(grep -E "Stage [0-9]|Stage [0-9][0-9]" "$LOG_FILE" | tail -1 | grep -oE "Stage [0-9]+" | tail -1)
        if [ ! -z "$LATEST_STAGE" ]; then
            echo "  Current: $LATEST_STAGE"
        fi
    else
        echo "[$(date +%H:%M:%S)] Waiting for log file..."
    fi
    
    echo ""
    sleep $CHECK_INTERVAL
done

