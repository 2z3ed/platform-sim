# Platform Spec - JD

## 1. 平台定位

京东在 official-sim 中代表：
- 查询型能力较强
- 订单/物流/售后分域清晰
- 物流轨迹与发货动作重要

P0 只做骨架，不做完整平台实现。

---

## 2. P0 范围

必须存在：
- `app/api/routes/jd.py`
- `app/platforms/jd/profile.py`
- `app/platforms/jd/state_machine.py`
- `app/platforms/jd/artifact_builder.py`
- `app/platforms/jd/error_injector.py`
- `app/platforms/jd/fixtures/`

这些文件只要求：
- 类型正确
- 结构可导入
- TODO 清晰
- 不伪造复杂 payload

---

## 3. P1 必做候选

- `GET /official-sim/jd/orders/{orderId}`
- `POST /official-sim/jd/orders/{orderId}/ship`
- `GET /official-sim/jd/shipments/{orderId}`
- `GET /official-sim/jd/after-sales/{afterSaleId}`
- OAuth/token
- 物流轨迹扩展
- 权限/签名错误

---

## 4. 最小状态建议

- created
- paid
- wait_ship
- shipped
- delivered
- completed
- closed

售后：
- requested
- reviewing
- approved
- rejected
- refunded
- closed

---

## 5. Known Limitations

P0 京东只建骨架。字段级行为到 P1/P2 再补。
