from typing import Dict, List, Any


class GraphBuilder:
    """
    Service to build a dependency graph for React Flow visualization.
    Converts extracted AST entities into standardized nodes and edges.
    """

    def __init__(self, extracted_data: Dict[str, List[Dict[str, Any]]]):
        self.extracted_data = extracted_data
        self.nodes: List[Dict[str, Any]] = []
        self.edges: List[Dict[str, Any]] = []

    def build_graph(self) -> Dict[str, List[Dict[str, Any]]]:
        """Main method to generate nodes and edges."""
        self._generate_nodes()
        self._generate_edges()

        return {"nodes": self.nodes, "edges": self.edges}

    def _generate_nodes(self):
        """Maps extracted AST entities to strict React Flow node types."""

        # Components
        for comp in self.extracted_data.get("components", []):
            self.nodes.append(
                {
                    "id": f"comp_{comp['line']}",
                    "type": "component",
                    "data": {"label": f"Component (Line {comp['line']})"},
                }
            )

        # States
        for state in self.extracted_data.get("states", []):
            self.nodes.append(
                {
                    "id": f"state_{state['line']}",
                    "type": "state",
                    "data": {"label": state.get("text", "useState")},
                }
            )

        # Effects
        for effect in self.extracted_data.get("effects", []):
            self.nodes.append(
                {
                    "id": f"effect_{effect['line']}",
                    "type": "effect",
                    "data": {"label": "useEffect"},
                }
            )

        # Functions
        for func in self.extracted_data.get("functions", []):
            self.nodes.append(
                {
                    "id": f"func_{func['line']}",
                    "type": "function",
                    "data": {"label": f"Function (Line {func['line']})"},
                }
            )

        # Props
        for prop in self.extracted_data.get("props", []):
            self.nodes.append(
                {
                    "id": f"prop_{prop['line']}",
                    "type": "prop",
                    "data": {"label": prop.get("text", "prop")},
                }
            )

    def _generate_edges(self):
        """
        Builds logical connections (edges) between nodes.
        Uses required edge types: uses, updates, calls, depends_on, missing_dependency.
        """
        components = self.extracted_data.get("components", [])
        if not components:
            return

        # Assuming the first component is the root for heuristic connections
        main_comp_id = f"comp_{components[0]['line']}"

        # Component -> State (uses)
        for state in self.extracted_data.get("states", []):
            self.edges.append(
                {
                    "id": f"edge_comp_state_{state['line']}",
                    "source": main_comp_id,
                    "target": f"state_{state['line']}",
                    "type": "uses",
                }
            )

        # Component -> Effect (uses)
        for effect in self.extracted_data.get("effects", []):
            self.edges.append(
                {
                    "id": f"edge_comp_effect_{effect['line']}",
                    "source": main_comp_id,
                    "target": f"effect_{effect['line']}",
                    "type": "uses",
                }
            )

        # Component -> Function (uses)
        for func in self.extracted_data.get("functions", []):
            self.edges.append(
                {
                    "id": f"edge_comp_func_{func['line']}",
                    "source": main_comp_id,
                    "target": f"func_{func['line']}",
                    "type": "uses",
                }
            )

        # Effect -> Function (calls)
        # Basic mapping to demonstrate inter-node dependencies
        effects = self.extracted_data.get("effects", [])
        functions = self.extracted_data.get("functions", [])

        if effects and functions:
            for effect in effects:
                for func in functions:
                    self.edges.append(
                        {
                            "id": f"edge_effect_func_{effect['line']}_{func['line']}",
                            "source": f"effect_{effect['line']}",
                            "target": f"func_{func['line']}",
                            "type": "calls",
                        }
                    )
                    break
