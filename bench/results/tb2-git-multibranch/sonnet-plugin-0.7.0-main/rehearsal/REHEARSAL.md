# Rehearsal: git+nginx deploy server
## Model
- sshd (password auth) -> bare repo /git/project -> post-receive -> /var/www/{main,dev} -> nginx :8443 self-signed
### S1: env check: sshd, nginx, git, openssl, curl present; no git user, no /git; sshpass missing
