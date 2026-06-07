# 🔍 GitHub Repository Analyzer

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)
![Tkinter](https://img.shields.io/badge/GUI-Tkinter-orange?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=for-the-badge)

**A powerful desktop analytics tool to fetch, analyze, and visualize any public GitHub repository — wrapped in a sleek dark-themed GUI.**

[Features](#-features) • [Installation](#-installation) • [Usage](#-usage) • [Project Structure](#-project-structure) • [Tech Stack](#-tech-stack)

</div>

---

## 📸 Overview

GitHub Repository Analyzer is a Python desktop application that lets you deep-dive into any public GitHub repository. From contributor stats to network graphs and health scores — all in one place, no browser needed.

---

## ✨ Features

| Feature | Details |
|---|---|
| 📦 **Repository Metadata** | Stars, forks, watchers, open issues, license, topics, size |
| 👥 **Contributor Analysis** | Top contributors table, commit ranking, contribution % |
| 📈 **Commit Activity** | Daily / weekly / monthly charts, trend analysis, busiest days |
| 🌐 **Language Breakdown** | Pie chart + bar chart with byte-level breakdown |
| 🕸️ **Network Graph** | NetworkX contributor → repository graph with 4 layout algorithms |
| 📐 **Centrality Metrics** | Degree, Betweenness, and Closeness centrality per node |
| 🏥 **Health Score** | 0–100 score with A+ → F grade and 5-dimension breakdown |
| 💾 **Data Export** | CSV, multi-sheet Excel (.xlsx), and PDF report |
| 🌑 **Dark UI** | GitHub-inspired dark palette throughout |

---

## 🖥️ Requirements

- **Python 3.10+**
- **Tkinter** (usually bundled with Python)
  - Ubuntu/Debian: `sudo apt install python3-tk`
  - Fedora: `sudo dnf install python3-tkinter`
  - macOS: comes with the official Python installer
- Internet connection to reach the GitHub API

---

## 🚀 Installation

```bash
# 1. Clone the repository
git clone https://github.com/mawiya-47/GitHub-Repository-Analyzer.git
cd GitHub-Repository-Analyzer

# 2. Create a virtual environment (recommended)
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt --only-binary=:all:
```

---

## ▶️ Usage

```bash
python main.py
```

### Optional: GitHub Personal Access Token

Without a token → **60 requests/hour** limit  
With a token → **5,000 requests/hour**

```bash
# Pass token as argument
python main.py ghp_xxxxxxxxxxxxxxxxxxxx

# Or paste it in the "API Token" box inside the app
```

> Generate a token at: **GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)**  
> No special scopes needed for public repositories.

### Step-by-step

1. Launch the app with `python main.py`
2. Paste any public GitHub repo URL (e.g. `https://github.com/django/django`)
3. *(Optional)* Enter your GitHub token
4. Click **🔍 Analyze Repository**
5. Explore the tabs:

| Tab | Contents |
|---|---|
| 📋 Overview | Stats cards, topics, trend summary |
| 📈 Commits | Four-panel commit activity charts |
| 🌐 Languages | Pie + bar chart with breakdown table |
| 👥 Contributors | Bar chart + ranked table |
| 🕸️ Network | Interactive graph with layout switcher |
| 🏥 Health Score | Gauge + score breakdown |
| 🔬 Centrality | Node centrality table + graph stats |

6. Export data using the sidebar buttons → files saved to `reports/`

---

## 🗂️ Project Structure

```
GitHub-Repository-Analyzer/
│
├── main.py             # Entry point — dependency check + launches GUI
├── github_api.py       # PyGithub wrapper (data fetching, validation, rate limit)
├── analytics.py        # Pandas/NumPy analytics engine + health score
├── graph_analysis.py   # NetworkX contributor graph + centrality
├── visualization.py    # Matplotlib/Seaborn chart rendering
├── export.py           # CSV / Excel / PDF export
├── gui.py              # Tkinter dashboard application
├── requirements.txt    # Python dependencies
└── reports/            # Auto-created — exported files land here
```

---

## 📊 Health Score Methodology

| Dimension | Max Points | Calculation |
|---|---|---|
| ⭐ Stars (Popularity) | 20 | Log-scaled, saturates at 10,000 stars |
| 🍴 Forks (Reusability) | 15 | Log-scaled, saturates at 2,000 forks |
| 🐛 Issue Responsiveness | 15 | Penalizes high open-issues-to-forks ratio |
| 📝 Commit Activity | 25 | Log-scaled commits in last 30 days |
| 👥 Contributor Community | 25 | Log-scaled contributor count |

**Grade mapping:** `A+` ≥85 · `A` ≥75 · `B` ≥65 · `C` ≥50 · `D` ≥35 · `F` <35

---

## 🕸️ Network Graph Details

- **Nodes:** One repository node (orange) + one per contributor (blue)
- **Edges:** Directed contributor → repository, weight = commit count
- **Node size:** Proportional to `log(commits)`
- **Layouts:** Spring · Circular · Shell · Kamada-Kawai

---

## ⚠️ Known Limitations

| Limitation | Detail |
|---|---|
| Public repos only | Private repos require appropriate token scopes |
| Commit sample | Fetches up to 1,000 recent commits |
| Contributor sample | Fetches up to 30 top contributors |
| Rate limits | Without token, large repos may hit the 60 req/hr cap |
| Very large repos | May be slow due to API pagination |

---

## 🛠️ Tech Stack

| Library | Purpose |
|---|---|
| `PyGithub` | GitHub REST API client |
| `Pandas` | DataFrame analytics engine |
| `NumPy` | Numerical computations |
| `Matplotlib` + `Seaborn` | Chart rendering (embedded in Tkinter) |
| `Plotly` | Available for future interactive charts |
| `NetworkX` | Contributor graph + centrality |
| `Tkinter` | Desktop GUI framework |
| `ReportLab` | PDF report generation |
| `openpyxl` | Excel workbook export |

---

## 📝 License

This project is licensed under the **MIT License** — free to use, modify, and distribute.

---

<div align="center">
Made with ❤️ by <a href="https://github.com/mawiya-47">mawiya-47</a>
</div>
