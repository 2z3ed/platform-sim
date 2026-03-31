# AGENTS.md

## 1. 项目目标

本仓库的目标不是实现真实平台接入，而是实现一个"多平台官方行为仿真层 + 客服中台统一层"。

核心价值：**在没有真实官方API和真实用户的情况下，仍能完整开发、测试、联调客服中台系统。**

### 仿真层架构

```
┌─────────────────────────────────────────────────────┐
│           完整客服中台系统（可正常开发）               │
│                                                     │
│  User Intent ──→ User Agent ──→ official-sim-server │
│     (用户输入)   (翻译成API调用)   (扮演官方平台)     │
│                          │              ↓            │
│                          │         Unified Layer    │
│                          │              ↓            │
│                          └────→ AI Orchestrator     │
│                                     ↓               │
│                                 前端/坐席工作台      │
└─────────────────────────────────────────────────────┘
              ↑ 全程不需要真实用户和真实官方API
```

**两个独立职责（不是同一个Agent的双重职责）：**

1. **User Agent（AI Orchestrator 内部模块）**：
   - 输入：用户的自然语言（"我要退款"、"查一下订单"）
   - 输出：**官方API格式的请求**（调用哪个平台、什么接口、什么参数）
   - 职责：把用户意图翻译成官方API调用

2. **official-sim-server（独立服务）**：
   - 输入：来自 User Agent 或其他系统的**官方API调用**
   - 输出：**官方级API payload**（从 fixtures 加载）
   - 职责：模拟官方平台返回真实格式的响应

当前要完成的核心工作是：

1. 新增 `official-sim-server`，用于：
   - 模拟真实用户行为触发后，平台官方 API / callback / webhook 的行为
   - 基于 fixtures 输出官方级完整字段的 payload
2. 保留现有 `/mock/...` 与 `/mock/unified/...` 契约层，作为中台、AI、前端联调接口。
3. 通过 provider 层实现 `mock -> real` 可替换，不改上层业务逻辑。
4. 以可回放、可审计、可测试、可增量扩展为第一优先级。
5. LLM 只能用于：
   - 计划生成
   - 场景编排
   - 报告生成
   - 测试说明
   - 文档整理
   不能用于定义"官方真实 payload 真相"（真相来源只能是 fixtures/state machine）。

---

## 2. 当前阶段范围（P0）

P0 只做以下内容：

- 新建 `apps/official-sim-server/`
- 实现基础 run 生命周期
- 实现数据库第一批核心表
- 实现 artifact / push event / snapshot 机制
- 实现 3 个平台 profile：
  - taobao
  - douyin_shop
  - wecom_kf
- 打通与 unified/provider 的最小接入路径
- 补齐 pytest、fixture、migration、最小 README

P0 不做：

- 全平台 100% 字段拟真
- 真实 provider 接入
- DeerFlow / DeepAgents 作为核心运行时
- 复杂 RAG
- 自动真实发送客服回复
- MQ / Kafka 重型基础设施
- 所有平台一次性全覆盖

---

## 3. 必须遵守的设计原则

### 3.1 真相来源
官方 API 返回、消息推送、错误码、状态推进，必须来自以下组合：

- **fixtures**（主要来源，官方级完整字段）
- state machine
- validators
- emitters
- repositories

**official-sim-server 必须从 fixtures/ 加载官方 payload，不得使用硬编码函数返回简化版。**

禁止用 LLM 直接生成"官方真相 payload"。

### 3.2 统一分层
严格保持以下边界：

- `official-sim-server`：模拟平台行为
- `providers/*`：平台 provider，负责对接或消费 official-sim / real API
- `domain-service` / `unified`：标准化领域对象
- `ai-orchestrator`：建议回复、规则判断
- 前端：只调用 unified 层

### 3.3 可回放
所有 run 都必须至少支持：

- 查询当前状态
- 查询状态快照
- 查询 artifacts
- 查询 push events
- 回放 push event
- 生成 evaluation report

### 3.4 可测试
任何新增功能都必须附带测试，最低要求：

- 单元测试
- 状态机转移测试
- API 路由测试
- fixture 一致性测试

### 3.5 可审计
所有重要对象都必须带：

- run_id
- request_id
- platform
- scenario_key
- step_no
- created_at / updated_at

---

## 4. 仓库约定

### 4.1 新增目录
本阶段主要新增：

- `apps/official-sim-server/`
- `docs/`
- `schemas/`
- `alembic/versions/`（若当前仓库尚未统一管理迁移，则补齐）

### 4.2 official-sim-server 目标目录树
目标结构如下：

apps/official-sim-server/
  app/
    main.py
    api/
      router.py
      routes/
        runs.py
        taobao.py
        douyin_shop.py
        wecom_kf.py
    core/
      config.py
      enums.py
      errors.py
      ids.py
      logging.py
      security.py
    models/
      run.py
      scenario.py
      order.py
      shipment.py
      after_sale.py
      conversation.py
      artifact.py
      push_event.py
    domain/
      run_service.py
      scenario_engine.py
      state_machine.py
      artifact_builder.py
      push_dispatcher.py
      error_injector.py
    platforms/
      base/
        profile.py
        adapter.py
        emitter.py
        validator.py
      taobao/
      douyin_shop/
      wecom_kf/
    repositories/
      run_repo.py
      snapshot_repo.py
      artifact_repo.py
      push_event_repo.py
      evaluation_repo.py
    fixtures/
      taobao/
      douyin_shop/
      wecom_kf/
    tests/
      unit/
      integration/
      fixtures/
  README.md

### 4.3 不要擅自改动
除非任务明确要求，不要大改以下模块的既有行为：

- `apps/api-gateway/`
- `apps/domain-service/`
- `apps/ai-orchestrator/`
- `apps/mock-platform-server/`
- 现有 `providers/*` 的 public interface

允许在必要时增加 adapter / integration 接口，但不要破坏已有契约。

---

## 5. 数据与状态建模规则

### 5.1 第一批核心表
优先实现：

- simulation_runs
- simulation_events
- state_snapshots
- push_events
- artifacts
- evaluation_reports

### 5.2 第二批业务表
后续实现：

- sim_orders
- sim_order_items
- sim_shipments
- sim_shipment_nodes
- sim_after_sales
- sim_conversations
- sim_messages

### 5.3 统一字段约定
- 金额用 `NUMERIC(18,2)` 或等价安全精度方案
- 时间统一存 UTC，接口输出带时区
- 外部对象 ID 原样保留，内部对象使用独立主键
- 平台枚举统一用小写 snake / kebab 规范，不混用
- 所有状态字段必须有 enum 定义，不允许裸字符串散落在逻辑中

---

## 6. API 约定

P0 至少实现以下接口：

- `POST /official-sim/runs`
- `GET /official-sim/runs/{run_id}`
- `POST /official-sim/runs/{run_id}/advance`
- `GET /official-sim/runs/{run_id}/artifacts`
- `POST /official-sim/runs/{run_id}/inject-error`
- `POST /official-sim/runs/{run_id}/replay-push`
- `GET /official-sim/runs/{run_id}/report`

要求：

1. 所有接口返回统一 envelope 或明确 schema。
2. 所有错误都有稳定 code / message / request_id。
3. 所有接口都要有 pytest。
4. 所有接口都要有 README 中的 curl 示例。

---

## 7. fixture 规则

### 7.1 目录规则
每个平台至少有三类 fixture：

- `success/`
- `edge_case/`
- `error_case/`

### 7.2 命名规则
示例：

- `order_wait_ship.json`
- `order_shipped_partial.json`
- `refund_pending_review.json`
- `push_order_status_changed.json`
- `callback_enter_session.json`

### 7.3 fixture 使用原则
- fixture 不是任意 JSON 样例，而是状态机产物或状态机模板
- fixture 必须能被测试引用
- fixture 版本变更必须同步更新测试
- 同一个状态不可出现多个互相冲突的 schema

---

## 8. 测试与验证规则

每完成一个 milestone，必须运行：

1. 格式化 / lint
2. 类型检查（若已配置）
3. 单元测试
4. 集成测试
5. migration smoke test
6. fixture consistency test

若任一验证失败：

- 先修复
- 再继续下一 milestone
- 禁止带着失败测试进入下个阶段

---

## 9. 编码要求

### 9.1 Python 代码要求
- 优先使用清晰、可维护、显式的类型定义
- 核心 domain/service/repository 必须有类型注解
- Pydantic schema 与 DB model 分离
- 路由层不直接写复杂业务逻辑
- 状态机逻辑集中管理，不允许分散在 route 中

### 9.2 FastAPI 要求
- 路由按平台 / runs 分模块
- 统一在 `api/router.py` 聚合
- 使用依赖注入获取 service / repo
- 路由层只做：
  - 参数校验
  - service 调用
  - response 序列化

### 9.3 数据库要求
- migration 必须可重复执行
- 所有外键和索引要明确
- 核心查询路径必须有索引
- 重要写入必须在事务内

---

## 10. 日志、审计、回放

必须记录：

- run 创建
- state advance
- artifact build
- push event emit
- push event ack
- inject-error
- replay-push
- evaluation 生成

日志最少包含：

- run_id
- platform
- scenario_key
- step_no
- request_id
- event_type

---

## 11. Milestone 输出要求

每完成一个 milestone，提交内容至少包括：

- 代码
- migration
- fixtures
- tests
- README / usage
- 本阶段 decision notes
- 未完成项 / TODO

---

## 12. 常见错误处理原则

P0 至少覆盖：

- token_expired
- invalid_signature
- timestamp_out_of_window
- permission_denied
- resource_not_found
- rate_limited
- duplicate_push
- out_of_order_push
- callback_ack_invalid
- conversation_closed
- msg_code_expired

每个错误都必须有：

- 稳定错误码
- HTTP 状态码
- message
- 是否可重试
- 测试覆盖

---

## 13. 完成定义（Definition of Done）

一个 milestone 只有在以下全部满足时才算完成：

1. 目标代码已实现
2. migration 已提交
3. fixtures 已提交
4. pytest 通过
5. README/curl 示例可运行
6. acceptance criteria 对应条目已满足
7. 未决问题已明确写入 TODO / decision notes

---

## 14. 优先级判断规则

遇到冲突时按以下优先级决策：

1. 正确性
2. 可回放
3. 可测试
4. 可审计
5. 与现有 unified/provider 兼容
6. 代码优雅性
7. 开发速度

---

## 15. 不确定时怎么处理

如果遇到以下情况：

- 平台字段细节无法确认
- 计划书未明确写死
- 现有仓库实现与计划冲突

处理方式：

1. 不要臆造平台事实
2. 优先保守实现最小可运行版本
3. 写出 TODO / decision note
4. 保持接口稳定
5. 用 fixture + test 锁定当前行为
