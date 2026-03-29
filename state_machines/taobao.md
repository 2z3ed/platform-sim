# State Machine - Taobao

## 1. 文档目的

定义淘宝 P0 阶段在 official-sim 中的状态机、事件、artifact 产出与错误注入规则。

本文件是 Codex 实现 `platforms/taobao/` 的直接规范，不是说明性文档。

---

## 2. 设计目标

淘宝 P0 只模拟以下核心能力：

1. trade/order 主子订单结构
2. 正向交易状态链路
3. 最小逆向退款/售后状态
4. 订单推送工件
5. 常见错误注入

P0 不追求全量真实细节。

---

## 3. 核心对象

### 3.1 Trade
字段最少包括：

- tid
- status
- buyer
- created
- paid_time
- orders[]
- payment
- post_fee
- extra

### 3.2 Order
字段最少包括：

- oid
- num_iid
- sku_id
- title
- num
- status
- refund_status
- price
- payment
- divide_order_fee

### 3.3 Refund
字段最少包括：

- refund_id
- tid
- oid
- status
- refund_fee
- reason
- created
- modified

---

## 4. 正向状态机

### 4.1 状态枚举
- WAIT_BUYER_PAY
- WAIT_SELLER_SEND_GOODS
- SELLER_CONSIGNED_PART
- WAIT_BUYER_CONFIRM_GOODS
- TRADE_FINISHED
- TRADE_CLOSED
- TRADE_CLOSED_BY_TAOBAO

### 4.2 P0 允许的主链路
1. WAIT_BUYER_PAY
2. WAIT_SELLER_SEND_GOODS
3. WAIT_BUYER_CONFIRM_GOODS
4. TRADE_FINISHED

### 4.3 P0 允许的补充分支
- WAIT_BUYER_PAY -> TRADE_CLOSED
- WAIT_SELLER_SEND_GOODS -> TRADE_CLOSED
- WAIT_SELLER_SEND_GOODS -> SELLER_CONSIGNED_PART
- SELLER_CONSIGNED_PART -> WAIT_BUYER_CONFIRM_GOODS

### 4.4 非法转移
以下转移必须报错：
- TRADE_FINISHED -> WAIT_SELLER_SEND_GOODS
- TRADE_CLOSED -> WAIT_BUYER_CONFIRM_GOODS
- WAIT_BUYER_CONFIRM_GOODS -> WAIT_BUYER_PAY

错误类型：
- invalid_trade_status_transition

---

## 5. 逆向售后状态机（P0 最小集）

### 5.1 状态枚举
- REFUND_REQUESTED
- PENDING_SELLER_REVIEW
- APPROVED
- REJECTED
- REFUNDED
- CLOSED

### 5.2 允许的转移
- REFUND_REQUESTED -> PENDING_SELLER_REVIEW
- PENDING_SELLER_REVIEW -> APPROVED
- PENDING_SELLER_REVIEW -> REJECTED
- APPROVED -> REFUNDED
- REJECTED -> CLOSED

### 5.3 非法转移
- REFUNDED -> PENDING_SELLER_REVIEW
- CLOSED -> APPROVED

错误类型：
- invalid_refund_status_transition

---

## 6. 触发动作（actions）

### 6.1 create_trade
效果：
- 创建 trade
- 创建一个或多个 order
- 初始状态为 WAIT_BUYER_PAY
- 产出 artifact: trade_detail

### 6.2 pay_trade
前置条件：
- trade.status == WAIT_BUYER_PAY

效果：
- trade.status -> WAIT_SELLER_SEND_GOODS
- paid_time 赋值
- 产出 artifact:
  - trade_detail
  - rds_push_trade_changed

### 6.3 consign_trade
前置条件：
- trade.status in [WAIT_SELLER_SEND_GOODS, SELLER_CONSIGNED_PART]

效果：
- 全单发货时 -> WAIT_BUYER_CONFIRM_GOODS
- 部分发货时 -> SELLER_CONSIGNED_PART
- 产出 artifact:
  - trade_detail
  - shipment_snapshot
  - rds_push_trade_changed

### 6.4 confirm_receipt
前置条件：
- trade.status == WAIT_BUYER_CONFIRM_GOODS

效果：
- trade.status -> TRADE_FINISHED
- 产出 artifact:
  - trade_detail
  - rds_push_trade_changed

### 6.5 close_trade
前置条件：
- trade.status in [WAIT_BUYER_PAY, WAIT_SELLER_SEND_GOODS]

效果：
- trade.status -> TRADE_CLOSED
- 产出 artifact:
  - trade_detail
  - rds_push_trade_changed

### 6.6 request_refund
前置条件：
- trade.status in [WAIT_SELLER_SEND_GOODS, WAIT_BUYER_CONFIRM_GOODS, TRADE_FINISHED]

效果：
- 创建 refund
- refund.status -> REFUND_REQUESTED
- 产出 artifact:
  - refund_snapshot
  - rds_push_refund_changed

### 6.7 review_refund
前置条件：
- refund.status == PENDING_SELLER_REVIEW

效果：
- APPROVED 或 REJECTED
- 产出 artifact:
  - refund_snapshot
  - rds_push_refund_changed

### 6.8 finish_refund
前置条件：
- refund.status == APPROVED

效果：
- refund.status -> REFUNDED
- 产出 artifact:
  - refund_snapshot
  - rds_push_refund_changed

---

## 7. Artifact 规则

### 7.1 trade_detail
最少包含：
- tid
- status
- orders[]
- payment
- created
- paid_time

### 7.2 shipment_snapshot
最少包含：
- tid
- shipping_type
- carrier
- out_sid
- nodes[]
- latest_status

### 7.3 refund_snapshot
最少包含：
- refund_id
- tid
- oid
- status
- refund_fee
- modified

### 7.4 rds_push_trade_changed
最少包含：
- tid
- new_status
- old_status
- occurred_at
- event_type

### 7.5 rds_push_refund_changed
最少包含：
- refund_id
- tid
- new_status
- old_status
- occurred_at
- event_type

---

## 8. Error Injector 规则

P0 必须支持：

### 8.1 token_expired
效果：
- 下一次鉴权相关查询返回 auth_error

### 8.2 resource_not_found
效果：
- 指定 tid / refund_id 查询返回 not_found

### 8.3 duplicate_push
效果：
- 同一 push event 可重复发一次
- report 中标记为 duplicate

### 8.4 out_of_order_push
效果：
- 后一个状态事件先于前一个状态事件发出
- report 中标记为 out_of_order

### 8.5 invalid_trade_status_transition
效果：
- 禁止非法推进

---

## 9. Fixtures 规范

目录结构：

fixtures/taobao/
  success/
    trade_wait_pay.json
    trade_wait_ship.json
    trade_shipped.json
    trade_finished.json
    refund_requested.json
    refund_refunded.json
  edge_case/
    trade_partial_consign.json
    trade_closed_before_pay.json
  error_case/
    token_expired.json
    duplicate_push.json
    out_of_order_push.json
    trade_not_found.json

---

## 10. Pytest 最低覆盖

必须存在：

1. 正向状态链路测试
2. 关闭订单测试
3. 部分发货测试
4. 退款链路测试
5. push artifact 生成测试
6. duplicate_push / out_of_order_push 测试
7. route 测试
8. fixture consistency 测试

---

## 11. P0 完成定义

淘宝 profile 只有在以下全部满足时完成：

- 正向状态机通过
- 退款最小状态机通过
- 5 类 artifact 可生成
- 4 类关键错误可注入
- README 样例可运行
- pytest 全绿
