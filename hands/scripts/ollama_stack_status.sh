#!/bin/bash
cd ~/SuneelWorkSpace
echo "=== Ollama Stack Status ==="
echo ""
echo "Tmux sessions:"
tmux ls 2>/dev/null | grep -E "orchestrator|healer|diagnostics" || echo "  none running"
echo ""
echo "Ollama service:"
curl -s http://localhost:11434/api/tags 2>/dev/null | python3 -c "
import json, sys
data = json.load(sys.stdin)
models = [m['name'] for m in data.get('models', [])]
print(f'  Running: yes | Models: {len(models)}')
for m in models:
    print(f'    - {m}')
" 2>/dev/null || echo "  Ollama not running"
echo ""
echo "Engine status:"
python3 lab/autolab/ollama_orchestrator.py --status 2>/dev/null
