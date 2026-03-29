# State Machine - Douyin Shop

## 1. 文档目的

定义抖店 P0 阶段在 official-sim 中的状态机、推送机制、签名校验规则和错误注入规则。

本文件用于约束 `platforms/douyin_shop/` 的实现，不是介绍文档。

---

## 2. 设计目标

抖店 P0 只模拟以下能力：

1. 订单状态机
2. 退款状态机
3. push payload
4. push ack 记录
5. sign 校验失败
6. token / permission / timestamp 类错误

P0 不实现全量商品和全量权限系统。

---

## 3. 核心对象

### 3.1 Order
最少字段：
- orderId
- status
- createTime
- payTime
- shopId
- amount
- items[]
- extra

### 3.2 Refund
最少字段：
- afterSaleId
- orderId
- refundStatus
- refundType
- refundAmount
- latestOperateTime
- evidenceRequired

### 3.3 Push Envelope
最少字段：
- topic
- biz_id
- shop_id
- timestamp
- body
- headers

headers 最少包括：
- event-sign
- app-id
- sign_method

---

## 4. 订单状态机

### 4.1 状态枚举
- CREATED
- PAID
- WAIT_SHIP
- SHIPPED
- COMPLETED
- CANCELLED

### 4.2 P0 允许链路
- CREATED -> PAID
- PAID -> WAIT_SHIP
- WAIT_SHIP -> SHIPPED
- SHIPPED -> COMPLETED
- CREATED -> CANCELLED
- PAID -> CANCELLED

### 4.3 非法转移
- COMPLETED -> WAIT_SHIP
- CANCELLED -> SHIPPED
- SHIPPED -> PAID

错误类型：
- invalid_order_status_transition

---

## 5. 退款状态机

### 5.1 状态枚举
- REQUESTED
- REVIEWING
- APPROVED
- REJECTED
- REFUNDED
- CLOSED

### 5.2 允许链路
- REQUESTED -> REVIEWING
- REVIEWING -> APPROVED
- REVIEWING -> REJECTED
- APPROVED -> REFUNDED
- REJECTED -> CLOSED

### 5.3 非法转移
- REFUNDED -> REVIEWING
- CLOSED -> APPROVED

错误类型：
- invalid_refund_status_transition

---

## 6. 触发动作（actions）

### 6.1 create_order
效果：
- 创建订单
- order.status = CREATED
- 产出 artifact:
  - order_detail

### 6.2 pay_order
前置条件：
- order.status == CREATED

效果：
- order.status -> PAID
- 产出 artifact:
  - order_detail
  - push_order_status_changed

### 6.3 ready_to_ship
前置条件：
- order.status == PAID

效果：
- order.status -> WAIT_SHIP
- 产出 artifact:
  - order_detail
  - push_order_status_changed

### 6.4 ship_order
前置条件：
- order.status == WAIT_SHIP

效果：
- order.status -> SHIPPED
- 产出 artifact:
  - order_detail
  - push_order_status_changed

### 6.5 complete_order
前置条件：
- order.status == SHIPPED

效果：
- order.status -> COMPLETED
- 产出 artifact:
  - order_detail
  - push_order_status_changed

### 6.6 request_refund
前置条件：
- order.status in [PAID, WAIT_SHIP, SHIPPED, COMPLETED]

效果：
- 创建 refund
- refund.status -> REQUESTED
- 产出 artifact:
  - refund_detail
  - push_refund_status_changed

### 6.7 review_refund
前置条件：
- refund.status == REVIEWING

效果：
- refund.status -> APPROVED or REJECTED
- 产出 artifact:
  - refund_detail
  - push_refund_status_changed

### 6.8 finish_refund
前置条件：
- refund.status == APPROVED

效果：
- refund.status -> REFUNDED
- 产出 artifact:
  - refund_detail
  - push_refund_status_changed

---

## 7. Push 规则

### 7.1 push 触发原则
以下事件必须生成 push artifact：
- 订单状态变化
- 退款状态变化

### 7.2 push 头部
push artifact 必须带：
- event-sign
- app-id
- sign_method

### 7.3 sign_method
P0 允许：
- md5
- hmac-sha256

### 7.4 ACK 规则
P0 最小实现：
- 记录 ack 成功 / 失败
- 记录 ack_at
- 记录 response body
- 失败时可重放

---

## 8. Artifact 规则

### 8.1 order_detail
最少包含：
- orderId
- status
- shopId
- amount
- items[]
- createTime
- payTime

### 8.2 refund_detail
最少包含：
- afterSaleId
- orderId
- refundStatus
- refundType
- refundAmount
- latestOperateTime

### 8.3 push_order_status_changed
最少包含：
- topic
- biz_id
- old_status
- new_status
- occurred_at
- body
- headers

### 8.4 push_refund_status_changed
最少包含：
- topic
- biz_id
- old_status
- new_status
- occurred_at
- body
- headers

### 8.5 signature_error_payload
最少包含：
- expected_sign_method
- provided_sign
- expected_sign
- validation_result

---

## 9. Error Injector 规则

P0 必须支持：

### 9.1 invalid_signature
效果：
- push 校验失败
- API 请求签名失败
- 记录 validation error artifact

### 9.2 token_expired
效果：
- access token 相关请求失败

### 9.3 permission_denied
效果：
- 指定 shop / app_key 权限不足

### 9.4 duplicate_push
效果：
- 同一事件重复投递一次

### 9.5 invalid_ack
效果：
- 接收方 ACK 不符合预期

### 9.6 timestamp_out_of_window
效果：
- 时间戳过期或不合法，校验失败

---

## 10. Fixtures 规范

目录结构：

fixtures/douyin_shop/
  success/
    order_created.json
    order_paid.json
    order_wait_ship.json
    order_shipped.json
    refund_requested.json
    refund_refunded.json
    push_order_status_changed.json
    push_refund_status_changed.json
  edge_case/
    duplicate_push.json
    invalid_ack.json
  error_case/
    invalid_signature.json
    token_expired.json
    permission_denied.json
    timestamp_out_of_window.json

---

## 11. Pytest 最低覆盖

必须存在：

1. 订单正向链路测试
2. 退款链路测试
3. push 生成测试
4. ACK 记录测试
5. invalid_signature 测试
6. timestamp_out_of_window 测试
7. route 测试
8. fixture consistency 测试

---

## 12. P0 完成定义

抖店 profile 只有在以下全部满足时完成：

- 订单状态机可运行
- 退款状态机可运行
- push artifact 可生成
- sign/ack 错误可测试
- README 样例可运行
- pytest 全绿
