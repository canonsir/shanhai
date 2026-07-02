# ShanHai Frontend Guideline（前端实现铁律）

> 适用范围：`apps/console` 及未来所有前端入口（Web Console / AI Research Workspace /
> Admin / Mobile / Dashboard）。本文件为强约束，不是建议。任何 AI（Claude / GPT /
> Trae worker）与协作者做前端实现前必须先读本文件与
> [design-system/README.md](../design-system/README.md)。

## 0. 唯一设计来源

所有前端实现的设计来源是 **ShanHai Design System**：

- **Token 事实来源（跨平台）**：[`design-system/tokens/`](../design-system/tokens)
  —— `shanhai-tokens.css`（运行时 `@import`）+ `colors.json` / `typography.json` /
  `spacing.json`（构建链消费）。任何平台取色 / 字体 / 圆角 / 间距都从这里来。
- 设计语言与组件规范：[`design-system/shanhai-console/`](../design-system/shanhai-console)
  （Trae Design 导出物，含 `colors_and_type.css` / `css.json` / `components/` /
  `preview/` / `ui_kits/`）。
- 「产品应该长什么样」的事实来源：`design-system/shanhai-console/preview/` 与
  `ui_kits/dashboard/index.html`（相当于 Design System 的 Storybook，先看它再写页面）。

## 0.1 机械化校验（不是只靠文档）

铁律由脚本强制，不只靠自觉：

```
node tools/design-guard/check.mjs apps/console   # 或在 apps/console 内：bun run lint:design
```

命中「写死十六进制色值」或「Tailwind 调色板魔法类（如 text-red-600 / bg-blue-50）」
即非零退出。新页面 / 改动提交前必须本地跑通；AI coding 同样受此约束，
不得用调色板魔法类绕过语义 token。

## 1. 必须遵守

1. **颜色 / 字体 / 圆角 / 间距 / 阴影一律走 token**，不得在组件里写死十六进制色值或
   magic number。token 的事实来源是 [`design-system/tokens/`](../design-system/tokens)
   （`shanhai-tokens.css` + `*.json`），语义变量如 `--primary` / `--background` /
   `--border` / `--destructive` / `--warning` / `--radius` / `--spacing`。导出物
   `design-system/shanhai-console/colors_and_type.css` 与之同源。
2. **不得随意引入新的 UI library**。技术栈固定为 `Next.js + Tailwind + shadcn/ui +
   Radix + Lucide`。新增任何 UI 依赖需经 Review。
3. **不得创建未登记组件**。组件必须先在 Design System 登记
   （`design-system/shanhai-console/components/index.json`）再落地实现。
4. **领域组件优先**。ShanHai 的领域组件（如 CompanyCard / FactTimeline / SourceBadge /
   ConfidenceTag / EntityGraph）是产品语言，不是 shadcn 默认组件；它们承载知识模型语义，
   应优先于裸 HTML/shadcn 拼装。

## 1.2 动画（统一用 framer-motion）

动画是产品语言的一部分，同样不允许各自为政。

- **唯一指定动画库是 [`framer-motion`](https://www.framer.com/motion/)**（已装入
  `apps/console`）。进出场、布局过渡、列表 stagger、手势反馈等“结构性动画”用它，
  **不得再引入其它动画库**（GSAP / react-spring / anime.js …）。
- **允许手搓的边界**：仅允许用 Tailwind 的 `transition-*` / `duration-*` / `ease-*`
  做 hover/focus/press 等简单微交互（如 `transition-colors duration-150 ease-out`）。
  禁止在业务代码里写自定义 `transition-duration: 173ms` 这类魔法值，禁止零散 CSS
  keyframes（需要 keyframes/复杂曲线/编排时用 framer-motion）。
- **何时用**：用动画服务「信息可读性 / 操作反馈」，而非炫技——典型场景：路由/区块进
  出场淡入、列表项 stagger、Timeline 事件渐显、抽屉/弹层滑入、加载骨架→内容的平滑切换、
  hover/press 的轻微缩放反馈。
- **与 ShanHai 调性一致**：本产品是冷静、border-led 的研究控制台，动画要克制——
  - 时长短（入场 0.15–0.25s，微交互 ≤0.15s），缓动用 `ease-out` 系；
  - 位移小（≤8px）、缩放轻（0.98–1.0）；不做夸张弹跳 / 大幅位移 / 持续循环动画；
  - **颜色仍走 token**，动画只动 opacity / transform / layout，不要在 motion 里写死
    十六进制色值（仍受 `tools/design-guard` 约束）。
  - 尊重无障碍：对大面积运动尊重 `prefers-reduced-motion`（用 framer-motion 的
    `useReducedMotion` 降级为无位移）。
- **放哪**：动画封装进领域组件 / `components/ui` 内部，页面层不散落一次性动画代码；
  可复用的进出场 variants 集中维护，便于全站一致。
- 动画相关组件需 `"use client"`（framer-motion 是客户端运行时）。

## 2. 架构关系（shadcn 是基础设施，ShanHai DS 是产品语言）

```
                 ShanHai Design System   ← 产品语言（token + 领域组件，本 guideline 约束）
                         |
          +--------------+--------------+
          |                             |
     Design Token                 Domain Components
          |                             |
     Tailwind Config              React Components
          |
     shadcn/ui primitives          ← 基础设施
          |
        Radix
```

shadcn/ui / Radix / Lucide 只是底层 primitives，不定义产品外观；产品外观由 ShanHai
Design System 的 token 与领域组件定义。

## 3. 新组件流程（强制）

```
Design System
      |  在 design-system/shanhai-console/components/ 登记规范 + preview
      ↓
Component Proposal
      |  说明：领域语义 / 用到的 token / 与现有组件的关系
      ↓
Implementation
      |  在 apps/<app>/ 用 shadcn/Radix primitives + token 实现
      ↓
Review
      |  核对 token 一致性、是否复用而非新造、是否登记
      ↓
落地
```

任何「先写页面、组件随手造」的顺序都不允许。

## 3.1 应用外壳与平台原语（Console Platform Layer，已落地）

除 token 与领域组件外，`apps/console` 已沉淀一层**应用外壳 / 平台原语**，是所有
console 页面共享的骨架。后续页面只在内容区开发，不得各自重造外壳、导航或主题逻辑。

- **AppShell**（[`components/shell/app-shell.tsx`](../apps/console/src/components/shell/app-shell.tsx)）
  —— 全视口骨架：可折叠侧栏 + Topbar + 单一全高滚动内容区。结构对齐
  `design-system/shanhai-console/ui_kits/dashboard`，映射到公司研究域（无 chat/agent UI）。
  - **Sidebar**（[`components/shell/sidebar.tsx`](../apps/console/src/components/shell/sidebar.tsx)）：
    品牌槽 + 全局搜索（⌘K）+ 主导航 + 最近查看 + footer。折叠时收成最小宽度
    **图标栏（icon rail，56px）而非完全隐藏**（参考 Manus 布局），始终保留入口可见。
  - **Topbar**（[`components/shell/topbar.tsx`](../apps/console/src/components/shell/topbar.tsx)）：
    折叠开关 + 标题/副标题（由路由派生）+ 主题切换。
  - **ContentLayout**：内容区统一 `mx-auto max-w-5xl px-6 py-8`，页面不自带外边距框架。
- **Navigation 单一事实来源**（[`lib/nav.ts`](../apps/console/src/lib/nav.ts)）：路由 + 导航
  清单集中在 `NAV` 一处定义，Sidebar 与 Topbar 标题都从它派生。**新增路由 = 追加一条
  entry**（含 `href` / `match` / `title` / `sub` / `soon`），禁止在 Sidebar 或 Topbar 里
  散落硬编码路由判断。
- **Theme（light first / dark explicit）**（[`lib/theme.ts`](../apps/console/src/lib/theme.ts)）：
  - **默认浅色**；仅当 localStorage 显式存 `dark` 才进暗色，**不跟随系统**
    `prefers-color-scheme`。
  - 主题通过 `<html>` 上的 `.dark` class 切换（与 `design-system/tokens` 的 `.dark` 对齐）。
  - 无闪烁：`layout.tsx` 在 `<head>` 内联 render-blocking bootstrap script，paint 前
    应用 class（next-themes/shadcn 标准 no-flash 写法）。
- **品牌资产**：动态 logo `public/logo.svg`（animated，平台页面展示），静态
  `public/logo.png`（favicon / app icon，挂在 `layout.tsx` 的 `metadata.icons`）。品牌色
  为独立资产，存于 `public/` 原始文件，不进 token 体系也不受 design-guard 扫描。

## 3.2 design-guard（机械化铁律执行器）

[`tools/design-guard/check.mjs`](../tools/design-guard/check.mjs) 扫描 `apps/` 源码
（`.ts/.tsx/.jsx/.js/.css`），命中写死十六进制色值或 Tailwind 调色板魔法类即非零退出，
可接 CI / pre-commit。豁免 `design-system/**` 与 `globals.css`（token 定义入口）。提交前
必须本地跑通；AI coding 同样受约束，不得绕过语义 token。

## 4. Token 收敛（已完成，Review 批准）

Token 已抽象到 [`design-system/tokens/`](../design-system/tokens)（跨平台事实来源），
`apps/console` 已 **`@import` `design-system/tokens/shanhai-tokens.css`**，统一到设计
系统色值：

| token        | 全平台统一值（design-system/tokens）        |
| ------------ | ------------------------------------------ |
| `--primary`  | `#0065fd`（蓝）                             |
| `--radius`   | `1.2rem`                                    |
| 字体 sans    | `Stack Sans Text`                           |
| 字体 mono    | `JetBrains Mono`                            |
| 暗色主题     | 提供 `.dark`（祖先加 `.dark` class 激活）   |

console 的 [`globals.css`](../apps/console/src/app/globals.css) 不再维护本地色值，只做
两件事：① `@import` 共享 token；② 把语义变量映射进 Tailwind `@theme`（生成
`text-primary` / `bg-card` / `text-destructive` 等工具类）。约束：

- 业务代码只引用语义变量名（`--primary` / `--destructive` / `--warning` / `--radius`
  …），**禁止写死十六进制色值或 Tailwind 调色板魔法类**（`text-red-600` 等），由
  `tools/design-guard` 强制。
- 不得在 `apps/console` 反向覆盖共享 token 值；如需调整色值，改
  `design-system/tokens/` 这一处事实来源，全平台同步。
- console 本地只允许从共享 token **派生别名**（如 `--pill: var(--secondary)`），不得
  引入新的色值。

## 5. 当前阶段不做（M3 Design System Foundation）

- ❌ 把 `components/*.json` 全部转换成 React 组件
- ❌ 把 `colors_and_type.css` 全塞进 Tailwind config
- ❌ 重构 shadcn/ui
- ❌ 搭独立 Storybook

理由：当前里程碑目标是用真实页面验证知识模型，不是建设前端基础设施。本阶段只做
「Design System 入库 → Token 抽象到 `design-system/tokens/` → 机械化校验接入 →
Console 开发引用 → 真实页面验证」。token 色值收敛已完成（console 已统一 `@import`
共享 token）；领域组件 React 化、JSON→CSS 自动生成脚本（Style Dictionary）待后续里程碑
经 Review 排期。
