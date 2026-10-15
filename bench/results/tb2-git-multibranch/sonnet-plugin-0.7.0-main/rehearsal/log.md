$ cd /app; ls -a .rehearsal; command -v sshd nginx git openssl sshpass curl useradd; id git; ls -d /git; head -2 /etc/os-release
.
..
active
fixtures
scaffold
/usr/sbin/sshd
/usr/sbin/nginx
/usr/bin/git
/usr/bin/openssl
/usr/bin/curl
/usr/sbin/useradd
id: 'git': no such user
ls: cannot access '/git': No such file or directory
PRETTY_NAME="Ubuntu 24.04.3 LTS"
NAME="Ubuntu"

$ mkdir -p /app/.rehearsal && cat >> /app/.rehearsal/REHEARSAL.md <<'EOF'
# Rehearsal: git+nginx deploy server
## Model
- sshd (password auth) -> bare repo /git/project -> post-receive -> /var/www/{main,dev} -> nginx :8443 self-signed
### S1: env check: sshd, nginx, git, openssl, curl present; no git user, no /git; sshpass missing
EOF
useradd -m -s /bin/bash git && echo 'git:password' | chpasswd && mkdir -p /git /var/www/main /var/www/dev && git init --bare -b main /git/project && chown -R git:git /git /var/www && id git
Initialized empty Git repository in /git/project/
uid=1001(git) gid=1001(git) groups=1001(git)

$ mkdir -p /etc/nginx/ssl && openssl req -x509 -newkey rsa:2048 -nodes -days 365 -subj /CN=localhost -addext "subjectAltName=DNS:localhost,IP:127.0.0.1" -keyout /etc/nginx/ssl/key.pem -out /etc/nginx/ssl/cert.pem 2>&1 | tail -1; ls /etc/nginx/sites-enabled /etc/nginx/conf.d
-----
/etc/nginx/conf.d:
/etc/nginx/sites-enabled:
default

$ rm -f /etc/nginx/sites-enabled/default
cat > /etc/nginx/conf.d/deploy.conf <<'EOF'
server {
    listen 8443 ssl;
    server_name localhost;
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    root /var/www/main;
    location /dev/ {
        alias /var/www/dev/;
    }
}
EOF
cat > /git/project/hooks/post-receive <<'EOF'
#!/bin/bash
while read old new ref; do
  branch=${ref#refs/heads/}
  case "$branch" in
    main) dest=/var/www/main ;;
    dev)  dest=/var/www/dev ;;
    *) continue ;;
  esac
  if [ "$new" = "0000000000000000000000000000000000000000" ]; then continue; fi
  git --work-tree="$dest" checkout -f "$branch"
done
EOF
chmod +x /git/project/hooks/post-receive; chown git:git /git/project/hooks/post-receive
printf 'PasswordAuthentication yes\nUsePAM yes\n' > /etc/ssh/sshd_config.d/pw.conf
nginx -t 2>&1; mkdir -p /run/sshd; nginx; /usr/sbin/sshd; ss -ltn | grep -E ':22|:8443'
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
LISTEN 0      511          0.0.0.0:8443       0.0.0.0:*          
LISTEN 0      128          0.0.0.0:22         0.0.0.0:*

$ (apt-get install -y sshpass >/dev/null 2>&1 || true); command -v sshpass
/usr/bin/sshpass

