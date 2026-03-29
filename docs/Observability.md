# Observability

## 1. 文档目的

本文档定义 official-sim-server 的日志、审计、追踪、回放与数据脱敏要求。

official-sim 的核心目标之一是：
- 可回放
- 可审计
- 可复现
- 可定位错误来源

因此 observability 不是附属能力，而是 P0 核心能力。

---

## 2. 总体原则

### 2.1 一切围绕 run
所有日志、事件、工件、推送、错误、报告，都必须能追溯到：
- run_id
- step_no
- platform
- scenario_key
- request_id

### 2.2 状态与工件分离观察
必须同时能看到：
1. 当前状态是什么
2. 平台吐出了什么工件
3. 推送有没有成功
4. 错误是在哪一层出现的

### 2.3 先结构化日志
P0 优先结构化 JSON 日志，不追求复杂 tracing 系统。

### 2.4 先可搜索，后可视化
P0 只要求日志字段稳定、可 grep / 可筛选；仪表盘放后面。

---

## 3. 统一日志字段

所有结构化日志至少包含：

- timestamp
- level
- service
- env
- request_id
- run_id
- step_no
- platform
- scenario_key
- event_type
- message

建议补充：
- route_key
- artifact_type
- push_event_id
- error_code
- duration_ms

---

## 4. 必记日志点

### 4.1 run 生命周期
必须记录：
- create_run
- get_run
- advance_run
- inject_error
- generate_report

### 4.2 状态推进
必须记录：
- old_state_summary
- new_state_summary
- action_type
- state_machine_name

### 4.3 artifact 生成
必须记录：
- artifact_id
- artifact_type
- route_key
- platform

### 4.4 push 相关
必须记录：
- push_event_created
- push_event_sent
- push_event_acked
- push_event_replayed
- push_event_failed

### 4.5 错误
必须记录：
- error_code
- error_type
- retryable
- injected / observed
- source_layer

---

## 5. 审计对象

以下对象必须可审计：

1. simulation_runs
2. simulation_events
3. state_snapshots
4. artifacts
5. push_events
6. evaluation_reports

审计要求：
- 可按 run_id 查询
- 可按 platform 查询
- 可按 time range 查询
- 可按 error_code 查询

---

## 6. 回放要求

### 6.1 run 回放
至少支持：
- 查看 run 当前状态
- 查看历史 events
- 查看历史 snapshots

### 6.2 artifact 回放
至少支持：
- 获取某一步生成的 HTTP artifact
- 获取 callback / webhook artifact

### 6.3 push 回放
至少支持：
- 重放已存在 push event
- 记录 replay 时间
- 记录 replay 结果

---

## 7. Metrics（P0 最小集）

P0 不要求引入完整监控系统，但应预留以下计数与时延指标：

### 7.1 计数类
- runs_created_total
- runs_completed_total
- runs_failed_total
- artifacts_created_total
- push_events_created_total
- push_events_failed_total
- error_injected_total
- observed_errors_total

### 7.2 时延类
- run_advance_duration_ms
- artifact_build_duration_ms
- push_replay_duration_ms
- report_generation_duration_ms

### 7.3 平台维度
所有指标建议支持平台标签：
- taobao
- douyin_shop
- wecom_kf
- jd
- xhs
- kuaishou

---

## 8. 数据脱敏规则

P0 必须遵守：

### 8.1 需要脱敏的字段
- phone
- receiver_mobile
- address_detail
- id_card / customs id
- corp_secret
- app_secret
- token / access_token
- sign 原文（必要时部分保留）

### 8.2 日志中禁止全量输出
以下不允许明文出现在日志：
- app_secret
- corp_secret
- access_token
- refresh_token
- raw signature secret

### 8.3 推荐策略
- 手机：中间 4 位打码
- 地址：详细门牌截断
- token：只显示前后少量字符
- secret：完全不打印

---

## 9. Report 可观测性要求

每份 report 至少包含：

- run_id
- platform
- scenario_key
- final_state_summary
- artifacts_count
- push_events_count
- injected_errors
- observed_errors
- replay_actions
- expected_vs_actual
- open_issues

---

## 10. 日志目录与级别建议

### 10.1 级别
- INFO：正常业务推进
- WARNING：重复推送、乱序推送、边界错误
- ERROR：系统错误、不可恢复错误
- DEBUG：开发环境详细调试信息

### 10.2 文件分流（可选）
P0 可不做复杂分流，但推荐至少区分：
- app.log
- error.log
- audit.log（可后续）

---

## 11. 测试要求

必须至少有：

1. request_id 贯穿测试
2. run_id / step_no 日志字段测试
3. error log 字段测试
4. artifact 审计字段测试
5. push replay 审计测试
6. 脱敏测试

---

## 12. P0 完成定义

observability 只有在以下全部满足时完成：

- 关键日志点存在
- 统一日志字段存在
- 审计对象可追溯
- push replay 可记录
- report 含可观测字段
- 脱敏规则已落地
