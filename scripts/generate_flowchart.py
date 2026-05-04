"""
Generate a layered dependency flowchart for Vedic AI.
Tiers flow top→bottom; edges show import direction (source imports target means arrow points down).
"""

import math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
import numpy as np

# ── palette ────────────────────────────────────────────────────────────────────
BG   = "#0d1117"
TEXT = "#e6edf3"

PKG_COLOR = {
    "domain":        "#1a5f7a",
    "core":          "#5a2d82",
    "engines":       "#1e6b3a",
    "features":      "#7a5a12",
    "retrieval":     "#7a2d1a",
    "llm":           "#1a3a7a",
    "orchestration": "#3a1a7a",
    "evaluation":    "#1a7a5a",
    "storage":       "#484848",
    "utils":         "#303030",
    "api":           "#7a1a3a",
    "cli":           "#3a7a1a",
    "static":        "#7a3a1a",
}

# ── nodes: (id, display_label, package) ────────────────────────────────────────
NODES = [
    # tier 0
    ("d_enums",   "domain/enums\n(Graha,Rasi,Nakshatra...)",  "domain"),
    ("d_birth",   "domain/birth\n(BirthData, GeoLocation)",   "domain"),
    ("d_corpus",  "domain/corpus\n(CorpusChunk, Passage)",    "domain"),
    ("c_exc",     "core/exceptions\n(all error types)",       "core"),
    ("c_rules",   "core/rules\n(RuleDefinition, Operator)",   "core"),
    ("c_log",     "core/logging\n(setup_logging)",            "core"),
    ("l_base",    "llm/base\n(LLMClient Protocol)",           "llm"),
    ("l_parser",  "llm/output_parser\n(repair_llm_output)",   "llm"),

    # tier 1
    ("d_planet",  "domain/planet\n(PlanetPlacement)",         "domain"),
    ("d_house",   "domain/house\n(HousePlacement)",           "domain"),
    ("d_nk",      "domain/nakshatra\n(NakshatraDetail×27)",   "domain"),
    ("d_dasha",   "domain/dasha\n(DashaPeriod)",              "domain"),
    ("c_cfg",     "core/config\n(AppConfig, load_app_config)", "core"),

    # tier 2
    ("d_chart",   "domain/chart  ★\n(ChartBundle — central)", "domain"),
    ("d_pred",    "domain/prediction\n(PredictionReport)",    "domain"),
    ("c_rload",   "core/rule_loader\n(load_rule_set)",        "core"),
    ("e_dignity", "engines/dignity\n(compute_dignity,RASI_LORDS)", "engines"),
    ("e_varga",   "engines/varga\n(compute_varga_rasi)",      "engines"),
    ("e_vim",     "engines/vimshottari\n(vimshottari_dashas)", "engines"),

    # tier 3
    ("e_norm",    "engines/normalizer\n(normalize_engine_output)", "engines"),
    ("c_reval",   "core/rule_evaluator\n(evaluate_rules,resolve_conflicts)", "core"),
    ("f_base",    "features/base\n(KENDRA,TRIKONA,DUSTHANA)", "features"),
    ("e_base",    "engines/base\n(AstrologyEngine Protocol)", "engines"),

    # tier 4a — engine adapters
    ("e_swiss",   "engines/swisseph  ★\n(SwissEphAdapter — PRIMARY)", "engines"),
    ("e_kery",    "engines/kerykeion\n(KerykeionAdapter)",    "engines"),
    ("e_reg",     "engines/registry\n(select_engine, cache)", "engines"),

    # tier 4b — feature sub-modules (group A: 8)
    ("f_strength","features/strength\n(planet_strengths, combustion)", "features"),
    ("f_aspects", "features/aspects\n(relationship_graph)",  "features"),
    ("f_drishti", "features/drishti\n(graha+rashi drishti matrix)", "features"),
    ("f_lords",   "features/lordships\n(house lords, karakas)", "features"),
    ("f_sandhi",  "features/sandhi\n(cusp zones, madhya)",   "features"),
    ("f_nkf",     "features/nakshatra_f\n(lord,guna,pada)",  "features"),
    ("f_dasha",   "features/dasha_feat\n(mahadasha, antardasha)", "features"),
    ("f_func",    "features/functional\n(benefic/malefic per asc)", "features"),

    # tier 4c — feature sub-modules (group B: 5)
    ("f_varga",   "features/varga_anal\n(D3/D7/D9/D10/D12)", "features"),
    ("f_yogas",   "features/yogas_ext\n(30+ yoga detectors)", "features"),
    ("f_raman",   "features/raman_flow\n(Raman personality)", "features"),
    ("f_hinfl",   "features/house_infl\n(HOUSE_TOPICS, effects)", "features"),
    ("f_transit", "features/transit_f\n(transit over natal)", "features"),

    # tier 5 — core_features + retrieval
    ("f_core",    "features/core_features  ★\nextract_core_features() → dict(50+ keys)", "features"),
    ("r_load",    "retrieval/corpus_loader\n(ingest_corpus, load_manifest)", "retrieval"),
    ("r_chunk",   "retrieval/chunker\n(chunk_corpus_documents, size=600)", "retrieval"),
    ("r_embed",   "retrieval/embedder\n(embed_chunks, MiniLM-384d)", "retrieval"),
    ("r_vstore",  "retrieval/vector_store\n(FAISS IndexFlatIP, cosine)", "retrieval"),
    ("r_retr",    "retrieval/retriever\n(Retriever.retrieve, top-k)", "retrieval"),
    ("r_qexp",    "retrieval/query_expander\n(expand_queries, HyDE)", "retrieval"),

    # tier 6 — LLM layer
    ("l_client",  "llm/local_client\n(Ollama/LMStudio/llama.cpp)", "llm"),
    ("l_prompt",  "llm/prompt_builder\n(build_interpretation_prompt)", "llm"),
    ("l_ftune",   "llm/fine_tune_prep\n(SFT dataset builder)", "llm"),

    # tier 7 — orchestration services
    ("o_evid",    "orchestration/\nevidence_builder\n(build_evidence, scope_report)", "orchestration"),
    ("o_pred",    "orchestration/\nprediction_service\n(load_rules, call_llm)", "orchestration"),
    ("o_time",    "orchestration/\ntiming_service\n(dasha+transit forecast)", "orchestration"),

    # tier 8 — eval + storage + utils
    ("ev_data",   "evaluation/dataset\n(EvaluationCase, load_set)", "evaluation"),
    ("ev_metr",   "evaluation/metrics\n(score_prediction_report)", "evaluation"),
    ("ev_run",    "evaluation/runner\n(run_regression_benchmark)", "evaluation"),
    ("ev_train",  "evaluation/training_data\n(build_sft_examples)", "evaluation"),
    ("s_cache",   "storage/cache\n(SQLite chart_cache.db)", "storage"),
    ("s_repo",    "storage/repository\n(save/load/list reports)", "storage"),
    ("u_repro",   "utils/repro\n(reproducibility manifest)", "utils"),

    # tier 9 — pipeline
    ("o_pipe",    "orchestration/pipeline  ★\nrun_prediction_pipeline()\n9-stage end-to-end", "orchestration"),

    # tier 10 — entry points
    ("a_app",     "api/app\n(create_api_app, FastAPI)", "api"),
    ("a_chart",   "api/routes_chart\nPOST /charts/compute", "api"),
    ("a_predrt",  "api/routes_prediction\nPOST /predictions", "api"),
    ("cli_main",  "cli/main\n(vedic-ai entrypoint)", "cli"),
    ("cli_pred",  "cli/commands_predict\nvedic-ai predict", "cli"),
    ("cli_corp",  "cli/commands_corpus\nvedic-ai build-index", "cli"),
    ("cli_srv",   "cli/commands_serve\nvedic-ai serve", "cli"),
    ("static",    "static/index.html\n(Web UI, 2111 LOC)", "static"),
]

# ── tier float positions (allows fractional tiers for sub-rows) ────────────────
TIER_Y = {
    "d_enums":0,  "d_birth":0,  "d_corpus":0, "c_exc":0,
    "c_rules":0,  "c_log":0,    "l_base":0,   "l_parser":0,

    "d_planet":1, "d_house":1,  "d_nk":1,     "d_dasha":1, "c_cfg":1,

    "d_chart":2,  "d_pred":2,   "c_rload":2,
    "e_dignity":2,"e_varga":2,  "e_vim":2,

    "e_norm":3,   "c_reval":3,  "f_base":3,   "e_base":3,

    "e_swiss":4.0,"e_kery":4.0, "e_reg":4.0,

    "f_strength":5.0,"f_aspects":5.0,"f_drishti":5.0,"f_lords":5.0,
    "f_sandhi":5.0,  "f_nkf":5.0,   "f_dasha":5.0,  "f_func":5.0,

    "f_varga":6.0,"f_yogas":6.0,"f_raman":6.0,"f_hinfl":6.0,"f_transit":6.0,

    "f_core":7,   "r_load":7,   "r_chunk":7,  "r_embed":7,
    "r_vstore":7, "r_retr":7,   "r_qexp":7,

    "l_client":8, "l_prompt":8, "l_ftune":8,

    "o_evid":9,   "o_pred":9,   "o_time":9,

    "ev_data":10, "ev_metr":10, "ev_run":10,  "ev_train":10,
    "s_cache":10, "s_repo":10,  "u_repro":10,

    "o_pipe":11,

    "a_app":12,   "a_chart":12, "a_predrt":12,
    "cli_main":12,"cli_pred":12,"cli_corp":12,"cli_srv":12,"static":12,
}

TIER_LABEL = {
    0:  "TIER 0 — Foundation  (no internal imports)",
    1:  "TIER 1 — Domain primitives + Config",
    2:  "TIER 2 — Complex domain + Engine primitives",
    3:  "TIER 3 — Engine normalizer + Rule evaluator + Feature base",
    4:  "TIER 4a — Engine adapters",
    5:  "TIER 4b — Individual feature modules (group A)",
    6:  "TIER 4c — Individual feature modules (group B)",
    7:  "TIER 5 — Feature orchestrator + Retrieval pipeline",
    8:  "TIER 6 — LLM layer",
    9:  "TIER 7 — Orchestration services",
    10: "TIER 8 — Evaluation · Storage · Utils",
    11: "TIER 9 — Main prediction pipeline",
    12: "TIER 10 — Entry points  (API · CLI · Web UI)",
}

# ── edges ──────────────────────────────────────────────────────────────────────
EDGES = [
    # tier 0 → 1
    ("d_enums","d_planet"),("d_enums","d_house"),("d_enums","d_nk"),("d_enums","d_dasha"),
    ("c_exc","c_cfg"),
    # tier 0/1 → 2
    ("d_planet","d_chart"),("d_house","d_chart"),("d_dasha","d_chart"),
    ("d_birth","d_chart"),("c_exc","d_chart"),
    ("d_chart","d_pred"),
    ("c_exc","c_rload"),("c_rules","c_rload"),("d_enums","c_rload"),
    ("d_enums","e_dignity"),("d_enums","e_varga"),
    ("d_dasha","e_vim"),("d_enums","e_vim"),
    # tier 2/3 → tier 3
    ("d_birth","e_norm"),("d_chart","e_norm"),("d_enums","e_norm"),
    ("d_house","e_norm"),("d_nk","e_norm"),("d_planet","e_norm"),
    ("c_exc","e_norm"),("e_dignity","e_norm"),("e_varga","e_norm"),
    ("d_chart","c_reval"),("d_pred","c_reval"),("c_rules","c_reval"),
    ("d_chart","f_base"),
    ("d_birth","e_base"),("d_chart","e_base"),("d_dasha","e_base"),("e_norm","e_base"),
    # tier 3 → 4a engines
    ("d_birth","e_swiss"),("d_chart","e_swiss"),("d_dasha","e_swiss"),
    ("d_enums","e_swiss"),("c_exc","e_swiss"),("e_norm","e_swiss"),("e_vim","e_swiss"),
    ("d_birth","e_kery"),("d_chart","e_kery"),("d_dasha","e_kery"),("c_exc","e_kery"),
    ("c_cfg","e_reg"),("c_exc","e_reg"),("e_base","e_reg"),("e_kery","e_reg"),("e_swiss","e_reg"),
    # tier 3 → 4b feature group A
    ("d_chart","f_strength"),("d_enums","f_strength"),("e_dignity","f_strength"),("f_base","f_strength"),
    ("d_chart","f_aspects"),("d_enums","f_aspects"),("e_dignity","f_aspects"),
    ("d_chart","f_drishti"),("d_enums","f_drishti"),
    ("d_chart","f_lords"),("d_enums","f_lords"),("f_base","f_lords"),("f_strength","f_lords"),
    ("d_chart","f_sandhi"),("d_enums","f_sandhi"),
    ("d_chart","f_nkf"),("d_enums","f_nkf"),("d_nk","f_nkf"),("e_norm","f_nkf"),
    ("d_chart","f_dasha"),("d_dasha","f_dasha"),("e_vim","f_dasha"),
    ("d_chart","f_func"),("d_enums","f_func"),("e_dignity","f_func"),("f_base","f_func"),
    # tier 3/4b → 4c feature group B
    ("d_chart","f_varga"),("d_enums","f_varga"),("e_dignity","f_varga"),("f_base","f_varga"),
    ("d_chart","f_yogas"),("d_enums","f_yogas"),("e_dignity","f_yogas"),("f_base","f_yogas"),
    ("d_chart","f_raman"),("f_base","f_raman"),
    ("d_chart","f_hinfl"),
    ("d_chart","f_transit"),("d_enums","f_transit"),
    # → tier 5: core_features (collects everything)
    ("d_chart","f_core"),("d_enums","f_core"),("e_dignity","f_core"),
    ("e_norm","f_core"),("e_vim","f_core"),
    ("f_aspects","f_core"),("f_base","f_core"),("f_dasha","f_core"),
    ("f_drishti","f_core"),("f_func","f_core"),("f_hinfl","f_core"),
    ("f_lords","f_core"),("f_nkf","f_core"),("f_raman","f_core"),
    ("f_sandhi","f_core"),("f_strength","f_core"),("f_transit","f_core"),
    ("f_varga","f_core"),("f_yogas","f_core"),
    # → retrieval pipeline
    ("c_exc","r_load"),("d_corpus","r_load"),
    ("d_corpus","r_chunk"),("r_load","r_chunk"),
    ("d_corpus","r_embed"),
    ("d_corpus","r_vstore"),
    ("d_corpus","r_retr"),
    ("d_pred","r_qexp"),
    # → tier 6 LLM
    ("c_exc","l_client"),
    ("d_chart","l_prompt"),("d_corpus","l_prompt"),("d_pred","l_prompt"),
    # → tier 7 orchestration
    ("d_chart","o_evid"),("d_corpus","o_evid"),("d_pred","o_evid"),
    ("c_reval","o_pred"),("c_rload","o_pred"),("c_rules","o_pred"),
    ("d_chart","o_pred"),("d_corpus","o_pred"),("d_pred","o_pred"),
    ("l_parser","o_pred"),("l_prompt","o_pred"),("l_client","o_pred"),
    ("c_reval","o_time"),("c_rload","o_time"),("c_rules","o_time"),
    ("d_birth","o_time"),("d_chart","o_time"),("d_pred","o_time"),
    ("e_base","o_time"),("f_core","o_time"),("f_dasha","o_time"),("f_transit","o_time"),
    # → tier 8 eval+storage
    ("c_exc","ev_data"),("d_pred","ev_data"),
    ("d_pred","ev_metr"),("ev_data","ev_metr"),
    ("d_pred","ev_run"),("ev_data","ev_run"),("ev_metr","ev_run"),
    ("d_pred","ev_train"),("ev_data","ev_train"),
    ("ev_run","l_ftune"),
    ("d_birth","s_cache"),("d_chart","s_cache"),
    ("d_pred","s_repo"),
    ("d_pred","u_repro"),
    # → tier 9 pipeline
    ("d_birth","o_pipe"),("d_pred","o_pipe"),("e_base","o_pipe"),
    ("e_swiss","o_pipe"),("f_core","o_pipe"),("o_evid","o_pipe"),("o_pred","o_pipe"),
    # → tier 10 entry points
    ("c_cfg","a_app"),("a_chart","a_app"),("a_predrt","a_app"),
    ("c_exc","a_chart"),("d_birth","a_chart"),("d_chart","a_chart"),
    ("e_base","a_chart"),("e_swiss","a_chart"),("f_core","a_chart"),
    ("d_birth","a_predrt"),("d_pred","a_predrt"),("o_pipe","a_predrt"),
    ("r_chunk","a_predrt"),("r_load","a_predrt"),("r_retr","a_predrt"),("r_vstore","a_predrt"),
    ("c_cfg","cli_main"),("c_exc","cli_main"),("c_log","cli_main"),
    ("c_cfg","cli_pred"),("c_exc","cli_pred"),("d_birth","cli_pred"),
    ("o_pipe","cli_pred"),("r_chunk","cli_pred"),("r_load","cli_pred"),
    ("r_retr","cli_pred"),("r_vstore","cli_pred"),("s_cache","cli_pred"),("s_repo","cli_pred"),
    ("r_chunk","cli_corp"),("r_load","cli_corp"),("r_embed","cli_corp"),("r_vstore","cli_corp"),
]

# ── layout ─────────────────────────────────────────────────────────────────────
def build_positions():
    from collections import defaultdict
    groups = defaultdict(list)
    node_map = {n[0]: n for n in NODES}
    for nid, _, _ in NODES:
        t = TIER_Y[nid]
        groups[t].append(nid)

    X_SPAN = 70.0
    Y_SCALE = -7.0
    pos = {}
    for t, nids in groups.items():
        n = len(nids)
        xs = np.linspace(-X_SPAN/2, X_SPAN/2, n) if n > 1 else [0.0]
        for i, nid in enumerate(nids):
            pos[nid] = (xs[i], t * Y_SCALE)
    return pos


# ── draw helpers ───────────────────────────────────────────────────────────────
NODE_W, NODE_H = 6.0, 1.9

def draw_node(ax, x, y, label, pkg):
    bg = PKG_COLOR.get(pkg, "#444")
    box = FancyBboxPatch((x - NODE_W/2, y - NODE_H/2), NODE_W, NODE_H,
                         boxstyle="round,pad=0.12",
                         facecolor=bg, edgecolor="#8b949e",
                         linewidth=0.9, alpha=0.95, zorder=3)
    ax.add_patch(box)
    ax.text(x, y, label, ha="center", va="center",
            fontsize=7, color=TEXT, fontweight="bold",
            linespacing=1.35, zorder=4, multialignment="center")


def draw_edge(ax, x0, y0, x1, y1, clr):
    pad = NODE_H / 2 + 0.05
    ax.annotate("",
        xy=(x1, y1 + pad),
        xytext=(x0, y0 - pad),
        arrowprops=dict(
            arrowstyle="-|>",
            color=clr,
            lw=0.9,
            mutation_scale=7,
            connectionstyle="arc3,rad=0.06",
        ),
        zorder=2,
    )


# ── main ────────────────────────────────────────────────────────────────────────
def build_figure():
    node_map = {n[0]: (n[1], n[2]) for n in NODES}
    pos = build_positions()

    fig, ax = plt.subplots(figsize=(72, 105), facecolor=BG)
    ax.set_facecolor(BG)
    ax.axis("off")

    # tier background bands
    Y_SCALE = -7.0
    all_tiers = sorted(set(TIER_Y.values()))
    for t in all_tiers:
        y = t * Y_SCALE
        band_h = abs(Y_SCALE) * 0.88
        rect = plt.Rectangle((-39, y - band_h/2), 78, band_h,
                              facecolor="#161b22", alpha=0.45, zorder=0)
        ax.add_patch(rect)

    # tier labels
    for int_t, label in TIER_LABEL.items():
        # find float tier for this integer
        float_t = int_t if int_t <= 3 else (
            {4:4.0, 5:5.0, 6:6.0, 7:7, 8:8, 9:9, 10:10, 11:11, 12:12}.get(int_t, int_t)
        )
        y = float_t * Y_SCALE
        ax.text(-40, y, label, ha="left", va="center",
                fontsize=9.5, color="#8b949e", fontstyle="italic", zorder=5)

    # edges (behind nodes)
    edge_seen = set()
    for src, dst in EDGES:
        if (src, dst) in edge_seen:
            continue
        edge_seen.add((src, dst))
        x0, y0 = pos[src]
        x1, y1 = pos[dst]
        pkg_dst = node_map[dst][1]
        clr = PKG_COLOR.get(pkg_dst, "#444") + "cc"
        draw_edge(ax, x0, y0, x1, y1, clr)

    # nodes
    for nid, label, pkg in NODES:
        x, y = pos[nid]
        draw_node(ax, x, y, label, pkg)

    # legend
    patches = [
        mpatches.Patch(facecolor=PKG_COLOR[p], edgecolor="#8b949e", lw=0.8, label=p)
        for p in ["domain","core","engines","features","retrieval",
                  "llm","orchestration","evaluation","storage","utils","api","cli","static"]
    ]
    ax.legend(handles=patches, loc="lower right", bbox_to_anchor=(1.0, 0.01),
              facecolor="#161b22", edgecolor="#30363d",
              fontsize=10, title="Package", title_fontsize=11,
              labelcolor=TEXT, ncol=2, framealpha=0.95)

    # title
    ax.set_title(
        "Vedic AI — Complete Module Dependency Flowchart\n"
        "Arrows point from dependencies → dependents  ·  ★ = central hub modules",
        fontsize=18, color=TEXT, pad=18, fontweight="bold"
    )

    xs = [p[0] for p in pos.values()]
    ys = [p[1] for p in pos.values()]
    ax.set_xlim(min(xs) - 44, max(xs) + 8)
    ax.set_ylim(min(ys) - 4, max(ys) + 4)
    return fig


if __name__ == "__main__":
    import os
    out = os.path.join(os.path.dirname(__file__), "..", "docs", "flowchart.png")
    fig = build_figure()
    fig.savefig(out, dpi=150, bbox_inches="tight",
                facecolor=BG, edgecolor="none")
    plt.close(fig)
    print(f"Saved → {os.path.abspath(out)}")
