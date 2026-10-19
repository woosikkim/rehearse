"""Project code and its fingerprint (plan section 1).

Code files are hashed; data/config files are not (their changes are recorded from edit-tool calls).
Inside git: `git status --porcelain=v1 -z --untracked-files=all` plus sha1 of every listed code file;
unlisted tracked files are taken as unchanged. Outside git: a walk hashing every code file.
"""
import hashlib
import os
import subprocess

CODE_EXT = {".py", ".pyi", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".rb", ".php", ".go", ".rs", ".java",
            ".kt", ".c", ".cc", ".cpp", ".h", ".hpp", ".cs", ".swift", ".sh", ".bash"}
DATA_EXT = {".sql", ".toml", ".cfg", ".ini", ".yaml", ".yml", ".json", ".html", ".css"}
EXCLUDED = {"node_modules", "__pycache__", "site-packages", "dist", "build", ".git", ".tox", ".nox",
            ".mypy_cache", ".pytest_cache", ".rehearsal"}
BIG = 2 * 1024 * 1024


def _git(root, *args):
    try:
        return subprocess.run(["git", *args], cwd=root, capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None


def in_git(root):
    p = _git(root, "rev-parse", "--is-inside-work-tree")
    return bool(p) and p.returncode == 0


def excluded(root, rel):
    """True if a parent directory of rel (relative to root) is excluded: a venv, a listed name, a hidden dir."""
    parts = rel.replace(os.sep, "/").split("/")[:-1]
    d = root
    for part in parts:
        d = os.path.join(d, part)
        if part in EXCLUDED or part.startswith(".") or os.path.isfile(os.path.join(d, "pyvenv.cfg")):
            return True
    return False


def is_code(path):
    return os.path.splitext(str(path))[1] in CODE_EXT


def kind(root, path):
    """'code', 'data' or None: what a path is to this project (plan section 1, Project code)."""
    root = os.path.realpath(root)
    path = os.path.realpath(path)
    if not path.startswith(root + os.sep):
        return None
    rel = os.path.relpath(path, root)
    if excluded(root, rel):
        return None
    ext = os.path.splitext(path)[1]
    git = in_git(root)
    if git:
        ign = _git(root, "check-ignore", "-q", "--", rel)
        if ign and ign.returncode == 0:
            return None
    if ext in CODE_EXT:
        return "code"
    if ext in DATA_EXT:
        return "data"
    if git:
        tracked = _git(root, "ls-files", "--error-unmatch", "--", rel)
        if tracked and tracked.returncode == 0:
            return "data"
    return None


def _sig(path):
    """A signature compared for equality only, never for order: the sha1 of the whole file; for a big file, its
    size, its modification time at full resolution (any write changes it, even after a clock step back; 3.1.0
    truncated it to seconds) and the sha1 of its first and last 64 KB, together. Any difference means changed."""
    try:
        st = os.stat(path)
        with open(path, "rb") as f:
            if st.st_size <= BIG:
                return hashlib.sha1(f.read()).hexdigest()
            h = hashlib.sha1(b"%d:%d:" % (st.st_size, st.st_mtime_ns))
            h.update(f.read(65536))
            f.seek(-65536, os.SEEK_END)
            h.update(f.read(65536))
            return "big:" + h.hexdigest()
    except OSError:
        return "missing"


def walk(root):
    """Every file outside excluded directories, relative to root."""
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x not in EXCLUDED and not x.startswith(".")
                   and not os.path.isfile(os.path.join(d, x, "pyvenv.cfg"))]
        for f in files:
            yield os.path.relpath(os.path.join(d, f), root)


def project_files(root):
    """Every project-code path (both groups) relative to root."""
    if in_git(root):
        p = _git(root, "ls-files", "-co", "--exclude-standard", "-z", "--", ".")
        rels = [r for r in (p.stdout.decode("utf-8", "replace").split("\0") if p else []) if r]
        return [r for r in rels if not excluded(root, r)]
    return [r for r in walk(root) if os.path.splitext(r)[1] in CODE_EXT | DATA_EXT]


def fingerprint(root):
    root = os.path.realpath(root)
    files = {}
    if in_git(root):
        top = _git(root, "rev-parse", "--show-toplevel").stdout.decode().strip()
        p = _git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all", "--", ".")
        items = p.stdout.decode("utf-8", "replace").split("\0") if p else []
        k = 0
        while k < len(items):
            item = items[k]
            k += 1
            if len(item) < 4:
                continue
            if item[0] in "RC":
                k += 1  # a rename carries its old path as the next item
            rel = os.path.relpath(os.path.join(top, item[3:]), root)
            if rel.startswith("..") or not is_code(rel) or excluded(root, rel):
                continue
            files[rel] = item[:2] + ":" + _sig(os.path.join(root, rel))
        return {"git": True, "files": files}
    for rel in walk(root):
        if is_code(rel):
            files[rel] = _sig(os.path.join(root, rel))
    return {"git": False, "files": files}


def code_change(a, b):
    """Code-file paths whose fingerprint differs between a and b."""
    fa, fb = (a or {}).get("files", {}), (b or {}).get("files", {})
    return sorted(r for r in set(fa) | set(fb) if fa.get(r) != fb.get(r) and is_code(r))
