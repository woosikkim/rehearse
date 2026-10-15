$ command -v openssl python3; openssl version; python3 -c 'import cryptography; print(cryptography.__version__)'; ls -la /app /app/ssl 2>&1 | head -20; ls .rehearsal 2>&1
/usr/bin/openssl
/usr/local/bin/python3
OpenSSL 3.0.22 25 Aug 2026 (Library: OpenSSL 3.0.22 25 Aug 2026)
Traceback (most recent call last):
  File "<string>", line 1, in <module>
    import cryptography; print(cryptography.__version__)
    ^^^^^^^^^^^^^^^^^^^
ModuleNotFoundError: No module named 'cryptography'
ls: cannot access '/app/ssl': No such file or directory
/app:
total 12
drwxr-xr-x 1 root root 4096 Oct 15 12:31 .
drwxr-xr-x 1 root root 4096 Oct 15 12:26 ..
drwxr-xr-x 4 root root 4096 Oct 15 12:31 .rehearsal
active
fixtures
scaffold
trace.jsonl

$ mkdir -p /app/ssl && openssl genrsa -out /app/ssl/server.key 2048 2>&1 && chmod 600 /app/ssl/server.key && openssl req -new -x509 -key /app/ssl/server.key -out /app/ssl/server.crt -days 365 -subj "/O=DevOps Team/CN=dev-internal.company.local" && cat /app/ssl/server.key /app/ssl/server.crt > /app/ssl/server.pem && chmod 600 /app/ssl/server.pem && ls -l /app/ssl
total 12
-rw-r--r-- 1 root root 1220 Oct 15 12:31 server.crt
-rw------- 1 root root 1704 Oct 15 12:31 server.key
-rw------- 1 root root 2924 Oct 15 12:31 server.pem

$ openssl x509 -in /app/ssl/server.crt -noout -subject -startdate -enddate -fingerprint -sha256
subject=O = DevOps Team, CN = dev-internal.company.local
notBefore=Oct 15 12:31:39 2026 GMT
notAfter=Oct 15 12:31:39 2027 GMT
sha256 Fingerprint=9C:8B:E6:16:CB:1B:06:BB:A7:7A:6A:7F:B2:B0:E7:43:DC:DD:C4:CB:E5:3F:6C:D3:57:68:BD:09:05:64:E9:44

$ openssl x509 -in /app/ssl/server.crt -noout -subject -startdate -enddate -fingerprint -sha256 > /app/ssl/verification.txt && cat /app/ssl/verification.txt
cat >> .rehearsal/REHEARSAL.md <<'EOF'
# Rehearsal: self-signed cert
### S1: openssl genrsa/req -x509/cat pem/x509 -noout -subject -dates -fingerprint
- saw: subject O=DevOps Team, CN=dev-internal.company.local; notAfter Oct 15 2027 GMT
- means: no cryptography lib; check_cert.py must shell out to openssl, parse notAfter
EOF
subject=O = DevOps Team, CN = dev-internal.company.local
notBefore=Oct 15 12:31:39 2026 GMT
notAfter=Oct 15 12:31:39 2027 GMT
sha256 Fingerprint=9C:8B:E6:16:CB:1B:06:BB:A7:7A:6A:7F:B2:B0:E7:43:DC:DD:C4:CB:E5:3F:6C:D3:57:68:BD:09:05:64:E9:44

