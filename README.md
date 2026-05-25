# FinancialChartChat

基于 Claude Agent SDK 的 AI 财经图表对话助手。用户通过自然语言对话，自动查询 A 股上市公司财务数据并生成专业分析图表。

## 功能特性

- **自然语言交互** — 输入公司名或分析需求，AI 自动解析意图并执行
- **6 种专业图表** — 营收净利润、毛利率、季度趋势、同行对比、饼图对比、多线趋势
- **实时数据获取** — Baostock 主方案（自有服务器稳定）+ akshare 自动降级
- **图表库管理** — 侧边栏实时展示已生成的图表，支持预览与下载
- **执行日志** — 右侧面板实时显示 AI 工具调用过程
- **文件上传** — 支持上传 CSV/Excel 等数据文件进行自定义图表生成

## 技术架构

```
┌──────────────┐     WebSocket      ┌──────────────┐
│   React UI   │ ◄──────────────► │   Express     │
│   (Vite)     │                   │   Server      │
└──────────────┘                   └──────┬───────┘
                                          │
                                   Claude Agent SDK
                                          │
                                   ┌──────┴───────┐
                                   │  Skills 层    │
                                   │  SKILL.md     │
                                   │  Python 脚本  │
                                   └──────────────┘
```

- **前端**: React 18 + Tailwind CSS 4 + Vite 6
- **后端**: Express + WebSocket (ws)
- **AI 引擎**: Claude Agent SDK（`@anthropic-ai/claude-agent-sdk`）
- **图表引擎**: Python matplotlib + numpy
- **数据源**: Baostock（主） + akshare（降级）

## 快速开始

### 环境要求

- Node.js >= 18
- Python >= 3.8
- npm 或 yarn

### 安装依赖

```bash
# Node.js 依赖
npm install

# Python 依赖
pip install matplotlib numpy baostock pandas akshare
```

### 配置环境变量

创建 `.env` 文件：

```env
ANTHROPIC_API_KEY=your-api-key
ANTHROPIC_AUTH_TOKEN=your-api-key
ANTHROPIC_BASE_URL=https://api.anthropic.com
MODEL=claude-sonnet-4-20250514
PORT=3015
CLAUDE_CONFIG_DIR=.claude
```

> 如果使用 DeepSeek 等兼容接口，将 `ANTHROPIC_BASE_URL` 替换为对应的 Anthropic 兼容地址。

### 启动开发服务

```bash
npm run dev
```

启动后访问 http://localhost:5173

- 前端开发服务：`http://localhost:5173`（Vite，自动代理到后端）
- 后端 API 服务：`http://localhost:3015`

### 生产构建

```bash
npm run build
npm start
```

构建后通过 `http://localhost:3015` 直接访问。

## 使用示例

在聊天框中输入自然语言指令：

| 输入示例 | 生成内容 |
|---------|---------|
| `查询贵州茅台2024年年报` | 营收+净利润双柱状图、毛利率图 |
| `对比比亚迪和蔚来近3年财务数据` | 同行对比 2×2 子图 |
| `分析宁德时代季度趋势` | 季度营收与毛利率双 Y 轴图 |
| `画一个饼图对比三家锂电企业营收结构` | 双饼图结构对比 |

生成的图表会自动出现在左侧「图表库」面板中，点击可预览和下载。

## 项目结构

```
financial-chart-chat/
├── .claude/
│   ├── settings.json              # MCP 配置
│   └── skills/
│       └── financial-charts/
│           ├── SKILL.md           # Skill 定义（AI 自动读取）
│           ├── financial_charts.py # 图表生成模块（6 种图表）
│           ├── data_fetcher.py    # A 股数据获取模块
│           └── requirements.txt   # Python 依赖
├── server/
│   ├── index.ts                   # Express + WebSocket 服务
│   ├── agent-client.ts            # Claude Agent SDK 集成
│   ├── message-queue.ts           # 异步消息队列
│   └── logger.ts                  # 文件日志
├── src/
│   ├── App.tsx                    # 主界面（三栏布局）
│   ├── types.ts                   # TypeScript 类型定义
│   ├── index.tsx                  # 入口
│   ├── index.css                  # Tailwind CSS
│   └── hooks/
│       ├── useWebSocket.ts        # WebSocket 连接管理
│       └── useFileUpload.ts       # 文件上传
├── charts/                        # 生成的图表（PNG）
├── package.json
├── vite.config.ts
├── tsconfig.json
└── tsconfig.server.json
```

## Skill 系统

项目核心基于 Claude Agent SDK 的 Skill 机制。`.claude/skills/financial-charts/SKILL.md` 定义了 AI 助手的财经图表能力，SDK 通过 `settingSources: ["project"]` 自动加载项目级 Skill。

工作流程：

1. 用户发送消息 → WebSocket 转发到后端
2. SDK 接收消息，AI 解析意图并选择合适的工具
3. AI 调用 Bash 执行 Python 脚本获取数据/生成图表
4. 图表保存到 `charts/` 目录，前端自动刷新侧边栏
5. AI 返回分析结果，包含图表路径（前端自动渲染图片）

## 常见问题

**Q: 数据获取失败怎么办？**

系统使用 Baostock（主）→ akshare（次）双引擎自动降级。如果主方案不可用会自动切换，不影响使用。

**Q: 图表中文显示乱码？**

图表模块已内置 Windows 中文字体支持（微软雅黑/黑体/宋体）。如仍有问题，请确保系统中安装了中文字体。

**Q: 如何更换 AI 模型？**

修改 `.env` 中的 `MODEL` 字段。支持所有 Anthropic API 兼容的模型。


## 感谢和参考
https://linux.do/  感谢佬友，

https://github.com/liangdabiao/claudesdk-skill  AI生成claude-agent-sdk 项目，

https://pan.quark.cn/s/3f91c08aafca#/list/share  akshare skill参考

## License

MIT



