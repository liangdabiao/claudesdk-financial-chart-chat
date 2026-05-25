import { query } from "@anthropic-ai/claude-agent-sdk";
import path from "path";
import dotenv from "dotenv";
import { MessageQueue } from "./message-queue.js";
import { fileLog } from "./logger.js";

dotenv.config({ override: true });

export interface SDKMessage {
  type: string;
  subtype?: string;
  session_id?: string;
  message?: { role: string; content: any };
  result?: string;
  total_cost_usd?: number;
  duration_ms?: number;
}

export class AgentSession {
  private queue: MessageQueue;
  private outputIterator: AsyncIterator<SDKMessage> | null = null;
  public sdkSessionId: string | null = null;
  private started = false;

  constructor() {
    this.queue = new MessageQueue();
  }

  private ensureStarted() {
    if (this.started) return;
    this.started = true;

    fileLog("Agent", "Starting SDK | MODEL:", process.env.MODEL || "sonnet", "| BASE_URL:", process.env.ANTHROPIC_BASE_URL || "(default)");

    try {
      const stream = query({
        prompt: this.queue as any,
        options: {
          cwd: path.resolve(process.cwd()),
          settingSources: ["project"],
          allowedTools: [
            "Skill", "Task", "TodoWrite",
            "WebSearch",
            "Bash",
            "Read", "Write", "Glob", "Grep",
          ],
          systemPrompt: `你是 FinancialChartChat，一个专业的 AI 财经图表助手。

你拥有专业的财经图表生成技能（financial-charts），覆盖 A 股上市公司全链路分析：

📊 核心能力：
- 年报/季报查询：获取上市公司财务数据，生成专业图表
- 同行对比：多家公司关键指标对比分析
- 趋势分析：季度/年度趋势图生成
- K线行情：股价走势图生成
- 自定义图表：根据用户提供数据生成指定类型图表

📈 6 种图表类型：
- chart_revenue_profit() — 营收+净利润双柱状图
- chart_margin_delivery() — 毛利率+业务量组合图
- chart_quarterly_trend() — 季度趋势双Y轴图
- chart_peer_comparison() — 同行对比2×2子图
- chart_pie_comparison() — 双饼图结构对比
- chart_line_trend() — 多线趋势图

🔧 工作流程：
1. 用户输入公司名或分析需求
2. 解析意图，确定查询类型和参数
3. 通过 Bash 执行 Python 脚本获取数据（Baostock 主方案，akshare 自动降级）
   - 搜索公司：python .claude/skills/financial-charts/data_fetcher.py --search "公司名"
   - 获取数据：python .claude/skills/financial-charts/data_fetcher.py --code 股票代码 --type annual --years 5
   - 获取同行：python .claude/skills/financial-charts/data_fetcher.py --codes 600519,000858 --years 5
   - K线行情：python .claude/skills/financial-charts/data_fetcher.py --code 600519 --kline --start 2024-01-01 --end 2024-12-31
4. 通过 Python 生成图表
   - python .claude/skills/financial-charts/financial_charts.py --data 'JSON' --output charts/公司名/
5. 返回分析结果和图表路径

📁 文件输出规则：
- 年报查询 → charts/{公司名}/
- 同行对比 → charts/对比_{主题}/
- K线行情 → charts/{公司名}/
- 自定义 → charts/custom/

⚠️ 重要约束：
- Python 脚本路径统一为 .claude/skills/financial-charts/ 目录下
- 数据获取使用 Baostock（主）→ akshare（自动降级），无需手动切换
- 所有图表使用中文标题和标签
- 图表保存为 PNG 格式

用中文回复用户。`,
          model: process.env.MODEL || "sonnet",
          permissionMode: "bypassPermissions",
          maxTurns: 80,
          stderr: (data: string) => {
            fileLog("SDK.stderr", data.replace(/\n$/, ""));
          },
          env: {
            ...process.env,
            ANTHROPIC_API_KEY: process.env.ANTHROPIC_API_KEY,
            ANTHROPIC_AUTH_TOKEN: process.env.ANTHROPIC_AUTH_TOKEN,
            ANTHROPIC_BASE_URL: process.env.ANTHROPIC_BASE_URL,
          },
        },
      });

      this.outputIterator = stream[Symbol.asyncIterator]();
    } catch (e) {
      fileLog("Agent", "FAILED to start:", e);
      this.started = false;
    }
  }

  sendMessage(content: string) {
    fileLog("UserMsg", content);
    this.ensureStarted();
    this.queue.push(content);
  }

  async *getOutputStream(): AsyncGenerator<SDKMessage> {
    while (!this.outputIterator) {
      await new Promise((r) => setTimeout(r, 50));
    }

    while (true) {
      try {
        const { value, done } = await this.outputIterator.next();
        if (done) break;
        if (value?.type === "system" && value?.subtype === "init") {
          this.sdkSessionId = value.session_id ?? null;
          fileLog("Agent", "Session init:", this.sdkSessionId);
        } else {
          this.logSDKMessage(value);
        }
        yield value;
      } catch (e) {
        fileLog("Agent", "Stream error:", e);
        break;
      }
    }
  }

  private logSDKMessage(msg: SDKMessage) {
    if (msg.type === "assistant" && msg.message) {
      for (const block of msg.message.content) {
        if (block.type === "text" && block.text) fileLog("AI", block.text.substring(0, 200));
        if (block.type === "tool_use") fileLog("ToolCall", block.name, JSON.stringify(block.input));
      }
    }
    if (msg.type === "result") {
      fileLog("Result", msg.subtype || "", "cost:", msg.total_cost_usd, "duration:", msg.duration_ms + "ms");
    }
  }

  close() {
    this.queue.close();
  }
}
