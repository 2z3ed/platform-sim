# Fixture Contract

## 1. 文档目的

本文档定义 official-sim 中 fixtures 的组织方式、命名规范、版本约束、与状态机的关系、与测试的关系。

本文件的目标不是描述"有哪些 fixture"，而是定义"fixture 必须如何存在"。

---

## 2. fixture 的角色

fixtures 在 official-sim 中有 4 个职责：

1. 提供平台侧 payload 模板
2. 为状态机产物提供静态底座
3. 为测试提供稳定输入/输出样本
4. 为回放和审计提供可重复数据源

### 重要原则
fixture 不是随机 JSON，也不是临时示例。

fixture 必须：
- 可追踪
- 可复用
- 可测试
- 可版本化
- 与 state machine 对应

---

## 3. 目录结构

### 3.1 平台目录
每个平台一套目录：

fixtures/
  taobao/
  douyin_shop/
  wecom_kf/
  jd/
  xhs/
  kuaishou/

### 3.2 场景层级
每个平台至少拆成：

- success/
- edge_case/
- error_case/

### 3.3 对象层级
如平台复杂度较高，可继续拆：

fixtures/taobao/
  success/
    trade/
    shipment/
    refund/
    push/
  edge_case/
  error_case/

P0 阶段允许平铺，但命名必须清晰。

---

## 4. 命名规范

文件命名统一：

`{object}_{state_or_case}.json`

示例：

- `trade_wait_pay.json`
- `trade_wait_ship.json`
- `trade_finished.json`
- `refund_requested.json`
- `push_trade_status_changed.json`
- `invalid_signature.json`
- `msg_code_expired.json`

禁止出现：

- `test1.json`
- `sample.json`
- `new.json`
- `tmp.json`

---

## 5. fixture 元信息要求

每个 fixture 文件必须满足以下两种方式之一：

### 方式 A：文件内含 meta
```json
{
  "_meta": {
    "platform": "taobao",
    "object_type": "trade_detail",
    "scenario_key": "trade_wait_ship",
    "state": "WAIT_SELLER_SEND_GOODS",
    "case_type": "success",
    "version": "1.0"
  },
  "payload": {}
}
```

### 方式 B：旁路 meta 文件
- trade_wait_ship.json
- trade_wait_ship.meta.json

P0 推荐使用方式 A，降低实现复杂度。

---

## 6. fixture 最小元字段

无论采用哪种方式，至少要有：

- platform
- object_type
- scenario_key
- case_type
- version

建议补充：

- source
- related_state
- related_action
- notes

---

## 7. fixture 与状态机的关系

### 7.1 单向约束

状态机定义"允许出现什么状态与行为"；fixture 是这些状态/行为的模板或快照。

不能反过来用 fixture 发明新的状态。

### 7.2 一个状态可对应多个 fixture

例如：

- trade_wait_ship_domestic.json
- trade_wait_ship_partial.json

但都必须归属于同一 canonical state。

### 7.3 必须存在 canonical fixture

每个 P0 状态至少有一个 canonical fixture。

例如：

- trade_wait_pay.json
- trade_wait_ship.json
- trade_finished.json

---

## 8. fixture 与 artifact 的关系

artifact 不是简单返回 fixture 原文。

artifact = fixture 模板 + run state + dynamic overrides

例如：

- tid
- orderId
- timestamps
- request_id
- step_no
- injected error info

这些动态字段可以在 runtime 注入，但基础结构必须来自 fixture。

---

## 9. fixture 与测试的关系

每个 fixture 必须至少服务于以下之一：

- route test
- state machine test
- integration test
- replay test
- error injection test

如果某 fixture 没有任何测试引用，默认视为无效 fixture，应清理或补测试。

---

## 10. 平台 P0 fixture 最低清单

### 10.1 Taobao

必须至少存在：

- trade_wait_pay.json
- trade_wait_ship.json
- trade_shipped.json
- trade_finished.json
- refund_requested.json
- refund_refunded.json
- push_trade_status_changed.json
- push_refund_status_changed.json
- duplicate_push.json
- out_of_order_push.json

### 10.2 Douyin Shop

必须至少存在：

- order_created.json
- order_paid.json
- order_wait_ship.json
- order_shipped.json
- refund_requested.json
- refund_refunded.json
- push_order_status_changed.json
- push_refund_status_changed.json
- invalid_signature.json
- timestamp_out_of_window.json

### 10.3 WeCom KF

必须至少存在：

- callback_enter_session.json
- callback_user_message.json
- sync_msg_page1.json
- event_message_success.json
- service_state_active.json
- invalid_cursor.json
- msg_code_expired.json
- conversation_closed.json

---

## 11. Schema 校验要求

所有 fixture 必须通过两层校验：

### 11.1 meta 校验
校验：
- 元字段齐全
- platform 与目录匹配
- case_type 合法
- version 合法

### 11.2 payload 校验
校验：
- 满足对应 schema
- 必须字段齐全
- 不允许关键字段类型错误

P0 建议实现：
- fixture schema registry
- fixture validator CLI 或 pytest

---

## 12. 版本规则

### 12.1 version 字段

fixture 必须带 version。

### 12.2 何时升级版本

以下情况必须升级：

- 结构变化
- 必填字段变化
- 语义变化
- 与 state machine 绑定变化

### 12.3 向后兼容

P0 不要求完整兼容策略，但如果修改了 canonical fixture，必须同步更新测试与 decision notes。

---

## 13. 禁止事项

以下做法禁止：

- 直接在 route 中手写大量匿名 JSON 替代 fixture
- 让 LLM 运行时生成官方 payload
- 多个同名状态 fixture 语义冲突
- fixture 改了但测试不更新
- fixture 中混入随机不可复现数据
- fixture 文件没有来源和元信息

---

## 14. 测试要求

必须至少有：

- fixture meta 校验测试
- fixture payload schema 校验测试
- fixture 文件命名规范测试
- 每个平台 fixture completeness 测试
- canonical fixture 覆盖测试

---

## 15. P0 完成定义

fixture contract 只有在以下条件全部满足时完成：

- fixture 目录结构建立
- 三个平台最低 fixture 清单存在
- meta 规则存在
- schema 校验存在
- fixture consistency tests 通过
