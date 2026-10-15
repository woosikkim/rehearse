$ cd /app; ls -la; ls .rehearsal; which oligotm primer3_core python3; python3 -c 'print(1)'; grep -c . sequences.fasta; awk '/^>/{if(n)print n; print; n=0; next}{n+=length($0)}END{print n}' sequences.fasta
total 20
drwxr-xr-x 1 root root 4096 Oct 15 12:25 .
drwxr-xr-x 1 root root 4096 Oct 15 12:15 ..
drwxr-xr-x 4 root root 4096 Oct 15 12:25 .rehearsal
-rw-r--r-- 1 root root 7712 Oct 24  2025 sequences.fasta
active
fixtures
scaffold
/usr/bin/python3
1
10
>input
2727
>egfp
717
>flag
90
>snap
549
>output
3591

$ cd /app; pip list 2>/dev/null | grep -i -E "primer3|biopython"; find / -name "oligotm*" 2>/dev/null | head; cat sequences.fasta
>input
actcttcctttttcaatattattgaagcatttatcagggttattgtctcatgagcggatacatatttgaatgtatttagaaaaataaacaaataggggttccgcgcacatttccccgaaaagtgctagtggtgctagccccgcgaaattaatacgactcactatagggtctagaaataattttgtttaactttaagaaggagatatacatatgatcagtctgattgcggcgttagcggtagatcgcgttatcggcatggaaaacgccatgccgtggaacctgcctgccgatctcgcctggtttaaacgcaacaccttaaataaacccgtgattatgggccgccatacctgggaatcaatcggtcgtccgttgccaggacgcaaaaatattatcctcagca
>egfp
atgagcaagggcgaggagctgttcaccggggtggtgcccatcctggtcgagctggacggcgacgtaaacggccacaagttcagcgtgtccggcgagggtgagggcgatgccacctacggcaagctgaccctgaagttcatctgcaccacgggcaagctgcccgtgccctggcccaccctcgtgaccaccctgacctacggcgtgcagtgcttcagccgctaccccgaccacatgaagcagcacgacttcttcaagtccgccatgcccgaaggctacgtccaggagcgcaccatcttcttcaaggacgacggcaactacaagacccgcgccgaggtgaagttcgagggcgacaccctggtgaaccgcatcgagctgaagggcatcgacttcaaggaggacg
>flag
atgggtagtggctccggtagcggtagcggcagcgactacaaggacgacgacgacaagggttccggttctggttcaggtagtggttcataa
>snap
atggacaaagactgcgaaatgaagcgcaccaccctggatagccctctgggcaagctggaactgtctgggtgcgaacagggcctgcaccgtatcatcttcctgggcaaaggaacatctgccgccgacgccgtggaagtgcctgccccagccgccgtgctgggcggaccagagccactgatgcaggctaccgcatggctcaacgcctactttcaccagcctgaggccatcgaggagttccctgtgccagcgctgcaccatccagtgttccagcaggagagctttacccgccaggtgctgtggaaactgctgaaagtggtgaagtttggagaggtcatcagctacagccacctggccgccctggccggcaatcccgcagccaccgccgcagtgaaaaccgcac
>output
actcttcctttttcaatattattgaagcatttatcagggttattgtctcatgagcggatacatatttgaatgtatttagaaaaataaacaaataggggttccgcgcacatttccccgaaaagtgctagtggtgctagccccgcgaaattaatacgactcactatagggtctagaaataattttgtttaactttaagaaggagatatacatatgagcaagggcgaggagctgttcaccggggtggtgcccatcctggtcgagctggacggcgacgtaaacggccacaagttcagcgtgtccggcgagggtgagggcgatgccacctacggcaagctgaccctgaagttcatctgcaccacgggcaagctgcccgtgccctggcccaccctcgtgaccaccc

$ cd /tmp && python3 -m venv pv && pv/bin/pip install -q primer3-py 2>&1 | tail -2; pv/bin/python -c 'import primer3;print(primer3.__version__)'; which gcc make
The virtual environment was not created successfully because ensurepip is not
available.  On Debian/Ubuntu systems, you need to install the python3-venv
package using the following command.
    apt install python3.12-venv
You may need to use sudo with that command.  After installing the python3-venv
package, recreate your virtual environment.
Failing command: /tmp/pv/bin/python3
Traceback (most recent call last):
  File "<string>", line 1, in <module>
ModuleNotFoundError: No module named 'primer3'
/usr/bin/gcc
/usr/bin/make
Shell cwd was reset to /app

$ cd /tmp && pip install -q --break-system-packages primer3-py 2>&1 | tail -2; python3 -c 'import primer3;print(primer3.__version__)'
Exit code 1
/bin/bash: line 1: pip: command not found
Traceback (most recent call last):
  File "<string>", line 1, in <module>
ModuleNotFoundError: No module named 'primer3'

$ cd /tmp && python3 -m pip install -q --break-system-packages primer3-py 2>&1 | tail -3; python3 -c 'import primer3;print(primer3.__version__)'
Exit code 1
/usr/bin/python3: No module named pip
Traceback (most recent call last):
  File "<string>", line 1, in <module>
ModuleNotFoundError: No module named 'primer3'

$ cd /tmp && (curl -sI -m 15 https://github.com | head -1; curl -sI -m 15 https://pypi.org | head -1; which apt-get conda uv pipx easy_install)
Exit code 1
HTTP/2 200 
HTTP/2 200 
/usr/bin/apt-get

