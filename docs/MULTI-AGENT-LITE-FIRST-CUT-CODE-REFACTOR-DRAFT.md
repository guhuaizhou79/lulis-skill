# MULTI-AGENT-LITE FIRST CUT CODE REFACTOR DRAFT

日期：2026-04-11
状态：draft-for-implementation
关联：`docs/MULTI-AGENT-LITE-INTEGRATION-REFIT-PLAN.md`
目标：把第一批最值得动的改造点进一步收敛成“接近可开工”的代码级草案，覆盖 schema、函数职责、最小字段、以及伪 diff 方向。

---

## 1. 本轮只做什么

只聚焦第一批最高价值改动：

1. `schemas/handoff.schema.json`
2. `core/dispatcher.py`
3. `core/delivery_synthesizer.py`
4. `core/orchestrator.py`
5. 必要的 `task/result` schema 扩展

本轮**不直接实现所有 review 收敛策略**，但会预留 review 所需字段和接口。

---

## 2. 核心设计原则

### P1. 角色之间只传 handoff packet
subtask 被分派后，后续角色主要消费 handoff，而不是任意读取全 task 历史。

### P2. task-level synthesis 生成 compact result packet
外层主框架只需要接住 compact `task_result_packet`。

### P3. orchestrator 负责协同模式与降级决策
执行链不再默认“全量跑完再说”，而是允许 compact/minimal 路径。

### P4. schema 先稳定，再扩执行逻辑
不先造复杂行为，再回头找字段承接。

---

## 3. 第一批新增/强化字段

## 3.1 task-level 字段
建议给 task 增加：

```json
{
  "orchestration_mode": "full",
  "execution_budget": {
    "max_context_items": 8,
    "max_evidence_refs": 5,
    "max_sendback_rounds": 2
  },
  "sendback_count": 0,
  "degrade_history": [],
  "writeback_hint": {
    "level": 0,
    "targets": []
  },
  "task_result_packet": null
}
```

### 说明
- `orchestration_mode`: 当前协同深度
- `execution_budget`: 协同预算
- `sendback_count`: review 回退次数
- `degrade_history`: 记录降级轨迹
- `writeback_hint`: 外层意图
- `task_result_packet`: 对外可回传结果包

---

## 3.2 subtask-level 字段
建议给 subtask 增加：

```json
{
  "handoff": {
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
}
```

### 说明
它是角色间最小交接包，不是 task 全量快照。

---

## 3.3 result-level 字段
建议在 result 上逐步支持：

```json
{
  "handoff_ready_summary": "...",
  "deliverable_strength": "strong|weak|none",
  "result_confidence": "high|medium|low",
  "evidence_refs": ["..."],
  "writeback_recommendation": {
    "level": 0,
    "targets": []
  }
}
```

---

## 4. 新增 schema：`schemas/handoff.schema.json`

建议新建一个最小 handoff schema：

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Handoff",
  "type": "object",
  "required": [
    "goal",
    "input_scope",
    "constraints",
    "acceptance_focus",
    "evidence_refs",
    "output_contract",
    "budget"
  ],
  "properties": {
    "goal": { "type": "string" },
    "input_scope": { "type": "array", "items": { "type": "string" } },
    "constraints": { "type": "array", "items": { "type": "string" } },
    "acceptance_focus": { "type": "array", "items": { "type": "string" } },
    "evidence_refs": { "type": "array", "items": { "type": "string" } },
    "output_contract": { "type": "string" },
    "budget": {
      "type": "object",
      "required": ["max_context_items", "max_evidence_refs"],
      "properties": {
        "max_context_items": { "type": "integer", "minimum": 1 },
        "max_evidence_refs": { "type": "integer", "minimum": 1 }
      },
      "additionalProperties": true
    }
  },
  "additionalProperties": true
}
```

---

## 5. `core/dispatcher.py` 改造草案

## 5.1 当前问题
目前 `assign()` 只负责：

- 选模型
- 加 fallback
- 标 ready

没有真正构造角色 handoff。

## 5.2 新职责
Dispatcher 应改为：

1. 选模型
2. 构造 handoff packet
3. 裁剪 context / acceptance / evidence
4. 写入 subtask

## 5.3 建议新增函数

### `_budget(task)`
返回 task 级预算，没有则给默认值。

### `_trim_list(items, limit)`
统一截断列表。

### `build_handoff(subtask, task)`
根据 task + 当前 subtask 构造 handoff packet。

## 5.4 建议伪代码

```python
class Dispatcher:
    def __init__(self, router: ModelRouter):
        self.router = router

    def _budget(self, task: Dict[str, Any]) -> Dict[str, Any]:
        return task.get("execution_budget") or {
            "max_context_items": 8,
            "max_evidence_refs": 5,
        }

    def _trim_list(self, items: list[Any], limit: int) -> list[str]:
        out = []
        seen = set()
        for item in items or []:
            value = str(item).strip()
            if not value or value in seen:
                continue
            seen.add(value)
            out.append(value)
            if len(out) >= limit:
                break
        return out

    def build_handoff(self, subtask: Dict[str, Any], task: Dict[str, Any]) -> Dict[str, Any]:
        budget = self._budget(task)
        acceptance = self._trim_list(task.get("acceptance", []), budget["max_context_items"])
        constraints = self._trim_list(task.get("constraints", []), budget["max_context_items"])
        context_refs = self._trim_list(task.get("context_refs", []), budget["max_context_items"])
        evidence_refs = self._trim_list(task.get("artifacts", []), budget["max_evidence_refs"])
        return {
            "goal": str(subtask.get("objective") or task.get("goal") or "").strip(),
            "input_scope": context_refs,
            "constraints": constraints,
            "acceptance_focus": acceptance,
            "evidence_refs": evidence_refs,
            "output_contract": "result.schema.json",
            "budget": {
                "max_context_items": budget["max_context_items"],
                "max_evidence_refs": budget["max_evidence_refs"],
            },
        }

    def assign(self, subtask: Dict[str, Any], task: Dict[str, Any]) -> Dict[str, Any]:
        role_key = subtask["assigned_role"]
        model_cfg = self.router.pick(role_key)
        return {
            **subtask,
            "assigned_model": model_cfg["primary"],
            "fallback_models": model_cfg.get("fallback", []),
            "dispatch_status": "ready",
            "handoff": self.build_handoff(subtask, task),
        }
```

## 5.5 联动改动
`orchestrator.dispatch_task()` 目前是：

```python
dispatched = [self.dispatcher.assign(st) for st in task["subtasks"]]
```

需要改为：

```python
dispatched = [self.dispatcher.assign(st, task) for st in task["subtasks"]]
```

---

## 6. `core/delivery_synthesizer.py` 改造草案

## 6.1 当前问题
当前 synthesis 输出很多 task-level 字段，但还没有一个明确给外层消费的 compact result packet。

## 6.2 新职责
在保留现有字段基础上，新增：

- `delivery_internal_evidence`
- `task_result_packet`

## 6.3 新增辅助函数

### `_pick_evidence_refs(evidence_map, max_refs=5)`
从 evidence_map 中提取轻量引用。

### `_derive_result_status(task)`
根据 `delivery_status`、风险、needs_input 推断对外状态。

### `_build_writeback_recommendation(task)`
这里只给 recommendation，不做真正写回。

## 6.4 建议伪代码

```python
def _pick_evidence_refs(evidence_map: List[Dict[str, Any]], max_refs: int = 5) -> List[str]:
    refs: List[str] = []
    for item in evidence_map:
        subtask_id = str(item.get("subtask_id") or "").strip()
        summary = str(item.get("summary") or "").strip()
        if subtask_id and summary:
            refs.append(f"{subtask_id}: {summary[:120]}")
        for artifact in item.get("artifacts") or []:
            refs.append(str(artifact))
        if len(refs) >= max_refs:
            break
    return refs[:max_refs]


def _derive_result_status(task: Dict[str, Any]) -> str:
    if task.get("delivery_status") == "delivered":
        return "success"
    if task.get("delivery_status") == "not_delivered":
        return "changes_requested"
    return "blocked"


def _build_writeback_recommendation(task: Dict[str, Any]) -> Dict[str, Any]:
    if task.get("delivery_status") == "delivered":
        return {"level": 0, "targets": []}
    return {"level": 0, "targets": []}
```

在 `synthesize_delivery()` 末尾追加：

```python
    task["delivery_internal_evidence"] = evidence_map
    task["task_result_packet"] = {
        "status": _derive_result_status(task),
        "summary": task["delivery_summary"],
        "deliverables": task["deliverables"],
        "changes": task["delivery_changes"],
        "risks": task["delivery_risks"],
        "needs_input": [],
        "evidence_refs": _pick_evidence_refs(evidence_map),
        "writeback_recommendation": _build_writeback_recommendation(task),
    }
```

## 6.5 第一阶段取舍
第一阶段不在 synthesis 里做过度智能判断，先把**对外 compact packet** 稳定住。

---

## 7. `core/orchestrator.py` 改造草案

## 7.1 当前问题
- task 创建时没有协同策略字段
- dispatch/execute/review 阶段没有 degrade 控制
- review 结果未沉淀为 task-level compact result

## 7.2 最小新增字段
建议在 `create_task()` 初始化：

```python
"orchestration_mode": "full",
"execution_budget": {
    "max_context_items": 8,
    "max_evidence_refs": 5,
    "max_sendback_rounds": 2,
},
"sendback_count": 0,
"degrade_history": [],
"writeback_hint": {"level": 0, "targets": []},
"task_result_packet": None,
```

## 7.3 建议新增函数

### `_select_orchestration_mode(task)`
根据 task_type / priority / acceptance 数量选择 `full|compact|minimal`。

### `_should_degrade(task, review)`
判断是否需要从 full 降到 compact，或 compact 降到 minimal。

### `_apply_degrade(task, reason)`
更新：
- `orchestration_mode`
- `degrade_history`

### `_build_review_augmented_result(task, review)`
把 review verdict 合并进 `task_result_packet`。

## 7.4 create_task 伪 diff

```python
task = {
    ...
    "orchestration_mode": "full",
    "execution_budget": {
        "max_context_items": 8,
        "max_evidence_refs": 5,
        "max_sendback_rounds": 2,
    },
    "sendback_count": 0,
    "degrade_history": [],
    "writeback_hint": {"level": 0, "targets": []},
    "task_result_packet": None,
}
```

## 7.5 dispatch_task 伪 diff

```python
dispatched = [self.dispatcher.assign(st, task) for st in task["subtasks"]]
```

## 7.6 review_task 伪 diff（第一阶段最小版）

当前：

```python
target = "DONE" if review["decision"] == "approved" else "PLAN"
```

建议先收紧成：

```python
if review["decision"] == "approved":
    target = "DONE"
else:
    task["sendback_count"] = int(task.get("sendback_count", 0)) + 1
    max_rounds = int((task.get("execution_budget") or {}).get("max_sendback_rounds", 2))
    if task["sendback_count"] >= max_rounds:
        task = self._apply_degrade(task, reason="sendback threshold reached")
    target = "PLAN"
```

并在 review 后补：

```python
task["task_result_packet"] = self._build_review_augmented_result(task, review)
```

## 7.7 第二阶段再做的事
后续再细分：
- 回 execution
- 回 plan
- blocked
- minimal mode

第一阶段先保证有 degrade 轨迹和 compact result。

---

## 8. `schemas/task.schema.json` 扩展草案

建议补充：

```json
"orchestration_mode": { "type": "string", "enum": ["full", "compact", "minimal"] },
"execution_budget": { "type": "object" },
"sendback_count": { "type": "integer", "minimum": 0 },
"degrade_history": { "type": "array", "items": { "type": "object" } },
"writeback_hint": { "type": "object" },
"task_result_packet": { "type": ["object", "null"] }
```

---

## 9. `schemas/result.schema.json` 扩展草案

建议补充：

```json
"handoff_ready_summary": { "type": "string" },
"deliverable_strength": { "type": "string", "enum": ["strong", "weak", "none"] },
"result_confidence": { "type": "string", "enum": ["high", "medium", "low"] },
"evidence_refs": { "type": "array", "items": { "type": "string" } },
"writeback_recommendation": { "type": "object" }
```

---

## 10. 第一批改造完成后的最低验证集

完成第一批后，至少验证 4 条链：

### V1. 普通成功链
- dispatch 时每个 subtask 都有 handoff
- execution 后产出 `task_result_packet`
- review approved -> DONE

### V2. changes_requested 链
- review 不通过
- `sendback_count` 正确增加
- `task_result_packet` 正确带出 review verdict

### V3. degrade 触发链
- 连续 send-back 到阈值
- `orchestration_mode` 发生变化
- `degrade_history` 留痕

### V4. 外层接入链
- 外层只消费 `task_result_packet`
- 不需要直接依赖内部 evidence_map 全量字段

---

## 11. 最小实施建议

如果只做真正最小可运行版本，建议按这个顺序：

1. 新建 `schemas/handoff.schema.json`
2. 改 `dispatcher.py`，让每个 subtask 都带 `handoff`
3. 改 `delivery_synthesizer.py`，产出 `task_result_packet`
4. 改 `orchestrator.py`，补 task 字段和 degrade 轨迹
5. 最后扩 schema

这样可以最快形成“主框架可接”的第一版闭环。

---

## 12. 当前最准确结论

第一批最重要的不是让 `multi-agent-lite` 变得更复杂，而是让它具备：

- **轻量交接**
- **紧凑结果包**
- **最小降级能力**
- **外层可接入边界**

只要这四点落地，它就已经从“内部原型”迈进到“现有框架中的受控协同内核”了。
