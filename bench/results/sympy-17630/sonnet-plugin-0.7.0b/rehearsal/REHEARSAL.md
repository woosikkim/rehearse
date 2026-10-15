### S1: (b.blocks*b.blocks)[0,1] type
- saw: Zero (scalar), not ZeroMatrix; BlockMatrix(...) of it raises ValueError here
- fix: in BlockMatrix._blockmul, turn Zero entries into ZeroMatrix(rowblocksizes[i], other.colblocksizes[j])
repro: /opt/miniconda3/envs/testbed/bin/python -c 'from sympy import *; a=MatrixSymbol("a",2,2); z=ZeroMatrix(2,2); b=BlockMatrix([[a,z],[z,z]]); print(block_collapse(b*b*b))'
