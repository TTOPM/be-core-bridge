# entanglement_engine.py
# Simulates conceptual entanglement within the Symbiont system

class EntangledNode:
    def __init__(self, concept, amplitude=1.0):
        self.concept = concept
        self.amplitude = amplitude
        self.links = []

    def entangle_with(self, other_node, strength=1.0):
        self.links.append((other_node, strength))
        other_node.links.append((self, strength))

    def __repr__(self):
        return f"<EntangledNode:{self.concept}|A:{self.amplitude}|Links:{len(self.links)}>"

class EntanglementEngine:
    def __init__(self):
        self.nodes = {}

    def get_or_create_node(self, concept):
        if concept not in self.nodes:
            self.nodes[concept] = EntangledNode(concept)
        return self.nodes[concept]

    def entangle(self, concept1, concept2, strength=1.0):
        node1 = self.get_or_create_node(concept1)
        node2 = self.get_or_create_node(concept2)
        node1.entangle_with(node2, strength)

    def explore(self, start_concept, depth=2):
        visited = set()
        results = []

        def dfs(node, current_depth):
            if node.concept in visited or current_depth > depth:
                return
            visited.add(node.concept)
            results.append(node)
            for link, strength in node.links:
                dfs(link, current_depth + 1)

        if start_concept in self.nodes:
            dfs(self.nodes[start_concept], 0)

        return results
