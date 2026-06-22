-- ShanHai Phase 0 数据库初始化
-- 由 postgres 容器在首次启动时自动执行（docker-entrypoint-initdb.d）。

-- 启用 pgvector，用于后续 Embedding / Vector Memory。
CREATE EXTENSION IF NOT EXISTS vector;

-- Phase 0 仅占位：验证扩展可用。
-- Wiki Entity / Relation 表结构将在知识层落地阶段，由 wiki-engine Schema 驱动生成。
