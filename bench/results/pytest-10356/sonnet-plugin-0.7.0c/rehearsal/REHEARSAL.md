# Rehearsal: marks lost with multiple inheritance
### S1: collect scaffold/t with -m bar -> 1 deselected (bar lost); -m foo -> collected
repro: /opt/miniconda3/envs/testbed/bin/python -m pytest .rehearsal/scaffold/t -q --collect-only -m bar
