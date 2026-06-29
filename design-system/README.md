# ShanHai Design System

ShanHai 的**第一层产品资产**：跨所有前端入口（Web Console / AI Research Workspace /
Admin / Mobile / Dashboard）共享的设计语言，而非某个页面的附件。因此它独立于
`apps/`，作为顶层 `design-system/` 存在。

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
└── tokens/                    # Design Token 规范化抽象（占位；JSON 化待 Review 排期）
    └── README.md              # colors.json / typography.json / spacing.json 规划
```

> **导入来源说明**：`shanhai-console/` 为 Trae Design 导出物，原始品牌标记为
> "Doubao"（Trae Design 默认模板），其 token 值（primary `#0065fd`、radius `1.2rem`、
> 字体 `Stack Sans Text / Source Serif 4 / JetBrains Mono`）与现有
> `apps/console` 的 token（primary `#2c3e50`、radius `0.5rem`、系统字体）**尚未对齐**。
> 二者的收敛（以哪套 token 为准、是否改名 ShanHai）是一个待决项，列入
> [docs/frontend-guideline.md](../docs/frontend-guideline.md) 的「已知差异」，本阶段
> 不修改 `apps/console` 代码。

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
