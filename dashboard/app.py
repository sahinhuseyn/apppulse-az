"""
AppPulse AZ — Streamlit Dashboard (polished)
İşə salmaq: streamlit run dashboard/app.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from queries import (
    load_overview,
    load_sentiment_distribution,
    load_topic_breakdown,
    load_rating_distribution,
    load_timeline,
    load_anomalies,
    load_reviews_filtered,
    load_topics_list,
)
from config.apps import APPS
from chat_page import render_chat_page


# ═════════ Konfiqurasiya ═════════
st.set_page_config(
    page_title="AppPulse AZ",
    page_icon="📊",
    layout="wide",
)

# Brend rəngləri (rəsmi)
APP_COLORS = {
    "azercell": "#009CDE",   # Azercell mavisi
    "bakcell":  "#E2001A",   # Bakcell qırmızısı
    "nar":      "#722F8E",   # Nar bənövşəyisi
}

SENTIMENT_COLORS = {
    "positive": "#16A34A",
    "neutral":  "#9CA3AF",
    "negative": "#DC2626",
}


def display_name(app_key: str) -> str:
    return APPS.get(app_key, {}).get("display_name", app_key)


def color_map_named() -> dict:
    """Plotly üçün: display_name → brend rəngi."""
    return {display_name(k): v for k, v in APP_COLORS.items()}


# ═════════ Sidebar ═════════
st.sidebar.title("AppPulse AZ")
st.sidebar.caption("Customer feedback intelligence")

page = st.sidebar.radio(
    "",
    ["Insights", "Overview", "Comparison", "Reviews", "AI Chat"],
    label_visibility="collapsed",
)

st.sidebar.divider()
st.sidebar.caption("Source: Google Play Store")
st.sidebar.caption("Languages: AZ · RU · EN")


# ═════════ CSS polish — Modern Dark UI ═════════
st.markdown("""
<style>
    /* ────── Global ────── */
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(180deg, #0E1117 0%, #131720 100%);
    }

    [data-testid="stHeader"] {
        background: transparent;
    }

    /* ────── Tipoqrafiya ────── */
    h1 {
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
        background: linear-gradient(135deg, #FFFFFF 0%, #B0B7C3 100%);
        -webkit-background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
        background-clip: text !important;
    }

    h2, h3 {
        font-weight: 600 !important;
        letter-spacing: -0.01em !important;
    }

    /* ────── Sidebar — modern look ────── */
    [data-testid="stSidebar"] {
        background: #0a0d12 !important;
        border-right: 1px solid rgba(255,255,255,0.06);
    }

    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h1 {
        font-size: 1.4rem !important;
    }

    /* Sidebar radio buttons → modern nav style */
    [data-testid="stSidebar"] [role="radiogroup"] {
        gap: 4px !important;
    }

    [data-testid="stSidebar"] [role="radiogroup"] label {
        background: transparent;
        padding: 10px 12px !important;
        border-radius: 8px !important;
        transition: all 0.15s ease;
        cursor: pointer;
        margin: 0 !important;
    }

    [data-testid="stSidebar"] [role="radiogroup"] label:hover {
        background: rgba(255,255,255,0.04);
    }

    [data-testid="stSidebar"] [role="radiogroup"] label[data-checked="true"] {
        background: rgba(99, 102, 241, 0.15);
        border-left: 2px solid #6366F1;
    }

    /* ────── KPI metric kartları ────── */
    [data-testid="stMetric"] {
        background: rgba(255,255,255,0.025);
        border: 1px solid rgba(255,255,255,0.06);
        padding: 16px 18px !important;
        border-radius: 12px !important;
        backdrop-filter: blur(8px);
        transition: all 0.2s ease;
    }

    [data-testid="stMetric"]:hover {
        background: rgba(255,255,255,0.04);
        border-color: rgba(255,255,255,0.1);
        transform: translateY(-1px);
    }

    [data-testid="stMetricLabel"] {
        font-size: 0.78rem !important;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #8B92A5 !important;
        font-weight: 500 !important;
    }

    [data-testid="stMetricValue"] {
        font-size: 1.85rem !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em;
    }

    /* ────── Konteynerlər (border=True) ────── */
    [data-testid="stContainer"][data-borderless="false"] {
        background: rgba(255,255,255,0.02) !important;
        border: 1px solid rgba(255,255,255,0.06) !important;
        border-radius: 12px !important;
        transition: all 0.15s ease;
    }

    [data-testid="stContainer"][data-borderless="false"]:hover {
        background: rgba(255,255,255,0.035) !important;
        border-color: rgba(255,255,255,0.1) !important;
    }

    /* ────── Selectbox / inputlar ────── */
    [data-baseweb="select"] > div {
        background: rgba(255,255,255,0.03) !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
        border-radius: 8px !important;
    }

    [data-testid="stTextInput"] input,
    [data-testid="stChatInput"] textarea {
        background: rgba(255,255,255,0.03) !important;
        border: 1px solid rgba(255,255,255,0.08) !important;
        border-radius: 8px !important;
    }

    /* ────── Buttons ────── */
    [data-testid="stButton"] button {
        background: rgba(99,102,241,0.1) !important;
        border: 1px solid rgba(99,102,241,0.25) !important;
        border-radius: 8px !important;
        color: #C7D2FE !important;
        font-weight: 500 !important;
        transition: all 0.15s ease;
    }

    [data-testid="stButton"] button:hover {
        background: rgba(99,102,241,0.18) !important;
        border-color: rgba(99,102,241,0.4) !important;
        transform: translateY(-1px);
    }

    /* ────── Chat mesajları ────── */
    [data-testid="stChatMessage"] {
        background: rgba(255,255,255,0.025) !important;
        border: 1px solid rgba(255,255,255,0.06) !important;
        border-radius: 12px !important;
        padding: 16px !important;
        margin-bottom: 12px;
    }

    /* User mesajı vurğusu */
    [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
        background: rgba(99,102,241,0.06) !important;
        border-color: rgba(99,102,241,0.15) !important;
    }

    /* ────── Insight kartları ────── */
    .big-metric {
        font-size: 3rem;
        font-weight: 700;
        line-height: 1;
        letter-spacing: -0.03em;
    }
    .metric-label {
        font-size: 0.78rem;
        color: #8B92A5;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-bottom: 0.6rem;
        font-weight: 500;
    }
    .insight-card {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.06);
        border-left: 3px solid #F59E0B;
        padding: 14px 18px;
        border-radius: 10px;
        margin-bottom: 10px;
        transition: all 0.15s ease;
    }
    .insight-card:hover {
        background: rgba(255,255,255,0.05);
        transform: translateX(2px);
    }

    /* ────── Scrollbar ────── */
    ::-webkit-scrollbar { width: 8px; height: 8px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb {
        background: rgba(255,255,255,0.1);
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.2); }

    /* ────── Divider ────── */
    hr {
        border-color: rgba(255,255,255,0.06) !important;
        margin: 1.5rem 0 !important;
    }

    /* ────── Caption ────── */
    [data-testid="stCaptionContainer"] {
        color: #8B92A5 !important;
    }
</style>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════
#  SƏHİFƏ: INSIGHTS (NEW — əsas səhifə)
# ════════════════════════════════════════════════════════
if page == "Insights":
    st.title("🎯 Əsas Insight-lər")
    st.caption("Bu həftənin ən vacib tapıntıları")

    overview = load_overview()
    overview["net_sentiment"] = overview["positive_pct"] - overview["negative_pct"]
    overview = overview.sort_values("net_sentiment", ascending=False)

    # ─── Lider göstəricisi ───
    leader = overview.iloc[0]
    loser  = overview.iloc[-1]

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown('<div class="metric-label">🏆 LİDER</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="big-metric" style="color:{APP_COLORS[leader["app_key"]]}">'
            f'{display_name(leader["app_key"])}</div>',
            unsafe_allow_html=True,
        )
        st.caption(f"Net sentiment: **+{leader['net_sentiment']:.1f}%**")

    with col2:
        st.markdown('<div class="metric-label">⚠️ DİQQƏT</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="big-metric" style="color:{APP_COLORS[loser["app_key"]]}">'
            f'{display_name(loser["app_key"])}</div>',
            unsafe_allow_html=True,
        )
        st.caption(f"Net sentiment: **{loser['net_sentiment']:+.1f}%**")

    with col3:
        st.markdown('<div class="metric-label">📝 CƏMİ RƏY</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="big-metric">{overview["total_reviews"].sum():,}</div>',
            unsafe_allow_html=True,
        )
        st.caption(f"Son analiz: bu gün")

    st.divider()

    # ─── Net Sentiment sıralaması ───
    st.subheader("📊 Net Sentiment sıralaması")
    st.caption("Müsbət % − Mənfi % · Yüksək rəqəm = daha məmnun müştərilər")

    overview_sorted = overview.sort_values("net_sentiment", ascending=True)
    overview_sorted["app_name"] = overview_sorted["app_key"].apply(display_name)
    overview_sorted["label"] = overview_sorted["net_sentiment"].apply(lambda x: f"{x:+.1f}%")

    fig = go.Figure(go.Bar(
        x=overview_sorted["net_sentiment"],
        y=overview_sorted["app_name"],
        orientation="h",
        text=overview_sorted["label"],
        textposition="outside",
        textfont=dict(size=16, color="white"),
        marker_color=[APP_COLORS[k] for k in overview_sorted["app_key"]],
        hovertemplate="<b>%{y}</b><br>Net Sentiment: %{x:+.1f}%<extra></extra>",
    ))
    fig.update_layout(
        xaxis_title="Net Sentiment (%)",
        height=280,
        margin=dict(l=20, r=60, t=20, b=40),
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)",
    )
    fig.add_vline(x=0, line_dash="dash", line_color="gray", line_width=1)
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ─── Anomaly alerts ───
    st.subheader("🚨 Anomaly Aşkarlaması")
    st.caption("Normaldan xeyli çox rəy gələn günlər — nəsə baş verib")

    anomalies = load_anomalies(days=30, threshold=2.0)

    if anomalies.empty:
        st.success("✅ Son 30 gündə heç bir anomaliya yoxdur.")
    else:
        for _, row in anomalies.head(5).iterrows():
            app_name = display_name(row["app_key"])
            color = APP_COLORS[row["app_key"]]
            st.markdown(
                f'''<div class="insight-card" style="border-left-color:{color}">
                    <strong style="color:{color}">{app_name}</strong> · {row["day"]}<br>
                    <span style="font-size:1.1rem">
                        <strong>{row["total"]} rəy</strong> gəldi
                        (gündəlik orta: {row["avg_daily"]})
                        — <strong>{row["spike_ratio"]}x spike!</strong>
                    </span>
                </div>''',
                unsafe_allow_html=True,
            )

    st.divider()

    # ─── Ən problemli mövzular ───
    st.subheader("🔥 Ən çox şikayət olunan mövzular")
    topic_df = load_topic_breakdown()

    if not topic_df.empty:
        totals = topic_df.groupby("topic")["complaints"].sum().reset_index()
        totals = totals.sort_values("complaints", ascending=False).head(3)

        cols = st.columns(len(totals))
        for i, row in totals.iterrows():
            idx = list(totals.index).index(i)
            with cols[idx]:
                st.markdown(f'<div class="metric-label">#{idx+1}</div>', unsafe_allow_html=True)
                st.markdown(
                    f'<div style="font-size:1.3rem;font-weight:600;margin-bottom:0.5rem">'
                    f'{row["topic"]}</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<div style="font-size:2rem;color:#DC2626;font-weight:700">'
                    f'{row["complaints"]}</div>',
                    unsafe_allow_html=True,
                )
                st.caption("şikayət (hər 3 şirkətdə cəmi)")


# ════════════════════════════════════════════════════════
#  SƏHİFƏ: OVERVIEW
# ════════════════════════════════════════════════════════
elif page == "Overview":
    st.title("📈 Overview")
    st.caption("Hər üç tətbiq üzrə müştəri məmnuniyyətinin ümumi vəziyyəti")

    df = load_overview()

    # KPI kartları
    cols = st.columns(len(df))
    for i, row in df.iterrows():
        with cols[i]:
            name  = display_name(row["app_key"])
            color = APP_COLORS[row["app_key"]]

            st.markdown(
                f'<div style="border-left:4px solid {color};padding-left:1rem;margin-bottom:1rem">'
                f'<div style="font-size:1.3rem;font-weight:600">{name}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            st.metric("Ümumi rəy", f"{row['total_reviews']:,}")
            st.metric("Orta reytinq", f"⭐ {row['avg_rating']}")

            pos = row["positive_pct"] or 0
            neg = row["negative_pct"] or 0
            net = pos - neg

            st.metric("Müsbət", f"{pos}%")
            st.metric("Mənfi", f"{neg}%", delta=f"{net:+.1f}% net", delta_color="normal")
            st.metric("Şikayət sayı", f"{row['complaints']:,}")

    st.divider()

    # Ulduz paylanması
    st.subheader("⭐ Ulduz paylanması")
    rating_df = load_rating_distribution()
    rating_df["app_name"] = rating_df["app_key"].apply(display_name)

    fig = px.bar(
        rating_df,
        x="count",
        y="rating",
        color="app_name",
        orientation="h",
        barmode="group",
        color_discrete_map=color_map_named(),
        labels={"count": "Rəy sayı", "rating": "Ulduz", "app_name": "Tətbiq"},
        height=400,
    )
    fig.update_layout(yaxis={"tickmode": "linear"}, plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)

    # Timeline
    st.subheader("📅 Son 30 günün trendi")
    timeline_df = load_timeline(days=30)

    if not timeline_df.empty:
        timeline_df["app_name"] = timeline_df["app_key"].apply(display_name)
        fig = px.line(
            timeline_df,
            x="day",
            y="total",
            color="app_name",
            color_discrete_map=color_map_named(),
            labels={"day": "Tarix", "total": "Gündəlik rəy", "app_name": "Tətbiq"},
            height=350,
            markers=True,
        )
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Son 30 gündə data yoxdur.")


# ════════════════════════════════════════════════════════
#  SƏHİFƏ: RƏQABƏT MÜQAYİSƏSİ
# ════════════════════════════════════════════════════════
elif page == "Comparison":
    st.title("⚔️ Rəqabət Müqayisəsi")
    st.caption("Azercell vs Bakcell vs Nar — birbaşa müqayisə")

    st.subheader("🎯 Sentiment paylanması")
    sent_df = load_sentiment_distribution()
    sent_df["app_name"] = sent_df["app_key"].apply(display_name)

    totals = sent_df.groupby("app_name")["count"].sum().reset_index()
    totals.columns = ["app_name", "total"]
    sent_df = sent_df.merge(totals, on="app_name")
    sent_df["percent"] = (sent_df["count"] / sent_df["total"] * 100).round(1)

    fig = px.bar(
        sent_df,
        x="app_name",
        y="percent",
        color="sentiment",
        color_discrete_map=SENTIMENT_COLORS,
        labels={"app_name": "Tətbiq", "percent": "Faiz (%)", "sentiment": "Sentiment"},
        text="percent",
        height=400,
    )
    fig.update_traces(texttemplate="%{text}%", textposition="inside")
    fig.update_layout(barmode="stack", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    st.subheader("🏷️ Ən çox şikayət mövzuları")
    st.caption("Hansı şirkətin hansı problemi daha böyükdür?")

    topic_df = load_topic_breakdown()
    if not topic_df.empty:
        topic_df["app_name"] = topic_df["app_key"].apply(display_name)
        fig = px.bar(
            topic_df,
            x="complaints",
            y="topic",
            color="app_name",
            barmode="group",
            orientation="h",
            color_discrete_map=color_map_named(),
            labels={"complaints": "Şikayət sayı", "topic": "Mövzu", "app_name": "Tətbiq"},
            height=450,
        )
        fig.update_layout(plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    st.subheader("📊 Net Sentiment sıralaması")
    overview = load_overview()
    overview["net_sentiment"] = overview["positive_pct"] - overview["negative_pct"]
    overview = overview.sort_values("net_sentiment", ascending=True)
    overview["app_name"] = overview["app_key"].apply(display_name)

    fig = go.Figure(go.Bar(
        x=overview["net_sentiment"],
        y=overview["app_name"],
        orientation="h",
        text=overview["net_sentiment"].apply(lambda x: f"{x:+.1f}%"),
        textposition="outside",
        marker_color=[APP_COLORS[k] for k in overview["app_key"]],
    ))
    fig.update_layout(
        xaxis_title="Net Sentiment (%)",
        height=300,
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)",
    )
    fig.add_vline(x=0, line_dash="dash", line_color="gray", line_width=1)
    st.plotly_chart(fig, use_container_width=True)


# ════════════════════════════════════════════════════════
#  SƏHİFƏ: RƏY EXPLORER
# ════════════════════════════════════════════════════════
elif page == "Reviews":
    st.title("💬 Rəy Explorer")
    st.caption("Filtrlər vasitəsilə konkret rəyləri tap və oxu")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        app_filter = st.selectbox("Tətbiq:", ["Hamısı"] + [display_name(k) for k in APPS])
    with col2:
        sent_filter = st.selectbox("Sentiment:", ["Hamısı", "positive", "negative", "neutral"])
    with col3:
        topic_filter = st.selectbox("Mövzu:", ["Hamısı"] + load_topics_list())
    with col4:
        lang_filter = st.selectbox("Dil:", ["Hamısı", "az", "ru", "en"])

    reverse_map = {display_name(k): k for k in APPS}
    app_key = reverse_map.get(app_filter, "Hamısı")

    df = load_reviews_filtered(
        app_key=app_key,
        sentiment=sent_filter,
        topic=topic_filter,
        language=lang_filter,
        limit=200,
    )

    st.caption(f"**{len(df)} rəy tapıldı**")

    for _, r in df.iterrows():
        sentiment = r.get("sentiment") or "neutral"
        s_color   = SENTIMENT_COLORS.get(sentiment, "#9CA3AF")
        app_color = APP_COLORS.get(r["app_key"], "#9CA3AF")

        emoji = "😊" if sentiment == "positive" else "😞" if sentiment == "negative" else "😐"
        stars = "⭐" * int(r["rating"])

        with st.container(border=True):
            cols = st.columns([3, 1])
            with cols[0]:
                st.markdown(
                    f'<span style="color:{app_color};font-weight:600">'
                    f'{display_name(r["app_key"])}</span>'
                    f' · {stars}'
                    f' · <span style="color:{s_color}">{emoji} {sentiment}</span>'
                    f' · <code>{r["language"]}</code>'
                    + (f' · 🏷️ {r["topic"]}' if r.get("topic") else ""),
                    unsafe_allow_html=True,
                )
                st.write(r["content"])
            with cols[1]:
                st.caption(f"📅 {r['reviewed_at'].strftime('%Y-%m-%d')}")
                if r.get("thumbs_up", 0) > 0:
                    st.caption(f"👍 {r['thumbs_up']}")
                if r.get("is_complaint"):
                    st.caption("🚨 Şikayət")


# ════════════════════════════════════════════════════════
#  PAGE: AI CHAT
# ════════════════════════════════════════════════════════
elif page == "AI Chat":
    render_chat_page()
