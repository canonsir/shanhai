-- ShanHai 运行记录表（见 ADR 0008）
-- 由 PostgresRunStore.init_schema() 幂等建表，亦可随容器初始化执行。
-- 数据模型：agent_runs（运行汇总）+ agent_steps（逐步 think/act/observe 记录）。

CREATE TABLE IF NOT EXISTS agent_runs (
    id          UUID PRIMARY KEY,
    agent       TEXT NOT NULL,
    status      TEXT NOT NULL,
    output      JSONB,
    error       TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS agent_steps (
    id           BIGSERIAL PRIMARY KEY,
    run_id       UUID NOT NULL REFERENCES agent_runs(id) ON DELETE CASCADE,
    step_index   INTEGER NOT NULL,
    type         TEXT NOT NULL,
    content      TEXT,
    tool         TEXT,
    tool_args    JSONB,
    tool_result  JSONB
);

CREATE INDEX IF NOT EXISTS idx_agent_runs_agent ON agent_runs (agent, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_steps_run ON agent_steps (run_id, step_index);
