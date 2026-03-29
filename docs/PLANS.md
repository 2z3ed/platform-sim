# PLANS.md

## 0. 目标

在现有多平台客服中台项目上，新增一个 `official-sim-server`，用于模拟平台官方 API 返回、callback、webhook、状态推进与错误注入行为；同时保持当前 `/mock/...` 和 `/mock/unified/...` 契约不被破坏。

P0 范围：

- 建立 `official-sim-server`
- 落第一批核心表
- 实现 run lifecycle
- 实现 artifacts / snapshots / push events
- 完成 taobao / douyin_shop / wecom_kf 三个平台 P0 profile
- 提供最小接入与最小测试覆盖

---

## 1. 全局执行规则

### 1.1 Stop-and-fix
若任一 milestone 的验证失败，必须先修复，再进入下一 milestone。

### 1.2 不跨阶段大改
每个 milestone 只做本阶段目标内的事情，不顺手重构整个仓库。

### 1.3 保守扩展
优先新增模块，不破坏现有模块 public interface。

### 1.4 决策留痕
所有重大实现分歧都要写到 decision notes。

---

## 2. Milestone 列表

### M1: 建立 official-sim-server 工程骨架 ✅ DONE

#### 目标
创建新应用目录与最小可启动 FastAPI 服务。

#### 输出
- [x] `apps/official-sim-server/`
- [x] `app/main.py`
- [x] `app/api/router.py`
- [x] `app/api/routes/runs.py`
- [x] `app/core/*`
- [x] `README.md`

#### 验收标准
- [x] 服务可启动
- [x] `/healthz` 或等价健康检查可返回成功
- [x] `POST /official-sim/runs` 有最小 stub
- [x] 项目基础测试框架可运行

#### 验证命令
- 启动应用命令
- 健康检查 curl
- pytest smoke tests

#### 决策说明
- 先不接数据库，只保留内存 / stub 版本也可
- 路由和 service 分层必须到位

#### 完成信息
- **完成时间**: 2026-03-29
- **Commit**: d42bc0c
- **验证结果**: 服务可启动，healthz 返回正常

---

### M2: 建立数据库与迁移基础 ✅ DONE

#### 目标
引入 DB migration，落第一批核心表。

#### 输出
- [x] migration 配置
- [x] 第一批核心表 migration
- [x] repository skeleton

#### 涉及表
- [x] simulation_runs
- [x] simulation_events
- [x] state_snapshots
- [x] push_events
- [x] artifacts
- [x] evaluation_reports

#### 验收标准
- [x] migration 可执行
- [x] migration 可回滚
- [x] repository 最小 CRUD 跑通
- [ ] pytest 覆盖最小 DB smoke tests

#### 验证命令
- migrate up
- migrate down
- pytest db smoke tests

#### 决策说明
- 第二批业务表暂缓
- 先把 run / artifact / event 链条打通
- 使用 SQLite 作为本地开发数据库（PostgreSQL 未运行）
- DB URL: sqlite:////home/kkk/Project/platform-sim/apps/official-sim-server/official_sim.db

#### 完成信息
- **完成时间**: 2026-03-29
- **验证结果**: 6 张表创建成功，up/down 验证通过
- **注意**: pytest db smoke tests 待补充

---

### M3: 实现 run 生命周期 ✅ DONE

#### 目标
实现 run 的创建、查询、推进。

#### 输出
- `POST /official-sim/runs`
- `GET /official-sim/runs/{run_id}`
- `POST /official-sim/runs/{run_id}/advance`

#### 状态
最少包括：
- created
- running
- paused
- completed
- failed

#### 验收标准
- run 创建成功
- advance 后 step_no 增长
- state_snapshot 被记录
- simulation_event 被记录
- 非法状态推进有稳定错误

#### 验证命令
- pytest run lifecycle
- curl create/get/advance

#### 决策说明
- 先实现 deterministic advance，不引入复杂 scheduler

---

### M4: 实现 artifacts / snapshots / push events ✅ DONE

#### 目标
让 run 能产出"平台侧工件"。

#### 输出
- artifact builder
- push dispatcher
- `GET /official-sim/runs/{run_id}/artifacts`
- `POST /official-sim/runs/{run_id}/replay-push`
- fixtures/ 目录和 JSON 文件

#### 工件类型
至少包含：
- api_response_snapshot
- callback_payload
- webhook_payload
- message_sync_payload
- error_response_payload

#### Fixtures 规范 ✅ DONE (P0 审计补充)
- `fixtures/taobao/success/` - 6 个 JSON 文件
- `fixtures/taobao/edge_case/` - 2 个 JSON 文件
- `fixtures/taobao/error_case/` - 4 个 JSON 文件
- `fixtures/douyin_shop/success/` - 7 个 JSON 文件
- `fixtures/douyin_shop/error_case/` - 2 个 JSON 文件
- `fixtures/wecom_kf/success/` - 3 个 JSON 文件
- `fixtures/wecom_kf/error_case/` - 2 个 JSON 文件
- fixture consistency pytest 测试 (114 passed)

#### 验收标准
- 每次 advance 后至少可产出一种 artifact
- push event 可以查询
- replay-push 能重新触发一条已存在事件
- artifact 与当前 step 绑定

#### 验证命令
- pytest artifact tests
- pytest push replay tests

#### 决策说明
- push 先做"记录 + 回放"，暂不做真实异步派发系统

---

### M5: 实现 taobao P0 profile ✅ DONE

#### 目标
实现淘宝 P0 平台 profile。

#### 范围
- trade/order 正向状态机
- 基础退款逆向状态
- 订单推送工件
- 常见错误注入

#### 最低接口能力
- 订单详情工件
- 物流工件
- 退款工件
- push 工件

#### 最低错误
- token_expired
- resource_not_found
- duplicate_push
- out_of_order_push

#### 验收标准
- 可创建淘宝 run
- 可从 wait_pay -> wait_ship -> shipped -> finished
- 可产出 push artifact
- 可注入至少 2 类错误
- pytest 覆盖状态转移

#### 验证命令
- pytest taobao profile
- fixture consistency tests

---

### M6: 实现 douyin_shop P0 profile ✅ DONE

#### 目标
实现抖店 P0 平台 profile。

#### 范围
- 订单状态
- 退款状态
- 推送验证
- 签名相关错误

#### 最低能力
- 订单工件
- 退款工件
- push 工件
- sign 校验失败工件

#### 最低错误
- invalid_signature
- token_expired
- permission_denied
- duplicate_push

#### 验收标准
- 可创建抖店 run
- 可生成订单 / 退款推送工件
- 签名错误测试覆盖
- push ack 流程最小可用

#### 验证命令
- pytest douyin profile
- pytest push signature tests

---

### M7: 实现 wecom_kf P0 profile ✅ DONE

#### 目标
实现企微客服 P0 平台 profile。

#### 范围
- callback -> sync_msg -> send_msg_on_event 链路
- 会话状态变更
- msg_code / code 失效类错误

#### 最低能力
- callback 工件
- sync_msg 工件
- event_message 工件
- conversation state 工件

#### 最低错误
- access_token_invalid
- msg_code_expired
- conversation_closed
- invalid_cursor

#### 验收标准
- 可创建企微 run
- 可推进会话状态
- 可模拟 callback 后拉消息
- 可模拟事件消息发送成功/失败
- pytest 覆盖链路

#### 验证命令
- pytest wecom profile
- pytest callback_sync_chain tests

---

### M8: unified/provider 最小接入 ✅ DONE

#### 目标
让 official-sim 能通过最小 adapter 喂给现有 unified / provider。

#### 输出
- integration adapter
- 示例接入文档
- 最小端到端测试

#### 验收标准
- official-sim 产物可映射到 unified 所需最小对象
- 不破坏现有 `/mock/unified/...`
- 至少一个端到端流程跑通

#### 验证命令
- pytest integration e2e

---

### M9: 错误注入与评估报告 ✅ DONE

#### 目标
实现 inject-error 和 report。

#### 输出
- `POST /official-sim/runs/{run_id}/inject-error`
- `GET /official-sim/runs/{run_id}/report`

#### 报告内容
- run summary
- steps
- artifacts
- injected errors
- expected vs actual
- open issues

#### 验收标准
- 错误注入后状态一致
- report 可生成结构化结果
- 至少覆盖 5 类常见错误

#### 验证命令
- pytest error injector
- pytest report generation

---

### M10: README / 示例 / 交付清理 ✅ DONE

#### 目标
补齐开发者使用说明与示例。

#### 输出
- `apps/official-sim-server/README.md`
- curl 示例
- fixture 示例
- migration 说明
- known limitations

#### 验收标准
- 新人按 README 能本地跑起来
- 至少有 3 条 curl 示例
- 至少有 1 条端到端场景示例
- 已知限制明确写出

#### 验证命令
- 文档 smoke walkthrough
- README 命令人工复现

---

## 3. P0 平台范围声明

P0 仅对以下平台做可运行 profile：

- taobao
- douyin_shop
- wecom_kf

以下平台只允许建立占位 profile / skeleton，不做完整实现：

- jd
- xhs
- kuaishou

---

## 4. 每阶段统一输出格式

每个 milestone 完成后，必须输出：

1. 改动文件列表
2. 新增命令
3. 通过的测试列表
4. 未解决问题
5. 下一阶段建议
6. decision notes

---

## 5. 风险控制

### 风险 1：模型臆造平台细节
处理：
- 不确定时写 TODO
- 使用 fixture + test 锁行为
- 不发明官方事实

### 风险 2：过度追求拟真
处理：
- 只做 P0 最小状态机
- 只做高频错误
- 先可跑再细化

### 风险 3：和现有模块耦合过深
处理：
- 通过 adapter 集成
- 不改 existing public interface
- 尽量新建模块

### 风险 4：测试不稳定
处理：
- 优先 deterministic tests
- 禁止依赖真实网络
- fixture 固定版本

---

## 6. 通过标准（P0 Exit Criteria）

P0 只有在以下全部满足时才算完成：

- official-sim-server 可独立启动
- 第一批核心表 migration 通过
- run / advance / artifact / replay / report 全部可用
- taobao / douyin_shop / wecom_kf 三个平台 P0 profile 可运行
- 至少一个 unified/provider 端到端接入用例通过
- README 可让新人本地跑通
- 所有关键 pytest 通过
