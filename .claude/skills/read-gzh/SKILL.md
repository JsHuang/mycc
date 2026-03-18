---
name: read-gzh
description: 自动读取公众号文章、生成总结并上传到飞书云盘。触发词："/read-gzh"
---

# 读取公众号文章

给 cc 一个微信公众号链接，自动完成：抓取文章 → 生成结构化总结 → 上传飞书云盘

## 触发词

- `/read-gzh <链接>`

---

## 工作流程

1. **抓取文章** - 脚本自动抓取公众号内容（标题，作者，正文）
2. **AI 总结** - cc 基于抓取的内容生成结构化总结
3. **上传到飞书云盘** - 自动上传到云盘文件夹

---

## 执行流程

### Step 1: 运行自动化脚本

```bash
python .claude/skills/read-gzh/scripts/auto_read_gzh.py "<公众号链接>"
```

脚本完成后会输出：
- 文章标题
- 作者
- 正文长度

### Step 2: AI 生成总结

cc 阅读抓取的内容，按照指定格式生成结构化总结

### Step 3: 上传到飞书云盘

调用上传函数自动上传：

```python
import sys
sys.path.insert(0, '.claude/skills/read-gzh/scripts')
from auto_read_gzh import upload_to_feishu

result = upload_to_feishu(
    title="大海捞针：用 LLM 进行漏洞研究",
    content=ai_summary_content
)
```

返回文档链接和文件名。

---

## 配置

在 `.env` 中配置：

```bash
FEISHU_SAVE_TO_DOC=true
FEISHU_APP_ID=xxx
FEISHU_APP_SECRET=xxx
FEISHU_DOC_FOLDER_TOKEN=xxx
```

---

## 总结格式

```
# 📄 文章总结：<标题>

## 基本信息
- 标题：
- 作者：
- 来源：

## 背景/上下文
- 写作背景：
- 目标读者：
- 解决什么问题：

## 核心观点（详细展开）
1. 观点一：<详细说明>
   - 论据/案例：
   - 启示：
2. 观点二：<详细说明>
   - 论据/案例：
   - 启示：
3. 观点三：<详细说明>
   - 论据/案例：
   - 启示：
...（更多观点）

## 关键信息
- 重要数据/统计：
- 核心概念/术语解释：
- 技术要点：
- 工具/资源：

## 详细案例
- 案例背景：
- 具体做法：
- 结果/影响：
- 可复用的点：

## 金句摘录
> "xxx"
> "xxx"
> "xxx"

## 我的思考
- 对我有什么启发？
- 可以行动的点：

## 相关推荐
- 相关主题：
- 延伸阅读：
```

**注意**：
- 观点要详细展开，不要只列一句话
- 必须包含具体案例和数据
- 结合自己的工作/兴趣场景思考

---

*更新：2026-03-06*
