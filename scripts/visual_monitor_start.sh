#!/bin/bash
tmux new-session -d -s visual-monitor \
  "cd ~/SuneelWorkSpace && source .venv/bin/activate && python3 visual/visual_monitor.py 2>&1 | tee agent-system/logs/visual_monitor.log"
echo "✅ Visual monitor started in tmux session 'visual-monitor'"
echo "   View: tmux attach -t visual-monitor"
