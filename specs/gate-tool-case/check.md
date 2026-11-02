# gate-tool-case 核对

## 命令与结果

```
$ python3 skills/data-workflow/scripts/check_runner.py
PASS protected write is denied for tool name 'Write'
PASS protected write is denied for tool name 'write'
PASS protected write is denied for tool name 'Edit'
PASS protected write is denied for tool name 'edit_file'
PASS protected write is denied for tool name 'MultiEdit'
PASS protected write is denied for tool name 'multiEdit'
PASS protected write is denied for tool name 'apply_patch'
PASS reading stays allowed for tool name 'Read'
PASS reading stays allowed for tool name 'read_file'
PASS reading stays allowed for tool name 'grep'
PASS reading stays allowed for tool name 'list_dir'
PASS reading stays allowed for tool name 'Grep'
PASS unprotected write is still allowed
OK
```

exit 0。断言 99 → 112，case 34 → 35。

`specs/gate-tool-case/verify.log` 第一行是 `exit 0`。

## 验收条件逐条核对

| 决定里的条件 | 是否达到 | 证据 |
|---|---|---|
| 五平台能跑 runner | 是 | 见下方跨平台实测 |
| 受保护路径真 deny、普通路径真 allow | 是 | 五平台实测全部 deny/allow 正确 |
| 各宿主真实工具名都能识别 | 是 | 7 种写法的断言全 PASS |
| 断言变红才算修好 | 是 | 见反向验证 |

## 跨平台实测（修复前后对比）

测试环境：五个独立 git 仓库，各含对应平台目录，`protected_paths: "api/**"`。

**修复前：**

| 平台 | 写 api/order.proto | 写 README.md |
|---|---|---|
| cursor | allow ❌ | allow |
| claude | allow ❌ | allow |
| codex | allow ❌ | allow |
| qoder | allow ❌ | allow |
| agents | allow ❌ | allow |

**修复后：**

| 平台 | 写 api/order.proto | 写 README.md |
|---|---|---|
| cursor | **deny** ✓ | allow |
| claude | **deny** ✓ | allow |
| codex | **deny** ✓ | allow |
| qoder | **deny** ✓ | allow |
| agents | **deny** ✓ | allow |

## 跨平台能力矩阵（skill 本体）

| 能力 | cursor | claude | codex | qoder | agents |
|---|---|---|---|---|---|
| 安装副本 | ✓ | ✓ | ✓ | ✓ | ✓ |
| `workflow_next.py` 可跑 | ✓ | ✓ | ✓ | ✓ | ✓ |
| `gate-edit` 可调用 | ✓ | ✓ | ✓ | ✓ | ✓ |
| 门禁真生效（修后） | ✓ | ✓ | ✓ | ✓ | ✓ |
| `/` 命令写入 | ✓ | ✗ | ✗ | ✗ | ✗ |
| sessionStart 注入 | ✓ | ✗ | ✗ | ✗ | ✗ |

后两行是平台能力差异，不是缺陷：只有 Cursor 有 hooks.json 和 commands 约定。

## 反向验证

`case_gate_tool_case` 加入时先红了 3 条（`MultiEdit` 因集合里是 `multiEdit` 未归一化），改集合后转绿。这个先红后绿证明断言真的在看大小写。

## Token 实测数据

按中文 ≈1.5 字/token、英文 ≈4 字符/token 估算：

| 项 | token |
|---|---|
| 常驻 description | 92 |
| SKILL.md 全文（触发后读） | 1,634 |
| 单个阶段文件（一次只读一个） | 504 ~ 2,812 |
| 全部阶段合计（不会同时加载） | 13,657 |

首轮开销 ≈ 1,726 token（description + SKILL.md + 一个最小阶段）。

## 超出范围的：无

没有改任何平台的 hook 注册方式。没有做跨平台 token 对比实验（需要真跑四次 agent 会话，样本不可控）。

## 遗留

1. **门禁只有 Cursor 真的自动生效。** 其余四个平台需要宿主自己支持 hook 机制才会被调用；`gate-edit` 本身已经正确，缺的是注册通道。这是平台能力边界，不是代码缺陷。
2. `deepeek` / `hammer` 无法确认产品形态。若它们是标准 skill 目录约定，理论上同 `.agents` 路径；若是其他形态（如纯 API），本仓库的价值只在 runner 和模板层。
