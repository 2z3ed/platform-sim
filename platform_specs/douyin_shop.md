# Platform Spec - Douyin Shop

## 1. 平台定位

抖店在 official-sim 中代表：
- 签名校验严格
- 订单/退款分域
- 主动消息推送显著
- push ACK 与签名验证重要

P0 目标是：
- 订单与退款状态机可运行
- push 工件可生成
- signature / ack 类错误可注入
- 能被 unified/provider 消费

---

## 2. P0 必须实现的 endpoints

### 2.1 run 侧
- `POST /official-sim/runs`
- `GET /official-sim/runs/{run_id}`
- `POST /official-sim/runs/{run_id}/advance`
- `GET /official-sim/runs/{run_id}/artifacts`
- `POST /official-sim/runs/{run_id}/inject-error`
- `POST /official-sim/runs/{run_id}/replay-push`

### 2.2 平台侧
- `POST /official-sim/douyin-shop/auth/token`
- `GET /official-sim/douyin-shop/orders/{order_id}`
- `GET /official-sim/douyin-shop/refunds/{after_sale_id}`
- `GET /official-sim/douyin-shop/products/{product_id}`
- `POST /official-sim/douyin-shop/push/verify`
- `POST /official-sim/douyin-shop/push/replay`

---

## 3. P0 必须实现的状态

### 3.1 订单状态
- CREATED
- PAID
- WAIT_SHIP
- SHIPPED
- COMPLETED
- CANCELLED

### 3.2 退款状态
- REQUESTED
- REVIEWING
- APPROVED
- REJECTED
- REFUNDED
- CLOSED

### 3.3 商品状态（最小）
- DRAFT
- ONLINE
- OFFLINE
- STOCK_CHANGED

---

## 4. P0 必须实现的 artifact

- order_detail
- refund_detail
- push_order_status_changed
- push_refund_status_changed
- signature_error_payload
- error_response_payload

---

## 5. P0 必须实现的错误

- invalid_signature
- timestamp_out_of_window
- token_expired
- permission_denied
- invalid_ack
- duplicate_push
- invalid_order_status_transition
- invalid_refund_status_transition

---

## 6. Unified 映射要求

### 6.1 Order
- `orderId` -> `orderId`
- `status` -> `Order.status`
- amount fields -> `payAmount` / `totalAmount`

### 6.2 AfterSale
- `afterSaleId` -> `afterSaleId`
- `refundStatus` -> `AfterSale.status`
- `refundType` -> `AfterSale.type`
- `refundAmount` -> `amount`

### 6.3 Push
- push payload -> `PushEvent`
- push ack result -> `push_events.status`

---

## 7. P0 不做

- 全量商品域
- 全量履约域
- 复杂店铺权限树
- 全量客服消息域
- 全量订阅主题管理

---

## 8. Fixtures 清单

至少包括：

- `order_created.json`
- `order_paid.json`
- `order_wait_ship.json`
- `order_shipped.json`
- `refund_requested.json`
- `refund_refunded.json`
- `push_order_status_changed.json`
- `push_refund_status_changed.json`
- `invalid_signature.json`
- `timestamp_out_of_window.json`
- `invalid_ack.json`

---

## 9. 测试要求

至少包括：

- 订单状态机测试
- 退款状态机测试
- push 生成测试
- push ack 测试
- sign 校验测试
- timestamp 错误测试
- route schema 测试
- fixture consistency 测试

---

## 10. Known Limitations

P0 抖店 profile 不追求全量官方 topic/字段，只保证：
- 签名与 push 是一等公民
- 订单/退款链路可联调
- 错误可注入
- 工件可回放
