# State Machine - WeCom KF

## 1. 文档目的

定义企业微信客服（WeCom KF）P0 阶段在 official-sim 中的会话状态机、callback / sync / event message 行为与错误注入规则。

本文件是 `platforms/wecom_kf/` 的执行规范。

---

## 2. 设计目标

WeCom KF P0 只模拟以下行为：

1. 开启 API 后的消息/事件回调视角
2. callback artifact
3. sync_msg artifact
4. send_msg_on_event artifact
5. service_state 变更
6. 会话状态机
7. msg_code / cursor / token 类错误

P0 不追求全量消息类型与后台管理能力。

---

## 3. 核心对象

### 3.1 Conversation
最少字段：
- conversation_id
- open_kfid
- external_userid
- state
- assigned_servicer
- created_at
- updated_at

### 3.2 CallbackEvent
最少字段：
- event_type
- open_kfid
- external_userid
- cursor
- occurred_at
- payload

### 3.3 SyncMsgPage
最少字段：
- cursor
- has_more
- msg_list[]

### 3.4 EventMessage
最少字段：
- msgid
- open_kfid
- external_userid
- msgtype
- content
- send_result

---

## 4. 会话状态机

### 4.1 状态枚举
- NEW
- QUEUED
- ACTIVE
- TRANSFERRED
- ENDED

### 4.2 P0 允许链路
- NEW -> QUEUED
- QUEUED -> ACTIVE
- ACTIVE -> TRANSFERRED
- TRANSFERRED -> ACTIVE
- ACTIVE -> ENDED
- QUEUED -> ENDED

### 4.3 非法转移
- ENDED -> ACTIVE
- ENDED -> TRANSFERRED
- NEW -> TRANSFERRED

错误类型：
- invalid_conversation_state_transition

---

## 5. 消息/事件链路

### 5.1 callback
用途：
- 表示平台向企业侧发送了消息或事件通知

P0 最少支持以下 callback 类型：
- user_message
- enter_session
- session_status_change
- msg_send_fail

### 5.2 sync_msg
用途：
- 拉取当前会话相关消息页

P0 最小行为：
- 由 callback 驱动 cursor 变化
- 可返回一页消息
- 支持 has_more = false/true

### 5.3 send_msg_on_event
用途：
- 基于特定事件上下文返回发送结果

P0 最小行为：
- 成功发送
- 会话已结束发送失败
- msg_code 过期发送失败

### 5.4 service_state/trans
用途：
- 改变会话服务状态 / 转接

P0 最小行为：
- queued -> active
- active -> transferred
- transferred -> active
- active -> ended

---

## 6. 触发动作（actions）

### 6.1 create_conversation
效果：
- 创建会话
- state = NEW
- 产出 artifact:
  - conversation_snapshot

### 6.2 enter_queue
前置条件：
- state == NEW

效果：
- state -> QUEUED
- 产出 artifact:
  - callback_event
  - service_state_change

### 6.3 assign_servicer
前置条件：
- state == QUEUED

效果：
- state -> ACTIVE
- 产出 artifact:
  - callback_event
  - service_state_change

### 6.4 receive_user_message
前置条件：
- state in [QUEUED, ACTIVE]

效果：
- 产生一条消息
- 更新 cursor
- 产出 artifact:
  - callback_event
  - sync_msg_page

### 6.5 transfer_conversation
前置条件：
- state == ACTIVE

效果：
- state -> TRANSFERRED
- 产出 artifact:
  - callback_event
  - service_state_change

### 6.6 accept_transfer
前置条件：
- state == TRANSFERRED

效果：
- state -> ACTIVE
- 产出 artifact:
  - service_state_change

### 6.7 end_conversation
前置条件：
- state in [QUEUED, ACTIVE, TRANSFERRED]

效果：
- state -> ENDED
- 产出 artifact:
  - callback_event
  - service_state_change

### 6.8 send_event_message
前置条件：
- state in [QUEUED, ACTIVE]
- msg_code 有效

效果：
- 发送结果成功
- 产出 artifact:
  - event_message_result

若不满足条件：
- 产出错误 artifact

---

## 7. Artifact 规则

### 7.1 conversation_snapshot
最少包含：
- conversation_id
- open_kfid
- external_userid
- state
- assigned_servicer

### 7.2 callback_event
最少包含：
- event_type
- open_kfid
- external_userid
- cursor
- occurred_at
- payload

### 7.3 sync_msg_page
最少包含：
- cursor
- next_cursor
- has_more
- msg_list[]

### 7.4 service_state_change
最少包含：
- open_kfid
- external_userid
- old_state
- new_state
- operated_at

### 7.5 event_message_result
最少包含：
- msgid
- send_result
- msgtype
- open_kfid
- external_userid

---

## 8. Error Injector 规则

P0 必须支持：

### 8.1 access_token_invalid
效果：
- token 相关请求失败

### 8.2 invalid_cursor
效果：
- sync_msg 请求 cursor 非法

### 8.3 msg_code_expired
效果：
- send_msg_on_event 失败

### 8.4 conversation_closed
效果：
- 会话结束后不能继续发送事件消息

### 8.5 send_message_failed
效果：
- 人为注入消息发送失败场景
- 生成 msg_send_fail callback artifact

---

## 9. Fixtures 规范

目录结构：

fixtures/wecom_kf/
  success/
    callback_enter_session.json
    callback_user_message.json
    sync_msg_page1.json
    event_message_success.json
    service_state_active.json
  edge_case/
    transfer_then_accept.json
    conversation_end_before_reply.json
  error_case/
    access_token_invalid.json
    invalid_cursor.json
    msg_code_expired.json
    send_message_failed.json

---

## 10. Pytest 最低覆盖

必须存在：

1. NEW -> QUEUED -> ACTIVE 链路测试
2. ACTIVE -> TRANSFERRED -> ACTIVE 测试
3. ACTIVE -> ENDED 测试
4. callback -> sync_msg 链路测试
5. send_msg_on_event 成功/失败测试
6. invalid_cursor 测试
7. conversation_closed 测试
8. route 测试
9. fixture consistency 测试

---

## 11. P0 完成定义

WeCom KF profile 只有在以下全部满足时完成：

- 会话状态机可运行
- callback/sync/event_message 工件可生成
- service_state 变更可表示
- 4 类关键错误可注入
- README 样例可运行
- pytest 全绿
