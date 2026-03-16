#!/usr/bin/env node
/**
 * 飞书流式表格卡片演示
 *
 * 演示 CardKit 流式更新 + Markdown 表格
 */

import fs from 'fs';
import path from 'path';

// 加载环境变量
const envPath = path.join(process.cwd(), '.env');
if (fs.existsSync(envPath)) {
  const envContent = fs.readFileSync(envPath, 'utf-8');
  envContent.split('\n').forEach(line => {
    const [key, ...valueParts] = line.split('=');
    if (key && valueParts.length > 0) {
      process.env[key.trim()] = valueParts.join('=').trim();
    }
  });
}

const FEISHU_APP_ID = process.env.FEISHU_APP_ID;
const FEISHU_APP_SECRET = process.env.FEISHU_APP_SECRET;
const FEISHU_RECEIVE_USER_ID = process.env.FEISHU_RECEIVE_USER_ID;

if (!FEISHU_APP_ID || !FEISHU_APP_SECRET || !FEISHU_RECEIVE_USER_ID) {
  console.error("错误: 未设置飞书环境变量");
  process.exit(1);
}

// ==================== token cache ====================

const tokenCache = new Map();

async function getFeishuToken() {
  const key = FEISHU_APP_ID;
  const cached = tokenCache.get(key);
  if (cached && cached.expiresAt > Date.now() + 60000) return cached.token;

  const res = await fetch(
    "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ app_id: FEISHU_APP_ID, app_secret: FEISHU_APP_SECRET }),
    }
  );
  const data = (await res.json());
  if (data.code !== 0 || !data.tenant_access_token)
    throw new Error(`Token error: ${data.msg}`);
  tokenCache.set(key, {
    token: data.tenant_access_token,
    expiresAt: Date.now() + (data.expire ?? 7200) * 1000,
  });
  return data.tenant_access_token;
}

// ==================== 流式卡片类 ====================

class StreamingCard {
  constructor() {
    this.cardId = null;
    this.messageId = null;
    this.sequence = 0;
    this.closed = false;
    this.queue = Promise.resolve();
  }

  async start() {
    if (this.cardId) return;

    const token = await getFeishuToken();

    const cardJson = {
      schema: "2.0",
      config: {
        streaming_mode: true,
        summary: { content: "[生成表格中...]" },
        streaming_config: {
          print_frequency_ms: { default: 30 },
          print_step: { default: 1 },
        },
      },
      body: {
        elements: [{ tag: "markdown", content: "正在分析数据...", element_id: "content" }],
      },
    };

    const createRes = await fetch(
      "https://open.feishu.cn/open-apis/cardkit/v1/cards",
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ type: "card_json", data: JSON.stringify(cardJson) }),
      }
    );
    const createData = (await createRes.json());
    if (createData.code !== 0 || !createData.data?.card_id) {
      throw new Error(`CardKit 创建失败 (code ${createData.code}): ${createData.msg}`);
    }
    this.cardId = createData.data.card_id;

    const cardContent = JSON.stringify({ type: "card", data: { card_id: this.cardId } });
    const sendRes = await fetch(
      `https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          receive_id: FEISHU_RECEIVE_USER_ID,
          msg_type: "interactive",
          content: cardContent,
        }),
      }
    );
    const sendData = (await sendRes.json());
    if (sendData.code !== 0 || !sendData.data?.message_id) {
      throw new Error(`发送卡片失败 (code ${sendData.code}): ${sendData.msg}`);
    }
    this.messageId = sendData.data.message_id;

    console.log(`✓ 流式卡片已启动`);
    console.log(`  Card ID: ${this.cardId}`);
    console.log(`  Message ID: ${this.messageId}\n`);
  }

  async update(text) {
    if (!this.cardId || this.closed) return;

    this.sequence += 1;
    const seq = this.sequence;
    const cardId = this.cardId;
    this.queue = this.queue.then(async () => {
      const token = await getFeishuToken();
      const updateRes = await fetch(
        `https://open.feishu.cn/open-apis/cardkit/v1/cards/${cardId}/elements/content/content`,
        {
          method: "PUT",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            content: text,
            sequence: seq,
            uuid: `s_${cardId}_${seq}`,
          }),
        }
      );
      if (!updateRes.ok) {
        console.error(`更新失败 (sequence=${seq})`);
      }
    });
    await this.queue;
  }

  async close(finalText) {
    if (this.closed || !this.cardId) return;
    this.closed = true;
    await this.queue;

    const token = await getFeishuToken();
    const cardId = this.cardId;

    this.sequence += 1;
    const seq1 = this.sequence;
    await fetch(
      `https://open.feishu.cn/open-apis/cardkit/v1/cards/${cardId}/elements/content/content`,
      {
        method: "PUT",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          content: finalText,
          sequence: seq1,
          uuid: `c_${cardId}_${seq1}`,
        }),
      }
    ).catch(() => {});

    this.sequence += 1;
    const seq2 = this.sequence;
    const summary = finalText.slice(0, 50) + "...";
    await fetch(
      `https://open.feishu.cn/open-apis/cardkit/v1/cards/${cardId}/settings`,
      {
        method: "PATCH",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json; charset=utf-8",
        },
        body: JSON.stringify({
          settings: JSON.stringify({
            config: {
              streaming_mode: false,
              summary: { content: summary },
            },
          }),
          sequence: seq2,
          uuid: `c_${cardId}_${seq2}`,
        }),
      }
    ).catch(() => {});

    console.log(`✓ 流式卡片已完成 (${this.sequence} 次更新)`);
  }
}

// ==================== 带表格的演示文本 ====================

async function main() {
  console.log("=== 飞书流式表格卡片演示 ===\n");

  const card = new StreamingCard();
  await card.start();

  const tableMarkdown = `## 📊 项目周报总结

### 1. 本周完成情况

| 任务 | 负责人 | 状态 | 完成度 |
|------|--------|------|--------|
| 飞书流式卡片开发 | @Joshua | ✅ 已完成 | 100% |
| Markdown 表格支持 | @cc | ✅ 已完成 | 100% |
| 系统会话过滤器 | @cc | ✅ 已完成 | 100% |
| 错误处理优化 | @cc | 🔄 进行中 | 70% |

### 2. 代码统计

| 项目 | 文件数 | 代码行数 | 测试覆盖 |
|------|--------|---------|---------|
| feishu.ts | 1 | 1500 | 85% |
| feishu-streaming.ts | 1 | 300 | 90% |
| feishu-commands.ts | 1 | 500 | 80% |
| **总计** | **3** | **2300** | **85%** |

### 3. 性能对比

| 指标 | 普通卡片 | 流式卡片 |
|------|---------|---------|
| 首次响应时间 | 2.5s | 0.3s |
| 用户体验评分 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 消息数量 | 1条 | 1条(连续更新) |

### 4. 本周计划

| 优先级 | 任务 | 预计工时 |
|--------|------|---------|
| 🔥 P0 | 上线测试 | 2h |
| 🔥 P0 | 文档编写 | 3h |
| 📌 P1 | 功能扩展 | 1d |

---
数据来自项目管理系统
`;

  // 模拟逐行渲染
  let current = "";
  const lines = tableMarkdown.split("\n");

  for (const line of lines) {
    current += line + "\n";
    console.log(`更新行: "${line.slice(0, 40)}${line.length > 40 ? '...' : ''}"`);
    await card.update(current);
    await new Promise(r => setTimeout(r, 300));
  }

  await card.close(current);
  console.log("\n✅ 演示完成！");
}

main().catch(console.error);
