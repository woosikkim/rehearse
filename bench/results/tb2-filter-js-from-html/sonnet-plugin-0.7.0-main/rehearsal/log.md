$ ls -la . .rehearsal 2>&1; python3 -c 'import bs4; print(bs4.__version__)' 2>&1; python3 -c 'import lxml; print(lxml.__version__)' 2>&1; python3 -c 'import html5lib; print(html5lib.__version__)' 2>&1; python3 -c 'import bleach; print(bleach.__version__)' 2>&1; python3 --version
.:
total 12
drwxr-xr-x 1 root root 4096 Oct 15 13:10 .
drwxr-xr-x 1 root root 4096 Oct 15 13:03 ..
drwxr-xr-x 4 root root 4096 Oct 15 13:10 .rehearsal
.rehearsal:
total 16
drwxr-xr-x 4 root root 4096 Oct 15 13:10 .
drwxr-xr-x 1 root root 4096 Oct 15 13:10 ..
-rw-r--r-- 1 root root    0 Oct 15 13:10 active
drwxr-xr-x 2 root root 4096 Oct 15 13:10 fixtures
drwxr-xr-x 2 root root 4096 Oct 15 13:10 scaffold
4.13.4
Traceback (most recent call last):
  File "<string>", line 1, in <module>
    import lxml; print(lxml.__version__)
    ^^^^^^^^^^^
ModuleNotFoundError: No module named 'lxml'
Traceback (most recent call last):
  File "<string>", line 1, in <module>
    import html5lib; print(html5lib.__version__)
    ^^^^^^^^^^^^^^^
ModuleNotFoundError: No module named 'html5lib'
Traceback (most recent call last):
  File "<string>", line 1, in <module>
    import bleach; print(bleach.__version__)
    ^^^^^^^^^^^^^
ModuleNotFoundError: No module named 'bleach'
Python 3.13.7

$ ls .rehearsal/fixtures; python3 -I -c 'import sys; from bs4 import BeautifulSoup; print(str(BeautifulSoup(sys.stdin.read(),"html.parser")))' < .rehearsal/fixtures/sample1.html
Exit code 1
/bin/bash: line 1: .rehearsal/fixtures/sample1.html: No such file or directory

$ python3 -I -c 'import sys; from bs4 import BeautifulSoup; print(str(BeautifulSoup(sys.stdin.read(),"html.parser")))' < .rehearsal/fixtures/sample1.html
<!DOCTYPE html>
<html><head><title>T</title><script>alert(1)</script><style>p{color:red}</style></head>
<body onload="x()"><h1 class="a">Head</h1>
<table border="1"><tr><td>1</td></tr></table>
<a href="javascript:alert(1)">bad</a> <a href=" JaVascript:alert(2)">bad2</a> <a href="http://ok/">ok</a>
<img onerror="alert(1)" src="x"/><iframe src="javascript:1"></iframe><object data="x"></object><embed src="x"/>
<svg><script>alert(1)</script></svg><!-- c --><p style="color:red">hi &amp; bye</p>
<form action="javascript:alert(1)"><button formaction="javascript:x">b</button></form>
</body></html>

