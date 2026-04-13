import tree_sitter_typescript as tsts
from tree_sitter import Language, Parser, Node
from typing import List, Dict, Any, Optional, Set

# Initialize the parser for TSX
TSX_LANGUAGE = Language(tsts.language_tsx())
parser = Parser(TSX_LANGUAGE)

# Common globals and React primitives to ignore during dependency checks
IGNORED_GLOBALS = {
    "console",
    "window",
    "document",
    "Math",
    "setTimeout",
    "setInterval",
    "clearTimeout",
    "clearInterval",
    "undefined",
    "null",
    "NaN",
    "Error",
    "useState",
    "useEffect",
    "useCallback",
    "useMemo",
    "useRef",
    "React",
}


class ReactASTAnalyzer:
    """
    A robust AST analyzer for React/TypeScript code.
    Extracts core React entities and detects common performance/logic issues.
    """

    def __init__(self, code: str):
        self.code = code
        self.code_bytes = bytes(code, "utf8")
        self.tree = parser.parse(self.code_bytes)

        self.issues: List[Dict[str, Any]] = []
        self.extracted_data: Dict[str, List[Dict[str, Any]]] = {
            "components": [],
            "states": [],
            "effects": [],
            "functions": [],
            "props": [],
        }

    def run_analysis(self) -> Dict[str, Any]:
        """Main entry point. Traverses the AST and returns extracted data and issues."""
        self._traverse_and_analyze(self.tree.root_node)
        return {"issues": self.issues, "extracted_data": self.extracted_data}

    def _get_node_text(self, node: Optional[Node]) -> str:
        """Helper to safely extract string text from a node."""
        if not node:
            return ""
        return self.code_bytes[node.start_byte : node.end_byte].decode("utf8")

    def _traverse_and_analyze(self, node: Node):
        """Recursively traverses the AST and applies specific inspectors."""
        if node.type == "call_expression":
            self._inspect_call_expression(node)
        elif node.type == "jsx_attribute":
            self._inspect_jsx_attribute(node)
        elif node.type in ("function_declaration", "arrow_function"):
            self._inspect_function_or_component(node)

        for child in node.children:
            self._traverse_and_analyze(child)

    def _inspect_call_expression(self, node: Node):
        """Analyzes hooks like useState and useEffect."""
        function_identifier = node.child_by_field_name("function")
        if not function_identifier:
            return

        func_name = self._get_node_text(function_identifier)

        # Stage 1: Handle useState extraction
        if func_name == "useState":
            state_var, setter_func = "unknown", "unknown"
            parent = node.parent
            if parent and parent.type == "variable_declarator":
                name_node = parent.child_by_field_name("name")
                if name_node and name_node.type == "array_pattern":
                    identifiers = [
                        c for c in name_node.children if c.type == "identifier"
                    ]
                    if len(identifiers) >= 1:
                        state_var = self._get_node_text(identifiers[0])
                    if len(identifiers) >= 2:
                        setter_func = self._get_node_text(identifiers[1])

            self.extracted_data["states"].append(
                {
                    "type": "state",
                    "text": self._get_node_text(node),
                    "state_variable": state_var,
                    "setter_function": setter_func,
                    "line": node.start_point[0] + 1,
                }
            )

        # Stage 2: Handle useEffect deep analysis
        elif func_name == "useEffect":
            effect_data = {
                "type": "effect",
                "line": node.start_point[0] + 1,
                "missing_dependencies": [],
            }
            self.extracted_data["effects"].append(effect_data)
            self._analyze_use_effect_dependencies(node, effect_data)

    def _analyze_use_effect_dependencies(
        self, effect_node: Node, effect_data: Dict[str, Any]
    ):
        """Detects missing dependencies by comparing used identifiers vs declared array."""
        arguments = effect_node.child_by_field_name("arguments")
        if (
            not arguments or len(arguments.children) < 2
        ):  # '(' and ')' count as children too
            return

        # Find the callback function and dependency array
        callback_node = None
        dep_array_node = None

        for child in arguments.children:
            if child.type in ("arrow_function", "function"):
                callback_node = child
            elif child.type == "array":
                dep_array_node = child

        if not dep_array_node:
            self.issues.append(
                {
                    "type": "warning",
                    "title": "Missing dependency array",
                    "explanation": "useEffect has no dependency array. It will run after every render, which might cause infinite loops.",
                    "suggestion": "Add a dependency array '[]' if it should only run once, or list required dependencies.",
                    "line": effect_node.start_point[0] + 1,
                }
            )
            return

        # Extract declared dependencies from the array
        declared_deps = set()
        for element in dep_array_node.children:
            if element.type == "identifier":
                declared_deps.add(self._get_node_text(element))
            elif element.type in ("object", "array"):
                self.issues.append(
                    {
                        "type": "error",
                        "title": "Unstable reference in dependency array",
                        "explanation": f"Found an inline {element.type} in the dependency array. This creates a new reference on every render.",
                        "suggestion": f"Move the {element.type} outside the component or use useMemo.",
                        "line": element.start_point[0] + 1,
                    }
                )

        # Deep AST search for used identifiers inside the callback body
        if callback_node:
            local_declarations: Set[str] = set()
            used_identifiers = self._extract_identifiers(
                callback_node, local_declarations
            )

            # Calculate missing dependencies
            missing = used_identifiers - declared_deps - IGNORED_GLOBALS

            if missing:
                missing_list = list(missing)
                # Save to graph data so GraphBuilder can map them as edges
                effect_data["missing_dependencies"] = missing_list

                self.issues.append(
                    {
                        "type": "warning",
                        "title": "Missing useEffect dependencies",
                        "explanation": f"React Hook useEffect has missing dependencies: {', '.join(missing_list)}.",
                        "suggestion": f"Include them in the dependency array: [...deps, {', '.join(missing_list)}]",
                        "line": effect_node.start_point[0] + 1,
                    }
                )

    def _extract_identifiers(
        self, node: Optional[Node], local_decls: Set[str]
    ) -> Set[str]:
        """
        Recursively extracts identifiers used in a block of code,
        ignoring property accesses and tracking local declarations.
        """
        used = set()
        if not node:
            return used

        # Track locally declared variables so we don't flag them as missing
        if node.type == "variable_declarator":
            name_node = node.child_by_field_name("name")
            if name_node and name_node.type == "identifier":
                local_decls.add(self._get_node_text(name_node))

        # Track function parameters
        if node.type in ("formal_parameters", "parameters"):
            for param in node.children:
                if param.type == "identifier":
                    local_decls.add(self._get_node_text(param))

        # Capture valid identifiers
        if node.type == "identifier":
            parent = node.parent
            # Ignore property identifiers (e.g., 'id' in 'user.id')
            is_property_access = (
                parent
                and parent.type == "member_expression"
                and parent.child_by_field_name("property") == node
            )
            # Ignore the variable declaration identifier itself
            is_declaration = (
                parent
                and parent.type in ("function_declaration", "variable_declarator")
                and parent.child_by_field_name("name") == node
            )

            if not is_property_access and not is_declaration:
                name = self._get_node_text(node)
                if name not in local_decls:
                    used.add(name)

        for child in node.children:
            used.update(self._extract_identifiers(child, local_decls))

        return used

    def _inspect_jsx_attribute(self, node: Node):
        """Detects inline functions in JSX attributes that cause re-renders."""
        attr_name_node = node.children[0] if node.children else None
        if not attr_name_node or attr_name_node.type != "property_identifier":
            return

        attr_name = self._get_node_text(attr_name_node)
        if not attr_name.startswith("on"):
            return

        jsx_expression = next(
            (c for c in node.children if c.type == "jsx_expression"), None
        )
        if not jsx_expression:
            return

        for child in jsx_expression.children:
            if child.type in ("arrow_function", "function"):
                self.issues.append(
                    {
                        "type": "warning",
                        "title": "Inline function in JSX",
                        "explanation": f"Inline function found in '{attr_name}' attribute. This creates a new function instance on every render.",
                        "suggestion": "Extract the function using useCallback or define it outside the JSX.",
                        "line": child.start_point[0] + 1,
                    }
                )

    def _inspect_function_or_component(self, node: Node):
        """Extracts Components, Functions, and their associated Props."""
        has_jsx = self._contains_node_type(
            node, ("jsx_element", "jsx_self_closing_element", "jsx_fragment")
        )

        if has_jsx:
            component_name = "AnonymousComponent"
            name_node = node.child_by_field_name("name")

            if (
                not name_node
                and node.parent
                and node.parent.type == "variable_declarator"
            ):
                name_node = node.parent.child_by_field_name("name")

            if name_node:
                component_name = self._get_node_text(name_node)

            self.extracted_data["components"].append(
                {
                    "type": "component",
                    "name": component_name,
                    "line": node.start_point[0] + 1,
                }
            )

            self._extract_props(node, component_name)
        else:
            self.extracted_data["functions"].append(
                {"type": "function", "line": node.start_point[0] + 1}
            )

    def _extract_props(self, component_node: Node, component_name: str):
        """Extracts properties passed to a component."""
        parameters_node = component_node.child_by_field_name("parameters")
        if not parameters_node:
            return

        for param in parameters_node.children:
            if param.type == "identifier":
                prop_name = self._get_node_text(param)
                if prop_name not in ("(", ")"):
                    self._add_prop(prop_name, component_name, param.start_point[0] + 1)

            elif param.type == "object_pattern":
                for prop_child in param.children:
                    if prop_child.type in (
                        "shorthand_property_identifier",
                        "identifier",
                    ):
                        self._add_prop(
                            self._get_node_text(prop_child),
                            component_name,
                            prop_child.start_point[0] + 1,
                        )
                    elif prop_child.type == "pair_pattern":
                        key_node = prop_child.child_by_field_name("key")
                        if key_node:
                            self._add_prop(
                                self._get_node_text(key_node),
                                component_name,
                                key_node.start_point[0] + 1,
                            )

    def _add_prop(self, name: str, component_name: str, line: int):
        self.extracted_data["props"].append(
            {"type": "prop", "text": name, "component": component_name, "line": line}
        )

    def _contains_node_type(self, root: Node, target_types: tuple) -> bool:
        if root.type in target_types:
            return True
        for child in root.children:
            if self._contains_node_type(child, target_types):
                return True
        return False
