"""运行产物放在哪。

本仓库自己使用时，写仓库根的 specs/。
装进别的仓库时，写技能来源仓库的 runs/<仓库名>/，不写进被测仓库。
DATA_WORKFLOW_STORE 或配置 artifacts_root 优先。
"""

import os
import re
import subprocess


def git_root(start):
    try:
        out = subprocess.check_output(
            ["git", "-C", start, "rev-parse", "--show-toplevel"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return ""
    return os.path.realpath(out) if out else ""


def read_yaml_key(path, key):
    if not os.path.isfile(path):
        return ""
    prefix = key + ":"
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
    except OSError:
        return ""
    for line in lines:
        if line.startswith("#") or not line.startswith(prefix):
            continue
        val = line.split(":", 1)[1].strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        val = re.sub(r"\s+#.*$", "", val).strip()
        return val
    return ""


def configured_store(repo):
    env = os.environ.get("DATA_WORKFLOW_STORE") or ""
    if env:
        return os.path.realpath(env)
    for tool in (".cursor", ".qoder", ".agents", ".claude", ".codex"):
        val = read_yaml_key(
            os.path.join(repo, tool, "skills", "data-workflow", "config.yaml"),
            "artifacts_root",
        )
        if val:
            return os.path.realpath(val)
    val = read_yaml_key(os.path.join(repo, "config.yaml"), "artifacts_root")
    if val:
        return os.path.realpath(val)
    return ""


def store_root(repo, skill_root):
    forced = configured_store(repo)
    if forced:
        return forced
    repo_real = os.path.realpath(repo)
    skill_real = os.path.realpath(skill_root)
    own = git_root(skill_real)
    if own and own == repo_real:
        return repo_real
    origin = os.path.join(skill_real, "origin")
    base = ""
    if os.path.isfile(origin):
        try:
            with open(origin, encoding="utf-8") as fh:
                base = fh.read().strip()
        except OSError:
            base = ""
    if not base or not os.path.isdir(base):
        base = own or skill_real
    name = os.path.basename(repo_real) or "repo"
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip("-") or "repo"
    path = os.path.join(os.path.realpath(base), "runs", name)
    os.makedirs(path, exist_ok=True)
    return path
