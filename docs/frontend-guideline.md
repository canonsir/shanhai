# ShanHai Frontend Guideline（前端实现铁律）

> 适用范围：`apps/console` 及未来所有前端入口（Web Console / AI Research Workspace /
> Admin / Mobile / Dashboard）。本文件为强约束，不是建议。任何 AI（Claude / GPT /
> Trae worker）与协作者做前端实现前必须先读本文件与
> [design-system/README.md](../design-system/README.md)。

## 0. 唯一设计来源

所有前端实现的设计来源是 **ShanHai Design System**：

- 设计语言与组件规范：[`design-system/shanhai-console/`](../design-system/shanhai-console)
  （Trae Design 导出物，含 `colors_and_type.css` / `css.json` / `components/` /
  `preview/` / `ui_kits/`）。
- 「产品应该长什么样」的事实来源：`design-system/shanhai-console/preview/` 与
  `ui_kits/dashboard/index.html`（相当于 Design System 的 Storybook，先看它再写页面）。

## 1. 必须遵守

1. **颜色 / 字体 / 圆角 / 间距 / 阴影一律走 token**，不得在组件里写死十六进制色值或
   magic number。token 的事实来源是 `design-system/shanhai-console/colors_and_type.css`
   （语义变量如 `--primary` / `--background` / `--border` / `--radius` / `--spacing`）。
2. **不得随意引入新的 UI library**。技术栈固定为 `Next.js + Tailwind + shadcn/ui +
   Radix + Lucide`。新增任何 UI 依赖需经 Review。
3. **不得创建未登记组件**。组件必须先在 Design System 登记
   （`design-system/shanhai-console/components/index.json`）再落地实现。
4. **领域组件优先**。ShanHai 的领域组件（如 CompanyCard / FactTimeline / SourceBadge /
   ConfidenceTag / EntityGraph）是产品语言，不是 shadcn 默认组件；它们承载知识模型语义，
   应优先于裸 HTML/shadcn 拼装。

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

## 4. 已知差异（待 Review 收敛，勿擅自改）

当前 `design-system/shanhai-console/`（Trae Design 导出，原始品牌标记 "Doubao"）的 token
与现有 `apps/console/src/app/globals.css` **尚未对齐**：

| token        | shanhai-console（导入）              | apps/console（现有）       |
| ------------ | ------------------------------------ | -------------------------- |
| `--primary`  | `#0065fd`（蓝）                       | `#2c3e50`（深蓝灰）        |
| `--radius`   | `1.2rem`                              | `0.5rem`                   |
| 字体 sans    | `Stack Sans Text`                     | 系统字体栈                 |
| 字体 mono    | `JetBrains Mono`                      | 系统等宽栈                 |
| 暗色主题     | 提供 `.dark`                          | 未提供                     |

**待决项**：以哪一套 token 为准、是否将导出物从 "Doubao" 改名为 ShanHai、是否引入暗色
主题。在 Review 给出结论前：

- 不得擅自把 `apps/console` 的 token 改成导入值，也不得反向改导入物。
- 新页面如需取色，引用语义变量名（如 `--primary`），不引用具体色值，便于后续统一收敛。

## 5. 当前阶段不做（M3 Design System Foundation）

- ❌ 把 `components/*.json` 全部转换成 React 组件
- ❌ 把 `colors_and_type.css` 全塞进 Tailwind config
- ❌ 重构 shadcn/ui
- ❌ 搭独立 Storybook

理由：当前里程碑目标是用真实页面验证知识模型，不是建设前端基础设施。本阶段只做
「Design System 入库 → Console 开发引用 → 真实页面验证」。规范化抽象（`design-system/tokens/`
JSON 化、领域组件 React 化、token 收敛）待后续里程碑经 Review 排期。
