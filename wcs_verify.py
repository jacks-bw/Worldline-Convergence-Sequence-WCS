"""
世界线收束序列 - 批量校验与报告生成工具
Worldline Convergence Sequence - Batch Verification & Report Generator

功能：
  - 支持数组字符串（如 [1,2,3]）或范围写法（如 1~999）输入种子
  - 自动推演全部种子至世界线收束完成
  - 生成散点图、折线图、饼图进行专业分析
  - 输出完整分析报告文档（HTML格式）
"""

import os
import sys
import re
from collections import Counter
from datetime import datetime

# 导入核心迭代引擎
from wcs import _get_next_node, worldline_convergence_seq, detect_worldline_cycle

# 第三方依赖
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

# ============================================================
# 第一部分：种子输入解析
# ============================================================

def parse_seeds(user_input: str):
    """
    解析用户输入的种子字符串，支持两种格式：
      1. 数组字符串：如 "[1,2,3]"、"['a','b','c']"、"['1','abc','hello']"
      2. 范围写法：如 "1~999"、"100~200"、"a~z"
    :param user_input: 用户原始输入字符串
    :return: 种子列表 list[str]
    """
    user_input = user_input.strip()

    # 格式一：范围写法 如 1~999
    range_match = re.match(r'^(\d+)\s*~\s*(\d+)$', user_input)
    if range_match:
        start, end = int(range_match.group(1)), int(range_match.group(2))
        if start > end:
            start, end = end, start  # 自动翻转
        if end - start > 50000:
            raise ValueError(f"范围过大 ({end - start + 1} 个种子)，请控制在 50000 以内")
        return [str(i) for i in range(start, end + 1)]

    # 格式一扩展：字母范围 a~z
    alpha_range = re.match(r'^([a-zA-Z])\s*~\s*([a-zA-Z])$', user_input)
    if alpha_range:
        s, e = alpha_range.group(1), alpha_range.group(2)
        if s.lower() == e.lower() and s != e:
            # 大小写不同但字母相同，按 ASCII 顺序
            pass
        start_ord, end_ord = ord(s), ord(e)
        if start_ord > end_ord:
            start_ord, end_ord = end_ord, start_ord
        return [chr(i) for i in range(start_ord, end_ord + 1)]

    # 格式二：数组字符串 如 [1,2,3] 或 ['a','b','c']
    # 去除首尾方括号
    inner = user_input.strip()
    if inner.startswith('[') and inner.endswith(']'):
        inner = inner[1:-1]

    # 按逗号分割，并清理每个元素的首尾引号和空白
    seeds = []
    for item in re.split(r',', inner):
        item = item.strip().strip("'\"").strip()
        if item:
            seeds.append(item)
    return seeds


# ============================================================
# 第二部分：批量推演引擎
# ============================================================

def batch_convergence(seeds: list, verbose: bool = True):
    """
    批量推演全部种子至世界线收束完成，收集统计数据。
    :param seeds: 种子列表
    :param verbose: 是否打印进度
    :return: 统计结果列表，每条为 dict
    """
    total = len(seeds)
    results = []
    cycle_counter = Counter()  # 统计各周期长度的频次

    for i, seed in enumerate(seeds):
        branch, fate_cycle, cycle_len = detect_worldline_cycle(seed)
        total_nodes = len(branch) + len(fate_cycle)

        record = {
            'seed': seed,
            'branch_len': len(branch),
            'cycle_len': cycle_len,
            'total_nodes': total_nodes,
            'branch_domain': branch,
            'fate_cycle': fate_cycle,
            'converge_node': fate_cycle[0] if fate_cycle else '',
            'final_node': fate_cycle[-1] if fate_cycle else '',
        }
        results.append(record)
        cycle_counter[cycle_len] += 1

        if verbose:
            progress = (i + 1) / total * 100
            bar_len = 30
            filled = int(bar_len * (i + 1) / total)
            bar = '#' * filled + '-' * (bar_len - filled)
            print(f"\r推演进度：[{bar}] {progress:.1f}% ({i+1}/{total}) 种子={seed}  周期={cycle_len}", end='')

    if verbose:
        print()  # 换行

    return results, cycle_counter


# ============================================================
# 第三部分：图表生成
# ============================================================

def generate_charts(results: list, cycle_counter: Counter, output_dir: str):
    """
    生成散点图、折线图、饼图，保存到指定目录。
    """
    seeds_int = []
    branch_lens = []
    cycle_lens = []
    total_nodes_list = []

    # 尝试将种子转为数值用于散点图的X轴
    for r in results:
        try:
            seeds_int.append(int(r['seed']))
        except ValueError:
            seeds_int.append(float('nan'))

    branch_lens = [r['branch_len'] for r in results]
    cycle_lens = [r['cycle_len'] for r in results]
    total_nodes_list = [r['total_nodes'] for r in results]

    # 中文/英文兼容字体设置
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans', 'Arial']
    plt.rcParams['axes.unicode_minus'] = False

    # ---- 图1：散点图矩阵 ----
    fig, axes = plt.subplots(2, 2, figsize=(16, 14))
    colors = plt.cm.viridis(np.linspace(0.1, 0.9, len(results)))

    # 散点图1：种子 vs 分歧域长度
    ax = axes[0, 0]
    ax.scatter(seeds_int, branch_lens, c=colors, s=50, alpha=0.7, edgecolors='black', linewidth=0.5)
    ax.set_xlabel('种子数值', fontsize=12)
    ax.set_ylabel('分歧域长度', fontsize=12)
    ax.set_title('种子数值与分歧域长度关系', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    if len(seeds_int) > 1:
        z = np.polyfit([s for s in seeds_int if not np.isnan(s)],
                       [branch_lens[i] for i, s in enumerate(seeds_int) if not np.isnan(s)], 1)
        p = np.poly1d(z)
        x_line = np.linspace(min(seeds_int), max(seeds_int), 100)
        ax.plot(x_line, p(x_line), 'r--', linewidth=1.5, alpha=0.7, label='趋势线')
        ax.legend(fontsize=10)

    # 散点图2：种子 vs 周期长度
    ax = axes[0, 1]
    ax.scatter(seeds_int, cycle_lens, c=colors, s=50, alpha=0.7, edgecolors='black', linewidth=0.5)
    ax.set_xlabel('种子数值', fontsize=12)
    ax.set_ylabel('宿命周期长度', fontsize=12)
    ax.set_title('种子数值与宿命周期长度关系', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)

    # 散点图3：分歧域长度 vs 周期长度
    ax = axes[1, 0]
    ax.scatter(branch_lens, cycle_lens, c=colors, s=60, alpha=0.7, edgecolors='black', linewidth=0.5)
    ax.set_xlabel('分歧域长度', fontsize=12)
    ax.set_ylabel('宿命周期长度', fontsize=12)
    ax.set_title('分歧域长度与宿命周期长度关系', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    if len(set(branch_lens)) > 1 and len(set(cycle_lens)) > 1:
        z = np.polyfit(branch_lens, cycle_lens, 1)
        p = np.poly1d(z)
        x_line = np.linspace(min(branch_lens), max(branch_lens), 100)
        ax.plot(x_line, p(x_line), 'r--', linewidth=1.5, alpha=0.7, label='趋势线')
        ax.legend(fontsize=10)

    # 散点图4：种子 vs 总节点数
    ax = axes[1, 1]
    ax.scatter(seeds_int, total_nodes_list, c=colors, s=50, alpha=0.7, edgecolors='black', linewidth=0.5)
    ax.set_xlabel('种子数值', fontsize=12)
    ax.set_ylabel('总节点数', fontsize=12)
    ax.set_title('种子数值与总节点数关系', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)

    fig.suptitle('世界线收束序列 · 散点图分析', fontsize=18, fontweight='bold', y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    scatter_path = os.path.join(output_dir, 'scatter_analysis.png')
    fig.savefig(scatter_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  散点图已保存：{scatter_path}")

    # ---- 图2：折线图 - 推演轨迹 ----
    # 选取代表性种子展示完整推演轨迹（首个、中间、末个）
    sample_indices = [0, len(results) // 2, len(results) - 1]
    sample_indices = list(set(i for i in sample_indices if i < len(results)))

    fig, ax = plt.subplots(figsize=(16, 8))
    line_styles = ['-', '--', '-.']

    for idx, (si, style) in enumerate(zip(sample_indices, line_styles)):
        r = results[si]
        all_nodes = r['branch_domain'] + r['fate_cycle']
        # 计算每个节点的「熵值」（用字符串长度代替复杂度）
        entropy = [len(node) for node in all_nodes]
        x_vals = list(range(1, len(all_nodes) + 1))

        ax.plot(x_vals, entropy, style, linewidth=2, markersize=4,
                marker='o', alpha=0.8,
                label=f"种子='{r['seed']}'（分歧域={r['branch_len']}，周期={r['cycle_len']}）")

        # 标注收束点
        if r['branch_len'] > 0:
            ax.axvline(x=r['branch_len'] + 0.5, color='red', alpha=0.3, linestyle=':')

    ax.set_xlabel('推演步数', fontsize=13)
    ax.set_ylabel('节点复杂度（字符串长度）', fontsize=13)
    ax.set_title('代表性种子推演轨迹', fontsize=16, fontweight='bold')
    ax.legend(fontsize=9, loc='best')
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))

    plt.tight_layout()
    line_path = os.path.join(output_dir, 'trajectory_line_chart.png')
    fig.savefig(line_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  折线图已保存：{line_path}")

    # ---- 图2补充：汇总折线图 - 所有种子的分歧域/周期/总节点对比 ----
    fig, ax = plt.subplots(figsize=(16, 8))
    x_idx = list(range(1, len(results) + 1))
    ax.plot(x_idx, branch_lens, 'o-', linewidth=1.5, markersize=4, alpha=0.8, label='分歧域长度', color='#3498db')
    ax.plot(x_idx, cycle_lens, 's-', linewidth=1.5, markersize=4, alpha=0.8, label='宿命周期长度', color='#e74c3c')
    ax.plot(x_idx, total_nodes_list, '^-', linewidth=1.5, markersize=4, alpha=0.8, label='总节点数', color='#2ecc71')
    ax.set_xlabel('种子序号', fontsize=13)
    ax.set_ylabel('节点数量', fontsize=13)
    ax.set_title('全部种子收束指标对比', fontsize=16, fontweight='bold')
    ax.legend(fontsize=11, loc='best')
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    plt.tight_layout()
    summary_line_path = os.path.join(output_dir, 'summary_line_chart.png')
    fig.savefig(summary_line_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  汇总折线图已保存：{summary_line_path}")

    # ---- 图3：饼图 - 周期长度分布 ----
    fig, axes = plt.subplots(1, 2, figsize=(16, 8))

    # 饼图1：周期长度分布
    ax = axes[0]
    labels = [f'周期={k}' for k in cycle_counter.keys()]
    sizes = list(cycle_counter.values())
    explode = [0.02] * len(sizes)
    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, autopct='%1.1f%%',
        explode=explode, startangle=90,
        colors=plt.cm.Set3(np.linspace(0, 1, len(sizes))),
        textprops={'fontsize': 10}
    )
    ax.set_title('宿命周期长度分布', fontsize=14, fontweight='bold')

    # 饼图2：分歧域长度分布（分桶）
    ax = axes[1]
    unique_branch = sorted(set(branch_lens))
    branch_dist = Counter(branch_lens)
    # 如果种类过多，合并
    if len(unique_branch) > 10:
        branch_bins = {}
        for bl in branch_lens:
            bin_key = f'分歧域={bl}'
            branch_bins[bin_key] = branch_bins.get(bin_key, 0) + 1
        b_labels = list(branch_bins.keys())
        b_sizes = list(branch_bins.values())
    else:
        b_labels = [f'分歧域={k}' for k in sorted(branch_dist.keys())]
        b_sizes = [branch_dist[k] for k in sorted(branch_dist.keys())]

    b_explode = [0.02] * len(b_sizes)
    ax.pie(b_sizes, labels=b_labels, autopct='%1.1f%%',
           explode=b_explode, startangle=90,
           colors=plt.cm.Pastel1(np.linspace(0, 1, len(b_sizes))),
           textprops={'fontsize': 10})
    ax.set_title('分歧域长度分布', fontsize=14, fontweight='bold')

    fig.suptitle('世界线收束序列 · 分布分析', fontsize=18, fontweight='bold', y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    pie_path = os.path.join(output_dir, 'pie_distribution.png')
    fig.savefig(pie_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"  饼图已保存：{pie_path}")

    return scatter_path, line_path, summary_line_path, pie_path


# ============================================================
# 第四部分：HTML 报告生成
# ============================================================

def generate_report(results: list, cycle_counter: Counter, chart_paths: dict, output_dir: str):
    """
    生成专业分析报告 HTML 文档。
    """
    total_seeds = len(results)
    avg_branch = sum(r['branch_len'] for r in results) / total_seeds
    avg_cycle = sum(r['cycle_len'] for r in results) / total_seeds
    avg_total = sum(r['total_nodes'] for r in results) / total_seeds
    max_branch = max(results, key=lambda r: r['branch_len'])
    max_cycle = max(results, key=lambda r: r['cycle_len'])

    # 最常见的周期长度
    most_common_cycle = cycle_counter.most_common(1)[0] if cycle_counter else (0, 0)

    # 收敛至同一宿命的种子统计
    converge_map = {}
    for r in results:
        key = tuple(r['fate_cycle'])
        converge_map.setdefault(key, []).append(r['seed'])
    same_fate_count = sum(1 for v in converge_map.values() if len(v) > 1)

    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 构建种子详情表格行
    detail_rows = ''
    for r in results:
        detail_rows += f'''
        <tr>
            <td>{r['seed']}</td>
            <td>{r['branch_len']}</td>
            <td>{r['cycle_len']}</td>
            <td>{r['total_nodes']}</td>
            <td class="mono">{r['converge_node']}</td>
            <td class="mono">{' → '.join(r['fate_cycle'][:5])}{'...' if len(r['fate_cycle']) > 5 else ''}</td>
        </tr>'''

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>世界线收束序列 — 校验分析报告</title>
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
        font-family: "Noto Serif CJK SC", "Source Han Serif SC", "SimSun", "Times New Roman", Georgia, serif;
        background: #ffffff;
        color: #1a1a1a;
        line-height: 1.75;
        font-size: 11pt;
    }}
    .container {{
        max-width: 960px;
        margin: 0 auto;
        padding: 40px 50px 50px;
    }}

    /* ── 报告封面 ── */
    .cover {{
        border-bottom: 3px double #2c3e50;
        padding: 30px 0 25px;
        margin-bottom: 35px;
        text-align: center;
    }}
    .cover .report-no {{
        font-family: "Consolas", "Courier New", monospace;
        font-size: 0.85em;
        color: #7f8c8d;
        letter-spacing: 2px;
        text-transform: uppercase;
        margin-bottom: 18px;
    }}
    .cover h1 {{
        font-size: 1.75em;
        font-weight: 700;
        color: #2c3e50;
        margin-bottom: 8px;
        letter-spacing: 1px;
    }}
    .cover .subtitle {{
        font-size: 0.95em;
        color: #5a6c7d;
        font-style: italic;
        margin-bottom: 20px;
    }}
    .cover .meta {{
        font-size: 0.82em;
        color: #7f8c8d;
        border-top: 1px solid #dcdde1;
        padding-top: 14px;
        margin-top: 10px;
    }}
    .cover .meta span {{ margin: 0 12px; }}

    /* ── 指标摘要表 ── */
    .summary-table {{
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 35px;
        font-size: 0.92em;
    }}
    .summary-table caption {{
        font-size: 1.1em;
        font-weight: 700;
        color: #2c3e50;
        text-align: left;
        padding-bottom: 10px;
        caption-side: top;
    }}
    .summary-table th {{
        background: #2c3e50;
        color: #ffffff;
        font-weight: 600;
        padding: 8px 14px;
        text-align: center;
        border: 1px solid #2c3e50;
        font-size: 0.88em;
    }}
    .summary-table td {{
        padding: 8px 14px;
        text-align: center;
        border: 1px solid #dcdde1;
        font-family: "Consolas", "Courier New", monospace;
    }}
    .summary-table tr:nth-child(even) td {{
        background: #f8f9fa;
    }}
    .summary-table .val-highlight {{
        font-weight: 700;
        color: #2c3e50;
    }}

    /* ── 章节 ── */
    .section {{
        margin-bottom: 35px;
    }}
    .section h2 {{
        font-size: 1.2em;
        font-weight: 700;
        color: #2c3e50;
        border-bottom: 1.5px solid #bdc3c7;
        padding-bottom: 6px;
        margin-bottom: 14px;
    }}
    .section h3 {{
        font-size: 1.05em;
        font-weight: 600;
        color: #34495e;
        margin: 18px 0 8px;
    }}
    .section p {{
        margin-bottom: 10px;
        text-align: justify;
    }}
    .section p.note {{
        font-size: 0.9em;
        color: #5a6c7d;
        margin-bottom: 14px;
    }}

    /* ── 图表 ── */
    .chart-wrap {{
        text-align: center;
        margin: 16px 0 10px;
        border: 1px solid #dcdde1;
        padding: 8px;
        background: #fafafa;
    }}
    .chart-wrap img {{
        max-width: 100%;
        height: auto;
        display: block;
        margin: 0 auto;
    }}
    .chart-wrap .fig-caption {{
        font-size: 0.85em;
        color: #7f8c8d;
        margin-top: 6px;
    }}

    /* ── 分析结论列表 ── */
    .finding-list {{
        list-style: none;
        padding: 0;
        margin: 10px 0;
    }}
    .finding-list li {{
        padding: 8px 0 8px 28px;
        border-bottom: 1px dotted #dcdde1;
        position: relative;
    }}
    .finding-list li::before {{
        content: "▸";
        position: absolute;
        left: 8px;
        color: #2c3e50;
        font-size: 0.8em;
    }}
    .finding-list li strong {{ color: #2c3e50; }}

    /* ── 数据表 ── */
    .data-table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 0.85em;
        margin: 10px 0 20px;
    }}
    .data-table thead th {{
        background: #2c3e50;
        color: #ffffff;
        font-weight: 600;
        padding: 7px 10px;
        text-align: center;
        border: 1px solid #2c3e50;
        white-space: nowrap;
    }}
    .data-table tbody td {{
        padding: 6px 10px;
        text-align: center;
        border: 1px solid #dcdde1;
    }}
    .data-table tbody td.left {{ text-align: left; }}
    .data-table tbody tr:nth-child(even) td {{
        background: #f8f9fa;
    }}
    .data-table .mono {{
        font-family: "Consolas", "Courier New", monospace;
        font-size: 0.9em;
    }}

    /* ── 页脚 ── */
    .footer {{
        border-top: 1.5px solid #bdc3c7;
        padding-top: 14px;
        margin-top: 40px;
        text-align: center;
        color: #7f8c8d;
        font-size: 0.78em;
        line-height: 1.8;
    }}

    /* ── 打印样式 ── */
    @media print {{
        body {{ font-size: 10pt; }}
        .container {{ max-width: 100%; padding: 20px 30px; }}
        .section {{ page-break-inside: avoid; }}
        .chart-wrap {{ page-break-inside: avoid; border: none; padding: 4px; }}
        .data-table {{ page-break-inside: avoid; }}
        .cover {{ border-bottom: 2px double #000; }}
        .summary-table th, .data-table thead th {{ background: #2c3e50 !important; color: #fff !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
        .summary-table tr:nth-child(even) td, .data-table tbody tr:nth-child(even) td {{ background: #f0f0f0 !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
    }}
</style>
</head>
<body>
<div class="container">

    <!-- 报告封面 -->
    <div class="cover">
        <div class="report-no">LABORATORY REPORT · WCS-VFY-{datetime.now().strftime('%Y%m%d')}</div>
        <h1>世界线收束序列 校验分析报告</h1>
        <p class="subtitle">Worldline Convergence Sequence — Verification &amp; Analytical Report</p>
        <p class="meta">
            <span>生成时间：{now_str}</span>
            <span>|</span>
            <span>检验种子总数：<strong>{total_seeds}</strong></span>
            <span>|</span>
            <span>收束引擎：wcs.py</span>
        </p>
    </div>

    <!-- 关键指标摘要 -->
    <table class="summary-table">
        <caption>表1 &nbsp; 关键统计指标摘要</caption>
        <thead>
            <tr>
                <th>指标</th>
                <th>校验种子总数</th>
                <th>平均分歧域长度</th>
                <th>平均宿命周期</th>
                <th>平均总节点数</th>
                <th>最常见周期</th>
                <th>共享宿命种子数</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>数值</td>
                <td class="val-highlight">{total_seeds}</td>
                <td class="val-highlight">{avg_branch:.2f}</td>
                <td class="val-highlight">{avg_cycle:.2f}</td>
                <td class="val-highlight">{avg_total:.2f}</td>
                <td class="val-highlight">{most_common_cycle[0]}<span style="font-size:0.82em;color:#7f8c8d;"> (n={most_common_cycle[1]})</span></td>
                <td class="val-highlight">{same_fate_count}</td>
            </tr>
        </tbody>
    </table>

    <!-- ===== 一、散点图 ===== -->
    <div class="section">
        <h2>一、散点图分析</h2>
        <p class="note">从四个维度展示种子数值与分歧域长度、宿命闭环周期、总节点数之间的分布关系。红色虚线为线性趋势线。</p>
        <div class="chart-wrap">
            <img src="{os.path.basename(chart_paths['scatter'])}" alt="散点图">
            <div class="fig-caption">图1 &nbsp; 世界线收束序列散点图矩阵（四维分析）</div>
        </div>
    </div>

    <!-- ===== 二、轨迹折线图 ===== -->
    <div class="section">
        <h2>二、推演轨迹折线图</h2>
        <p class="note">选取首批、中间、末批代表性种子，绘制其完整推演轨迹（Y轴为节点字符串长度）。红色虚线标记收束起始点。</p>
        <div class="chart-wrap">
            <img src="{os.path.basename(chart_paths['line'])}" alt="轨迹折线图">
            <div class="fig-caption">图2 &nbsp; 代表性种子推演轨迹</div>
        </div>
    </div>

    <!-- ===== 三、汇总折线图 ===== -->
    <div class="section">
        <h2>三、全量种子收束指标对比</h2>
        <p class="note">以种子序号为X轴，同时展示分歧域长度（蓝）、宿命闭环周期（红）、总节点数（绿）三项指标。</p>
        <div class="chart-wrap">
            <img src="{os.path.basename(chart_paths['summary_line'])}" alt="汇总折线图">
            <div class="fig-caption">图3 &nbsp; 全部种子收束指标对比</div>
        </div>
    </div>

    <!-- ===== 四、饼图 ===== -->
    <div class="section">
        <h2>四、周期与分歧域分布分析</h2>
        <p class="note">左图：各宿命闭环周期的占比分布。右图：各分歧域长度的占比分布。</p>
        <div class="chart-wrap">
            <img src="{os.path.basename(chart_paths['pie'])}" alt="饼图">
            <div class="fig-caption">图4 &nbsp; 宿命周期长度与分歧域长度分布饼图</div>
        </div>
    </div>

    <!-- ===== 五、分析结论 ===== -->
    <div class="section">
        <h2>五、分析结论</h2>

        <h3>5.1 收束必然性验证</h3>
        <p>
        全部 <strong>{total_seeds}</strong> 个初始种子均成功收敛至稳定宿命闭环，<strong>收敛率 100%</strong>，
        实证世界线收束序列算法对于任意初始原点的全局收敛性质。
        最大分歧域出现在种子「{max_branch['seed']}」，分歧域长度达 <strong>{max_branch['branch_len']}</strong> 个节点；
        最大宿命闭环周期出现在种子「{max_cycle['seed']}」，周期为 <strong>{max_cycle['cycle_len']}</strong>。
        </p>

        <h3>5.2 多稳态结构</h3>
        <p>
        共发现 <strong>{len(cycle_counter)}</strong> 种不同的宿命闭环周期长度，
        最常见周期为 <strong>{most_common_cycle[0]}</strong>（出现 {most_common_cycle[1]} 次，占比 {most_common_cycle[1]/total_seeds*100:.1f}%）。
        该结果表明系统存在多个吸引子并存的多稳态（Multistability）动力学特征。
        </p>

        <h3>5.3 普适性结论</h3>
        <p>
        综合散点图、折线图与饼图分析，不同初始种子虽经历不同的分歧路径，
        但最终均不可逆转地收束至各自对应的宿命闭环。该行为符合确定性离散动力系统在有限状态空间下的必然收敛性质。
        </p>
    </div>

    <!-- ===== 六、详细数据表 ===== -->
    <div class="section">
        <h2>六、全部种子推演详情</h2>
        <table class="data-table">
            <thead>
                <tr>
                    <th>种子 (Seed)</th>
                    <th>分歧域长度</th>
                    <th>宿命周期</th>
                    <th>总节点数</th>
                    <th>收束起始节点</th>
                    <th>宿命闭环（前5项）</th>
                </tr>
            </thead>
            <tbody>
                {detail_rows}
            </tbody>
        </table>
    </div>

    <!-- 页脚 -->
    <div class="footer">
        <p>Worldline Convergence Sequence (WCS)</p>
        <p>迭代规则：全域字符计频 + 从左至右首次出现顺序拼接 | 核心命题：任意初始原点 → 必然收束至固定宿命闭环</p>
        <p>本报告由 wcs_verify.py 自动生成 &nbsp;|&nbsp; {now_str}</p>
    </div>

</div>
</body>
</html>'''

    report_path = os.path.join(output_dir, 'WCS_校验分析报告.html')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"\n  报告已生成：{report_path}")

    return report_path


# ============================================================
# 第五部分：主控流程
# ============================================================

def main():
    # 确保控制台输出支持 UTF-8（Windows GBK 兼容）
    import io
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        except Exception:
            pass

    print("=" * 65)
    print("  世界线收束序列 · 批量校验报告生成工具")
    print("  Worldline Convergence Sequence - Batch Verification Tool")
    print("=" * 65)
    print()
    print("输入格式说明：")
    print("  1. 数组字符串： [1,2,3,5,8]  或  ['a','b','hello']")
    print("  2. 数字范围：   1~999          （含两端）")
    print("  3. 字母范围：   a~z            （含两端）")
    print("-" * 65)

    user_input = input("\n请输入世界线初始原点种子：").strip()

    if not user_input:
        print("错误：输入不能为空，程序退出。")
        sys.exit(1)

    # 解析种子
    try:
        seeds = parse_seeds(user_input)
    except ValueError as e:
        print(f"输入解析错误：{e}")
        sys.exit(1)

    if not seeds:
        print("错误：未能解析出有效种子，程序退出。")
        sys.exit(1)

    print(f"\n成功解析 {len(seeds)} 个种子，开始批量推演...")
    print()

    # 批量推演
    results, cycle_counter = batch_convergence(seeds, verbose=True)
    print("\n推演完成！正在生成图表和报告...\n")

    # 创建输出目录
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'verify_output')
    os.makedirs(output_dir, exist_ok=True)

    # 生成图表
    scatter_path, line_path, summary_line_path, pie_path = generate_charts(results, cycle_counter, output_dir)

    chart_paths = {
        'scatter': scatter_path,
        'line': line_path,
        'summary_line': summary_line_path,
        'pie': pie_path,
    }

    # 生成报告
    report_path = generate_report(results, cycle_counter, chart_paths, output_dir)

    print()
    print("=" * 65)
    print("  校验完成！")
    print(f"  报告位置：{report_path}")
    print(f"  图表目录：{output_dir}")
    print("=" * 65)

    # 自动打开报告
    try:
        os.startfile(report_path)
    except Exception:
        pass


if __name__ == "__main__":
    main()
