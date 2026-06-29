# Design Tokens（规范化抽象，占位）

本目录是 ShanHai Design System 的 **Design Token 规范化层**：把
`../shanhai-console/colors_and_type.css` / `css.json` 里的原始 token 抽象为
工具无关、可被多个 app 与构建链消费的结构化 JSON。

## 规划产物（尚未落地）

```
tokens/
├── colors.json       # 语义颜色：primary / background / foreground / border / chart-* / sidebar-* …
├── typography.json   # 字体族 / 字号 / 行高 / 字重 / tracking
└── spacing.json      # 间距单位 / 圆角（radius）/ 阴影
```

## 为什么现在只放占位

当前阶段（M3 Design System Foundation）只做「Design System 入库 → Console 开发引用
→ 真实页面验证」，**不提前抽象**。JSON 化（含 Style Dictionary / Tailwind 生成链）
待 token 在真实页面验证收敛、且 `shanhai-console` 与 `apps/console` 的 token 差异
（见 [docs/frontend-guideline.md](../../docs/frontend-guideline.md) 的「已知差异」）
对齐后，经 Review 排期再做。

在此之前，唯一事实来源是 `../shanhai-console/colors_and_type.css`。
