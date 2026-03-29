# Platform Matrix

## 1. 文档目的

本文档用于明确各平台在 official-sim 中的实现边界、行为重点、P0/P1 范围和与 unified 层的映射关系。

该文档服务于以下目标：

1. 避免 Codex 在平台行为上自由发挥。
2. 把"必须做 / 暂不做 / 后续做"的边界写死。
3. 让 state machine、fixtures、emitters、error injectors 具有统一参照。
4. 为 provider 和 unified 层提供稳定上游。

---

## 2. 平台总表

| platform | 官方行为特征 | P0 是否实现 | P0 核心重点 | P1/P2 延展 |
|---|---|---:|---|---|
| taobao | 主单/子单；交易状态明确；订单推送重要 | 是 | trade/order 状态机、退款最小逆向、推送工件 | 子单部分发货、更多退款场景、hold 单 |
| douyin_shop | API 调用强签名；消息推送强；订单/退款/商品分域 | 是 | 订单状态机、退款状态机、push、签名错误 | 商品事件、更多权限/订阅分支 |
| wecom_kf | callback -> 拉取/收发消息 -> 会话流转 | 是 | callback、sync_msg、send_msg_on_event、会话状态 | 欢迎语、更多事件类型、服务台能力 |
| jd | 查询型能力强；订单/物流/售后分域 | 否（P0占位） | 路由骨架、profile 占位 | 订单列表、发货动作、物流轨迹、售后细分 |
| xhs | 订单列表轮询；待发货后补拉详情/收件人/海关信息 | 否（P0占位） | 路由骨架、profile 占位 | 轮询列表、详情补拉、售后审核/确认收货 |
| kuaishou | 商品/订单/退款/物流/客服能力分域 | 否（P0占位） | 路由骨架、profile 占位 | 物流、商品卡片、客服消息、退款状态 |

---

## 3. 统一建模原则

所有平台都必须映射到以下统一对象：

- Customer
- Conversation
- Message
- Order
- Shipment
- AfterSale
- Suggestion
- Artifact
- PushEvent
- EvaluationReport

统一层目标不是复制平台字段，而是保留最小必要语义：

- 订单：状态、金额、时间、客户、商品
- 物流：承运商、运单号、最新状态、轨迹节点
- 售后：类型、状态、原因、金额、更新时间
- 会话：会话状态、消息、客服响应能力
- 工件：平台侧"真相快照"
- 推送：平台主动触发的 payload

---

## 4. P0 与 P1 范围定义

### 4.1 P0 必须实现的平台
- taobao
- douyin_shop
- wecom_kf

### 4.2 P0 只做骨架的平台
- jd
- xhs
- kuaishou

### 4.3 P0 统一要求
P0 平台必须具备：

1. profile
2. state machine
3. fixtures
4. artifact builder
5. push/callback emitter（若平台需要）
6. error injector
7. pytest 覆盖
8. README 示例

---

## 5. 平台细化

---

### 5.1 Taobao

#### 5.1.1 平台定位
淘宝在 official-sim 中代表"主/子订单 + 正向交易状态 + 订单推送 + 最小逆向售后"的典型电商平台。

#### 5.1.2 P0 必做能力
- trade/order 主子结构
- 正向交易状态机
- 最小退款/售后状态机
- trade detail artifact
- shipment artifact
- refund artifact
- push artifact
- 常见错误注入

#### 5.1.3 P0 不做
- 全量 type 场景
- 全量履约细节
- 全量 hold 单逻辑
- 全量家装/保税/海外直邮
- 全量子单差异发货逻辑

#### 5.1.4 与 unified 的映射重点
- `trade.tid` -> `Order.orderId`
- `order.oid` -> `OrderItem.itemOrderId` 或 `extra.subOrderId`
- `trade.status` -> `Order.status`
- `orders[].status` -> `OrderItem.itemStatus`
- `refund/rights state` -> `AfterSale.status`

#### 5.1.5 P0 关键 artifact
- trade_detail
- shipment_snapshot
- refund_snapshot
- rds_push_trade_changed
- rds_push_refund_changed

#### 5.1.6 P0 关键错误
- token_expired
- resource_not_found
- duplicate_push
- out_of_order_push
- invalid_trade_status_transition

---

### 5.2 Douyin Shop

#### 5.2.1 平台定位
抖店在 official-sim 中代表"强签名 + 主动消息推送 + 订单/退款状态分域"的典型平台。

#### 5.2.2 P0 必做能力
- 订单状态机
- 退款状态机
- push artifact
- ack 记录
- sign 校验失败
- token / permission 错误

#### 5.2.3 P0 不做
- 商品全量状态机
- 全量店铺权限模型
- 全量多订阅主题
- 全量物流细节

#### 5.2.4 与 unified 的映射重点
- `orderId` -> `Order.orderId`
- `refund.afterSaleId` -> `AfterSale.afterSaleId`
- `refundStatus` -> `AfterSale.status`
- `refundType` -> `AfterSale.type`
- push payload -> `PushEvent`

#### 5.2.5 P0 关键 artifact
- order_detail
- refund_detail
- push_order_status_changed
- push_refund_status_changed
- signature_error_payload

#### 5.2.6 P0 关键错误
- invalid_signature
- token_expired
- permission_denied
- duplicate_push
- invalid_ack
- timestamp_out_of_window

---

### 5.3 WeCom KF

#### 5.3.1 平台定位
企微客服在 official-sim 中代表"消息/事件回调 + 会话状态流转 + 事件响应消息"的客服场景平台。

#### 5.3.2 P0 必做能力
- callback artifact
- sync_msg artifact
- send_msg_on_event artifact
- service_state artifact
- conversation state machine
- msg_code / code 类错误

#### 5.3.3 P0 不做
- 全量消息类型
- 全量客户工具栏能力
- 全量智能助手能力
- 全量客服管理后台配置能力

#### 5.3.4 与 unified 的映射重点
- `open_kfid` -> `Conversation.platformAccountId`
- `external_userid` -> `Customer.platformUserId`
- callback/sync_msg payload -> `Message[]`
- service_state -> `Conversation.status`

#### 5.3.5 P0 关键 artifact
- callback_event
- sync_msg_page
- event_message_result
- service_state_change

#### 5.3.6 P0 关键错误
- access_token_invalid
- invalid_cursor
- msg_code_expired
- conversation_closed
- send_message_failed

---

### 5.4 JD

#### 5.4.1 平台定位
京东在 official-sim 中代表"订单 / 物流 / 售后分域清晰、查询型行为较强"的平台。

#### 5.4.2 P0 只做骨架
- platform profile skeleton
- route skeleton
- enum skeleton
- fixture directory skeleton

#### 5.4.3 P1 候选
- order detail
- shipment detail
- after-sale detail
- 发货动作
- 物流轨迹节点

---

### 5.5 XHS

#### 5.5.1 平台定位
小红书在 official-sim 中代表"订单列表轮询 + 详情补拉 + 收件人/海关信息拆分"的平台。

#### 5.5.2 P0 只做骨架
- route skeleton
- profile skeleton
- fixtures skeleton

#### 5.5.3 P1 候选
- order list polling
- order detail
- receiver detail
- customs detail
- aftersale review / confirm-receipt

---

### 5.6 Kuaishou

#### 5.6.1 平台定位
快手在 official-sim 中代表"商品/订单/退款/物流/客服管理分域"的平台。

#### 5.6.2 P0 只做骨架
- route skeleton
- profile skeleton
- fixture skeleton

#### 5.6.3 P1 候选
- order detail
- refund detail
- logistics detail
- customer message / card
- product detail

---

## 6. 实现优先级

### P0
1. taobao
2. douyin_shop
3. wecom_kf

### P1
4. xhs
5. jd

### P2
6. kuaishou

---

## 7. 统一错误类别

所有平台错误都应该先映射到以下统一分类：

- auth_error
- signature_error
- permission_error
- not_found
- rate_limited
- invalid_state_transition
- duplicate_push
- out_of_order_push
- callback_ack_error
- conversation_error
- internal_error

---

## 8. Codex 执行限制

实现 platform profile 时必须遵守：

1. 不得臆造未明确的平台事实。
2. 不确定字段放 `extra` 或 TODO，不得写死为"官方一定如此"。
3. 每个平台至少先做 success / edge_case / error_case 三类 fixture。
4. 每个平台必须先有 state machine，再写 route 行为。
5. route 返回必须由 service / state machine / fixture 组合生成，不允许直接写死随机 JSON。

---

## 9. 完成定义

某个平台 profile 只有在以下条件全部满足时才算完成：

1. profile 已存在
2. state machine 已存在
3. fixtures 已存在
4. artifacts builder 已存在
5. error injector 已存在
6. pytest 通过
7. README 示例齐全
