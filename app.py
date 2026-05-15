# Streamlit 러브버그 조기경보 시스템 진입점.

import streamlit as st

from lovebug_alert.ui.state_loader import load_app_state
from lovebug_alert.ui.official import render_official_view
from lovebug_alert.ui.citizen import render_citizen_view

st.set_page_config(
    page_title="러브버그 조기경보 시스템",
    page_icon="🐛",
    layout="wide",
)

col_logo, col_toggle = st.columns([5, 1])
with col_logo:
    st.title("🐛 러브버그 조기경보 시스템")
with col_toggle:
    is_official = st.toggle("담당자 뷰", value=True)

app_state = load_app_state()

if is_official:
    render_official_view(app_state)
else:
    render_citizen_view(app_state)
