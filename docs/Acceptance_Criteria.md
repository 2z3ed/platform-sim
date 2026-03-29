# Acceptance Criteria

## 1. 文档目的

本文档定义 P0 阶段的验收标准。
只有满足本文档中的强制性条目，相关模块才可视为"完成"。

---

## 2. 全局验收标准

### AC-G1: 工程可启动
- 仓库中存在 `apps/official-sim-server/`
- 应用可以本地启动
- 有健康检查或等价探针
- README 包含启动说明

### AC-G2: 工程可测试
- 存在 pytest 配置
- 存在 unit/integration 测试目录
- 可运行最小测试集
- fixture 测试可执行

### AC-G3: 工程可迁移
- 存在 migration 机制
- migration 可正向执行
- migration 可回滚
- 第一批核心表创建成功

### AC-G4: 工程可审计
以下对象至少具备：
- request_id
- run_id
- platform
- scenario_key
- step_no
- created_at / updated_at

### AC-G5: 工程可回放
- run 可查询
- artifacts 可查询
- push events 可回放
- evaluation report 可生成

---

## 3. Run 生命周期验收

### AC-R1: 创建 run
接口：
- `POST /official-sim/runs`

要求：
- 入参校验严格
- 返回唯一 run_id
- 初始化状态为 created 或等价状态
- 初始化 step_no = 0
- 写入 simulation_runs
- 写入首条 simulation_event

### AC-R2: 查询 run
接口：
- `GET /official-sim/runs/{run_id}`

要求：
- 返回 run 基本信息
- 返回当前状态
- 返回当前 step_no
- 返回 platform / scenario_key
- run 不存在时返回稳定错误

### AC-R3: 推进一步
接口：
- `POST /official-sim/runs/{run_id}/advance`

要求：
- step_no 增长
- 状态推进合法
- 写入 state_snapshot
- 写入 simulation_event
- 触发 artifact 生成
- 非法推进返回稳定错误

---

## 4. Artifact 与 Push 验收

### AC-A1: artifacts 查询
接口：
- `GET /official-sim/runs/{run_id}/artifacts`

要求：
- 返回当前 run 的 artifact 列表
- artifact 至少包含：
  - artifact_id
  - run_id
  - step_no
  - platform
  - artifact_type
  - payload
  - created_at

### AC-A2: push event 记录
要求：
- 每条 push event 都绑定 run_id 和 step_no
- 记录 event_type
- 记录 payload
- 记录 sent_at / acked_at
- 支持失败状态

### AC-A3: replay-push
接口：
- `POST /official-sim/runs/{run_id}/replay-push`

要求：
- 可重放已存在 push event
- 重放行为可记录
- 重放失败有稳定错误
- 不允许重放不属于当前 run 的事件

---

## 5. Error Injection 与 Report 验收

### AC-E1: inject-error
接口：
- `POST /official-sim/runs/{run_id}/inject-error`

要求：
- 至少支持 5 类错误
- 错误注入可追踪
- 错误注入后 artifact / push / report 能体现影响
- 非法错误类型返回稳定错误

### AC-E2: report
接口：
- `GET /official-sim/runs/{run_id}/report`

要求：
- 生成结构化报告
- 至少包含：
  - run summary
  - scenario
  - steps
  - artifacts
  - injected errors
  - evaluation result
  - open issues

---

## 6. 数据库验收

### AC-DB1: 第一批核心表存在
必须存在：
- simulation_runs
- simulation_events
- state_snapshots
- push_events
- artifacts
- evaluation_reports

### AC-DB2: 关键索引存在
最少应有：
- simulation_runs(run_id)
- simulation_events(run_id, step_no)
- state_snapshots(run_id, step_no)
- push_events(run_id, step_no)
- artifacts(run_id, step_no)

### AC-DB3: 数据约束存在
至少包括：
- 非空约束
- 主外键约束
- 时间字段合理性约束
- retry_count >= 0
- 金额非负约束（在对应业务表阶段启用）

---

## 7. 平台验收：Taobao

### AC-TB1: 基础状态机
至少支持：
- wait_buyer_pay
- wait_seller_send_goods
- wait_buyer_confirm_goods
- trade_finished

### AC-TB2: 逆向售后最小状态
至少支持：
- refund_requested
- pending_review
- approved / rejected
- refunded / closed

### AC-TB3: 工件覆盖
至少能生成：
- trade detail artifact
- shipment artifact
- refund artifact
- push artifact

### AC-TB4: 错误覆盖
至少支持：
- token_expired
- resource_not_found
- duplicate_push
- out_of_order_push

### AC-TB5: 测试覆盖
至少有：
- 状态转移测试
- route 测试
- fixture 一致性测试

---

## 8. 平台验收：Douyin Shop

### AC-DY1: 基础状态机
至少支持：
- created
- paid
- wait_ship
- shipped
- completed / cancelled

### AC-DY2: 退款状态机
至少支持：
- requested
- reviewing
- approved / rejected
- refunded / closed

### AC-DY3: 推送能力
至少支持：
- 订单推送工件
- 退款推送工件
- ack 记录
- 签名失败工件

### AC-DY4: 错误覆盖
至少支持：
- invalid_signature
- token_expired
- permission_denied
- duplicate_push

### AC-DY5: 测试覆盖
至少有：
- 状态转移测试
- push 验证测试
- route 测试

---

## 9. 平台验收：WeCom KF

### AC-WC1: 会话链路
至少支持：
- callback
- sync_msg
- send_msg_on_event

### AC-WC2: 会话状态
至少支持：
- new
- queued
- active
- transferred
- ended

### AC-WC3: 工件覆盖
至少能生成：
- callback artifact
- sync_msg artifact
- event message artifact
- service state artifact

### AC-WC4: 错误覆盖
至少支持：
- access_token_invalid
- msg_code_expired
- conversation_closed
- invalid_cursor

### AC-WC5: 测试覆盖
至少有：
- callback -> sync_msg 链路测试
- 会话状态测试
- route 测试

---

## 10. Integration 验收

### AC-I1: 最小 provider/unified 接入
要求：
- 至少一个 official-sim 产物可以通过 adapter 映射到 unified 对象
- 不破坏现有 `/mock/unified/...`
- 有最小 e2e test

### AC-I2: 与现有架构兼容
要求：
- 不强迫修改现有 public provider interface
- adapter 方式接入优先
- 文档说明清晰

---

## 11. 文档验收

### AC-DOC1: README
必须包含：
- 项目目的
- 启动方式
- migration 方式
- 测试方式
- curl 示例
- 已知限制

### AC-DOC2: 示例
至少有：
- 创建 run 示例
- 推进一步示例
- 获取 artifacts 示例
- 一个平台场景示例

### AC-DOC3: 决策记录
必须至少包含：
- 为什么不让 LLM 生成真相 payload
- 为什么 P0 只做 3 平台
- 为什么优先新增模块而不是大改旧模块

---

## 12. P0 最终验收

P0 通过的标准：

1. `official-sim-server` 存在且可运行
2. 第一批核心表 migration 完成
3. run / advance / artifacts / replay / report 可用
4. taobao / douyin_shop / wecom_kf 三平台 P0 profile 可用
5. 至少一个 integration e2e case 通过
6. README 和 curl 示例齐全
7. 关键 pytest 全绿

若任一未满足，则 P0 不通过。
