"""
graph_analysis.py
-----------------
NetworkX-based contributor network graph builder and centrality analyzer.

Graph topology
--------------
  Nodes: repository node + one node per contributor
  Edges: contributor → repository (weighted by commit count)
"""

import networkx as nx
import numpy as np
from typing import Optional


class ContributorGraph:
    """
    Builds and analyzes a bipartite contributor–repository network
    using NetworkX, then exposes layout and centrality data for
    downstream visualization.
    """

    def __init__(self):
        self.graph: Optional[nx.DiGraph] = None
        self.repo_node: Optional[str] = None
        self.centrality: dict = {}
        self._positions: Optional[dict] = None

    # ------------------------------------------------------------------ #
    #  Graph Construction                                                  #
    # ------------------------------------------------------------------ #

    def build_graph(self, repo_info: dict, contributors: list[dict]) -> nx.DiGraph:
        """
        Construct the directed contributor graph.

        Args:
            repo_info:    Repository metadata (must include 'full_name').
            contributors: List of contributor dicts from GitHubAnalyzer.

        Returns:
            The constructed NetworkX DiGraph.
        """
        G = nx.DiGraph()
        repo_name = repo_info.get('full_name', repo_info.get('name', 'Repository'))
        self.repo_node = repo_name

        # Central repository node
        G.add_node(
            repo_name,
            node_type='repository',
            stars=repo_info.get('stars', 0),
            forks=repo_info.get('forks', 0),
            label=repo_info.get('name', repo_name),
        )

        # Contributor nodes + edges
        for contributor in contributors:
            login = contributor['login']
            commits = contributor['contributions']
            pct = contributor.get('percentage', 0)

            G.add_node(
                login,
                node_type='contributor',
                commits=commits,
                percentage=pct,
                label=login,
            )

            # Directed edge: contributor → repository
            G.add_edge(
                login,
                repo_name,
                weight=commits,
                percentage=pct,
            )

        self.graph = G
        self._compute_centrality()
        self._positions = None  # Invalidate cached layout
        return G

    # ------------------------------------------------------------------ #
    #  Centrality                                                          #
    # ------------------------------------------------------------------ #

    def _compute_centrality(self):
        """Compute degree, betweenness, and closeness centrality."""
        if not self.graph:
            return

        # Use undirected version for closeness/betweenness (more meaningful)
        G_undirected = self.graph.to_undirected()

        degree      = nx.degree_centrality(self.graph)
        betweenness = nx.betweenness_centrality(G_undirected, normalized=True)
        closeness   = nx.closeness_centrality(G_undirected)

        self.centrality = {}
        for node in self.graph.nodes():
            self.centrality[node] = {
                'degree':      round(degree.get(node, 0), 4),
                'betweenness': round(betweenness.get(node, 0), 4),
                'closeness':   round(closeness.get(node, 0), 4),
            }

    def centrality_table(self) -> list[dict]:
        """
        Return centrality metrics as a sorted list for tabular display.

        Returns:
            List of dicts sorted by degree centrality (descending).
        """
        rows = []
        for node, metrics in self.centrality.items():
            node_type = self.graph.nodes[node].get('node_type', 'unknown')
            rows.append({
                'Node': node,
                'Type': node_type.capitalize(),
                'Degree Centrality':      metrics['degree'],
                'Betweenness Centrality': metrics['betweenness'],
                'Closeness Centrality':   metrics['closeness'],
            })
        return sorted(rows, key=lambda r: r['Degree Centrality'], reverse=True)

    # ------------------------------------------------------------------ #
    #  Layout                                                              #
    # ------------------------------------------------------------------ #

    def get_layout(self, layout: str = 'spring') -> dict:
        """
        Compute or return cached node positions.

        Args:
            layout: 'spring' | 'circular' | 'shell' | 'kamada_kawai'

        Returns:
            Dict mapping node → (x, y) position.
        """
        if self._positions is not None:
            return self._positions

        G = self.graph
        if not G:
            return {}

        seed = 42
        if layout == 'spring':
            # Weight by commit count for visually meaningful spacing
            pos = nx.spring_layout(G, seed=seed, k=2.5, iterations=100,
                                   weight='weight')
        elif layout == 'circular':
            pos = nx.circular_layout(G)
        elif layout == 'shell':
            # Place repo at center, contributors on outer shell
            repo_nodes  = [n for n, d in G.nodes(data=True) if d.get('node_type') == 'repository']
            contr_nodes = [n for n, d in G.nodes(data=True) if d.get('node_type') == 'contributor']
            shells = [repo_nodes, contr_nodes] if repo_nodes else [contr_nodes]
            pos = nx.shell_layout(G, nlist=shells)
        elif layout == 'kamada_kawai':
            pos = nx.kamada_kawai_layout(G.to_undirected())
        else:
            pos = nx.spring_layout(G, seed=seed)

        self._positions = pos
        return pos

    # ------------------------------------------------------------------ #
    #  Graph Statistics                                                    #
    # ------------------------------------------------------------------ #

    def graph_stats(self) -> dict:
        """Return a summary of basic graph statistics."""
        if not self.graph:
            return {}

        G = self.graph
        return {
            'nodes':               G.number_of_nodes(),
            'edges':               G.number_of_edges(),
            'density':             round(nx.density(G), 4),
            'is_connected':        nx.is_weakly_connected(G),
            'avg_degree':          round(
                sum(d for _, d in G.degree()) / max(G.number_of_nodes(), 1), 2
            ),
            'most_central_contributor': self._most_central(),
        }

    def _most_central(self) -> str:
        """Return the contributor node with the highest degree centrality."""
        if not self.centrality:
            return 'N/A'
        contrib_only = {
            n: v['degree']
            for n, v in self.centrality.items()
            if self.graph.nodes[n].get('node_type') == 'contributor'
        }
        if not contrib_only:
            return 'N/A'
        return max(contrib_only, key=contrib_only.get)
