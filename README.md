# ChatGPT Export Archive

把 ChatGPT 导出记录整理成轻量的本地档案，供人阅读，也供 Agent 搜索。

按原项目分类、拆分长会话，提供分页 HTML、Markdown 和消息级查询。只需 Python 标准库，无数据库、无模型调用，记录在本机处理。

## 快速开始

需要 **Python 3.10+**。Windows 可以运行 `python --version` 检查；其他系统通常使用 `python3`。没有需要安装的 Python 依赖。

1. 解压 ChatGPT 导出压缩包。输入目录需包含 `conversations.json` 或 `conversations-*.json`；保留同目录中的附件文件。
2. 双击 **转换导出记录.bat**，选择导出目录，等待转换完成。
3. 双击 **打开阅读器.bat**，浏览器会打开最近转换成功的档案。

当前启动器会保留一个命令行窗口，关闭它或按 Ctrl+C 即停止服务；只关闭浏览器标签页不会停止服务。服务只监听本机地址，不对局域网开放。后台无窗口快捷方式尚未实现。

不启动服务也可以打开生成的 `index.html`，浏览项目、会话和筛选标题／提问摘录；**网页全文搜索需要启动阅读器**。

### 用命令行转换与阅读

以下命令在工具目录运行。路径请替换为自己的输入目录：

```powershell
python archive.py build "D:\Exports\ChatGPT"
python archive.py serve --open
```

每次转换会生成新的 `archives/导出目录名-时间/`，不会覆盖旧档案。也可以明确指定一个尚不存在的输出目录：

```powershell
python archive.py build "D:\Exports\ChatGPT" --out "D:\Archives\chat-2026-10"
python archive.py serve --archive "D:\Archives\chat-2026-10" --open
```

未指定 `--archive` 时，工具读取 `last-archive.txt` 中最近成功转换的档案。移动工具或换一台电脑后，如果旧路径失效，请通过 `--archive` 指定当前路径，或重新转换。

默认每次启动使用系统分配的空闲端口。需要固定浏览器地址时可使用 `--port 8765 --open`；主题、字号等浏览器偏好与站点地址有关，端口变化时不一定沿用。

## 阅读与查找

- **项目目录**：按导出中的原项目 ID 分类，保留名称映射。未归入项目、自定义 GPT 会话单列。
- **排序**：项目和会话按最后聊天时间从新到旧排列；月份筛选采用会话最后聊天月份，不是每条命中消息的月份。
- **分页**：项目每页 12 组，会话和全文搜索每批 40 条；长会话另有分页目录和正文页。
- **正文**：用户消息显示在右侧气泡；同一轮 GPT 回复连续展示，思考、搜索和耗时合并折叠。不同分支不合并，跨页内容在各页独立展示。
- **阅读偏好**：右上角切换浅色／深色；正文支持 16、18、20 三档字号。
- **返回位置**：保留项目、页码、筛选条件和滚动位置，支持刷新及浏览器前进／后退。

输入框会筛选标题和提问摘录。进入会话列表后，点击“搜索全文”或按回车查询正文。默认只搜当前路径中的**用户原话**；可以切换为所有角色或包含其他分支。

搜索是大小写不敏感的连续文本匹配，没有语义检索。记不清原话时，分别试几个短关键词。没有命中不能证明从未讨论过。

## 给 Agent 使用

**Agent 无需启动阅读器或后台服务。** 直接调用脚本即可获得 JSON 结果、上下文和消息定位链接。

```powershell
python archive.py projects --limit 12
python archive.py conversations --project "g-p-项目ID" --limit 20
python archive.py search "长期记忆" --limit 10
python archive.py search "关键词" --project "g-p-项目ID" --role all
python archive.py read "会话ID" --message "消息ID" --context 3
```

新 Agent 先阅读 [Agent 查询说明](docs/agent-usage.md)，再告知它本机脚本和档案的路径。每份生成档案内也有 `给Agent的说明.md`。

常用流程：**找到项目 → 搜关键词 → 读取上下文 → 给出结论和原记录链接**。读取支持长度预算，搜索及列表支持分页，避免把全部历史塞进上下文。

工具不会自动写入 Agent 的长期记忆，也不会自动收集后续新聊天；需要另行导入新的导出记录。

## 项目名称

项目归属使用导出中的 `conversation_template_id`。导出可能不含项目名称，因此可提供名称映射：

1. 复制 `project-names.example.json` 为 `project-names.json`。
2. 将示例 ID 和名称替换成自己的原项目 ID 与项目名称。
3. 转换时自动读取工具目录内的 `project-names.json`；也可用 `--project-names "映射文件路径"` 指定其他文件。

没有名称映射时仍按原 ID 分类，显示 ID，不根据聊天内容猜项目名。工具不自动联网获取名称。

## 附件与完整性

**生成档案是阅读副本，不是独立的完整备份。** 图片和附件引用原导出目录，不复制大附件；请同时保留原导出。

- 每条消息保留稳定定位点；Agent 返回的链接可以直接定位正文或展开过程记录。
- Markdown 和消息索引保留原话、消息 ID、父节点和分支关系。
- 当前路径按 `current_node` 父链还原；缺少有效节点时明确标记回退，其余分支另存。
- 非文本对象保留原始 JSON 表示，导出中缺失的附件无法由工具还原。
- HTML 支持常用 Markdown 排版；复杂嵌套和数学公式采用简化展示，公式保留原文。
- 只处理会话 JSON，不合并群聊、账户资料、Codex 元数据等其他独立数据。

只更改项目名称或移动原导出目录时，可更新目录与附件路径：

```powershell
python archive.py refresh --archive "D:\Archives\chat-2026-10" --source "D:\Exports\ChatGPT"
```

`refresh` 会校验源会话 JSON 的 SHA-256；输入内容改变时应重新 `build`。它不会重新生成所有正文排版。升级阅读器后刷新浏览器；需要完整应用新转换格式时，新建一次档案。

转换中断时会留下 `build-in-progress.json`，该目录不会被作为成功档案。排查后选一个新输出目录重试。

## 目录与 GitHub 同步

仓库：[HuanHuanHuanFFF/chatgpt-export-archive](https://github.com/HuanHuanHuanFFF/chatgpt-export-archive)。

```text
archive.py                   转换、阅读服务和 Agent 查询入口
README.md                    使用说明
打开阅读器.bat               Windows 阅读入口
转换导出记录.bat             Windows 转换入口
project-names.example.json   可提交的虚构名称映射示例
docs/agent-usage.md          Agent 查询说明
tests/                       功能与导航检查
.gitignore                   本地数据忽略规则

archives/                    本地生成档案（忽略）
project-names.json            个人项目名称（忽略）
last-archive.txt              本机档案路径（忽略）
```

同步工具源码即可；`.gitignore` 已忽略生成档案、个人项目映射、启动路径、缓存和临时测试文件。若需把原始导出放在工具目录内，请统一放入 `exports/`（已忽略）。自定义到其他位置的数据目录需自行加入忽略规则。

提交前用 `git status --short` 查看准备同步的文件。忽略规则不会移除已经提交过的数据；已有仓库需另外检查历史。

生成档案的主要文件：

| 文件 | 用途 |
| --- | --- |
| `index.html`、`catalog.js` | 分页目录与元数据 |
| `项目索引.jsonl`、`会话索引.jsonl` | 按项目、会话定位 |
| `用户原话.jsonl` | 用户消息搜索索引 |
| `build-report.json` | 完成状态、源文件哈希与数量 |
| `assets.json` | 原始附件路径 |
| `conversations/<稳定ID>/part-*.html`、`.md` | 分页正文 |
| `conversations/<稳定ID>/manifest.json` | 消息、分支及正文 UTF-8 字节位置 |

## 开发检查

```powershell
python -B -m unittest discover -s tests -v
```

安装 Node.js 时还会运行导航检查；日常使用只需 Python。转换时一次解析一个 JSON 分片，超大分片仍需相应内存；阅读时仅加载选中的正文页。

## 许可证

采用 [MIT License](LICENSE)。允许使用、修改和分发，包括商业用途；分发时保留许可证及版权声明。
