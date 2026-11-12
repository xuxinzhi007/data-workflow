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


def runs(name, *args):
    """`which` 找得到 ≠ 跑得起来。

    真实的坑：pnpm 存在但那台机器上它自己一跑就被信号杀掉（Killed: 9），
    `tool("pnpm")` 仍然 True，于是 case_pnpm 断言「应该推进」——而 verify
    永远 RED。测的环境不是用的环境，就会把环境故障读成技能故障。
    这里只要求它至少能跑完并给出退出码（0 或 1 都算能用）。
    """
    if not tool(name):
        return False
    try:
        proc = subprocess.run([name, *args], capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return False
    return proc.returncode in (0, 1)


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

    # ── 技能副本（改 workflow JSON 用）──

    def skill_copy(self, workflow, mutate):
        """复制一份技能到本仓库内，改一个 workflow JSON，返回跑副本的入口。

        close_if.fingerprint 必须以真实 bug 为转移，而本仓库出的模板是恒 exit 0
        的占位（故意的：不改就关不了单）。所以每个要真正关单的用例都得改 JSON。
        改**源**技能会污染其它用例、也会把仓库弄脏，只能改副本。

        返回 (run_copy, wf_path)；run_copy(*args) 用副本的 runner 打本仓库。
        副本里自己写 run.json，所以副本 runner 与源 runner 看到的是同一个 store。
        """
        copy = os.path.join(self.path, "skillcopy")
        shutil.copytree(SKILL_ROOT, copy)
        wf_path = os.path.join(copy, "workflows", "%s.json" % workflow)
        with open(wf_path, encoding="utf-8") as fh:
            data = json.load(fh)
        mutate(data)
        with open(wf_path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        copy_runner = os.path.join(copy, "scripts", "workflow_next.py")

        def run_copy(*args):
            return subprocess.run(
                [PY, copy_runner, *args, "--repo", self.path],
                capture_output=True, text=True, encoding="utf-8",
                env=self.env(clean_env()),
            )

        return run_copy, wf_path

    def write_spec_fixed(self, feature=FEATURE, extra=""):
        """写出满足出厂的三个 close_if 字面量（已修复 / 验证命令 / 退出码）。"""
        return self.write(
            "specs/%s/spec.md" % feature,
            "- 已修复 commit abc123\n- 验证命令: go test ./...\n- 退出码: 0\n" + extra,
        )

    def evidence_path(self, feature=FEATURE):
        return os.path.join(self.path, "specs", feature, "evidence.log")

    def evidence_text(self, feature=FEATURE):
        p = self.evidence_path(feature)
        return open(p, encoding="utf-8").read() if os.path.isfile(p) else ""


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
                   "pnpm test", runs("pnpm", "--version"))


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


def case_commands_path_is_resolvable():
    """命令文件里的脚本路径，在真实安装方式下必须能解析到。

    曾经的 bug：四个 commands/*.md 都写死「装进别的仓库后在
    `.cursor/skills/data-workflow/scripts/workflow_next.py`」，但默认安装（$HOME）
    根本不往项目里放技能。照这行找文件，必然 ENOENT。
    """
    names = ("dw-next.md", "dw-done.md", "dw-wait.md", "dw-start.md")

    # 1. 默认安装（$HOME）：项目里没有技能副本，命令里的路径必须指向能跑到的位置
    with TestRoot("dw-cmdhome-") as r, TestRoot("dw-cmdhome-h-") as home:
        r.git_init()
        r.write("README.md", "probe\n")
        os.makedirs(os.path.join(r.path, ".cursor"), exist_ok=True)
        proc = r.install(home=home.path)
        expect(proc.returncode == 0, "默认安装成功", proc.stdout + proc.stderr)
        expect(not os.path.isdir(os.path.join(r.path, ".cursor", "skills", "data-workflow")),
               "默认安装不往项目里放技能副本", "")
        for name in names:
            text = open(os.path.join(r.path, ".cursor", "commands", name),
                        encoding="utf-8").read()
            # 命令文件必须给出可解析的具体路径，不能只有「skills/data-workflow/...」
            # 这种相对当前项目、但项目里并不存在的位置。
            expect(".cursor/skills/data-workflow" not in text
                   or "装进别的仓库后" not in text,
                   "%s 不再把「.cursor/skills」当成唯一落点" % name, text)
            # 落点必须是一个真的能跑到的绝对路径（install 时注入），
            # 或者明确写了 $HOME / 解析顺序。不接受「只在项目里」的相对路径。
            import re as _re
            abs_paths = _re.findall(r"(/[A-Za-z0-9_./~-]*workflow_next\.py)", text)
            ok = bool(abs_paths) or "$HOME" in text or "~/" in text
            expect(ok, "%s 给了可解析的绝对路径或 HOME 落点" % name, text)
            for p in abs_paths:
                expect(os.path.isfile(p), "%s 里的路径真的存在：%s" % (name, p), text)
            # 占位符不许漏出去
            expect("{{RUNNER}}" not in text and "{{SKILL}}" not in text,
                   "%s 没有漏掉未替换的占位符" % name, text)

    # 2. --project：技能副本真的在项目里，命令里的路径要指得对
    with TestRoot("dw-cmdproj-") as r, TestRoot("dw-cmdproj-h-") as home:
        r.git_init()
        r.write("README.md", "probe\n")
        os.makedirs(os.path.join(r.path, ".cursor"), exist_ok=True)
        proc = r.install("--project", home=home.path)
        expect(proc.returncode == 0, "--project 安装成功", proc.stdout + proc.stderr)
        runner = os.path.join(r.path, ".cursor", "skills", "data-workflow",
                              "scripts", "workflow_next.py")
        expect(os.path.isfile(runner), "--project 真的把 runner 放进项目", runner)
        for name in names:
            text = open(os.path.join(r.path, ".cursor", "commands", name),
                        encoding="utf-8").read()
            expect("workflow_next.py" in text, "%s 提到了 runner" % name, text)


def case_default_install_commands_land_in_project():
    """默认安装（$HOME）必须把 4 个命令写进**当前项目**，并在项目没有 .cursor 时建出来。

    曾经的 bug：install_commands 在 `$root/.cursor` 不存在时静默 return 0，
    然后 DONE 仍然打印「Cursor 命令在 <base>/.cursor/commands/」——一个不存在的目录。
    在全新项目里第一次装，4 个命令就这么丢了，而且没有任何提示。
    """
    names = ("dw-next.md", "dw-done.md", "dw-wait.md", "dw-start.md")

    # 1. 默认安装 + 项目里没有 .cursor：命令仍要落到项目
    with TestRoot("dw-cmdnp-") as r, TestRoot("dw-cmdnp-h-") as home:
        r.git_init()
        r.write("README.md", "probe\n")
        expect(not os.path.isdir(os.path.join(r.path, ".cursor")),
               "前置：项目本来没有 .cursor", "")
        proc = r.install(home=home.path)
        expect(proc.returncode == 0, "默认安装成功", proc.stdout + proc.stderr)
        for name in names:
            target = os.path.join(r.path, ".cursor", "commands", name)
            expect(os.path.isfile(target),
                   "默认安装把 %s 写进当前项目" % name,
                   proc.stdout + proc.stderr)
        # 技能副本不该进项目
        expect(not os.path.isdir(os.path.join(r.path, ".cursor", "skills", "data-workflow")),
               "默认安装仍然不往项目放技能副本", "")
        # 输出里报的路径必须真的存在
        for line in proc.stdout.splitlines():
            if "commands/" in line and "/" in line:
                import re as _re
                m = _re.search(r"(/[^ ]*?/commands/)", line)
                if m:
                    expect(os.path.isdir(m.group(1)),
                           "输出里报的 commands 目录真的存在：%s" % m.group(1), line)

    # 2. --project 也要把命令落到项目
    with TestRoot("dw-cmdproj2-") as r, TestRoot("dw-cmdproj2-h-") as home:
        r.git_init()
        r.write("README.md", "probe\n")
        proc = r.install("--project", home=home.path)
        expect(proc.returncode == 0, "--project 安装成功", proc.stdout + proc.stderr)
        for name in names:
            expect(os.path.isfile(os.path.join(r.path, ".cursor", "commands", name)),
                   "--project 把 %s 写进项目" % name, proc.stdout + proc.stderr)


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


def case_description_is_a_trigger():
    """description 是触发器，不是流程摘要。

    照 tempest 的判据：description 里写「先跑 X 再读 Y」这类步骤，agent 会照着摘要
    办事，而不去读正文。data-workflow 是唯一靠 description 自动触发的 skill，
    stage 文件按路径读、不靠 description，所以只查这一个。
    """
    import re as _re
    text = open(os.path.join(SKILL_ROOT, "SKILL.md"), encoding="utf-8").read()
    m = _re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    expect(bool(m), "SKILL.md 有 frontmatter", text[:80])
    front = m.group(1)
    desc = _re.search(r"^description:\s*(.+)$", front, _re.M)
    expect(bool(desc), "description 存在", front)
    d = desc.group(1).strip()
    expect(len(d) <= 1024, "description <= 1024 字符", len(d))

    # 触发器式：描述「什么时候用」。禁止把执行步骤写进来。
    step_markers = ["先跑", "然后去读", "接着", "再运行", "第一步"]
    leaked = [k for k in step_markers if k in d]
    expect(not leaked,
           "description 不写执行步骤（会盖掉正文）：%s" % leaked, d)

    # 必须点明触发场景
    trigger_markers = ["当用户说", "当用户", "Use when", "用到时"]
    expect(any(k in d for k in trigger_markers),
           "description 有触发条件", d)


def case_stages_have_failure_modes():
    """每个 stage 必须有一段失败模式，且不靠新增章节数来堆体积。

    历史证据：specs/ 20 次运行，「未知」栏 88% 写「无」——说明文件只讲「做什么」，
    没讲「最容易错成什么样」。失败模式段是补这一层的唯一位置。
    体积约束：每个 stage 文件 <= 200 行（超过说明该拆 reference，不是加长）。
    """
    import re as _re
    stages_dir = os.path.join(SKILL_ROOT, "stages")
    missing = []
    too_long = []
    for name in sorted(os.listdir(stages_dir)):
        path = os.path.join(stages_dir, name, "SKILL.md")
        if not os.path.isfile(path):
            continue
        text = open(path, encoding="utf-8").read()
        lines = text.count("\n") + 1
        if lines > 200:
            too_long.append("%s(%d)" % (name, lines))
        # 认「常见错法」或「失败模式」两种标题
        if not _re.search(r"^#+\s*.*(常见错法|失败模式|最容易错)", text, _re.M):
            missing.append(name)
    expect(not missing,
           "每个 stage 都有失败模式段（缺：%s）" % missing, "")
    expect(not too_long,
           "stage 文件不超 200 行（超：%s）" % too_long, "")


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


def case_confess_never_gates():
    """confess 通道的机制性质：写不写、写什么都不影响推进。

    这是整套设计的支架。以后谁“顺手”把 confess 接进任何门，这几条会红灯。
    见 docs/dev/c3-c9-experiment.md 第一层。
    """
    # 1. needs_confess 对写决定的阶段返回 False
    sys.path.insert(0, os.path.join(SKILL_ROOT, "scripts"))
    import workflow_next as W  # noqa: E402
    decide = {"id": 1, "name": "写下决定"}
    coding = {"id": 2, "name": "按决定改", "code": True}
    verify = {"id": 3, "name": "核对"}
    expect(not W.needs_confess(decide), "写决定的阶段不要自白", str(decide))
    expect(W.needs_confess(coding), "改代码的阶段要自白", str(coding))
    expect(W.needs_confess(verify), "核对阶段要自白", str(verify))

    # 2. 有 confess / 没 confess，同一份 decision.md 停在同一个地方
    with TestRoot("dw-confess-") as r:
        r.git_init()
        r.write("a.txt", "x\n").git_commit()
        r.make_config('verify: "true"\n')
        r.change_reach()
        baseline = r.run("next").stdout
        r.write("specs/%s/confess/1.md" % FEATURE, "无可坦白\n")
        expect(r.run("next").stdout == baseline,
               "写一份自白不改变下一步的输出", (baseline, r.run("next").stdout))

    # 3. confess 说「我超范围改了」，不让流程退回
    with TestRoot("dw-confess-") as r:
        r.git_init()
        r.write("a.txt", "x\n").git_commit()
        r.make_config('verify: "true"\n')
        r.change_reach()
        r.write("specs/%s/confess/1.md" % FEATURE,
                "我超范围改了 3 个文件，verify 实际没跑到。\n")
        out = r.run("next")
        expect("DO" in out.stdout and "GATE" not in out.stdout
               and "OPEN" not in out.stdout and "WAIT" not in out.stdout,
               "自白里承认越界不让流程退回也不打门", out.stdout)
        expect(r.read_run(FEATURE).get("stage") == 2,
               "自白不改变 stage", str(r.read_run(FEATURE)))

    # 4. 自白文件存在与内容是「无可坦白」时，不产生任何待办提示
    with TestRoot("dw-confess-") as r:
        r.git_init()
        r.write("a.txt", "x\n").git_commit()
        r.make_config('verify: "true"\n')
        r.change_reach()
        r.write("a.txt", "x\ncode change\n")
        confirm = r.change_done().stdout
        expect("CONFESS" in confirm, "改完代码那一刻要打 CONFESS", confirm)
        r.write("specs/%s/confess/2.md" % FEATURE, "无可坦白\n")
        expect("UNCONFESSED" not in r.run("next").stdout,
               "写了自白就不再提醒漏写", r.run("next").stdout)


def case_honesty_stats_runs():
    """honesty_stats 的两个子命令都要能跑，且「无」/ 真实未知的判定正确。

    这个脚本给 C3/C9 提供真实分布。它挂了，实验就没有起点。
    """
    stats = os.path.join(REPO_ROOT, "scripts", "honesty_stats.py")
    if not os.path.isfile(stats):
        expect(False, "scripts/honesty_stats.py 存在", stats)
    # 1. 判「无」的几种写法
    sys.path.insert(0, os.path.join(SKILL_ROOT, "scripts"))
    sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))
    import importlib.util
    spec = importlib.util.spec_from_file_location("honesty_stats", stats)
    H = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(H)
    for text in ("无", "无（三个已认的债明确不在本次范围）", "无歧义", "暂无"):
        expect(H.is_none(text) is True, "判为「无」：%s" % text, text)
    for text in ("不知道 knowledge_drift 的输出是否够用",
                 "deepeek 的确切产品形态"):
        expect(H.is_none(text) is False, "判为真实未知：%s" % text[:20], text)
    expect(H.is_none(None) is None, "没有这一栏时返回 None，不进分母", "")

    # 2. 在临时 specs 上跑一次 specs 子命令
    with TestRoot("dw-stats-") as r:
        r.write("specs/a/decision.md", "- 未知：无\n- 可能理解错：有\n")
        r.write("specs/b/decision.md", "- 未知：不知道 X 是否成立\n")
        r.write("specs/c/decision.md", "- 本质：没写未知栏\n")
        out = subprocess.run(
            [PY, stats, "specs"], cwd=r.path, capture_output=True,
            text=True, encoding="utf-8",
        )
        expect(out.returncode == 0, "specs 子命令 exit 0", out.stdout + out.stderr)
        expect("DECISION 共 3 份" in out.stdout, "数对了 3 份", out.stdout)
        expect("有「未知」栏 2 份" in out.stdout, "认出 2 份有未知栏", out.stdout)
        expect("写了真实未知 1 份" in out.stdout, "认出 1 份真实未知", out.stdout)

    # 3. 在仓库自己身上跑一遍，不许崩
    real = subprocess.run(
        [PY, stats, "specs"], cwd=REPO_ROOT, capture_output=True,
        text=True, encoding="utf-8",
    )
    expect(real.returncode == 0, "在真实 specs/ 上跑得通", real.stdout + real.stderr)


def case_confess_scope_follows_workflow():
    """自白第一个问题要引对本 workflow 的产物，不能硬写 decision.md。

    bugfix / hotfix / feature 没有 decision.md。写错了 AI 会去找一个不存在的文件，
    比不写更糟。
    """
    sys.path.insert(0, os.path.join(SKILL_ROOT, "scripts"))
    import workflow_next as W  # noqa: E402
    coding = {"id": 2, "name": "按决定改", "code": True}
    expect(W.confess_scope("change", coding) == "decision.md",
           "change 引 decision.md", W.confess_scope("change", coding))
    for name, want in (("bugfix", "根因定位"), ("hotfix", "止血决策")):
        got = W.confess_scope(name, coding)
        expect(got == want, "%s 引自己的产物" % name, got)
        expect("decision.md" not in got,
               "%s 的问题里不出现 decision.md" % name, got)
    expect("plan.md" in W.confess_scope("feature", coding),
           "feature 引方案产物", W.confess_scope("feature", coding))
    # 未知 workflow 不许抛异常
    expect(W.confess_scope("nonexistent", coding),
           "未知 workflow 有兜底文案", "")
    # stage 自己声明时优先
    expect(W.confess_scope("change", {"confess_scope": "自定义产物"}) == "自定义产物",
           "stage.confess_scope 优先", "")

    # 端到端：bugfix 的 done 打出来的问题里不出现 decision.md
    with TestRoot("dw-scope-") as r:
        r.git_init()
        r.write("a.txt", "x\n").git_commit()
        r.make_config('verify: "true"\n')
        r.run("start", "bugfix", FEATURE, "探测根因产物")
        r.write("specs/%s/run.json" % FEATURE,
                json.dumps({"workflow": "bugfix", "feature": FEATURE,
                            "stage": 3, "status": "working"}, ensure_ascii=False))
        r.write("a.txt", "x\nfix\n")
        out = r.change_done()
        expect("CONFESS" in out.stdout, "bugfix 的 code 阶段打 CONFESS", out.stdout)
        expect("decision.md" not in out.stdout,
               "bugfix 的 CONFESS 问题里不出现 decision.md", out.stdout)


def case_no_hints_switch():
    """DATA_WORKFLOW_NO_HINTS=1 只摘 SELF_CHECK，其余输出逐字不变。

    C3 对照实验的两组必须用同一个 runner，否则开关本身就带了别的变量。
    """
    with TestRoot("dw-hints-") as r:
        r.git_init()
        r.write("a.txt", "x\n").git_commit()
        r.run("start", "change", FEATURE, "探测提示开关")
        text_on = r.run("next", FEATURE).stdout
        env = r.env()
        env["DATA_WORKFLOW_NO_HINTS"] = "1"
        off = subprocess.run(
            [PY, RUNNER, "next", FEATURE, "--repo", r.path],
            capture_output=True, text=True, encoding="utf-8", env=env,
        )
        text_off = off.stdout
        expect("SELF_CHECK" in text_on, "默认打印 SELF_CHECK", text_on)
        expect("SELF_CHECK" not in text_off, "NO_HINTS=1 时不打印 SELF_CHECK", text_off)
        stripped = "\n".join(
            line for line in text_on.splitlines()
            if not line.startswith("SELF_CHECK")
        ) + "\n"
        expect(stripped == text_off,
               "摘掉 SELF_CHECK 后其余输出逐字不变",
               ("--on--", stripped, "--off--", text_off))


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


def case_close_exit():
    """close 出口：三项同时满足才关单；关掉后 next/done 都不再推阶段。"""
    with TestRoot("dw-close-") as r:
        r.git_init()
        r.make_config('verify: "true"\n')
        started = r.run("start", "bugfix", FEATURE, "状态卡住")
        expect(started.returncode == 0,
               "bugfix starts", started.stdout + started.stderr)
        # 有 close_if 的阶段要把出口告诉 AI，否则它只会一直往下推。
        expect("CLOSE_IF" in started.stdout and "fingerprint" in started.stdout
               and "exit 0 表示「bug 仍然复现」" in started.stdout,
               "stage with close_if advertises the exit and its polarity to the AI",
               started.stdout)

        # 字面量不全 -> GATE，不许关
        r.write("specs/%s/spec.md" % FEATURE, "- 只有症状，没写已修复\n")
        partial = r.run("close", FEATURE)
        expect(partial.returncode != 0 and "GATE" in partial.stdout
               and r.read_run().get("status") == "working",
               "close refuses when the literal is missing", partial.stdout)

        # 出厂占位指纹必须关不了：它 exit 1，且说明要改什么。
        # 留一个恒真的占位等于给门开后门。
        r.write("specs/%s/spec.md" % FEATURE,
                "- 已修复 commit abc123\n- 验证命令: go test ./...\n- 退出码: 0\n")
        placeholder = r.run("close", FEATURE)
        expect(placeholder.returncode != 0 and "CHECK" in placeholder.stdout
               and r.read_run().get("status") == "working",
               "the shipped placeholder fingerprint cannot close a bug",
               placeholder.stdout)

        # 把指纹改成真命令后 -> 关，落 outcome
        copy = os.path.join(r.path, "skillcopy")
        shutil.copytree(SKILL_ROOT, copy)
        wf_path = os.path.join(copy, "workflows", "bugfix.json")
        with open(wf_path, encoding="utf-8") as fh:
            wf = json.load(fh)
        wf["stages"][0]["close_if"]["fingerprint"] = "exit 1"  # 不复现（exit1）= 可以关
        with open(wf_path, "w", encoding="utf-8") as fh:
            json.dump(wf, fh, ensure_ascii=False, indent=2)
        copy_runner = os.path.join(copy, "scripts", "workflow_next.py")

        def run_copy(*args):
            return subprocess.run(
                [PY, copy_runner, *args, "--repo", r.path],
                capture_output=True, text=True, encoding="utf-8",
                env=r.env(clean_env()),
            )

        closed = run_copy("close", FEATURE)
        record = r.read_run()
        log = open(os.path.join(r.path, "specs", FEATURE, "evidence.log"),
                   encoding="utf-8").read()
        expect(closed.returncode == 0 and "CLOSED %s fixed" % FEATURE in closed.stdout
               and record.get("status") == "closed"
               and record.get("outcome") == "fixed"
               and "outcome=fixed" in log,
               "close reaches the terminal state and records the outcome",
               closed.stdout + log)

        # 幂等：再关一次不多写证据、不推阶段
        again = run_copy("close", FEATURE)
        log2 = open(os.path.join(r.path, "specs", FEATURE, "evidence.log"),
                    encoding="utf-8").read()
        expect(again.returncode == 0 and "CLOSED" in again.stdout
               and log2.count("\n") == log.count("\n"),
               "close is idempotent and writes no second evidence line",
               again.stdout + log2)

        # next 之后只打 CLOSED，不推 NEED / DO
        nxt = r.run("next", FEATURE)
        expect("CLOSED" in nxt.stdout and "NEED" not in nxt.stdout
               and "DO" not in nxt.stdout,
               "next on a closed run prints CLOSED and no next step", nxt.stdout)

        # done 之后也不推阶段
        done = r.run("done", FEATURE)
        expect(done.returncode == 0 and "CLOSED" in done.stdout
               and r.read_run().get("status") == "closed",
               "done on a closed run is an idempotent success", done.stdout)

        # 钩子不再注入：closed 是终态
        expect(r.hook_text() == "",
               "a closed run injects no NOTICE", r.hook_text())

        # 同名再 start 当新运行（与 done 一致），不再 ALREADY
        fresh = r.run("start", "bugfix", FEATURE, "另一件事")
        expect("ALREADY" not in fresh.stdout and fresh.returncode == 0,
               "start on a closed run proceeds as a fresh run", fresh.stdout)


def case_close_refuses_literal_only():
    """字面量齐了但指纹失败：bug 还在，不许关。

    这是整个出口设计的要害。docs/dev/learnings.md 记过：「未知」栏 88% 写「无」，
    因为那个自评没有外部锚点。一个只认字面量的出口，会变成第二个「未知=无」。
    """
    with TestRoot("dw-closefp-") as r:
        r.git_init()
        r.make_config('verify: "true"\n')
        # 临时技能副本，把 fingerprint 改成「一定失败」，模拟 bug 仍然存在
        copy = os.path.join(r.path, "skillcopy")
        shutil.copytree(SKILL_ROOT, copy)
        wf_path = os.path.join(copy, "workflows", "bugfix.json")
        with open(wf_path, encoding="utf-8") as fh:
            wf = json.load(fh)
        wf["stages"][0]["close_if"]["fingerprint"] = "exit 0"  # 仍然复现（exit0）= 不能关
        with open(wf_path, "w", encoding="utf-8") as fh:
            json.dump(wf, fh, ensure_ascii=False, indent=2)
        copy_runner = os.path.join(copy, "scripts", "workflow_next.py")

        def run_copy(*args):
            return subprocess.run(
                [PY, copy_runner, *args, "--repo", r.path],
                capture_output=True, text=True, encoding="utf-8",
                env=r.env(clean_env()),
            )

        run_copy("start", "bugfix", FEATURE, "还有问题")
        r.write("specs/%s/spec.md" % FEATURE,
                "- 已修复\n- 验证命令: go test\n- 退出码: 0\n")
        refused = run_copy("close", FEATURE)
        expect(refused.returncode != 0 and "CHECK" in refused.stdout
               and r.read_run().get("status") == "working",
               "all literals present but a failing fingerprint still refuses",
               refused.stdout)

        # 不配 close_if 的阶段没有出口 -> NO_EXIT
        with open(wf_path, encoding="utf-8") as fh:
            wf = json.load(fh)
        wf["stages"][0].pop("close_if", None)
        with open(wf_path, "w", encoding="utf-8") as fh:
            json.dump(wf, fh, ensure_ascii=False, indent=2)
        no_exit = run_copy("close", FEATURE)
        expect(no_exit.returncode != 0 and "NO_EXIT" in no_exit.stdout,
               "a stage without close_if answers NO_EXIT", no_exit.stdout)

        # 配错（缺 fingerprint）要响，不能静默禁掉出口
        with open(wf_path, encoding="utf-8") as fh:
            wf = json.load(fh)
        wf["stages"][0]["close_if"] = {"artifact": "specs/<feature>/spec.md",
                                       "literal": ["已修复"]}
        with open(wf_path, "w", encoding="utf-8") as fh:
            json.dump(wf, fh, ensure_ascii=False, indent=2)
        malformed = run_copy("close", FEATURE)
        expect("BAD close_if" in malformed.stdout,
               "a malformed close_if fails loudly instead of silently",
               malformed.stdout)


def case_close_fingerprint_polarity():
    """fingerprint 的极性：exit 0 = bug 仍在 = 关不了；exit 非 0 = 不在了 = 可以关。

    这个方向弄反就会在 bug 还活着的时候静默关单。这里不用 `exit 0`/`exit 1` 这种
    抽象命令，而是用**真实文件 + 真实 grep** 跑两个方向——因为实现和用例曾经
    同时拿错极性，269 条全绿也没拦住（见 docs/dev/learnings.md 2026-11-12）。
    """
    with TestRoot("dw-polarity-") as r:
        r.git_init()
        r.make_config('verify: "true"\n')
        copy = os.path.join(r.path, "skillcopy")
        shutil.copytree(SKILL_ROOT, copy)
        wf_path = os.path.join(copy, "workflows", "bugfix.json")
        with open(wf_path, encoding="utf-8") as fh:
            wf = json.load(fh)
        # 复现命令：app.go 里还有 stuck-status 就 exit 0（bug 还在）
        wf["stages"][0]["close_if"]["fingerprint"] = "grep -q 'stuck-status' app.go"
        with open(wf_path, "w", encoding="utf-8") as fh:
            json.dump(wf, fh, ensure_ascii=False, indent=2)
        copy_runner = os.path.join(copy, "scripts", "workflow_next.py")

        def run_copy(*args):
            return subprocess.run(
                [PY, copy_runner, *args, "--repo", r.path],
                capture_output=True, text=True, encoding="utf-8",
                env=r.env(clean_env()),
            )

        run_copy("start", "bugfix", FEATURE, "状态卡住")
        r.write("specs/%s/spec.md" % FEATURE,
                "- 已修复 commit abc123\n- 验证命令: go test\n- 退出码: 0\n")

        # 方向 1：bug 仍在（grep exit 0）-> 必须拒绝
        r.write("app.go", "package app // stuck-status\n")
        alive = run_copy("close", FEATURE)
        expect(alive.returncode != 0
               and r.read_run().get("status") == "working",
               "a still-reproducing bug (fingerprint exit 0) must NOT close",
               alive.stdout + json.dumps(r.read_run(), ensure_ascii=False))
        expect("CHECK" in alive.stdout and "不能关" in alive.stdout,
               "the refusal names the fingerprint and says why", alive.stdout)

        # 方向 2：真的不在了（grep exit 1）-> 可以关
        r.write("app.go", "package app // fixed\n")
        gone = run_copy("close", FEATURE)
        expect(gone.returncode == 0
               and r.read_run().get("status") == "closed"
               and r.read_run().get("outcome") == "fixed",
               "a no-longer-reproducing bug (fingerprint exit non-0) closes",
               gone.stdout + json.dumps(r.read_run(), ensure_ascii=False))


def case_start_new():
    """ALREADY 不是死路，--new 能开新的一条，且不覆盖旧记录。"""
    with TestRoot("dw-new-") as r:
        r.git_init()
        r.make_config('verify: "true"\n')
        first = r.run("start", "bugfix", FEATURE, "第一件事")
        expect(first.returncode == 0, "first start works", first.stdout)

        # 同名再来：不是失败，打出旧 RAW 和两条出路，且不再把旧链条甩回来
        again = r.run("start", "bugfix", FEATURE, "另一件事")
        expect(again.returncode == 0
               and "ALREADY" in again.stdout
               and "第一件事" in again.stdout
               and "--new" in again.stdout
               and "next %s" % FEATURE in again.stdout,
               "ALREADY names both ways out and echoes the old raw request",
               again.stdout)
        expect("RAW 另一件事" not in again.stdout,
               "ALREADY does not swallow the new request as if it were started",
               again.stdout)
        expect(r.read_run().get("raw_request") == "第一件事",
               "ALREADY leaves the old run untouched",
               json.dumps(r.read_run(), ensure_ascii=False))

        # --new 开 <feature>-2，再开就是 -3，旧的不动
        second = r.run("start", "bugfix", FEATURE, "第二件事", "--new")
        expect("NEW %s-2" % FEATURE in second.stdout
               and os.path.isfile(r.run_path("%s-2" % FEATURE)),
               "--new opens a suffixed run", second.stdout)
        third = r.run("start", "bugfix", FEATURE, "第三件事", "--new")
        expect("NEW %s-3" % FEATURE in third.stdout,
               "--new never reuses an occupied suffix", third.stdout)
        expect(r.read_run().get("raw_request") == "第一件事"
               and r.read_run("%s-2" % FEATURE).get("raw_request") == "第二件事",
               "--new never overwrites earlier runs",
               json.dumps(r.read_run(), ensure_ascii=False))


def case_closed_stops_notice():
    """closed 与 done/abandoned 同级：不再注入 NOTICE，也不再算未完成运行。"""
    with TestRoot("dw-closednotice-") as r:
        r.git_init()
        r.make_config('verify: "true"\n')
        r.run("start", "bugfix", FEATURE, "已修好的")
        expect("NOTICE" in r.hook_text(),
               "precondition: an open run injects a notice", r.hook_text())

        # 出厂占位指纹关不了；改成一个真命令才能关。
        copy = os.path.join(r.path, "skillcopy")
        shutil.copytree(SKILL_ROOT, copy)
        wf_path = os.path.join(copy, "workflows", "bugfix.json")
        with open(wf_path, encoding="utf-8") as fh:
            wf = json.load(fh)
        wf["stages"][0]["close_if"]["fingerprint"] = "exit 1"  # 不复现（exit1）= 可以关
        with open(wf_path, "w", encoding="utf-8") as fh:
            json.dump(wf, fh, ensure_ascii=False, indent=2)
        copy_runner = os.path.join(copy, "scripts", "workflow_next.py")

        def run_copy(*args):
            return subprocess.run(
                [PY, copy_runner, *args, "--repo", r.path],
                capture_output=True, text=True, encoding="utf-8",
                env=r.env(clean_env()),
            )

        r.write("specs/%s/spec.md" % FEATURE,
                "- 已修复\n- 验证命令: go test\n- 退出码: 0\n")
        closed = run_copy("close", FEATURE)
        expect(closed.returncode == 0, "close succeeds", closed.stdout)
        expect(r.hook_text() == "",
               "a closed run stops the session notice", r.hook_text())
        # 不指定 feature 的 next 也不该再把它当未完成
        bare = r.run("next")
        expect("CLOSED" not in bare.stdout and "NEED" not in bare.stdout,
               "bare next treats a closed run as finished", bare.stdout)


def case_gates_reach_code_stage():
    """code 阶段也走 OPEN / GATE / CHECK。以前 show() 在 code 之前就 return 了。

    后果：next 说 DO，done 说 GATE，中间没有任何提示。两个入口对同一阶段
    给出不同结论，AI 只能靠自己撞。
    """
    with TestRoot("dw-codegate-") as r:
        r.git_init()
        r.make_config('verify: "true"\n')

        # 造一个 code 阶段带 artifact + requires 的工作流副本
        copy = os.path.join(r.path, "skillcopy")
        shutil.copytree(SKILL_ROOT, copy)
        wf_path = os.path.join(copy, "workflows", "change.json")
        with open(wf_path, encoding="utf-8") as fh:
            wf = json.load(fh)
        code_stage = wf["stages"][1]
        code_stage["artifacts"] = ["specs/<feature>/code.md"]
        code_stage["requires"] = ["改了什么"]
        with open(wf_path, "w", encoding="utf-8") as fh:
            json.dump(wf, fh, ensure_ascii=False, indent=2)
        copy_runner = os.path.join(copy, "scripts", "workflow_next.py")

        def run_copy(*args):
            return subprocess.run(
                [PY, copy_runner, *args, "--repo", r.path],
                capture_output=True, text=True, encoding="utf-8",
                env=r.env(clean_env()),
            )

        run_copy("start", "change", FEATURE, "改一处")
        r.write_decision()
        run_copy("done", FEATURE)
        expect(r.read_run().get("stage") == 2,
               "precondition: reached the code stage",
               json.dumps(r.read_run(), ensure_ascii=False))

        # 产物没有 requires 里的字面量 -> next 要打 GATE，不能再打 DO
        r.write("specs/%s/code.md" % FEATURE, "随便写了点\n")
        nxt = run_copy("next", FEATURE)
        expect("GATE" in nxt.stdout and "DO" not in nxt.stdout,
               "next now gates a code stage instead of saying DO", nxt.stdout)
        expect("改了什么" in nxt.stdout,
               "the gate names the missing literal", nxt.stdout)

        r.write("specs/%s/code.md" % FEATURE, "改了什么: a.go\n")
        passed = run_copy("next", FEATURE)
        expect("DO" in passed.stdout and "GATE" not in passed.stdout,
               "a satisfied code stage still reaches DO", passed.stdout)

    # 回归：paths 为空的 code 阶段行为不变（change 原样 stage 2 就是这种）
    with TestRoot("dw-codegate2-") as r:
        r.git_init()
        r.write("a.txt", "x\n").git_commit()
        r.make_config('verify: "true"\n')
        r.change_reach()
        nxt = r.run("next", FEATURE)
        expect("DO" in nxt.stdout and "GATE" not in nxt.stdout
               and "OPEN" not in nxt.stdout,
               "a code stage with no judgeable artifact still just says DO",
               nxt.stdout)


def case_evidence_outcome_column():
    """outcome 只在给了值时才加这一列：历史证据行的格式不许改。"""
    sys.path.insert(0, os.path.join(SKILL_ROOT, "scripts"))
    import workflow_next as W  # noqa: E402

    with TestRoot("dw-outcome-") as r:
        r.git_init()
        r.make_config('verify: "true"\n')
        r.write("a.txt", "x\n").git_commit()
        run = {"feature": FEATURE, "workflow": "change", "stage": 1,
               "status": "working"}
        plain = W.record_evidence(r.path, run, {"id": 1})
        marked = W.record_evidence(r.path, run, {"id": 1}, outcome="fixed")
        expect("outcome=" not in plain,
               "an advance row without an outcome is unchanged", plain)
        expect(plain.endswith("by=runner"),
               "the row still ends with by=runner", plain)
        expect("outcome=fixed" in marked,
               "declaring the outcome appends the column", marked)


# ── close_if 判定表 ───────────────────────────────────────────────────────


# 表驱动用例里「这个键干脆不要」的哨兵：与 None / 空串区分开。
class _Drop:
    def __repr__(self):
        return "<drop>"


_DROP = _Drop()


def case_close_if_spec_table():
    """close_if_spec() 的表驱动用例：合格返回规范化 dict，不合格一律 None。

    不合格一律 None 而不是抛异常，是故意的：cmd_close 靠
    `"close_if" in stage and close_if_spec(stage) is None` 区分「没配出口」与
    「配错了」。配错要响（BAD close_if），没配要 NO_EXIT；两者都是 None 时
    就只能靠 close_if 键在不在来分流，所以这个返回约定是接口的一部分。
    """
    sys.path.insert(0, os.path.join(SKILL_ROOT, "scripts"))
    import workflow_next as W  # noqa: E402

    ok_stage = {"artifact": "specs/<feature>/spec.md",
                "literal": ["已修复"],
                "fingerprint": "grep -q x app.go"}

    def with_spec(spec):
        return {"close_if": spec}

    def replace(**kw):
        spec = dict(ok_stage)
        for key, value in kw.items():
            if value is _DROP:
                spec.pop(key, None)
            else:
                spec[key] = value
        return with_spec(spec)

    # (用例名, stage, 期望返回)
    cases = [
        ("no_dict", with_spec("x"), None),
        ("no_dict_list", with_spec(["已修复"]), None),
        ("empty_literal", replace(literal=[]), None),
        ("blank_literal_item", replace(literal=["已修复", ""]), None),
        ("whitespace_literal_item", replace(literal=["已修复", "   "]), None),
        ("non_str_literal_item", replace(literal=["已修复", 1]), None),
        ("no_fingerprint", replace(fingerprint=_DROP), None),
        ("blank_fingerprint", replace(fingerprint="   "), None),
        ("no_artifact", replace(artifact=_DROP), None),
        ("blank_artifact", replace(artifact=" "), None),
        # 没配 close_if 键：返回 None，但 malformed 为 False（cmd_close 靠这个分流 NO_EXIT）
        ("nonexit_no_key", {}, None),
        # 三项齐全 -> 规范化 dict，outcome 缺省 fixed
        ("default_outcome", replace(),
         {"artifact": "specs/<feature>/spec.md", "literal": ["已修复"],
          "fingerprint": "grep -q x app.go", "outcome": "fixed"}),
        ("custom_outcome", replace(outcome="wontfix"),
         {"artifact": "specs/<feature>/spec.md", "literal": ["已修复"],
          "fingerprint": "grep -q x app.go", "outcome": "wontfix"}),
        ("empty_outcome_falls_back", replace(outcome=""),
         {"artifact": "specs/<feature>/spec.md", "literal": ["已修复"],
          "fingerprint": "grep -q x app.go", "outcome": "fixed"}),
        # 首尾空白要 strip 掉，否则指纹命令带着空格跑不起来、字面量也匹配不上
        ("strips_whitespace", with_spec({"artifact": "  specs/<feature>/spec.md  ",
                                         "literal": ["  已修复 "],
                                         "fingerprint": "  grep -q x app.go  "}),
         {"artifact": "specs/<feature>/spec.md", "literal": ["已修复"],
          "fingerprint": "grep -q x app.go", "outcome": "fixed"}),
    ]
    for name, stage, want in cases:
        got = W.close_if_spec(stage)
        expect(got == want,
               "close_if_spec[%s] -> %r" % (name, want),
               "got=%r want=%r stage=%r" % (got, want, stage))

    # 「配错了」与「没配」必须在 close_if 键上可分：否则 cmd_close 会把
    # 没配出口的执行阶段报成 BAD，或者把配错的出口静默禁掉。
    # 两者都返回 None，唯一的分流依据是键在不在。
    nonexit_stage = {}
    malformed_stage = replace(literal=[])
    expect("close_if" not in nonexit_stage
           and W.close_if_spec(nonexit_stage) is None,
           "close_if_spec[nonexit] no key -> None and key absent "
           "(cmd_close: NO_EXIT)",
           "got stage=%r spec=%r want spec=None and key absent"
           % (nonexit_stage, W.close_if_spec(nonexit_stage)))
    expect("close_if" in malformed_stage
           and W.close_if_spec(malformed_stage) is None,
           "close_if_spec[malformed] present but bad -> None and key present "
           "(cmd_close: BAD close_if)",
           "got stage=%r spec=%r want spec=None and key present"
           % (malformed_stage, W.close_if_spec(malformed_stage)))

    # close_artifact_path：中文项 / 以 $ 开头落不成可判定路径。
    # 注意（实测，与 BAD 文案「通配符...都不行」不完全一致）：以 specs/ 开头的
    # 通配符**会**被放行（`specs/<feature>/*.md`），因为 artifact_paths 在通配符
    # 检查之前就 return 了。这里按真实行为钉住，不让未来改动悄悄改掉关单范围。
    for label, artifact, want in [
        ("plain", "specs/<feature>/spec.md", "specs/f/spec.md"),
        ("chinese", "中文产物", ""),
        ("dollar", "$CARDS/x.md", ""),
        ("glob_bare", "*.md", ""),
        ("glob_under_specs", "specs/<feature>/*.md", "specs/f/*.md"),
    ]:
        got = W.close_artifact_path({"artifact": artifact}, "f")
        expect(got == want,
               "close_artifact_path[%s] -> %r" % (label, want),
               "got=%r want=%r artifact=%r" % (got, want, artifact))


def case_close_judgement_table():
    """cmd_close 的判定表：唯一能关单的组合是 artifact✓ literal✓ fingerprint 不复现。

    每行一个独立的临时仓库。断言的共同点：走不通时 run.json 必须**原样**
    （status 仍 working、没有 outcome），因为「关错了」比「关不了」严重得多。
    """

    def fingerprint_alive(data):
        # 复现命令：app.go 里有 stuck-status 就 exit 0（bug 还在）
        data["stages"][0]["close_if"]["fingerprint"] = \
            "grep -q 'stuck-status' app.go"

    def bare(data):
        return None

    def no_exit(data):
        data["stages"][0].pop("close_if", None)

    def malformed(data):
        data["stages"][0]["close_if"] = {"artifact": "specs/<feature>/spec.md",
                                         "literal": ["已修复"]}

    def bad_artifact(data):
        data["stages"][0]["close_if"]["artifact"] = "中文产物"

    # (用例名, 改 JSON, spec.md 内容或 None, app.go 内容或 None,
    #  期望退出码, 期望 stdout 必须含, 期望 stdout 不许含)
    cases = [
        ("fingerprint_reproduces__refuse", fingerprint_alive,
         "- 已修复\n- 验证命令: go test\n- 退出码: 0\n",
         "package app // stuck-status\n",
         1, ["CHECK", "不能关"], ["CLOSED"]),
        ("literal_missing__gate", fingerprint_alive,
         "- 症状だけ，没写结论\n",
         "package app // fixed\n",
         1, ["GATE", "缺："], ["CLOSED"]),
        ("artifact_missing__need", fingerprint_alive, None,
         "package app // fixed\n",
         1, ["NEED specs/%s/spec.md" % FEATURE], ["CLOSED"]),
        ("template_placeholder__refuse", bare,
         "- 已修复\n- 验证命令: go test\n- 退出码: 0\n",
         "package app // stuck-status\n",
         1, ["CHECK", "不能关"], ["CLOSED"]),
        ("no_close_if__no_exit", no_exit,
         "- 已修复\n- 验证命令: go test\n- 退出码: 0\n",
         None, 1, ["NO_EXIT"], ["CLOSED"]),
        ("malformed__bad", malformed,
         "- 已修复\n- 验证命令: go test\n- 退出码: 0\n",
         None, 1, ["BAD close_if"], ["CLOSED"]),
        ("unresolvable_artifact__bad", bad_artifact,
         "- 已修复\n- 验证命令: go test\n- 退出码: 0\n",
         None, 1, ["BAD close_if"], ["CLOSED"]),
        # 正向对照：三关全过才关得掉。没有这一行，上面 7 行可能全是「什么都不行」
        ("all_pass__close", fingerprint_alive,
         "- 已修复\n- 验证命令: go test\n- 退出码: 0\n",
         "package app // fixed\n",
         0, ["CLOSED %s fixed" % FEATURE], []),
    ]

    for name, mutate, spec, app, want_code, must, must_not in cases:
        label = "close table[%s]" % name
        with TestRoot("dw-closetable-") as r:
            r.git_init()
            r.make_config('verify: "true"\n')
            run_copy, _ = r.skill_copy("bugfix", mutate)
            started = run_copy("start", "bugfix", FEATURE, "状态卡住")
            expect(started.returncode == 0, label + " starts",
                   started.stdout + started.stderr)
            if spec is not None:
                r.write("specs/%s/spec.md" % FEATURE, spec)
            if app is not None:
                r.write("app.go", app)

            proc = run_copy("close", FEATURE)
            got = proc.returncode
            expect(got == want_code, label + " exit -> %d" % want_code,
                   "got=%d want=%d\nstdout=%s\nstderr=%s"
                   % (got, want_code, proc.stdout, proc.stderr))
            for needle in must:
                expect(needle in proc.stdout,
                       label + " stdout contains %r" % needle,
                       "got stdout=%r\nwant substring=%r" % (proc.stdout, needle))
            for needle in must_not:
                expect(needle not in proc.stdout,
                       label + " stdout omits %r" % needle,
                       "got stdout=%r\nforbidden substring=%r"
                       % (proc.stdout, needle))
            if want_code != 0:
                record = r.read_run()
                expect(record.get("status") == "working"
                       and "outcome" not in record,
                       label + " leaves run.json untouched",
                       "want status=working and no outcome; got=%s"
                       % json.dumps(record, ensure_ascii=False))


def case_close_run_absent():
    """没有运行记录时 close 报 NO_RUN，且不凭空造出 specs/ 目录。"""
    with TestRoot("dw-closenorun-") as r:
        r.git_init()
        r.make_config('verify: "true"\n')
        proc = r.run("close", FEATURE)
        expect(proc.returncode == 1 and "NO_RUN %s" % FEATURE in proc.stdout,
               "close on a missing run answers NO_RUN",
               "got exit=%d stdout=%r" % (proc.returncode, proc.stdout))
        expect(not os.path.exists(r.run_path()),
               "close on a missing run writes no run.json",
               "run.json exists at %s" % r.run_path())


def case_close_on_stage_without_exit():
    """change 的第 1 阶段没有 close_if：close 必须 NO_EXIT，且 run.json 字节不变。"""
    with TestRoot("dw-closenoexit-") as r:
        r.git_init()
        r.make_config('verify: "true"\n')
        r.run("start", "change", FEATURE, "定架构")
        r.write_decision()
        before = open(r.run_path(), "rb").read()
        proc = r.run("close", FEATURE)
        after = open(r.run_path(), "rb").read()
        expect(proc.returncode == 1 and "NO_EXIT %s 1" % FEATURE in proc.stdout,
               "close on a stage without close_if answers NO_EXIT <feature> <stage>",
               "got exit=%d stdout=%r" % (proc.returncode, proc.stdout))
        expect(before == after,
               "NO_EXIT does not rewrite run.json",
               "bytes changed: before=%r after=%r" % (before, after))


def case_closed_is_terminal():
    """closed 与 done/abandoned 同级：next 不打 NEED/DO/STAGE，不推阶段，不注入 NOTICE。

    这是 D1 的主诉求本身：bug 修好后，工作流不许再要求继续排查。
    """
    with TestRoot("dw-terminal-") as r:
        r.git_init()
        r.make_config('verify: "true"\n')
        run_copy, _ = r.skill_copy(
            "bugfix", lambda d: d["stages"][0]["close_if"].__setitem__(
                "fingerprint", "exit 1"))  # 不复现 = 可以关
        run_copy("start", "bugfix", FEATURE, "状态卡住")
        r.write_spec_fixed()
        closed = run_copy("close", FEATURE)
        expect(closed.returncode == 0, "precondition: close succeeds",
               closed.stdout + closed.stderr)
        stage_after_close = r.read_run().get("stage")

        # next：只报 CLOSED，绝不把旧链条甩回来
        nxt = r.run("next", FEATURE)
        expect(nxt.returncode == 0 and "CLOSED %s fixed" % FEATURE in nxt.stdout,
               "next on a closed run prints CLOSED",
               "got exit=%d stdout=%r" % (nxt.returncode, nxt.stdout))
        for needle in ("NEED", "DO", "STAGE 2", "STAGE 1"):
            expect(needle not in nxt.stdout,
                   "next on a closed run does not print %r" % needle,
                   "forbidden %r in stdout=%r" % (needle, nxt.stdout))

        # done：幂等成功，不推阶段
        done = r.run("done", FEATURE)
        expect(done.returncode == 0 and "CLOSED" in done.stdout
               and r.read_run().get("stage") == stage_after_close
               and r.read_run().get("status") == "closed",
               "done on a closed run is an idempotent success that advances nothing",
               "got exit=%d stdout=%r stage=%r want stage=%r"
               % (done.returncode, done.stdout, r.read_run().get("stage"),
                  stage_after_close))

        # 钩子：closed 是终态，不再注入 NOTICE
        expect(r.hook_text() == "",
               "a closed run injects no session NOTICE",
               "got additional_context=%r" % r.hook_text())


def case_bare_next_skips_closed():
    """不指定 feature 的 next：closed 不进 MANY、不被当未完成、也不被选中推进。"""
    with TestRoot("dw-barenext-") as r:
        r.git_init()
        r.make_config('verify: "true"\n')
        for name in ("aa", "bb", "cc"):
            r.run("start", "change", name, "原话%s" % name)

        def close_run(name):
            path = r.run_path(name)
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            data["status"] = "closed"
            data["outcome"] = "fixed"
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False, indent=2)

        # 一条 closed + 两条 working -> MANY 只列两条 working
        close_run("aa")
        many = r.run("next")
        expect("MANY" in many.stdout,
               "bare next with two open runs answers MANY", many.stdout)
        expect("aa" not in many.stdout,
               "MANY omits the closed run",
               "forbidden 'aa' in MANY output=%r" % many.stdout)
        expect("bb" in many.stdout and "cc" in many.stdout,
               "MANY lists both open runs", many.stdout)

        # 全部 closed -> 当已完成，不再报 NEED
        close_run("bb")
        close_run("cc")
        bare = r.run("next")
        expect(bare.returncode == 0 and "NEED" not in bare.stdout
               and "MANY" not in bare.stdout,
               "bare next with only closed runs reports no next step",
               "got exit=%d stdout=%r" % (bare.returncode, bare.stdout))


def case_start_already_and_new():
    """ALREADY 不是死路：给出旧 RAW 与两条出路，且不再把旧链条甩回来。

    D2 的诉求：同名 feature 二次提交时，不能被旧运行拽回去。
    """
    with TestRoot("dw-already-") as r:
        r.git_init()
        r.make_config('verify: "true"\n')
        first = r.run("start", "bugfix", FEATURE, "第一件事")
        expect(first.returncode == 0, "first start succeeds",
               first.stdout + first.stderr)

        again = r.run("start", "bugfix", FEATURE, "第二件事")
        expect(again.returncode == 0,
               "start on an open run is not a failure",
               "got exit=%d stdout=%r" % (again.returncode, again.stdout))
        expect("ALREADY %s working" % FEATURE in again.stdout,
               "ALREADY names the feature and its status", again.stdout)
        expect("第一件事" in again.stdout,
               "ALREADY echoes the old run's RAW request", again.stdout)
        expect("next %s" % FEATURE in again.stdout,
               "ALREADY offers 'continue this run'", again.stdout)
        expect("--new" in again.stdout,
               "ALREADY offers 'open a new run'", again.stdout)
        for needle in ("STAGE 2", "NEED specs/%s/impact.md" % FEATURE):
            expect(needle not in again.stdout,
                   "ALREADY does not drag the caller into the old chain (%r)" % needle,
                   "forbidden %r in stdout=%r" % (needle, again.stdout))
        expect("RAW 第二件事" not in again.stdout,
               "ALREADY does not pretend the new request was started",
               again.stdout)
        expect(r.read_run().get("raw_request") == "第一件事",
               "ALREADY leaves the old run untouched",
               "got raw_request=%r want '第一件事'"
               % r.read_run().get("raw_request"))

        # --new 递增后缀，绝不覆盖旧的
        second = r.run("start", "bugfix", FEATURE, "第二件事", "--new")
        expect("NEW %s-2 (from %s)" % (FEATURE, FEATURE) in second.stdout,
               "--new opens <feature>-2 and says where it came from",
               second.stdout)
        expect(os.path.isfile(r.run_path("%s-2" % FEATURE)),
               "--new creates specs/<feature>-2/run.json",
               "missing %s" % r.run_path("%s-2" % FEATURE))
        expect(r.read_run("%s-2" % FEATURE).get("stage") == 1,
               "the new run starts at stage 1",
               "got stage=%r" % r.read_run("%s-2" % FEATURE).get("stage"))

        third = r.run("start", "bugfix", FEATURE, "第三件事", "--new")
        expect("NEW %s-3" % FEATURE in third.stdout,
               "--new never reuses an occupied suffix", third.stdout)
        expect(r.read_run().get("raw_request") == "第一件事"
               and r.read_run("%s-2" % FEATURE).get("raw_request") == "第二件事"
               and r.read_run("%s-3" % FEATURE).get("raw_request") == "第三件事",
               "--new never overwrites earlier runs",
               "raw_requests=%r" % [r.read_run(n).get("raw_request")
                                    for n in (FEATURE, "%s-2" % FEATURE,
                                              "%s-3" % FEATURE)])


def case_start_new_argument_position():
    """--new 前置 / 后置都认，且不破坏 raw_request 的参数元数。"""
    with TestRoot("dw-newpos-") as r:
        r.git_init()
        r.make_config('verify: "true"\n')

        front = r.run("start", "change", "pre", "--new", "原话前置")
        expect(front.returncode == 0
               and r.read_run("pre").get("raw_request") == "原话前置",
               "--new before the raw request keeps the argument count",
               "got exit=%d stdout=%r raw=%r"
               % (front.returncode, front.stdout,
                  r.read_run("pre").get("raw_request")
                  if os.path.isfile(r.run_path("pre")) else None))

        back = r.run("start", "change", "post", "原话后置", "--new")
        expect(back.returncode == 0
               and r.read_run("post").get("raw_request") == "原话后置",
               "--new after the raw request keeps the argument count",
               "got exit=%d stdout=%r raw=%r"
               % (back.returncode, back.stdout,
                  r.read_run("post").get("raw_request")
                  if os.path.isfile(r.run_path("post")) else None))


def case_start_new_on_finished_run():
    """已结束（closed/done/abandoned）的运行上 --new 是 no-op：正常开同名，不生成 -2。"""
    for status in ("closed", "done", "abandoned"):
        label = "start --new on a %s run" % status
        with TestRoot("dw-newfinished-") as r:
            r.git_init()
            r.make_config('verify: "true"\n')
            r.run("start", "change", FEATURE, "旧的")
            path = r.run_path()
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            data["status"] = status
            if status == "closed":
                data["outcome"] = "fixed"
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False, indent=2)

            proc = r.run("start", "change", FEATURE, "新的", "--new")
            expect(proc.returncode == 0 and "NEW" not in proc.stdout,
                   label + " does not invent a suffix",
                   "got exit=%d stdout=%r" % (proc.returncode, proc.stdout))
            expect(r.read_run().get("raw_request") == "新的"
                   and r.read_run().get("status") == "working"
                   and r.read_run().get("stage") == 1,
                   label + " reopens the same name from stage 1",
                   "got=%s" % json.dumps(r.read_run(), ensure_ascii=False))
            expect(not os.path.exists(r.run_path("%s-2" % FEATURE)),
                   label + " creates no -2 run",
                   "unexpected %s" % r.run_path("%s-2" % FEATURE))


def case_close_advertised_to_ai():
    """AI 是执行方：出口必须出现在它唯一会读的地方（next 的输出）。

    AGENTS.md：runner 打印的 READ 指向 stage SKILL.md，AI 跟着 READ 走，
    永远不会主动读 JSON 里的提示字段。close_if 只存在于 JSON -> 只有
    print_stage_hints 转发，AI 才知道「这一步可以不继续」。
    """
    with TestRoot("dw-closehint-") as r:
        r.git_init()
        r.make_config('verify: "true"\n')
        r.run("start", "bugfix", FEATURE, "状态卡住")
        text = r.run("next", FEATURE).stdout
        expect("CLOSE_IF:" in text,
               "next advertises the close_if exit", text)
        expect("artifact=specs/<feature>/spec.md" in text
               and "literal=" in text and "outcome=fixed" in text,
               "the advertisement names artifact, literals and outcome", text)
        expect("fingerprint:" in text,
               "the advertisement shows the fingerprint command", text)
        expect("exit 0 表示「bug 仍然复现」" in text,
               "the advertisement states the inverted polarity", text)


def case_close_hint_survives_no_hints():
    """NO_HINTS=1 只摘 SELF_CHECK：CLOSE_IF 是门不是提示，不许被一起摘掉。

    摘掉的后果是「出口看不见」-> AI 继续推已修好的 bug，正是这次要修的缺陷。
    """
    with TestRoot("dw-closehint2-") as r:
        r.git_init()
        r.make_config('verify: "true"\n')
        r.run("start", "bugfix", FEATURE, "状态卡住")
        on = r.run("next", FEATURE).stdout
        env = r.env()
        env["DATA_WORKFLOW_NO_HINTS"] = "1"
        off = subprocess.run(
            [PY, RUNNER, "next", FEATURE, "--repo", r.path],
            capture_output=True, text=True, encoding="utf-8", env=env,
        ).stdout
        expect("CLOSE_IF:" in on, "precondition: CLOSE_IF printed by default", on)
        expect("CLOSE_IF:" in off,
               "NO_HINTS=1 must not strip the close exit",
               "CLOSE_IF missing from NO_HINTS output=%r" % off)
        stripped = "\n".join(
            line for line in on.splitlines()
            if not line.startswith("SELF_CHECK")
        ) + "\n"
        expect(stripped == off,
               "NO_HINTS=1 strips SELF_CHECK and nothing else",
               "--on(two-line-diff)--\n%r\n--off--\n%r" % (stripped, off))


def case_close_evidence_outcome():
    """关单证据行：outcome 追加在末尾，其余列与推进行同构；非关单行不受影响。"""
    with TestRoot("dw-closeevid-") as r:
        r.git_init()
        r.make_config('verify: "true"\n')
        def to_wontfix(data):
            spec = data["stages"][0]["close_if"]
            spec["outcome"] = "wontfix"
            spec["fingerprint"] = "exit 1"  # 不复现 = 可以关

        run_copy, _ = r.skill_copy("bugfix", to_wontfix)
        run_copy("start", "bugfix", FEATURE, "不修")
        r.write_spec_fixed()
        closed = run_copy("close", FEATURE)
        expect(closed.returncode == 0, "precondition: close succeeds",
               closed.stdout + closed.stderr)
        expect(r.read_run().get("outcome") == "wontfix",
               "a custom outcome reaches run.json verbatim",
               "got outcome=%r want 'wontfix'" % r.read_run().get("outcome"))

        text = r.evidence_text()
        rows = [line for line in text.splitlines() if line.strip()]
        expect(len(rows) == 1,
               "close writes exactly one evidence row",
               "got %d rows: %r" % (len(rows), rows))
        row = rows[0]
        expect(row.endswith("outcome=wontfix"),
               "the close row records the outcome at the end",
               "got row=%r want suffix 'outcome=wontfix'" % row)
        for label in ("stage=1", "requires=ok", "gate_check=", "verify=",
                      "head=", "at=", "by=runner"):
            expect(label in row,
                   "the close row keeps the %r column" % label,
                   "missing %r in row=%r" % (label, row))
        expect(row.index("by=runner") < row.index("outcome="),
               "outcome is appended after by=runner, not inserted before it",
               "got row=%r" % row)

        # 幂等：再关一次不写第二行
        again = run_copy("close", FEATURE)
        expect(again.returncode == 0
               and len([l for l in r.evidence_text().splitlines() if l.strip()]) == 1,
               "closing twice writes no second evidence row",
               "got exit=%d rows=%r" % (again.returncode, r.evidence_text()))


def case_gate_priority_on_code_stage():
    """code 阶段：待拍板优先于 DO，且 requires 门在 code 分支之前生效。"""
    with TestRoot("dw-codepriority-") as r:
        r.git_init()
        r.make_config('verify: "true"\n')

        def add_code_artifacts(data):
            stage = data["stages"][1]
            stage["artifacts"] = ["specs/<feature>/code.md"]
            stage["requires"] = ["改了什么"]

        run_copy, _ = r.skill_copy("change", add_code_artifacts)
        run_copy("start", "change", FEATURE, "改一处")
        r.write_decision()
        run_copy("done", FEATURE)
        expect(r.read_run().get("stage") == 2,
               "precondition: reached the code stage",
               json.dumps(r.read_run(), ensure_ascii=False))

        # 待拍板 -> OPEN，不能同时打 DO
        r.write("specs/%s/code.md" % FEATURE, "待拍板：要不要兼容旧数据\n改了什么: a.go\n")
        opened = run_copy("next", FEATURE)
        expect("OPEN" in opened.stdout and "DO" not in opened.stdout,
               "an open decision on a code stage blocks DO",
               "got stdout=%r" % opened.stdout)

        # 已拍板 + 字面量齐 -> DO
        r.write("specs/%s/code.md" % FEATURE,
                "待拍板：要不要兼容旧数据\n已拍板：兼容\n改了什么: a.go\n")
        passed = run_copy("next", FEATURE)
        expect("DO" in passed.stdout and "OPEN" not in passed.stdout
               and "GATE" not in passed.stdout,
               "a decided, literal-satisfied code stage reaches DO",
               "got stdout=%r" % passed.stdout)


def case_close_glob_artifact():
    """close_if.artifact 写成 specs/<feature>/*.md 时，字面量可以分散在多个文件。

    实测行为（不在文档里，但确实可达）：artifact_paths 先接受 specs/ 前缀，
    再走 concrete_files 的 glob 展开，所以字面量是「任意匹配文件里任一条满足」。
    这意味着关单依赖的文件集不是单一文件——这里把它钉住，变了就会被看到。
    """
    with TestRoot("dw-closeglob-") as r:
        r.git_init()
        r.make_config('verify: "true"\n')

        def to_glob(data):
            data["stages"][0]["close_if"]["artifact"] = "specs/<feature>/*.md"
            data["stages"][0]["close_if"]["fingerprint"] = "exit 1"

        run_copy, _ = r.skill_copy("bugfix", to_glob)
        run_copy("start", "bugfix", FEATURE, "状态卡住")

        # 字面量分散在两个文件里：合并后满足
        r.write("specs/%s/spec.md" % FEATURE, "- 已修复\n")
        r.write("specs/%s/notes.md" % FEATURE, "- 验证命令: go test\n- 退出码: 0\n")
        closed = run_copy("close", FEATURE)
        expect(closed.returncode == 0
               and r.read_run().get("status") == "closed",
               "a glob artifact unions literals across matching files",
               "got exit=%d stdout=%r run=%s"
               % (closed.returncode, closed.stdout,
                  json.dumps(r.read_run(), ensure_ascii=False)))


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
    case_commands_path_is_resolvable()
    case_default_install_commands_land_in_project()
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
    case_description_is_a_trigger()
    case_stages_have_failure_modes()
    case_open_marker()
    case_evidence_first()
    case_card_writeback()
    case_knowledge_feedback()
    case_gate_edit_coverage()
    case_self_check_not_a_gate()
    case_confess_never_gates()
    case_no_hints_switch()
    case_confess_scope_follows_workflow()
    case_honesty_stats_runs()
    case_g7_gate_runs()
    case_lazy_load()
    case_evals_are_runnable()
    case_foreign()
    case_default_no_hooks()
    case_record_follows_install()
    case_close_exit()
    case_close_refuses_literal_only()
    case_close_fingerprint_polarity()
    case_start_new()
    case_closed_stops_notice()
    case_gates_reach_code_stage()
    case_evidence_outcome_column()
    case_close_if_spec_table()
    case_close_judgement_table()
    case_close_run_absent()
    case_close_on_stage_without_exit()
    case_close_glob_artifact()
    case_closed_is_terminal()
    case_bare_next_skips_closed()
    case_start_already_and_new()
    case_start_new_argument_position()
    case_start_new_on_finished_run()
    case_close_advertised_to_ai()
    case_close_hint_survives_no_hints()
    case_close_evidence_outcome()
    case_gate_priority_on_code_stage()
    print("OK")


if __name__ == "__main__":
    main()
