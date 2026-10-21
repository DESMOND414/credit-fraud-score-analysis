"""
Build interactive dashboard & high-resolution static visualisations for
Credit Fraud Trends & Credit Score Analysis.

Generates:
1. dashboard/interactive_dashboard.html (Self-contained interactive Power BI-style web report)
2. dashboard/images/executive_dashboard_overview.png (Full 4-panel executive dashboard view)
3. dashboard/images/geographic_fraud_heatmap.png (Geographic fraud hotspot & regional matrix)
4. dashboard/images/timeseries_fraud_trends.png (Time-series fraud trend & exposure velocity)
5. dashboard/images/utilisation_vs_delinquency.png (Credit utilisation vs. delinquency risk segmentation)
"""

from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib_cache")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

ROOT = Path(__file__).resolve().parents[1]
PROC_DIR = ROOT / "data" / "processed"
DASH_DIR = ROOT / "dashboard"
IMG_DIR = DASH_DIR / "images"

# Dark Executive FinTech Theme Palette
BG_DARK = "#0b1120"
PANEL_BG = "#131c31"
BORDER_CLR = "#1e293b"
TEXT_MAIN = "#f8fafc"
TEXT_MUTED = "#94a3b8"
TIER_COLORS = {
    "Low Risk": "#10b981",     # Emerald Green
    "Medium Risk": "#f59e0b",  # Amber Gold
    "High Risk": "#ef4444",    # Crimson Red
}
ACCENT_CYAN = "#06b6d4"
ACCENT_PURPLE = "#8b5cf6"


def style_ax(ax: plt.Axes, title: str, xlabel: str = "", ylabel: str = "") -> None:
    ax.set_facecolor(PANEL_BG)
    ax.set_title(title, color=TEXT_MAIN, fontsize=12.5, fontweight="bold", loc="left", pad=12)
    if xlabel:
        ax.set_xlabel(xlabel, color=TEXT_MUTED, fontsize=10, labelpad=6)
    if ylabel:
        ax.set_ylabel(ylabel, color=TEXT_MUTED, fontsize=10, labelpad=6)
    ax.tick_params(colors=TEXT_MUTED, labelsize=9)
    for spine in ax.spines.values():
        spine.set_color(BORDER_CLR)
        spine.set_linewidth(1.1)
    ax.grid(True, linestyle="--", alpha=0.22, color=TEXT_MUTED)


def plot_utilisation_vs_delinquency(cust_df: pd.DataFrame) -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6.2), facecolor=BG_DARK, gridspec_kw={"width_ratios": [1.45, 1]})
    fig.subplots_adjust(wspace=0.24, top=0.84, bottom=0.13, left=0.06, right=0.96)

    fig.suptitle(
        "CREDIT UTILISATION VS. DELINQUENCY & REPAYMENT RISK SEGMENTATION",
        color=TEXT_MAIN, fontsize=15, fontweight="bold", x=0.06, ha="left", y=0.95
    )

    # Sample for crisp scatter plot rendering
    sample_df = cust_df.sample(min(1800, len(cust_df)), random_state=42)
    for tier in ["Low Risk", "Medium Risk", "High Risk"]:
        sub = sample_df[sample_df["credit_risk_tier"] == tier]
        sizes = np.clip(sub["monthly_spend_avg_gbp"] / 14.0, 22, 160)
        ax1.scatter(
            sub["credit_utilisation_pct"],
            sub["delinquency_rate_pct"],
            s=sizes,
            c=TIER_COLORS[tier],
            alpha=0.68,
            edgecolors="white",
            linewidths=0.35,
            label=f"{tier} (n={len(cust_df[cust_df['credit_risk_tier']==tier]):,})",
        )

    # Threshold guidelines
    ax1.axvline(75.0, color="#ef4444", linestyle="--", linewidth=1.2, alpha=0.8)
    ax1.axvline(38.0, color="#f59e0b", linestyle=":", linewidth=1.2, alpha=0.8)
    ax1.axhline(10.0, color="#ef4444", linestyle="--", linewidth=1.2, alpha=0.8)
    ax1.text(76.5, 23.5, "High Util Threshold (75%)", color="#fca5a5", fontsize=8.5, fontweight="bold")
    ax1.text(3.0, 10.7, "Severe Delinquency Threshold (10%)", color="#fca5a5", fontsize=8.5, fontweight="bold")

    style_ax(
        ax1,
        "Credit Utilisation (%) vs. Delinquency Rate (%) by Risk Tier",
        xlabel="Credit Utilisation Ratio (%)",
        ylabel="Delinquency Rate (% of Payment Cycles)",
    )
    ax1.xaxis.set_major_formatter(mtick.PercentFormatter())
    ax1.yaxis.set_major_formatter(mtick.PercentFormatter())
    leg = ax1.legend(frameon=True, facecolor=BG_DARK, edgecolor=BORDER_CLR, fontsize=9, loc="upper left")
    for text in leg.get_texts():
        text.set_color(TEXT_MAIN)

    # Right panel: Credit Score & Fraud Incidence by Risk Tier
    tier_order = ["Low Risk", "Medium Risk", "High Risk"]
    tier_stats = (
        cust_df.groupby("credit_risk_tier")
        .agg(
            avg_score=("credit_score", "mean"),
            avg_util=("credit_utilisation_pct", "mean"),
            avg_delinq=("delinquency_rate_pct", "mean"),
            fraud_rate=("customer_fraud_rate_pct", "mean"),
            loc_cons=("location_consistency_score", "mean"),
        )
        .reindex(tier_order)
    )

    x = np.arange(len(tier_order))
    width = 0.25
    b1 = ax2.bar(x - width, tier_stats["avg_util"], width, label="Avg Utilisation (%)", color=ACCENT_CYAN)
    b2 = ax2.bar(x, tier_stats["avg_delinq"] * 4.0, width, label="Delinquency Rate (x4 scaled)", color="#f59e0b")
    b3 = ax2.bar(x + width, tier_stats["fraud_rate"] * 10.0, width, label="Fraud Rate % (x10 scaled)", color="#ef4444")

    style_ax(ax2, "Behavioural Risk & Fraud Metrics Across Credit Tiers", xlabel="Customer Credit Risk Segment", ylabel="Normalized Metric Scale")
    ax2.set_xticks(x)
    ax2.set_xticklabels([f"{t}\n(Avg Score: {int(tier_stats.loc[t, 'avg_score'])})" for t in tier_order], color=TEXT_MAIN, fontweight="bold")

    for bars, mult, suffix in [(b1, 1.0, "%"), (b2, 0.25, "%"), (b3, 0.10, "%")]:
        for bar in bars:
            h = bar.get_height()
            ax2.text(
                bar.get_x() + bar.get_width() / 2.0,
                h + 1.2,
                f"{h * mult:.1f}{suffix}",
                ha="center", va="bottom", color=TEXT_MAIN, fontsize=8, fontweight="bold"
            )

    leg2 = ax2.legend(frameon=True, facecolor=BG_DARK, edgecolor=BORDER_CLR, fontsize=8.5, loc="upper left")
    for text in leg2.get_texts():
        text.set_color(TEXT_MAIN)

    fig.savefig(IMG_DIR / "utilisation_vs_delinquency.png", dpi=200)
    plt.close(fig)


def plot_geographic_fraud_heatmap(geo_df: pd.DataFrame, cust_df: pd.DataFrame) -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16.5, 6.8), facecolor=BG_DARK, gridspec_kw={"width_ratios": [1.0, 1.35]})
    fig.subplots_adjust(wspace=0.46, top=0.84, bottom=0.12, left=0.05, right=0.96)

    fig.suptitle(
        "GEOGRAPHIC FRAUD HEATMAP & LOCATION CONSISTENCY ANALYSIS (UK CITIES)",
        color=TEXT_MAIN, fontsize=15, fontweight="bold", x=0.05, ha="left", y=0.95
    )

    # Left: UK Spatial Coordinate Bubble Heatmap
    sc = ax1.scatter(
        geo_df["lon"],
        geo_df["lat"],
        s=np.clip(geo_df["fraud_exposure_gbp"] / 190.0, 85, 880),
        c=geo_df["fraud_rate_pct"],
        cmap="YlOrRd",
        alpha=0.88,
        edgecolors="white",
        linewidths=1.2,
        zorder=4,
    )
    # Custom non-overlapping label offsets for top hubs
    label_offsets = {
        "London": (10, -6),
        "Manchester": (-68, 12),
        "Birmingham": (10, -10),
        "Leeds": (10, 8),
        "Glasgow": (-62, -6),
        "Edinburgh": (10, 8),
        "Bristol": (10, -12),
        "Cardiff": (-58, 8),
        "Belfast": (10, 6),
        "Newcastle": (10, 6),
    }
    for _, row in geo_df.iterrows():
        city = row["merchant_city"]
        if city in label_offsets:
            dx, dy = label_offsets[city]
            ax1.annotate(
                f"{city} (£{row['fraud_exposure_gbp']/1000:.0f}k)",
                (row["lon"], row["lat"]),
                xytext=(dx, dy),
                textcoords="offset points",
                color=TEXT_MAIN,
                fontsize=7.8,
                fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.18", fc=BG_DARK, ec=BORDER_CLR, alpha=0.82),
            )

    style_ax(
        ax1,
        "Spatial Fraud Hotspot Map (Size = Fraud £, Color = Rate %)",
        xlabel="Longitude (°W / °E)",
        ylabel="Latitude (°N)",
    )
    ax1.set_xlim(-7.2, 2.0)
    ax1.set_ylim(50.2, 56.7)
    cbar = fig.colorbar(sc, ax=ax1, fraction=0.040, pad=0.02)
    cbar.ax.yaxis.set_tick_params(color=TEXT_MUTED, labelcolor=TEXT_MUTED, labelsize=8)
    cbar.set_label("Fraud Rate (%)", color=TEXT_MUTED, fontsize=8.5)

    # Right: Regional Fraud Exposure & Distance Anomaly Horizontal Bar Chart
    top_cities = geo_df.sort_values("fraud_exposure_gbp", ascending=True).tail(12)
    y_pos = np.arange(len(top_cities))
    bars = ax2.barh(
        y_pos,
        top_cities["fraud_exposure_gbp"] / 1000.0,
        color=plt.cm.YlOrRd(np.linspace(0.35, 0.92, len(top_cities))),
        edgecolor="white",
        linewidth=0.4,
        height=0.68,
    )
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(
        [f"{r['merchant_city']} ({r['merchant_region']})" for _, r in top_cities.iterrows()],
        color=TEXT_MAIN, fontsize=8.5, fontweight="bold"
    )
    style_ax(
        ax2,
        "Top UK Cities by Gross Fraud Exposure (£K) & Distance Anomaly",
        xlabel="Gross Fraud Exposure (£ Thousands)",
    )
    for bar, (_, r) in zip(bars, top_cities.iterrows()):
        w = bar.get_width()
        ax2.text(
            w + 3.0,
            bar.get_y() + bar.get_height() / 2.0,
            f"£{w:.1f}k ({r['fraud_rate_pct']:.1f}% | {r['avg_distance_km']:.0f}km)",
            va="center", ha="left", color=TEXT_MAIN, fontsize=8, fontweight="bold"
        )
    ax2.set_xlim(0, top_cities["fraud_exposure_gbp"].max() / 1000.0 * 1.36)

    fig.savefig(IMG_DIR / "geographic_fraud_heatmap.png", dpi=200)
    plt.close(fig)


def plot_timeseries_fraud_trends(monthly_df: pd.DataFrame) -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5.8), facecolor=BG_DARK, gridspec_kw={"width_ratios": [1.3, 1.1]})
    fig.subplots_adjust(wspace=0.24, top=0.83, bottom=0.15, left=0.06, right=0.96)

    fig.suptitle(
        "TIME-SERIES FRAUD TREND VELOCITY & MONTHLY LOSS RECOVERY",
        color=TEXT_MAIN, fontsize=15, fontweight="bold", x=0.06, ha="left", y=0.95
    )

    # Pivot by month and risk tier
    piv = monthly_df.pivot(index="year_month", columns="credit_risk_tier", values="fraud_rate_pct").fillna(0)
    months = piv.index.tolist()
    x = np.arange(len(months))

    for tier in ["High Risk", "Medium Risk", "Low Risk"]:
        if tier in piv.columns:
            ax1.plot(
                x, piv[tier], marker="o", linewidth=2.5, markersize=6,
                color=TIER_COLORS[tier], label=f"{tier} Tier Fraud Rate (%)"
            )
            ax1.fill_between(x, piv[tier], alpha=0.10, color=TIER_COLORS[tier])

    style_ax(
        ax1,
        "Monthly Fraud Incidence Rate (%) by Customer Credit Risk Tier",
        xlabel="Transaction Month (2025)",
        ylabel="Fraud Rate (% of Transactions)",
    )
    ax1.set_xticks(x)
    ax1.set_xticklabels(months, rotation=30, ha="right", color=TEXT_MUTED)
    ax1.yaxis.set_major_formatter(mtick.PercentFormatter())
    leg1 = ax1.legend(frameon=True, facecolor=BG_DARK, edgecolor=BORDER_CLR, fontsize=9, loc="upper left")
    for text in leg1.get_texts():
        text.set_color(TEXT_MAIN)

    # Right: Monthly Gross Fraud Exposure vs Confirmed Net Loss (Auto-Blocked Savings)
    m_tot = (
        monthly_df.groupby("year_month", as_index=False)
        .agg(
            gross=("fraud_exposure_gbp", "sum"),
            net_loss=("confirmed_loss_gbp", "sum"),
            fraud_cnt=("fraud_transactions", "sum"),
        )
        .sort_values("year_month")
    )

    ax2.bar(x - 0.18, m_tot["gross"] / 1000.0, width=0.35, color="#ef4444", label="Gross Fraud Exposure (£K)")
    ax2.bar(x + 0.18, m_tot["net_loss"] / 1000.0, width=0.35, color="#f59e0b", label="Confirmed Net Loss (£K)")
    ax2.plot(x, (m_tot["gross"] - m_tot["net_loss"]) / 1000.0, color="#10b981", marker="s", linewidth=2.2, label="Prevented / Auto-Blocked (£K)")

    style_ax(
        ax2,
        "Monthly Gross Fraud Exposure vs. Prevented Savings (£K)",
        xlabel="Transaction Month (2025)",
        ylabel="Amount (£ Thousands)",
    )
    ax2.set_xticks(x)
    ax2.set_xticklabels(months, rotation=30, ha="right", color=TEXT_MUTED)
    leg2 = ax2.legend(frameon=True, facecolor=BG_DARK, edgecolor=BORDER_CLR, fontsize=8.5, loc="upper left")
    for text in leg2.get_texts():
        text.set_color(TEXT_MAIN)

    fig.savefig(IMG_DIR / "timeseries_fraud_trends.png", dpi=200)
    plt.close(fig)


def plot_executive_dashboard_overview(
    cust_df: pd.DataFrame, geo_df: pd.DataFrame, monthly_df: pd.DataFrame, kpis: dict
) -> None:
    fig = plt.figure(figsize=(16, 10), facecolor=BG_DARK)
    gs = fig.add_gridspec(3, 4, height_ratios=[0.32, 1.0, 1.0], hspace=0.46, wspace=0.28, left=0.07, right=0.97, top=0.90, bottom=0.07)

    fig.suptitle(
        "CREDIT FRAUD TRENDS & CREDIT SCORE ANALYSIS — POWER BI EXECUTIVE MONITOR",
        color=TEXT_MAIN, fontsize=16, fontweight="bold", x=0.05, ha="left", y=0.96
    )

    # Top row: 4 KPI Cards
    kpi_specs = [
        ("TOTAL CARD SPEND ANALYSED", f"£{kpis['total_spend_gbp']/1e6:.2f}M", f"{kpis['total_transactions']:,} Txns | {kpis['total_customers']:,} Accounts", ACCENT_CYAN),
        ("GROSS FRAUD EXPOSURE", f"£{kpis['gross_fraud_exposure_gbp']/1e3:.1f}K", f"{kpis['total_fraud_txns']:,} Fraud Events ({kpis['overall_fraud_rate_pct']:.2f}%)", "#ef4444"),
        ("PORTFOLIO AVG CREDIT SCORE", f"{kpis['avg_credit_score']:.0f} / 850", f"Avg Utilisation: {kpis['avg_utilisation_pct']:.1f}%", "#10b981"),
        ("HIGH RISK TIER ACCOUNTS", f"{kpis['risk_tier_distribution'].get('High Risk', 0):,}", f"Avg Delinquency: {kpis['avg_delinquency_rate_pct']:.2f}% | Loc Score: {kpis['avg_location_consistency']:.1f}", "#f59e0b"),
    ]
    for idx, (label, val, sub, clr) in enumerate(kpi_specs):
        ax_k = fig.add_subplot(gs[0, idx])
        ax_k.set_facecolor(PANEL_BG)
        ax_k.set_xticks([])
        ax_k.set_yticks([])
        for spine in ax_k.spines.values():
            spine.set_color(clr)
            spine.set_linewidth(1.8)
        ax_k.text(0.06, 0.72, label, color=TEXT_MUTED, fontsize=8.5, fontweight="bold")
        ax_k.text(0.06, 0.34, val, color=clr, fontsize=18, fontweight="bold")
        ax_k.text(0.06, 0.10, sub, color=TEXT_MAIN, fontsize=8)

    # Panel 1 (Middle Left): Credit Utilisation vs Delinquency Scatter
    ax_p1 = fig.add_subplot(gs[1, :2])
    sample_df = cust_df.sample(min(1400, len(cust_df)), random_state=42)
    for tier in ["Low Risk", "Medium Risk", "High Risk"]:
        sub = sample_df[sample_df["credit_risk_tier"] == tier]
        ax_p1.scatter(
            sub["credit_utilisation_pct"], sub["delinquency_rate_pct"],
            s=36, c=TIER_COLORS[tier], alpha=0.65, label=tier
        )
    style_ax(ax_p1, "1. Credit Utilisation (%) vs. Delinquency Rate (%) by Risk Tier", "Credit Utilisation (%)", "Delinquency Rate (%)")
    leg = ax_p1.legend(frameon=True, facecolor=BG_DARK, edgecolor=BORDER_CLR, fontsize=8.5)
    for t in leg.get_texts():
        t.set_color(TEXT_MAIN)

    # Panel 2 (Middle Right): Time-Series Fraud Trend
    ax_p2 = fig.add_subplot(gs[1, 2:])
    piv = monthly_df.pivot(index="year_month", columns="credit_risk_tier", values="fraud_exposure_gbp").fillna(0) / 1000.0
    x = np.arange(len(piv.index))
    bottom = np.zeros(len(piv.index))
    for tier in ["Low Risk", "Medium Risk", "High Risk"]:
        if tier in piv.columns:
            vals = piv[tier].values
            ax_p2.bar(x, vals, bottom=bottom, color=TIER_COLORS[tier], label=tier, width=0.62)
            bottom += vals
    style_ax(ax_p2, "2. Monthly Fraud Exposure (£K) Stacked by Credit Risk Tier", "Month (2025)", "Fraud Exposure (£K)")
    ax_p2.set_xticks(x)
    ax_p2.set_xticklabels(piv.index, rotation=25, ha="right", fontsize=8)
    leg2 = ax_p2.legend(frameon=True, facecolor=BG_DARK, edgecolor=BORDER_CLR, fontsize=8.5)
    for t in leg2.get_texts():
        t.set_color(TEXT_MAIN)

    # Panel 3 (Bottom Left): Top UK Cities Geographic Fraud Heatmap
    ax_p3 = fig.add_subplot(gs[2, :2])
    top_geo = geo_df.sort_values("fraud_exposure_gbp", ascending=True).tail(8)
    y_g = np.arange(len(top_geo))
    ax_p3.barh(y_g, top_geo["fraud_exposure_gbp"] / 1000.0, color="#ef4444", alpha=0.85, height=0.62)
    ax_p3.set_yticks(y_g)
    ax_p3.set_yticklabels(top_geo["merchant_city"], color=TEXT_MAIN, fontsize=8.5, fontweight="bold")
    style_ax(ax_p3, "3. Geographic Fraud Hotspots — Top UK Cities (£K Exposure)", "Gross Fraud Exposure (£K)")

    # Panel 4 (Bottom Right): Credit Score Distribution & Location Consistency by Risk Tier
    ax_p4 = fig.add_subplot(gs[2, 2:])
    for tier in ["Low Risk", "Medium Risk", "High Risk"]:
        sub = cust_df[cust_df["credit_risk_tier"] == tier]
        ax_p4.hist(sub["credit_score"], bins=24, alpha=0.65, color=TIER_COLORS[tier], label=f"{tier} (Mean: {sub['credit_score'].mean():.0f})")
    style_ax(ax_p4, "4. Customer Credit Score Distribution Across Risk Segments", "Credit Score (300–850)", "Customer Count")
    leg4 = ax_p4.legend(frameon=True, facecolor=BG_DARK, edgecolor=BORDER_CLR, fontsize=8.5)
    for t in leg4.get_texts():
        t.set_color(TEXT_MAIN)

    fig.savefig(IMG_DIR / "executive_dashboard_overview.png", dpi=200)
    plt.close(fig)


def build_interactive_html(
    cust_df: pd.DataFrame, geo_df: pd.DataFrame, monthly_df: pd.DataFrame, kpis: dict
) -> None:
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            "Geographic Fraud Exposure & Rate by UK City",
            "Monthly Fraud Exposure (£) by Customer Credit Risk Tier",
            "Credit Utilisation (%) vs. Delinquency Rate (%) Segmentation",
            "Customer Credit Score Distribution by Risk Tier",
        ),
        specs=[[{"type": "scattergeo"}, {"type": "xy"}], [{"type": "xy"}, {"type": "xy"}]],
        vertical_spacing=0.14,
        horizontal_spacing=0.10,
    )

    # 1. Geo Map
    fig.add_trace(
        go.Scattergeo(
            lat=geo_df["lat"],
            lon=geo_df["lon"],
            text=geo_df.apply(
                lambda r: f"<b>{r['merchant_city']} ({r['merchant_region']})</b><br>"
                          f"Fraud Exposure: £{r['fraud_exposure_gbp']:,.0f}<br>"
                          f"Fraud Rate: {r['fraud_rate_pct']:.2f}%<br>"
                          f"Avg Distance from Home: {r['avg_distance_km']:.1f} km",
                axis=1,
            ),
            hoverinfo="text",
            mode="markers+text",
            textposition="top center",
            marker=dict(
                size=np.clip(geo_df["fraud_exposure_gbp"] / 1600.0, 10, 38),
                color=geo_df["fraud_rate_pct"],
                colorscale="YlOrRd",
                showscale=True,
                colorbar=dict(title="Fraud %", len=0.4, y=0.8),
                line=dict(width=1, color="white"),
            ),
            name="UK Cities",
        ),
        row=1, col=1,
    )
    fig.update_geos(
        scope="europe",
        center=dict(lat=53.5, lon=-2.2),
        projection_scale=6.2,
        bgcolor=PANEL_BG,
        landcolor="#1e293b",
        coastlinecolor="#475569",
        showcountries=True,
    )

    # 2. Time-series stacked bar
    for tier in ["Low Risk", "Medium Risk", "High Risk"]:
        sub = monthly_df[monthly_df["credit_risk_tier"] == tier].sort_values("year_month")
        fig.add_trace(
            go.Bar(
                x=sub["year_month"],
                y=sub["fraud_exposure_gbp"],
                name=f"{tier} Exposure (£)",
                marker_color=TIER_COLORS[tier],
            ),
            row=1, col=2,
        )

    # 3. Credit Utilisation vs Delinquency Scatter
    sample_df = cust_df.sample(min(1500, len(cust_df)), random_state=42)
    for tier in ["Low Risk", "Medium Risk", "High Risk"]:
        sub = sample_df[sample_df["credit_risk_tier"] == tier]
        fig.add_trace(
            go.Scatter(
                x=sub["credit_utilisation_pct"],
                y=sub["delinquency_rate_pct"],
                mode="markers",
                name=f"{tier} Customers",
                marker=dict(color=TIER_COLORS[tier], size=7, opacity=0.7),
                text=sub.apply(
                    lambda r: f"Customer: {r['customer_id']}<br>Score: {r['credit_score']}<br>"
                              f"Loc Consistency: {r['location_consistency_score']}%",
                    axis=1,
                ),
                hoverinfo="text+x+y",
            ),
            row=2, col=1,
        )

    # 4. Credit Score Box/Histogram
    for tier in ["Low Risk", "Medium Risk", "High Risk"]:
        sub = cust_df[cust_df["credit_risk_tier"] == tier]
        fig.add_trace(
            go.Histogram(
                x=sub["credit_score"],
                name=f"{tier} Score Dist",
                marker_color=TIER_COLORS[tier],
                opacity=0.7,
            ),
            row=2, col=2,
        )

    fig.update_layout(
        title="Credit Fraud Trends & Credit Score Analysis — Interactive Power BI Companion Dashboard",
        template="plotly_dark",
        paper_bgcolor=BG_DARK,
        plot_bgcolor=PANEL_BG,
        barmode="stack",
        height=920,
        margin=dict(t=80, l=50, r=50, b=50),
    )

    DASH_DIR.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(DASH_DIR / "interactive_dashboard.html"), include_plotlyjs="cdn")
    print(f"[Dashboard] Saved interactive HTML to {DASH_DIR / 'interactive_dashboard.html'}")


def main() -> None:
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    cust_df = pd.read_csv(PROC_DIR / "customer_risk_profiles.csv")
    geo_df = pd.read_csv(PROC_DIR / "geographic_fraud_summary.csv")
    monthly_df = pd.read_csv(PROC_DIR / "monthly_fraud_trends.csv")
    kpis = json.loads((PROC_DIR / "pipeline_kpi_summary.json").read_text())

    plot_utilisation_vs_delinquency(cust_df)
    plot_geographic_fraud_heatmap(geo_df, cust_df)
    plot_timeseries_fraud_trends(monthly_df)
    plot_executive_dashboard_overview(cust_df, geo_df, monthly_df, kpis)
    build_interactive_html(cust_df, geo_df, monthly_df, kpis)
    print("[Charts] Generated all 4 high-resolution PNG dashboard views in dashboard/images/")


if __name__ == "__main__":
    main()
