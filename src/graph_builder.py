import networkx as nx
import json

def build_context_graph(bim_data, include_types=None):
    # TODO: Implement graph creation logic using networkx
    G = nx.DiGraph()

    # Add all entity nodes
    id_to_type = {}
    for element in bim_data["entities"]:
        G.add_node(element["id"], **element)
        id_to_type[element["id"]] = element["Typ"]

    relationships = bim_data.get("relations", [])

    for rel in relationships:
        from_id = rel["from"]
        to_id = rel["to"]
        
        from_type = id_to_type.get(from_id)
        to_type = id_to_type.get(to_id)
        
        if not from_type or not to_type:
            continue  # skip unknown ids

        # Tür/Fenster → Wand OR Wand → Tür/Fenster
        if (from_type in ["Tür", "Fenster"] and to_type == "Wand") or \
        (to_type in ["Tür", "Fenster"] and from_type == "Wand"):
            # Make edge from Tür/Fenster → Wand
            if from_type in ["Tür", "Fenster"]:
                G.add_edge(from_id, to_id, relation="contained_in")
            else:
                G.add_edge(to_id, from_id, relation="contained_in")

        # Wand ↔ Wand
        elif from_type == "Wand" and to_type == "Wand":
            G.add_edge(from_id, to_id, relation="connected_to")
            G.add_edge(to_id, from_id, relation="connected_to")
        
        else:
            # fallback
            G.add_edge(from_id, to_id, relation=rel["type"])

    # Inspect
    print("Edges:")
    for u, v, d in G.edges(data=True):
        print(f"{u} → {v} : {d['relation']}")


        print("Nodes:")
        for n, d in G.nodes(data=True):
            print(f"{n} : {d['Typ']}")

        print("\nEdges:")
        for u, v, d in G.edges(data=True):
            print(f"{u} → {v} : {d['relation']}")
        pass

with open('D://Sounok//ai-code-jam-gnn3//json_cr.json', 'r') as file:
    bim_data = json.load(file)

build_context_graph(bim_data)


# Typ": "Tür"
# Typ": "Wand"
# Typ": "Fenster"