# ⚡ GitHub Repository Analyzer

A professional desktop analytics application that fetches, analyzes, and visualizes data for any public GitHub repository — all from a sleek dark-themed Tkinter GUI.

---

## ✨ Features

| Feature | Details |
|---|---|
| **Repository Metadata** | Stars, forks, watchers, open issues, license, topics, size |
| **Contributor Analysis** | Top contributors table, commit ranking, contribution % |
| **Commit Activity** | Daily / weekly / monthly charts, trend analysis, busiest days |
| **Language Breakdown** | Pie chart + horizontal bar chart with byte-level breakdown |
| **Network Graph** | NetworkX contributor → repository graph, 4 layout algorithms |
| **Centrality Metrics** | Degree, Betweenness, and Closeness centrality per node |
| **Health Score** | 0–100 score with A+→F grade and 5-dimension breakdown |
| **Data Export** | CSV (per dataset), multi-sheet Excel (.xlsx), PDF report |
| **Dark UI** | GitHub-inspired dark palette throughout |

---

## 🖥️ Requirements

- **Python 3.12+** (3.10+ will also work)
- **Tkinter** — usually bundled with Python; if missing:
  - Ubuntu/Debian: `sudo apt install python3-tk`
  - Fedora: `sudo dnf install python3-tkinter`
  - macOS: comes with the official Python installer from python.org
- Internet connection to reach the GitHub API

---

## 🚀 Installation

```bash
# 1. Clone or download the project
git clone <your-repo-url>
cd github_analyzer

# 2. (Recommended) Create a virtual environment
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

---

## ▶️ Running the Application

```bash
python main.py
```

### Optional: supply a GitHub token to raise the rate limit

Without a token the GitHub API allows **60 requests per hour**.  
With a Personal Access Token (PAT) you get **5 000 requests per hour**.

```bash
# Inline argument
python main.py ghp_xxxxxxxxxxxxxxxxxxxx

# Or paste it in the "API Token" box in the app header at runtime
```

Generate a token at **GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)**.  
The token needs no special scopes for public repositories.

---

## 🗂️ Project Structure

```
github_analyzer/
│
├── main.py           # Entry point — dependency check + launches GUI
├── github_api.py     # PyGithub wrapper (data fetching, validation, rate limit)
├── analytics.py      # Pandas/NumPy analytics engine + health score
├── graph_analysis.py # NetworkX contributor graph + centrality
├── visualization.py  # Matplotlib/Seaborn chart rendering
├── export.py         # CSV / Excel / PDF export
├── gui.py            # Tkinter dashboard application
├── requirements.txt  # Python dependencies
└── reports/          # Auto-created; exported files land here
```

---

## 📖 Usage Guide

1. **Launch** `python main.py`
2. **Enter URL** — paste any public GitHub repo URL (e.g. `https://github.com/django/django`) in the sidebar search box
3. *(Optional)* Paste your GitHub token in the **API Token** field in the header bar
4. Click **🔍 Analyze Repository** or press **Enter**
5. Watch the status bar for live progress — fetching typically takes 10–60 seconds depending on repository size and rate limit
6. Explore the six analytics tabs:
   - **📋 Overview** — stats cards, topics, trend summary
   - **📈 Commits** — four-panel commit activity charts
   - **🌐 Languages** — pie + bar chart with table
   - **👥 Contributors** — bar chart + ranked table
   - **🕸️ Network** — interactive graph (switch layouts with radio buttons)
   - **🏥 Health Score** — gauge + score breakdown
   - **🔬 Centrality** — node centrality table + graph statistics
7. **Export** using the sidebar buttons → files saved to `reports/`

---

## 📊 Health Score Methodology

| Dimension | Max Points | Calculation |
|---|---|---|
| Stars (Popularity) | 20 | log-scaled, saturates at 10 000 stars |
| Forks (Reusability) | 15 | log-scaled, saturates at 2 000 forks |
| Issue Responsiveness | 15 | penalizes high open-issues-to-forks ratio |
| Commit Activity | 25 | log-scaled commits in last 30 days, saturates at 100 |
| Contributor Community | 25 | log-scaled contributor count, saturates at 50 |

Grade mapping: **A+** ≥85 · **A** ≥75 · **B** ≥65 · **C** ≥50 · **D** ≥35 · **F** <35

---

## 🕸️ Network Graph Details

- **Nodes:** one repository node (orange) + one node per contributor (blue)
- **Edges:** directed contributor → repository, weight = commit count
- **Node size:** proportional to log(commits) for contributors; fixed large for repo
- **Edge width:** proportional to log(commit weight)
- **Layout algorithms:** Spring · Circular · Shell · Kamada-Kawai

---

## ⚠️ Known Limitations

| Limitation | Detail |
|---|---|
| Public repos only | Private repositories require appropriate token scopes |
| Commit sample | Fetches up to 1 000 recent commits to stay within rate limits |
| Contributor sample | Fetches up to 30 top contributors |
| Rate limits | Without a token, analysis of large repos may hit the 60 req/hr cap |
| Very large repos | May be slow due to pagination in the GitHub API |

---

## 🛠️ Tech Stack

| Library | Purpose |
|---|---|
| PyGithub | GitHub REST API client |
| Pandas | DataFrame analytics engine |
| NumPy | Numerical computations |
| Matplotlib + Seaborn | Chart rendering (embedded in Tkinter) |
| Plotly | (imported, available for future interactive charts) |
| NetworkX | Contributor graph + centrality |
| Tkinter | Desktop GUI framework |
| ReportLab | PDF report generation |
| openpyxl | Excel workbook export |

---

## 📝 License

MIT — free to use, modify, and distribute.
