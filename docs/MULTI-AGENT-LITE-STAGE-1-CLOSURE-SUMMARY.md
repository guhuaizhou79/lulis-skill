# MULTI-AGENT-LITE STAGE-1 CLOSURE SUMMARY

日期：2026-04-11
状态：stage-1-closed
范围：`lulis-skill/frameworks/multi-agent-lite` 及其 outer adapter / outer shell first-cut 落地收口

---

## 1. 这轮到底完成了什么

这轮工作不是单点修补，而是把 `multi-agent-lite` 从“可跑 demo / 设计草案”推进到了一个**可接入现有框架的 first-cut 协同内核**。

完成面分五层：

### A. inner kernel runtime
已完成：
- `handoff` contract 注入 subtask
- `task_result_packet` 生成
- review verdict 回写 task-level result packet
- `gap_groups` 分类
- `next_action` 路由提示
- `sendback_count` / `degrade_history`
- `orchestration_mode` 降级
- `review -> execution` selective rerun
- stale result 保留
- active / stale evidence 分层
- `artifact_lifecycle` 建账

### B. validation surface
已完成：
- 原有 delivery 场景验证保留
- handoff / result packet / rerun / stale / artifact lifecycle 验证并入统一入口
- 统一验证入口：
  - `frameworks/multi-agent-lite/validate_delivery.py`
- 兼容包装保留：
  - `validate_handoff_and_result_packet.py`

### C. adapter layer
已完成：
- outer adapter contract 文档
- `outer_adapter.py` first-cut shim
- `choose_route(payload)`
- `run_adapter(root, payload)`
- staged path 的 outer result 面收口
- `validate_outer_adapter.py`

### D. outer shell skeleton
已完成：
- `outer_framework.py`
- `classify_task_shape(payload)`
- direct / light / staged 三路 dispatch skeleton
- unified outer converger
- `route_explanation`
- `normalized_status`
- advisory-only `writeback_policy`
- `validate_outer_framework.py`

### E. docs / skill / readme sync
已完成：
- integration refit plan 同步到 runtime 现状
- first-cut refactor draft 标记为 partially implemented
- outer adapter contract 文档落地
- README 补 outer adapter / outer shell / validation
- SKILL 补 route 边界 / validation / integration boundary

---

## 2. 当前系统定位（很重要）

当前的 `multi-agent-lite` 应被理解为：

> **bounded staged collaboration kernel + outer adapter + outer shell skeleton**

不是：
- 全局 controller
- 总状态机
- 全局 writeback authority
- 所有任务默认路径
- 完整 outer framework runtime

也就是说：
- inner kernel 已经具备第一阶段可用性
- adapter 已经具备外层接入面
- outer shell 已经具备框架骨架
- 但整个系统还没有成长为“全局主框架”

---

## 3. 已验证过的关键行为

当前已经跑通过的关键行为包括：

1. baseline staged flow 正常完成
2. deliverable-required 场景可产出 task-level artifact
3. semantic execution failure 可回 `READY` 走 selective rerun
4. strict review contract-gap 可回 execution 修补
5. handoff packet 在 dispatch 后存在且带 budget
6. `task_result_packet` 在 execute 后存在，并在 review 后合并 verdict
7. repeated sendback 可触发 `degrade_history`
8. rerun 只标记受影响 execution subtasks
9. stale evidence 会被 internal evidence 保留
10. public evidence 只保留 active 项
11. `artifact_lifecycle` 可记录 active / stale artifact 行
12. outer adapter 可正确进行 direct vs staged 路由验证
13. outer framework skeleton 可正确进行 direct / light / staged 路由验证
14. outer result 已包含 `route_explanation` / `normalized_status` / `writeback_policy`

---

## 4. 当前仍明确没做完的部分

### 4.1 outer writeback 还只是 advisory stub
现在只有：
- `writeback_hint`
- `writeback_recommendation`
- `writeback_policy`

还没有：
- 真正的 docs writeback executor
- 真正的 memory/state writeback executor
- 真正的 outer converger 持久化动作

### 4.2 outer shell 还没有 registry / trace / audit surface
当前还缺：
- run id / route trace
- outer-level task registry
- outer audit log
- 跨任务观察面

### 4.3 direct / light 路径还是骨架
当前 direct / light 只是：
- 结果壳统一
- 路由壳统一

还没有：
- 更真实的 outer direct executor
- 更真实的 light role-check runtime

### 4.4 rerun 还不是依赖图级别
当前 selective rerun 粒度是：
- affected execution subtask

还不是：
- artifact dependency graph
- provenance graph
- 更强的修复最优化

### 4.5 还没进入真实 CI / release 面
当前虽然验证统一了，但还没有：
- CI job
- repo-level recommended command surface
- release checklist

---

## 5. 这轮工作的价值判断

这轮最有价值的不是“功能数量”，而是**边界被理顺了**。

理顺了这些边界：
- inner kernel 做什么
- outer adapter 做什么
- outer shell 做什么
- writeback authority 在哪
- validation 以哪个入口为准
- 文档是否跟 runtime 同步

这意味着后面继续扩展时，不需要再反复争论：
- 它是不是全局 controller
- rerun 该不该在 inner 做
- writeback 该不该在 inner 做
- outer 是否必须直接读 raw task

这些基础边界现在已经清楚了。

---

## 6. 建议的下一阶段顺序

### S2-1：outer trace / registry stub
优先补：
- run id
- route trace
- outer task registry skeleton
- outer audit surface

这是当前 outer shell 最缺的一层。

### S2-2：writeback executor stub
在不越权的前提下补：
- summary writeback stub
- state writeback stub
- 仍然保持 outer final authority

### S2-3：direct / light path strengthening
如果后续真的要把 outer shell 变成更完整主框架，再考虑：
- direct executor contract
- light role-check executor contract
- richer route policy

### S2-4：CI / command surface
最后再收：
- CI hook
- repo-level documented commands
- release / regression checklist

---

## 7. 阶段结论

这轮可以正式视为：

> **multi-agent-lite stage-1 已收口**

它现在已经不是一个只存在于文档和草图里的想法，而是：
- 有 runtime
- 有 adapter
- 有 outer shell
- 有 validation
- 有同步文档
- 有明确边界

下一阶段不该回到“是不是要多 agent / 怎么设计 handoff”这种前置问题，
而应该直接进入：

> **outer trace / registry / writeback stub 的第二阶段实装。**
