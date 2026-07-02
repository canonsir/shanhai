# ShanHai Design Guard

机械化执行前端「必须走 Design System token，不得自己发挥」铁律的扫描脚本。
文档约束（[docs/frontend-guideline.md](../../docs/frontend-guideline.md)）靠自觉，本脚本靠退出码。

## 它拦什么

1. **硬编码十六进制色值**（`#fff` / `#0065fd` …）出现在业务源码里。
2. **Tailwind 调色板魔法类**（`text-red-600` / `bg-blue-50` / `border-gray-200` …）——
   这些绕过语义 token，是「AI coding 自己发挥」的典型形态。

## 它放行什么（事实来源）

- `design-system/**`：token 与 preview 本身就是定义色值的地方。
- `apps/*/src/app/globals.css`：token 定义入口（`:root` / `@theme`），允许出现色值。

## 用法

```bash
node tools/design-guard/check.mjs                # 默认扫 apps/
node tools/design-guard/check.mjs apps/console   # 指定目录
# 或在 apps/console 内：
bun run lint:design
```

命中即非零退出，逐条打印 `文件:行 [类型] 命中文本 -> 修复提示`。

## 接入建议

- 本地：提交前手动跑，或挂 pre-commit。
- CI：作为前端 lint 步骤之一，违规即 fail。

> 颜色 token 的事实来源是 [`design-system/tokens/`](../../design-system/tokens)；
> 业务代码只引用语义变量（`--primary` / `--destructive` / `--muted-foreground` …）
> 与语义 Tailwind 类（`text-foreground` / `bg-muted` …）。
