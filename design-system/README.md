# ShanHai Design System

ShanHai 的**第一层产品资产**：跨所有前端入口（Web Console / AI Research Workspace /
Admin / Mobile / Dashboard）共享的设计语言，而非某个页面的附件。因此它独立于
`apps/`，作为顶层 `design-system/` 存在。

## 定位（这是什么、不是什么）

这是 **ShanHai Intelligence Console Design Language**，不是一个通用 UI 组件库。

**Purpose** —— 为「以知识为中心的金融智能 UI」维持一致的视觉表达：实体 / 事实 /
来源 / 置信度 / 时间线等知识模型语义，在所有前端入口呈现一致。

**Not included（明确不覆盖，避免未来误解为通用组件库）**：

- ❌ generic SaaS dashboard（通用后台模板）
- ❌ marketing website（市场营销站）
- ❌ chat UI（对话式交互界面）
- ❌ trading terminal UI（交易终端）

新增能力若属于上述方向，不应往本设计系统里塞，需另立 Review 讨论边界。

## 为什么不放在 `apps/console`

如果放进 `apps/console/design/`，它就会退化为「console 自己的规范」。但 Design Token
（颜色 / 字体 / 间距 / 圆角 / 阴影）与领域组件语言（CompanyCard / FactTimeline /
SourceBadge / ConfidenceTag / EntityGraph …）应属于整个产品体系，被未来多个 app 复用。

## 目录

```
design-system/
├── README.md                  # 本文件
├── shanhai-console/           # Trae Design 导出的产品级 UI 规范（Console 设计语言）
│   ├── README.md
│   ├── SKILL.md
│   ├── colors_and_type.css    # 颜色 / 字体（→ 未来抽象为 tokens/）
│   ├── css.json
│   ├── components/            # ShanHai 领域组件（非 shadcn 默认组件）
│   ├── ui_kits/
│   ├── assets/
│   └── preview/               # Design System 的「Storybook」：产品应该长什么样
└── tokens/                    # Design Token 规范化抽象（跨平台事实来源）
    ├── README.md              # 消费方式说明
    ├── shanhai-tokens.css     # 运行时 @import 的 CSS 变量（:root + .dark）
    ├── colors.json            # 语义颜色（light / dark）
    ├── typography.json        # 字体族 / 字号 / 行高 / 字重
    └── spacing.json           # 间距 / 圆角 / 阴影
```

> **导入来源说明**：`shanhai-console/` 为 Trae Design 导出物（品牌已标记 ShanHai，
> 含 23 个组件 + preview + ui_kit）。其 token 已抽象到外层 `tokens/`，成为跨平台事实
> 来源（primary `#0065fd`、radius `1.2rem`、字体 `Stack Sans Text / Source Serif 4 /
> JetBrains Mono`，并提供 `.dark` 暗色主题）。
>
> **收敛已完成（Review 批准）**：`apps/console` 已 `@import` 本目录的
> `tokens/shanhai-tokens.css`，统一到设计系统色值（蓝 primary + 1.2rem 圆角 + 品牌
> 字体 + 暗色主题），不再维护本地一套色值。console 的 `globals.css` 只负责把共享 token
> 映射进 Tailwind `@theme`，禁止再写死十六进制色值（由 `tools/design-guard` 强制）。

## 与技术栈的关系（shadcn 是基础设施，ShanHai DS 是产品语言）

```
                 ShanHai Design System
                         |
          +--------------+--------------+
          |                             |
     Design Token                 Domain Components
          |                             |
     Tailwind Config              React Components
          |
     shadcn/ui primitives
          |
        Radix
```

- `shadcn/ui` / Radix / Lucide：底层基础设施，不与 ShanHai DS 冲突。
- ShanHai Design System：产品语言层，定义 token 与领域组件，约束所有前端实现。

## 强约束

所有 Console / Web 前端实现必须遵守 [docs/frontend-guideline.md](../docs/frontend-guideline.md)
与本目录的 `shanhai-console/` 规范（颜色 / 字体 / 组件不得自定义、未登记组件不得直接落地）。

## 当前阶段不做（M3 Design System Foundation）

- ❌ 把组件全部转换成 React
- ❌ 把 CSS 全塞进 Tailwind
- ❌ 重构 shadcn
- ❌ 搭 Storybook

本阶段只做「Design System 入库 → Console 开发引用 → 真实页面验证」。规范化抽象
（`tokens/` JSON 化、领域组件 React 化）待后续里程碑经 Review 排期。
