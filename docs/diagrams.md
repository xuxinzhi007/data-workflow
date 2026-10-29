# 图

`assets/architecture.png` 和 `assets/flow.png` 由 excalidraw-diagram 阶段生成。源是 `.staging/` 里的 spec JSON。

```bash
node skills/data-workflow/stages/excalidraw-diagram/scripts/diagram_generator.js .staging/architecture.spec.json assets architecture
node skills/data-workflow/stages/excalidraw-diagram/scripts/diagram_generator.js .staging/flow.spec.json assets flow
bash scripts/svg_to_png.sh assets/architecture.svg assets/architecture.png 2
bash scripts/svg_to_png.sh assets/flow.svg assets/flow.png 2
```

改卡片内容就改 spec，再跑这四条。`.excalidraw` 可以拖进 excalidraw.com 手改。PNG 在 git 里，不跑脚本也能看图。
