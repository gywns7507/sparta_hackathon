import pathlib

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="콘텐츠 성과 예측 리포트", layout="wide")

html_path = pathlib.Path(__file__).parent / "sample-final.html"
html = html_path.read_text(encoding="utf-8")

# Korean content triggers browser auto-translate, which mutates the DOM Streamlit's
# own React shell manages and crashes it (streamlit/streamlit#7745). Mark the parent
# page notranslate too, not just this iframe's document.
notranslate_patch = """
<script>
try {
  const doc = window.parent.document;
  doc.documentElement.setAttribute("translate", "no");
  if (!doc.querySelector('meta[name="google"]')) {
    const meta = doc.createElement("meta");
    meta.name = "google";
    meta.content = "notranslate";
    doc.head.appendChild(meta);
  }
} catch (e) {}
</script>
"""

components.html(html + notranslate_patch, height=1000, scrolling=True)
