#!/usr/bin/python3
"""临时仓库上的外部行为。

编码步骤的 done：没有检查入口、package.json 的 test、Makefile 的 test、
只有 go.mod、显式 verify 盖过 package.json。
会话钩子：没有运行、只有已完成运行时不注入。有未完成运行时注入 NOTICE，不注入 next 的操作指令，也不改 run.json。
"""

import json
import os
import shutil
import subprocess
import tempfile

ME = os.path.abspath(__file__)
SKILL_ROOT = os.path.dirname(os.path.dirname(ME))
REPO_ROOT = os.path.dirname(os.path.dirname(SKILL_ROOT))
RUNNER = os.path.join(SKILL_ROOT, "scripts", "workflow_next.py")
HOOK = os.path.join(SKILL_ROOT, "hooks", "session-start")
INSTALL = os.path.join(REPO_ROOT, "scripts", "install.sh")
FEATURE = "probe"


def run(root, *args):
    return subprocess.run(
        [RUNNER, *args, "--repo", root],
        capture_output=True,
        text=True,
    )


def read_run(root):
    path = os.path.join(root, "specs", FEATURE, "run.json")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def reach_code(root):
    start = run(root, "start", "change", FEATURE)
    if start.returncode != 0:
        raise SystemExit(start.stdout + start.stderr)
    folder = os.path.join(root, "specs", FEATURE)
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, "decision.md"), "w", encoding="utf-8") as fh:
        fh.write("改一处。\n")
    done = run(root, "done", FEATURE)
    if done.returncode != 0 or read_run(root).get("stage") != 2:
        raise SystemExit(done.stdout + done.stderr)
    return done


def finish_code(root):
    return run(root, "done", FEATURE)


def log_text(root):
    path = os.path.join(root, "specs", FEATURE, "verify.log")
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def expect(ok, label, detail):
    if ok:
        print("PASS " + label)
        return
    print("FAIL " + label)
    print(detail)
    raise SystemExit(1)


def case_none():
    root = tempfile.mkdtemp(prefix="dw-none-")
    try:
        reach_code(root)
        done = finish_code(root)
        expect(
            done.returncode != 0
            and read_run(root).get("stage") == 2
            and "RED" in done.stdout
            and "verify 未配置" in done.stdout,
            "none stays RED",
            done.stdout + done.stderr,
        )
    finally:
        shutil.rmtree(root, ignore_errors=True)


def case_npm():
    root = tempfile.mkdtemp(prefix="dw-npm-")
    try:
        with open(os.path.join(root, "package.json"), "w", encoding="utf-8") as fh:
            json.dump({"scripts": {"test": "true"}}, fh)
        with open(os.path.join(root, "package-lock.json"), "w", encoding="utf-8") as fh:
            fh.write("{}\n")
        reach_code(root)
        done = finish_code(root)
        log = log_text(root) if os.path.isfile(os.path.join(root, "specs", FEATURE, "verify.log")) else ""
        expect(
            done.returncode == 0
            and read_run(root).get("stage") == 3
            and "cmd npm test" in log,
            "npm test advances",
            done.stdout + done.stderr + log,
        )
    finally:
        shutil.rmtree(root, ignore_errors=True)


def case_make():
    root = tempfile.mkdtemp(prefix="dw-make-")
    try:
        with open(os.path.join(root, "Makefile"), "w", encoding="utf-8") as fh:
            fh.write("test:\n\ttrue\n")
        reach_code(root)
        done = finish_code(root)
        log = log_text(root) if os.path.isfile(os.path.join(root, "specs", FEATURE, "verify.log")) else ""
        expect(
            done.returncode == 0
            and read_run(root).get("stage") == 3
            and "cmd make test" in log,
            "make test advances",
            done.stdout + done.stderr + log,
        )
    finally:
        shutil.rmtree(root, ignore_errors=True)


def case_gomod():
    root = tempfile.mkdtemp(prefix="dw-go-")
    try:
        with open(os.path.join(root, "go.mod"), "w", encoding="utf-8") as fh:
            fh.write("module example.com/probe\n\ngo 1.22\n")
        reach_code(root)
        done = finish_code(root)
        expect(
            done.returncode != 0
            and read_run(root).get("stage") == 2
            and "RED" in done.stdout
            and "verify 未配置" in done.stdout,
            "go.mod only stays RED",
            done.stdout + done.stderr,
        )
    finally:
        shutil.rmtree(root, ignore_errors=True)


def case_verify_wins():
    root = tempfile.mkdtemp(prefix="dw-verify-")
    try:
        with open(os.path.join(root, "package.json"), "w", encoding="utf-8") as fh:
            json.dump({"scripts": {"test": "true"}}, fh)
        with open(os.path.join(root, "config.yaml"), "w", encoding="utf-8") as fh:
            fh.write('verify: "false"\n')
        reach_code(root)
        done = finish_code(root)
        log = log_text(root) if os.path.isfile(os.path.join(root, "specs", FEATURE, "verify.log")) else ""
        expect(
            done.returncode != 0
            and read_run(root).get("stage") == 2
            and "RED" in done.stdout
            and "cmd false" in log,
            "explicit verify stops",
            done.stdout + done.stderr + log,
        )
    finally:
        shutil.rmtree(root, ignore_errors=True)


def git_init(root):
    subprocess.run(["git", "init", "-q", root], check=True)


def hook_text(root):
    proc = subprocess.run(
        [HOOK],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(proc.stdout)
    return data.get("additional_context") or ""


def case_hook_quiet():
    empty = tempfile.mkdtemp(prefix="dw-hook-empty-")
    done = tempfile.mkdtemp(prefix="dw-hook-done-")
    open_root = tempfile.mkdtemp(prefix="dw-hook-open-")
    try:
        git_init(empty)
        expect(hook_text(empty) == "", "no run injects nothing", hook_text(empty))

        git_init(done)
        folder = os.path.join(done, "specs", "finished")
        os.makedirs(folder)
        with open(os.path.join(folder, "run.json"), "w", encoding="utf-8") as fh:
            json.dump(
                {
                    "workflow": "change",
                    "feature": "finished",
                    "stage": 3,
                    "status": "done",
                    "question": "",
                    "reply": "",
                },
                fh,
            )
        expect(hook_text(done) == "", "finished run injects nothing", hook_text(done))

        left = tempfile.mkdtemp(prefix="dw-hook-left-")
        try:
            git_init(left)
            folder = os.path.join(left, "specs", "old")
            os.makedirs(folder)
            with open(os.path.join(folder, "run.json"), "w", encoding="utf-8") as fh:
                json.dump(
                    {
                        "workflow": "change",
                        "feature": "old",
                        "stage": 2,
                        "status": "working",
                        "question": "",
                        "reply": "",
                    },
                    fh,
                )
            dropped = run(left, "abandon", "old")
            status = json.load(open(os.path.join(folder, "run.json"), encoding="utf-8")).get("status")
            injected = hook_text(left)
            expect(
                dropped.returncode == 0 and injected == "" and status == "abandoned",
                "abandon stops injection",
                dropped.stdout + injected,
            )
        finally:
            shutil.rmtree(left, ignore_errors=True)

        git_init(open_root)
        started = run(open_root, "start", "change", FEATURE)
        text = hook_text(open_root)
        status = json.load(open(os.path.join(open_root, "specs", FEATURE, "run.json"), encoding="utf-8")).get("status")
        nxt = run(open_root, "next")
        expect(
            started.returncode == 0
            and text.startswith("NOTICE %s working" % FEATURE)
            and "NEED" not in text
            and "写完后运行" not in text
            and status == "working"
            and "NEED" in nxt.stdout,
            "open run injects a notice and next still prints the step",
            text + nxt.stdout,
        )
        waited = run(open_root, "wait", FEATURE, "继续吗？", "继续")
        noticed = hook_text(open_root)
        record = json.load(open(os.path.join(open_root, "specs", FEATURE, "run.json"), encoding="utf-8"))
        resumed = run(open_root, "next")
        expect(
            waited.returncode == 0
            and "NOTICE %s waiting" % FEATURE in noticed
            and "摘要：继续吗？" in noticed
            and "answer " not in noticed
            and record.get("status") == "waiting"
            and "WAIT" in resumed.stdout
            and "REPLY 继续" in resumed.stdout,
            "waiting notice does not resume or clear the run",
            noticed + resumed.stdout,
        )
    finally:
        shutil.rmtree(empty, ignore_errors=True)
        shutil.rmtree(done, ignore_errors=True)
        shutil.rmtree(open_root, ignore_errors=True)


def tool(name):
    return shutil.which(name) is not None


def module(name):
    proc = subprocess.run(
        ["python3", "-c", "import %s" % name],
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0


def case_selected(label, write_files, command, advances):
    root = tempfile.mkdtemp(prefix="dw-sel-")
    try:
        write_files(root)
        reach_code(root)
        done = finish_code(root)
        log = log_text(root) if os.path.isfile(os.path.join(root, "specs", FEATURE, "verify.log")) else ""
        chosen = ("cmd %s" % command) in log
        if advances:
            ok = done.returncode == 0 and read_run(root).get("stage") == 3 and chosen
        else:
            ok = (
                done.returncode != 0
                and read_run(root).get("stage") == 2
                and "RED" in done.stdout
                and chosen
            )
        expect(ok, label, done.stdout + done.stderr + log)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def case_pnpm():
    def write_files(root):
        with open(os.path.join(root, "package.json"), "w", encoding="utf-8") as fh:
            json.dump({"scripts": {"test": "true"}}, fh)
        with open(os.path.join(root, "pnpm-lock.yaml"), "w", encoding="utf-8") as fh:
            fh.write("lockfileVersion: 9\n")

    case_selected("pnpm test", write_files, "pnpm test", tool("pnpm"))


def case_yarn():
    def write_files(root):
        with open(os.path.join(root, "package.json"), "w", encoding="utf-8") as fh:
            json.dump({"scripts": {"test": "true"}}, fh)
        with open(os.path.join(root, "yarn.lock"), "w", encoding="utf-8") as fh:
            fh.write("# yarn lock\n")

    case_selected("yarn test", write_files, "yarn test", tool("yarn"))


def case_pytest():
    def write_files(root):
        with open(os.path.join(root, "pytest.ini"), "w", encoding="utf-8") as fh:
            fh.write("[pytest]\n")
        with open(os.path.join(root, "test_probe.py"), "w", encoding="utf-8") as fh:
            fh.write("def test_ok():\n    assert True\n")

    case_selected("pytest", write_files, "python3 -m pytest -q", module("pytest"))


def case_cargo():
    def write_files(root):
        with open(os.path.join(root, "Cargo.toml"), "w", encoding="utf-8") as fh:
            fh.write('[package]\nname = "probe"\nversion = "0.1.0"\nedition = "2021"\n')
        os.makedirs(os.path.join(root, "src"))
        with open(os.path.join(root, "src", "lib.rs"), "w", encoding="utf-8") as fh:
            fh.write("#[cfg(test)]\nmod tests {\n    #[test]\n    fn ok() {}\n}\n")

    case_selected("cargo test", write_files, "cargo test", tool("cargo"))


def case_answer():
    root = tempfile.mkdtemp(prefix="dw-answer-")
    try:
        start = run(root, "start", "change", "ask")
        folder = os.path.join(root, "specs", "ask")
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, "decision.md"), "w", encoding="utf-8") as fh:
            fh.write("范围待拍板\n")
        nxt = run(root, "next", "ask")
        waited = run(root, "wait", "ask", "用全量还是三态？", "全量")
        record = json.load(open(os.path.join(folder, "run.json"), encoding="utf-8"))
        mismatch = run(root, "answer", "ask", "三态")
        answered = run(root, "answer", "ask", "全量")
        text = open(os.path.join(folder, "decision.md"), encoding="utf-8").read()
        expect(
            start.returncode == 0
            and "OPEN" in nxt.stdout
            and waited.returncode == 0
            and record.get("reply") == "全量"
            and mismatch.returncode != 0
            and "MISMATCH" in mismatch.stdout
            and answered.returncode == 0
            and "已拍板：全量" in text,
            "reply is recorded",
            nxt.stdout + waited.stdout + mismatch.stdout + answered.stdout + text,
        )
    finally:
        shutil.rmtree(root, ignore_errors=True)


def clean_env():
    env = os.environ.copy()
    for key in list(env):
        if key.startswith("DATA_WORKFLOW_"):
            del env[key]
    return env


def gate_permission(hook, root, path):
    payload = json.dumps({"cwd": root, "tool_input": {"path": path}})
    proc = subprocess.run(
        [hook],
        input=payload,
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(proc.stdout).get("permission")


def case_foreign():
    root = tempfile.mkdtemp(prefix="dw-foreign-")
    try:
        git_init(root)
        os.makedirs(os.path.join(root, ".cursor", "skills", "keep-me"))
        with open(os.path.join(root, ".cursor", "skills", "keep-me", "SKILL.md"), "w", encoding="utf-8") as fh:
            fh.write("keep\n")
        with open(os.path.join(root, "package.json"), "w", encoding="utf-8") as fh:
            json.dump({"scripts": {"test": "true"}}, fh)
        with open(os.path.join(root, "package-lock.json"), "w", encoding="utf-8") as fh:
            fh.write("{}\n")
        installed = subprocess.run(
            ["bash", INSTALL, root],
            cwd=root,
            capture_output=True,
            text=True,
            env=clean_env(),
        )
        copy = os.path.join(root, ".cursor", "skills", "data-workflow")
        expect(
            installed.returncode == 0 and os.path.isdir(copy) and not os.path.islink(copy),
            "foreign install copies the skill",
            installed.stdout + installed.stderr,
        )
        script = os.path.realpath(os.path.join(copy, "scripts", "workflow_next.py"))
        expect(
            script.startswith(os.path.realpath(root) + os.sep)
            and os.path.isfile(os.path.join(root, ".cursor", "skills", "keep-me", "SKILL.md")),
            "copy stays in the foreign repo and keeps the other skill",
            script,
        )
        hooks = json.load(open(os.path.join(root, ".cursor", "hooks.json"), encoding="utf-8"))
        commands = []
        for entries in (hooks.get("hooks") or {}).values():
            for entry in entries:
                commands.append(entry.get("command") or "")
        expect(
            any(cmd == ".cursor/skills/data-workflow/hooks/session-start" for cmd in commands)
            and all(REPO_ROOT not in cmd for cmd in commands),
            "foreign hooks point at the copy",
            "\n".join(commands),
        )
        config_path = os.path.join(copy, "config.yaml")
        config_text = open(config_path, encoding="utf-8").read()
        paths = subprocess.run(
            ["bash", os.path.join(copy, "scripts", "paths.sh")],
            cwd=root,
            capture_output=True,
            text=True,
            env=clean_env(),
        )
        expect(
            "check_runner" not in config_text
            and "KNOW=''" in paths.stdout
            and "TEMPLATES=''" in paths.stdout
            and "REPO=''" in paths.stdout,
            "foreign knowledge path stays empty",
            paths.stdout + paths.stderr,
        )
        gate = os.path.join(copy, "hooks", "gate-edit")
        expect(
            gate_permission(gate, root, "api/foo.proto") == "deny"
            and gate_permission(gate, root, "internal/x.go") == "deny"
            and gate_permission(gate, root, "README.md") == "allow",
            "foreign repo keeps the default write gate",
            "",
        )
        runner = os.path.join(copy, "scripts", "workflow_next.py")

        def copy_run(*args):
            return subprocess.run(
                [runner, *args, "--repo", root],
                cwd=root,
                capture_output=True,
                text=True,
                env=clean_env(),
            )

        started = copy_run("start", "change", FEATURE)
        folder = os.path.join(root, "specs", FEATURE)
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, "decision.md"), "w", encoding="utf-8") as fh:
            fh.write("改一处。\n")
        stepped = copy_run("done", FEATURE)
        finished = copy_run("done", FEATURE)
        record = json.load(open(os.path.join(folder, "run.json"), encoding="utf-8"))
        log = open(os.path.join(folder, "verify.log"), encoding="utf-8").read()
        expect(
            started.returncode == 0
            and stepped.returncode == 0
            and finished.returncode == 0
            and record.get("stage") == 3
            and "cmd npm test" in log
            and "check_runner" not in log,
            "foreign code step uses the copy and npm test",
            started.stdout + stepped.stdout + finished.stdout + log,
        )
        hook = subprocess.run(
            [os.path.join(copy, "hooks", "session-start")],
            cwd=root,
            capture_output=True,
            text=True,
            env=clean_env(),
            check=True,
        )
        injected = json.loads(hook.stdout).get("additional_context") or ""
        after = json.load(open(os.path.join(folder, "run.json"), encoding="utf-8"))
        expect(
            "NOTICE" in injected
            and FEATURE in injected
            and "NEED" not in injected
            and "写完后运行" not in injected
            and after.get("status") == "working"
            and after.get("stage") == record.get("stage"),
            "foreign session hook injects a notice and leaves the run",
            injected,
        )
        feature = copy_run("start", "feature", "chain")
        expect(
            "NEED specs/chain/spec.md" in feature.stdout
            and "stages/requirement-analysis/SKILL.md" in feature.stdout,
            "foreign copy still starts the feature chain",
            feature.stdout,
        )
        review = copy_run("start", "review-only", "look")
        expect(
            review.returncode == 0 and gate_permission(gate, root, "README.md") == "deny",
            "foreign review run blocks product writes",
            review.stdout,
        )
        commands = os.path.join(root, ".cursor", "commands")
        next_cmd = open(os.path.join(commands, "dw-next.md"), encoding="utf-8").read()
        with open(os.path.join(commands, "mine.md"), "w", encoding="utf-8") as fh:
            fh.write("mine\n")
        expect(
            "workflow_next.py next" in next_cmd
            and os.path.isfile(os.path.join(commands, "dw-done.md"))
            and os.path.isfile(os.path.join(commands, "dw-wait.md"))
            and os.path.isfile(os.path.join(commands, "dw-start.md")),
            "foreign install adds slash commands",
            next_cmd,
        )
        with open(config_path, "a", encoding="utf-8") as fh:
            fh.write('verify: "echo foreign-marker"\n')
        again = subprocess.run(
            ["bash", INSTALL, root],
            cwd=root,
            capture_output=True,
            text=True,
            env=clean_env(),
        )
        kept = open(config_path, encoding="utf-8").read()
        other = open(os.path.join(root, ".cursor", "skills", "keep-me", "SKILL.md"), encoding="utf-8").read()
        mine = open(os.path.join(commands, "mine.md"), encoding="utf-8").read()
        expect(
            again.returncode == 0
            and 'verify: "echo foreign-marker"' in kept
            and other == "keep\n"
            and mine == "mine\n"
            and "COMMAND " in again.stdout,
            "reinstall keeps foreign config, the other skill, and other commands",
            again.stdout + again.stderr + kept,
        )
        removed = subprocess.run(
            ["bash", INSTALL, "--unlink", root],
            cwd=root,
            capture_output=True,
            text=True,
            env=clean_env(),
        )
        expect(
            removed.returncode == 0
            and not os.path.isfile(os.path.join(commands, "dw-next.md"))
            and open(os.path.join(commands, "mine.md"), encoding="utf-8").read() == "mine\n"
            and open(os.path.join(root, ".cursor", "skills", "keep-me", "SKILL.md"), encoding="utf-8").read() == "keep\n",
            "unlink removes only the dw slash commands",
            removed.stdout + removed.stderr,
        )
    finally:
        shutil.rmtree(root, ignore_errors=True)


def main():
    case_none()
    case_npm()
    case_make()
    case_gomod()
    case_verify_wins()
    case_pnpm()
    case_yarn()
    case_pytest()
    case_cargo()
    case_answer()
    case_hook_quiet()
    case_foreign()
    print("OK")


if __name__ == "__main__":
    main()
