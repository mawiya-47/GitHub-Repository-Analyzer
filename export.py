"""
export.py
---------
Data export module supporting CSV, Excel (.xlsx), and PDF report generation.
"""

import os
import io
from datetime import datetime
from typing import Optional

import pandas as pd
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


# ─── Colour Constants for PDF ───────────────────────────────────────────────── #
PDF_BG     = colors.HexColor('#0D1117')
PDF_ACCENT = colors.HexColor('#58A6FF')
PDF_GREEN  = colors.HexColor('#3FB950')
PDF_TEXT   = colors.HexColor('#E6EDF3')
PDF_MUTED  = colors.HexColor('#8B949E')
PDF_SURFACE= colors.HexColor('#161B22')
PDF_BORDER = colors.HexColor('#30363D')


class DataExporter:
    """
    Handles exporting analytics data to CSV, Excel, and PDF formats.
    """

    def __init__(self, analytics, health_data: dict,
                 contributor_graph=None, output_dir: str = 'reports'):
        """
        Args:
            analytics:         RepositoryAnalytics instance.
            health_data:       Output of analytics.compute_health_score().
            contributor_graph: ContributorGraph instance (optional, for graph metrics).
            output_dir:        Directory to write reports into.
        """
        self.analytics          = analytics
        self.health_data        = health_data
        self.contributor_graph  = contributor_graph
        self.output_dir         = output_dir
        os.makedirs(output_dir, exist_ok=True)

    # ------------------------------------------------------------------ #
    #  CSV                                                                 #
    # ------------------------------------------------------------------ #

    def export_csv(self) -> list[str]:
        """
        Export all analytics DataFrames to separate CSV files.

        Returns:
            List of file paths written.
        """
        repo_name = self._safe_name()
        paths = []

        exports = {
            'contributors': self.analytics.contributor_df,
            'daily_commits': self.analytics.daily_commits(),
            'weekly_commits': self.analytics.weekly_commits(),
            'monthly_commits': self.analytics.monthly_commits(),
            'languages': self.analytics.language_df,
        }

        for name, df in exports.items():
            if df is None or df.empty:
                continue
            path = os.path.join(self.output_dir, f'{repo_name}_{name}.csv')
            df.to_csv(path, index=False)
            paths.append(path)

        return paths

    # ------------------------------------------------------------------ #
    #  Excel                                                               #
    # ------------------------------------------------------------------ #

    def export_excel(self) -> str:
        """
        Export all analytics data to a single multi-sheet Excel workbook.

        Returns:
            Path to the written .xlsx file.
        """
        repo_name = self._safe_name()
        path = os.path.join(self.output_dir, f'{repo_name}_analytics.xlsx')

        with pd.ExcelWriter(path, engine='openpyxl') as writer:

            # Repository Info sheet
            info_df = pd.DataFrame([{
                'Field': k, 'Value': v
            } for k, v in self.analytics.repo_info.items()
                if not isinstance(v, list)])
            info_df.to_excel(writer, sheet_name='Repository Info', index=False)

            # Contributors
            if self.analytics.contributor_df is not None and not self.analytics.contributor_df.empty:
                self.analytics.contributor_df.to_excel(
                    writer, sheet_name='Contributors', index=True
                )

            # Commit activity sheets
            for label, df_fn in [
                ('Daily Commits',   self.analytics.daily_commits),
                ('Weekly Commits',  self.analytics.weekly_commits),
                ('Monthly Commits', self.analytics.monthly_commits),
            ]:
                df = df_fn()
                if not df.empty:
                    df.to_excel(writer, sheet_name=label, index=False)

            # Languages
            if self.analytics.language_df is not None and not self.analytics.language_df.empty:
                self.analytics.language_df.to_excel(
                    writer, sheet_name='Languages', index=False
                )

            # Health Score
            breakdown = self.health_data.get('breakdown', {})
            health_df = pd.DataFrame([
                {'Dimension': k, 'Score': v, 'Max': self.health_data['max_scores'].get(k, 25)}
                for k, v in breakdown.items()
            ])
            health_df.loc[len(health_df)] = {
                'Dimension': 'TOTAL', 'Score': self.health_data['total'], 'Max': 100
            }
            health_df.to_excel(writer, sheet_name='Health Score', index=False)

            # Network Centrality
            if self.contributor_graph:
                centrality_rows = self.contributor_graph.centrality_table()
                if centrality_rows:
                    pd.DataFrame(centrality_rows).to_excel(
                        writer, sheet_name='Network Centrality', index=False
                    )

        return path

    # ------------------------------------------------------------------ #
    #  PDF                                                                 #
    # ------------------------------------------------------------------ #

    def export_pdf(self) -> str:
        """
        Generate a comprehensive PDF analytics report.

        Returns:
            Path to the written PDF file.
        """
        repo_name = self._safe_name()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        path = os.path.join(self.output_dir, f'{repo_name}_report_{timestamp}.pdf')

        doc = SimpleDocTemplate(
            path,
            pagesize=A4,
            rightMargin=1.5 * cm, leftMargin=1.5 * cm,
            topMargin=1.5 * cm, bottomMargin=1.5 * cm,
        )

        styles = getSampleStyleSheet()
        story  = []

        # ── Cover Header ──
        title_style = ParagraphStyle(
            'Title', parent=styles['Title'],
            textColor=colors.HexColor('#58A6FF'),
            fontSize=22, spaceAfter=6, alignment=TA_CENTER,
        )
        sub_style = ParagraphStyle(
            'Sub', parent=styles['Normal'],
            textColor=colors.HexColor('#8B949E'),
            fontSize=10, spaceAfter=4, alignment=TA_CENTER,
        )
        body_style = ParagraphStyle(
            'Body', parent=styles['Normal'],
            textColor=colors.black,
            fontSize=9, spaceAfter=3,
        )
        h2_style = ParagraphStyle(
            'H2', parent=styles['Heading2'],
            textColor=colors.HexColor('#0D3B8C'),
            fontSize=13, spaceBefore=14, spaceAfter=4,
        )

        info = self.analytics.repo_info
        story.append(Paragraph('GitHub Repository Analytics Report', title_style))
        story.append(Paragraph(
            f"Repository: <b>{info.get('full_name', 'Unknown')}</b>", sub_style
        ))
        story.append(Paragraph(
            f"Generated: {datetime.now().strftime('%B %d, %Y at %H:%M UTC')}", sub_style
        ))
        story.append(HRFlowable(width='100%', thickness=1,
                                color=colors.HexColor('#58A6FF'), spaceAfter=12))

        # ── Repository Overview ──
        story.append(Paragraph('Repository Overview', h2_style))
        overview_data = [
            ['Metric', 'Value'],
            ['Name',          info.get('name', 'N/A')],
            ['Owner',         info.get('owner', 'N/A')],
            ['Stars ⭐',      f"{info.get('stars', 0):,}"],
            ['Forks 🍴',      f"{info.get('forks', 0):,}"],
            ['Open Issues',   f"{info.get('open_issues', 0):,}"],
            ['Watchers',      f"{info.get('watchers', 0):,}"],
            ['Language',      info.get('main_language', 'N/A')],
            ['License',       info.get('license', 'N/A')],
            ['Default Branch',info.get('default_branch', 'main')],
        ]
        story.append(self._table(overview_data))
        story.append(Spacer(1, 0.3 * cm))

        # ── Health Score ──
        story.append(Paragraph('Repository Health Score', h2_style))
        score = self.health_data.get('total', 0)
        grade = self.health_data.get('grade', '?')
        score_color = '#3FB950' if score >= 75 else ('#FFA657' if score >= 50 else '#F78166')
        story.append(Paragraph(
            f'Overall Score: <font color="{score_color}"><b>{score}/100 (Grade {grade})</b></font>',
            body_style
        ))
        breakdown = self.health_data.get('breakdown', {})
        max_scores = self.health_data.get('max_scores', {})
        health_data_rows = [['Dimension', 'Score', 'Max']] + [
            [k, str(v), str(max_scores.get(k, 25))]
            for k, v in breakdown.items()
        ]
        story.append(self._table(health_data_rows))
        story.append(Spacer(1, 0.3 * cm))

        # ── Top Contributors ──
        story.append(Paragraph('Top Contributors', h2_style))
        if self.analytics.contributor_df is not None and not self.analytics.contributor_df.empty:
            top = self.analytics.contributor_df.head(10)
            contrib_rows = [['Rank', 'Contributor', 'Commits', 'Contribution %']]
            for rank, row in enumerate(top.itertuples(), 1):
                contrib_rows.append([
                    str(rank),
                    str(row.login),
                    f"{row.contributions:,}",
                    f"{row.percentage:.1f}%",
                ])
            story.append(self._table(contrib_rows))
        else:
            story.append(Paragraph('No contributor data available.', body_style))
        story.append(Spacer(1, 0.3 * cm))

        # ── Language Breakdown ──
        story.append(Paragraph('Language Breakdown', h2_style))
        if self.analytics.language_df is not None and not self.analytics.language_df.empty:
            lang_rows = [['Language', 'Percentage', 'Size (KB)']]
            for _, row in self.analytics.language_df.iterrows():
                lang_rows.append([
                    row['Language'],
                    f"{row['Percentage']:.1f}%",
                    f"{row['KB']:,.1f}",
                ])
            story.append(self._table(lang_rows))
        else:
            story.append(Paragraph('No language data available.', body_style))
        story.append(Spacer(1, 0.3 * cm))

        # ── Commit Trend ──
        story.append(Paragraph('Commit Trend Analysis', h2_style))
        trend = self.analytics.commit_trend()
        trend_rows = [['Metric', 'Value']] + [
            [k, str(v)] for k, v in trend.items()
        ]
        story.append(self._table(trend_rows))

        # ── Network Centrality ──
        if self.contributor_graph:
            story.append(Paragraph('Network Centrality (Top 10 Nodes)', h2_style))
            c_rows = self.contributor_graph.centrality_table()[:10]
            if c_rows:
                headers = list(c_rows[0].keys())
                table_data = [headers] + [[str(row[h]) for h in headers] for row in c_rows]
                story.append(self._table(table_data))

        doc.build(story)
        return path

    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #

    def _table(self, data: list) -> Table:
        """Build a styled ReportLab Table from a 2D list."""
        t = Table(data, repeatRows=1)
        style = TableStyle([
            ('BACKGROUND',  (0, 0), (-1, 0), colors.HexColor('#0D3B8C')),
            ('TEXTCOLOR',   (0, 0), (-1, 0), colors.white),
            ('FONTNAME',    (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE',    (0, 0), (-1, 0), 9),
            ('ALIGN',       (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME',    (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE',    (0, 1), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1),
             [colors.HexColor('#F5F7FA'), colors.white]),
            ('GRID',        (0, 0), (-1, -1), 0.4, colors.HexColor('#CCCCCC')),
            ('LEFTPADDING',  (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING',   (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING',(0, 0), (-1, -1), 3),
        ])
        t.setStyle(style)
        return t

    def _safe_name(self) -> str:
        """Return a filesystem-safe version of the repository name."""
        name = self.analytics.repo_info.get('full_name', 'repo')
        return name.replace('/', '_').replace(' ', '_')[:40]
