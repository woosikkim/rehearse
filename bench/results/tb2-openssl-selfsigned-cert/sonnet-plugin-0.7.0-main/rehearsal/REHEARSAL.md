# Rehearsal: self-signed cert
### S1: openssl genrsa/req -x509/cat pem/x509 -noout -subject -dates -fingerprint
- saw: subject O=DevOps Team, CN=dev-internal.company.local; notAfter Oct 15 2027 GMT
- means: no cryptography lib; check_cert.py must shell out to openssl, parse notAfter

## Sweep
| Place | Caller or sibling | Called with | Saw | Fixed |
|-------|-------------------|-------------|-----|-------|
| check_cert.py | only new file; no other callers or siblings in /app | missing cert, junk cert (rc=1, no success line) | handled | n/a |
