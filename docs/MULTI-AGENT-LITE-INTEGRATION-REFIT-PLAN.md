# MULTI-AGENT-LITE INTEGRATION REFIT PLAN

日期：2026-04-11
状态：proposal
目标：把 `lulis-skill/frameworks/multi-agent-lite` 从“可跑原型”收紧为“可接入现有主框架的受控协同内核”，重点补齐轻量交接、失败降级、结果包标准化、以及外层接入边界。

---

## 1. 当前判断

`multi-agent-lite` 现有骨架已经成立：

- 角色链路：`manager -> research -> execution -> reviewer`
- 关键内核：`planner -> dispatcher -> executor -> delivery_synthesizer -> review_engine`
- 运行态目录：`runtime/tasks`、`runtime/logs`、`runtime/artifacts`
- schema 基础：`task.schema.json`、`result.schema.json`、`review.schema.json`

这说明它不是概念稿，而是一个值得继续收紧的轻量协同原型。

当前主要缺口不是“角色不够”，而是：

1. agent 间交接契约过弱
2. 协同预算 / 失败降级缺失
3. task-level synthesis 仍偏拼装，不够轻量可回传
4. review 能发现问题，但还不能有效控制回退路径
5. 与外层主框架的输入输出边界还不够稳定

---

## 2. 目标定位

这次改造不把 `multi-agent-lite` 升格为总控大脑。

它在现有框架中的定位应当是：

> **复杂任务的 staged collaboration engine**

即：

- 外层主框架负责：任务识别、主线判断、是否进入 staged path、状态回写
- `multi-agent-lite` 负责：单任务范围内的阶段化协同、交付收敛、review 判定

因此，这次改造坚持四条边界：

1. 不接管长期记忆治理
2. 不接管全局主线判断
3. 不默认接管所有任务
4. 不扩角色谱系，先收紧当前四角色

---

## 3. 改造总目标

### G1. 轻量交接
角色之间传递结构化 handoff packet，而不是散装上下文或整坨历史。

### G2. 失败降级
当结果质量低、反复 send-back、needs_input 无法收敛、或协同成本过高时，流程可退化为 compact/minimal 模式，而不是一直全流程回环。

### G3. 标准结果包
协同内核对外输出 compact task result packet，便于现有主框架接住并做 converger/writeback。

### G4. 外层写回隔离
写回 memory / docs / current-state 的决定留在外层主框架，`multi-agent-lite` 只产出 writeback recommendation。

---

## 4. 现有主框架中的接入位置

推荐接入关系：

```text
main framework
  -> task classifier
    -> direct path
    -> light role check path
    -> multi-agent-lite path
          -> manager / research / execution / reviewer
          -> compact task result packet
  -> outer converger / writeback
```

接入原则：

- `multi-agent-lite` 是一个“按需启用的执行引擎”
- 外层主框架只依赖它的标准输入输出
- 不要求外层知道它内部每个角色的细节

---

## 5. 第一批改造范围（优先顺序）

### P1
1. `core/dispatcher.py`
2. `core/delivery_synthesizer.py`
3. `core/orchestrator.py`

### P2
4. `core/review_engine.py`
5. `schemas/*.json`

### 暂缓
- 扩新角色
- 并行复杂调度
- 面板/UI 级深耦合
- 长期记忆写回内嵌到协同内核

---

## 6. 文件级改造点

## 6.1 `core/dispatcher.py`

### 当前问题
当前 `assign()` 只补充：

- `assigned_model`
- `fallback_models`
- `dispatch_status`

仍然缺少真正的 handoff contract。

### 目标
把 Dispatcher 从“模型分配器”升级为“交接包构造器”。

### 计划新增
建议新增：

- `build_handoff(subtask, task)`
- `trim_context_refs(task, subtask)`

### 建议 handoff packet 最小字段

```json
{
  "goal": "...",
  "input_scope": ["..."],
  "constraints": ["..."],
  "acceptance_focus": ["..."],
  "evidence_refs": ["..."],
  "output_contract": "result.schema.json",
  "budget": {
    "max_context_items": 8,
    "max_evidence_refs": 5
  }
}
```

### 预期收益
- 限制上下文膨胀
- 提高角色交接稳定性
- 为外层主框架适配器提供稳定入口

---

## 6.2 `core/delivery_synthesizer.py`

### 当前问题
当前 synthesis 更像结果汇总器：

- `delivery_summary` 由多个 summary 拼接
- `deliverable_candidates` 容易膨胀
- `delivery_evidence` 仍偏原始收集

### 目标
把它升级为“对外结果包生成器”。

### 建议新增概念
区分两层：

- `delivery_internal_evidence`
- `task_result_packet`

### `task_result_packet` 最小建议字段

```json
{
  "status": "success|changes_requested|blocked|failed",
  "summary": "...",
  "deliverables": ["..."],
  "changes": ["..."],
  "risks": ["..."],
  "needs_input": ["..."],
  "evidence_refs": ["..."],
  "writeback_recommendation": {
    "level": 0,
    "targets": []
  }
}
```

### 关键规则
- 外层默认读取 `task_result_packet`
- 内部细证据继续留在 task 内部字段
- 不把所有 execution 原文继续向上转发

### 预期收益
- 减轻汇总层负担
- 更适合集成到现有框架的 converger
- 控制协同链路中间产物体积

---

## 6.3 `core/orchestrator.py`

### 当前问题
当前 orchestrator 更像流程串联器：

- 缺 orchestration mode
- 缺 budget
- 缺 degrade policy
- review 失败只会粗暴回 `PLAN`

### 目标
升级为“轻控制器”。

### 建议新增 task 级字段

- `orchestration_mode`: `full | compact | minimal`
- `sendback_count`
- `degrade_history`
- `execution_budget`
- `writeback_hint`

### 建议新增控制函数

- `_select_orchestration_mode(task)`
- `_should_degrade(task, signals)`
- `_next_sendback_target(task, review)`
- `_build_task_result(task, review)`

### review 后的目标状态不再只分两种
建议最少区分：

- `approved -> DONE`
- `execution-fixable -> READY`
- `replan-required -> PLAN`
- `repeat-low-gain / needs-input-stalled -> BLOCKED`

### 预期收益
- 回退路径更智能
- 能把“协同失败”收敛成明确状态，而不是无限回环
- 为多路径接入现有框架提供更稳定控制面

---

## 6.4 `core/review_engine.py`

### 当前问题
当前 review 已能发现很多问题，但“问题分类 -> 回退动作”的映射还太弱。

### 目标
从质量检查器升级为收敛裁判。

### 建议新增判断维度
将 gap 分类为：

- `planning_gap`
- `execution_gap`
- `contract_gap`
- `input_gap`
- `delivery_gap`

### 建议新增输出字段

- `recommended_mode`
- `recommended_writeback_level`
- `low_gain_detected`
- `repeat_gap_detected`
- `stop_reason`

### send-back 规则
- 规划问题 -> 回 `PLAN`
- 执行问题 -> 回 `READY/EXECUTING`
- 输入缺失 -> `BLOCKED` 或 `needs_input`
- 多轮无增益 -> 建议降级为 `compact/minimal`

### 预期收益
- review 真正控制收敛
- 避免流程型死循环
- 为降级逻辑提供判断依据

---

## 6.5 `core/execution_runner.py`

### 当前问题
执行层目前是线性串跑，没有执行级预算控制，也没有提前短路。

### 目标
从“跑完所有 subtasks”升级为“按质量信号受控执行”。

### 建议新增运行信号

每个 subtask 结果外，附加：

- `has_needs_input`
- `deliverable_strength`
- `failure_kind`
- `budget_warning`
- `used_fallback`

### 建议新增短路规则
- 关键执行子任务连续 `needs_input`
- 主执行子任务无 deliverable signal
- 失败率超过阈值

以上任一触发时，不必机械跑完全链，可提前返回 review/orchestrator。

---

## 7. schema 改造

## 7.1 `schemas/task.schema.json`

### 建议新增字段
- `orchestration_mode`
- `execution_budget`
- `sendback_count`
- `degrade_history`
- `writeback_hint`
- `task_result_packet`

## 7.2 `schemas/result.schema.json`

### 建议增强字段
- `evidence_refs`
- `result_confidence`
- `deliverable_strength`
- `handoff_ready_summary`
- `writeback_recommendation`

## 7.3 建议新增 `schemas/handoff.schema.json`

### 最小字段
- `subtask_id`
- `role`
- `goal`
- `input_scope`
- `constraints`
- `acceptance_focus`
- `evidence_refs`
- `output_contract`
- `budget`

### 作用
把当前“角色串联”升级为“契约协同”。

---

## 8. 与现有框架的标准接口

### 输入
外层主框架向 `multi-agent-lite` 提供 `task_packet`：

- `task_id`
- `task_type`
- `goal`
- `context_scope`
- `constraints`
- `acceptance`
- `writeback_hint`
- `orchestration_mode`

### 输出
`multi-agent-lite` 返回 `task_result_packet`：

- `status`
- `summary`
- `deliverables`
- `changes`
- `risks`
- `needs_input`
- `evidence_refs`
- `writeback_recommendation`
- `review_verdict`

### 外层负责
- 是否采纳结果
- 是否写回 docs / memory / current-state
- 如何对用户回复

---

## 9. 第一批实施顺序

### Step 1：先定契约
产物：
- `schemas/handoff.schema.json`
- `task_result_packet` 最小字段约定
- `orchestration_mode` / `degrade_policy` task 字段约定

### Step 2：改 3 个核心文件
- `core/dispatcher.py`
- `core/delivery_synthesizer.py`
- `core/orchestrator.py`

### Step 3：补 review 收敛控制
- `core/review_engine.py`
- 必要时联动 `execution_runner.py`

### Step 4：再做一次验证
优先跑：
- 一次正常交付链
- 一次 needs_input 链
- 一次 changes_requested -> execution fix -> approved 链
- 一次 repeated low-gain -> degrade/block 链

---

## 10. 非目标

当前阶段不做：

- 泛化的分布式 orchestrator
- 大规模并行 agent 调度
- 把多实例控制面并入 `multi-agent-lite`
- 在内核里直接写长期 memory / 全局状态
- 为了“显得像多 agent”而增加 ceremony

---

## 11. 最准确的当前结论

`multi-agent-lite` 现在最值得做的不是继续扩角色，也不是抽象成更大的平台。

最优方向是：

> **把它收紧为一个有 handoff 契约、有失败降级、有 compact result packet、且能被外层主框架稳定调用的轻量协同内核。**

只要这一步做好，它就能自然融入现有框架，而不是成为另一套平行系统。
