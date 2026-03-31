# Platform Spec - Kuaishou

## 1. 平台定位

快手在 official-sim 中代表：
- 商品/订单/退款/物流/客服消息分域
- 查询型行为为主
- 客服消息/卡片能力是重要差异点

**Agent 集成方式**：
- User Agent 生成用户行为（下单、付款、申请退款等）
- official-sim-server 基于 fixtures/kuaishou/ 返回官方级 payload
- 前端/AI 直接消费 unified 层，不感知平台差异

**Fixture 使用原则**：
- 官方 API payload 必须从 fixtures/kuaishou/ 加载
- 不得使用 profile.py 硬编码函数返回简化版
- fixtures/ 字段必须与 docs/official_api/OFFICIAL_API_FIELDS.md 一致

P0 只做骨架。

---

## 2. P0 范围

必须存在：
- `app/api/routes/kuaishou.py`
- `app/platforms/kuaishou/profile.py`
- `app/platforms/kuaishou/state_machine.py`
- `app/platforms/kuaishou/artifact_builder.py`
- `app/platforms/kuaishou/error_injector.py`
- `app/platforms/kuaishou/fixtures/`

---

## 3. P1 必做候选

- `GET /official-sim/kuaishou/orders/{orderId}`
- `GET /official-sim/kuaishou/refunds/{afterSaleId}`
- `GET /official-sim/kuaishou/products/{productId}`
- `GET /official-sim/kuaishou/logistics/{orderId}`
- `POST /official-sim/kuaishou/customer-messages/send`

---

## 4. 最小状态建议

订单：
- created
- paid
- wait_ship
- shipped
- completed

退款：
- requested
- processing
- approved
- rejected
- refunded
- closed

物流：
- none
- transit
- delivered

客服消息：
- pending
- sent
- failed

---

## 5. Known Limitations

P0 快手只建骨架。客服消息细节和物流细节到 P1/P2。
