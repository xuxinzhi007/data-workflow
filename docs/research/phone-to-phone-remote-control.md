# 调研：一台手机操作另一台手机，能不能做？市面上有哪些产品？

> 调研时间 2026-02。来源全部是官方文档 / 官方仓库，营销页只用来确认产品是否存在，不当作技术事实。

## 结论先说

**能做，四条路都成立，但每条的代价差得很远。选哪条取决于两件事：被控机是 Android 还是 iPhone，以及你接不接受“被控机装 App 并授权”。**

| 方案 | 被控机 Android | 被控机 iPhone | 需要被控机装东西 | 需要电脑吗 |
|---|---|---|---|---|
| A. 主控机跑 ADB + scrcpy | ✅ 完整可控 | ❌ | 否（scrcpy 用完不留东西） | 否，但要能跑 ADB，见 A 的坑 |
| B. 被控机装 App（无障碍 / 投屏授权） | ✅ | ✅ 有限，走 ReplayKit 投屏 + 无法真注入 | 是 | 否 |
| C. 云控 / MDM 平台 | ✅ | ✅ 企业场景 | 是 | 否 |
| D. 厂商自带互控（华为/小米/苹果生态） | 仅同生态 | 仅同生态 | — | 否 |

---

## A. 主控机跑 ADB + scrcpy（Android → Android，最好用的一条）

**已证实**（scrcpy 官方 README，v5.0.1，<https://github.com/Genymobile/scrcpy>）：

- 定位就是“把 Android 设备画面投到电脑上，并用键盘鼠标操作它”。走 USB 或 TCP/IP。
- **不需要 root，不需要在被控设备上安装任何 App**（原文：*It does not require root access or an app installed on the device*）。
- 延迟 35~70ms，30~120fps，启动约 1 秒。
- 支持：音频转发（Android 11+）、录屏、虚拟显示、被控机熄屏仍投屏、双向剪贴板、摄像头投屏、键鼠 HID 模拟、手柄、OTG 模式。

**无线是官方支持的**（`doc/connection.md`）：`scrcpy --tcpip=192.168.1.1:5555`，前提是该设备已在 TCP/IP 上监听。Android 11+ 的官方配对方式见 ADB 文档（<https://developer.android.com/tools/adb>）：*要配对必须用二维码或配对码，主控端和被控端要在同一个无线网络*。配对只需一次。

**OTG 模式**（`doc/otg.md`）值得单独看：它用 AOA 协议模拟物理键鼠，**完全不经过 adb，因此不需要开 USB 调试**，代价是 `--otg` 下视频和音频被禁用，只剩输入。

### 这条路的真实坑：谁来跑 ADB

上面这些以“电脑主控”为前提。你要的是**手机控手机**，那就得让主控手机跑起 ADB 客户端。这里有两个硬门槛：

1. **USB 主机角色**：手机插手机，需要主控手机支持 USB Host/OTG 供电并识别对方为 USB 设备。Android 提供了 `UsbHost` API（<https://developer.android.com/guide/topics/connectivity/usb/host>），硬件上多数中高端机支持 OTG，但“识别一个 ADB 设备”和“读 U 盘”不是一回事，需要实测。
2. **ADB 二进制**：`adb` 要在 Android 上跑。Termux 的 `android-tools` 包确实提供了 Android 版 platform-tools（构建时 `-DANDROID_TOOLS_USE_BUNDLED_LIBUSB=ON`，即自带 libusb，理论上能走 USB），版本跟随上游 37.0.0p1 —— 见 <https://github.com/termux/termux-packages/blob/master/packages/android-tools/build.sh>。但 Termux 官方 README 自己标注：**Android 12+ 上 Termux 可能不稳定**，系统会杀掉超过 32 个的 phantom 进程、以及占用 CPU 过高的进程（<https://github.com/termux/termux-app>）。长期挂着的 ADB 会话有被杀的风险。
3. 更省事的绕法：**别用 USB，用 WiFi**。主控手机在 Termux 里 `adb connect <被控机IP>:端口`，就绕开了 USB 主机这层不确定性。代价是两台机在同一局域网，且 Android 11+ 首次配对要输入配对码。**推断**：这是手机控手机最现实的一条路，但“主控手机自己当 ADB host”没有官方支持声明，属于社区做法，需要自己验证。

**小结**：技术上成立，是本清单里画质延迟最好的方案。前提是两台都是 Android，且你愿意在主控手机上装 Termux 敲命令。

---

## B. 被控机装 App：无障碍服务 / 投屏授权

这是市面上消费级远控产品的通用做法。

**已证实**：Android 的 `AccessibilityService` 官方定义就写明它的用途与限制（<https://developer.android.com/reference/android/accessibilityservice/AccessibilityService>）：*Accessibility services should only be used to assist users with disabilities in using Android devices and apps*，且**只能由用户在系统设置里显式打开**，系统独占管理其生命周期。也就是说：能读控件、能点，但①必须用户手动授权，②用途被官方限定为无障碍辅助，拿来做远控处于灰色地带（Google Play 政策上更容易被拒或下架）。

**已证实**：iPhone 端没法真注入。Apple 的 iPhone Mirroring（<https://support.apple.com/en-us/120421>）官方要求是 **macOS Sequoia 15+ 的 Mac**——iPhone 只能被 Mac 镜像操作，**苹果没有开放 iPhone 被另一台 iPhone 控制的能力**。iOS 上第三方最多做到 ReplayKit 屏幕直播（看得到），点击注入没有官方 API。

**推断**：所以任何宣称“iPhone 控 iPhone”的产品，要么走企业 MDM（被控机是企业管的、装了描述文件），要么是受限的“看画面 + 引导对方点”，不是真注入。

---

## C. 市面上的产品（按是否一手可查分级）

| 产品 | 覆盖 | 说明 | 证据强度 |
|---|---|---|---|
| **scrcpy** | Android | 开源 GBYTE，上述能力全公开，免费无广告。**最接近你需求的底座** | 一手（官方 README/文档） |
| **AirDroid / AirDroid Business / Remote Support** | Android + iOS | 官方站点存在 Remote Access(View & Control)、Remote Support、MDM、Kiosk 等产品线 | 一手确认产品存在；具体注入机制是二手 |
| **TeamViewer（含 Tensor）** | Android + iOS | 官方有 Android 客户端与 Remote Management 产品线 | 一手确认产品存在；Android 远控需装其 Add-On 属二手 |
| **AnyDesk** | Android + iOS | 有 Android 客户端 | 仅确认存在（页面需 JS，未取到正文） |
| **华为「多屏协同」/ 小米互传等** | 同品牌生态 | 手机↔平板/PC 互控，跨品牌不通 | 二手（未查官方文档） |
| **Apple iPhone Mirroring** | iPhone → Mac | 官方明确只支持 Mac，不支持 iPhone→iPhone | 一手 |

**注意**：B/C 段里“某产品到底靠无障碍还是靠厂商签名权限注入”这类细节，我只有营销页和二手信息，**未经一手证实**，别直接引。要定选型就自己装一个抓包 / 看权限清单确认。

---

## 给你的建议（按你的场景二选一）

- **两台都是 Android，想自己动手、要最好效果**：先在主控手机装 Termux，`pkg install android-tools`，走 `adb connect` + scrcpy 的 WiFi 路线。注意 Android 12+ 的进程回收，别指望 24 小时常驻。要做成产品，就把这套包进自己的 App，用 `UsbHost` API 或 WiFi ADB。
- **要现成能用、不折腾**：AirDroid 或 TeamViewer，接受被控机装 App + 手动开权限。iPhone 被控基本只有企业 MDM 一条路。

## 待确认（我没查实、别当事实用）

1. 主控手机当 USB Host 直连另一台手机跑 adb，在主流机型上的成功率——需实测。
2. AirDroid / TeamViewer 在 Android 上具体用哪个权限通道注入输入。
3. 跨品牌厂商互控（华为↔小米）是否有官方支持。
4. iPhone→iPhone 除 MDM 外是否真有可用的第三方方案。
