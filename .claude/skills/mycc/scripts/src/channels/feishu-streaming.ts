/**
 * 飞书流式卡片
 *
 * 集成自 clawdbot-feishu（MIT License）
 * 来源: https://github.com/m1heng/clawdbot-feishu
 *
 * 主要功能：
 * - FeishuStreamingSession: 流式卡片，AI 回复实时更新到单个卡片
 */

// ==================== token cache ====================

const tokenCache = new Map<
 string,
 { token: string; expiresAt: number }
>();

type Credentials = { appId: string; appSecret: string };

async function getFeishuToken(creds: Credentials): Promise<string> {
 const key = creds.appId;
 const cached = tokenCache.get(key);
 if (cached && cached.expiresAt > Date.now() + 60000) return cached.token;

 const res = await fetch(
  "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
  {
   method: "POST",
   headers: { "Content-Type": "application/json" },
   body: JSON.stringify({ app_id: creds.appId, app_secret: creds.appSecret }),
  }
 );
 const data = (await res.json()) as {
  code: number;
  msg: string;
  tenant_access_token?: string;
  expire?: number;
 };
 if (data.code !== 0 || !data.tenant_access_token)
  throw new Error(`Token error: ${data.msg}`);
 tokenCache.set(key, {
  token: data.tenant_access_token,
  expiresAt: Date.now() + (data.expire ?? 7200) * 1000,
 });
 return data.tenant_access_token;
}

// ==================== 工具函数 ====================

function truncateSummary(text: string, max = 50): string {
 const clean = text.replace(/\n/g, " ").trim();
 return clean.length <= max ? clean : clean.slice(0, max - 3) + "...";
}

function mergeStreamingText(
 prev: string | undefined,
 next: string | undefined
): string {
 const p = typeof prev === "string" ? prev : "";
 const n = typeof next === "string" ? next : "";
 if (!n) return p;
 if (!p || n === p || n.includes(p)) return n;
 if (p.includes(n)) return p;
 return p + n;
}

// ==================== FeishuStreamingSession ====================

type CardState = {
 cardId: string;
 messageId: string;
 sequence: number;
 currentText: string;
};

/**
 * 飞书流式卡片会话
 *
 * 用法：
 * 1. session.start(receiveId, receiveIdType, replyToMessageId?)
 * 2. session.update(text) // 随文本增长调用
 * 3. session.close(finalText?)
 *
 * 如果 CardKit API 不可用（权限不足等），会抛出错误，
 * 调用方应降级到普通消息发送。
 */
export class FeishuStreamingSession {
 private creds: Credentials;
 private state: CardState | null = null;
 private queue: Promise<void> = Promise.resolve();
 private closed = false;
 private lastUpdateTime = 0;
 private pendingText: string | null = null;
 private readonly updateThrottleMs = parseInt(process.env.FEISHU_STREAMING_THROTTLE_MS || "100", 10);
 private log?: (msg: string) => void;

 constructor(creds: Credentials, log?: (msg: string) => void) {
  this.creds = creds;
  this.log = log;
 }

 async start(
  receiveId: string,
  receiveIdType: "open_id" | "user_id" | "union_id" | "email" | "chat_id",
  replyToMessageId?: string
 ): Promise<void> {
  if (this.state) return;

  const token = await getFeishuToken(this.creds);

  // 创建流式卡片（streaming_mode: true）
  const cardJson = {
   schema: "2.0",
   config: {
    streaming_mode: true,
    summary: { content: "[生成中...]" },
    streaming_config: {
     print_frequency_ms: { default: 50 },
     print_step: { default: 2 },
    },
   },
   body: {
    elements: [{ tag: "markdown", content: "思考中...", element_id: "content" }],
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
  const createData = (await createRes.json()) as {
   code: number;
   msg: string;
   data?: { card_id: string };
  };
  if (createData.code !== 0 || !createData.data?.card_id) {
   throw new Error(
    `CardKit 创建卡片失败 (code ${createData.code}): ${createData.msg}`
   );
  }
  const cardId = createData.data.card_id;

  // 发送卡片（或回复消息）
  const cardContent = JSON.stringify({ type: "card", data: { card_id: cardId } });
  const sendUrl = replyToMessageId
   ? `https://open.feishu.cn/open-apis/im/v1/messages/${replyToMessageId}/reply`
   : `https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=${receiveIdType}`;
  const sendBody = replyToMessageId
   ? { msg_type: "interactive", content: cardContent }
   : { receive_id: receiveId, msg_type: "interactive", content: cardContent };

  const sendRes = await fetch(sendUrl, {
   method: "POST",
   headers: {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
   },
   body: JSON.stringify(sendBody),
  });
  const sendData = (await sendRes.json()) as {
   code: number;
   msg: string;
   data?: { message_id: string };
  };
  if (sendData.code !== 0 || !sendData.data?.message_id) {
   throw new Error(
    `发送卡片失败 (code ${sendData.code}): ${sendData.msg}`
   );
  }

  this.state = {
   cardId,
   messageId: sendData.data.message_id,
   sequence: 1,
   currentText: "",
  };
  this.log?.(`[Streaming] 已启动: cardId=${cardId}, messageId=${sendData.data.message_id}`);
 }

 async update(text: string): Promise<void> {
  if (!this.state || this.closed) return;
  const merged = mergeStreamingText(
   this.pendingText ?? this.state.currentText,
   text
  );
  if (!merged || merged === this.state.currentText) return;

  const now = Date.now();
  if (now - this.lastUpdateTime < this.updateThrottleMs) {
   this.pendingText = merged;
   return;
  }
  this.pendingText = null;
  this.lastUpdateTime = now;

  this.queue = this.queue.then(async () => {
   if (!this.state || this.closed) return;
   const mergedText = mergeStreamingText(this.state.currentText, merged);
   if (!mergedText || mergedText === this.state.currentText) return;
   this.state.currentText = mergedText;
   this.state.sequence += 1;
   await fetch(
    `https://open.feishu.cn/open-apis/cardkit/v1/cards/${this.state.cardId}/elements/content/content`,
    {
     method: "PUT",
     headers: {
      Authorization: `Bearer ${await getFeishuToken(this.creds)}`,
      "Content-Type": "application/json",
     },
     body: JSON.stringify({
      content: mergedText,
      sequence: this.state.sequence,
      uuid: `s_${this.state.cardId}_${this.state.sequence}`,
     }),
    }
   ).catch((e) => this.log?.(`Update failed: ${String(e)}`));
  });
  await this.queue;
 }

 async close(finalText?: string): Promise<void> {
  if (!this.state || this.closed) return;
  this.closed = true;
  await this.queue;

  const pendingMerged = mergeStreamingText(
   this.state.currentText,
   this.pendingText ?? undefined
  );
  const text = finalText
   ? mergeStreamingText(pendingMerged, finalText)
   : pendingMerged;
  const token = await getFeishuToken(this.creds);

  // 最终文本更新
  if (text && text !== this.state.currentText) {
   this.state.sequence += 1;
   await fetch(
    `https://open.feishu.cn/open-apis/cardkit/v1/cards/${this.state.cardId}/elements/content/content`,
    {
     method: "PUT",
     headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
     },
     body: JSON.stringify({
      content: text,
      sequence: this.state.sequence,
      uuid: `s_${this.state.cardId}_${this.state.sequence}`,
     }),
    }
   ).catch(() => {});
   this.state.currentText = text;
  }

  // 关闭流式模式
  const summary = text ? truncateSummary(text) : "";
  this.state.sequence += 1;
  await fetch(
   `https://open.feishu.cn/open-apis/cardkit/v1/cards/${this.state.cardId}/settings`,
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
     sequence: this.state.sequence,
     uuid: `c_${this.state.cardId}_${this.state.sequence}`,
    }),
   }
  ).catch((e) => this.log?.(`Close failed: ${String(e)}`));

  this.log?.(`[Streaming] 已完成: cardId=${this.state.cardId}`);
 }

 isActive(): boolean {
  return this.state !== null && !this.closed;
 }
}