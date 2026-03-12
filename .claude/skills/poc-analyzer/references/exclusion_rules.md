# 攻击活动分析排除规则

## 1. IOC 分析 (入侵指标)
- "IOCs", "indicators of compromise", "threat indicators", "入侵指标"
- 多个MD5/SHA1/SHA256哈希值
- YARA规则、Sigma规则、检测规则

## 2. 归因与活动分析
- APT组织名称：APT28, Lazarus, FIN7, Carbanak
- "attributed to", "linked to", "campaign analysis", "溯源分析"
- "攻击团伙", "APT组织"

## 3. 应急响应与取证
- "incident response", "forensic analysis", "breach investigation", "应急响应"
- "取证分析", "入侵调查"
- "attack timeline", "lateral movement observed", "data exfiltration"

## 4. 威胁情报
- "threat intel", "intelligence report", "威胁情报", "情报共享"
- "threat sharing", "IOC feed"
- "MISP", "ThreatConnect", "AlienVault OTX"

## 5. 防御建议
- "how to detect", "defense against", "防护建议", "检测规则"
- "monitoring for", "signs of"
- "protect from", "prevent", "mitigate"

## 6. 恶意软件分析
- "malware family", "malware analysis", "沙箱分析", "僵尸网络分析"
- "sandbox report", "dynamic analysis" (仅行为分析)
- "C2 infrastructure", "command and control"

## 7. 合规与安全公告
- "security bulletin", "patch Tuesday", "合规报告", "安全更新"
- "risk assessment", "vulnerability scanner", "security scan"

## 8. 其他排除项
- 仅包含IP地址、域名、文件哈希的列表
- 纯粹的统计报告、趋势分析
- 安全培训、意识教育内容

## 重要原则
- **优先级最高**：任何上述特征出现，立即设置 technical_analysis_detected = false
- **不进行判断**：如果内容属于上述类别，不要尝试评估其技术深度
- **保持中立**：即使内容包含技术术语，只要属于上述类别，就视为非PoC内容