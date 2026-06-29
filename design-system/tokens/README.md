# Design Tokens（ShanHai 跨平台 token 层）

本目录是 ShanHai Design System 的 **Design Token 规范化层**：把
`../shanhai-console/colors_and_type.css` / `css.json` 里随导出物绑定的原始 token，
抽象为**工具无关、平台无关、可被多个 app 与构建链直接复用**的事实来源。

> 为什么放在 `design-system/tokens/`（外层）而不是 `shanhai-console/` 内：
> token 是整个产品体系的资产，不属于 Console 一家。Workspace / Admin / Mobile /
> Dashboard 任何前端入口都应直接复用同一套，而不是各自重抄。

## 产物（事实来源）

```
tokens/
├── shanhai-tokens.css   # ★ 跨平台直接 @import 的 CSS 变量（:root + .dark）
├── colors.json          # 语义颜色：light / dark 两套，键名 == CSS --<key>
├── typography.json      # 字体族 / 字号 / 行高 / 字重 / tracking
└── spacing.json         # 间距单位 / 圆角（radius）/ 阴影
```

- `shanhai-tokens.css` 是给**运行时**用的：任何平台 `@import` 即得全部变量。
- `*.json` 是给**构建链 / 跨语言消费**用的（Tailwind 生成、Style Dictionary、
  RN / 设计工具同步），平台无关。
- 三者同源、必须保持一致。改 token 时三处一起改（或后续由脚本从 JSON 生成 CSS）。

## 如何消费（任何平台）

CSS / Tailwind v4：

```css
@import "../../design-system/tokens/shanhai-tokens.css";
/* 之后业务代码只用语义变量，禁止写死色值 */
.btn { background: var(--primary); color: var(--primary-foreground); }
```

暗色主题：在祖先元素加 `.dark` class 即切换全部变量。

JSON（构建链）：

```js
import colors from "../../design-system/tokens/colors.json";
const primary = colors.light.primary; // "#0065fd"
```

## 与 shanhai-console 导出物的关系

- `shanhai-console/colors_and_type.css`：Trae Design 导出物，是设计工具产物。
- 本目录：从导出物抽象出的**规范化层**，是工程侧的事实来源。
- 当前两份颜色值一致；若未来导出物更新，以本目录为对齐基准，并同步导出物。

## 待 Review 收敛项

- `typography.json` 的字号 / 行高梯度：导出物未定义（Trae Design 仅导出字体族），
  当前为 ShanHai dashboard 密度的基础约定，待真实页面验证后收敛。
- JSON → CSS 的自动生成脚本（Style Dictionary / 自研）：当前手工保持一致，
  待 Review 排期后引入，消除手工同步。
