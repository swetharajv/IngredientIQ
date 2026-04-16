import streamlit as st
import requests
import plotly.express as px
from collections import Counter
import json
from datetime import datetime

st.set_page_config(
    page_title="IngredientIQ",
    page_icon="",
    layout="wide"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    
    .main { background: #0a0a0f; }
    
    .hero {
        text-align: center;
        padding: 3rem 0 2rem 0;
        border-bottom: 1px solid #1e1e2e;
        margin-bottom: 2rem;
    }
    .hero h1 {
        font-size: 3.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #a78bfa, #60a5fa, #34d399);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .hero p {
        color: #6b7280;
        font-size: 1rem;
        letter-spacing: 0.15em;
        text-transform: uppercase;
    }
    
    .badge-allowed {
        background: #064e3b; color: #34d399;
        padding: 4px 12px; border-radius: 20px;
        font-size: 0.8rem; font-weight: 600;
        border: 1px solid #34d399;
    }
    .badge-restricted {
        background: #451a03; color: #fb923c;
        padding: 4px 12px; border-radius: 20px;
        font-size: 0.8rem; font-weight: 600;
        border: 1px solid #fb923c;
    }
    .badge-banned {
        background: #450a0a; color: #f87171;
        padding: 4px 12px; border-radius: 20px;
        font-size: 0.8rem; font-weight: 600;
        border: 1px solid #f87171;
    }
    .badge-unknown {
        background: #1f2937; color: #9ca3af;
        padding: 4px 12px; border-radius: 20px;
        font-size: 0.8rem; font-weight: 600;
        border: 1px solid #374151;
    }
    
    .verdict-safe {
        background: linear-gradient(135deg, #064e3b, #065f46);
        border: 1px solid #34d399; border-radius: 12px;
        padding: 1.2rem 1.5rem; margin: 1rem 0;
        color: #34d399; font-weight: 600; font-size: 1.1rem;
    }
    .verdict-caution {
        background: linear-gradient(135deg, #451a03, #78350f);
        border: 1px solid #fb923c; border-radius: 12px;
        padding: 1.2rem 1.5rem; margin: 1rem 0;
        color: #fb923c; font-weight: 600; font-size: 1.1rem;
    }
    .verdict-danger {
        background: linear-gradient(135deg, #450a0a, #7f1d1d);
        border: 1px solid #f87171; border-radius: 12px;
        padding: 1.2rem 1.5rem; margin: 1rem 0;
        color: #f87171; font-weight: 600; font-size: 1.1rem;
    }
    
    .insight-card {
        background: #111827; border: 1px solid #1f2937;
        border-radius: 10px; padding: 1rem 1.2rem;
        margin: 0.5rem 0; color: #d1d5db;
        border-left: 3px solid #a78bfa;
    }
    
    .metric-card {
        background: #111827; border: 1px solid #1f2937;
        border-radius: 12px; padding: 1.2rem;
        text-align: center;
    }
    .metric-value {
        font-size: 1.8rem; font-weight: 700;
        color: #a78bfa; margin: 0.3rem 0;
    }
    .metric-label {
        font-size: 0.75rem; color: #6b7280;
        text-transform: uppercase; letter-spacing: 0.1em;
    }
    
    .section-header {
        color: #e5e7eb; font-size: 1rem;
        font-weight: 600; text-transform: uppercase;
        letter-spacing: 0.1em; margin: 1.5rem 0 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid #1f2937;
    }
    
    .cta-box {
        background: linear-gradient(135deg, #1e1b4b, #1e3a5f);
        border: 1px solid #3730a3; border-radius: 16px;
        padding: 2rem; text-align: center; margin-top: 3rem;
    }
    .cta-box h3 { color: #a78bfa; font-size: 1.3rem; margin-bottom: 0.5rem; }
    .cta-box p { color: #9ca3af; margin-bottom: 1rem; }
    .cta-email {
        background: #a78bfa; color: #0a0a0f;
        padding: 0.6rem 1.5rem; border-radius: 8px;
        font-weight: 600; text-decoration: none;
        display: inline-block;
    }
    
    .ingredient-header {
        background: #111827; border: 1px solid #1f2937;
        border-radius: 12px; padding: 1.5rem;
        margin: 1.5rem 0 1rem 0;
    }
    
    .stTextInput > div > div > input {
        background: #111827 !important;
        border: 1px solid #374151 !important;
        color: #e5e7eb !important;
        border-radius: 10px !important;
        font-size: 1rem !important;
        padding: 0.75rem 1rem !important;
    }
    
    div[data-testid="stMetricValue"] { color: #a78bfa !important; }
    
    .stSpinner { color: #a78bfa !important; }
    
    footer { display: none; }
    #MainMenu { display: none; }
    header { display: none; }
</style>
""", unsafe_allow_html=True)


# ── FUNCTIONS ────────────────────────────────────────────────────────────────

def get_fda_total(ingredient):
    try:
        url = "https://api.fda.gov/drug/event.json"
        params = {"search": f"patient.drug.medicinalproduct:{ingredient}", "limit": 1}
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            return r.json()["meta"]["results"]["total"]
    except:
        pass
    return 0

def get_top_reactions(ingredient):
    try:
        url = "https://api.fda.gov/drug/event.json"
        params = {"search": f"patient.drug.medicinalproduct:{ingredient}", "limit": 100}
        r = requests.get(url, params=params, timeout=10)
        if r.status_code != 200:
            return []
        reactions = []
        for report in r.json()["results"]:
            for reaction in report["patient"]["reaction"]:
                reactions.append(reaction["reactionmeddrapt"])
        return reactions
    except:
        return []

def risk_score(total):
    if total > 1000000: return 2, "Very High Risk", "danger"
    elif total > 100000: return 4, "High Risk", "caution"
    elif total > 10000: return 6, "Moderate Risk", "caution"
    else: return 8, "Low Risk", "safe"

def marketability_score(fda_total):
    if fda_total > 1000000: return 3
    elif fda_total > 100000: return 5
    elif fda_total > 10000: return 7
    else: return 9

def get_verdict(score, level):
    if level == "danger":
        return "danger", "Not suitable for general formulation without expert review"
    elif score <= 4:
        return "caution", "High caution required — consult regulatory specialist"
    elif score <= 6:
        return "caution", "Regulatory review recommended before use"
    else:
        return "safe", "Generally safer candidate for formulation"

def get_insights(ingredient, total, reactions):
    insights = []
    if total > 1000000:
        insights.append(f"{ingredient.title()} appears in over 1 million FDA reports — this warrants careful formulation consideration.")
    elif total > 100000:
        insights.append(f"{ingredient.title()} has a high FDA report volume. Check concentration guidelines before use.")
    else:
        insights.append(f"{ingredient.title()} has relatively low FDA adverse event reports, suggesting general tolerability.")
    
    if reactions:
        top = Counter(reactions).most_common(1)[0][0]
        insights.append(f"Most frequently reported reaction: {top}. Consider patch testing guidance in product labeling.")
    
    skincare_actives = ["retinol", "vitamin c", "aha", "bha", "glycolic", "salicylic", "benzoyl"]
    if any(a in ingredient.lower() for a in skincare_actives):
        insights.append(f"Active ingredient detected. Concentration and pH management are critical for safety and efficacy.")
    
    return insights

def analyze_product(ingredients_list):
    results = []
    for ing in ingredients_list:
        ing = ing.strip()
        if not ing:
            continue
        total = get_fda_total(ing)
        score, level_label, level = risk_score(total)
        results.append({
            "ingredient": ing,
            "total": total,
            "score": score,
            "level": level,
            "level_label": level_label
        })
    return results


# ── HERO ─────────────────────────────────────────────────────────────────────

st.markdown("""
<div class="hero">
    <h1>IngredientIQ</h1>
    <p>Regulatory Risk &nbsp;•&nbsp; Safety Signals &nbsp;•&nbsp; Market Intelligence</p>
</div>
""", unsafe_allow_html=True)


# ── MODE SELECT ──────────────────────────────────────────────────────────────

mode = st.radio(
    "Analysis Mode",
    ["Single Ingredient", "Compare Ingredients", "Full Product Analysis"],
    horizontal=True,
    label_visibility="collapsed"
)

st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# MODE 1: SINGLE INGREDIENT
# ══════════════════════════════════════════════════════════════════════════════

if mode == "Single Ingredient":
    ingredient = st.text_input(
        "", placeholder="Enter an ingredient — e.g. retinol, niacinamide, salicylic acid",
        label_visibility="collapsed"
    )

    if ingredient:
        with st.spinner(f"Analysing {ingredient}..."):
            total = get_fda_total(ingredient)
            reactions = get_top_reactions(ingredient)

        if total == 0:
            st.warning("No FDA data found. Try checking the spelling.")
        else:
            score, level_label, level = risk_score(total)
            market = marketability_score(total)
            verdict_level, verdict_text = get_verdict(score, level)
            insights = get_insights(ingredient, total, reactions)

            st.markdown(f"""
            <div class="ingredient-header">
                <span style="color:#6b7280;font-size:0.8rem;text-transform:uppercase;letter-spacing:0.1em">Analysing</span>
                <h2 style="color:#e5e7eb;margin:0.3rem 0 0 0;font-size:1.8rem">{ingredient.title()}</h2>
            </div>
            """, unsafe_allow_html=True)

            # 4 metrics
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.markdown(f"""<div class="metric-card">
                    <div class="metric-label">Regulatory Status</div>
                    <div class="metric-value" style="font-size:1rem;margin-top:0.5rem">
                        <span class="badge-unknown">FDA Monitored</span>
                    </div></div>""", unsafe_allow_html=True)
            with c2:
                color = "#f87171" if score <= 4 else "#fb923c" if score <= 6 else "#34d399"
                st.markdown(f"""<div class="metric-card">
                    <div class="metric-label">Risk Score</div>
                    <div class="metric-value" style="color:{color}">{score}/10</div>
                    <div style="color:#6b7280;font-size:0.75rem">{level_label}</div>
                    </div>""", unsafe_allow_html=True)
            with c3:
                st.markdown(f"""<div class="metric-card">
                    <div class="metric-label">Marketability</div>
                    <div class="metric-value">{market}/10</div>
                    </div>""", unsafe_allow_html=True)
            with c4:
                st.markdown(f"""<div class="metric-card">
                    <div class="metric-label">FDA Reports</div>
                    <div class="metric-value">{total:,}</div>
                    </div>""", unsafe_allow_html=True)

            st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

            # Verdict
            st.markdown('<div class="section-header">Final Verdict</div>', unsafe_allow_html=True)
            if verdict_level == "safe":
                st.markdown(f'<div class="verdict-safe">Generally safer candidate for formulation</div>', unsafe_allow_html=True)
            elif verdict_level == "caution":
                st.markdown(f'<div class="verdict-caution">{verdict_text}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="verdict-danger">{verdict_text}</div>', unsafe_allow_html=True)

            # Insights
            st.markdown('<div class="section-header">Key Insights</div>', unsafe_allow_html=True)
            for insight in insights:
                st.markdown(f'<div class="insight-card">{insight}</div>', unsafe_allow_html=True)

            # Chart
            if reactions:
                st.markdown('<div class="section-header">Top Reported Reactions (FDA)</div>', unsafe_allow_html=True)
                counts = Counter(reactions)
                top10 = counts.most_common(10)
                labels = [r[0] for r in top10]
                values = [r[1] for r in top10]
                fig = px.bar(x=values, y=labels, orientation="h",
                            labels={"x": "Reports", "y": ""},
                            title="")
                fig.update_traces(marker_color="#a78bfa")
                fig.update_layout(
                    height=320, paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#9ca3af"),
                    xaxis=dict(gridcolor="#1f2937"),
                    yaxis=dict(autorange="reversed", gridcolor="rgba(0,0,0,0)"),
                    showlegend=False, margin=dict(l=0, r=0, t=10, b=0)
                )
                st.plotly_chart(fig, use_container_width=True)

            # Export
            st.markdown('<div class="section-header">Export Report</div>', unsafe_allow_html=True)
            report = {
                "ingredient": ingredient,
                "fda_reports": total,
                "risk_score": score,
                "marketability_score": market,
                "verdict": verdict_text,
                "insights": insights,
                "top_reactions": [r[0] for r in Counter(reactions).most_common(5)] if reactions else [],
                "generated": datetime.now().strftime("%Y-%m-%d %H:%M")
            }
            st.download_button(
                label="Download Full Report (JSON)",
                data=json.dumps(report, indent=2),
                file_name=f"ingredientiq_{ingredient.lower().replace(' ','_')}.json",
                mime="application/json"
            )


# ══════════════════════════════════════════════════════════════════════════════
# MODE 2: COMPARE
# ══════════════════════════════════════════════════════════════════════════════

elif mode == "Compare Ingredients":
    col1, col2, col3 = st.columns(3)
    with col1:
        i1 = st.text_input("Ingredient 1", placeholder="retinol")
    with col2:
        i2 = st.text_input("Ingredient 2", placeholder="niacinamide")
    with col3:
        i3 = st.text_input("Ingredient 3", placeholder="salicylic acid")

    ingredients = [i for i in [i1, i2, i3] if i]

    if ingredients:
        with st.spinner("Comparing ingredients..."):
            data = []
            for ing in ingredients:
                total = get_fda_total(ing)
                score, level_label, level = risk_score(total)
                data.append({"Ingredient": ing.title(), "FDA Reports": total,
                            "Risk Score": score, "Level": level_label})

        st.markdown('<div class="section-header">Comparison Results</div>', unsafe_allow_html=True)

        cols = st.columns(len(data))
        for i, (col, d) in enumerate(zip(cols, data)):
            with col:
                color = "#f87171" if d["Risk Score"] <= 4 else "#fb923c" if d["Risk Score"] <= 6 else "#34d399"
                st.markdown(f"""<div class="metric-card">
                    <div style="color:#e5e7eb;font-size:1.1rem;font-weight:600;margin-bottom:0.8rem">{d['Ingredient']}</div>
                    <div class="metric-value" style="color:{color}">{d['Risk Score']}/10</div>
                    <div style="color:#6b7280;font-size:0.8rem;margin-bottom:0.5rem">{d['Level']}</div>
                    <div style="color:#9ca3af;font-size:0.85rem">{d['FDA Reports']:,} FDA reports</div>
                    </div>""", unsafe_allow_html=True)

        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        fig = px.bar(
            x=[d["Ingredient"] for d in data],
            y=[d["Risk Score"] for d in data],
            labels={"x": "", "y": "Risk Score"},
            title="Risk Score Comparison"
        )
        fig.update_traces(marker_color=["#f87171" if d["Risk Score"] <= 4 else "#fb923c" if d["Risk Score"] <= 6 else "#a78bfa" for d in data])
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#9ca3af"), yaxis=dict(range=[0, 10], gridcolor="#1f2937"),
            xaxis=dict(gridcolor="rgba(0,0,0,0)"),
            height=300, margin=dict(l=0, r=0, t=40, b=0)
        )
        st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# MODE 3: FULL PRODUCT ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

elif mode == "Full Product Analysis":
    st.markdown('<p style="color:#6b7280">Paste your full ingredient list, separated by commas</p>', unsafe_allow_html=True)
    product_input = st.text_area(
        "", height=120,
        placeholder="e.g. retinol, niacinamide, salicylic acid, hyaluronic acid, fragrance",
        label_visibility="collapsed"
    )

    if st.button("Analyse Product", type="primary") and product_input:
        ingredients_list = [i.strip() for i in product_input.split(",") if i.strip()]

        with st.spinner(f"Analysing {len(ingredients_list)} ingredients..."):
            results = analyze_product(ingredients_list)

        if results:
            danger_count = sum(1 for r in results if r["level"] == "danger")
            caution_count = sum(1 for r in results if r["level"] == "caution")
            safe_count = sum(1 for r in results if r["level"] == "safe")
            avg_score = sum(r["score"] for r in results) / len(results)

            # Product metrics
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.markdown(f"""<div class="metric-card">
                    <div class="metric-label">Total Ingredients</div>
                    <div class="metric-value">{len(results)}</div></div>""", unsafe_allow_html=True)
            with c2:
                st.markdown(f"""<div class="metric-card">
                    <div class="metric-label">High Risk</div>
                    <div class="metric-value" style="color:#f87171">{danger_count}</div></div>""", unsafe_allow_html=True)
            with c3:
                st.markdown(f"""<div class="metric-card">
                    <div class="metric-label">Caution</div>
                    <div class="metric-value" style="color:#fb923c">{caution_count}</div></div>""", unsafe_allow_html=True)
            with c4:
                color = "#f87171" if avg_score <= 4 else "#fb923c" if avg_score <= 6 else "#34d399"
                st.markdown(f"""<div class="metric-card">
                    <div class="metric-label">Avg Risk Score</div>
                    <div class="metric-value" style="color:{color}">{avg_score:.1f}/10</div></div>""", unsafe_allow_html=True)

            st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

            # Product verdict
            st.markdown('<div class="section-header">Product Verdict</div>', unsafe_allow_html=True)
            if danger_count > 0:
                st.markdown(f'<div class="verdict-danger">High-risk ingredients detected ({danger_count} flagged). Expert regulatory review required before formulation.</div>', unsafe_allow_html=True)
            elif caution_count > len(results) * 0.3:
                st.markdown(f'<div class="verdict-caution">Multiple ingredients require caution. Regulatory review recommended before launch.</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="verdict-safe">Product formulation appears generally low-risk. Standard safety testing recommended.</div>', unsafe_allow_html=True)

            # Fragrance + actives check
            has_fragrance = any("fragrance" in r["ingredient"].lower() or "parfum" in r["ingredient"].lower() for r in results)
            has_active = any(any(a in r["ingredient"].lower() for a in ["retinol", "acid", "benzoyl"]) for r in results)
            if has_fragrance and has_active:
                st.markdown('<div class="insight-card">Fragrance + active ingredients detected. High irritation potential — consider fragrance-free formulation.</div>', unsafe_allow_html=True)

            # Per ingredient breakdown
            st.markdown('<div class="section-header">Ingredient Breakdown</div>', unsafe_allow_html=True)
            for r in results:
                color = "#f87171" if r["level"] == "danger" else "#fb923c" if r["level"] == "caution" else "#34d399"
                st.markdown(f"""
                <div style="display:flex;justify-content:space-between;align-items:center;
                    background:#111827;border:1px solid #1f2937;border-radius:8px;
                    padding:0.8rem 1rem;margin:0.3rem 0;border-left:3px solid {color}">
                    <span style="color:#e5e7eb;font-weight:500">{r['ingredient'].title()}</span>
                    <span style="color:{color};font-weight:600">{r['score']}/10 — {r['level_label']}</span>
                </div>""", unsafe_allow_html=True)

            # Export
            st.markdown('<div class="section-header">Export Report</div>', unsafe_allow_html=True)
            report = {
                "product_analysis": {
                    "total_ingredients": len(results),
                    "high_risk_count": danger_count,
                    "caution_count": caution_count,
                    "average_risk_score": round(avg_score, 1),
                    "ingredients": results,
                    "generated": datetime.now().strftime("%Y-%m-%d %H:%M")
                }
            }
            st.download_button(
                label="Download Full Product Report (JSON)",
                data=json.dumps(report, indent=2),
                file_name="ingredientiq_product_report.json",
                mime="application/json"
            )


# ── CTA ──────────────────────────────────────────────────────────────────────

st.markdown("""
<div class="cta-box">
    <h3>Want a Full Ingredient Audit?</h3>
    <p>Get a complete compliance, risk, and marketability report for your product formulation.</p>
    <a class="cta-email" href="mailto:swetharaj@clinicaldataintelligence.uk">
        Get a Professional Audit
    </a>
    <p style="margin-top:1rem;font-size:0.8rem;color:#4b5563">swetharaj@clinicaldataintelligence.uk</p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div style="text-align:center;padding:2rem 0 1rem;color:#374151;font-size:0.75rem">
    Data: FDA FAERS via openFDA API &nbsp;•&nbsp; For informational purposes only &nbsp;•&nbsp; 
    Built by <a href="https://clinicaldataintelligence.uk" style="color:#6b7280">Clinical Data Intelligence</a>
</div>
""", unsafe_allow_html=True)
