import pathlib

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="콘텐츠 성과 예측 리포트", layout="wide")

html_path = pathlib.Path(__file__).parent / "output" / "sample-final.html"
html = html_path.read_text(encoding="utf-8")

components.html(html, height=1000, scrolling=True)
