"""
visualization.py
----------------
Chart and graph rendering module.

Uses Matplotlib/Seaborn for static charts embedded in Tkinter,
and NetworkX+Matplotlib for the contributor network graph.
All charts follow a unified dark-tech colour palette.
"""

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import seaborn as sns
import networkx as nx
from typing import Optional

# ─── Colour Palette ────────────────────────────────────────────────────────── #
PALETTE = {
    'bg':         '#0D1117',   # GitHub dark background
    'surface':    '#161B22',   # Card/panel surface
    'border':     '#30363D',   # Subtle border
    'accent':     '#58A6FF',   # Primary blue
    'accent2':    '#3FB950',   # Green (success)
    'accent3':    '#F78166',   # Red/orange
    'accent4':    '#D2A8FF',   # Purple
    'accent5':    '#FFA657',   # Orange
    'text':       '#E6EDF3',   # Primary text
    'text_muted': '#8B949E',   # Muted text
}

CHART_COLORS = [
    PALETTE['accent'], PALETTE['accent2'], PALETTE['accent3'],
    PALETTE['accent4'], PALETTE['accent5'],
    '#79C0FF', '#56D364', '#FF7B72', '#BC8CFF', '#FFB347',
]

def _apply_dark_style(fig: Figure, axes):
    """Apply the unified dark theme to a figure and its axes."""
    fig.patch.set_facecolor(PALETTE['bg'])
    if not hasattr(axes, '__iter__'):
        axes = [axes]
    for ax in axes:
        ax.set_facecolor(PALETTE['surface'])
        ax.tick_params(colors=PALETTE['text_muted'], labelsize=8)
        ax.xaxis.label.set_color(PALETTE['text'])
        ax.yaxis.label.set_color(PALETTE['text'])
        if ax.get_title():
            ax.title.set_color(PALETTE['text'])
        for spine in ax.spines.values():
            spine.set_edgecolor(PALETTE['border'])
        ax.grid(color=PALETTE['border'], linestyle='--', linewidth=0.5, alpha=0.6)


# ─── Commit Activity Charts ─────────────────────────────────────────────────── #

def plot_commit_activity(analytics, master_frame) -> FigureCanvasTkAgg:
    """
    Render a 2×2 commit activity panel:
      - Daily commits (bar)
      - Weekly commits (line)
      - Monthly commits (bar)
      - Commits by weekday (horizontal bar)

    Args:
        analytics: RepositoryAnalytics instance.
        master_frame: Tkinter parent widget.

    Returns:
        FigureCanvasTkAgg embedded in master_frame.
    """
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.patch.set_facecolor(PALETTE['bg'])
    fig.suptitle('Commit Activity Analysis', color=PALETTE['text'],
                 fontsize=14, fontweight='bold', y=1.01)
    plt.subplots_adjust(hspace=0.45, wspace=0.35)

    # 1. Daily commits
    ax = axes[0, 0]
    daily = analytics.daily_commits()
    if not daily.empty:
        ax.bar(daily['Date'], daily['commits'],
               color=PALETTE['accent'], alpha=0.8, width=0.8)
        ax.set_title('Daily Commits', color=PALETTE['text'], fontsize=10)
        ax.set_xlabel('Date', fontsize=8)
        ax.set_ylabel('Commits', fontsize=8)
        _rotate_xlabels(ax)
    else:
        _no_data(ax, 'Daily Commits')

    # 2. Weekly commits
    ax = axes[0, 1]
    weekly = analytics.weekly_commits()
    if not weekly.empty:
        ax.plot(weekly['Week'], weekly['commits'],
                color=PALETTE['accent2'], linewidth=2, marker='o',
                markersize=4, markerfacecolor=PALETTE['accent5'])
        ax.fill_between(weekly['Week'], weekly['commits'],
                        alpha=0.15, color=PALETTE['accent2'])
        ax.set_title('Weekly Commits', color=PALETTE['text'], fontsize=10)
        ax.set_xlabel('Week', fontsize=8)
        ax.set_ylabel('Commits', fontsize=8)
        _rotate_xlabels(ax)
    else:
        _no_data(ax, 'Weekly Commits')

    # 3. Monthly commits
    ax = axes[1, 0]
    monthly = analytics.monthly_commits()
    if not monthly.empty:
        colors_m = [PALETTE['accent4'] if i % 2 == 0 else PALETTE['accent3']
                    for i in range(len(monthly))]
        bars = ax.bar(range(len(monthly)), monthly['commits'],
                      color=colors_m, alpha=0.85)
        ax.set_xticks(range(len(monthly)))
        ax.set_xticklabels(
            [str(m)[:7] for m in monthly['Month']],
            rotation=45, ha='right', fontsize=7
        )
        ax.set_title('Monthly Commits', color=PALETTE['text'], fontsize=10)
        ax.set_ylabel('Commits', fontsize=8)
    else:
        _no_data(ax, 'Monthly Commits')

    # 4. Commits by weekday
    ax = axes[1, 1]
    busiest = analytics.busiest_days()
    if not busiest.empty:
        days_col = busiest.columns[0]
        counts_col = busiest.columns[1]
        colors_d = [PALETTE['accent5'] if busiest[counts_col].iloc[i] == busiest[counts_col].max()
                    else PALETTE['accent'] for i in range(len(busiest))]
        ax.barh(busiest[days_col], busiest[counts_col], color=colors_d, alpha=0.85)
        ax.set_title('Commits by Day of Week', color=PALETTE['text'], fontsize=10)
        ax.set_xlabel('Commits', fontsize=8)
    else:
        _no_data(ax, 'Commits by Day')

    for row in axes:
        for ax in row:
            _apply_dark_style(fig, ax)

    return _embed(fig, master_frame)


# ─── Language Charts ────────────────────────────────────────────────────────── #

def plot_languages(analytics, master_frame) -> FigureCanvasTkAgg:
    """
    Render a side-by-side pie + horizontal bar chart for language distribution.

    Args:
        analytics: RepositoryAnalytics instance.
        master_frame: Tkinter parent widget.

    Returns:
        FigureCanvasTkAgg embedded in master_frame.
    """
    fig, (ax_pie, ax_bar) = plt.subplots(1, 2, figsize=(12, 5))
    fig.patch.set_facecolor(PALETTE['bg'])
    fig.suptitle('Language Distribution', color=PALETTE['text'],
                 fontsize=14, fontweight='bold')

    df = analytics.language_df

    if df is None or df.empty:
        _no_data(ax_pie, 'Languages')
        _no_data(ax_bar, 'Languages')
        return _embed(fig, master_frame)

    # Group small languages into "Other"
    threshold = 2.0  # % below which languages are grouped
    major = df[df['Percentage'] >= threshold].copy()
    minor_sum = df[df['Percentage'] < threshold]['Bytes'].sum()
    minor_pct = df[df['Percentage'] < threshold]['Percentage'].sum()

    labels = list(major['Language'])
    sizes  = list(major['Bytes'])
    pcts   = list(major['Percentage'])

    if minor_sum > 0:
        labels.append('Other')
        sizes.append(minor_sum)
        pcts.append(round(minor_pct, 2))

    colors = CHART_COLORS[:len(labels)]

    # Pie chart
    wedges, texts, autotexts = ax_pie.pie(
        sizes, labels=None, colors=colors,
        autopct=lambda p: f'{p:.1f}%' if p > 4 else '',
        startangle=140, pctdistance=0.75,
        wedgeprops=dict(edgecolor=PALETTE['bg'], linewidth=1.5),
    )
    for at in autotexts:
        at.set_color(PALETTE['bg'])
        at.set_fontsize(8)
        at.set_fontweight('bold')

    ax_pie.set_facecolor(PALETTE['surface'])
    ax_pie.set_title('Language Share', color=PALETTE['text'], fontsize=11)
    ax_pie.legend(
        wedges, [f"{l} ({p}%)" for l, p in zip(labels, pcts)],
        loc='lower left', bbox_to_anchor=(0, -0.25),
        facecolor=PALETTE['surface'], edgecolor=PALETTE['border'],
        labelcolor=PALETTE['text'], fontsize=8,
    )

    # Bar chart
    ax_bar.set_facecolor(PALETTE['surface'])
    y_pos = range(len(labels))
    bars = ax_bar.barh(y_pos, pcts, color=colors, alpha=0.9)
    ax_bar.set_yticks(y_pos)
    ax_bar.set_yticklabels(labels, color=PALETTE['text'], fontsize=9)
    ax_bar.set_xlabel('Percentage (%)', color=PALETTE['text'], fontsize=9)
    ax_bar.set_title('Language Comparison', color=PALETTE['text'], fontsize=11)
    ax_bar.invert_yaxis()

    for bar, pct in zip(bars, pcts):
        ax_bar.text(
            bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
            f'{pct}%', va='center', color=PALETTE['text_muted'], fontsize=8
        )

    _apply_dark_style(fig, ax_bar)
    fig.tight_layout()
    return _embed(fig, master_frame)


# ─── Contributor Charts ─────────────────────────────────────────────────────── #

def plot_contributors(analytics, master_frame) -> FigureCanvasTkAgg:
    """
    Render top-contributors bar chart with contribution percentage overlay.

    Args:
        analytics: RepositoryAnalytics instance.
        master_frame: Tkinter parent widget.

    Returns:
        FigureCanvasTkAgg embedded in master_frame.
    """
    fig, ax = plt.subplots(figsize=(12, 5))
    fig.patch.set_facecolor(PALETTE['bg'])

    df = analytics.contributor_df
    if df is None or df.empty:
        _no_data(ax, 'Contributors')
        return _embed(fig, master_frame)

    top = df.head(15).copy()
    colors = [CHART_COLORS[i % len(CHART_COLORS)] for i in range(len(top))]

    bars = ax.bar(top['login'], top['contributions'], color=colors, alpha=0.85)

    # Annotate each bar with commit count
    for bar, commits in zip(bars, top['contributions']):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + bar.get_height() * 0.01,
            str(commits),
            ha='center', va='bottom',
            color=PALETTE['text'], fontsize=7, fontweight='bold'
        )

    ax.set_title('Top Contributors by Commit Count', color=PALETTE['text'],
                 fontsize=12, fontweight='bold')
    ax.set_xlabel('Contributor', fontsize=9)
    ax.set_ylabel('Commits', fontsize=9)
    plt.xticks(rotation=30, ha='right')

    _apply_dark_style(fig, ax)
    fig.tight_layout()
    return _embed(fig, master_frame)


# ─── Network Graph ──────────────────────────────────────────────────────────── #

def plot_network_graph(contributor_graph, master_frame,
                       layout: str = 'spring') -> FigureCanvasTkAgg:
    """
    Render the contributor → repository NetworkX graph.

    Node size encodes commit count (contributors) or star count (repo).
    Edge width encodes commit weight.

    Args:
        contributor_graph: ContributorGraph instance.
        master_frame:      Tkinter parent widget.
        layout:            Layout algorithm name.

    Returns:
        FigureCanvasTkAgg embedded in master_frame.
    """
    G   = contributor_graph.graph
    pos = contributor_graph.get_layout(layout)

    fig, ax = plt.subplots(figsize=(12, 7))
    fig.patch.set_facecolor(PALETTE['bg'])
    ax.set_facecolor(PALETTE['bg'])
    ax.set_title('Contributor Network Graph', color=PALETTE['text'],
                 fontsize=13, fontweight='bold', pad=12)
    ax.axis('off')

    if not G or G.number_of_nodes() == 0:
        _no_data(ax, 'Network Graph')
        return _embed(fig, master_frame)

    # Separate node types
    repo_nodes  = [n for n, d in G.nodes(data=True) if d.get('node_type') == 'repository']
    contr_nodes = [n for n, d in G.nodes(data=True) if d.get('node_type') == 'contributor']

    # Edge widths proportional to commit weight (log-scaled)
    edges      = list(G.edges(data=True))
    max_weight = max((e[2].get('weight', 1) for e in edges), default=1)
    edge_widths = [
        1.0 + 3.0 * (np.log1p(e[2].get('weight', 1)) / np.log1p(max_weight))
        for e in edges
    ]

    # Draw edges
    nx.draw_networkx_edges(
        G, pos, ax=ax,
        edge_color=PALETTE['border'],
        alpha=0.6,
        width=edge_widths,
        arrowsize=12,
        connectionstyle='arc3,rad=0.1',
    )

    # Contributor node sizes ∝ log(commits)
    max_commits = max(
        (G.nodes[n].get('commits', 1) for n in contr_nodes), default=1
    )
    contr_sizes = [
        300 + 1200 * (np.log1p(G.nodes[n].get('commits', 0)) / np.log1p(max_commits))
        for n in contr_nodes
    ]

    nx.draw_networkx_nodes(
        G, pos, nodelist=contr_nodes, ax=ax,
        node_color=PALETTE['accent'],
        node_size=contr_sizes,
        alpha=0.9,
    )

    # Repository node (larger, distinct colour)
    if repo_nodes:
        nx.draw_networkx_nodes(
            G, pos, nodelist=repo_nodes, ax=ax,
            node_color=PALETTE['accent5'],
            node_size=[2500] * len(repo_nodes),
            alpha=0.95,
        )

    # Labels – shorten long names
    labels = {n: (n[:12] + '…' if len(n) > 13 else n) for n in G.nodes()}
    nx.draw_networkx_labels(
        G, pos, labels=labels, ax=ax,
        font_color=PALETTE['text'],
        font_size=7,
        font_weight='bold',
    )

    # Legend
    legend_elements = [
        mpatches.Patch(facecolor=PALETTE['accent5'], label='Repository'),
        mpatches.Patch(facecolor=PALETTE['accent'],  label='Contributor'),
    ]
    ax.legend(
        handles=legend_elements, loc='upper left',
        facecolor=PALETTE['surface'], edgecolor=PALETTE['border'],
        labelcolor=PALETTE['text'], fontsize=9,
    )

    fig.tight_layout()
    return _embed(fig, master_frame)


# ─── Health Score Gauge ─────────────────────────────────────────────────────── #

def plot_health_gauge(health_data: dict, master_frame) -> FigureCanvasTkAgg:
    """
    Render a health score gauge (half-donut) plus breakdown bars.

    Args:
        health_data: Output of RepositoryAnalytics.compute_health_score().
        master_frame: Tkinter parent widget.

    Returns:
        FigureCanvasTkAgg embedded in master_frame.
    """
    fig, (ax_gauge, ax_bars) = plt.subplots(1, 2, figsize=(12, 5))
    fig.patch.set_facecolor(PALETTE['bg'])

    score = health_data.get('total', 0)
    grade = health_data.get('grade', '?')

    # ── Half-donut gauge ──
    ax_gauge.set_facecolor(PALETTE['bg'])
    ax_gauge.set_aspect('equal')
    ax_gauge.axis('off')

    # Determine colour from score
    if score >= 75:
        score_color = PALETTE['accent2']
    elif score >= 50:
        score_color = PALETTE['accent5']
    else:
        score_color = PALETTE['accent3']

    # Background arc (full half-circle)
    theta = np.linspace(np.pi, 0, 200)
    r_outer, r_inner = 1.0, 0.65
    ax_gauge.fill_between(
        np.concatenate([r_outer * np.cos(theta), r_inner * np.cos(theta[::-1])]),
        np.concatenate([r_outer * np.sin(theta), r_inner * np.sin(theta[::-1])]),
        color=PALETTE['surface'], zorder=1
    )

    # Filled arc for score
    fill_angle = np.pi - (score / 100) * np.pi
    theta_fill = np.linspace(np.pi, fill_angle, 200)
    ax_gauge.fill_between(
        np.concatenate([r_outer * np.cos(theta_fill), r_inner * np.cos(theta_fill[::-1])]),
        np.concatenate([r_outer * np.sin(theta_fill), r_inner * np.sin(theta_fill[::-1])]),
        color=score_color, zorder=2, alpha=0.9
    )

    # Score text
    ax_gauge.text(0, 0.05, f'{score:.0f}', ha='center', va='center',
                  fontsize=36, fontweight='bold', color=score_color, zorder=3)
    ax_gauge.text(0, -0.2, f'Grade: {grade}', ha='center', va='center',
                  fontsize=14, color=PALETTE['text'], zorder=3)
    ax_gauge.text(0, -0.38, 'Health Score / 100', ha='center', va='center',
                  fontsize=9, color=PALETTE['text_muted'], zorder=3)
    ax_gauge.set_xlim(-1.2, 1.2)
    ax_gauge.set_ylim(-0.5, 1.2)
    ax_gauge.set_title('Repository Health Score', color=PALETTE['text'],
                       fontsize=11, fontweight='bold', pad=10)

    # ── Breakdown bars ──
    ax_bars.set_facecolor(PALETTE['surface'])
    breakdown = health_data.get('breakdown', {})
    max_scores = health_data.get('max_scores', {})
    dimensions = list(breakdown.keys())
    achieved   = list(breakdown.values())
    maximums   = [max_scores.get(d, 25) for d in dimensions]

    bar_colors = [PALETTE['accent2'] if a / m >= 0.7 else
                  (PALETTE['accent5'] if a / m >= 0.4 else PALETTE['accent3'])
                  for a, m in zip(achieved, maximums)]

    y_pos = range(len(dimensions))
    ax_bars.barh(y_pos, maximums, color=PALETTE['border'], alpha=0.4, height=0.5)
    ax_bars.barh(y_pos, achieved, color=bar_colors, alpha=0.9, height=0.5)
    ax_bars.set_yticks(y_pos)
    ax_bars.set_yticklabels(dimensions, fontsize=8)
    ax_bars.set_xlabel('Score', fontsize=9)
    ax_bars.set_title('Score Breakdown', color=PALETTE['text'], fontsize=11, fontweight='bold')

    for i, (a, m) in enumerate(zip(achieved, maximums)):
        ax_bars.text(m + 0.2, i, f'{a}/{m}', va='center',
                     fontsize=8, color=PALETTE['text_muted'])

    _apply_dark_style(fig, ax_bars)
    ax_bars.tick_params(colors=PALETTE['text_muted'])
    for label in ax_bars.get_yticklabels():
        label.set_color(PALETTE['text'])

    fig.tight_layout()
    return _embed(fig, master_frame)


# ─── Utility Helpers ────────────────────────────────────────────────────────── #

def _embed(fig: Figure, master) -> FigureCanvasTkAgg:
    """Embed a matplotlib Figure into a Tkinter widget."""
    canvas = FigureCanvasTkAgg(fig, master=master)
    canvas.draw()
    return canvas


def _no_data(ax, title: str):
    """Show a 'no data' placeholder in an axes."""
    ax.set_facecolor(PALETTE['surface'])
    ax.text(0.5, 0.5, 'No data available', transform=ax.transAxes,
            ha='center', va='center', color=PALETTE['text_muted'],
            fontsize=11)
    ax.set_title(title, color=PALETTE['text'], fontsize=10)
    ax.axis('off')


def _rotate_xlabels(ax, rotation=30):
    """Rotate x-axis tick labels for readability."""
    plt.setp(ax.get_xticklabels(), rotation=rotation, ha='right', fontsize=7)
