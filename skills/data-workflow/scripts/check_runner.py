#!/usr/bin/python3
"""临时仓库上的外部行为。

编码步骤的 done：没有检查入口、package.json 的 test、Makefile 的 test、
只有 go.mod、显式 verify 盖过 package.json。
会话钩子：没有运行、只有已完成运行时不注入。有未完成运行时注入 NOTICE，不注入 next 的操作指令，也不改 run.json。
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ME = os.path.abspath(__file__)
SKILL_ROOT = os.path.dirname(os.path.dirname(ME))
REPO_ROOT = os.path.dirname(os.path.dirname(SKILL_ROOT))
RUNNER = os.path.join(SKILL_ROOT, "scripts", "workflow_next.py")
HOOK = os.path.join(SKILL_ROOT, "hooks", "session-start")
GATE = os.path.join(SKILL_ROOT, "hooks", "gate-edit")
INSTALL = os.path.join(REPO_ROOT, "scripts", "install.sh")
FEATURE = "probe"

BASH = shutil.which("bash") or "bash"
PY = sys.executable


def expect(ok, label, detail):
    if ok:
        print("PASS " + label)
        return
    print("FAIL " + label)
    print(detail)
    raise SystemExit(1)


def tool(name):
    return shutil.which(name) is not None


def module(name):
    proc = subprocess.run(
        ["python3", "-c", "import %s" % name],
        capture_output=True, text=True,
    )
    return proc.returncode == 0


def clean_env():
    env = os.environ.copy()
    for key in list(env):
        if key.startswith("DATA_WORKFLOW_"):
            del env[key]
    return env


# ── Fixture 工厂 ─────────────────────────────────────────────────────────


class TestRoot:
    """临时测试仓库。封装 tempfile + git + 常用文件模板 + workflow 快捷路径。

    用法：
        with TestRoot("prefix-") as r:
            r.git_init()
            r.make_pkg(pnpm=True)
            r.change_reach()
            done = r.change_done()
            expect(done.returncode == 0, ...)
    """

    def __init__(self, prefix="dw-test-"):
        self._prefix = prefix

    def __enter__(self):
        self.path = tempfile.mkdtemp(prefix=self._prefix)
        self.store = self.path
        return self

    def __exit__(self, *exc):
        shutil.rmtree(self.path, ignore_errors=True)
        return False

    # ── env / runner ──

    def env(self, extra=None):
        base = dict(extra or os.environ)
        base["DATA_WORKFLOW_STORE"] = self.store
        return base

    def run(self, *args):
        return subprocess.run(
            [PY, RUNNER, *args, "--repo", self.path],
            capture_output=True, text=True, encoding="utf-8",
            env=self.env(),
        )

    # ── git ──

    def git_init(self):
        subprocess.run(["git", "init", "-q", self.path], check=True)
        return self

    def git_commit(self, message="probe"):
        subprocess.run(["git", "-C", self.path, "add", "-A"], check=True)
        subprocess.run(
            ["git", "-C", self.path,
             "-c", "user.name=probe", "-c", "user.email=probe@example.com",
             "commit", "-qm", message],
            check=True,
        )
        return self

    def git_head(self):
        return subprocess.run(
            ["git", "-C", self.path, "rev-parse", "HEAD"],
            capture_output=True, text=True, encoding="utf-8",
        ).stdout.strip()

    # ── 文件模板 ──

    def write(self, rel_path, content):
        full = os.path.join(self.path, rel_path)
        os.makedirs(os.path.dirname(full) or self.path, exist_ok=True)
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(content)
        return self

    def make_config(self, text):
        return self.write("config.yaml", text)

    def make_pkg(self, test_cmd="true", lock=None):
        pkg = {"scripts": {"test": test_cmd}}
        self.write("package.json", json.dumps(pkg))
        locks = {
            "npm": ("package-lock.json", "{}\n"),
            "pnpm": ("pnpm-lock.yaml", "lockfileVersion: 9\n"),
            "yarn": ("yarn.lock", "# yarn lock\n"),
        }
        if lock in locks:
            self.write(*locks[lock])
        return self

    def make_makefile(self, test_cmd="true"):
        return self.write("Makefile", "test:\n\t%s\n" % test_cmd)

    def make_gomod(self):
        (os.makedirs(os.path.join(self.path, "src"), exist_ok=True),)
        return (self
                .write("go.mod", "module example.com/probe\n\ngo 1.22\n")
                .write("src/probe.go", "package probe\n"))

    def make_cargo(self):
        (os.makedirs(os.path.join(self.path, "src"), exist_ok=True),)
        return (self
                .write("Cargo.toml",
                       '[package]\nname = "probe"\nversion = "0.1.0"\nedition = "2021"\n')
                .write("src/lib.rs",
                       "#[cfg(test)]\nmod tests {\n    #[test]\n    fn ok() {}\n}\n"))

    def make_pytest(self):
        return (self
                .write("pytest.ini", "[pytest]\n")
                .write("test_probe.py", "def test_ok():\n    assert True\n"))

    # ── workflow 快捷路径 ──

    def run_path(self, feature=FEATURE):
        return os.path.join(self.path, "specs", feature, "run.json")

    def read_run(self, feature=FEATURE):
        with open(self.run_path(feature), encoding="utf-8") as fh:
            return json.load(fh)

    def log_text(self, feature=FEATURE):
        p = os.path.join(self.path, "specs", feature, "verify.log")
        return open(p, encoding="utf-8").read() if os.path.isfile(p) else ""

    def write_decision(self, feature=FEATURE, raw="探测用",
                       understand="改一处", satisfies="跑 next 返回 DO"):
        folder = os.path.join(self.path, "specs", feature)
        os.makedirs(folder, exist_ok=True)
        content = (
            "- 原话（一字不改）：%s\n"
            "- 我理解你要的是：%s\n"
            "- 可能理解错的地方：无歧义\n"
            "- 本质：改一处\n"
            "- 怎样算满足：%s\n"
            "- 未知：无\n" % (raw, understand, satisfies)
        )
        with open(os.path.join(folder, "decision.md"), "w", encoding="utf-8") as fh:
            fh.write(content)
        return self

    def change_reach(self, feature=FEATURE, raw="探测用",
                     understand="改一处", satisfies="跑 next 返回 DO"):
        """start change → 写 decision.md 第一屏 → done 到 DO。"""
        start = self.run("start", "change", feature, raw)
        if start.returncode != 0:
            raise SystemExit(start.stdout + start.stderr)
        self.write_decision(feature, raw, understand, satisfies)
        done = self.run("done", feature)
        if done.returncode != 0 or self.read_run(feature).get("stage") != 2:
            raise SystemExit(done.stdout + done.stderr)
        return done

    def change_done(self, feature=FEATURE):
        return self.run("done", feature)

    # ── gate shortcut ──

    def gate_perm(self, path, tool_name="edit_file", raw=None):
        payload = raw if raw is not None else json.dumps(
            {"cwd": self.path, "tool_name": tool_name, "tool_input": {"path": path}}
        )
        proc = subprocess.run(
            [BASH, GATE], input=payload, cwd=self.path,
            capture_output=True, text=True, encoding="utf-8",
            env=self.env(), check=True,
        )
        return json.loads(proc.stdout).get("permission")

    # ── hook ──

    def hook_text(self):
        proc = subprocess.run(
            [BASH, HOOK], cwd=self.path,
            capture_output=True, text=True, encoding="utf-8",
            env=self.env(), check=True,
        )
        return (json.loads(proc.stdout).get("additional_context") or "")

    # ── install ──

    def install(self, *args, home=None):
        env = clean_env()
        if home:
            env["HOME"] = home
        return subprocess.run(
            [BASH, INSTALL, *args], cwd=self.path,
            capture_output=True, text=True, encoding="utf-8",
            env=env,
        )

    def install_runner(self, sub="workflow_next.py"):
        return os.path.join(self.path, ".cursor", "skills", "data-workflow",
                            "scripts", sub)


# ── Cases ─────────────────────────────────────────────────────────────────


def case_none():
    """完全没测试入口时：RED + 说清怎么补。"""
    with TestRoot() as r:
        r.change_reach()
        done = r.change_done()
        expect(
            done.returncode != 0
            and r.read_run().get("stage") == 2
            and "RED" in done.stdout,
            "none stays RED", done.stdout + done.stderr,
        )
        expect(
            "config.yaml" in done.stdout and "verify:" in done.stdout,
            "RED names where to configure verify", done.stdout + done.stderr,
        )
        expect(
            "go.mod" in done.stdout and "package.json" in done.stdout,
            "RED lists the auto-detected entry files", done.stdout + done.stderr,
        )


def case_npm():
    with TestRoot() as r:
        r.make_pkg(lock="npm")
        r.change_reach()
        done = r.change_done()
        log = r.log_text()
        expect(
            done.returncode == 0
            and r.read_run().get("stage") == 3
            and "cmd npm test" in log,
            "npm test advances", done.stdout + done.stderr + log,
        )


def case_make():
    with TestRoot() as r:
        r.make_makefile()
        r.change_reach()
        done = r.change_done()
        log = r.log_text()
        expect(
            done.returncode == 0
            and r.read_run().get("stage") == 3
            and "cmd make test" in log,
            "make test advances", done.stdout + done.stderr + log,
        )


def case_gomod():
    with TestRoot() as r:
        r.make_gomod()
        r.change_reach()
        done = r.change_done()
        log = r.log_text()
        expect(
            "go test" in log and "verify.log" not in log.split("\n")[0],
            "go.mod discovered as the verify entry",
            done.stdout + done.stderr + "\n--- verify.log ---\n" + log,
        )


def case_verify_wins():
    with TestRoot() as r:
        r.make_pkg(lock="npm")
        r.make_config('verify: "false"\n')
        r.change_reach()
        done = r.change_done()
        log = r.log_text()
        expect(
            done.returncode != 0
            and r.read_run().get("stage") == 2
            and "RED" in done.stdout
            and "cmd false" in log,
            "explicit verify stops", done.stdout + done.stderr + log,
        )


def _case_selected(label, setup, command, advances):
    """pnpm/yarn/pytest/cargo 共享的模板。"""
    with TestRoot("dw-sel-") as r:
        setup(r)
        r.change_reach()
        done = r.change_done()
        log = r.log_text()
        chosen = ("cmd %s" % command) in log
        if advances:
            ok = done.returncode == 0 and r.read_run().get("stage") == 3 and chosen
        else:
            ok = (done.returncode != 0 and r.read_run().get("stage") == 2
                  and "RED" in done.stdout and chosen)
        expect(ok, label, done.stdout + done.stderr + log)


def case_pnpm():
    _case_selected("pnpm test", lambda r: r.make_pkg(lock="pnpm"),
                   "pnpm test", tool("pnpm"))


def case_yarn():
    _case_selected("yarn test", lambda r: r.make_pkg(lock="yarn"),
                   "yarn test", tool("yarn"))


def case_pytest():
    _case_selected("pytest", lambda r: r.make_pytest(),
                   "python3 -m pytest -q", module("pytest"))


def case_cargo():
    _case_selected("cargo test", lambda r: r.make_cargo(),
                   "cargo test", tool("cargo"))


def case_install_makes_tool_dir():
    """新仓库连 .cursor 都没有时，--project 应该自己建。"""
    with TestRoot("dw-nodir-") as r, TestRoot("dw-nodirhome-") as home:
        r.git_init()
        r.write("README.md", "probe\n")
        proc = r.install("--project", home=home.path)
        expect(
            proc.returncode == 0 and "NOTHING" not in proc.stdout,
            "--project on a repo without tool dirs does not refuse",
            proc.stdout + proc.stderr,
        )
        expect(
            os.path.isdir(os.path.join(r.path, ".cursor", "skills", "data-workflow")),
            "--project creates the Cursor skill dir when none exists",
            proc.stdout + proc.stderr,
        )


def case_hook_quiet():
    """会话钩子：没有运行、只有已完成运行时不注入。"""
    with TestRoot("dw-hook-empty-") as empty, \
         TestRoot("dw-hook-done-") as done, \
         TestRoot("dw-hook-open-") as open_root, \
         TestRoot("dw-hook-left-") as left:

        empty.git_init()
        expect(empty.hook_text() == "", "no run injects nothing", empty.hook_text())

        done.git_init()
        os.makedirs(os.path.join(done.path, "specs", "finished"))
        with open(os.path.join(done.path, "specs", "finished", "run.json"),
                  "w", encoding="utf-8") as fh:
            json.dump({"workflow": "change", "feature": "finished",
                       "stage": 3, "status": "done",
                       "question": "", "reply": ""}, fh)
        expect(done.hook_text() == "", "finished run injects nothing", done.hook_text())

        left.git_init()
        os.makedirs(os.path.join(left.path, "specs", "old"))
        with open(os.path.join(left.path, "specs", "old", "run.json"),
                  "w", encoding="utf-8") as fh:
            json.dump({"workflow": "change", "feature": "old",
                       "stage": 2, "status": "working",
                       "question": "", "reply": ""}, fh)
        dropped = left.run("abandon", "old")
        status = json.load(open(os.path.join(left.path, "specs", "old", "run.json"),
                                encoding="utf-8")).get("status")
        injected = left.hook_text()
        expect(
            dropped.returncode == 0 and injected == "" and status == "abandoned",
            "abandon stops injection", dropped.stdout + injected,
        )

        open_root.git_init()
        started = open_root.run("start", "change", FEATURE)
        text = open_root.hook_text()
        record = open_root.read_run()
        nxt = open_root.run("next")
        expect(
            started.returncode == 0
            and text.startswith("NOTICE %s working" % FEATURE)
            and "NEED" not in text and "写完后运行" not in text
            and record.get("status") == "working"
            and "NEED" in nxt.stdout,
            "open run injects a notice and next still prints the step",
            text + nxt.stdout,
        )
        waited = open_root.run("wait", FEATURE, "继续吗？", "继续")
        noticed = open_root.hook_text()
        record = open_root.read_run()
        resumed = open_root.run("next")
        expect(
            waited.returncode == 0
            and "NOTICE %s waiting" % FEATURE in noticed
            and "摘要：继续吗？" in noticed
            and "answer " not in noticed
            and record.get("status") == "waiting"
            and "WAIT" in resumed.stdout and "REPLY 继续" in resumed.stdout,
            "waiting notice does not resume or clear the run",
            noticed + resumed.stdout,
        )


def case_answer():
    """wait / answer / reply 逐字匹配。"""
    with TestRoot("dw-answer-") as r:
        r.git_init()
        ask = "ask"
        folder = os.path.join(r.path, "specs", ask)
        os.makedirs(folder, exist_ok=True)
        r.run("start", "change", ask)
        r.write("specs/ask/decision.md", "- 待拍板：用全量还是三态？\n")
        nxt = r.run("next", ask)
        waited = r.run("wait", ask, "用全量还是三态？", "全量")
        record = r.read_run(ask)
        mismatch = r.run("answer", ask, "三态")
        answered = r.run("answer", ask, "全量")
        text = open(os.path.join(folder, "decision.md"), encoding="utf-8").read()
        expect(
            "OPEN" in nxt.stdout
            and waited.returncode == 0
            and record.get("reply") == "全量"
            and mismatch.returncode != 0 and "MISMATCH" in mismatch.stdout
            and answered.returncode == 0 and "已拍板：全量" in text,
            "reply is recorded",
            nxt.stdout + waited.stdout + mismatch.stdout + answered.stdout + text,
        )


def case_gate_tool_case():
    """各宿主给的工具名大小写不一，门禁必须都认得。"""
    with TestRoot("dw-gate-case-") as r:
        r.git_init()
        os.makedirs(os.path.join(r.path, "api"))
        r.write("api/a.proto", 'syntax = "proto3";\n')
        r.write("README.md", "probe\n")
        r.make_config('protected_paths: "api/**"\n')
        for tool in ("Write", "write", "Edit", "edit_file",
                     "MultiEdit", "multiEdit", "apply_patch"):
            expect(
                r.gate_perm("api/a.proto", tool) == "deny",
                "protected write is denied for tool name %r" % tool, "",
            )
        for tool in ("Read", "read_file", "grep", "list_dir", "Grep"):
            expect(
                r.gate_perm("api/a.proto", tool) == "allow",
                "reading stays allowed for tool name %r" % tool, "",
            )
        expect(
            r.gate_perm("README.md", "Write") == "allow",
            "unprotected write is still allowed", "",
        )


def case_gate_read_write():
    """读不能当写拦。"""
    with TestRoot("dw-gate-rw-") as r:
        r.git_init()
        os.makedirs(os.path.join(r.path, "api"))
        r.write("api/a.proto", 'syntax = "proto3";\n')
        r.make_config('protected_paths: "api/**"\nwaiver_globs: "*.go"\n')
        expect(
            r.gate_perm("api/a.proto", "read_file") == "allow"
            and r.gate_perm("api/a.proto", "grep") == "allow"
            and r.gate_perm("api/a.proto", "list_dir") == "allow",
            "reading protected paths is allowed", "",
        )
        expect(
            r.gate_perm("api/a.proto", "edit_file") == "deny"
            and r.gate_perm("api/a.proto", "write") == "deny",
            "writing protected paths is denied", "",
        )
        expect(
            r.gate_perm("api/a.proto", "some_future_tool") == "allow",
            "unknown tool name fails open", "",
        )
        expect(
            r.gate_perm("README.md", "edit_file") == "allow",
            "unprotected paths stay writable", "",
        )


def case_gate_strict():
    """坏输入默认放行；gate_strict 开着才拒绝。"""
    with TestRoot("dw-gate-strict-") as r:
        r.git_init()
        loose = r.gate_perm("README.md", raw="{not json")
        r.make_config('gate_strict: "true"\n')
        tight = r.gate_perm("README.md", raw="{not json")
        expect(
            loose == "allow" and tight == "deny",
            "bad input fails open unless gate_strict is on",
            "loose=%s tight=%s" % (loose, tight),
        )


def case_gate_no_python():
    """解释器缺失时输出合法 JSON 并放行。"""
    with TestRoot("dw-gate-nopy-") as r, TestRoot("dw-nopath-") as empty:
        r.git_init()
        env = r.env()
        env["PATH"] = empty.path
        proc = subprocess.run(
            [BASH, GATE], input="{}", cwd=r.path,
            capture_output=True, text=True, encoding="utf-8", env=env,
        )
        data = json.loads(proc.stdout)
        expect(
            proc.returncode == 0
            and data.get("permission") == "allow"
            and "python" in (data.get("agent_message") or ""),
            "missing interpreter allows instead of blocking",
            proc.stdout + proc.stderr,
        )


def case_utf8_output():
    with TestRoot("dw-utf8-") as r:
        r.git_init()
        r.run("start", "change", FEATURE)
        nxt = r.run("next")
        expect(
            "写完后运行" in nxt.stdout and "\ufffd" not in nxt.stdout,
            "runner prints readable utf-8", nxt.stdout + nxt.stderr,
        )


def case_no_phantom():
    """不造 stage-N.md 幻影文件名。"""
    with TestRoot("dw-phantom-") as r:
        r.git_init()
        hot = r.run("start", "hotfix", "h1")
        expect(
            "NEED specs/h1/triage.md" in hot.stdout
            and "stage-1.md" not in hot.stdout,
            "hotfix asks for triage.md, not a phantom stage file",
            hot.stdout,
        )
        r.run("start", "review-only", "r1")
        r.write("specs/r1/diff.patch", "diff\n")
        for name in ("spec-compliance.md", "code-quality.md", "interface-impact.md"):
            r.write("specs/r1/review/%s" % name, "x\n")
        r.write("specs/r1/interface-test.md", "x\n")
        nxt = r.run("next", "r1")
        expect(
            "NEED specs/r1/review/verdict.md" in nxt.stdout
            and "stage-4.md" not in nxt.stdout,
            "review-only asks for review/verdict.md", nxt.stdout,
        )


def case_intake():
    """原话进记录，缺「未知」停在内容门。"""
    with TestRoot("dw-intake-") as r:
        r.git_init()
        raw = "把导出的默认集改成三态，别再问我「根据项目规则」"
        r.run("start", "change", FEATURE, raw)
        expect(r.read_run().get("raw_request") == raw,
               "start stores the raw request verbatim",
               json.dumps(r.read_run(), ensure_ascii=False))
        r.write("specs/probe/decision.md",
                "- 原话（一字不改）：%s\n- 本质：改默认集\n" % raw)
        blocked = r.run("next")
        expect("GATE" in blocked.stdout and "未知" in blocked.stdout
               and r.read_run().get("stage") == 1,
               "missing 未知 stops at the gate", blocked.stdout)
        expect("我理解你要的是" in blocked.stdout and "可能理解错" in blocked.stdout,
               "gate also demands the understanding lines", blocked.stdout)
        r.write("specs/probe/decision.md",
                (open(os.path.join(r.path, "specs", FEATURE, "decision.md"),
                      encoding="utf-8").read() + "\n- 未知：无\n"))
        still = r.run("next")
        expect("GATE" in still.stdout and "我理解你要的是" in still.stdout,
               "understanding lines alone do not slip past the gate",
               still.stdout)
        with open(os.path.join(r.path, "specs", FEATURE, "decision.md"),
                  "a", encoding="utf-8") as fh:
            fh.write("\n- 我理解你要的是：把导出默认集改成三态，不再交互追问\n")
            fh.write("- 可能理解错的地方：三态具体是哪三个尚未确认\n")
            fh.write("- 怎样算满足：跑 next 返回 DO\n")
        nxt = r.run("next")
        expect("DO" in nxt.stdout and "RAW %s" % raw in nxt.stdout,
               "complete intake advances and echoes the raw request",
               nxt.stdout)


def case_restated_raw():
    """「我理解你要的是」照抄原话时给一句 NOTE。"""
    with TestRoot("dw-restate-") as r:
        r.git_init()
        raw = "把导出的默认集改成三态，别再问我根据项目规则"
        r.run("start", "change", FEATURE, raw)
        r.write("specs/probe/decision.md",
                "- 原话（一字不改）：%s\n"
                "- 我理解你要的是：%s\n"
                "- 可能理解错的地方：无歧义\n"
                "- 本质：改默认集\n"
                "- 怎样算满足：跑 next 返回 DO\n"
                "- 未知：无\n" % (raw, raw))
        copied = r.run("next")
        expect("NOTE" in copied.stdout and "原话的复制" in copied.stdout,
               "copying the raw line raises a note", copied.stdout)
        expect("DO" in copied.stdout,
               "the note does not block progress", copied.stdout)
        r.write("specs/probe/decision.md",
                "- 原话（一字不改）：%s\n"
                "- 我理解你要的是：导出默认集固定三态，不再交互追问\n"
                "- 可能理解错的地方：三态具体是哪三个尚未确认\n"
                "- 本质：改默认集\n"
                "- 未知：无\n" % raw)
        own = r.run("next")
        expect("NOTE" not in own.stdout and "DO" in own.stdout,
               "rephrasing in own words raises no note", own.stdout)


def case_domains():
    with TestRoot("dw-domains-") as r:
        r.git_init()
        r.make_config('domains: "采集任务,质检管理"\n')
        proc = subprocess.run(
            [BASH, os.path.join(SKILL_ROOT, "scripts", "paths.sh")],
            cwd=r.path, capture_output=True, text=True, encoding="utf-8",
            env=clean_env(),
        )
        expect("DOMAINS='采集任务,质检管理'" in proc.stdout,
               "paths.sh exposes the configured domains",
               proc.stdout + proc.stderr)


def case_domain_docs():
    with TestRoot("dw-domain-") as r:
        r.git_init()
        r.write("README.md", "probe\n")
        os.makedirs(os.path.join(r.path, "docs", "domain"))
        r.git_commit()
        head = r.git_head()
        r.write("docs/domain/order.md",
                "---\nid: domain-order\nobject: 订单\nverified_commit: %s\n"
                "watches:\n  - README.md\n---\n\n# 订单\n" % head)
        r.git_commit("doc")
        paths = subprocess.run(
            [BASH, os.path.join(SKILL_ROOT, "scripts", "paths.sh")],
            cwd=r.path, capture_output=True, text=True, encoding="utf-8",
            env=clean_env(),
        )
        drift = subprocess.run(
            [BASH, os.path.join(SKILL_ROOT, "scripts", "knowledge_drift.sh")],
            cwd=r.path, capture_output=True, text=True, encoding="utf-8",
            env=clean_env(),
        )
        expect("DOMAIN_DOCS='" in paths.stdout and "docs/domain" in paths.stdout,
               "paths.sh exposes the repo domain docs",
               paths.stdout + paths.stderr)
        expect("FRESH" in drift.stdout and "order.md" in drift.stdout,
               "drift grades the repo domain doc",
               drift.stdout + drift.stderr)


def case_approve():
    """放行行只由 approve 写；手写行在 gate_strict 下不作数。"""
    with TestRoot("dw-approve-") as r:
        r.git_init()
        os.makedirs(os.path.join(r.path, "api"))
        r.make_config('protected_paths: "api/**"\ngate_strict: "true"\n')
        r.run("start", "change", FEATURE)
        r.write_decision()
        blocked = r.run("approve", FEATURE, "design", "api")
        expect("NEED_ANSWER" in blocked.stdout,
               "approve refuses without an answered question", blocked.stdout)
        r.write("specs/passes.log", "design %s api\n" % FEATURE)
        r.write("specs/probe/plan.md", "plan\n")
        r.write("specs/probe/gate", "plan pass\n")
        expect(r.gate_perm("api/a.proto") == "deny",
               "hand-written pass line is ignored under gate_strict", "")
        r.run("wait", FEATURE, "可以把 api/ 放行吗？", "可以")
        r.run("answer", FEATURE, "可以")
        approved = r.run("approve", FEATURE, "design", "api")
        expect("APPROVED" in approved.stdout
               and r.gate_perm("api/a.proto") == "allow",
               "approve after a real reply unlocks the write",
               approved.stdout)


def case_gate_check():
    """gate_check 跑命令，退出码非 0 就停。"""
    with TestRoot("dw-gatecheck-") as r:
        r.git_init()
        r.make_config('verify: "true"\n')
        r.run("start", "change", FEATURE)
        r.write_decision()
        r.run("done", FEATURE)
        r.git_commit()
        blocked = r.run("done", FEATURE)
        expect("GATE" in blocked.stdout and "CHECK" in blocked.stdout
               and r.read_run().get("stage") == 2,
               "gate_check blocks a clean working tree", blocked.stdout)
        r.write("app.txt", "x\n")
        passed = r.run("done", FEATURE)
        expect(passed.returncode == 0 and r.read_run().get("stage") == 3,
               "gate_check passes when the tree changed", passed.stdout)


def case_evidence_log():
    """推进时落一行证据（含 head）；HEAD 变了 next 要提醒。"""
    with TestRoot("dw-evidence-") as r:
        r.git_init()
        r.make_config('verify: "true"\n')
        r.git_commit()
        r.run("start", "change", FEATURE)
        r.write_decision()
        r.run("next")
        log = open(os.path.join(r.path, "specs", FEATURE, "evidence.log"),
                   encoding="utf-8").read()
        expect("stage=1" in log and "head=" in log and "by=runner" in log,
               "advancing appends an evidence line", log)
        r.git_commit()
        r.write("later.txt", "x\n")
        r.git_commit("later")
        nxt = r.run("next")
        expect("NOTE 工作树已变" in nxt.stdout,
               "head drift shows up as a note", nxt.stdout)


def case_decided():
    """拍板过的话由 next 带出来（不另存一份）。"""
    with TestRoot("dw-decided-") as r:
        r.git_init()
        r.make_config('verify: "true"\n')
        r.run("start", "change", FEATURE)
        r.write("specs/probe/decision.md",
                "- 原话（一字不改）：探测\n- 我理解你要的是：改一处\n"
                "- 可能理解错的地方：无歧义\n- 本质：改一处\n"
                "- 怎样算满足：跑 next 返回 DO\n- 未知：无\n"
                "- 待拍板：范围多大？\n")
        r.run("next")
        r.run("wait", FEATURE, "用全量还是三态？", "只改判定那一行")
        r.run("answer", FEATURE, "只改判定那一行")
        nxt = r.run("next")
        expect("DECIDED 只改判定那一行" in nxt.stdout,
               "next echoes the last decision", nxt.stdout)


def case_docs_match_reality():
    """docs/scripts.md 必须列出每个 skill 脚本。"""
    scripts_md = open(os.path.join(REPO_ROOT, "docs", "scripts.md"),
                       encoding="utf-8").read()
    missing = [
        name for name in sorted(os.listdir(os.path.join(SKILL_ROOT, "scripts")))
        if not name.startswith(".") and name not in scripts_md
    ]
    expect(not missing,
           "docs/scripts.md lists every skill script (missing: %s)" % missing, "")


def case_readme_matches_requires():
    """README 的 decision.md 第一屏示例必须与 change.json 的 requires 一致。"""
    wf = json.load(open(os.path.join(SKILL_ROOT, "workflows", "change.json"),
                         encoding="utf-8"))
    req = wf["stages"][0].get("requires") or []
    readme = open(os.path.join(REPO_ROOT, "README.md"), encoding="utf-8").read()
    first_screen = []
    for line in readme.splitlines():
        stripped = line[line.find("#"):] if "#" in line else ""
        if "写 decision.md 第一屏" in stripped or first_screen:
            if stripped.startswith("#"):
                first_screen.append(stripped)
            elif first_screen:
                break
    block_text = "\n".join(first_screen)
    expect(bool(block_text),
           "README documents the decision.md first screen", "")
    missing = [k for k in req if k not in block_text]
    expect(not missing,
           "README first-screen matches change.json requires (missing: %s)" % missing,
           block_text)


def case_intent_confirm_wired():
    """两个工作流的第 1 步都要求理解确认，且模板措辞与 requires 逐字一致。"""
    pairs = [("change.json", "decision-template.md"),
             ("feature.json", "spec-template.md")]
    lines = ["我理解你要的是", "可能理解错"]
    for wf_name, tpl_name in pairs:
        wf = json.load(open(os.path.join(SKILL_ROOT, "workflows", wf_name),
                             encoding="utf-8"))
        req = wf["stages"][0].get("requires") or []
        for line in lines:
            expect(line in req,
                   "%s stage 1 requires %s" % (wf_name, line),
                   json.dumps(req, ensure_ascii=False))
        tpl = open(os.path.join(SKILL_ROOT, "templates", tpl_name),
                   encoding="utf-8").read()
        for line in lines:
            expect(line in tpl, "%s contains %s" % (tpl_name, line), "")
    for _, tpl_name in pairs:
        tpl = open(os.path.join(SKILL_ROOT, "templates", tpl_name),
                   encoding="utf-8").read()
        expect("原话（一字不改）" in tpl,
               "%s keeps the raw line" % tpl_name, "")


def case_skill_routing():
    """阶段→文件只留一份（next）；SKILL.md 不再维护那张表。"""
    text = open(os.path.join(SKILL_ROOT, "SKILL.md"), encoding="utf-8").read()
    expect("| 需求分析 |" not in text
           and "| 业务梳理 |" in text
           and "| 画图 |" in text,
           "SKILL.md keeps only the four non-workflow entries", text)


def case_card_writeback():
    """卡片回写：写下去的东西能被脚本验证。"""
    with TestRoot("dw-card-") as root, TestRoot("dw-cards-") as cards:
        root.git_init()
        root.write("README.md", "probe\n")
        root.git_commit()
        head = root.git_head()
        env = clean_env()
        env["DATA_WORKFLOW_CARDS_DIR"] = cards.path
        body = (
            "---\n"
            "id: support-20260101-mqtt-false\n"
            "title: MQTT 推送被误认为不存在\n"
            "kind: fact\n"
            "status: verified-static\n"
            "domains: [job]\n"
            "object: job\n"
            "symptoms: [mqtt, 没收到通知, push]\n"
            "source_paths: [internal/biz/job_dispatch_notification.go]\n"
            "invalidates_when: 此文件被删除或重命名\n"
            "verified_branch: main\n"
            "verified_commit: %s\n"
            "verified_at: 2026-01-01T00:00:00+08:00\n"
            "verification: static\n"
            "---\n\n# MQTT\n的确有推送。\n" % head
        )
        card_path = os.path.join(cards.path, "2026-01-01-mqtt.md")
        with open(card_path, "w", encoding="utf-8") as fh:
            fh.write(body)
        for field in ("source_paths", "invalidates_when", "symptoms"):
            expect(re.search(r"^%s:\s*\S" % field, body, re.M) is not None,
                   "card has non-empty %s" % field, body)
        hit = subprocess.run(["grep", "-rl", "mqtt", cards.path],
                             capture_output=True, text=True, encoding="utf-8")
        expect(hit.returncode == 0 and "2026-01-01-mqtt.md" in hit.stdout,
               "card is findable by symptom keyword", hit.stdout)
        drift = subprocess.run(
            [BASH, os.path.join(SKILL_ROOT, "scripts", "knowledge_drift.sh"),
             card_path],
            cwd=root.path, capture_output=True, text=True, encoding="utf-8",
            env=env,
        )
        expect("FRESH" in drift.stdout,
               "drift grades the freshly written card as FRESH",
               drift.stdout + drift.stderr)


def case_knowledge_feedback():
    """知识反哺：指针可自动写，业务口径不许自动改。"""
    qg = open(os.path.join(SKILL_ROOT, "stages", "quality-gate", "SKILL.md"),
              encoding="utf-8").read()
    expect("G7" in qg, "quality-gate has the G7 step", "")
    expect("knowledge_drift.sh" in qg,
           "G7 finds drift with the existing script", "")
    expect("verified_commit" in qg,
           "G7 refreshes verified_commit", "")
    expect(re.search(r"指针类", qg) and re.search(r"口径类", qg),
           "G7 splits pointer entries from semantic entries", "")
    expect(re.search(r"不[许允许].{0,12}(用代码|代码现状).{0,20}(口径|语义)", qg),
           "G7 forbids rewriting business semantics from code", "")
    expect(re.search(r"不自行决定以哪份为准", qg),
           "G7 leaves conflicts to a human, does not self-resolve", "")


def case_gate_edit_coverage():
    """gate-edit 的拦截面：写操作的覆盖边界必须被钉住。"""
    sys.path.insert(0, os.path.join(SKILL_ROOT, "hooks"))
    import gate_edit  # noqa: E402

    root = os.path.abspath(os.sep + "tmp" + os.sep + "dw-cov")
    target = "api/x.proto"

    must_block_shell = [
        "echo hi > api/x.proto",
        "echo hi >> api/x.proto",
        "echo hi >api/x.proto",
        "cat > api/x.proto <<EOF\nhi\nEOF",
        "sed -i 's/a/b/' api/x.proto",
        "echo hi | tee api/x.proto",
        "cp /tmp/x api/x.proto",
        "mv /tmp/x api/x.proto",
        "rm api/x.proto",
    ]
    for cmd in must_block_shell:
        dest = gate_edit.shell_destinations(cmd, root)
        expect(any(target in d for d in dest),
               "gate-edit blocks shell write: %s" % cmd.split()[0], str(dest))

    known_gaps = [
        ("python -c open().write",
         "python3 -c \"open('api/x.proto','w').write('x')\""),
        ("git apply", "git apply patch.diff"),
        ("patch", "patch -p1 < /tmp/f.diff"),
        ("dd of=", "dd if=/dev/zero of=api/x.proto"),
        ("truncate", "truncate -s 0 api/x.proto"),
    ]
    for label, cmd in known_gaps:
        dest = gate_edit.shell_destinations(cmd, root)
        expect(not any(target in d for d in dest),
               "known gap still open (fix the doc if it closes): %s" % label,
               str(dest))

    for tool in ("write", "edit", "multiedit", "write_file"):
        dest = gate_edit.targets(
            {"tool_name": tool, "tool_input": {"file_path": target, "path": target}},
            root)
        expect(dest is not None and any(target in (d or "") for d in dest),
               "gate-edit sees writes from tool: %s" % tool, str(dest))

    for tool in ("mcp__fs__write_file", "some_future_tool"):
        dest = gate_edit.targets(
            {"tool_name": tool, "tool_input": {"path": target}}, root)
        expect(dest is None,
               "unknown/MCP tool fails open (documented gap): %s" % tool,
               str(dest))


def case_self_check_not_a_gate():
    """self_check 字段不许被任何代码当成门读。"""
    import glob as _glob
    leftover = []
    for wf in sorted(_glob.glob(os.path.join(SKILL_ROOT, "workflows", "*.json"))):
        if '"gate"' in open(wf, encoding="utf-8").read():
            leftover.append(os.path.basename(wf))
    expect(not leftover, "no workflow reintroduces the 'gate' key", str(leftover))
    src = open(os.path.join(SKILL_ROOT, "scripts", "workflow_next.py"),
               encoding="utf-8").read()
    expect('["gate"]' not in src and "get(\"gate\")" not in src
           and "get('gate')" not in src,
           "workflow_next.py never reads stage['gate'] as a gate", "")


def case_g7_gate_runs():
    """G7 知识反哺的判据必须真的会拦。"""
    sys.path.insert(0, os.path.join(SKILL_ROOT, "scripts"))
    import workflow_next as W  # noqa: E402

    with TestRoot("dw-g7-") as r:
        r.git_init()
        os.makedirs(os.path.join(r.path, "docs", "domain"))
        os.makedirs(os.path.join(r.path, "src", "user"))
        r.write("docs/domain/user.md",
                "---\nid: domain-user\nverified_commit: %s\n"
                "watches:\n  - src/user\n---\n# user\n" % ("0" * 40))
        r.write("src/user/api.go", "package user\n")
        r.git_commit()
        head = r.git_head()

        # 1) 改动被 watches 覆盖，commit 没跟上 -> 拦
        with open(os.path.join(r.path, "src", "user", "api.go"),
                  "a", encoding="utf-8") as fh:
            fh.write("// touched\n")
        ok, hits, detail = W.knowledge_feedback(r.path, "x")
        expect(not ok,
               "G7 blocks when watched file changed and commit not refreshed",
               detail)
        expect(hits == ["docs/domain/user.md"],
               "G7 names the hit domain doc", str(hits))

        # 2) 刷新 verified_commit -> 放行
        doc = os.path.join(r.path, "docs", "domain", "user.md")
        with open(doc, encoding="utf-8") as fh:
            text = fh.read()
        with open(doc, "w", encoding="utf-8") as fh:
            fh.write(re.sub(r"^verified_commit:.*$",
                            "verified_commit: %s" % head, text, flags=re.M))
        ok, hits, _ = W.knowledge_feedback(r.path, "x")
        expect(ok, "G7 passes once verified_commit is refreshed", str(hits))

        # 3) 改动不碰任何 watches -> 不命中
        with open(doc, "w", encoding="utf-8") as fh:
            fh.write(re.sub(r"^verified_commit:.*$",
                            "verified_commit: %s" % ("0" * 40), text, flags=re.M))
        subprocess.run(["git", "-C", r.path, "checkout", "--", "src/user/api.go"],
                       check=False)
        r.write("unrelated.txt", "x\n")
        ok, hits, _ = W.knowledge_feedback(r.path, "x")
        expect(ok and hits == [],
               "G7 does not touch unrelated domains", str(hits))


def case_lazy_load():
    """SKILL.md 短，references 不被无条件加载。"""
    skill = open(os.path.join(SKILL_ROOT, "SKILL.md"), encoding="utf-8").read()
    lines = len(skill.splitlines())
    expect(lines <= 200,
           "SKILL.md stays under 200 lines (got %d)" % lines, "")
    expect(not re.search(r"references/\*", skill),
           "SKILL.md does not glob-load references", "")
    m = re.search(r"^description:\s*(.*)$", skill, re.M)
    desc = m.group(1) if m else ""
    expect(len(desc) <= 260,
           "description stays short (got %d chars)" % len(desc), desc)


def case_evals_are_runnable():
    """evals.json 里只许放能被脚本判定的用例。"""
    path = os.path.join(REPO_ROOT, "evals", "evals.json")
    data = json.load(open(path, encoding="utf-8"))
    evals = data.get("evals") or []
    expect(bool(evals), "evals.json is not empty", "")
    expect(data.get("policy", {}).get("executed_by"),
           "evals.json declares who executes it", "")
    missing = [e.get("id") for e in evals
               if not (e.get("machine_case") or "").strip()]
    expect(not missing,
           "every eval names the check_runner case (missing: %s)" % missing, "")
    src = open(os.path.join(SKILL_ROOT, "scripts", "check_runner.py"),
               encoding="utf-8").read()
    unbacked = []
    for e in evals:
        names = re.findall(r"\bcase_[a-z_]+", e.get("machine_case") or "")
        for n in names:
            if "def %s(" % n not in src:
                unbacked.append(n)
    expect(not unbacked,
           "every named case actually exists in check_runner.py (missing: %s)" % unbacked,
           "")
    expect(os.path.isfile(os.path.join(REPO_ROOT, "docs", "review-cases.md")),
           "human review cases live in docs/review-cases.md", "")


def case_open_marker():
    """待拍板只认行首标记；正文里提到不算。"""
    sys.path.insert(0, os.path.join(SKILL_ROOT, "scripts"))
    import workflow_next as w

    cases = [
        ("正文提到就不算:\n- 现有能力：`open_decision` 检「待拍板」标记后打 OPEN", False),
        ("待拍板", True),
        ("- 待拍板", True),
        ("- 待拍板：用全量还是三态？", True),
        ("> 待拍板", True),
        ("# 决定\n\n- 原话：改一处\n- 待拍板\n", True),
        ("- 待拍板\n已拍板：用全量\n", False),
        ("- 待拍板", True),
        ("没有这个标记\n", False),
    ]
    for text, want in cases:
        got = w.file_is_open(text)
        expect(got == want,
               "file_is_open(%r) should be %s" % (text[:30], want),
               "got %s" % got)
    text = "- 待拍板\n已拍板：A\n- 待拍板\n已拍板：B\n"
    expect(w.file_is_open(text) is False,
           "closed markers do not reopen the file", text)


def case_evidence_first():
    """查证义务必须在 scope.md 里，且带可判定边界。"""
    scope = open(os.path.join(SKILL_ROOT, "references", "scope.md"),
                  encoding="utf-8").read()
    expect("查证义务" in scope,
           "scope.md keeps the evidence-first section", "")
    for needle in ("本机文件", "业务口径", "卡在哪", "谁去补"):
        expect(needle in scope,
               "scope.md names the boundary marker %r" % needle, "")
    expect("不通过的样子" in scope,
           "scope.md carries a failing example", "")
    agents = open(os.path.join(REPO_ROOT, "AGENTS.md"),
                   encoding="utf-8").read()
    expect("先查完再给方案" in agents,
           "AGENTS.md points at the evidence-first rule", "")


def case_foreign():
    """装进哪个仓库，就用哪个仓库的副本（不是技能源）。"""
    with TestRoot("dw-foreign-") as r:
        r.git_init()
        r.write(".cursor/skills/keep-me/SKILL.md", "keep\n")
        r.make_pkg(lock="npm")

        proc = r.install("--project", "--with-hooks")
        copy = os.path.join(r.path, ".cursor", "skills", "data-workflow")
        expect(proc.returncode == 0 and os.path.isdir(copy)
               and not os.path.islink(copy),
               "foreign install copies the skill",
               proc.stdout + proc.stderr)

        copy_runner = r.install_runner()
        expect(
            os.path.realpath(copy_runner).startswith(os.path.realpath(r.path) + os.sep)
            and os.path.isfile(os.path.join(r.path, ".cursor", "skills",
                                            "keep-me", "SKILL.md")),
            "copy stays in the foreign repo and keeps the other skill",
            copy_runner,
        )

        hooks = json.load(open(os.path.join(r.path, ".cursor", "hooks.json"),
                                encoding="utf-8"))
        cmds = []
        for entries in (hooks.get("hooks") or {}).values():
            for entry in entries:
                cmds.append(entry.get("command") or "")
        expect(any(cmd.endswith("data-workflow/hooks/session-start") for cmd in cmds)
               and all(REPO_ROOT not in cmd for cmd in cmds),
               "foreign hooks point at the copy", "\n".join(cmds))
        expect(all(entry.get("failClosed") is not True
                   for entries in (hooks.get("hooks") or {}).values()
                   for entry in entries),
               "hooks do not fail closed",
               json.dumps(hooks, ensure_ascii=False))

        config_path = os.path.join(copy, "config.yaml")
        config_text = open(config_path, encoding="utf-8").read()
        paths = subprocess.run(
            [BASH, os.path.join(copy, "scripts", "paths.sh")],
            cwd=r.path, capture_output=True, text=True, encoding="utf-8",
            env=clean_env(),
        )
        expect("check_runner" not in config_text
               and "KNOW=''" in paths.stdout
               and "TEMPLATES=''" in paths.stdout
               and "REPO=''" in paths.stdout,
               "foreign knowledge path stays empty",
               paths.stdout + paths.stderr)

        gate = os.path.join(copy, "hooks", "gate-edit")
        expect(
            subprocess.run([BASH, gate], input="{}", cwd=r.path,
                           capture_output=True, text=True, encoding="utf-8",
                           env=clean_env()).returncode == 0,
            "foreign hook runs", "")
        import subprocess as _sp

        def _copy_run(*args):
            return _sp.run(
                [PY, copy_runner, *args, "--repo", r.path], cwd=r.path,
                capture_output=True, text=True, encoding="utf-8",
                env=r.env(clean_env()),
            )

        started = _copy_run("start", "change", FEATURE)
        r.write_decision()
        stepped = _copy_run("done", FEATURE)
        finished = _copy_run("done", FEATURE)
        record = json.load(open(os.path.join(r.path, "specs", FEATURE, "run.json"),
                                 encoding="utf-8"))
        log = open(os.path.join(r.path, "specs", FEATURE, "verify.log"),
                    encoding="utf-8").read()
        expect(started.returncode == 0 and stepped.returncode == 0
               and finished.returncode == 0
               and record.get("stage") == 3
               and "cmd npm test" in log and "check_runner" not in log,
               "foreign code step uses the copy and npm test",
               started.stdout + stepped.stdout + finished.stdout + log)

        hook_out = subprocess.run(
            [BASH, os.path.join(copy, "hooks", "session-start")],
            cwd=r.path, capture_output=True, text=True, encoding="utf-8",
            env=r.env(clean_env()), check=True,
        )
        injected = json.loads(hook_out.stdout).get("additional_context") or ""
        expect("NOTICE" in injected and FEATURE in injected
               and "NEED" not in injected and "写完后运行" not in injected,
               "foreign session hook injects a notice and leaves the run",
               injected)

        feature = _copy_run("start", "feature", "chain")
        expect("NEED specs/chain/spec.md" in feature.stdout
               and "stages/requirement-analysis/SKILL.md" in feature.stdout,
               "foreign copy still starts the feature chain",
               feature.stdout)

        review = _copy_run("start", "review-only", "look")
        expect(review.returncode == 0,
               "foreign review run starts", review.stdout)

        cmds_dir = os.path.join(r.path, ".cursor", "commands")
        next_cmd = open(os.path.join(cmds_dir, "dw-next.md"),
                         encoding="utf-8").read()
        expect("workflow_next.py next" in next_cmd
               and os.path.isfile(os.path.join(cmds_dir, "dw-done.md"))
               and os.path.isfile(os.path.join(cmds_dir, "dw-wait.md"))
               and os.path.isfile(os.path.join(cmds_dir, "dw-start.md")),
               "foreign install adds slash commands", next_cmd)

        # reinstall keeps foreign config + other skill + other commands
        r.write(".cursor/commands/mine.md", "mine\n")
        r.write_ = None  # placeholder

        rpath = r.path

        class _Wrap:
            pass
        w = _Wrap()
        w.path = rpath

        # 重写 config.yaml，追加 verify
        with open(os.path.join(copy, "config.yaml"), "a", encoding="utf-8") as fh:
            fh.write('verify: "echo foreign-marker"\n')
        again = r.install(rpath)
        kept = open(os.path.join(copy, "config.yaml"), encoding="utf-8").read()
        other = open(os.path.join(rpath, ".cursor", "skills", "keep-me", "SKILL.md"),
                      encoding="utf-8").read()
        mine = open(os.path.join(rpath, ".cursor", "commands", "mine.md"),
                    encoding="utf-8").read()
        expect(again.returncode == 0
               and 'verify: "echo foreign-marker"' in kept
               and other == "keep\n" and mine == "mine\n"
               and "COMMAND " in again.stdout,
               "reinstall keeps foreign config, the other skill, and other commands",
               again.stdout + again.stderr + kept)

        removed = r.install("--unlink", rpath)
        expect(removed.returncode == 0
               and not os.path.isfile(os.path.join(rpath, ".cursor", "commands",
                                                     "dw-next.md"))
               and open(os.path.join(rpath, ".cursor", "commands", "mine.md"),
                        encoding="utf-8").read() == "mine\n"
               and open(os.path.join(rpath, ".cursor", "skills", "keep-me",
                                      "SKILL.md"), encoding="utf-8").read() == "keep\n",
               "unlink removes only the dw slash commands",
               removed.stdout + removed.stderr)


def case_default_no_hooks():
    """默认安装（不加 --with-hooks）不写 hooks.json。"""
    with TestRoot("dw-defaulthooks-") as root, TestRoot("dw-home-") as home:
        root.git_init()
        os.makedirs(os.path.join(root.path, ".cursor"))
        os.makedirs(os.path.join(home.path, ".cursor"))
        proc = root.install(home=home.path)
        expect(proc.returncode == 0
               and not os.path.exists(os.path.join(root.path, ".cursor", "hooks.json")),
               "default install writes no hooks.json",
               proc.stdout + proc.stderr)
        expect(not os.path.isdir(os.path.join(root.path, ".cursor", "skills",
                                                "data-workflow")),
               "default install leaves no skill copy in the project",
               proc.stdout + proc.stderr)
        expect(os.path.isdir(os.path.join(home.path, ".cursor", "skills",
                                            "data-workflow", "stages")),
               "default install puts the full skill in HOME",
               proc.stdout + proc.stderr)
        expect(os.path.isfile(os.path.join(root.path, ".cursor", "commands",
                                             "dw-next.md")),
               "default install still writes slash commands",
               proc.stdout + proc.stderr)


def case_record_follows_install():
    """装进哪个仓库，运行记录就写在那个仓库。"""
    with TestRoot("dw-record-") as root, TestRoot("dw-rechome-") as home:
        root.git_init()
        os.makedirs(os.path.join(root.path, ".cursor"))
        os.makedirs(os.path.join(home.path, ".cursor"))
        root.install("--project", home=home.path)
        runner = os.path.join(root.path, ".cursor", "skills", "data-workflow",
                              "scripts", "workflow_next.py")
        env = clean_env()
        proc = subprocess.run(
            [PY, runner, "start", "change", FEATURE, "--repo", root.path],
            cwd=root.path, capture_output=True, text=True, encoding="utf-8",
            env=env,
        )
        expect(os.path.isfile(os.path.join(root.path, "specs", FEATURE, "run.json")),
               "record lands in the installed repo",
               proc.stdout + proc.stderr)
        expect(not os.path.isdir(os.path.join(REPO_ROOT, "runs")),
               "record does not leak back into the skill source repo", "")
        ignore = os.path.join(root.path, ".gitignore")
        text = open(ignore, encoding="utf-8").read() if os.path.isfile(ignore) else ""
        expect("specs/" in text,
               "install keeps specs/ out of git status", text)


# ── main ─────────────────────────────────────────────────────────────────


def main():
    case_none()
    case_npm()
    case_make()
    case_gomod()
    case_install_makes_tool_dir()
    case_verify_wins()
    case_pnpm()
    case_yarn()
    case_pytest()
    case_cargo()
    case_answer()
    case_hook_quiet()
    case_gate_read_write()
    case_gate_tool_case()
    case_gate_strict()
    case_gate_no_python()
    case_utf8_output()
    case_no_phantom()
    case_intake()
    case_restated_raw()
    case_domains()
    case_domain_docs()
    case_approve()
    case_gate_check()
    case_evidence_log()
    case_decided()
    case_skill_routing()
    case_intent_confirm_wired()
    case_readme_matches_requires()
    case_docs_match_reality()
    case_open_marker()
    case_evidence_first()
    case_card_writeback()
    case_knowledge_feedback()
    case_gate_edit_coverage()
    case_self_check_not_a_gate()
    case_g7_gate_runs()
    case_lazy_load()
    case_evals_are_runnable()
    case_foreign()
    case_default_no_hooks()
    case_record_follows_install()
    print("OK")


if __name__ == "__main__":
    main()
