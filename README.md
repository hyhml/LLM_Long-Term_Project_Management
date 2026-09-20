# LLM Long-Term Project Management

一个面向 Codex CLI 的显式调用 skill，用项目本地状态、探索交接包和用户逐项确认，实现跨对话协作与长期项目管理。

## 安装

将仓库克隆或链接到 Codex 的用户 skill 目录，并确保目录名与 skill 名一致：

```bash
git clone --depth 1 --single-branch --branch main \
  https://github.com/hyhml/LLM_Long-Term_Project_Management.git \
  ~/.agents/skills/long-term-project-manager
```

`main` 只包含用户运行所需内容。架构决策记录位于单独的 `development` 分支；上述单分支安装不会下载该分支。只有框架开发者需要切换到 `development`。

重启 Codex 后显式调用：

```text
$long-term-project-manager 初始化这个项目
```

该 skill 不允许隐式调用。第一次运行会提出本机环境档案草案；只有用户确认后才保存。创建项目子 skill 时，也会先展示项目目标、完成标准、项目地图和高低优先级待办，确认后才写入 `.agents/skills/<project-skill>/`。

## 工作循环

1. 整理对话维护项目地图、数据库和已确认待办。
2. 探索对话只执行一个已确认任务，不修改管理状态。
3. 探索对话导出单文件 `.llmpack`。
4. 整理对话校验并解包，逐项提出变更。
5. 用户逐项接受、修改、拒绝或暂缓后，才提交项目状态。

`.llmpack` 使用逐文件 SHA-256 校验完整性，但当前版本不提供发送者身份认证。导入的脚本不会自动执行。

## 开发验证

```bash
python -m unittest discover -s tests -v
python /path/to/skill-creator/scripts/quick_validate.py .
```
