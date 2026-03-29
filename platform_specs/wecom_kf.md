# Platform Spec - WeCom KF

## 1. 平台定位

企业微信客服在 official-sim 中代表：
- 事件回调优先
- 消息需通过 sync_msg 拉取
- 会话状态流转重要
- event message 依赖 code / msg_code 语义

P0 目标是：
- callback -> sync_msg -> event message 链路可运行
- 会话状态可推进
- 错误可注入
- 与 unified/AI 联调场景可支撑

---

## 2. P0 必须实现的 endpoints

### 2.1 run 侧
- `POST /official-sim/runs`
- `GET /official-sim/runs/{run_id}`
- `POST /official-sim/runs/{run_id}/advance`
- `GET /official-sim/runs/{run_id}/artifacts`
- `POST /official-sim/runs/{run_id}/inject-error`
- `GET /official-sim/runs/{run_id}/report`

### 2.2 平台侧
- `POST /official-sim/wecom-kf/token`
- `POST /official-sim/wecom-kf/callback`
- `POST /official-sim/wecom-kf/messages/sync`
- `POST /official-sim/wecom-kf/service-state/trans`
- `POST /official-sim/wecom-kf/event-message/send`
- `GET /official-sim/wecom-kf/conversations/{external_userid}`

---

## 3. P0 必须实现的状态

### 3.1 会话状态
- NEW
- QUEUED
- ACTIVE
- TRANSFERRED
- ENDED

### 3.2 事件类型（最小）
- user_message
- enter_session
- session_status_change
- msg_send_fail

---

## 4. P0 必须实现的 artifact

- conversation_snapshot
- callback_event
- sync_msg_page
- service_state_change
- event_message_result
- error_response_payload

---

## 5. P0 必须实现的错误

- access_token_invalid
- invalid_cursor
- msg_code_expired
- conversation_closed
- send_message_failed
- invalid_conversation_state_transition

---

## 6. Unified 映射要求

### 6.1 Conversation
- `open_kfid` -> `platformAccountId`
- `external_userid` -> `Customer.platformUserId`
- `service state` -> `Conversation.status`

### 6.2 Message
- callback / sync_msg payload -> `Message[]`
- 文本消息至少标准化为 text 类型

### 6.3 Suggestion 场景
P0 应支持最小联调：
- 用户发消息
- unified 拿到消息
- AI 生成建议回复
- 是否转人工由上层判断

---

## 7. P0 不做

- 全量消息类型
- 全量企业微信客服后台功能
- 全量欢迎语 / 结束语细节
- 多客服复杂排班
- 完整 48 小时窗口策略细化

---

## 8. Fixtures 清单

至少包括：

- `callback_enter_session.json`
- `callback_user_message.json`
- `sync_msg_page1.json`
- `event_message_success.json`
- `service_state_active.json`
- `invalid_cursor.json`
- `msg_code_expired.json`
- `conversation_closed.json`
- `send_message_failed.json`

---

## 9. 测试要求

至少包括：

- NEW -> QUEUED -> ACTIVE 测试
- ACTIVE -> TRANSFERRED -> ACTIVE 测试
- ACTIVE -> ENDED 测试
- callback -> sync_msg 链路测试
- send_msg_on_event 成功/失败测试
- invalid_cursor 测试
- conversation_closed 测试
- route schema 测试
- fixture consistency 测试

---

## 10. Known Limitations

P0 WeCom KF profile 只保证：
- 会话链路合理
- callback/sync/event_message 可联调
- 错误可注入
- 工件可审计
- 不追求全量企业微信客服协议细节
