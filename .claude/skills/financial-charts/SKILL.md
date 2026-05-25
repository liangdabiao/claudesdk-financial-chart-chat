# financial-charts — A 股财经图表生成技能

## 概述

本技能根据用户输入的自然语言查询，自动获取 A 股上市公司财报数据并生成专业可视化图表。

## 数据源（双引擎）

**主方案：Baostock**（自有服务器，稳定快速，不受反爬限制）
**次方案：akshare**（自动降级，baostock 不可用时启用）

## 支持的查询类型

### 1. 年报/季报查询
- "查询贵州茅台2024年年报"
- "查询比亚迪2025年三季报"
- "查询宁德时代2023年半年报"
- "分析蔚来的财务数据"

### 2. 同行对比
- "对比蔚来、理想、小鹏的营收"
- "贵州茅台 vs 五粮液"
- "对比银行业几家公司"

### 3. 趋势分析
- "贵州茅台近5年营收趋势"
- "比亚迪毛利率变化"
- "宁德时代季度趋势"

### 4. K线行情
- "贵州茅台2024年股价走势"
- "比亚迪近一年月K线"

### 5. 自定义图表
- 用户提供数据，指定图表类型

## 执行流程

### 年报/季报查询流程

1. **解析查询**：提取公司名、年份、报告类型
2. **获取股票代码**：运行 `python .claude/skills/financial-charts/data_fetcher.py --search "公司名"`
3. **获取财务数据**：运行 `python .claude/skills/financial-charts/data_fetcher.py --code 股票代码 --type annual --years 5`
4. **生成图表**：运行 `python .claude/skills/financial-charts/financial_charts.py --data JSON数据 --output charts/公司名/`
5. **返回结果**：列出所有生成的图表文件路径

### 同行对比流程

1. 获取每家公司的关键数据：`python .claude/skills/financial-charts/data_fetcher.py --codes 600519,000858,000596`
2. 调用 `chart_peer_comparison()` 生成对比图
3. 输出到 `charts/对比_主题/`

### K线行情流程

1. 获取K线数据：`python .claude/skills/financial-charts/data_fetcher.py --code 600519 --kline --start 2024-01-01 --end 2024-12-31`
2. 生成股价走势图
3. 输出到 `charts/公司名/`

## Python 模块

### data_fetcher.py

数据获取模块，Baostock 主方案 + akshare 降级。

```bash
# 搜索公司（首次搜索会缓存 8754 只股票列表到本地）
python .claude/skills/financial-charts/data_fetcher.py --search "贵州茅台"

# 获取年报数据（5年）
python .claude/skills/financial-charts/data_fetcher.py --code 600519 --type annual --years 5

# 获取同行数据
python .claude/skills/financial-charts/data_fetcher.py --codes 600519,000858 --years 5

# 获取K线数据
python .claude/skills/financial-charts/data_fetcher.py --code 600519 --kline --start 2024-01-01 --end 2024-12-31
```

输出为 JSON 格式，包含：
- 盈利数据：营收、净利润、毛利率、净利率、ROE、EPS
- 成长数据：营收增长率(YOYNI)、净利润增长率(YOYPNI)
- 季度数据：最近 4 个季度的营收、毛利率、净利润

### financial_charts.py

图表生成模块，6 种图表类型：

- `chart_revenue_profit()` — 营收+净利润双柱状图
- `chart_margin_delivery()` — 毛利率+交付量组合图
- `chart_quarterly_trend()` — 季度趋势双 Y 轴图
- `chart_peer_comparison()` — 同行对比 2×2 子图
- `chart_pie_comparison()` — 双饼图对比
- `chart_line_trend()` — 多线趋势图

```bash
# 生成所有图表
python .claude/skills/financial-charts/financial_charts.py --data '{"company":"贵州茅台","years":["2021","2022","2023","2024","2025"],"revenue":[...],...}' --output charts/贵州茅台/
```

## 输出规则

- 年报查询 → `charts/{公司名}/`
- 同行对比 → `charts/对比_{主题}/`
- 季度趋势 → `charts/{公司名}/`
- K线行情 → `charts/{公司名}/`
- 自定义 → `charts/custom/`

## Baostock 字段映射

| 图表需要 | Baostock 字段 | 含义 |
|---------|--------------|------|
| 营业收入 | MBRevenue | 主营业务收入（元→亿元转换） |
| 净利润 | netProfit | 净利润（元→亿元转换） |
| 毛利率 | gpMargin | 毛利率（小数→百分比） |
| 净利率 | npMargin | 净利率 |
| ROE | roeAvg | 平均净资产收益率 |
| EPS | epsTTM | 每股收益 |
| 营收增长 | YOYNI | 净利润同比 |
| 利润增长 | YOYPNI | 归母净利同比 |
| 股价 | close (K线) | 收盘价（前复权） |

## 重要约束

- 必须先调用 `setup_chinese_font()` 修复中文字体
- 所有图表使用中文标题和标签
- 图表配色采用诗与星空风格
- 净利润为负时使用红色标注
- 最新年份/季度使用橙色高亮
- 所有图表输出为 PNG 格式，dpi=200
- 股票代码格式：用户输入纯数字 `600519`，模块自动转换 `sh.600519`

## 依赖

```bash
pip install matplotlib numpy baostock pandas akshare
```

如果用户未安装依赖，先运行安装命令。
