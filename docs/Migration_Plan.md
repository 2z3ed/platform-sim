# Migration Plan

## 1. 文档目的

本文档定义 official-sim-server 的数据库迁移顺序、每轮 migration 的目标、回滚规则、验证规则与 seed 顺序。

本文件是 Codex 编写 Alembic migration 时的直接依据。

---

## 2. 设计原则

### 2.1 先"可运行、可回放、可审计"，后"业务全量"
迁移顺序必须优先保证以下能力：

1. run 可创建
2. step 可推进
3. snapshot 可记录
4. artifact 可存储
5. push event 可回放
6. report 可生成

因此，第一批核心表先于业务真相表落库。

### 2.2 先稳定主键与外键，再补 JSONB 索引
P0 阶段先保证：
- 主外键
- 唯一键
- 基础查询索引

GIN / JSONB 深度索引可以放到第二轮。

### 2.3 migration 必须可回滚
每个 migration 都必须有 downgrade。

### 2.4 migration 脚本不能依赖真实外部网络
所有 migration 必须只依赖：
- 本地 schema
- 本地 metadata
- 本地已知常量

---

## 3. 推荐迁移编号

推荐采用以下编号顺序：

- `0001_init_extensions`
- `0002_platform_accounts`
- `0003_scenario_templates`
- `0004_simulation_runs`
- `0005_simulation_events`
- `0006_state_snapshots`
- `0007_push_events`
- `0008_artifacts`
- `0009_evaluation_reports`
- `0010_sim_orders`
- `0011_sim_order_items`
- `0012_sim_shipments`
- `0013_sim_shipment_nodes`
- `0014_sim_after_sales`
- `0015_sim_conversations`
- `0016_sim_messages`
- `0017_jsonb_indexes`
- `0018_constraints_and_checks`

---

## 4. 分阶段迁移说明

### 4.1 0001_init_extensions
目标：
- 初始化 PostgreSQL 扩展
- 为后续 uuid、jsonb、索引能力做准备

建议内容：
- `pgcrypto` 或等价 UUID 方案
- 若项目已有统一规范，则遵从现有规范

验收：
- extension 存在
- migration up/down 成功

---

### 4.2 0002_platform_accounts
目标：
- 建立被模拟的平台主体/租户表

字段最少包括：
- id
- platform
- account_code
- shop_id
- corp_id
- open_kfid
- display_name
- status
- config_json
- created_at
- updated_at

索引：
- unique(platform, account_code)
- index(platform, shop_id)

---

### 4.3 0003_scenario_templates
目标：
- 建立场景模板表

字段最少包括：
- id
- code
- name
- platform_scope
- category
- description
- initial_state_json
- default_actions_json
- enabled
- version
- created_at
- updated_at

索引：
- unique(code)
- index(platform_scope, category)

---

### 4.4 0004_simulation_runs
目标：
- 建立 run 主表

字段最少包括：
- id
- run_code
- template_id
- platform
- account_id
- status
- strict_mode
- push_enabled
- seed
- current_step
- metadata_json
- started_at
- ended_at
- created_at
- updated_at

索引：
- unique(run_code)
- index(platform, status)
- index(account_id, status)

---

### 4.5 0005_simulation_events
目标：
- 建立离散事件表

字段最少包括：
- id
- run_id
- step_no
- event_type
- source_type
- payload_json
- created_at

索引：
- index(run_id, step_no)
- index(run_id, event_type)

---

### 4.6 0006_state_snapshots
目标：
- 建立状态快照表

字段最少包括：
- id
- run_id
- step_no
- auth_state_json
- order_state_json
- shipment_state_json
- after_sale_state_json
- conversation_state_json
- push_state_json
- created_at

索引：
- unique(run_id, step_no)
- index(run_id, created_at)

---

### 4.7 0007_push_events
目标：
- 建立推送事件表

字段最少包括：
- id
- run_id
- step_no
- platform
- event_type
- status
- headers_json
- body_json
- sent_at
- acked_at
- retry_count
- created_at

索引：
- index(run_id, step_no)
- index(platform, status)
- index(event_type, status)

---

### 4.8 0008_artifacts
目标：
- 建立工件表

字段最少包括：
- id
- run_id
- step_no
- platform
- artifact_type
- route_key
- request_headers_json
- request_body_json
- response_headers_json
- response_body_json
- created_at

索引：
- index(run_id, step_no)
- index(platform, artifact_type)
- index(route_key)

---

### 4.9 0009_evaluation_reports
目标：
- 建立评估报告表

字段最少包括：
- id
- run_id
- report_version
- summary_json
- expected_json
- actual_json
- issues_json
- created_at

索引：
- unique(run_id, report_version)

---

### 4.10 0010 ~ 0016 业务真相表
目标：
- 逐步引入业务真相表，而非仅靠 snapshot JSON

建议顺序：
1. sim_orders
2. sim_order_items
3. sim_shipments
4. sim_shipment_nodes
5. sim_after_sales
6. sim_conversations
7. sim_messages

目的：
- 让状态推进不只存在于 JSON
- 支持更稳定查询
- 支持 integration / diff / replay

---

### 4.11 0017_jsonb_indexes
目标：
- 为高频 JSONB 查询补 GIN 索引

建议包括：
- simulation_runs.metadata_json
- state_snapshots.order_state_json
- state_snapshots.after_sale_state_json
- push_events.body_json
- artifacts.response_body_json

---

### 4.12 0018_constraints_and_checks
目标：
- 补关键 CHECK 约束和平台/状态约束

建议包括：
- platform 枚举约束
- run.status 约束
- push_events.status 约束
- retry_count >= 0
- acked_at >= sent_at
- 金额非负约束（在业务表已引入后补）

---

## 5. 回滚策略

### 5.1 单步回滚
每个 migration 必须支持：
- drop index
- drop constraint
- drop table
- drop extension（若允许）

### 5.2 风险较高的回滚
以下 migration 回滚前要注意数据丢失：
- 0004_simulation_runs 之后
- 0005_simulation_events 之后
- 0008_artifacts 之后
- 0010~0016 业务表之后

### 5.3 安全规则
若 migration 涉及数据转换：
- 先写 upgrade 数据复制逻辑
- downgrade 至少要保证 schema 可回退
- 若 downgrade 会损失数据，必须写清楚 warning

---

## 6. Seed 计划

### 6.1 P0 最小 seed
建议 seed：
- platform_accounts
- scenario_templates

### 6.2 初始平台主体
至少包括：
- taobao demo account
- douyin_shop demo shop
- wecom_kf demo account

### 6.3 初始场景模板
至少包括：
- taobao_wait_ship_basic
- taobao_refund_pending
- douyin_order_wait_ship
- douyin_refund_reviewing
- wecom_enter_session
- wecom_msg_send_fail

---

## 7. 验证命令要求

每个 migration 至少要经过以下验证：

1. upgrade 到最新
2. downgrade 回前一版
3. 再 upgrade 到最新
4. 表存在性检查
5. 基础索引检查
6. 最小 CRUD smoke test

---

## 8. Alembic 约定

### 8.1 revision 命名
推荐：
- `alembic revision -m "create simulation_runs"`
- `alembic revision -m "create artifacts and push_events"`

### 8.2 autogenerate 规则
允许使用 autogenerate 生成候选 migration，但必须人工检查，不可直接信任输出。

### 8.3 env.py
必须保证：
- metadata 注册完整
- 离线/在线模式可运行
- 统一数据库 URL 读取逻辑

---

## 9. P0 完成定义

migration plan 只有在以下条件全部满足时才算完成：

- 第一批核心表 migration 已存在
- migration up/down 可执行
- 至少 1 轮 seed 可执行
- migration smoke tests 通过
- README 中包含 migration 命令说明
