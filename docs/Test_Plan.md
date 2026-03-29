# Test Plan

## 1. 文档目的

本文档定义 official-sim P0 阶段的测试分层、测试目标、测试命令、覆盖边界和 stop-and-fix 规则。

本文件是 Codex 编写测试与执行验证命令的直接依据。

---

## 2. 总体测试原则

P0 的测试目标不是覆盖所有平台所有字段，而是保证：

1. 核心 run 生命周期正确
2. 状态机转移正确
3. artifacts / push events 可生成
4. 错误注入可生效
5. fixtures 稳定
6. integration 最小闭环可跑通

---

## 3. 测试分层

### 3.1 Unit Tests
目标：
- 测 state machine
- 测 validator
- 测 artifact builder
- 测 error injector
- 测 repository 纯逻辑

目录建议：
- `tests/unit/`

### 3.2 API Route Tests
目标：
- 测 FastAPI routes
- 测响应 schema
- 测错误返回
- 测依赖注入与 service 调用边界

目录建议：
- `tests/api/`

### 3.3 Integration Tests
目标：
- 测 route -> service -> repo -> artifact 链路
- 测 push replay
- 测 inject-error
- 测 unified/provider 最小 adapter

目录建议：
- `tests/integration/`

### 3.4 Fixture Consistency Tests
目标：
- 测 fixture 命名
- 测 fixture meta
- 测 fixture schema
- 测 fixture completeness

目录建议：
- `tests/fixtures/`

### 3.5 Migration Smoke Tests
目标：
- migration up/down
- 表存在性
- 基础索引存在性

目录建议：
- `tests/migrations/`

### 3.6 Optional Async Tests
如果 official-sim 使用异步 DB / async service，则增加：
- `tests/async/`

---

## 4. 工具与方法

### 4.1 FastAPI
使用：
- `TestClient` 测同步 API
- 若测试本身为 async，则使用 HTTPX/AnyIO 方案

### 4.2 pytest
使用：
- `conftest.py` 统一 fixture
- marker 区分：
  - unit
  - api
  - integration
  - fixture
  - migration
  - slow

### 4.3 数据库
使用独立测试数据库或临时 schema。

### 4.4 fixture
所有测试引用 platform fixture 时，优先通过 helper / loader，不直接手敲路径字符串。

---

## 5. 必测范围

### 5.1 Run Lifecycle
必须测试：
- create run
- get run
- advance run
- invalid state transition
- missing run
- report generation

### 5.2 Artifact & Push
必须测试：
- artifact list
- push event creation
- replay push
- duplicate push
- out_of_order push
- invalid ack

### 5.3 Error Injection
必须测试：
- inject-error API
- token_expired
- invalid_signature
- resource_not_found
- invalid_cursor
- msg_code_expired
- conversation_closed

### 5.4 Platform Profiles
必须测试：

#### Taobao
- 正向状态链路
- 关闭单
- 部分发货
- 退款链路
- push artifact

#### Douyin Shop
- 订单链路
- 退款链路
- push 签名
- ack 记录
- timestamp 错误

#### WeCom KF
- NEW -> QUEUED -> ACTIVE
- callback -> sync_msg
- transfer -> active
- ended 后发消息失败
- invalid_cursor

### 5.5 Fixture Contract
必须测试：
- 命名规范
- meta 字段
- schema 校验
- canonical fixture 存在

### 5.6 Migration
必须测试：
- migration up
- migration down
- 表存在
- 基础索引存在

---

## 6. 推荐测试命令

以下命令是规范，不要求你必须使用完全相同的脚本名称，但必须有等价能力。

### 6.1 全量测试
```bash
pytest
```

### 6.2 unit tests
```bash
pytest -m unit
```

### 6.3 api tests
```bash
pytest -m api
```

### 6.4 integration tests
```bash
pytest -m integration
```

### 6.5 fixture tests
```bash
pytest -m fixture
```

### 6.6 migration tests
```bash
pytest -m migration
```

### 6.7 单个平台 profile
```bash
pytest tests/unit/platforms/taobao
pytest tests/unit/platforms/douyin_shop
pytest tests/unit/platforms/wecom_kf
```

---

## 7. 每个 Milestone 的必跑验证

### M1 完成后
- health route smoke test
- create run stub test

### M2 完成后
- migration up/down
- repository smoke tests

### M3 完成后
- run lifecycle tests
- invalid transition tests

### M4 完成后
- artifact tests
- replay push tests

### M5 完成后
- taobao profile tests
- taobao fixture tests

### M6 完成后
- douyin profile tests
- push signature tests

### M7 完成后
- wecom chain tests
- wecom fixture tests

### M8 完成后
- integration e2e tests

### M9 完成后
- inject-error tests
- report tests

### M10 完成后
- README smoke walkthrough

---

## 8. Stop-and-fix 规则

出现以下任一情况，必须停止进入下一阶段，先修复：

- migration 失败
- run lifecycle 失败
- state machine 测试失败
- fixture consistency 失败
- route schema 失败
- 关键 integration case 失败

禁止带着红测进入下个 milestone。

---

## 9. 覆盖建议

P0 不强制写死总代码覆盖率百分比，但要求：

- 核心 domain/service/state machine 重点覆盖
- platform profiles 的主链路覆盖
- error injectors 有显式测试
- route 层不追求机械覆盖率，重点验证 schema 与关键错误

如果项目已有覆盖率门槛，则遵守现有门槛。

---

## 10. 测试数据规则

### 10.1 隔离
测试数据必须隔离，不得污染开发环境数据。

### 10.2 可重复
所有测试应可重复执行，不能依赖真实网络和随机外部状态。

### 10.3 固定时钟
若逻辑依赖时间，建议使用可注入 clock。

### 10.4 固定 ID
关键测试建议使用 deterministic ID 生成器或 test helper。

---

## 11. CI 建议

P0 阶段推荐 CI 流程：

1. lint / format check
2. unit tests
3. api tests
4. fixture tests
5. migration tests
6. integration tests

若 integration tests 较慢，可分阶段运行，但 fixture / migration 不能跳过。

---

## 12. P0 完成定义

test plan 只有在以下全部满足时完成：

- marker 约定建立
- 基础测试目录建立
- milestone 对应测试存在
- fixture consistency tests 存在
- migration smoke tests 存在
- 三个平台 profile tests 存在
- integration 最小闭环存在
