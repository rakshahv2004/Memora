import json
import time
import hashlib
import sqlite3
import networkx as nx
import matplotlib.pyplot as plt

DB_NAME = "memora.db"


def get_memory_signature(memories):
    """Create a fingerprint of the current saved memories."""
    memory_data = [
        (memory_id, content, category)
        for memory_id, content, category, created_at in memories
    ]

    raw_data = json.dumps(memory_data, ensure_ascii=False)
    return hashlib.sha256(raw_data.encode("utf-8")).hexdigest()


def initialize_graph_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS graph_cache (
            id INTEGER PRIMARY KEY,
            memory_signature TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS graph_entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            entity_type TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS graph_relationships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            relation TEXT NOT NULL,
            target TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def save_knowledge_graph(graph, signature):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM graph_entities")
    cursor.execute("DELETE FROM graph_relationships")
    cursor.execute("DELETE FROM graph_cache")

    cursor.execute(
        "INSERT INTO graph_cache (memory_signature) VALUES (?)",
        (signature,)
    )

    for node, data in graph.nodes(data=True):
        cursor.execute(
            "INSERT INTO graph_entities (name, entity_type) VALUES (?, ?)",
            (node, data.get("entity_type", "Concept"))
        )

    for source, target, data in graph.edges(data=True):
        cursor.execute(
            """
            INSERT INTO graph_relationships (source, relation, target)
            VALUES (?, ?, ?)
            """,
            (source, data.get("relation", "related to"), target)
        )

    conn.commit()
    conn.close()


def load_knowledge_graph(signature):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT memory_signature FROM graph_cache LIMIT 1"
    )
    cached = cursor.fetchone()

    if not cached or cached[0] != signature:
        conn.close()
        return None

    graph = nx.DiGraph()

    cursor.execute(
        "SELECT name, entity_type FROM graph_entities"
    )

    for name, entity_type in cursor.fetchall():
        graph.add_node(name, entity_type=entity_type)

    cursor.execute(
        "SELECT source, relation, target FROM graph_relationships"
    )

    for source, relation, target in cursor.fetchall():
        graph.add_edge(source, target, relation=relation)

    conn.close()
    return graph


def create_knowledge_graph(memories, client):
    graph = nx.DiGraph()

    if not memories:
        return graph

    memory_text = "\n".join(
        [content for memory_id, content, category, created_at in memories]
    )

    prompt = f"""
You are an information extraction system.

Extract entities and meaningful relationships from the user's memories.

Return ONLY valid JSON in this format:
{{
    "entities": [
        {{"id": "Artificial Intelligence", "type": "Field"}}
    ],
    "relationships": [
        {{
            "source": "Artificial Intelligence",
            "relation": "includes",
            "target": "Machine Learning"
        }}
    ]
}}

Rules:
- Extract only information supported by memories.
- Do not invent facts.
- Use short, clear entity names.
- Relationships must connect existing entities.
- Include the user as an entity when appropriate.

USER MEMORIES:
{memory_text}
"""

    response = None

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-3.5-flash",
                contents=prompt
            )
            break

        except Exception as e:
            if "503" in str(e) and attempt < 2:
                time.sleep(3 * (attempt + 1))
            else:
                raise

    if response is None or not response.text:
        raise ValueError("Gemini returned an empty response.")

    text_response = response.text.strip()

    if text_response.startswith("```"):
        text_response = text_response.replace("```json", "")
        text_response = text_response.replace("```", "").strip()

    result = json.loads(text_response)

    for entity in result.get("entities", []):
        graph.add_node(
            entity["id"],
            entity_type=entity.get("type", "Concept")
        )

    for relationship in result.get("relationships", []):
        source = relationship["source"]
        target = relationship["target"]
        relation = relationship["relation"]

        if source in graph and target in graph:
            graph.add_edge(
                source,
                target,
                relation=relation
            )

    return graph


def get_or_create_knowledge_graph(memories, client):
    initialize_graph_database()

    if not memories:
        return nx.DiGraph(), "empty"

    signature = get_memory_signature(memories)

    # First, check whether a matching graph is already saved
    cached_graph = load_knowledge_graph(signature)

    if cached_graph is not None:
        return cached_graph, "cached"

    # Generate a new graph if memories have changed
    graph = create_knowledge_graph(memories, client)

    save_knowledge_graph(graph, signature)

    return graph, "generated"


def display_knowledge_graph(graph):
    if graph.number_of_nodes() == 0:
        return None

    fig, ax = plt.subplots(figsize=(12, 7))

    positions = nx.spring_layout(graph, seed=42, k=1.5)

    nx.draw_networkx_nodes(
        graph, positions, ax=ax,
        node_color="skyblue", node_size=2800
    )

    nx.draw_networkx_labels(
        graph, positions, ax=ax,
        font_size=9, font_weight="bold"
    )

    nx.draw_networkx_edges(
        graph, positions, ax=ax,
        arrows=True, arrowstyle="-|>", arrowsize=20,
        edge_color="gray"
    )

    edge_labels = nx.get_edge_attributes(graph, "relation")

    nx.draw_networkx_edge_labels(
        graph, positions, edge_labels=edge_labels,
        ax=ax, font_size=8
    )

    ax.set_title("Memora - Persistent Knowledge Graph")
    ax.axis("off")

    return fig
