#!/usr/bin/python3
"""下一步只做一件事：读哪个阶段文件，或者停下来等一句可以原样粘贴的回复。

不写 spec，不改业务代码，不派子代理。运行记录在 specs/<feature>/run.json。
产物目录一律是当前工作仓的仓库根：谁 install，记录就跟着谁，不回到技能源仓库。
"""

import glob
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime

import layout

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ME = os.path.abspath(__file__)
SKILL_ROOT = os.path.dirname(os.path.dirname(ME))
FEATURE_RE = re.compile(r"^[A-Za-z0-9._-]+$")
BUSINESS = ""
STORE = ""
BASH = shutil.which("bash") or ""


def shown(rel):
    if not STORE or not BUSINESS:
        return rel
    if os.path.realpath(STORE) == os.path.realpath(BUSINESS):
        return rel
    return os.path.join(STORE, rel)


def repo_root(explicit):
    if explicit:
        return os.path.abspath(explicit)
    try:
        out = subprocess.check_output(
            ["git", "-C", os.getcwd(), "rev-parse", "--show-toplevel"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return None
    return out or None


def read_yaml_key(path, key):
    if not os.path.isfile(path):
        return None
    prefix = key + ":"
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            if line.startswith(prefix):
                val = line.split(":", 1)[1].strip()
                if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
                    val = val[1:-1]
                val = re.sub(r"\s+#.*$", "", val).strip()
                return val
    return None


def config_value(root, key):
    if not root:
        return None
    candidates = []
    for tool in (".cursor", ".qoder", ".agents", ".claude", ".codex"):
        candidates.append(
            os.path.join(root, tool, "skills", "data-workflow", "config.yaml")
        )
    candidates.append(os.path.join(root, "config.yaml"))
    home = os.environ.get("HOME") or ""
    if home:
        candidates.append(os.path.join(home, ".config", "data-workflow", "config.yaml"))
    for path in candidates:
        val = read_yaml_key(path, key)
        if val:
            return val
    return None


def write_verify_log(root, feature, code, output):
    folder = os.path.join(root, "specs", feature)
    os.makedirs(folder, exist_ok=True)
    text = output or ""
    if len(text) > 8000:
        text = text[-8000:]
    with open(os.path.join(folder, "verify.log"), "w", encoding="utf-8") as fh:
        fh.write("exit %s\n" % code)
        fh.write(text)
        if text and not text.endswith("\n"):
            fh.write("\n")


def declared_verify(root):
    """仓库自己写明的那条测试命令。没有就空，不按语言猜一套。"""
    explicit = config_value(root, "verify")
    if explicit:
        return explicit
    package_json = os.path.join(root, "package.json")
    if os.path.isfile(package_json):
        try:
            with open(package_json, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError):
            data = {}
        script = (data.get("scripts") or {}).get("test") if isinstance(data, dict) else ""
        if script and script != 'echo "Error: no test specified" && exit 1':
            if os.path.isfile(os.path.join(root, "pnpm-lock.yaml")):
                return "pnpm test"
            if os.path.isfile(os.path.join(root, "yarn.lock")):
                return "yarn test"
            return "npm test"
    makefile = os.path.join(root, "Makefile")
    if os.path.isfile(makefile):
        try:
            with open(makefile, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            text = ""
        if re.search(r"(?m)^test:", text):
            return "make test"
    if os.path.isfile(os.path.join(root, "pytest.ini")) or os.path.isfile(
        os.path.join(root, "pyproject.toml")
    ):
        pyproject = os.path.join(root, "pyproject.toml")
        use_pytest = os.path.isfile(os.path.join(root, "pytest.ini"))
        if not use_pytest and os.path.isfile(pyproject):
            try:
                with open(pyproject, encoding="utf-8", errors="replace") as fh:
                    use_pytest = "[tool.pytest" in fh.read()
            except OSError:
                use_pytest = False
        if use_pytest:
            return "python3 -m pytest -q"
    if os.path.isfile(os.path.join(root, "Cargo.toml")):
        return "cargo test"
    # Go：go.mod 即声明的入口。go test 在无 *_test.go 时也能跑（ok / no test files），
    # 且退出码可信，不会把「没有测试」伪装成失败。
    if os.path.isfile(os.path.join(root, "go.mod")):
        return "go test ./..."
    return ""


def tail_lines(text, limit=8):
    lines = [line for line in (text or "").splitlines() if line.strip()]
    return lines[-limit:]


def fm_list_of(text, key):
    """取 frontmatter 里某个列表键的值。只读首个 --- 块。"""
    lines = text.splitlines()
    infm = False
    started = False
    inlist = False
    out = []
    for ln in lines:
        if not started and ln.strip() == "---":
            started = True
            infm = True
            continue
        if infm and ln.strip() == "---":
            break
        if not infm:
            continue
        if re.match(r"^%s\s*:" % re.escape(key), ln):
            inlist = True
            continue
        if inlist:
            m = re.match(r"^\s*-\s*(.+?)\s*$", ln)
            if m:
                out.append(m.group(1).strip("\"'"))
                continue
            if ln.strip():
                break
    return out


def knowledge_feedback(root, feature):
    """G7 判据：这次改动命中的域，其 verified_commit 必须等于 HEAD。

    返回 (ok, hits, detail)。hits 是命中的域文档相对路径。
    doc-watches 与这次 diff 求交；没有域文档或没有交集时返回 ok=True。
    """
    run = load_run(root, feature) or {}
    rows = run.get("stages") or []
    changed = []
    for row in rows:
        changed.extend(row.get("changed_files") or [])
    # run.json 不记 changed_files 时，退回 stage1 的 decision 里写的范围不靠谱，
    # 直接问 git：最后一次 commit 与工作树合计的改动文件。
    if not changed:
        for args in (["diff", "--name-only", "HEAD"], ["status", "--porcelain"]):
            p = subprocess.run(["git", "-C", root] + args,
                               capture_output=True, text=True, encoding="utf-8")
            if p.returncode != 0:
                continue
            for ln in p.stdout.splitlines():
                ln = ln.strip()
                if args[0] == "status":
                    ln = ln[3:] if len(ln) > 3 else ""
                if ln:
                    changed.append(ln)
    changed = set(c for c in changed if c)

    docs_dir = os.path.join(root, "docs", "domain")
    if not os.path.isdir(docs_dir):
        return True, [], "no docs/domain/"
    head = subprocess.run(["git", "-C", root, "rev-parse", "HEAD"],
                          capture_output=True, text=True, encoding="utf-8").stdout.strip()

    hits, stale = [], []
    for name in sorted(os.listdir(docs_dir)):
        if not name.endswith(".md"):
            continue
        path = os.path.join(docs_dir, name)
        text = read_text(path)
        watches = fm_list_of(text, "watches")
        if not watches:
            continue
        touched = False
        for w in watches:
            w = w.rstrip("/")
            for c in changed:
                if c == w or c.startswith(w + "/"):
                    touched = True
                    break
            if touched:
                break
        if not touched:
            continue
        rel = os.path.join("docs", "domain", name)
        hits.append(rel)
        m = re.search(r"^verified_commit\s*:\s*(\S+)", text, re.M)
        got = m.group(1).strip("\"'") if m else ""
        if not head or got != head:
            stale.append("%s（verified_commit=%s，HEAD=%s）"
                         % (rel, got[:8] or "无", head[:8] or "?"))
    if stale:
        return False, hits, "；".join(stale)
    return True, hits, ""


def run_gate_check(root, stage, feature):
    """stage.gate_check：一条命令，退出码就是门。

    没声明就返回 (True, "", "")——不编一个默认门。
    有 bash 时用 `bash -c` 跑，否则交给系统 shell（Windows 上就是 cmd，语法自理）。
    """
    cmd = (stage.get("gate_check") or "").strip()
    if not cmd:
        return True, "", ""
    cmd = cmd.replace("<feature>", feature)
    business = BUSINESS or root
    try:
        if BASH:
            proc = subprocess.run(
                [BASH, "-c", cmd],
                cwd=business,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=120,
            )
        else:
            proc = subprocess.run(
                cmd,
                shell=True,
                cwd=business,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=120,
            )
    except subprocess.TimeoutExpired:
        return False, cmd, "timeout 120s"
    return proc.returncode == 0, cmd, (proc.stdout or "") + (proc.stderr or "")


def run_verify(root, feature):
    """跑仓库声明的 verify。返回退出码：0 通过、非 0 失败、-1 未配置。

    返回码而不是布尔：证据行要写真的退出码（`verify=exit0` / `verify=exit1` / `verify=none`）。
    """
    business = BUSINESS or root
    cmd = declared_verify(business)
    if not cmd:
        print("RED")
        print("这个仓库没有可判定的测试入口。")
        print("在 config.yaml 写一行 verify，或在该目录放 package.json / Makefile(test:) / go.mod / Cargo.toml / pytest 配置。")
        print("例：verify: \"go build ./... && go test ./...\"")
        print("没有命令可跑就写明原因，不要写成通过。")
        return -1
    try:
        proc = subprocess.run(
            cmd,
            shell=True,
            cwd=business,
            capture_output=True,
            text=True,
            timeout=180,
        )
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or "") + (exc.stderr or "")
        write_verify_log(root, feature, 124, output if isinstance(output, str) else "")
        print("RED")
        print("VERIFY exit 124")
        print("LOG %s" % shown("specs/%s/verify.log" % feature))
        return 124
    output = "cmd %s\n" % cmd + (proc.stdout or "") + (proc.stderr or "")
    write_verify_log(root, feature, proc.returncode, output)
    print("VERIFY exit %s" % proc.returncode)
    print("LOG %s" % shown("specs/%s/verify.log" % feature))
    if proc.returncode != 0:
        print("RED")
        lines = [line for line in output.splitlines() if line.strip()]
        for line in lines[-8:]:
            print(line)
        return proc.returncode
    return 0


def load_workflow(name):
    if not FEATURE_RE.fullmatch(name or ""):
        return None
    path = os.path.join(SKILL_ROOT, "workflows", name + ".json")
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict) or not isinstance(data.get("stages"), list):
        return None
    data["kind"] = data.get("kind") or "execute"
    return data


def artifact_paths(artifact, feature):
    text = str(artifact).replace("<feature>", feature)
    text = text.replace("<artifacts_root>", "specs/" + feature)
    text = text.split("（")[0].strip()
    if not text or text.startswith("$"):
        return []
    if " " in text:
        text = text.split()[0]
    if any(ord(c) > 127 for c in text):
        return []
    if text.startswith("specs/"):
        return [text]
    if "*" in text or "?" in text:
        return []
    if re.fullmatch(r"[\w./~-]+", text) and (text.endswith(".md") or text.endswith(".patch")):
        return ["specs/%s/%s" % (feature, text.lstrip("/"))]
    return []


def stage_paths(stage, feature):
    """本阶段可判定的产物路径。没有就返回空表。

    不要兜底成 specs/<feature>/stage-<id>.md：那是 runner 自己造出来的文件名，
    任何文档都没写过，模型只能凭空捏一个交差。没有可判定产物就直说没有。
    """
    paths = []
    for item in stage.get("artifacts") or []:
        paths.extend(artifact_paths(item, feature))
    return paths


def satisfied(root, pattern):
    full = os.path.join(root, pattern)
    if any(ch in pattern for ch in "*?"):
        matches = glob.glob(full)
        return any(os.path.isfile(m) and os.path.getsize(m) > 0 for m in matches)
    return os.path.isfile(full) and os.path.getsize(full) > 0


def file_is_open(text):
    """文件里还有未拍板的选择吗。

    只看**行首标记**：一行以「待拍板」开头（允许 - * > 空格等前缀）。
    正文里提到这个词不算——否的话写文档时引用一下就误打 OPEN，
    而那个误报会让人不再相信这个信号。

    行首标记之后的内容就是未决问题本身；没有内容也算开着的。
    最后一个标记之后出现过「已拍板：」行就算已关闭。
    """
    open_at = -1
    closed_at = -1
    for match in re.finditer(r"^\s*(?:[-*>]\s*)?待拍板", text, re.M):
        open_at = match.start()
    for match in re.finditer(r"^\s*(?:[-*>]\s*)?已拍板[：:]", text, re.M):
        closed_at = match.start()
    if open_at < 0:
        return False
    return open_at > closed_at


def concrete_files(root, pattern):
    full = os.path.join(root, pattern)
    if any(ch in pattern for ch in "*?"):
        return [path for path in glob.glob(full) if os.path.isfile(path)]
    if os.path.isfile(full):
        return [full]
    return []


def read_text(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def open_decision(root, pattern):
    for path in concrete_files(root, pattern):
        if file_is_open(read_text(path)):
            return True
    return False


def unmet_requires(root, stage, paths):
    """stage.requires 里的字面量必须出现在本阶段的产物里。

    这是「内容门」：文件非空还不够，得写到点上（比如决定里必须有「未知」）。
    没写 artifacts、或者产物还没落盘时不检查——那不是门该拦的时候。
    """
    needed = stage.get("requires") or []
    if not needed or not paths:
        return []
    text = ""
    for pattern in paths:
        for path in concrete_files(root, pattern):
            text += read_text(path) + "\n"
    if not text:
        return []
    return [item for item in needed if item not in text]


def norm(text):
    return " ".join((text or "").split())


def restated_raw(root, paths):
    """「我理解你要的是」如果只是原话的复制，提醒一句。

    不拦。判断权在用户：写得对不对是人看出来的，不是脚本算出来的。
    这里只抓一种最低级的偷懒——把原话粘一遍当理解。
    """
    for pattern in paths:
        for path in concrete_files(root, pattern):
            text = read_text(path)
            raw = re.search(r"^\s*-?\s*原话[^：:]*[：:]\s*(.+)$", text, re.M)
            mine = re.search(r"^\s*-?\s*我理解你要的是[：:]\s*(.+)$", text, re.M)
            if not raw or not mine:
                continue
            a = norm(raw.group(1))
            b = norm(mine.group(1))
            if a and b and (a == b or (len(a) > 8 and a in b)):
                return path
    return ""


def close_decisions(root, paths, reply):
    line = "已拍板：%s\n" % reply
    for pattern in paths:
        for path in concrete_files(root, pattern):
            text = read_text(path)
            if not file_is_open(text):
                continue
            with open(path, "a", encoding="utf-8") as fh:
                if text and not text.endswith("\n"):
                    fh.write("\n")
                fh.write(line)


def run_path(root, feature):
    return os.path.join(root, "specs", feature, "run.json")


def load_run(root, feature):
    path = run_path(root, feature)
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        return None
    data["feature"] = feature
    return data


def save_run(root, run):
    feature = run["feature"]
    folder = os.path.join(root, "specs", feature)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, "run.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(run, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def list_runs(root):
    specs = os.path.join(root, "specs")
    found = []
    if not os.path.isdir(specs):
        return found
    for name in sorted(os.listdir(specs)):
        if not FEATURE_RE.fullmatch(name):
            continue
        path = os.path.join(specs, name, "run.json")
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict):
            found.append(
                (
                    name,
                    data.get("workflow") or "",
                    data.get("status") or "",
                )
            )
    return found


def is_finished(run):
    """这条运行是否已经结束。

    终态有三个，判定只在这一处。以前三处各写一遍 `not in ("done", "abandoned")`，
    加一个终态就要改三个地方——漏一个，运行就永远算「未完成」，
    会话钩子每次都注入 NOTICE，`start` 每次都打 ALREADY。
    """
    return run.get("status") in ("done", "closed", "abandoned")


def stage_at(workflow, stage_id):
    for stage in workflow["stages"]:
        if stage.get("id") == stage_id:
            return stage
    return None


def advance(workflow, run):
    stages = workflow["stages"]
    current = stage_at(workflow, run.get("stage"))
    if current is None:
        return False
    idx = stages.index(current)
    if idx + 1 >= len(stages):
        run["status"] = "done"
        return True
    run["stage"] = stages[idx + 1].get("id")
    run["status"] = "working"
    return True


def print_context(root, run):
    feature = run.get("feature") or ""
    print("RUN %s %s %s" % (feature, run.get("workflow") or "", run.get("status") or ""))
    print("RECORD %s" % shown("specs/%s/run.json" % feature))
    print("REPO %s" % root)
    print("SKILL %s" % SKILL_ROOT)
    raw = run.get("raw_request") or ""
    if raw:
        print("RAW %s" % raw)
    decided = last_decision(root, feature)
    if decided:
        print("DECIDED %s" % decided)
    note = head_note(root, feature)
    if note:
        print("NOTE %s" % note)


def last_decision(root, feature):
    """最近一次拍板。从产物里读，不另存一份——避免两处真相。"""
    folder = os.path.join(root, "specs", feature)
    found = []
    for pattern in ("*.md", "*/*.md"):
        for path in sorted(glob.glob(os.path.join(folder, pattern))):
            for line in read_text(path).splitlines():
                line = line.strip()
                if line.startswith("已拍板："):
                    found.append(line[len("已拍板："):].strip())
    return found[-1] if found else ""


def git_head(root):
    try:
        out = subprocess.check_output(
            ["git", "-C", root, "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return "nogit"
    return out or "nogit"


def last_evidence_head(root, feature):
    text = read_text(os.path.join(root, "specs", feature, "evidence.log"))
    head = ""
    for line in text.splitlines():
        for part in line.split():
            if part.startswith("head="):
                head = part[len("head="):]
    return head


def head_note(root, feature):
    """记录里的 head 与当前 HEAD 不一致时提醒。不阻塞，只提示。"""
    recorded = last_evidence_head(root, feature)
    if not recorded or recorded == "nogit":
        return ""
    now = git_head(BUSINESS or root)
    if not now or now == "nogit" or now == recorded:
        return ""
    return "工作树已变（记录 %s → 现在 %s）。已过的阶段按旧代码成立；改过的地方重新核对。" % (recorded, now)


CONFESS_QUESTIONS = [
    "我刚才有没有做「{scope}」没写的事（改了范围外的文件、顺手改了别的债）？",
    "我说的「验过了」，验的是哪个具体用例、期望什么输出、实际看到什么？对不上就说对不上。",
    "有没有我编了一个看起来合理、但从没查证过的路径 / 字段名 / 事实？",
]

# 各工作流里「决定写在哪」。自白的第一个问题要引对本任务那份，不能硬写 decision.md——
# bugfix / hotfix / feature 没有 decision.md，写错了 AI 会去找一个不存在的文件。
SCOPE_ARTIFACT = {
    "change": "decision.md",
    "feature": "需求与方案（requirement.md、plan.md）",
    "bugfix": "根因定位",
    "hotfix": "止血决策",
}


def confess_scope(workflow, stage):
    """自白第一个问题里的「{scope}」指什么产物。"""
    if stage.get("confess_scope"):
        return str(stage["confess_scope"])
    name = (workflow or {}).get("name") if isinstance(workflow, dict) else workflow
    return SCOPE_ARTIFACT.get(name or "", "这一步的产物")


def confess_path(root, feature, stage_id):
    return os.path.join(root, "specs", feature, "confess", "%s.md" % stage_id)


def needs_confess(stage):
    """哪些阶段要自白：会改代码的阶段，和核对阶段。

    写决定的阶段不迫问——它还没有可对账的动作。
    """
    if stage.get("code"):
        return True
    return bool(stage.get("confess")) or stage.get("name") in ("核对", "回归", "复现")


def confess_missing(root, feature, stage):
    if not needs_confess(stage):
        return False
    return not os.path.isfile(confess_path(root, feature, stage.get("id")))


def print_confess(root, feature, stage, workflow=None):
    """done 推进成功后单独打一次。写什么都不会影响推进——这是整个机制的要害。"""
    if not needs_confess(stage):
        return
    scope = confess_scope(workflow, stage)
    path = "specs/%s/confess/%s.md" % (feature, stage.get("id"))
    print()
    print("CONFESS %s" % shown(path))
    print("上面那一步已经过了门，下面这份不会改变它，也不会让流程退回。")
    print("只写事实，不写评价。没有可坦白的就写「无可坦白」——那也是合法答案。")
    for i, q in enumerate(CONFESS_QUESTIONS, 1):
        print("%d. %s" % (i, q.format(scope=scope)))


def print_unconfessed(root, feature, workflow):
    """收尾时点一下漏写的阶段。只提醒，不拦——一旦拦，「诚实有代价」就又回来了。"""
    missed = []
    for stage in workflow.get("stages") or []:
        if needs_confess(stage) and confess_missing(root, feature, stage):
            missed.append(str(stage.get("id")))
    if not missed:
        return
    print("UNCONFESSED 这几个阶段没写自白：%s（不影响这次运行，下次想补就补）" % ", ".join(missed))


def record_evidence(root, run, stage, verify_code=None, outcome=None):
    """推进成功时追加一行。只由 runner 写；行尾带 by=runner，手写的行没有。

    `outcome` 只在真的给了值时才追加这一列，所以所有历史行和已有的断言
    逐字不变——改证据格式等于让过去的所有记录换一种读法。
    """
    feature = run.get("feature") or ""
    folder = os.path.join(root, "specs", feature)
    os.makedirs(folder, exist_ok=True)
    row = "stage=%s requires=ok gate_check=%s verify=%s head=%s at=%s by=runner" % (
        stage.get("id"),
        "ok" if (stage.get("gate_check") or "").strip() else "none",
        "none" if verify_code is None else "exit%s" % verify_code,
        git_head(BUSINESS or root),
        datetime.now().astimezone().isoformat(timespec="seconds"),
    )
    if outcome is not None:
        row += " outcome=%s" % outcome
    with open(os.path.join(folder, "evidence.log"), "a", encoding="utf-8") as fh:
        fh.write(row + "\n")
    return row


def print_stage_hints(stage):
    """Print AI-facing hints from workflow JSON fields that the runner itself
    does not consume but the model should see. Only prints fields with a value.

    DATA_WORKFLOW_NO_HINTS=1 时不打印 SELF_CHECK。只给 C3 对照实验用（见
    docs/dev/c3-c9-experiment.md）——它必须只摘这一个字段，其余输出逐字不变，
    否则两组实验用的不是同一个 runner。
    """
    no_self_check = os.environ.get("DATA_WORKFLOW_NO_HINTS") == "1"
    hints = []
    sc = stage.get("self_check")
    if sc and not no_self_check:
        hints.append(("SELF_CHECK", sc))
    reads = stage.get("reads")
    if reads:
        if isinstance(reads, list):
            hints.append(("READS", ", ".join(str(r) for r in reads)))
        else:
            hints.append(("READS", str(reads)))
    note = stage.get("note")
    if note:
        hints.append(("NOTE", note))
    ogf = stage.get("on_gate_fail")
    if ogf:
        hints.append(("ON_GATE_FAIL", ogf))
    calls = stage.get("calls")
    if calls:
        if isinstance(calls, list):
            hints.append(("CALLS", ", ".join(str(c) for c in calls)))
        else:
            hints.append(("CALLS", str(calls)))
    sa = stage.get("subagents")
    if sa and isinstance(sa, dict):
        parts = []
        if sa.get("allowed") is not None:
            parts.append("allowed=%s" % sa["allowed"])
        if sa.get("criteria"):
            parts.append("criteria: %s" % sa["criteria"])
        if sa.get("forbidden"):
            parts.append("forbidden: %s" % ", ".join(sa["forbidden"]))
        if sa.get("reason"):
            parts.append("reason: %s" % sa["reason"])
        if parts:
            hints.append(("SUBAGENTS", "; ".join(parts)))
    for label, text in hints:
        print("%s: %s" % (label, text))
    # close_if 是机器判的（close 会跑它），但**存在本身**是 AI 需要知道的指令：
    # 不知道有出口，就会一直往下推那个已经修好的 bug。这里把指纹和要写的字面量
    # 摆到 AI 眼前，让它知道「不修也能结案」并且知道凭什么结。
    spec = close_if_spec(stage)
    if spec:
        print("CLOSE_IF: artifact=%s literal=%s outcome=%s" % (
            spec["artifact"],
            "、".join(spec["literal"]),
            spec["outcome"],
        ))
        print("  fingerprint: %s" % spec["fingerprint"])
        print("  ↑ 这一步可以不继续，而是关掉：把上面字面量写进 artifact，让 fingerprint 命令 exit 0，"
              "然后 %s close <feature>" % ME)
        print("  ↑ fingerprint 的极性：exit 0 表示「bug 仍然复现」。还没改成你这个 bug 的复现命令时它不会过。")
    elif "close_if" in stage:
        print("BAD close_if：artifact / literal（非空列表）/ fingerprint 三项都要写，否则 close 用不了")


def print_wait(root, run):
    print_context(root, run)
    print("WAIT")
    print("QUESTION " + (run.get("question") or ""))
    print("REPLY " + (run.get("reply") or ""))
    print("对方回的是 REPLY 这一句时，再运行：")
    print("%s answer %s %s" % (ME, run["feature"], json.dumps(run.get("reply") or "", ensure_ascii=False)))


def stage_gates_block(root, run, stage, paths, feature):
    """跑本阶段的机器门（待拍板 / requires / gate_check）。拦住了返回 True。

    `show()` 和 `cmd_done()` 各有一份副本的时候，`show()` 在 `code` 阶段**之前**
    就 `return` 了，于是 `code` 阶段的 OPEN / GATE / CHECK 从来没被 `next` 判过——
    而 `done` 会判。两个入口对同一个阶段给出不同结论，`next` 说「去做」，
    `done` 说「不许」，中间没有任何提示。这里只有一份，两个入口共用。

    返回 True 表示已经打印了拦住的原因，调用方别再往下走。
    """
    if any(open_decision(root, p) for p in paths):
        print_context(root, run)
        print("OPEN")
        print("STAGE %s %s" % (stage.get("id"), stage.get("name") or ""))
        print_stage_hints(stage)
        print("文件里还有待拍板。先运行 wait，reply 写成对方能原样粘贴的一句，然后停止。")
        print("%s wait %s \"<问题>\" \"<一句回复>\"" % (ME, feature))
        return True
    unmet = unmet_requires(root, stage, paths)
    if unmet:
        print_context(root, run)
        print("GATE")
        print("STAGE %s %s" % (stage.get("id"), stage.get("name") or ""))
        print_stage_hints(stage)
        print("缺：%s" % "、".join(unmet))
        print("READ %s" % stage.get("file"))
        print("补进本阶段产物后再运行：")
        print("%s next %s" % (ME, feature))
        return True
    ok, check_cmd, check_out = run_gate_check(root, stage, feature)
    if not ok:
        print_context(root, run)
        print("GATE")
        print("STAGE %s %s" % (stage.get("id"), stage.get("name") or ""))
        print_stage_hints(stage)
        print("CHECK %s" % check_cmd)
        for line in tail_lines(check_out):
            print(line)
        print("READ %s" % stage.get("file"))
        return True
    return False


def show(root, run):
    workflow = load_workflow(run.get("workflow") or "")
    if workflow is None:
        print("BAD workflow %s" % run.get("workflow"))
        return 1
    feature = run["feature"]
    guard = 0
    while guard <= len(workflow["stages"]):
        guard += 1
        if run.get("status") == "waiting":
            print_wait(root, run)
            return 0
        if run.get("status") == "abandoned":
            print("LAST %s" % feature)
            print("RECORD %s" % shown("specs/%s/run.json" % feature))
            return 0
        if run.get("status") == "done":
            print_context(root, run)
            print("DONE %s" % feature)
            print_unconfessed(root, feature, workflow)
            return 0
        if run.get("status") == "closed":
            print_context(root, run)
            print("CLOSED %s %s" % (feature, run.get("outcome") or "fixed"))
            print("RECORD %s" % shown("specs/%s/run.json" % feature))
            print_unconfessed(root, feature, workflow)
            return 0
        stage = stage_at(workflow, run.get("stage"))
        if stage is None:
            print_context(root, run)
            print("BAD stage %s" % run.get("stage"))
            return 1
        if workflow.get("kind") == "review" and stage.get("code"):
            print_context(root, run)
            print("BLOCK 审阅运行不进入改代码阶段")
            return 1
        paths = stage_paths(stage, feature)
        missing = [p for p in paths if not satisfied(root, p)]
        if missing:
            print_context(root, run)
            print("STAGE %s %s" % (stage.get("id"), stage.get("name") or ""))
            print("READ %s" % stage.get("file"))
            print_stage_hints(stage)
            for path in missing:
                print("NEED %s" % shown(path))
            print("写完后运行：")
            print("%s next %s" % (ME, feature))
            return 0
        # 门要在 code 分支之前：以前 code 阶段的 OPEN / GATE / CHECK 全部被跳过，
        # next 说 DO，done 说 GATE。paths 为空时不判（那些阶段本来就没有可检的产物）。
        if paths and stage_gates_block(root, run, stage, paths, feature):
            return 0
        copied = restated_raw(root, paths)
        if copied:
            print_context(root, run)
            print("NOTE 「我理解你要的是」看起来是原话的复制。换成你自己的话说一遍，或写「无歧义」。见 %s" % copied)
            print()
        if stage.get("code"):
            print_context(root, run)
            print("DO")
            print("STAGE %s %s" % (stage.get("id"), stage.get("name") or ""))
            print("READ %s" % stage.get("file"))
            print_stage_hints(stage)
            print("做完后运行：")
            print("%s done %s" % (ME, feature))
            return 0
        if not paths:
            print_context(root, run)
            print("STAGE %s %s" % (stage.get("id"), stage.get("name") or ""))
            print("READ %s" % stage.get("file"))
            print_stage_hints(stage)
            print("NO_ARTIFACT 本阶段没有可判定的产物文件（不编一个文件名）。做完后运行：")
            print("%s done %s" % (ME, feature))
            return 0
        if not advance(workflow, run):
            print("BAD stage %s" % run.get("stage"))
            return 1
        record_evidence(root, run, stage)
        save_run(root, run)
        print_confess(root, feature, stage, workflow)
    print_context(root, run)
    print("DONE %s" % feature)
    print_unconfessed(root, feature, workflow)
    return 0


def latest_run(root, runs):
    def mtime(item):
        path = run_path(root, item[0])
        try:
            return os.path.getmtime(path)
        except OSError:
            return 0

    return max(runs, key=mtime)


def cmd_next(root, feature):
    if feature:
        run = load_run(root, feature)
        if run is None:
            print("NO_RUN %s" % feature)
            return 1
        return show(root, run)
    runs = list_runs(root)
    open_runs = [item for item in runs
                 if item[2] not in ("done", "closed", "abandoned")]
    if not runs:
        print("NO_RUN")
        return 0
    if len(open_runs) > 1:
        print("MANY")
        print("REPO %s" % root)
        for name, workflow, status in open_runs:
            print("%s %s %s" % (name, workflow, status))
        print("指定：%s next <feature>" % ME)
        return 0
    if len(open_runs) == 1:
        return show(root, load_run(root, open_runs[0][0]))
    name = latest_run(root, runs)[0]
    print("LAST %s" % name)
    print("RECORD %s" % shown("specs/%s/run.json" % name))
    return 0


def cmd_start(root, workflow_name, feature, raw_request="", new=False):
    if not FEATURE_RE.fullmatch(feature or ""):
        print("BAD feature")
        return 1
    workflow = load_workflow(workflow_name)
    if workflow is None:
        print("BAD workflow %s" % workflow_name)
        return 1
    existing = load_run(root, feature)
    if existing and not is_finished(existing):
        if new:
            # 同名开新的一条：找最小的空闲后缀，绝不覆盖旧记录。
            # 旧运行留在那里，谁想回去看都还在。
            base = feature
            n = 2
            while os.path.exists(os.path.join(root, "specs", "%s-%d" % (base, n))):
                n += 1
            fresh = "%s-%d" % (base, n)
            print("NEW %s (from %s)" % (fresh, base))
            return cmd_start(root, workflow_name, fresh, raw_request, new=False)
        # 死路修复：以前这里直接 show(existing)，于是新需求被旧链条拽回去，
        # 而且看不出自己是被哪条旧运行拽回去的。现在把旧运行的 RAW / DECIDED
        # 原话一起打出来，让人自己判断是不是同一件事。
        print("ALREADY %s %s" % (feature, existing.get("status")))
        print_context(root, existing)
        print("这是一个还没结束的运行，不是失败。两条出路：")
        print("继续这条：%s next %s" % (ME, feature))
        print("另开一条：%s start %s %s --new" % (ME, workflow_name, feature))
        return 0
    if workflow_name in ("feature", "bugfix", "hotfix"):
        stack = config_value(root, "stack")
        if stack != "go":
            print(
                "STACK 项目未声明 stack=go（当前：%s）。feature/bugfix/hotfix 是 Go 栈模板，其 Go 门（go-style、contract_diff、go test ./api/...）不适用。任意仓库的 L3 或定架构建议 start change；要用 Go 栈链请先在该项目 config.yaml 写 stack: go。"
                % (stack or "未配置")
            )
    first = workflow["stages"][0]
    run = {
        "workflow": workflow_name,
        "feature": feature,
        "stage": first.get("id"),
        "status": "working",
        "question": "",
        "reply": "",
        "raw_request": (raw_request or "").strip(),
    }
    save_run(root, run)
    return show(root, run)


def cmd_wait(root, feature, question, reply):
    run = load_run(root, feature)
    if run is None:
        print("NO_RUN %s" % feature)
        return 1
    question = (question or "").strip()
    reply = (reply or "").strip()
    if not question or not reply:
        print("BAD wait 需要问题和一句可原样粘贴的回复")
        return 1
    run["status"] = "waiting"
    run["question"] = question
    run["reply"] = reply
    save_run(root, run)
    print_wait(root, run)
    return 0


def cmd_answer(root, feature, text):
    run = load_run(root, feature)
    if run is None:
        print("NO_RUN %s" % feature)
        return 1
    if run.get("status") != "waiting":
        return show(root, run)
    if norm(text) != norm(run.get("reply") or ""):
        print("MISMATCH")
        print("REPLY " + (run.get("reply") or ""))
        return 1
    reply = run.get("reply") or ""
    workflow = load_workflow(run.get("workflow") or "")
    stage = stage_at(workflow, run.get("stage")) if workflow else None
    if stage is not None:
        close_decisions(root, stage_paths(stage, feature), reply)
    run["last_reply"] = reply
    run["status"] = "working"
    run["question"] = ""
    run["reply"] = ""
    save_run(root, run)
    return show(root, run)


def cmd_done(root, feature):
    run = load_run(root, feature)
    if run is None:
        print("NO_RUN %s" % feature)
        return 1
    if run.get("status") == "waiting":
        print_wait(root, run)
        return 1
    if run.get("status") == "done":
        print_context(root, run)
        print("DONE %s" % feature)
        return 0
    if run.get("status") == "closed":
        # 已关掉的运行不再推进任何阶段。再 done 一次就是幂等的成功。
        print_context(root, run)
        print("CLOSED %s %s" % (feature, run.get("outcome") or "fixed"))
        return 0
    workflow = load_workflow(run.get("workflow") or "")
    if workflow is None:
        print("BAD workflow %s" % run.get("workflow"))
        return 1
    stage = stage_at(workflow, run.get("stage"))
    if stage is None:
        print("BAD stage %s" % run.get("stage"))
        return 1
    paths = stage_paths(stage, feature)
    missing = [p for p in paths if not satisfied(root, p)]
    if missing and not stage.get("code"):
        print_context(root, run)
        print("STAGE %s %s" % (stage.get("id"), stage.get("name") or ""))
        print("READ %s" % stage.get("file"))
        print_stage_hints(stage)
        for path in missing:
            print("NEED %s" % shown(path))
        print("写完后运行：")
        print("%s next %s" % (ME, feature))
        return 1
    if stage_gates_block(root, run, stage, paths, feature):
        return 1
    if stage.get("knowledge_feedback"):
        kf_ok, kf_hits, kf_detail = knowledge_feedback(root, feature)
        if not kf_ok:
            print_context(root, run)
            print("GATE")
            print("STAGE %s %s" % (stage.get("id"), stage.get("name") or ""))
            print_stage_hints(stage)
            print("G7 知识反哺：这次改动命中了域文档，但 verified_commit 没跟上")
            for line in kf_hits:
                print("HIT %s" % line)
            print("DETAIL %s" % kf_detail)
            print("按 references/edit-gate.md 的口径：指针类可自动刷新，口径类只标冲突不改结论。")
            print("READ %s" % stage.get("file"))
            return 1
    verify_code = None
    if stage.get("code"):
        verify_code = run_verify(root, feature)
        if verify_code != 0:
            return 1
    if not advance(workflow, run):
        return 1
    record_evidence(root, run, stage, verify_code)
    save_run(root, run)
    show(root, run)
    # show() 已经把下一步打印完了；自白追加在后面，不改变任何判定。
    print_confess(root, feature, stage, workflow)
    return 0


def cmd_approve(root, feature, kind, prefix, reason=""):
    """写放行行。只有已经问过人、且人回过话（run.json 里 last_reply 非空）才写。

    gate_edit 在 gate_strict 下只认末尾带 `approved` 标记的行；手写的行不带它。
    """
    run = load_run(root, feature)
    if run is None:
        print("NO_RUN %s" % feature)
        return 1
    if kind not in ("design", "waiver"):
        print("BAD approve 需要 design 或 waiver")
        return 1
    prefix = (prefix or "").strip().strip("/")
    if not prefix or " " in prefix or ".." in prefix.split("/"):
        print("BAD 前缀要相对仓库根、不含空格")
        return 1
    reply = (run.get("last_reply") or "").strip()
    if not reply:
        print("NEED_ANSWER 没有已答复的拍板。先 wait，等对方回 REPLY 那一句并 answer，然后才能 approve。")
        print("这一行没有写进 specs/passes.log。")
        return 1
    stamp = datetime.now().astimezone().isoformat(timespec="seconds")
    trail = 'approved %s "%s"' % (stamp, reply.replace('"', "'"))
    if kind == "design":
        line = "design %s %s %s" % (feature, prefix, trail)
    else:
        line = "waiver %s %s %s" % (prefix, (reason or "内部改动").strip(), trail)
    folder = os.path.join(root, "specs")
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, "passes.log"), "a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    print("APPROVED %s" % line)
    print("RECORD %s" % shown("specs/passes.log"))
    return 0


def cmd_abandon(root, feature):
    run = load_run(root, feature)
    if run is None:
        print("NO_RUN %s" % feature)
        return 1
    run["status"] = "abandoned"
    run["question"] = ""
    run["reply"] = ""
    save_run(root, run)
    print("LAST %s" % feature)
    print("RECORD %s" % shown("specs/%s/run.json" % feature))
    return 0


def close_if_spec(stage):
    """读 stage.close_if。合格返回规范化的 dict，不合格返回 None。

    三项都要非空：
      artifact     可机器解析的产物文件（走 artifact_paths，所以中文项当场就落空）
      literal      列表，每一条都必须在产物里出现
      fingerprint  一条命令，exit 0 表示**这个 bug 仍然能复现**

    为什么不用 requires 的语义：`requires` 是全文子串匹配，「无法复现，已修复」
    也含「复现」二字，拿它当门等于把门退化成第二个「未知=无」（见
    docs/dev/learnings.md：未知栏 88% 写「无」，就是因为没有外部锚点）。
    字面量只能证明「写了」，fingerprint 才能证明「现在真的不坏」。
    """
    spec = stage.get("close_if")
    if not isinstance(spec, dict):
        return None
    artifact = spec.get("artifact")
    literal = spec.get("literal")
    fingerprint = spec.get("fingerprint")
    if not isinstance(artifact, str) or not artifact.strip():
        return None
    if not isinstance(literal, list) or not literal:
        return None
    if not all(isinstance(item, str) and item.strip() for item in literal):
        return None
    if not isinstance(fingerprint, str) or not fingerprint.strip():
        return None
    outcome = spec.get("outcome") or "fixed"
    return {
        "artifact": artifact.strip(),
        "literal": [item.strip() for item in literal],
        "fingerprint": fingerprint.strip(),
        "outcome": str(outcome),
    }


def close_artifact_path(spec, feature):
    """close_if.artifact 落成仓库相对路径。落不了就返回空串（由调用方报 BAD）。"""
    paths = artifact_paths(spec["artifact"], feature)
    return paths[0] if paths else ""


def cmd_close(root, feature):
    """已修的 bug 的出口：不是一个新阶段，是一次终止判定。

    只在显式敲 close 时才评，不在 next 里自动评：next 必须是只读的
    （钩子、C3 实验、case_no_hints_switch 都依赖它不改 run.json），
    而且「关掉」是一个有代价的决定，该由人/AI 主动确认，不该是滑块自己走到的位置。
    """
    run = load_run(root, feature)
    if run is None:
        print("NO_RUN %s" % feature)
        return 1
    if is_finished(run):
        # 幂等：已经结束了就只报一声，不重复写证据、不推进阶段。
        print_context(root, run)
        print("CLOSED %s %s" % (feature, run.get("outcome") or "fixed"))
        return 0
    workflow = load_workflow(run.get("workflow") or "")
    if workflow is None:
        print("BAD workflow %s" % run.get("workflow"))
        return 1
    stage = stage_at(workflow, run.get("stage"))
    if stage is None:
        print("BAD stage %s" % run.get("stage"))
        return 1
    malformed = "close_if" in stage and close_if_spec(stage) is None
    spec = close_if_spec(stage)
    if malformed:
        # 配错了必须响。静默地把出口禁掉，比报错更难发现。
        print("BAD close_if stage %s：artifact / literal（非空列表）/ fingerprint 三项都要写" % stage.get("id"))
        return 1
    if spec is None:
        print("NO_EXIT %s %s" % (feature, stage.get("id")))
        print("STAGE %s %s" % (stage.get("id"), stage.get("name") or ""))
        print("这个阶段没有 close_if，没有早退出口。要么继续走完，要么用 abandon 结束。")
        return 1
    path = close_artifact_path(spec, feature)
    if not path:
        print("BAD close_if：artifact %r 解析不出可判定的文件路径（中文项 / 通配符 / 以 $ 开头都不行）"
              % spec["artifact"])
        return 1
    if not satisfied(root, path):
        print_context(root, run)
        print("NEED %s" % shown(path))
        print("先写出关闭证据，再运行：")
        print("%s close %s" % (ME, feature))
        return 1
    text = ""
    for concrete in concrete_files(root, path):
        text += read_text(concrete) + "\n"
    unmet = [item for item in spec["literal"] if item not in text]
    if unmet:
        print_context(root, run)
        print("GATE")
        print("STAGE %s %s" % (stage.get("id"), stage.get("name") or ""))
        print("缺：%s" % "、".join(unmet))
        print("READ %s" % shown(path))
        print("写进 %s 后再运行：" % shown(path))
        print("%s close %s" % (ME, feature))
        return 1
    # 极性：fingerprint 是「复现命令」，exit 0 = bug 仍然复现。而 run_gate_check 的
    # `ok` 是「命令成功」——正好相反，所以必须在这里取反。
    # 弄反的后果是：bug 还好好的时候把单关掉，而且不报错、不留痕。
    reproduces, check_cmd, check_out = run_gate_check(
        root, {"gate_check": spec["fingerprint"]}, feature)
    if reproduces:
        print_context(root, run)
        print("CHECK %s" % check_cmd)
        for line in tail_lines(check_out):
            print(line)
        print("复现指纹仍成立：bug 还在，不能关。要么继续修，要么写明为什么不修（abandon）。")
        return 1
    outcome = spec["outcome"]
    run["status"] = "closed"
    run["outcome"] = outcome
    run["closed_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    run["closed_by"] = "runner"
    run["question"] = ""
    run["reply"] = ""
    record_evidence(root, run, stage, outcome=outcome)
    save_run(root, run)
    print_context(root, run)
    print("CLOSED %s %s" % (feature, outcome))
    print("EVIDENCE %s" % shown("specs/%s/evidence.log" % feature))
    print("RECORD %s" % shown("specs/%s/run.json" % feature))
    print_unconfessed(root, feature, workflow)
    return 0


def usage():
    print("用法: workflow_next.py next [feature] [--repo DIR]")
    print("      workflow_next.py start <workflow> <feature> [\"<用户原话>\"] [--new] [--repo DIR]")
    print("      workflow_next.py wait <feature> <问题> <一句回复> [--repo DIR]")
    print("      workflow_next.py answer <feature> <回复原文> [--repo DIR]")
    print("      workflow_next.py done <feature> [--repo DIR]")
    print("      workflow_next.py close <feature> [--repo DIR]")
    print("      workflow_next.py approve <feature> <design|waiver> <前缀> [原因] [--repo DIR]")
    print("      workflow_next.py abandon <feature> [--repo DIR]")
    return 2


def main(argv):
    args = list(argv)
    root = None
    if "--repo" in args:
        idx = args.index("--repo")
        if idx + 1 >= len(args):
            return usage()
        root = args[idx + 1]
        del args[idx : idx + 2]
    # --new 先摘出来，否则下面的 len(args) in (3, 4) 会被它撑坏。
    new = "--new" in args
    if new:
        args = [item for item in args if item != "--new"]
    root = repo_root(root)
    if not root or not os.path.isdir(root):
        print("BAD repo")
        return 1
    global BUSINESS, STORE
    BUSINESS = root
    STORE = layout.store_root(root, SKILL_ROOT)
    root = STORE
    if not args:
        return usage()
    cmd = args[0]
    if cmd == "next":
        feature = args[1] if len(args) > 1 else ""
        if feature and not FEATURE_RE.fullmatch(feature):
            print("BAD feature")
            return 1
        return cmd_next(root, feature)
    if cmd == "start" and len(args) in (3, 4):
        raw = args[3] if len(args) == 4 else ""
        return cmd_start(root, args[1], args[2], raw, new=new)
    if cmd == "wait" and len(args) == 4:
        return cmd_wait(root, args[1], args[2], args[3])
    if cmd == "answer" and len(args) >= 3:
        return cmd_answer(root, args[1], " ".join(args[2:]))
    if cmd == "done" and len(args) == 2:
        return cmd_done(root, args[1])
    if cmd == "close" and len(args) == 2:
        return cmd_close(root, args[1])
    if cmd == "approve" and len(args) >= 4:
        return cmd_approve(root, args[1], args[2], args[3], " ".join(args[4:]))
    if cmd == "abandon" and len(args) == 2:
        return cmd_abandon(root, args[1])
    return usage()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
