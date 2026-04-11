# MULTI-AGENT-LITE OUTER ADAPTER CONTRACT

日期：2026-04-11
状态：first-cut
目标：定义外层主框架如何**按条件调用** `frameworks/multi-agent-lite`，以及如何消费其结果，而不把 `multi-agent-lite` 升格成全局 controller。

---

## 1. 定位

`multi-agent-lite` 在外层主框架中的角色应当是：

> **可选的 staged collaboration kernel**

不是：
- 全局任务分类器
- 长期记忆总控
- 所有任务的默认执行路径
- 外部写回的最终裁决者

外层主框架仍然负责：
- 任务识别
- direct / light / staged 路径选择
- 对话主线控制
- writeback / converger / state sync

`multi-agent-lite` 负责：
- 单任务范围内的阶段化协同
- review 驱动的局部回退
- compact task result packet 输出

---

## 2. 建议的最小接入形态

```text
outer framework
  -> classify_task_shape(task)
  -> choose_route(task)
       - direct
       - light_role_check
       - multi_agent_lite
  -> if multi_agent_lite:
       - build inner task payload
       - run staged orchestration
       - receive task_result_packet + runtime task snapshot
  -> outer converger
  -> outer writeback / state sync
```

关键原则：
- 外层只依赖稳定 adapter contract
- 不直接依赖 inner engine 的内部字段细节作为主契约
- 允许 inner engine 演进，但 adapter contract 尽量稳定

---

## 3. outer -> inner 输入契约（建议最小字段）

```json
{
  "title": "...",
  "goal": "...",
  "task_type": "automation|framework_design|code|...",
  "priority": "low|normal|high|critical",
  "constraints": ["..."],
  "acceptance": ["..."],
  "context_refs": ["..."]
}
```

说明：
- 外层只传“当前任务范围内最小必要输入”
- 不把大段聊天历史原样整坨塞进去
- `context_refs` 优先传摘要化对象，而不是原始 transcript

---

## 4. inner -> outer 输出契约（建议最小字段）

adapter 对外返回时，建议至少稳定以下字段：

```json
{
  "route": "multi_agent_lite",
  "task_id": "TASK-...",
  "final_status": "DONE|READY|PLAN|BLOCKED|FAILED",
  "orchestration_mode": "full|compact|minimal",
  "task_result_packet": {
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
  },
  "writeback_hint": {"level": 0, "targets": []},
  "degrade_history": [],
  "sendback_count": 0,
  "artifact_lifecycle": [],
  "raw_task": {}
}
```

其中：
- `task_result_packet` 是 outer converger 的首选读取对象
- `raw_task` 只作 debug / deeper inspection，不作为默认上层消费面

---

## 5. 路由建议（outer choose_route）

### 走 direct path
当任务满足以下特征时：
- 一轮能答完
- 没必要拆 planning/execution/review
- 更多是判断、解释、轻问答

### 走 light role check path
当任务有轻度复杂性，但没必要启动完整 staged collaboration：
- 需要一个简短检查或结构化回答
- 需要轻量自检，但不值得起完整 review loop

### 走 multi-agent-lite path
当任务满足这些条件时：
- 用户明确要求多 agent / staged orchestration
- 任务需要 planning -> execution -> review 的明确分层
- 需要 sendback / gap 分类 / rerun 控制
- 单代理直做容易失去审查闭环

### 暂不进入 multi-agent-lite
当任务存在这些情况时：
- 高风险外部动作且审批边界不清
- 更像持续项目管理，而不是单任务 staged collaboration
- 当前更需要 outer framework 自己做主线判断，而不是 inner orchestration

---

## 6. 外层 converger 如何消费

建议 outer converger 按这个顺序读：

1. `task_result_packet`
2. `final_status`
3. `orchestration_mode`
4. `degrade_history`
5. `artifact_lifecycle`
6. 必要时再看 `raw_task`

### outer response 的建议逻辑
- `task_result_packet.status == success` 且 `final_status == DONE`
  - 可对用户输出交付摘要
- `final_status == READY`
  - 表示 inner engine 判定 execution-side repair path 已建立
  - outer framework 不应误读为“任务已完成”
- `final_status == PLAN`
  - 表示需重新规划 / 重构路径
- `final_status == BLOCKED`
  - outer 应把 `needs_input` / `risks` 明确暴露给用户

---

## 7. writeback authority 边界

必须保持：
- `multi-agent-lite` 只给 recommendation / hint
- outer framework 决定是否写回：
  - memory
  - docs
  - current-state
  - working-summary

原因：
- writeback 是否值得做，本质是全局主线判断
- inner engine 只看到单任务局部，不适合直接决定长期状态面

---

## 8. 最小可运行接法建议

第一阶段不要急着把主框架大改。

更稳的做法是先提供一个薄适配器：
- 输入一个 outer task payload
- 内部调用 `Orchestrator`
- 输出标准 adapter result

这样后续主框架只需要：
- 调 `adapter.run(payload)`
- 再决定如何汇总 / 写回

---

## 9. 当前建议的下一步代码动作

1. 新增一个 `outer_adapter.py` / `adapter.py`
2. 提供：
   - `choose_route(payload)`
   - `run_multi_agent_lite(payload)`
   - `build_outer_result(task)`
3. 先把它做成 repo 内可直接调用的 shim
4. 等 outer framework 主入口清晰后，再把 shim 接进去

---

## 10. 结论

当前最合理的方式不是“宣布已经接入外层主框架”，因为 repo 里还没有明确的 outer framework runtime 入口可挂。

更正确的阶段性做法是：

> **先把 outer adapter contract 固化，再让主框架按这个契约接入。**

这样能避免把 `multi-agent-lite` 误做成另一个平行系统，也能保证后续真正集成时改动最小。
