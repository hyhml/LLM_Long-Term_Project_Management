# LTPM core terms

Use these terms when explaining the framework or naming its project files. A project may add its own domain vocabulary in its project-owned instructions; it must not redefine these authority boundaries.

| Term | Meaning |
| --- | --- |
| **LTPM** | Long-Term Project Manager: the whole long-term project-management framework. In this repository it includes development material; the installed runtime is its user-facing part. |
| **Total skill / 总 skill** | The installed, explicitly invoked `long-term-project-manager` skill. It provides shared protocols and tools but stores no concrete project's accepted facts. It is not the project's parent objective. |
| **Child skill / 子 skill** | One project-local, explicitly invoked thin adapter. It binds a stable project identity and delegates shared behavior to a compatible total skill. Its project-owned files hold that project's data and instructions. |
| **Research content tree / 内容树** | An optional, accepted structure for research questions, dependencies, evidence assessments, and gaps. It guides candidate task planning. A tree node is a content question, not a scheduled task or a truth verdict. |
| **Project map / 项目地图** | A rebuildable view for locating the objective, confirmed tasks, their status, and an entry to an accepted content tree when present. It is derived from formal data and cannot approve a task or change research content. |
| **Task board / 任务板** | Formal scheduling data in `state/task-board.json`: `high` and `low` priorities and task lifecycle statuses. Only user-accepted task changes enter it. |
| **Formal record / 正式记录** | A user-accepted item in `records/store.json`, such as a task, claim, evidence item, or artifact. Acceptance records a project decision; it does not by itself prove an external claim. |
| **Pending work / 待审核工作** | Exploration and proposals under `work/`. They do not enter formal records, the task board, or derived views until accepted through a transaction. |
| **Transaction / 正式事务** | An itemized, user-decided change from one project revision to the next, validated before publication and followed by a receipt. Tree and task changes require separate decisions even when committed in one revision. |

For research projects, the planning direction is **content tree → candidate task → user decision → task board and map**. Execution results then return as proposed evidence or tree changes for another review. The map remains useful for navigating already confirmed work.
