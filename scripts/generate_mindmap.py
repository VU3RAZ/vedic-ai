"""Generate a visual mind map image for the Vedic AI project."""

import math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import numpy as np

# ── palette ──────────────────────────────────────────────────────────────────
BG        = "#0d1117"
ROOT_CLR  = "#f0c040"
COLORS = [
    "#58a6ff",  # 0 Domain
    "#3fb950",  # 1 Engines
    "#d29922",  # 2 Features
    "#bc8cff",  # 3 Core/Rules
    "#ff7b72",  # 4 Retrieval
    "#79c0ff",  # 5 LLM
    "#56d364",  # 6 Orchestration
    "#ffa657",  # 7 Evaluation
    "#f778ba",  # 8 Storage
    "#7ee787",  # 9 API
    "#e3b341",  # 10 CLI
    "#a5d6ff",  # 11 Web UI
    "#ff9f9f",  # 12 Tech Stack
]

# ── data ─────────────────────────────────────────────────────────────────────
ROOT = "VEDIC AI\n(local-first Jyotish\nprediction system)"

BRANCHES = [
    {
        "label": "DOMAIN\nSchemas",
        "color": COLORS[0],
        "children": [
            "ChartBundle\n(central artifact)",
            "BirthData\n& GeoLocation",
            "PlanetPlacement\n(9 grahas)",
            "NakshatraDetail\n(27 nakshatras)",
            "DashaPeriod\nVimshottari",
            "PredictionReport\n& Sections",
            "CorpusChunk\nRetrievedPassage",
        ],
    },
    {
        "label": "ENGINES\nCalculation",
        "color": COLORS[1],
        "children": [
            "SwissEphAdapter\n(PRIMARY)",
            "Lahiri Ayanamsa\nWhole Sign",
            "Vargas D1–D60",
            "Vimshottari\nDasha calc",
            "Dignity\n(exalt/debil/moola)",
            "KerykeionAdapter\n(secondary)",
        ],
    },
    {
        "label": "FEATURES\nExtraction",
        "color": COLORS[2],
        "children": [
            "core_features.py\nOrchestrator",
            "Graha Drishti\n+ Rashi Drishti",
            "30+ Yoga\nDetectors",
            "Sandhi\n(cusp zones)",
            "Nakshatra\nlord/guna/pada",
            "Dasha/Transit\nfeatures",
            "Varga Analysis\nD3/D7/D9/D10/D12",
            "Raman\nFlowchart",
            "Functional\nBenefic/Malefic",
        ],
    },
    {
        "label": "RULES\n& Core",
        "color": COLORS[3],
        "children": [
            "~450 YAML rules\n(4 scopes)",
            "personality.yaml\n~100 rules",
            "career.yaml\n~100 rules",
            "relationships.yaml\n~100 rules",
            "health.yaml\n~100 rules",
            "rule_evaluator.py\nconflict resolution",
        ],
    },
    {
        "label": "RETRIEVAL\nRAG / FAISS",
        "color": COLORS[4],
        "children": [
            "9 Jyotish texts\n1.5M chars",
            "3,054 chunks\n(size=600)",
            "all-MiniLM-L6-v2\n384-dim",
            "FAISS IndexFlatIP\ncosine sim",
            "top-k retrieval\n(k=5 default)",
            "BPHS + Jaimini\nSutras",
        ],
    },
    {
        "label": "LLM\nInference",
        "color": COLORS[5],
        "children": [
            "llama.cpp\n(primary backend)",
            "Ollama / LM Studio\n(alt backends)",
            "gemma-4-26B\n(active model)",
            "prompt_builder.py\nstructured prompts",
            "output_parser.py\nJSON repair",
            "fine_tune_prep.py\nSFT dataset",
        ],
    },
    {
        "label": "ORCHESTRATION\nPipeline",
        "color": COLORS[6],
        "children": [
            "pipeline.py\n9-stage flow",
            "Chart → Features\n→ Rules → RAG",
            "Prompt → LLM\n→ Parse → Report",
            "Artifact persistence\n(debug JSONs)",
            "timing_service.py\ndasha/transit",
            "evidence_builder.py\ncite refs",
        ],
    },
    {
        "label": "EVALUATION\n& Testing",
        "color": COLORS[7],
        "children": [
            "538+ tests\n(353 passing)",
            "unit / integration\nregression / e2e",
            "eval_set_v1.json\ngolden cases",
            "grounding &\ncoverage metrics",
            "Repro manifest\n(hash + params)",
        ],
    },
    {
        "label": "API + CLI\n+ Web UI",
        "color": COLORS[9],
        "children": [
            "FastAPI\nPOST /predictions",
            "Typer CLI\nvedic-ai predict",
            "index.html 2111 LOC\nVanilla JS offline",
            "Chart / Drishti\n/ Vargas tabs",
            "Standard + Raman\nanalysis tabs",
            "GET /health\nSwagger /docs",
        ],
    },
    {
        "label": "TECH STACK\n& Config",
        "color": COLORS[12],
        "children": [
            "Python 3.11+\nPydantic v2",
            "pyswisseph\nMoshier ephem",
            "structlog\nJSON-capable",
            "SQLite cache\nchart_cache.db",
            "Hatchling build\npyproject.toml",
            "4 YAML configs\n(app/models/astro/retrieval)",
        ],
    },
]

# ── helpers ──────────────────────────────────────────────────────────────────

def polar_to_xy(r, angle_deg):
    a = math.radians(angle_deg)
    return r * math.cos(a), r * math.sin(a)


def draw_rounded_box(ax, cx, cy, text, bg, fg="white", fontsize=7.5,
                     width=1.55, height=0.55, alpha=0.93, zorder=3):
    box = FancyBboxPatch(
        (cx - width / 2, cy - height / 2), width, height,
        boxstyle="round,pad=0.06",
        facecolor=bg, edgecolor=fg, linewidth=0.6,
        alpha=alpha, zorder=zorder,
    )
    ax.add_patch(box)
    ax.text(cx, cy, text, ha="center", va="center",
            fontsize=fontsize, color=fg, fontweight="bold",
            linespacing=1.3, zorder=zorder + 1,
            multialignment="center")


def draw_root(ax, text, r=0):
    circle = plt.Circle((0, 0), 1.25, color=ROOT_CLR, zorder=4, alpha=0.95)
    ax.add_patch(circle)
    ax.text(0, 0, text, ha="center", va="center",
            fontsize=9, fontweight="bold", color=BG,
            linespacing=1.4, zorder=5, multialignment="center")


# ── main drawing ─────────────────────────────────────────────────────────────

def build_figure():
    fig, ax = plt.subplots(figsize=(28, 28), facecolor=BG)
    ax.set_facecolor(BG)
    ax.set_aspect("equal")
    ax.axis("off")

    n = len(BRANCHES)
    branch_r   = 3.6   # distance from root to branch node
    child_r    = 6.8   # distance from root to child node

    for i, branch in enumerate(BRANCHES):
        angle = 360 * i / n - 90          # start at top, go clockwise
        bx, by = polar_to_xy(branch_r, angle)
        color  = branch["color"]

        # spoke: root → branch
        ax.plot([0, bx], [0, by], color=color, lw=1.8, alpha=0.55, zorder=1)

        # branch node
        draw_rounded_box(ax, bx, by, branch["label"],
                         bg=color, fg=BG, fontsize=9, width=1.75, height=0.7)

        # children — fan out ±spread around branch angle
        children = branch["children"]
        nc = len(children)
        spread = min(28, 170 / n)         # degrees of arc for children
        if nc == 1:
            offsets = [0]
        else:
            offsets = np.linspace(-spread, spread, nc)

        for j, child_text in enumerate(children):
            cangle = angle + offsets[j]
            cx, cy = polar_to_xy(child_r, cangle)

            # spoke: branch → child
            ax.plot([bx, cx], [by, cy], color=color, lw=0.9,
                    alpha=0.35, zorder=1)

            draw_rounded_box(ax, cx, cy, child_text,
                             bg="#161b22", fg=color,
                             fontsize=7.2, width=1.62, height=0.52)

    draw_root(ax, ROOT)

    # title
    ax.text(0, -8.6, "Vedic AI — Full System Mind Map",
            ha="center", va="center", fontsize=14, color="#8b949e",
            fontstyle="italic")

    ax.set_xlim(-9, 9)
    ax.set_ylim(-9, 9)

    return fig


if __name__ == "__main__":
    import os
    out = os.path.join(os.path.dirname(__file__), "..", "docs", "mindmap.png")
    fig = build_figure()
    fig.savefig(out, dpi=180, bbox_inches="tight",
                facecolor=BG, edgecolor="none")
    plt.close(fig)
    print(f"Saved → {os.path.abspath(out)}")
