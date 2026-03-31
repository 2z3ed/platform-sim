# Platform Spec - XHS

## 1. 平台定位

小红书在 official-sim 中代表：
- 订单列表轮询
- 订单详情补拉
- 收件人信息/海关信息拆分
- 售后列表与审核链路

**Agent 集成方式**：
- User Agent 生成用户行为（下单、付款、申请售后等）
- official-sim-server 基于 fixtures/xhs/ 返回官方级 payload
- 前端/AI 直接消费 unified 层，不感知平台差异

**Fixture 使用原则**：
- 官方 API payload 必须从 fixtures/xhs/ 加载
- 不得使用 profile.py 硬编码函数返回简化版
- fixtures/ 字段必须与 docs/official_api/OFFICIAL_API_FIELDS.md 一致

P0 只做骨架。

---

## 2. P0 范围

必须存在：
- `app/api/routes/xhs.py`
- `app/platforms/xhs/profile.py`
- `app/platforms/xhs/state_machine.py`
- `app/platforms/xhs/artifact_builder.py`
- `app/platforms/xhs/error_injector.py`
- `app/platforms/xhs/fixtures/`

---

## 3. P1 必做候选

- `GET /official-sim/xhs/orders`
- `GET /official-sim/xhs/orders/{orderId}`
- `GET /official-sim/xhs/orders/{orderId}/receiver`
- `GET /official-sim/xhs/orders/{orderId}/customs`
- `GET /official-sim/xhs/aftersales/{afterSaleId}`
- `POST /official-sim/xhs/aftersales/{afterSaleId}/review`
- `POST /official-sim/xhs/aftersales/{afterSaleId}/confirm-receipt`

---

## 4. 最小状态建议

订单：
- new
- wait_ship
- shipped
- completed

售后：
- requested
- pending_review
- approved
- rejected
- waiting_return
- merchant_received
- refunded
- closed

---

## 5. Known Limitations

P0 小红书只建骨架。轮询节奏、售后细化到 P1。
