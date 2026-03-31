# Platform-Sim: 多平台官方行为仿真层

[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 项目简介

Platform-Sim 是一个**多平台官方行为仿真层 + 客服中台统一层**，核心价值在于：**在没有真实官方 API 和真实用户的情况下，仍能完整开发、测试、联调客服中台系统。**

### 核心架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    完整客服中台系统（可正常开发）                    │
│                                                                 │
│  User Intent ──→ User Agent ──→ official-sim-server             │
│     (用户输入)   (翻译成API调用)   (扮演官方平台)                   │
│                          │              ↓                        │
│                          │         Unified Layer                 │
│                          │              ↓                        │
│                          └────→ AI Orchestrator                  │
│                                     ↓                           │
│                                 前端/坐席工作台                    │
└─────────────────────────────────────────────────────────────────┘
              ↑ 全程不需要真实用户和真实官方API
```

### 两个独立职责

1. **User Agent（AI Orchestrator 内部模块）**
   - 输入：用户的自然语言（"我要退款"、"查一下订单"）
   - 输出：**官方 API 格式的请求**（调用哪个平台、什么接口、什么参数）
   - 职责：把用户意图翻译成官方 API 调用

2. **official-sim-server（独立服务）**
   - 输入：来自 User Agent 或其他系统的**官方 API 调用**
   - 输出：**官方级 API payload**（从 fixtures 加载）
   - 职责：模拟官方平台返回真实格式的响应

---

## 项目结构

```
platform-sim/
├── apps/
│   ├── official-sim-server/     # 官方行为仿真服务
│   │   ├── app/
│   │   │   ├── api/routes/      # API 路由
│   │   │   ├── core/            # 核心配置
│   │   │   ├── domain/          # 领域逻辑
│   │   │   ├── models/          # 数据模型
│   │   │   ├── platforms/       # 平台 Profile
│   │   │   └── repositories/    # 数据访问层
│   │   ├── fixtures/            # 官方级 payload 数据
│   │   │   ├── taobao/          # 淘宝
│   │   │   ├── douyin_shop/     # 抖店
│   │   │   ├── wecom_kf/        # 企微客服
│   │   │   ├── jd/              # 京东
│   │   │   ├── xhs/             # 小红书
│   │   │   └── kuaishou/        # 快手
│   │   └── tests/               # 测试用例
│   │
│   ├── ai-orchestrator/         # AI 编排服务
│   │   ├── nodes/               # 节点模块
│   │   │   ├── user_simulator.py    # 用户模拟器
│   │   │   ├── conversation_studio.py # 会话工作室
│   │   │   └── reply/           # 回复节点
│   │   ├── services/            # LLM 服务
│   │   └── prompts/             # Prompt 模板
│   │
│   ├── domain-service/          # 领域服务
│   │   ├── models/unified.py    # 统一领域模型
│   │   ├── adapters/            # 平台适配器
│   │   └── services/            # 业务服务
│   │
│   └── conversation-studio-web/ # 会话工作室前端
│
├── providers/                   # 平台 Provider
│   ├── base/provider.py         # 基础 Provider 接口
│   ├── taobao/                  # 淘宝 Provider
│   ├── douyin_shop/             # 抖店 Provider
│   ├── wecom_kf/                # 企微 Provider
│   ├── jd/                      # 京东 Provider
│   ├── xhs/                     # 小红书 Provider
│   ├── kuaishou/                # 快手 Provider
│   └── utils/fixture_loader.py  # Fixture 加载器
│
├── data/
│   └── extracted_user_queries/  # 用户查询模板数据
│
├── docs/                        # 文档
├── schemas/                     # JSON Schema
├── scripts/                     # 脚本工具
└── platform_specs/              # 平台规格说明
```

---

## 支持的平台

| 平台 | 标识 | 状态 | 说明 |
|-----|------|------|------|
| 淘宝 | `taobao` | ✅ 完整支持 | 订单、物流、售后、会话 |
| 抖店 | `douyin_shop` | ✅ 完整支持 | 订单、物流、售后、会话 |
| 企微客服 | `wecom_kf` | ✅ 完整支持 | 会话、消息 |
| 京东 | `jd` | ✅ 完整支持 | 订单、物流、售后 |
| 小红书 | `xhs` | ✅ 完整支持 | 订单、物流、售后 |
| 快手 | `kuaishou` | ✅ 完整支持 | 订单、物流、售后 |

---

## 快速开始

### 环境要求

- Python 3.12+
- PostgreSQL 15+ (可选，Run 生命周期需要)
- Redis (可选)

### 安装

```bash
# 克隆项目
git clone https://github.com/standbyme626/platform-sim.git
cd platform-sim

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 配置

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑配置
# DATABASE_URL=postgresql://postgres:postgres@localhost:5432/official_sim
# REDIS_URL=redis://localhost:6379/0
```

### 启动服务

```bash
# 启动 PostgreSQL (使用 Docker)
docker run -d --name official-sim-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=official_sim \
  -p 5432:5432 postgres:15-alpine

# 创建数据库表
cd apps/official-sim-server
python -c "from app.core.database import engine, Base; from app.models.models import *; Base.metadata.create_all(bind=engine)"

# 启动服务
uvicorn app.main:app --reload --port 8000
```

### 健康检查

```bash
curl http://localhost:8000/healthz
# {"status": "ok", "service": "official-sim-server"}
```

---

## API 接口说明

### 1. Run 生命周期接口

#### 创建仿真运行

```bash
POST /official-sim/runs
Content-Type: application/json

{
  "platform": "taobao",
  "scenario_name": "full_flow",
  "strict_mode": true,
  "push_enabled": true
}
```

响应：
```json
{
  "run_id": "da115dc7-6b08-46bd-86c6-7f920d09777f",
  "run_code": "run_36553b07",
  "platform": "taobao",
  "scenario_name": "full_flow",
  "status": "created",
  "current_step": 0,
  "created_at": "2026-03-30T14:23:15.321092Z"
}
```

#### 推进一步

```bash
POST /official-sim/runs/{run_id}/advance
```

响应：
```json
{
  "run_id": "da115dc7-6b08-46bd-86c6-7f920d09777f",
  "previous_step": 0,
  "current_step": 1,
  "status": "running",
  "message": "Advanced from step 0 to 1"
}
```

#### 获取 Artifacts

```bash
GET /official-sim/runs/{run_id}/artifacts
```

#### 错误注入

```bash
POST /official-sim/runs/{run_id}/inject-error
Content-Type: application/json

{
  "error_code": "token_expired"
}
```

#### 生成评估报告

```bash
GET /official-sim/runs/{run_id}/report
```

### 2. Query 接口（不依赖数据库）

#### 查询订单

```bash
GET /official-sim/query/orders/{order_id}?platform=taobao
```

响应：
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "order": {
      "order_id": "12345678901234",
      "status": "WAIT_SELLER_SEND_GOODS",
      "total_fee": "199.00",
      "receiver_name": "张三",
      ...
    }
  }
}
```

#### 查询物流

```bash
GET /official-sim/query/orders/{order_id}/shipment?platform=taobao
```

#### 查询售后

```bash
GET /official-sim/query/orders/{order_id}/refund?platform=taobao
```

#### 查询用户列表

```bash
GET /official-sim/query/users?platform=taobao
```

---

## 核心功能模块

### 1. 状态机（State Machine）

每个平台都有独立的状态机定义，控制订单、物流、售后、会话的状态转移。

**淘宝订单状态机**：
```
wait_pay ──→ wait_ship ──→ shipped ──→ finished
    │            │            │
    └────────────┴────────────┴──→ trade_closed
```

**状态转移验证**：
```python
from app.platforms.taobao.profile import validate_status_transition, TaobaoOrderStatus

is_valid = validate_status_transition(
    TaobaoOrderStatus.WAIT_PAY, 
    TaobaoOrderStatus.WAIT_SHIP
)  # True
```

### 2. Fixture 系统

所有官方级 payload 都存储在 `fixtures/` 目录：

```
fixtures/
├── taobao/
│   ├── success/           # 成功场景
│   │   ├── trade_wait_ship.json
│   │   ├── trade_shipped.json
│   │   └── ...
│   ├── edge_case/         # 边界场景
│   └── error_case/        # 错误场景
│       ├── token_expired.json
│       └── duplicate_push.json
└── users/                 # 用户数据
    └── taobao_user_001.json
```

**Fixture 结构**：
```json
{
  "platform": "taobao",
  "fixture_type": "success",
  "scenario_key": "trade_wait_ship",
  "description": "订单待发货状态",
  "metadata": {
    "version": "1.0",
    "created_at": "2026-03-29",
    "official_doc": "https://open.taobao.com/api.htm?docId=46..."
  },
  "response": {
    "trade": {
      "tid": 12345678901234,
      "status": "WAIT_SELLER_SEND_GOODS",
      "total_fee": "199.00",
      ...
    }
  }
}
```

### 3. 统一领域模型（Unified Layer）

将各平台差异化的数据结构映射为统一模型：

```python
from apps.domain_service.models.unified import UnifiedOrder, Platform

order = UnifiedOrder(
    order_id="TB123456",
    platform=Platform.TAOBAO,
    status=OrderStatus.WAIT_SHIP,
    total_amount="199.00",
    pay_amount="199.00",
    receiver=UnifiedAddress(
        name="张三",
        phone="138****1234",
        province="浙江省",
        city="杭州市",
        address="西湖区xxx路xxx号"
    ),
    products=[
        UnifiedProduct(
            product_id="P001",
            name="测试商品",
            price="199.00",
            quantity=1
        )
    ]
)
```

### 4. Provider 层

Provider 负责对接或消费 official-sim / real API：

```python
from providers.taobao.provider import TaobaoProvider
from providers.base.provider import ProviderMode

# Mock 模式（使用 fixture）
provider = TaobaoProvider(mode=ProviderMode.MOCK)
order = provider.get_order("TB123456")

# Real 模式（调用真实 API）
provider = TaobaoProvider(mode=ProviderMode.REAL)
order = provider.get_order("TB123456")
```

### 5. 用户模拟器（User Simulator）

基于 LLM 生成真实的用户问题：

```python
from apps.ai_orchestrator.nodes.user_simulator import UserSimulator

simulator = UserSimulator()

# 生成用户消息
result = simulator.generate_user_message(
    platform="taobao",
    user_id="taobao_user_001"
)

print(result.user_message)  # "我的订单怎么还没发货？"
print(result.decision.intent)  # IntentType.ASK_SHIPMENT
```

---

## 场景（Scenario）

每个平台都预定义了常用场景：

### 淘宝场景

| 场景名 | 说明 | 步骤 |
|-------|------|------|
| `wait_ship_basic` | 待发货 | pay → wait_ship |
| `full_flow` | 完整流程 | pay → ship → confirm_receive |
| `wait_ship_to_shipped` | 发货 | ship |
| `shipped_to_finished` | 确认收货 | confirm_receive |

### 抖店场景

| 场景名 | 说明 |
|-------|------|
| `full_flow` | 完整订单流程 |
| `refund_flow` | 退款流程 |
| `basic_shipped_to_confirmed` | 发货到确认 |

### 企微场景

| 场景名 | 说明 |
|-------|------|
| `basic_session` | 基础会话 |
| `full_session` | 完整会话流程 |
| `session_expired` | 会话超时 |

---

## 错误处理

支持以下错误类型：

| 错误码 | HTTP 状态 | 说明 | 可重试 |
|-------|----------|------|--------|
| `token_expired` | 401 | Token 过期 | ✅ |
| `invalid_signature` | 403 | 签名无效 | ❌ |
| `permission_denied` | 403 | 权限不足 | ❌ |
| `resource_not_found` | 404 | 资源不存在 | ❌ |
| `duplicate_push` | 409 | 重复推送 | ❌ |
| `rate_limited` | 429 | 频率限制 | ✅ |
| `out_of_order_push` | 400 | 乱序推送 | ✅ |
| `msg_code_expired` | 400 | 消息码过期 | ✅ |
| `conversation_closed` | 400 | 会话已关闭 | ❌ |

---

## 测试

### 运行测试

```bash
# 运行所有测试
pytest apps/official-sim-server/tests/ -v

# 运行特定平台测试
pytest apps/official-sim-server/tests/test_taobao.py -v

# 运行集成测试
pytest tests/integration/ -v
```

### 测试覆盖

```
测试模块                          测试数量    通过
official-sim-server (核心)         87        87
providers                          23        23
domain-service                      9         9
ai-orchestrator                    24        24
integration                         9         9
────────────────────────────────────────────────
总计                              152       152
```

---

## 开发指南

### 添加新平台

1. 创建平台 Profile：
```python
# apps/official-sim-server/app/platforms/new_platform/profile.py

class NewPlatformOrderStatus(str, Enum):
    WAIT_PAY = "wait_pay"
    PAID = "paid"
    # ...

ORDER_STATUS_TRANSITIONS = {
    NewPlatformOrderStatus.WAIT_PAY: [NewPlatformOrderStatus.PAID],
    # ...
}
```

2. 创建 Fixture 目录：
```bash
mkdir -p apps/official-sim-server/fixtures/new_platform/{success,edge_case,error_case,users}
```

3. 创建 Provider：
```python
# providers/new_platform/provider.py

from providers.base.provider import BaseProvider

class NewPlatformProvider(BaseProvider):
    def get_order(self, order_id: str) -> Dict[str, Any]:
        # ...
```

4. 创建适配器：
```python
# apps/domain-service/adapters/new_platform_adapter.py

class NewPlatformAdapter(PlatformAdapter):
    def to_unified_order(self, platform_order: Dict) -> UnifiedOrder:
        # ...
```

### 添加新场景

1. 在 Profile 中定义场景：
```python
ORDER_SCENARIOS["new_scenario"] = {
    "initial_order_status": NewPlatformOrderStatus.WAIT_PAY,
    "steps": [
        {"action": "pay", "next_status": NewPlatformOrderStatus.PAID},
    ],
}
```

2. 创建对应 Fixture：
```json
// fixtures/new_platform/success/new_scenario.json
{
  "platform": "new_platform",
  "fixture_type": "success",
  "scenario_key": "new_scenario",
  "response": { ... }
}
```

---

## 配置说明

### 环境变量

| 变量 | 默认值 | 说明 |
|-----|-------|------|
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/official_sim` | 数据库连接 |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis 连接 |
| `LOG_LEVEL` | `INFO` | 日志级别 |
| `DB_ECHO` | `false` | SQL 日志开关 |

### 数据库表

| 表名 | 说明 |
|-----|------|
| `simulation_runs` | 仿真运行记录 |
| `simulation_events` | 仿真事件 |
| `state_snapshots` | 状态快照 |
| `push_events` | 推送事件 |
| `artifacts` | 产物记录 |
| `evaluation_reports` | 评估报告 |

---

## 注意事项

1. **真相来源**：所有官方 API 返回必须来自 fixtures，禁止硬编码或 LLM 生成
2. **状态机验证**：状态转移必须符合状态机定义，`strict_mode` 下会严格校验
3. **数据隔离**：每个 run 的数据相互隔离，支持并行执行
4. **可回放**：所有 run 都支持查询状态、快照、artifacts、push events
5. **可审计**：所有重要操作都记录 run_id、platform、scenario_key、step_no

---

## 许可证

MIT License

---

## 贡献

欢迎提交 Issue 和 Pull Request！
