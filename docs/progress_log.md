# Progress Log

记录每个 milestone 的执行进度、当前阻塞、下一步动作。

---

## M1: 工程骨架 ✅ DONE

- **状态**: done
- **开始时间**: 2026-03-29
- **完成时间**: 2026-03-29
- **目标**: 建立 official-sim-server 基础骨架

- **实际完成**:
  - 创建 apps/official-sim-server 目录结构
  - 实现 main.py + healthz 路由
  - 实现 router.py 路由聚合
  - 实现 runs.py POST /official-sim/runs (stub)
  - 添加 requirements.txt 和 pyproject.toml

- **未完成项**: 无

- **阻塞**: 无

- **下一步**: M2 - 建立数据库与迁移基础

- **验证命令**:
  ```bash
  cd apps/official-sim-server
  pip install -r requirements.txt
  uvicorn app.main:app --reload --port 8088
  curl http://127.0.0.1:8088/healthz
  ```

- **结果**: ✅ 通过

---

## M2: 数据库与迁移基础

- **状态**: ✅ DONE
- **开始时间**: 2026-03-29
- **完成时间**: 2026-03-29
- **目标**: 引入 DB migration，落第一批核心表

- **实际完成**:
  - 初始化 Alembic 配置
  - 创建 6 张核心表（simulation_runs, simulation_events, state_snapshots, push_events, artifacts, evaluation_reports）
  - 创建 repository skeleton（run_repo, event_repo, snapshot_repo）
  - 更新 runs.py 连接 DB（实际使用 SQLite）

- **未完成项**:
  - pytest db smoke tests

- **阻塞**: 无

- **下一步**: M3 - 实现 run 生命周期

- **验证命令**:
  ```bash
  cd apps/official-sim-server
  alembic upgrade head
  alembic downgrade base
  alembic upgrade head
  ```

- **结果**: ✅ 通过 - 6 张表创建成功，up/down 验证通过

---

## M3: Run 生命周期

- **状态**: ✅ DONE
- **开始时间**: 2026-03-29
- **完成时间**: 2026-03-29
- **目标**: 实现 run 的创建、查询、推进

- **实际完成**:
  - 实现 GET /official-sim/runs/{run_id} 查询端点
  - 实现 POST /official-sim/runs/{run_id}/advance 推进端点
  - advance 时自动创建 event 和 snapshot
  - 实现 GET /official-sim/runs/{run_id}/events 事件列表
  - 实现 GET /official-sim/runs/{run_id}/snapshots 快照列表
  - 创建完整 pytest 测试（11 个测试用例）
  - 修复 step 推进逻辑 bug（advance_step + 1 重复）
  - 切换为 PostgreSQL 数据库（使用 finance-invoice-ocr-postgres-1）

- **未完成项**: 无

- **阻塞**: 无

- **下一步**: M4 - Artifacts / Snapshots / Push Events

- **验证命令**:
  ```bash
  cd apps/official-sim-server
  python -m pytest tests/ -v
  ```

- **结果**: ✅ 11 passed

---

## M4: Artifacts / Snapshots / Push Events

- **状态**: ✅ DONE
- **开始时间**: 2026-03-29
- **完成时间**: 2026-03-29
- **目标**: 让 run 能产出"平台侧工件"

- **实际完成**:
  - 实现 ArtifactRepository 和 ArtifactBuilder
  - 实现 PushEventRepository 和 PushDispatcher
  - 实现 `GET /official-sim/runs/{run_id}/artifacts` 端点
  - 实现 `GET /official-sim/runs/{run_id}/pushes` 端点
  - 实现 `POST /official-sim/runs/{run_id}/replay-push` 端点
  - 实现 `POST /official-sim/runs/{run_id}/inject-error` 端点
  - advance 时自动创建 api_response_snapshot artifact
  - 实现 12 种错误码注入（token_expired, invalid_signature, rate_limited 等）
  - 创建完整 pytest 测试（23 个测试用例全部通过）

- **未完成项**: 无

- **阻塞**: 无

- **下一步**: M5 - 实现 taobao P0 profile

- **验证命令**:
  ```bash
  cd apps/official-sim-server
  python -m pytest tests/ -v
  ```

- **结果**: ✅ 23 passed

---

## M5: Taobao P0 Profile

- **状态**: ✅ DONE
- **开始时间**: 2026-03-29
- **完成时间**: 2026-03-29
- **目标**: 实现淘宝 P0 平台 profile

- **实际完成**:
  - 实现 `app/platforms/taobao/profile.py` - 淘宝订单状态机和场景定义
  - 实现 `app/domain/scenario_engine.py` - 场景执行引擎
  - 支持场景: wait_ship_basic, wait_ship_to_shipped, shipped_to_finished, full_flow
  - advance 时根据场景自动创建订单/物流 artifact 和 push event
  - 创建 8 个淘宝测试用例（状态转移、push、错误注入）
  - 31 个 pytest 测试全部通过

- **未完成项**: 无

- **阻塞**: 无

- **下一步**: M6 - 实现 douyin_shop P0 profile

- **验证命令**:
  ```bash
  cd apps/official-sim-server
  python -m pytest tests/test_taobao.py -v
  ```

- **结果**: ✅ 31 passed

- **结果**:

---

## M6: Douyin Shop P0 Profile

- **状态**: ✅ DONE
- **开始时间**: 2026-03-29
- **完成时间**: 2026-03-29
- **目标**: 实现抖店 P0 平台 profile

- **实际完成**:
  - 实现 `app/platforms/douyin_shop/profile.py` - 抖店订单状态机和场景定义
  - 支持场景: basic_paid_to_shipped, basic_shipped_to_confirmed, basic_confirmed_to_completed, full_flow, refund_flow
  - 支持退款流程: apply_refund -> approve_refund
  - 更新 `app/domain/scenario_engine.py` 支持多平台
  - 创建 9 个抖店测试用例
  - 40 个 pytest 测试全部通过

- **未完成项**: 无

- **阻塞**: 无

- **下一步**: M7 - 实现 wecom_kf P0 profile

- **验证命令**:
  ```bash
  cd apps/official-sim-server
  python -m pytest tests/test_douyin_shop.py -v
  ```

- **结果**: ✅ 40 passed

---

## M7: Wecom KF P0 Profile

- **状态**: todo
- **开始时间**:
- **完成时间**:
- **目标**: 实现企微客服 P0 平台 profile

- **实际完成**:

- **未完成项**:

- **阻塞**:

- **下一步**:

- **验证命令**:

- **结果**:

---

## M8: Integration

- **状态**: todo
- **开始时间**:
- **完成时间**:
- **目标**: 打通与 unified/provider 的最小集成

- **实际完成**:

- **未完成项**:

- **阻塞**:

- **下一步**:

- **验证命令**:

- **结果**:

---

## M9: 错误注入与报告

- **状态**: todo
- **开始时间**:
- **完成时间**:
- **目标**: 完善错误注入和报告生成

- **实际完成**:

- **未完成项**:

- **阻塞**:

- **下一步**:

- **验证命令**:

- **结果**:

---

## M10: README 与验收

- **状态**: todo
- **开始时间**:
- **完成时间**:
- **目标**: 完善文档，提交验收

- **实际完成**:

- **未完成项**:

- **阻塞**:

- **下一步**:

- **验证命令**:

- **结果**:
