#!/bin/bash
# Script to temporarily stop phosphobot, run hand tracking, then restart

echo "🛑 Stopping phosphobot process to free camera..."
PHOSPHOBOT_PID=$(pgrep phosphobot)

if [ ! -z "$PHOSPHOBOT_PID" ]; then
    echo "   Found phosphobot process: $PHOSPHOBOT_PID"
    kill -TERM $PHOSPHOBOT_PID
    sleep 2
    
    if pgrep phosphobot > /dev/null; then
        echo "   Force killing phosphobot..."
        pkill -9 phosphobot
        sleep 1
    fi
    
    echo "✅ Phosphobot stopped"
else
    echo "   No phosphobot process found"
fi

echo ""
echo "🎯 Starting hand tracking with camera access..."
echo "   Press Ctrl+C when done to restart phosphobot"
echo ""

# Run hand tracking
python hand_tracking.py

echo ""
echo "🔄 Restarting phosphobot..."
cd /home/hafnium/phosphobot && phosphobot run &
echo "✅ Phosphobot restarted"
