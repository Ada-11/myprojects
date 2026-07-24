import os
import json
import numpy as np
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA

def visualize_embeddings_with_pca():
    # 1. Define paths matching your active project footprint
    project_root = "/Users/ada/myprojects/my-first-app"
    jsonl_path = os.path.join(project_root, "knowledge_base_embedded.jsonl")
    plot_output = os.path.join(project_root, "embeddings_2d.png")

    if not os.path.exists(jsonl_path):
        print(f"[ERROR] Could not locate file at: {jsonl_path}")
        return

    # Containers to isolate records and color metrics
    embeddings_list = []
    sections_list = []

    # 2. Loop through each line / chunk from your database file
    print("[PROCESSING] Ingesting text blocks and vector matrix data arrays...")
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                record = json.loads(line)
                # Append arrays for metadata routing
                embeddings_list.append(record["embedding"])
                sections_list.append(record["section"])

    # Convert to pure NumPy arrays for mathematical slicing operations
    X = np.array(embeddings_list, dtype=np.float32)
    sections = np.array(sections_list)

    print(f"[PROCESSING] Ingested matrix footprint dimensions: {X.shape}")

    # 3. PCA DIMENSIONALITY REDUCTION (Instruction Requirement)
    print("[PROCESSING] Applying sklearn.decomposition.PCA(n_components=2)...")
    pca = PCA(n_components=2, random_state=42)
    embeddings_2d = pca.fit_transform(X)
    print(f" -> Explained Variance Ratio: {pca.explained_variance_ratio_}")

    # 4. COLOR-CODE MAP CONFIGURATION (Instruction Requirement)
    # Mapping unique colors to explicit insurance document section names
    color_map = {
        "coverage": "#2ca02c",    # Emerald Green
        "exclusions": "#d62728",  # Ruby Red
        "claims": "#1f77b4",      # Steel Blue
        "enrollment": "#ff7f0e"   # Safety Orange
    }

    # 5. RENDER CANVAS GRAPH VIA MATPLOTLIB
    print("[PROCESSING] Generating canvas view cluster plot layout diagram...")
    plt.figure(figsize=(10, 8))

    # Loop through each target label category to render distinct scatter points sequentially
    for section_name, hex_color in color_map.items():
        # Check if the section actually has any coordinates to plot in the 136 rows
        indices = (sections == section_name)
        if np.any(indices):
            plt.scatter(
                embeddings_2d[indices, 0],
                embeddings_2d[indices, 1],
                color=hex_color,
                label=section_name.capitalize(),
                s=70,
                edgecolor="black",
                linewidth=0.6,
                alpha=0.85
            )

    # Apply formatting and visual anchors
    plt.title("Knowledge Base Vector Semantic Space Map (2D PCA)", fontsize=14, fontweight="bold", pad=15)
    plt.xlabel("Principal Component 1", fontsize=11)
    plt.ylabel("Principal Component 2", fontsize=11)
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.legend(title="Insurance Section", loc="upper right", frameon=True, shadow=True)

    # Save to your requested file location destination path
    plt.tight_layout()
    plt.savefig(plot_output, dpi=300)
    plt.close()

    print("\n" + "="*60)
    print("[SUCCESS] Chart task executed successfully!")
    print(f" -> Output Image Chart Saved: {plot_output}")
    print("="*60)

if __name__ == "__main__":
    visualize_embeddings_with_pca()