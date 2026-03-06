---
name: read-gzh
description: 读取微信公众号文章并总结。触发词："/read-gzh"、"帮我读一下这篇公众号"
---

# 读取公众号文章

给 cc 一个微信公众号链接，自动抓取文章并生成结构化总结。

## 触发词

- `/read-gzh <链接>`
- "帮我读一下这篇公众号"

---

## 工作流程

1. **抓取文章** - 脚本抓取公众号内容（标题，作者，正文）
2. **AI 总结** - cc 生成结构化总结（核心观点、关键信息、金句提取）
4. **上传到飞书云盘** - 自动上传结构化总结到云盘文件夹

---

## 执行流程

### Step 1: 抓取文章

```bash
python3 .claude/skills/read-gzh/scripts/fetch_wechat_article.py "<公众号链接>"
```

脚本会抓取：标题、作者、正文，直接输出到终端

### Step 2: AI 总结

cc 阅读抓取的内容，生成结构化总结(参考总结格式部分)

### Step 3: 上传到飞书云盘

直接上传 AI 总结内容到飞书云盘

**调用方式**：
```python
import sys
sys.path.insert(0, '.claude/skills/read-gzh/scripts')
from feishu_doc import upload_summary

result = upload_summary(
    title="2026-03-06-原文标题",  # 不含 .md 后缀
    content=ai_summary_content      # AI 总结的 markdown 内容
)
print(result['url'])  # 打印飞书文档链接
```

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
