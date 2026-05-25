"""
财经图表生成技能包 - Financial Chart Generator Skill
基于matplotlib，适配中文显示（Windows/Linux），适配诗与星空风格财经文章
支持命令行调用和模块导入两种使用方式
"""

import shutil
import matplotlib
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
import os
import sys
import json
import argparse

# ========== 配色方案（诗与星空风格）==========
COLORS = {
    'primary': '#4472C4',
    'secondary': '#ED7D31',
    'success': '#70AD47',
    'warning': '#FFC000',
    'danger': '#C55A11',
    'neutral': '#5B9BD5',
}


def setup_chinese_font():
    """修复matplotlib中文显示问题（方框/乱码），适配 Windows/Linux"""
    try:
        shutil.rmtree(matplotlib.get_cachedir(), ignore_errors=True)
    except Exception:
        pass
    font_manager.fontManager.__init__()

    # Windows 优先使用系统自带中文字体
    plt.rcParams['font.sans-serif'] = [
        'Microsoft YaHei',      # Windows 微软雅黑
        'SimHei',               # Windows 黑体
        'SimSun',               # Windows 宋体
        'WenQuanYi Zen Hei',    # Linux
        'Droid Sans Fallback',  # Linux 备选
        'DejaVu Sans',
    ]
    plt.rcParams['axes.unicode_minus'] = False

    # 强制使用 FontProperties 查找字体
    font_found = False
    for fname in ['msyh.ttc', 'msyhbd.ttc', 'simhei.ttf', 'simsun.ttc']:
        for fpath in font_manager.findSystemFonts():
            if fname.lower() in fpath.lower():
                try:
                    prop = font_manager.FontProperties(fname=fpath)
                    plt.rcParams['font.family'] = prop.get_name()
                    font_found = True
                    break
                except Exception:
                    continue
        if font_found:
            break

    print("✓ 中文字体配置完成")


def save_chart(fig, filepath, dpi=200):
    """统一保存图表，确保白底、高清"""
    os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else '.', exist_ok=True)
    fig.savefig(filepath, dpi=dpi, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close(fig)
    print(f"✓ 图表已保存: {filepath}")


def chart_revenue_profit(years, revenue, net_profit,
                         save_path='/tmp/chart_revenue_profit.png'):
    """营收与净利润组合图（双柱状图）"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    colors_rev = [COLORS['primary']] * (len(years) - 1) + [COLORS['secondary']]
    bars1 = ax1.bar(years, revenue, color=colors_rev, width=0.6,
                    edgecolor='white', linewidth=0.5)
    ax1.set_title('营业收入（亿元）', fontsize=14, fontweight='bold')
    ax1.set_ylabel('亿元', fontsize=11)
    max_rev = max(revenue) * 1.15
    ax1.set_ylim(0, max_rev)
    for bar, val in zip(bars1, revenue):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max_rev * 0.02,
                 f'{val}', ha='center', va='bottom', fontsize=10, fontweight='bold')

    colors_np = [COLORS['success'] if v >= 0 else COLORS['danger'] for v in net_profit]
    bars2 = ax2.bar(years, net_profit, color=colors_np, width=0.6,
                    edgecolor='white', linewidth=0.5)
    ax2.set_title('净利润（亿元）', fontsize=14, fontweight='bold')
    ax2.set_ylabel('亿元', fontsize=11)
    ax2.axhline(y=0, color='black', linewidth=0.8)
    min_np, max_np = min(net_profit), max(net_profit)
    padding = (max_np - min_np) * 0.1
    ax2.set_ylim(min_np - padding, max_np + padding)
    for bar, val in zip(bars2, net_profit):
        y_pos = bar.get_height() + padding * 0.3 if val >= 0 else bar.get_height() - padding * 0.3
        va = 'bottom' if val >= 0 else 'top'
        ax2.text(bar.get_x() + bar.get_width() / 2, y_pos, f'{val}',
                 ha='center', va=va, fontsize=10, fontweight='bold')

    plt.tight_layout()
    save_chart(fig, save_path)
    return save_path


def chart_margin_delivery(years, gross_margin, delivery,
                          save_path='/tmp/chart_margin_delivery.png'):
    """毛利率与交付量组合图（折线+柱状）"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    ax1.plot(years, gross_margin, marker='o', markersize=8,
             linewidth=2.5, color=COLORS['primary'])
    ax1.fill_between(years, gross_margin, alpha=0.15, color=COLORS['primary'])
    ax1.set_title('综合毛利率（%）', fontsize=14, fontweight='bold')
    ax1.set_ylabel('%', fontsize=11)
    max_gm = max(gross_margin) * 1.2
    ax1.set_ylim(0, max_gm)
    for i, val in enumerate(gross_margin):
        ax1.text(i, val + max_gm * 0.03, f'{val}%',
                 ha='center', fontsize=10, fontweight='bold')

    colors_del = [COLORS['primary']] * (len(years) - 1) + [COLORS['secondary']]
    delivery_wan = [d / 10000 for d in delivery]
    bars = ax2.bar(years, delivery_wan, color=colors_del, width=0.6,
                   edgecolor='white')
    ax2.set_title('年度交付量（万辆）', fontsize=14, fontweight='bold')
    ax2.set_ylabel('万辆', fontsize=11)
    max_del = max(delivery_wan) * 1.15
    ax2.set_ylim(0, max_del)
    for bar, val in zip(bars, delivery):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max_del * 0.02,
                 f'{val / 10000:.1f}', ha='center', va='bottom',
                 fontsize=10, fontweight='bold')

    plt.tight_layout()
    save_chart(fig, save_path)
    return save_path


def chart_quarterly_trend(quarters, q_revenue, q_gross_margin=None,
                          save_path='/tmp/chart_quarterly.png'):
    """季度趋势图（营收柱状图+毛利率折线图，双Y轴）"""
    fig, ax1 = plt.subplots(figsize=(14, 6))

    colors_q = [COLORS['primary']] * (len(quarters) - 1) + [COLORS['secondary']]
    bars = ax1.bar(quarters, q_revenue, color=colors_q, width=0.5,
                   edgecolor='white', alpha=0.85)
    ax1.set_title('季度营收趋势（亿元）', fontsize=14, fontweight='bold')
    ax1.set_ylabel('营收（亿元）', fontsize=11, color=COLORS['primary'])
    ax1.tick_params(axis='y', labelcolor=COLORS['primary'])
    max_rev = max(q_revenue) * 1.2
    ax1.set_ylim(0, max_rev)
    for bar, val in zip(bars, q_revenue):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max_rev * 0.02,
                 f'{val}', ha='center', va='bottom', fontsize=9)

    if q_gross_margin:
        ax2 = ax1.twinx()
        ax2.plot(quarters, q_gross_margin, marker='o', markersize=7,
                 linewidth=2.5, color=COLORS['success'], label='毛利率')
        ax2.fill_between(quarters, q_gross_margin, alpha=0.1, color=COLORS['success'])
        ax2.set_ylabel('毛利率（%）', fontsize=11, color=COLORS['success'])
        ax2.tick_params(axis='y', labelcolor=COLORS['success'])
        max_gm = max(q_gross_margin) * 1.3
        ax2.set_ylim(0, max_gm)
        for i, val in enumerate(q_gross_margin):
            ax2.text(i, val + max_gm * 0.03, f'{val}%',
                     ha='center', fontsize=9, color=COLORS['success'])
        ax2.legend(loc='upper left')

    plt.xticks(rotation=45)
    plt.tight_layout()
    save_chart(fig, save_path)
    return save_path


def chart_peer_comparison(companies, metrics_dict,
                          save_path='/tmp/chart_comparison.png'):
    """同行对比图（2x2子图）"""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()

    colors = [COLORS['secondary'], COLORS['primary'], COLORS['success']]

    for idx, (metric_name, values) in enumerate(metrics_dict.items()):
        ax = axes[idx]
        if '净利润' in metric_name or '利润' in metric_name:
            bar_colors = [COLORS['success'] if v >= 0 else COLORS['danger'] for v in values]
        else:
            bar_colors = colors[:len(values)]

        bars = ax.bar(companies, values, color=bar_colors, width=0.5, edgecolor='white')
        ax.set_title(metric_name, fontsize=12, fontweight='bold')

        max_val = max([abs(v) for v in values]) * 1.2
        for bar, val in zip(bars, values):
            if '净利润' in metric_name and val < 0:
                y_pos = val - max_val * 0.05
                va = 'top'
            else:
                y_pos = val + max_val * 0.03
                va = 'bottom'
            label = f'{val}%' if '%' in metric_name else f'{val}'
            ax.text(bar.get_x() + bar.get_width() / 2, y_pos, label,
                    ha='center', va=va, fontsize=10)

        if '净利润' in metric_name:
            ax.axhline(y=0, color='black', linewidth=0.8)

        ax.set_ylim(-max_val * 0.3 if any(v < 0 for v in values) else 0, max_val)

    plt.tight_layout()
    save_chart(fig, save_path)
    return save_path


def chart_pie_comparison(labels_2024, values_2024, labels_2026, values_2026,
                         save_path='/tmp/chart_pie.png'):
    """双饼图对比"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    colors_pie = [COLORS['primary'], COLORS['secondary'], COLORS['success'],
                  COLORS['warning'], COLORS['neutral']]

    wedges1, texts1, autotexts1 = ax1.pie(values_2024, labels=labels_2024,
                                           autopct='%1.1f%%',
                                           colors=colors_pie[:len(labels_2024)],
                                           startangle=90)
    ax1.set_title('2024年', fontsize=13, fontweight='bold')

    wedges2, texts2, autotexts2 = ax2.pie(values_2026, labels=labels_2026,
                                           autopct='%1.1f%%',
                                           colors=colors_pie[:len(labels_2026)],
                                           startangle=90)
    ax2.set_title('2026年', fontsize=13, fontweight='bold')

    plt.tight_layout()
    save_chart(fig, save_path)
    return save_path


def chart_line_trend(x_labels, *lines, line_names=None, ylabel='',
                     save_path='/tmp/chart_line.png'):
    """多线趋势图"""
    fig, ax = plt.subplots(figsize=(12, 6))

    line_colors = [COLORS['primary'], COLORS['secondary'], COLORS['success'],
                   COLORS['warning']]

    for idx, line_data in enumerate(lines):
        name = line_names[idx] if line_names and idx < len(line_names) else f'线{idx + 1}'
        color = line_colors[idx % len(line_colors)]
        ax.plot(x_labels, line_data, marker='o', markersize=6,
                linewidth=2, color=color, label=name)

    ax.set_title(ylabel + '趋势', fontsize=14, fontweight='bold')
    ax.set_ylabel(ylabel, fontsize=11)
    ax.legend(loc='best')
    ax.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()
    save_chart(fig, save_path)
    return save_path


def generate_all_charts(data, output_dir):
    """
    根据完整财报数据生成全套图表
    data: dict, 包含 company, years, revenue, net_profit, gross_margin, delivery 等字段
    output_dir: 输出目录
    """
    os.makedirs(output_dir, exist_ok=True)
    company = data.get('company', 'unknown')
    years = data.get('years', [])
    generated = []

    # 1. 营收与净利润
    if 'revenue' in data and 'net_profit' in data:
        path = os.path.join(output_dir, f'{company}_营收净利润.png')
        chart_revenue_profit(years, data['revenue'], data['net_profit'], path)
        generated.append(path)

    # 2. 毛利率与交付量/业务量
    if 'gross_margin' in data:
        delivery = data.get('delivery', [0] * len(years))
        path = os.path.join(output_dir, f'{company}_毛利率.png')
        chart_margin_delivery(years, data['gross_margin'], delivery, path)
        generated.append(path)

    # 3. 季度趋势
    if 'quarters' in data and 'q_revenue' in data:
        path = os.path.join(output_dir, f'{company}_季度趋势.png')
        chart_quarterly_trend(data['quarters'], data['q_revenue'],
                              data.get('q_gross_margin'), path)
        generated.append(path)

    # 4. 资产负债表指标（每个指标一张柱状图）
    for metric_key, metric_label in [
        ('cash', '货币资金'), ('trading_assets', '交易性金融资产'),
        ('accounts_receivable', '应收账款'), ('inventory', '存货'),
        ('short_loan', '短期借款'), ('long_loan', '长期借款'),
        ('contract_liability', '合同负债'), ('selling_expense', '销售费用'),
        ('rd_expense', '研发费用'), ('finance_expense', '财务费用'),
        ('operating_cashflow', '经营性现金流'), ('capex', '资本支出'),
    ]:
        if metric_key in data:
            values = data[metric_key]
            fig, ax = plt.subplots(figsize=(12, 5))
            colors = [COLORS['primary']] * (len(years) - 1) + [COLORS['secondary']]
            bars = ax.bar(years, values, color=colors, width=0.6, edgecolor='white')
            ax.set_title(f'{company} - {metric_label}（亿元）', fontsize=14, fontweight='bold')
            ax.set_ylabel('亿元', fontsize=11)
            max_v = max(abs(v) for v in values) * 1.15 if values else 1
            for bar, val in zip(bars, values):
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max_v * 0.02,
                        f'{val}', ha='center', va='bottom', fontsize=10, fontweight='bold')
            plt.tight_layout()
            path = os.path.join(output_dir, f'{company}_{metric_key}.png')
            save_chart(fig, path)
            generated.append(path)

    return generated


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='财经图表生成器')
    parser.add_argument('--data', type=str, help='JSON 格式数据')
    parser.add_argument('--output', type=str, default='charts/', help='输出目录')
    parser.add_argument('--demo', action='store_true', help='运行演示')
    args = parser.parse_args()

    setup_chinese_font()

    if args.demo:
        demo_data = {
            'company': '蔚来',
            'years': ['2021', '2022', '2023', '2024', '2025'],
            'revenue': [361.4, 492.7, 556.2, 657.3, 874.9],
            'net_profit': [-40.2, -146.0, -211.5, -224.0, -149.4],
            'gross_margin': [18.9, 13.7, 10.5, 13.6, 13.6],
            'delivery': [91429, 122486, 160038, 221000, 326000],
        }
        files = generate_all_charts(demo_data, os.path.join(args.output, '蔚来'))
        print(f"\n✓ 演示完成，生成 {len(files)} 张图表")
    elif args.data:
        data = json.loads(args.data)
        company = data.get('company', 'output')
        files = generate_all_charts(data, os.path.join(args.output, company))
        print(json.dumps({'generated': files, 'count': len(files)}, ensure_ascii=False))
    else:
        print("用法: python financial_charts.py --data 'JSON' --output charts/")
        print("      python financial_charts.py --demo --output charts/")
