# Commands

## 1. 文档目的

本文档固定 Codex 在本仓库中应优先使用的命令模板。

如果仓库已有现成脚本，应以现成脚本为准；如果尚未落地，则按本文档补齐。

---

## 2. 环境初始化

### 2.1 Python 虚拟环境
示例：

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2.2 安装依赖

若项目使用 requirements.txt：

```bash
pip install -r requirements.txt
```

若官方后续统一到 poetry/uv，则 AGENTS.md 以实际工具为准。

---

## 3. 启动 official-sim-server

```bash
cd apps/official-sim-server
uvicorn app.main:app --reload --port 8088
```

健康检查：

```bash
curl http://127.0.0.1:8088/healthz
```

---

## 4. Migration

### 4.1 升级到最新
```bash
alembic upgrade head
```

### 4.2 回滚一步
```bash
alembic downgrade -1
```

### 4.3 生成新 migration
```bash
alembic revision -m "create simulation_runs"
```

若启用 autogenerate：

```bash
alembic revision --autogenerate -m "add push_events"
```

---

## 5. 测试

### 5.1 全量
```bash
pytest
```

### 5.2 单元测试
```bash
pytest -m unit
```

### 5.3 API 测试
```bash
pytest -m api
```

### 5.4 集成测试
```bash
pytest -m integration
```

### 5.5 Fixture 测试
```bash
pytest -m fixture
```

### 5.6 Migration 测试
```bash
pytest -m migration
```

### 5.7 平台专项测试
```bash
pytest tests/unit/platforms/taobao
pytest tests/unit/platforms/douyin_shop
pytest tests/unit/platforms/wecom_kf
```

---

## 6. 常用 curl

### 6.1 创建 run
```bash
curl -X POST http://127.0.0.1:8088/official-sim/runs \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "taobao",
    "scenario_name": "wait_ship_basic",
    "strict_mode": true,
    "push_enabled": true
  }'
```

### 6.2 查询 run
```bash
curl http://127.0.0.1:8088/official-sim/runs/<run_id>
```

### 6.3 推进一步
```bash
curl -X POST http://127.0.0.1:8088/official-sim/runs/<run_id>/advance \
  -H "Content-Type: application/json" \
  -d '{
    "action_type": "user.ask_shipment",
    "payload": {"message": "怎么还没发货"}
  }'
```

### 6.4 获取 artifacts
```bash
curl http://127.0.0.1:8088/official-sim/runs/<run_id>/artifacts
```

### 6.5 注入错误
```bash
curl -X POST http://127.0.0.1:8088/official-sim/runs/<run_id>/inject-error \
  -H "Content-Type: application/json" \
  -d '{
    "error_code": "duplicate_push",
    "injection_scope": "current_step",
    "target": "taobao.push"
  }'
```

### 6.6 获取 report
```bash
curl http://127.0.0.1:8088/official-sim/runs/<run_id>/report
```

---

## 7. Stop-and-fix 规则

任一命令失败时：

1. 先看错误日志
2. 修复失败项
3. 重跑当前阶段命令
4. 不带着失败进入下一 milestone
