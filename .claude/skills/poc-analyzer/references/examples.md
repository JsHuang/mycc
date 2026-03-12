# PoC 分析示例集合

## ✅ 正向示例（contains_actual_poc = true）

### 1. HTTP请求参数注入
```
"Send POST /api/login with body {"user":"admin'--", ...} to bypass auth"
→ 包含具体的HTTP请求和参数值
```

### 2. 内存溢出分析
```
"Overflow occurs at offset 0x48, overwrite return address with gadget at 0xdeadbeef"
→ 包含具体的内存偏移值和地址
```

### 3. 复现步骤指南
```
1. Install version 2.3.1
2. Configure X
3. Execute: curl -X POST ...
4. Observe shell
→ 清晰的复现步骤和命令
```

### 4. 漏洞触发代码
```python
requests.post(url, data={'cmd': '; cat /etc/passwd'})
→ 实际的漏洞利用代码
```

### 5. PoC仓库链接
```
参考 https://github.com/user/CVE-2025-XXXXX-poc 仓库
→ 包含PoC仓库链接本身就足够判定
```

### 6. Nuclei攻击模板
```yaml
body: "username=admin';--&password=any"
→ 包含SQL注入payload
```

---

## ❌ 负向示例（contains_actual_poc = false）

### 1. 仅描述漏洞结果
```
"This vulnerability allows attackers to execute arbitrary code by exploiting a buffer overflow"
→ 只说WHAT，没说HOW
```

### 2. 仅版本和影响信息
```
Affected versions: 1.0-2.5
Impact: Critical
Fix: Update to 2.6
→ 没有技术细节
```

### 3. 泛化的根本原因
```
"The vulnerability exists in the authentication module due to improper input validation"
→ 无具体利用方法
```

### 4. 理论性影响声明
```
"Attackers could potentially leverage this flaw to gain unauthorized access"
→ 理论描述，无实际步骤
```

### 5. 简单的漏洞公告
```
"A remote code execution vulnerability was discovered in Product X"
→ 纯公告，无细节
```

### 6. 仅提及存在PoC
```
"The official advisory contains PoC demonstrating the attack steps"
（没有提供PoC链接）
→ contains_actual_poc = false
→ technical_analysis_summary: "本页面提到存在PoC，但未提供PoC链接"
```

### 7. 纯检测工具
```
"This scanner checks if your React application is using a vulnerable version"
→ 仅检测，不包含利用逻辑
```

### 8. 被动Nuclei模板
```
Template only matches version in HTTP response header
→ 仅匹配版本，无攻击payload
```

---

## ⚠️ 边界案例

### 案例1：技术分析文章（边界）
```
原文：
"我们分析了CVE-2024-1234，发现它影响parseXML函数。
当输入超过1MB时会崩溃。我们编写了fuzzer并发现了多个类似问题。"

分析：
✅ 具体函数名：parseXML
✅ 具体输入条件：超过1MB
✅ 原创分析：编写了fuzzer
→ 3个具体性指标 → technical_analysis_detected = true
→ 但无完整复现步骤 → contains_actual_poc = false
```

### 案例2：博客文章 + GitHub链接（边界）
```
原文：
"这个RCE漏洞很有趣，详情见 https://github.com/user/CVE-2025-XXXXX-research"

分析：
→ 包含GitHub PoC研究链接
→ contains_actual_poc = true（链接本身就足够）
```

### 案例3：部分信息（边界）
```
原文：
"漏洞在 /api/upload 接口，需要特殊构造的请求才能触发"

分析：
✅ 具体端点：/api/upload
❌ 无具体参数值
❌ 无具体构造方法
→ 1个具体性指标 → technical_analysis_detected = false
→ 信息不足，无法复现 → contains_actual_poc = false
```

---

## 评分案例

### 案例1：高质量PoC ✅
```
评分：
- 具体代码元素：parseXML()函数 + 127行 → 1
- 具体参数：Content-Length > 0x7fffffff → 1
- 原创分析：逆向分析过程 → 1
- 具体端点：/api/v2/admin/import → 1
- 具体上下文：DEBUG=true + memcached → 1

总分：5 ≥ 2 → technical_analysis_detected = true
置信度：high
```

### 案例2：中等质量分析 ⚠️
```
评分：
- 具体端点：/wp-json/wp/v2/users → 1
- 具体参数：{"role":"administrator"} → 1
- 无原创分析：❌
- 无代码元素：❌
- 无具体上下文：❌

总分：2 ≥ 2 → technical_analysis_detected = true
置信度：medium
```

### 案例3：低质量文章 ❌
```
评分：
- 无代码元素：❌
- 无具体参数：❌
- 无原创分析：❌
- 无具体端点：❌
- 无具体上下文：❌

总分：0 < 2 → technical_analysis_detected = false
包含CVE描述和CVSS评分 → 但无复现价值
```