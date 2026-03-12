# 具体性指标详解

## 判断标准
设置 `technical_analysis_detected = true` 需要内容包含 **至少2个** 以下指标。

---

## 1. 具体代码元素

### ✅ 有效示例
- "漏洞存在于 `parseXML()` 函数的第127行"
- "The vulnerable code is in `src/auth/validator.js:validateToken()`"
- "检查 `UserController::handleRequest()` 方法"
- "在 `lib/crypto.cpp` 的 `encrypt()` 函数中"

### ❌ 无效示例
- "漏洞存在于解析模块" （太笼统）
- "vulnerability in the authentication component" （太泛化）
- "代码有问题" （无具体信息）

---

## 2. 具体参数/输入

### ✅ 有效示例
- "当 `Content-Length` 超过 `0x7fffffff` 时触发溢出"
- "Setting `admin=true` in the JWT payload bypasses authorization"
- "The payload `{{$ne:1}}` in the password field causes NoSQL injection"
- "发送 `{'cmd': '; cat /etc/passwd'}` 作为参数"

### ❌ 无效示例
- "通过发送恶意请求触发" （太模糊）
- "by sending crafted input" （无具体值）
- "特殊输入导致问题" （无具体参数）

---

## 3. 原创分析内容

### ✅ 有效示例
- "我们通过逆向分析发现..." / "经过fuzzing测试，我们发现..."
- "During our research, we identified that..."
- "By tracing the call stack, we found..."
- "在调试过程中，我们观察到..."

### ❌ 无效示例
- 纯复制CVE描述
- 重写厂商公告但无新见解
- "根据官方公告，这个漏洞..." （无原创分析）

---

## 4. 具体漏洞端点/接口

### ✅ 有效示例
- "The `/api/v2/admin/import` endpoint is vulnerable when..."
- "漏洞存在于 `/wp-json/wp/v2/users` 接口"
- "The SOAP action `ExecuteCommand` can be exploited..."
- "通过 `/rest/api/2/user/picker` 路径访问"

### ❌ 无效示例
- "an API endpoint is vulnerable" （太泛化）
- "某个接口存在问题" （无具体路径）
- "web接口有漏洞" （太笼统）

---

## 5. 具体技术上下文

### ✅ 有效示例
- "When running with `DEBUG=true` and memcached enabled..."
- "Requires default installation with anonymous binding enabled"
- "漏洞需要在开启了X功能且使用Y数据库的情况下才能触发"
- "仅影响版本 2.3.1 至 2.5.0，且配置了Z选项时"

### ❌ 无效示例
- "under certain conditions" （太模糊）
- "在特定环境下" （无具体条件）
- "某些配置下可能受影响" （无具体信息）

---

## 评分方法

### 计算指标数量
```
具体代码元素     → 有/无 (1/0)
具体参数/输入    → 有/无 (1/0)
原创分析内容     → 有/无 (1/0)
具体漏洞端点     → 有/无 (1/0)
具体技术上下文   → 有/无 (1/0)

总分 = 各指标之和
```

### 判断规则
- **总分 ≥ 2** → `technical_analysis_detected = true`
- **总分 < 2** → 需要额外检查其他技术细节

---

## 注意事项

1. **质量优先**：确保指标确实提供了具体信息，而非泛泛而谈
2. **语言无关**：中英文都可以，关键是具体性
3. **组合判断**：多个模糊信息组合起来可能提供足够具体性
4. **上下文考虑**：某些领域可能需要调整具体性标准

---

## 常见误区

### 误区1：技术术语 = 具体性
❌ "这是一个RCE漏洞，攻击者可以执行任意代码"
→ 仅描述了漏洞类型，没有具体复现信息

### 误区2：细节 = 具体性
❌ "漏洞很严重，CVSS评分9.8，影响广泛"
→ 严重程度不等于技术具体性

### 误区3：代码存在 = 具体性
❌ "存在漏洞代码，需要修复"
→ 必须指明具体位置或触发条件

---

## 实战案例

### 案例1：优质技术分析 ✅
```
漏洞位于 parseRequest() 函数（具体代码元素）
当 Content-Length > 0x7fffffff 时触发（具体参数）
我们在调试中发现调用栈：main → handle → parseRequest（原创分析）
通过 POST /api/upload 接口触发（具体端点）

→ 4个指标，technical_analysis_detected = true
```

### 案例2：劣质技术文章 ❌
```
这是一个严重的RCE漏洞
影响版本 1.0-2.5
建议立即更新到 2.6 版本
CVSS评分 9.8

→ 0个具体性指标，technical_analysis_detected = false
```