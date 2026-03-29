# Platform Spec - Taobao

## 1. 平台定位

淘宝在 official-sim 中代表：
- 主单 trade / 子单 order 结构
- 明确的正向交易状态链
- 逆向退款/售后流程
- 强调订单推送的电商平台

P0 目标不是做全量淘宝开放平台镜像，而是做：
- 可运行的正向/逆向状态机
- 可查询的 trade/order/refund 工件
- 可回放的订单/退款推送工件
- 可验证的常见错误

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
- `POST /official-sim/taobao/oauth/token`
- `GET /official-sim/taobao/trades/{tid}`
- `GET /official-sim/taobao/orders/{oid}`
- `GET /official-sim/taobao/logistics/{tid}`
- `GET /official-sim/taobao/refunds/{refund_id}`
- `POST /official-sim/taobao/push/replay`

---

## 3. P0 必须实现的状态

### 3.1 正向订单状态
- WAIT_BUYER_PAY
- WAIT_SELLER_SEND_GOODS
- SELLER_CONSIGNED_PART
- WAIT_BUYER_CONFIRM_GOODS
- TRADE_FINISHED
- TRADE_CLOSED

### 3.2 逆向售后状态
- REFUND_REQUESTED
- PENDING_SELLER_REVIEW
- APPROVED
- REJECTED
- REFUNDED
- CLOSED

---

## 4. P0 必须实现的 artifact

- trade_detail
- order_detail
- shipment_snapshot
- refund_snapshot
- rds_push_trade_changed
- rds_push_refund_changed
- error_response_payload

---

## 5. P0 必须实现的错误

- token_expired
- resource_not_found
- invalid_trade_status_transition
- invalid_refund_status_transition
- duplicate_push
- out_of_order_push

---

## 6. Unified 映射要求

### 6.1 Order
- `tid` -> `orderId`
- `trade.status` -> `Order.status`
- `buyer nick / info` -> `Customer`
- `orders[]` -> `Order.items[]`
- `payment` -> `payAmount`

### 6.2 Shipment
- `out_sid` -> `trackingNo`
- `company_name` -> `carrier`
- logistics node -> `ShipmentNode`

### 6.3 AfterSale
- `refund_id` -> `afterSaleId`
- `refund_status` -> `AfterSale.status`
- `refund_fee` -> `amount`

---

## 7. P0 不做

- 全量淘宝子业务域
- 完整隐私号链路
- 全量营销/履约复杂场景
- 全量跨境/保税场景
- 全量子单部分发货变体

---

## 8. Fixtures 清单

至少包括：

- `trade_wait_pay.json`
- `trade_wait_ship.json`
- `trade_shipped_partial.json`
- `trade_finished.json`
- `refund_requested.json`
- `refund_refunded.json`
- `push_trade_status_changed.json`
- `push_refund_status_changed.json`
- `duplicate_push.json`
- `out_of_order_push.json`

---

## 9. 测试要求

至少包括：

- 正向状态机测试
- 退款状态机测试
- push 工件测试
- 重复推送测试
- 乱序推送测试
- route schema 测试
- fixture consistency 测试

---

## 10. Known Limitations

P0 淘宝 profile 不是官方 1:1 镜像，只保证：
- 状态链路合理
- 工件稳定
- 接口可联调
- 错误可注入
- 可回放、可审计
