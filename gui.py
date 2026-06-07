"""
gui.py
------
Main Tkinter GUI application for the GitHub Repository Analyzer.

Layout:
  ┌─────────────────────────────────────────────────────┐
  │  Header (logo + title)                              │
  ├──────────────┬──────────────────────────────────────┤
  │  Sidebar     │  Main content (scrollable notebook)  │
  │  - Search    │    Overview | Commits | Languages |   │
  │  - Stats     │    Contributors | Network | Health   │
  │  - Rate Lmt  │                                      │
  │  - Export    │                                      │
  └──────────────┴──────────────────────────────────────┘
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import threading
import os
import shutil
from typing import Optional

# Local modules
from github_api import GitHubAnalyzer, GitHubAPIError, RateLimitError, RepoNotFoundError
from analytics import RepositoryAnalytics
from graph_analysis import ContributorGraph
import visualization as viz
from export import DataExporter

# ─── Colour tokens (match visualization.py) ─────────────────────────────────── #
C = {
    'bg':         '#0D1117',
    'surface':    '#161B22',
    'surface2':   '#1C2128',
    'border':     '#30363D',
    'accent':     '#58A6FF',
    'accent2':    '#3FB950',
    'accent3':    '#F78166',
    'accent4':    '#D2A8FF',
    'accent5':    '#FFA657',
    'text':       '#E6EDF3',
    'text_muted': '#8B949E',
    'btn':        '#21262D',
    'btn_hover':  '#30363D',
}

FONT_MONO = ('JetBrains Mono', 9) if 'JetBrains Mono' in tk.font.families(tk.Tk()) \
    else ('Consolas', 9) if 'Consolas' in tk.font.families() \
    else ('Courier', 9)

FONT_SANS  = ('Segoe UI', 9)
FONT_TITLE = ('Segoe UI', 13, 'bold')
FONT_CARD  = ('Segoe UI', 20, 'bold')
FONT_LABEL = ('Segoe UI', 8)


class AnimatedButton(tk.Button):
    """A Tkinter button with hover colour animation."""

    def __init__(self, master, **kwargs):
        normal_bg  = kwargs.pop('normal_bg',  C['btn'])
        hover_bg   = kwargs.pop('hover_bg',   C['accent'])
        normal_fg  = kwargs.pop('normal_fg',  C['text'])
        hover_fg   = kwargs.pop('hover_fg',   C['bg'])
        super().__init__(
            master,
            bg=normal_bg, fg=normal_fg,
            activebackground=hover_bg, activeforeground=hover_fg,
            relief='flat', bd=0, cursor='hand2',
            **kwargs
        )
        self._normal_bg = normal_bg
        self._hover_bg  = hover_bg
        self._normal_fg = normal_fg
        self._hover_fg  = hover_fg
        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)

    def _on_enter(self, _):
        self.config(bg=self._hover_bg, fg=self._hover_fg)

    def _on_leave(self, _):
        self.config(bg=self._normal_bg, fg=self._normal_fg)


class StatCard(tk.Frame):
    """Compact analytics card showing a label and a big numeric value."""

    def __init__(self, master, label: str, value: str = '—',
                 accent: str = C['accent'], **kwargs):
        super().__init__(master, bg=C['surface'], bd=0,
                         highlightbackground=C['border'],
                         highlightthickness=1, **kwargs)
        tk.Label(self, text=label, bg=C['surface'],
                 fg=C['text_muted'], font=FONT_LABEL).pack(pady=(8, 0))
        self._val_label = tk.Label(
            self, text=value, bg=C['surface'],
            fg=accent, font=FONT_CARD
        )
        self._val_label.pack(pady=(0, 8))

    def update_value(self, value: str):
        self._val_label.config(text=value)


class GitHubAnalyzerApp:
    """
    Main application class — owns the Tkinter root window and all widgets.
    """

    def __init__(self, root: tk.Tk):
        self.root = root
        self._configure_root()

        # State
        self.github_client    : Optional[GitHubAnalyzer]    = None
        self.analytics        : Optional[RepositoryAnalytics] = None
        self.contributor_graph: Optional[ContributorGraph]   = None
        self.health_data      : dict = {}
        self.repo_info        : dict = {}
        self._chart_canvases  : list = []
        self._token           : str  = ''

        self._build_ui()

    # ------------------------------------------------------------------ #
    #  Root configuration                                                  #
    # ------------------------------------------------------------------ #

    def _configure_root(self):
        self.root.title('GitHub Repository Analyzer')
        self.root.geometry('1400x860')
        self.root.minsize(1100, 700)
        self.root.configure(bg=C['bg'])
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=1)

        # ttk theme overrides for dark look
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TNotebook',
                         background=C['bg'], borderwidth=0)
        style.configure('TNotebook.Tab',
                         background=C['surface'], foreground=C['text_muted'],
                         padding=[14, 6], font=FONT_SANS)
        style.map('TNotebook.Tab',
                  background=[('selected', C['surface2'])],
                  foreground=[('selected', C['accent'])])
        style.configure('TScrollbar',
                         background=C['surface'], troughcolor=C['bg'],
                         arrowcolor=C['text_muted'], borderwidth=0)
        style.configure('Treeview',
                         background=C['surface'], foreground=C['text'],
                         fieldbackground=C['surface'], rowheight=26,
                         font=FONT_SANS)
        style.configure('Treeview.Heading',
                         background=C['surface2'], foreground=C['accent'],
                         font=('Segoe UI', 9, 'bold'))
        style.map('Treeview', background=[('selected', C['accent'])])
        style.configure('TSeparator', background=C['border'])

    # ------------------------------------------------------------------ #
    #  UI Build                                                            #
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        self._build_header()
        body = tk.Frame(self.root, bg=C['bg'])
        body.grid(row=1, column=0, sticky='nsew', padx=0, pady=0)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)
        self._build_sidebar(body)
        self._build_main(body)
        self._build_status_bar()

    def _build_header(self):
        header = tk.Frame(self.root, bg=C['surface'],
                          highlightbackground=C['border'], highlightthickness=1)
        header.grid(row=0, column=0, sticky='ew')
        tk.Label(
            header,
            text='⚡ GitHub Repository Analyzer',
            bg=C['surface'], fg=C['accent'],
            font=('Segoe UI', 16, 'bold')
        ).pack(side='left', padx=20, pady=12)
        tk.Label(
            header,
            text='Deep analytics & network visualisation for any public repository',
            bg=C['surface'], fg=C['text_muted'],
            font=FONT_SANS
        ).pack(side='left', padx=0, pady=12)

        # Token entry (right side of header)
        tk.Label(header, text='API Token (optional):',
                 bg=C['surface'], fg=C['text_muted'], font=FONT_LABEL).pack(
            side='right', padx=(0, 4), pady=12)
        self._token_var = tk.StringVar()
        token_entry = tk.Entry(
            header, textvariable=self._token_var, show='*',
            bg=C['btn'], fg=C['text'], insertbackground=C['text'],
            relief='flat', font=FONT_MONO, width=22
        )
        token_entry.pack(side='right', padx=(0, 8), pady=12)

    def _build_sidebar(self, parent):
        sidebar = tk.Frame(parent, bg=C['surface'], width=260,
                           highlightbackground=C['border'], highlightthickness=1)
        sidebar.grid(row=0, column=0, sticky='ns')
        sidebar.grid_propagate(False)

        # ── Search Section ──
        search_frame = tk.LabelFrame(
            sidebar, text=' Repository URL ',
            bg=C['surface'], fg=C['accent'],
            font=('Segoe UI', 9, 'bold'),
            bd=1, relief='groove',
            highlightbackground=C['border']
        )
        search_frame.pack(fill='x', padx=12, pady=(16, 8))

        self._url_var = tk.StringVar()
        self._url_entry = tk.Entry(
            search_frame, textvariable=self._url_var,
            bg=C['btn'], fg=C['text'], insertbackground=C['text'],
            relief='flat', font=FONT_MONO, width=26
        )
        self._url_entry.pack(padx=8, pady=(8, 4), fill='x')
        self._url_entry.insert(0, 'e.g. https://github.com/owner/repo')
        self._url_entry.bind('<FocusIn>',  self._clear_placeholder)
        self._url_entry.bind('<FocusOut>', self._set_placeholder)
        self._url_entry.bind('<Return>', lambda _: self._start_analysis())

        self._analyze_btn = AnimatedButton(
            search_frame, text='🔍  Analyze Repository',
            command=self._start_analysis,
            font=('Segoe UI', 10, 'bold'),
            normal_bg=C['accent'], normal_fg=C['bg'],
            hover_bg='#79C0FF', hover_fg=C['bg'],
            padx=10, pady=8
        )
        self._analyze_btn.pack(fill='x', padx=8, pady=(4, 10))

        # ── Stats Cards ──
        self._cards: dict[str, StatCard] = {}
        card_defs = [
            ('Stars ⭐',    '—', C['accent5']),
            ('Forks 🍴',    '—', C['accent2']),
            ('Issues 🐛',   '—', C['accent3']),
            ('Watchers 👁', '—', C['accent4']),
        ]
        cards_frame = tk.Frame(sidebar, bg=C['surface'])
        cards_frame.pack(fill='x', padx=12, pady=4)
        for i, (label, val, color) in enumerate(card_defs):
            row, col = divmod(i, 2)
            card = StatCard(cards_frame, label, val, accent=color)
            card.grid(row=row, column=col, padx=4, pady=4, sticky='ew')
            cards_frame.grid_columnconfigure(col, weight=1)
            self._cards[label] = card

        # ── Health Score Card ──
        self._health_card = StatCard(
            sidebar, 'Health Score 💯', '—/100', accent=C['accent2']
        )
        self._health_card.pack(fill='x', padx=12, pady=4)

        # ── Info Labels ──
        self._info_frame = tk.Frame(sidebar, bg=C['surface'])
        self._info_frame.pack(fill='x', padx=12, pady=4)
        self._info_vars: dict[str, tk.StringVar] = {}
        for label in ['Owner', 'Language', 'License', 'Contributors']:
            row = tk.Frame(self._info_frame, bg=C['surface'])
            row.pack(fill='x', pady=1)
            tk.Label(row, text=f'{label}:', bg=C['surface'],
                     fg=C['text_muted'], font=FONT_LABEL, width=12, anchor='w'
                     ).pack(side='left')
            var = tk.StringVar(value='—')
            tk.Label(row, textvariable=var, bg=C['surface'],
                     fg=C['text'], font=FONT_LABEL, anchor='w'
                     ).pack(side='left')
            self._info_vars[label] = var

        # ── Rate Limit ──
        rate_frame = tk.LabelFrame(
            sidebar, text=' API Rate Limit ',
            bg=C['surface'], fg=C['text_muted'],
            font=FONT_LABEL, bd=1, relief='groove'
        )
        rate_frame.pack(fill='x', padx=12, pady=8)
        self._rate_var = tk.StringVar(value='Remaining: —')
        tk.Label(rate_frame, textvariable=self._rate_var,
                 bg=C['surface'], fg=C['text_muted'], font=FONT_LABEL
                 ).pack(padx=8, pady=4)

        # ── Export Buttons ──
        export_frame = tk.LabelFrame(
            sidebar, text=' Export Data ',
            bg=C['surface'], fg=C['text_muted'],
            font=FONT_LABEL, bd=1, relief='groove'
        )
        export_frame.pack(fill='x', padx=12, pady=4)

        for label, cmd in [
            ('📊 Export CSV',   self._export_csv),
            ('📗 Export Excel', self._export_excel),
            ('📄 Export PDF',   self._export_pdf),
        ]:
            AnimatedButton(
                export_frame, text=label, command=cmd,
                font=FONT_SANS, padx=8, pady=6
            ).pack(fill='x', padx=8, pady=3)

        # Bottom spacer
        tk.Frame(sidebar, bg=C['surface']).pack(fill='both', expand=True)

    def _build_main(self, parent):
        self._notebook = ttk.Notebook(parent)
        self._notebook.grid(row=0, column=1, sticky='nsew', padx=0, pady=0)

        self._tabs = {}
        tab_defs = [
            ('📋 Overview',      self._build_overview_tab),
            ('📈 Commits',       self._build_commits_tab),
            ('🌐 Languages',     self._build_languages_tab),
            ('👥 Contributors',  self._build_contributors_tab),
            ('🕸️ Network',       self._build_network_tab),
            ('🏥 Health Score',  self._build_health_tab),
            ('🔬 Centrality',    self._build_centrality_tab),
        ]
        for name, builder in tab_defs:
            frame = tk.Frame(self._notebook, bg=C['bg'])
            self._notebook.add(frame, text=name)
            self._tabs[name] = frame
            builder(frame)

    def _build_status_bar(self):
        self._status_var = tk.StringVar(value='Ready  •  Enter a GitHub repository URL and click Analyze')
        bar = tk.Label(
            self.root, textvariable=self._status_var,
            bg=C['surface'], fg=C['text_muted'],
            font=FONT_LABEL, anchor='w', padx=12, pady=4,
            highlightbackground=C['border'], highlightthickness=1
        )
        bar.grid(row=2, column=0, sticky='ew')

    # ------------------------------------------------------------------ #
    #  Tab Builders                                                        #
    # ------------------------------------------------------------------ #

    def _scrollable(self, parent) -> tuple[tk.Frame, tk.Canvas]:
        """Wrap a frame in a scrollable canvas."""
        canvas = tk.Canvas(parent, bg=C['bg'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient='vertical', command=canvas.yview)
        inner = tk.Frame(canvas, bg=C['bg'])
        inner.bind('<Configure>', lambda e: canvas.configure(
            scrollregion=canvas.bbox('all')
        ))
        canvas.create_window((0, 0), window=inner, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')

        canvas.bind_all('<MouseWheel>', _on_mousewheel)
        return inner, canvas

    def _build_overview_tab(self, parent):
        inner, _ = self._scrollable(parent)
        self._overview_inner = inner
        self._overview_placeholder(inner)

    def _overview_placeholder(self, parent):
        tk.Label(
            parent,
            text='🚀\n\nEnter a repository URL in the sidebar and click Analyze.',
            bg=C['bg'], fg=C['text_muted'], font=('Segoe UI', 13),
            justify='center'
        ).pack(expand=True, pady=80)

    def _build_commits_tab(self, parent):
        self._commits_inner, _ = self._scrollable(parent)

    def _build_languages_tab(self, parent):
        self._languages_inner, _ = self._scrollable(parent)

    def _build_contributors_tab(self, parent):
        self._contributors_inner, _ = self._scrollable(parent)

    def _build_network_tab(self, parent):
        # Layout selector
        ctrl = tk.Frame(parent, bg=C['surface'],
                        highlightbackground=C['border'], highlightthickness=1)
        ctrl.pack(fill='x', padx=0, pady=0)

        tk.Label(ctrl, text='Layout:', bg=C['surface'],
                 fg=C['text_muted'], font=FONT_LABEL).pack(side='left', padx=12, pady=8)
        self._layout_var = tk.StringVar(value='spring')
        for val, lbl in [('spring', 'Spring'), ('circular', 'Circular'),
                         ('shell', 'Shell'), ('kamada_kawai', 'Kamada-Kawai')]:
            tk.Radiobutton(
                ctrl, text=lbl, value=val, variable=self._layout_var,
                bg=C['surface'], fg=C['text'], selectcolor=C['bg'],
                activebackground=C['surface'], command=self._redraw_network,
                font=FONT_LABEL
            ).pack(side='left', padx=6)

        self._network_inner = tk.Frame(parent, bg=C['bg'])
        self._network_inner.pack(fill='both', expand=True)

    def _build_health_tab(self, parent):
        self._health_inner, _ = self._scrollable(parent)

    def _build_centrality_tab(self, parent):
        self._centrality_inner = tk.Frame(parent, bg=C['bg'])
        self._centrality_inner.pack(fill='both', expand=True, padx=8, pady=8)

    # ------------------------------------------------------------------ #
    #  Analysis Orchestration                                              #
    # ------------------------------------------------------------------ #

    def _start_analysis(self):
        url = self._url_var.get().strip()
        if not url or url.startswith('e.g.'):
            messagebox.showwarning('Input Required', 'Please enter a GitHub repository URL.')
            return

        self._set_status('🔄  Connecting to GitHub API…')
        self._analyze_btn.config(state='disabled', text='Analyzing…')
        token = self._token_var.get().strip() or None

        thread = threading.Thread(
            target=self._run_analysis, args=(url, token), daemon=True
        )
        thread.start()

    def _run_analysis(self, url: str, token: Optional[str]):
        """Background worker — runs API calls off the main thread."""
        try:
            self._set_status('📡  Fetching repository metadata…')
            client = GitHubAnalyzer(token)
            repo_info = client.load_repository(url)
            self.github_client = client

            self._set_status('👥  Fetching contributors…')
            contributors = client.get_contributors(max_contributors=30)

            self._set_status('📝  Fetching commit history (last 365 days)…')
            commits = client.get_commit_activity(days=365)

            self._set_status('🌐  Fetching language data…')
            languages = client.get_languages()

            self._set_status('⚙️  Computing analytics…')
            analytics = RepositoryAnalytics()
            analytics.load_data(repo_info, commits, contributors, languages)

            self._set_status('🕸️  Building contributor graph…')
            graph = ContributorGraph()
            graph.build_graph(repo_info, contributors)

            health = analytics.compute_health_score()
            rate   = client.check_rate_limit()

            # Schedule UI update on main thread
            self.root.after(0, self._update_ui,
                            repo_info, analytics, graph, health, rate)

        except (RateLimitError, RepoNotFoundError, GitHubAPIError) as e:
            self.root.after(0, self._show_error, str(e))
        except Exception as e:
            self.root.after(0, self._show_error, f'Unexpected error: {e}')

    def _update_ui(self, repo_info, analytics, graph, health, rate):
        """Main-thread UI refresh after successful analysis."""
        self.repo_info         = repo_info
        self.analytics         = analytics
        self.contributor_graph = graph
        self.health_data       = health

        self._clear_charts()
        self._populate_sidebar(repo_info, analytics, health, rate)
        self._populate_overview(repo_info, analytics, health)
        self._populate_commits_tab()
        self._populate_languages_tab()
        self._populate_contributors_tab()
        self._populate_network_tab()
        self._populate_health_tab()
        self._populate_centrality_tab()

        repo_name = repo_info.get('full_name', repo_info.get('name', ''))
        self._set_status(f'✅  Analysis complete: {repo_name}  •  '
                         f"{rate.get('remaining', '?')} API requests remaining")
        self._analyze_btn.config(state='normal', text='🔍  Analyze Repository')

    # ------------------------------------------------------------------ #
    #  Sidebar population                                                  #
    # ------------------------------------------------------------------ #

    def _populate_sidebar(self, info, analytics, health, rate):
        self._cards['Stars ⭐'].update_value(f"{info.get('stars', 0):,}")
        self._cards['Forks 🍴'].update_value(f"{info.get('forks', 0):,}")
        self._cards['Issues 🐛'].update_value(f"{info.get('open_issues', 0):,}")
        self._cards['Watchers 👁'].update_value(f"{info.get('watchers', 0):,}")
        self._health_card.update_value(f"{health.get('total', 0):.0f}/100")

        n_contrib = len(analytics.contributor_df) if analytics.contributor_df is not None else 0
        self._info_vars['Owner'].set(info.get('owner', '—'))
        self._info_vars['Language'].set(info.get('main_language', '—'))
        self._info_vars['License'].set(info.get('license', '—'))
        self._info_vars['Contributors'].set(str(n_contrib))

        remaining = rate.get('remaining', '?')
        limit     = rate.get('limit', 60)
        self._rate_var.set(f'Remaining: {remaining}/{limit}')

    # ------------------------------------------------------------------ #
    #  Tab population                                                      #
    # ------------------------------------------------------------------ #

    def _populate_overview(self, info, analytics, health):
        for widget in self._overview_inner.winfo_children():
            widget.destroy()

        # Title
        tk.Label(self._overview_inner,
                 text=f"📦  {info.get('full_name', '')}",
                 bg=C['bg'], fg=C['accent'], font=FONT_TITLE
                 ).pack(anchor='w', padx=24, pady=(16, 2))
        desc = info.get('description', 'No description.')
        tk.Label(self._overview_inner, text=desc,
                 bg=C['bg'], fg=C['text_muted'], font=FONT_SANS,
                 wraplength=820, justify='left'
                 ).pack(anchor='w', padx=24, pady=(0, 8))

        # Topics
        topics = info.get('topics', [])
        if topics:
            t_frame = tk.Frame(self._overview_inner, bg=C['bg'])
            t_frame.pack(anchor='w', padx=24, pady=4)
            for topic in topics[:12]:
                tk.Label(
                    t_frame, text=f'  {topic}  ',
                    bg=C['surface'], fg=C['accent4'],
                    font=FONT_LABEL, relief='flat',
                    padx=4, pady=2
                ).pack(side='left', padx=3)

        sep = ttk.Separator(self._overview_inner, orient='horizontal')
        sep.pack(fill='x', padx=24, pady=8)

        # Stats grid
        stats = [
            ('⭐ Stars',          f"{info.get('stars', 0):,}",      C['accent5']),
            ('🍴 Forks',          f"{info.get('forks', 0):,}",      C['accent2']),
            ('🐛 Open Issues',    f"{info.get('open_issues', 0):,}", C['accent3']),
            ('👁 Watchers',       f"{info.get('watchers', 0):,}",   C['accent4']),
            ('💬 Language',       info.get('main_language', '—'),    C['accent']),
            ('📄 License',        info.get('license', '—'),          C['text']),
            ('🌿 Branch',         info.get('default_branch', '—'),   C['text']),
            ('📦 Size',           f"{info.get('size_kb', 0):,} KB",  C['text_muted']),
        ]
        grid = tk.Frame(self._overview_inner, bg=C['bg'])
        grid.pack(fill='x', padx=20, pady=4)
        for i, (lbl, val, col) in enumerate(stats):
            r, c = divmod(i, 4)
            card = tk.Frame(grid, bg=C['surface'],
                            highlightbackground=C['border'], highlightthickness=1)
            card.grid(row=r, column=c, padx=6, pady=6, sticky='ew')
            grid.grid_columnconfigure(c, weight=1)
            tk.Label(card, text=lbl, bg=C['surface'],
                     fg=C['text_muted'], font=FONT_LABEL).pack(pady=(8, 0))
            tk.Label(card, text=val, bg=C['surface'],
                     fg=col, font=('Segoe UI', 14, 'bold')).pack(pady=(0, 8))

        # Commit trend summary
        sep2 = ttk.Separator(self._overview_inner, orient='horizontal')
        sep2.pack(fill='x', padx=24, pady=8)
        trend = analytics.commit_trend()
        trend_text = (
            f"Commit Trend (last 365 days):  "
            f"Direction → {trend.get('direction', '?').upper()}  |  "
            f"Change → {trend.get('pct_change', 0):+.1f}%  |  "
            f"Avg weekly → {trend.get('avg_weekly', 0)} commits  |  "
            f"Peak week → {trend.get('max_weekly', 0)} commits"
        )
        tk.Label(self._overview_inner, text=trend_text,
                 bg=C['bg'], fg=C['text_muted'], font=FONT_LABEL
                 ).pack(anchor='w', padx=24, pady=4)

        # Health badge
        score = health.get('total', 0)
        grade = health.get('grade', '?')
        h_color = C['accent2'] if score >= 75 else (C['accent5'] if score >= 50 else C['accent3'])
        tk.Label(self._overview_inner,
                 text=f'Health Score: {score:.0f}/100  (Grade {grade})',
                 bg=C['bg'], fg=h_color, font=('Segoe UI', 11, 'bold')
                 ).pack(anchor='w', padx=24, pady=(4, 16))

    def _populate_commits_tab(self):
        for w in self._commits_inner.winfo_children():
            w.destroy()
        canvas_widget = viz.plot_commit_activity(self.analytics, self._commits_inner)
        canvas_widget.get_tk_widget().pack(fill='both', expand=True, padx=8, pady=8)
        self._chart_canvases.append(canvas_widget)

    def _populate_languages_tab(self):
        for w in self._languages_inner.winfo_children():
            w.destroy()
        canvas_widget = viz.plot_languages(self.analytics, self._languages_inner)
        canvas_widget.get_tk_widget().pack(fill='both', expand=True, padx=8, pady=8)
        self._chart_canvases.append(canvas_widget)

        # Language table
        if self.analytics.language_df is not None and not self.analytics.language_df.empty:
            tk.Label(self._languages_inner, text='Language Breakdown Table',
                     bg=C['bg'], fg=C['accent'], font=FONT_TITLE
                     ).pack(anchor='w', padx=12, pady=(8, 4))
            self._make_treeview(
                self._languages_inner,
                columns=['Language', 'Percentage', 'KB'],
                rows=[
                    (row['Language'], f"{row['Percentage']:.1f}%", f"{row['KB']:,.1f}")
                    for _, row in self.analytics.language_df.iterrows()
                ]
            )

    def _populate_contributors_tab(self):
        for w in self._contributors_inner.winfo_children():
            w.destroy()
        canvas_widget = viz.plot_contributors(self.analytics, self._contributors_inner)
        canvas_widget.get_tk_widget().pack(fill='both', expand=True, padx=8, pady=8)
        self._chart_canvases.append(canvas_widget)

        if self.analytics.contributor_df is not None and not self.analytics.contributor_df.empty:
            tk.Label(self._contributors_inner, text='Top Contributors Table',
                     bg=C['bg'], fg=C['accent'], font=FONT_TITLE
                     ).pack(anchor='w', padx=12, pady=(8, 4))
            df = self.analytics.contributor_df.head(20)
            self._make_treeview(
                self._contributors_inner,
                columns=['Rank', 'Contributor', 'Commits', 'Percentage'],
                rows=[
                    (i + 1, row['login'], f"{row['contributions']:,}", f"{row['percentage']:.1f}%")
                    for i, (_, row) in enumerate(df.iterrows())
                ]
            )

    def _populate_network_tab(self):
        for w in self._network_inner.winfo_children():
            w.destroy()
        layout = self._layout_var.get()
        canvas_widget = viz.plot_network_graph(
            self.contributor_graph, self._network_inner, layout=layout
        )
        canvas_widget.get_tk_widget().pack(fill='both', expand=True, padx=8, pady=8)
        self._chart_canvases.append(canvas_widget)

    def _redraw_network(self):
        if self.contributor_graph:
            self.contributor_graph._positions = None  # Force layout recalc
            self._populate_network_tab()

    def _populate_health_tab(self):
        for w in self._health_inner.winfo_children():
            w.destroy()
        canvas_widget = viz.plot_health_gauge(self.health_data, self._health_inner)
        canvas_widget.get_tk_widget().pack(fill='both', expand=True, padx=8, pady=8)
        self._chart_canvases.append(canvas_widget)

    def _populate_centrality_tab(self):
        for w in self._centrality_inner.winfo_children():
            w.destroy()

        tk.Label(self._centrality_inner, text='Network Centrality Metrics',
                 bg=C['bg'], fg=C['accent'], font=FONT_TITLE
                 ).pack(anchor='w', padx=12, pady=(8, 4))
        tk.Label(
            self._centrality_inner,
            text=(
                'Degree Centrality: how many direct connections a node has.\n'
                'Betweenness Centrality: how often a node lies on shortest paths between others.\n'
                'Closeness Centrality: how close a node is to all others in the graph.'
            ),
            bg=C['bg'], fg=C['text_muted'], font=FONT_LABEL, justify='left'
        ).pack(anchor='w', padx=12, pady=(0, 8))

        rows = self.contributor_graph.centrality_table()
        self._make_treeview(
            self._centrality_inner,
            columns=['Node', 'Type', 'Degree Centrality', 'Betweenness Centrality', 'Closeness Centrality'],
            rows=[
                (r['Node'], r['Type'],
                 r['Degree Centrality'], r['Betweenness Centrality'], r['Closeness Centrality'])
                for r in rows
            ],
            col_widths=[180, 90, 130, 160, 140]
        )

        # Graph statistics
        stats = self.contributor_graph.graph_stats()
        sep = ttk.Separator(self._centrality_inner, orient='horizontal')
        sep.pack(fill='x', padx=12, pady=8)
        tk.Label(self._centrality_inner, text='Graph Statistics',
                 bg=C['bg'], fg=C['accent'], font=FONT_TITLE
                 ).pack(anchor='w', padx=12, pady=(0, 4))
        stats_grid = tk.Frame(self._centrality_inner, bg=C['bg'])
        stats_grid.pack(anchor='w', padx=12)
        for i, (k, v) in enumerate(stats.items()):
            tk.Label(stats_grid, text=f'{k}:',
                     bg=C['bg'], fg=C['text_muted'], font=FONT_LABEL, width=22, anchor='w'
                     ).grid(row=i, column=0, sticky='w', pady=1)
            tk.Label(stats_grid, text=str(v),
                     bg=C['bg'], fg=C['text'], font=FONT_LABEL, anchor='w'
                     ).grid(row=i, column=1, sticky='w', pady=1, padx=8)

    # ------------------------------------------------------------------ #
    #  Utility Widgets                                                     #
    # ------------------------------------------------------------------ #

    def _make_treeview(self, parent, columns, rows,
                       col_widths: Optional[list] = None) -> ttk.Treeview:
        frame = tk.Frame(parent, bg=C['bg'])
        frame.pack(fill='both', expand=True, padx=12, pady=(0, 12))

        vsb = ttk.Scrollbar(frame, orient='vertical')
        hsb = ttk.Scrollbar(frame, orient='horizontal')
        tree = ttk.Treeview(
            frame, columns=columns, show='headings',
            yscrollcommand=vsb.set, xscrollcommand=hsb.set,
            height=min(len(rows), 20)
        )
        vsb.config(command=tree.yview)
        hsb.config(command=tree.xview)
        vsb.pack(side='right', fill='y')
        hsb.pack(side='bottom', fill='x')
        tree.pack(fill='both', expand=True)

        for i, col in enumerate(columns):
            w = col_widths[i] if col_widths and i < len(col_widths) else 120
            tree.heading(col, text=col)
            tree.column(col, width=w, anchor='center')

        for row in rows:
            tree.insert('', 'end', values=row)

        return tree

    # ------------------------------------------------------------------ #
    #  Export                                                              #
    # ------------------------------------------------------------------ #

    def _require_data(self) -> bool:
        if not self.analytics:
            messagebox.showwarning('No Data', 'Please analyze a repository first.')
            return False
        return True

    def _export_csv(self):
        if not self._require_data():
            return
        exporter = DataExporter(
            self.analytics, self.health_data,
            self.contributor_graph, output_dir='reports'
        )
        paths = exporter.export_csv()
        messagebox.showinfo('CSV Export',
                            f'Exported {len(paths)} CSV files to reports/\n\n' +
                            '\n'.join(os.path.basename(p) for p in paths))

    def _export_excel(self):
        if not self._require_data():
            return
        exporter = DataExporter(
            self.analytics, self.health_data,
            self.contributor_graph, output_dir='reports'
        )
        path = exporter.export_excel()
        messagebox.showinfo('Excel Export', f'Saved Excel workbook:\n{path}')

    def _export_pdf(self):
        if not self._require_data():
            return
        exporter = DataExporter(
            self.analytics, self.health_data,
            self.contributor_graph, output_dir='reports'
        )
        path = exporter.export_pdf()
        messagebox.showinfo('PDF Report', f'PDF report saved:\n{path}')

    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #

    def _clear_charts(self):
        import matplotlib.pyplot as plt
        for canvas in self._chart_canvases:
            try:
                plt.close(canvas.figure)
            except Exception:
                pass
        self._chart_canvases.clear()

    def _set_status(self, msg: str):
        self._status_var.set(msg)
        self.root.update_idletasks()

    def _show_error(self, msg: str):
        self._set_status(f'❌  Error: {msg}')
        self._analyze_btn.config(state='normal', text='🔍  Analyze Repository')
        messagebox.showerror('Error', msg)

    def _clear_placeholder(self, event):
        if self._url_var.get().startswith('e.g.'):
            self._url_var.set('')

    def _set_placeholder(self, event):
        if not self._url_var.get().strip():
            self._url_var.set('e.g. https://github.com/owner/repo')


# ─── Needed for font family check ───────────────────────────────────────────── #
import tkinter.font as tk_font
