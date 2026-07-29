"""
AppPulse AZ — Chatbot Streamlit səhifəsi
Söhbət yaddaşı + avtomatik chart
"""

import json
import re
import streamlit as st
import plotly.graph_objects as go
from chatbot.rag import ask

APP_COLORS = {
    "azercell": "#009CDE",
    "bakcell":  "#E2001A",
    "nar":      "#722F8E",
}

SAMPLE_QUESTIONS = [
    {"title": "Lider analizi",      "subtitle": "Hansı şirkət ən yüksək net sentiment-ə malikdir?"},
    {"title": "Kritik problemlər",  "subtitle": "Nar-ın ən böyük 3 problemi nədir?"},
    {"title": "Birbaşa müqayisə",   "subtitle": "Azercell və Bakcell-i hər tərəfdən müqayisə et"},
    {"title": "Tövsiyə",            "subtitle": "Azercell product manager-i hansı 3 şeyi düzəltməlidir?"},
    {"title": "Həftəlik vəziyyət",  "subtitle": "Bu həftə hansı şirkətdə dəyişiklik baş verib?"},
    {"title": "Müsbət siqnallar",   "subtitle": "Müştərilər tətbiqlərin nəyini ən çox tərifləyir?"},
]


def parse_chart(text: str) -> tuple[str, dict | None]:
    """
    Cavab mətndən ```chart ... ``` bloku ayır.
    Qaytarır: (təmiz mətn, chart_data və ya None)
    """
    pattern = r"```chart\s*(\{.*?\})\s*```"
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        return text, None
    try:
        chart_data = json.loads(match.group(1))
        clean_text = text[:match.start()].strip()
        return clean_text, chart_data
    except json.JSONDecodeError:
        return text, None


def render_chart(chart_data: dict):
    """chart_data-dan Plotly bar chart çək."""
    items = chart_data.get("data", [])
    if not items:
        return

    labels = [d["label"] for d in items]
    values = [d["value"] for d in items]
    title  = chart_data.get("title", "")

    # Rəng seç — şirkət adına görə
    colors = []
    for label in labels:
        label_lower = label.lower()
        if "azercell" in label_lower:
            colors.append(APP_COLORS["azercell"])
        elif "bakcell" in label_lower:
            colors.append(APP_COLORS["bakcell"])
        elif "nar" in label_lower:
            colors.append(APP_COLORS["nar"])
        else:
            colors.append("#6366F1")

    fig = go.Figure(go.Bar(
        x=labels,
        y=values,
        marker_color=colors,
        text=[f"{v}" for v in values],
        textposition="outside",
        textfont=dict(size=13, color="white"),
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(size=14, color="#E2E8F0")),
        height=280,
        margin=dict(l=20, r=20, t=40, b=20),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(
            gridcolor="rgba(255,255,255,0.06)",
            color="#8B92A5",
        ),
        xaxis=dict(color="#E2E8F0"),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)


def render_chat_page():
    """Chat səhifəsi — söhbət yaddaşı + chart."""

    st.markdown(
        """
        <div style="margin-bottom: 2rem">
            <h1 style="margin-bottom: 0.4rem">AI Analitika</h1>
            <p style="color: #8B92A5; font-size: 1rem; margin: 0">
                Datayı sualla danışdır — Azərbaycanca, Rusca və ya İngiliscə
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "groq_history" not in st.session_state:
        st.session_state.groq_history = []

    # ── Boş ekran: nümunə suallar ──
    if not st.session_state.messages:
        st.markdown(
            '<p style="color:#8B92A5; font-size:0.85rem; '
            'text-transform:uppercase; letter-spacing:0.06em; '
            'margin-bottom:1rem; font-weight:500">Nümunə suallar</p>',
            unsafe_allow_html=True,
        )
        for row_start in range(0, len(SAMPLE_QUESTIONS), 3):
            cols = st.columns(3)
            for i, sq in enumerate(SAMPLE_QUESTIONS[row_start:row_start + 3]):
                with cols[i]:
                    if st.button(
                        f"**{sq['title']}**\n\n{sq['subtitle']}",
                        key=f"sample_{row_start}_{i}",
                        use_container_width=True,
                    ):
                        _send_message(sq["subtitle"])
                        st.rerun()
        st.markdown("<br>", unsafe_allow_html=True)

    # ── Mesaj tarixçəsi ──
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if msg["role"] == "assistant":
                clean_text, chart_data = parse_chart(msg["content"])
                st.markdown(clean_text)
                if chart_data:
                    render_chart(chart_data)
            else:
                st.markdown(msg["content"])

    # ── Yeni input ──
    if prompt := st.chat_input("Sualını yaz..."):
        _send_message(prompt)
        st.rerun()

    # ── Sidebar ──
    if st.session_state.messages:
        st.sidebar.divider()
        count = len(st.session_state.messages) // 2
        st.sidebar.caption(f"{count} sual verilib")
        if st.sidebar.button("Söhbəti təmizlə", use_container_width=True):
            st.session_state.messages = []
            st.session_state.groq_history = []
            st.rerun()


def _send_message(question: str):
    """Sualı göndər, cavabı al, yaddaşa yaz."""
    st.session_state.messages.append({"role": "user", "content": question})
    with st.spinner("Düşünürəm..."):
        answer = ask(question, history=st.session_state.groq_history)
    st.session_state.messages.append({"role": "assistant", "content": answer})
    st.session_state.groq_history.append({"role": "user", "content": question})
    st.session_state.groq_history.append({"role": "assistant", "content": answer})
