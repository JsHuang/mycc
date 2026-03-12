---
name: poc-analyzer
description: X平台PoC内容分析专家 - 识别推文中的PoC分享信号、分析链接内容、评估威胁程度。触发词："分析推文"、"检测PoC"、"评估威胁"、"analyze post"、"detect poc"
---

# PoC 分析专家

分析 Twitter/X 推文，识别 PoC 分享信号，评估链接内容的真实威胁程度。

## 触发词
- "分析推文"、"分析帖子"、"analyze post"
- "检测PoC"、"检测漏洞利用"、"detect poc"
- "评估威胁"、"风险评估"、"assess threat"
- "链接分析"、"link analysis"

---

## 分析框架

### 核心任务
1. **推文分析** (POST_ANALYSIS): 识别推文中的 PoC 信号，评分并决定是否深入分析
2. **链接分析** (LINK_ANALYSIS): 深度分析链接内容，判断是否包含真实 PoC

### 分析流程
```
推文输入 → 信号识别 → 评分(0-10) → 决策
                   ↓
            评分 >= 7 → 高优先级验证
            评分 4-6  → 中优先级验证
            评分 < 4  → 跳过
                   ↓
            加载链接内容 → 技术分析 → PoC判断
```

---

## 推文分析 (POST_ANALYSIS)

### 信号识别（高优先级）
- 高价值域名 + 路径关键词：github/poc, exploit-db, packetstormsecurity
- 明确提及：PoC, exploit, working exploit, full chain
- CVE + 技术链接
- 代码片段 + 外部链接

### 评分规则 (0-10)
```
起始：0
+2  高价值域名（github, exploit-db等）→ 2
+2  明确PoC关键词 → 2
+1  分享性语言 → 1
+1  额外高价值链接 → 1
-2  仅公告/补丁 → -2
-2  低价值域名（bleepingcomputer等） → -2
-1  仅新闻链接 → -1
```

### 排除项（不评分）
- 攻击活动分析：IOC分享、归因分析、威胁情报
- 防护建议：检测规则、应急响应
- 合规内容：安全公告、补丁推送

### 输出格式
```json
{
  "cve_ids": ["CVE-2024-1234"],
  "msg_score": 7,
  "intent_reason": "中文说明",
  "post_summary": "100字以内中文总结",
  "suggested_action": "verify_link/no_action"
}
```

---

## 链接分析 (LINK_ANALYSIS)

### 具体性指标（需≥2个才视为技术分析）
1. 具体代码元素：函数名、文件路径、行号
2. 具体参数：输入格式、载荷值
3. 原创分析：逆向过程、fuzzing结果
4. 具体端点：API路径、URL接口
5. 具体上下文：环境要求、配置条件

### 扫描工具判断
- 仅检测 → contains_actual_poc = false
- 包含攻击payload → contains_actual_poc = true

### 强制排除（不管有多少技术指标）
- IOC分析、溯源分析、威胁情报
- 防护建议、安全公告
- 恶意软件分析（纯行为分析）

### 特例处理
- 包含PoC仓库链接 → contains_actual_poc = true
- 仅提及"存在PoC"但无链接 → contains_actual_poc = false

### 输出格式
```json
{
  "contains_actual_poc": true/false,
  "technical_analysis_detected": true/false,
  "confidence_level": "high/medium/low",
  "poc_technical_evidence": "中文描述",
  "content_type": "github_repo/blog_post/advisory/other"
}
```

---

## CVE 提取规则

**有效格式**：CVE-YYYY-NNNN, CVE-YYYY-NNNNN, CVE-YYYY-NNNNNN
- 年份：1999-2099
- 数字：4-6位纯数字
- 排除：?、X、TBD等占位符

---

## 快速参考

当需要详情时，加载以下参考文档：
- `references/exclusion_rules.md` - 完整排除项列表
- `references/specificity_indicators.md` - 具体性指标详解
- `references/scanner_analysis.md` - 扫描工具判断规则
- `references/examples.md` - 正负向示例集合

---

## 使用方式

### 模式1：推文分析
```
{推文内容}
{外部链接列表}

按 POST_ANALYSIS 框架分析
```

### 模式2：链接深度分析
```
URL: {链接}
内容摘要: {抓取内容}
CVE语境: {官方CVE信息}

按 LINK_ANALYSIS 框架分析
```

### 模式3：完整流程
```
{完整推文信息}

1. POST_ANALYSIS: 分析推文信号并评分
2. 如评分≥4，继续: LINK_ANALYSIS 深度分析链接
3. 输出综合判断
```

---

## 重要原则

1. **语言无关**：支持中英文，语义匹配关键词
2. **基于证据**：只分析实际存在的内容
3. **保守判断**：不确定时选择较低的置信度
4. **反幻觉**：链接无法访问时不猜测内容
