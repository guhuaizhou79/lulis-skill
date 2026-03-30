# multi-agent-lite

轻量多 Agent 协同框架原型。

## 当前包含
- 角色分层：manager / research / execution / reviewer
- 状态机：NEW → PLAN → READY → EXECUTING → REVIEW → DONE
- 文件态任务存储
- 模型路由配置
- schema 基础定义

## 目标
先形成可运行闭环，再逐步增加执行器、review 机制、subtask 分派。
