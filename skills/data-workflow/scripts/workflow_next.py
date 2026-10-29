#!/usr/bin/python3
"""下一步只做一件事：读哪个阶段文件，或者停下来等一句可以原样粘贴的回复。

不写 spec，不改业务代码，不派子代理。运行记录在产物目录的 specs/<feature>/run.json。
装进别的仓库时，产物目录在技能来源仓库的 runs/<仓库名>/。
"""

import glob
import json
import os
import re
import subprocess
import sys

import layout

ME = os.path.abspath(__file__)
SKILL_ROOT = os.path.dirname(os.path.dirname(ME))
FEATURE_RE = re.compile(r"^[A-Za-z0-9._-]+$")
BUSINESS = ""
STORE = ""


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
    return ""


def run_verify(root, feature):
    business = BUSINESS or root
    cmd = declared_verify(business)
    if not cmd:
        print("RED")
        print("verify 未配置")
        return False
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
        return False
    output = "cmd %s\n" % cmd + (proc.stdout or "") + (proc.stderr or "")
    write_verify_log(root, feature, proc.returncode, output)
    print("VERIFY exit %s" % proc.returncode)
    print("LOG %s" % shown("specs/%s/verify.log" % feature))
    if proc.returncode != 0:
        print("RED")
        lines = [line for line in output.splitlines() if line.strip()]
        for line in lines[-8:]:
            print(line)
        return False
    return True


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
    paths = []
    for item in stage.get("artifacts") or []:
        paths.extend(artifact_paths(item, feature))
    if paths or stage.get("code"):
        return paths
    return ["specs/%s/stage-%s.md" % (feature, stage.get("id"))]


def satisfied(root, pattern):
    full = os.path.join(root, pattern)
    if any(ch in pattern for ch in "*?"):
        matches = glob.glob(full)
        return any(os.path.isfile(m) and os.path.getsize(m) > 0 for m in matches)
    return os.path.isfile(full) and os.path.getsize(full) > 0


def file_is_open(text):
    last_open = text.rfind("待拍板")
    if last_open < 0:
        return False
    return last_open > text.rfind("已拍板：")


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


def print_wait(root, run):
    print_context(root, run)
    print("WAIT")
    print("QUESTION " + (run.get("question") or ""))
    print("REPLY " + (run.get("reply") or ""))
    print("对方回的是 REPLY 这一句时，再运行：")
    print("%s answer %s %s" % (ME, run["feature"], json.dumps(run.get("reply") or "", ensure_ascii=False)))


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
            for path in missing:
                print("NEED %s" % shown(path))
            print("写完后运行：")
            print("%s next %s" % (ME, feature))
            return 0
        if any(open_decision(root, p) for p in paths):
            print_context(root, run)
            print("OPEN")
            print("STAGE %s %s" % (stage.get("id"), stage.get("name") or ""))
            print("文件里还有待拍板。先运行 wait，reply 写成对方能原样粘贴的一句，然后停止。")
            print("%s wait %s \"<问题>\" \"<一句回复>\"" % (ME, feature))
            return 0
        if stage.get("code"):
            print_context(root, run)
            print("DO")
            print("STAGE %s %s" % (stage.get("id"), stage.get("name") or ""))
            print("READ %s" % stage.get("file"))
            print("做完后运行：")
            print("%s done %s" % (ME, feature))
            return 0
        if not advance(workflow, run):
            print("BAD stage %s" % run.get("stage"))
            return 1
        save_run(root, run)
    print_context(root, run)
    print("DONE %s" % feature)
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
    open_runs = [item for item in runs if item[2] not in ("done", "abandoned")]
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


def cmd_start(root, workflow_name, feature):
    if not FEATURE_RE.fullmatch(feature or ""):
        print("BAD feature")
        return 1
    workflow = load_workflow(workflow_name)
    if workflow is None:
        print("BAD workflow %s" % workflow_name)
        return 1
    existing = load_run(root, feature)
    if existing and existing.get("status") not in ("done", "abandoned"):
        print("ALREADY %s %s" % (feature, existing.get("status")))
        return show(root, existing)
    first = workflow["stages"][0]
    run = {
        "workflow": workflow_name,
        "feature": feature,
        "stage": first.get("id"),
        "status": "working",
        "question": "",
        "reply": "",
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


def norm(text):
    return " ".join((text or "").split())


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
        for path in missing:
            print("NEED %s" % shown(path))
        print("写完后运行：")
        print("%s next %s" % (ME, feature))
        return 1
    if any(open_decision(root, p) for p in paths):
        print_context(root, run)
        print("OPEN")
        print("文件里还有待拍板。先 wait，再 answer。")
        return 1
    if stage.get("code") and not run_verify(root, feature):
        return 1
    if not advance(workflow, run):
        return 1
    save_run(root, run)
    return show(root, run)


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


def usage():
    print("用法: workflow_next.py next [feature] [--repo DIR]")
    print("      workflow_next.py start <workflow> <feature> [--repo DIR]")
    print("      workflow_next.py wait <feature> <问题> <一句回复> [--repo DIR]")
    print("      workflow_next.py answer <feature> <回复原文> [--repo DIR]")
    print("      workflow_next.py done <feature> [--repo DIR]")
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
    if cmd == "start" and len(args) == 3:
        return cmd_start(root, args[1], args[2])
    if cmd == "wait" and len(args) == 4:
        return cmd_wait(root, args[1], args[2], args[3])
    if cmd == "answer" and len(args) >= 3:
        return cmd_answer(root, args[1], " ".join(args[2:]))
    if cmd == "done" and len(args) == 2:
        return cmd_done(root, args[1])
    if cmd == "abandon" and len(args) == 2:
        return cmd_abandon(root, args[1])
    return usage()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
