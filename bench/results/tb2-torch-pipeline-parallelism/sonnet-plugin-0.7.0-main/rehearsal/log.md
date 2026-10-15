$ cd /app; ls -a . .rehearsal 2>&1 | head -30; python3 -c 'import torch, transformers; print(torch.__version__, transformers.__version__)'
Exit code 1
.:
.
..
.rehearsal
.rehearsal:
.
..
active
fixtures
scaffold
Traceback (most recent call last):
  File "<string>", line 1, in <module>
ModuleNotFoundError: No module named 'torch'

$ cd /app; command -v -a python python3 pip; ls /opt /opt/*/envs 2>&1 | head; pip list 2>/dev/null | grep -i -E "torch|transformers|numpy"; find / -name "torch" -maxdepth 6 -type d 2>/dev/null | head
/bin/bash: line 1: command: -a: invalid option
command: usage: command [-pVv] command [arg ...]
ls: cannot access '/opt/*/envs': No such file or directory
/opt:

$ cd /app; which python3 pip pip3; python3 --version; timeout 60 pip download torch --no-deps -d /tmp/x 2>&1 | tail -3
/usr/bin/python3
Python 3.12.3
timeout: failed to run command 'pip': No such file or directory

$ cd /app; timeout 90 python3 -m pip --version 2>&1 | tail -2; timeout 20 curl -sI https://pypi.org | head -1
/usr/bin/python3: No module named pip
HTTP/2 200

$ cd /tmp; python3 -m venv /tmp/venv 2>&1 | tail -2; ls /tmp/venv/bin 2>&1 | head
Failing command: /tmp/venv/bin/python3
python
python3
python3.12
Shell cwd was reset to /app

$ cd /tmp && timeout 580 /tmp/venv/bin/pip install -q torch --index-url https://download.pytorch.org/whl/cpu 2>&1 | tail -3
timeout: failed to run command '/tmp/venv/bin/pip': No such file or directory
Shell cwd was reset to /app

