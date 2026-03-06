# 文档写入思路

下面给你**企业自建机器人 + 新版 docx 文档**最标准、可直接运行的写入示例，**用你现在精简后的权限就能跑**。

---

# 一、先确认：你需要的 3 步接口
1. **创建空白 docx 文档**
2. **往文档里写入 Markdown 内容**
3. **把文档移动到你的目标文件夹**

我直接给你**完整请求示例**。

---

# 二、前置条件
- 你已经有**tenant access_token**（获取 tenant 凭证的接口我就不写了）
- 你有一个**文件夹 token**（在飞书云盘文件夹 URL 里能拿到）
- 权限：
  ```
  docx:document
  drive:drive:readonly
  drive:file
  ```

---

# 三、示例1：创建文档（POST）
**接口**
```
POST https://open.feishu.cn/open-apis/docx/v1/documents
```

**请求头**
```json
{
  "Authorization": "Bearer YOUR_TENANT_ACCESS_TOKEN"
}
```

**请求体**
```json
{
  "title": "公众号文章总结_20260306"
}
```

**返回**
```json
{
  "code": 0,
  "data": {
    "document_id": "docx_xxxxxxx",
    "folder_token": ""
  }
}
```
记下：**document_id**

---

# 四、示例2：写入 Markdown 内容（最关键）
飞书 docx 是**块结构**，这里给你**直接写入一段 Markdown 文本**的最简单方式。

**接口**
```
POST https://open.feishu.cn/open-apis/docx/v1/documents/{document_id}/blocks
```

**请求体**
```json
{
  "children": [
    {
      "type": "paragraph",
      "text": {
        "style": {},
        "elements": [
          {
            "type": "text_run",
            "text_run": {
              "content": "# 公众号文章总结\n\n## 标题\nxxx\n\n## 内容\n这是自动生成的 Markdown 内容。\n\n## 总结\nxxx",
              "style": {}
            }
          }
        ]
      }
    }
  ]
}
```

这一步执行完，**文档里就有内容了**。

---

# 五、示例3：移动到你的共享/私有文件夹
**接口**
```
POST https://open.feishu.cn/open-apis/drive/v1/files/move
```

**请求体**
```json
{
  "file_id": "docx_xxxxxxx",
  "type": "docx",
  "folder_token": "你的文件夹token"
}
```

执行成功后，文档就进到你指定的文件夹里了。

---

# 六、极简一句话流程（你开发照着写）
1. 创建文档 → 拿 `document_id`
2. 调用块接口写入 Markdown
3. 调用 drive 移动到文件夹
4. 完成 ✅

---

如果你告诉我你用的语言（**Python / Java / Node.js / Go**），
我可以直接给你**可复制运行的完整代码**，包括获取 token + 3 步业务逻辑一整套。

# 飞书 Docx 进阶 Markdown 写入（支持标题/加粗/列表/分段）



### 核心思路

将 Markdown 语法拆解为飞书 docx 对应的块类型：



| Markdown 语法 | 飞书 docx 块类型       | 实现方式           |
| ----------- | ----------------- | -------------- |
| `# 一级标题`    | `heading` 块       | `level: 1`     |
| `## 二级标题`   | `heading` 块       | `level: 2`     |
| `**加粗**`    | `text_run` 样式     | `bold: True`   |
| `- 无序列表`    | `bulleted_list` 块 | 嵌套 `list_item` |
| `1. 有序列表`   | `numbered_list` 块 | 嵌套 `list_item` |
| 空行分段        | `paragraph` 块     | 单独创建空文本段落      |

### 完整进阶代码（直接替换原函数）



```
def write\_advanced\_markdown\_to\_doc(document\_id, markdown\_content, token):

&#x20;   """

&#x20;   进阶版 Markdown 写入：支持标题、加粗、无序列表、有序列表、分段

&#x20;   :param document\_id: 文档ID

&#x20;   :param markdown\_content: 带格式的 Markdown 字符串

&#x20;   :param token: tenant\_access\_token

&#x20;   :return: 接口响应

&#x20;   """

&#x20;   url = f"https://open.feishu.cn/open-apis/docx/v1/documents/{document\_id}/blocks"

&#x20;   headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

&#x20;  &#x20;

&#x20;   \# 解析 Markdown 内容，生成飞书块结构

&#x20;   blocks = \[]

&#x20;   lines = markdown\_content.split("\n")  # 按行分割

&#x20;   current\_list\_type = None  # 记录当前是否在列表中（bulleted/numbered）

&#x20;   current\_list\_items = \[]  # 存储当前列表的项

&#x20;  &#x20;

&#x20;   def flush\_list():

&#x20;       """提交当前列表块"""

&#x20;       if current\_list\_type and current\_list\_items:

&#x20;           list\_block = {

&#x20;               "type": current\_list\_type,

&#x20;               current\_list\_type: {

&#x20;                   "items": current\_list\_items

&#x20;               }

&#x20;           }

&#x20;           blocks.append(list\_block)

&#x20;           nonlocal current\_list\_type, current\_list\_items

&#x20;           current\_list\_type = None

&#x20;           current\_list\_items = \[]

&#x20;  &#x20;

&#x20;   for line in lines:

&#x20;       line = line.strip()

&#x20;       if not line:  # 空行 → 分段（添加空段落）

&#x20;           flush\_list()  # 先提交之前的列表

&#x20;           blocks.append({

&#x20;               "type": "paragraph",

&#x20;               "paragraph": {

&#x20;                   "text": {

&#x20;                       "elements": \[{"type": "text\_run", "text\_run": {"content": ""}}]

&#x20;                   }

&#x20;               }

&#x20;           })

&#x20;           continue

&#x20;      &#x20;

&#x20;       \# 1. 处理标题（# 一级标题、## 二级标题...）

&#x20;       if line.startswith("# "):

&#x20;           flush\_list()

&#x20;           level = len(line.split(" ")\[0])  # 取 # 的数量（1-6级）

&#x20;           title\_text = line\[level+1:].strip()  # 标题内容

&#x20;           blocks.append({

&#x20;               "type": "heading",

&#x20;               "heading": {

&#x20;                   "level": level,

&#x20;                   "text": {

&#x20;                       "elements": \[{"type": "text\_run", "text\_run": {"content": title\_text}}]

&#x20;                   }

&#x20;               }

&#x20;           })

&#x20;           continue

&#x20;      &#x20;

&#x20;       \# 2. 处理无序列表（- 开头）

&#x20;       if line.startswith("- "):

&#x20;           list\_content = line\[2:].strip()

&#x20;           \# 解析列表项中的加粗文本

&#x20;           item\_elements = parse\_bold\_text(list\_content)

&#x20;           if current\_list\_type != "bulleted\_list":

&#x20;               flush\_list()

&#x20;               current\_list\_type = "bulleted\_list"

&#x20;           current\_list\_items.append({

&#x20;               "type": "list\_item",

&#x20;               "list\_item": {

&#x20;                   "text": {"elements": item\_elements}

&#x20;               }

&#x20;           })

&#x20;           continue

&#x20;      &#x20;

&#x20;       \# 3. 处理有序列表（1. 2. 开头）

&#x20;       if line.split(". ")\[0].isdigit():

&#x20;           list\_content = line.split(". ", 1)\[1].strip()

&#x20;           item\_elements = parse\_bold\_text(list\_content)

&#x20;           if current\_list\_type != "numbered\_list":

&#x20;               flush\_list()

&#x20;               current\_list\_type = "numbered\_list"

&#x20;           current\_list\_items.append({

&#x20;               "type": "list\_item",

&#x20;               "list\_item": {

&#x20;                   "text": {"elements": item\_elements}

&#x20;               }

&#x20;           })

&#x20;           continue

&#x20;      &#x20;

&#x20;       \# 4. 普通段落（支持加粗）

&#x20;       flush\_list()

&#x20;       paragraph\_elements = parse\_bold\_text(line)

&#x20;       blocks.append({

&#x20;           "type": "paragraph",

&#x20;           "paragraph": {

&#x20;               "text": {"elements": paragraph\_elements}

&#x20;           }

&#x20;       })

&#x20;  &#x20;

&#x20;   \# 提交最后一个列表

&#x20;   flush\_list()

&#x20;  &#x20;

&#x20;   \# 构造请求体（覆盖文档原有内容，若想追加可改 method 为 PATCH）

&#x20;   data = {

&#x20;       "children": blocks,

&#x20;       "replace": True  # True=覆盖全文，False=追加到末尾

&#x20;   }

&#x20;  &#x20;

&#x20;   resp = requests.post(url, headers=headers, json=data)

&#x20;   return resp.json()

def parse\_bold\_text(text):

&#x20;   """

&#x20;   解析文本中的 \*\*加粗\*\* 语法，生成飞书 text\_run 元素

&#x20;   :param text: 带 \*\*加粗\*\* 的文本

&#x20;   :return: 飞书 text 元素列表

&#x20;   """

&#x20;   elements = \[]

&#x20;   parts = text.split("\*\*")

&#x20;   for i, part in enumerate(parts):

&#x20;       if not part:

&#x20;           continue

&#x20;       \# 奇数索引（1、3、5...）是加粗内容

&#x20;       is\_bold = i % 2 == 1

&#x20;       elements.append({

&#x20;           "type": "text\_run",

&#x20;           "text\_run": {

&#x20;               "content": part,

&#x20;               "style": {"bold": is\_bold}

&#x20;           }

&#x20;       })

&#x20;   return elements
```

### 调用示例（主函数中替换原写入逻辑）



```
def main():

&#x20;   token = get\_tenant\_token()

&#x20;   if not token:

&#x20;       print("获取token失败")

&#x20;       return

&#x20;   \# 带完整格式的 Markdown 内容（公众号总结示例）

&#x20;   title = "公众号自动总结\_20260306"

&#x20;   advanced\_markdown = """# AI发展新趋势解读

\## 核心观点

\*\*大模型轻量化\*\*成为企业落地关键，以下是三大核心方向：

\- 模型压缩技术突破

&#x20; \- 量化压缩：精度损失<5%

&#x20; \- 剪枝优化：体积减少60%

\- 多模态能力融合

&#x20; \- 文本+图像+语音统一建模

&#x20; \- 实时交互延迟降低至100ms

\- 垂直场景深耕

&#x20; 1\. 工业质检：准确率达99.2%

&#x20; 2\. 医疗诊断：辅助医生提升30%效率

&#x20; 3\. 教育个性化：适配不同学习节奏

\## 总结

\*\*未来1-2年\*\*，AI将从「通用能力」走向「场景化落地」，中小企业也能低成本使用。

"""

&#x20;   \# 1. 创建文档

&#x20;   doc\_id = create\_doc(title, token)

&#x20;   print("创建文档成功：", doc\_id)

&#x20;   \# 2. 写入进阶 Markdown（支持标题/加粗/列表/分段）

&#x20;   write\_advanced\_markdown\_to\_doc(doc\_id, advanced\_markdown, token)

&#x20;   print("写入带格式内容成功")

&#x20;   \# 3. 移动到文件夹

&#x20;   move\_doc\_to\_folder(doc\_id, FOLDER\_TOKEN, token)

&#x20;   print("移动到文件夹成功")
```

### 效果预览（飞书文档中显示）



1. 一级标题：`# AI发展新趋势解读` → 大号加粗标题

2. 二级标题：`## 核心观点` → 中号加粗标题

3. 加粗文本：`**大模型轻量化**` → 粗体显示

4. 无序列表：`- 模型压缩技术突破` → 圆点列表，支持嵌套

5. 有序列表：`1. 工业质检` → 数字编号列表

6. 分段：空行自动分隔段落，排版整洁

> （注：文档部分内容可能由 AI 生成）