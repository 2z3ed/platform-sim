# Error Matrix

## 1. 文档目的

本文档定义 official-sim P0 阶段必须支持的错误类型、错误归类、错误响应结构、注入方式、可重试性和测试要求。

本文件是 Codex 实现 error injector、route error handling、evaluation report 的直接规范。

---

## 2. 统一错误设计原则

### 2.1 错误分层
所有错误分为 4 层：

1. protocol layer
   - token
   - signature
   - timestamp
   - permission
2. resource layer
   - not found
   - empty result
   - invalid cursor
3. business layer
   - invalid state transition
   - conversation closed
   - msg code expired
   - duplicate push
   - out of order push
4. system layer
   - rate limited
   - internal error
   - dependency unavailable

### 2.2 错误输出结构
所有 route 错误最少返回：

- `code`
- `message`
- `request_id`
- `error_type`
- `retryable`
- `details`

### 2.3 错误记录要求
所有错误都必须：
- 写入 simulation_events
- 必要时产出 error artifact
- 可出现在 evaluation report
- 与 run_id / step_no 绑定

### 2.4 错误注入方式
P0 统一支持 3 种注入方式：

1. run 级别
2. step 级别
3. next-call 级别

---

## 3. 统一错误码命名规范

命名统一为小写 snake_case，例如：

- token_expired
- invalid_signature
- timestamp_out_of_window
- permission_denied
- resource_not_found
- invalid_state_transition
- duplicate_push
- out_of_order_push
- invalid_cursor
- msg_code_expired
- conversation_closed
- rate_limited
- internal_error

---

## 4. 统一错误矩阵

| error_code | error_type | http_status | retryable | 默认注入范围 | 必须产出 artifact |
|---|---|---:|---:|---|---:|
| token_expired | auth_error | 401 | 是 | next-call / run | 是 |
| invalid_signature | signature_error | 401 | 否 | next-call | 是 |
| timestamp_out_of_window | signature_error | 400 | 否 | next-call | 是 |
| permission_denied | permission_error | 403 | 否 | run / next-call | 是 |
| resource_not_found | not_found | 404 | 否 | next-call | 是 |
| invalid_cursor | resource_error | 400 | 否 | next-call | 是 |
| invalid_state_transition | business_error | 409 | 否 | step | 是 |
| duplicate_push | push_error | 200/202 | 是 | step | 否（可选） |
| out_of_order_push | push_error | 200/202 | 是 | step | 否（可选） |
| invalid_ack | push_error | 400 | 是 | step | 是 |
| msg_code_expired | business_error | 400 | 否 | next-call | 是 |
| conversation_closed | business_error | 409 | 否 | run / next-call | 是 |
| rate_limited | system_error | 429 | 是 | next-call | 是 |
| internal_error | system_error | 500 | 是 | run / next-call | 是 |

---

## 5. 平台专属错误矩阵

### 5.1 Taobao

#### 必须支持
- token_expired
- resource_not_found
- invalid_state_transition
- duplicate_push
- out_of_order_push

#### 说明
- `resource_not_found` 可作用于 tid / refund_id
- `invalid_state_transition` 作用于 trade 或 refund
- `duplicate_push` / `out_of_order_push` 主要作用于 RDS 类工件

#### 推荐 response 示例
```json
{
  "code": "resource_not_found",
  "message": "trade not found",
  "request_id": "req_xxx",
  "error_type": "not_found",
  "retryable": false,
  "details": {
    "platform": "taobao",
    "resource_type": "trade",
    "resource_id": "123456"
  }
}
```

### 5.2 Douyin Shop

#### 必须支持
- token_expired
- invalid_signature
- timestamp_out_of_window
- permission_denied
- duplicate_push
- invalid_ack
- invalid_state_transition

#### 说明
- invalid_signature 作用于 API 调用和 push 验签
- timestamp_out_of_window 作用于带时间戳验证的请求
- invalid_ack 作用于 push 接收确认

#### 推荐 response 示例
```json
{
  "code": "invalid_signature",
  "message": "signature verification failed",
  "request_id": "req_xxx",
  "error_type": "signature_error",
  "retryable": false,
  "details": {
    "platform": "douyin_shop",
    "sign_method": "hmac-sha256",
    "expected": "xxx",
    "provided": "yyy"
  }
}
```

### 5.3 WeCom KF

#### 必须支持
- access_token_invalid
- invalid_cursor
- msg_code_expired
- conversation_closed
- send_message_failed
- invalid_state_transition

#### 说明
- access_token_invalid 在内部统一映射到 token_expired 或 auth_error
- invalid_cursor 作用于 sync_msg
- msg_code_expired 作用于 send_msg_on_event
- conversation_closed 作用于结束态之后继续发消息

#### 推荐 response 示例
```json
{
  "code": "msg_code_expired",
  "message": "msg code expired",
  "request_id": "req_xxx",
  "error_type": "business_error",
  "retryable": false,
  "details": {
    "platform": "wecom_kf",
    "conversation_id": "conv_xxx",
    "open_kfid": "kf_xxx"
  }
}
```

---

## 6. Error Artifact 规范

所有"必须产出 artifact"的错误都要生成一份 error artifact。

### 6.1 通用字段
- artifact_id
- run_id
- step_no
- platform
- artifact_type = error_response_payload
- error_code
- error_type
- payload
- created_at

### 6.2 payload 最少字段
- request
- expected_behavior
- actual_behavior
- retryable
- injected_by
- trace

---

## 7. Error Injection API 约束

接口：
`POST /official-sim/runs/{run_id}/inject-error`

入参最少字段：
- error_code
- injection_scope
- target
- active_until
- options

scope 枚举：
- next_call
- current_step
- whole_run

target 示例：
- platform.auth
- taobao.trade.detail
- douyin.push.verify
- wecom.sync_msg

---

## 8. Evaluation Report 中的错误表现

report 至少要列出：

- injected_errors[]
- observed_errors[]
- expected_vs_actual
- retry_suggestion
- open_issues

如果发生以下情况，必须在 report 中高亮：

- duplicate_push
- out_of_order_push
- invalid_signature
- msg_code_expired
- invalid_state_transition

---

## 9. Pytest 最低覆盖

必须存在：

1. 每个统一错误码至少一个 route test
2. 每个平台至少 3 个平台专属错误测试
3. inject-error API 测试
4. error artifact 生成测试
5. evaluation report 错误呈现测试
6. retryable 标记测试
7. fixture consistency 测试

---

## 10. P0 完成定义

error matrix 只有在以下全部满足时算完成：

- 统一错误码枚举存在
- 统一错误响应 schema 存在
- inject-error API 可用
- 关键错误可注入
- error artifact 可生成
- pytest 覆盖通过
