import pathlib
import sys

import streamlit as st
import streamlit.components.v1 as components

SCRIPTS_DIR = pathlib.Path(__file__).parent / "[10] 마케팅 공통" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import pipeline  # noqa: E402
import dashboard_html  # noqa: E402
from data_loading import DataValidationError, load_new, load_past  # noqa: E402

st.set_page_config(page_title="콘텐츠 성과 예측 리포트", layout="wide")

st.title("콘텐츠 성과 예측 대시보드")
st.caption(
    "과거 콘텐츠 성과 데이터와 신규 콘텐츠 정보를 업로드하면 scripts/pipeline.py의 "
    "유사도 매칭·CTR 범위·개선 제안 로직으로 대시보드를 즉시 생성합니다."
)

with st.sidebar:
    st.header("데이터 업로드")
    past_file = st.file_uploader("과거 콘텐츠 성과 데이터 (CSV/Excel)", type=["csv", "xlsx", "xls"], key="past")
    new_file = st.file_uploader("신규 콘텐츠 정보 (CSV/Excel)", type=["csv", "xlsx", "xls"], key="new")
    include_strategy = st.checkbox("전략 기획안 포함 (Challenge)", value=True)
    st.markdown("---")
    st.markdown(
        "**필수 컬럼**\n\n"
        "- 과거 데이터: `content_id, title, type, topic_category, channel, ctr, "
        "posting_hour, has_emoji, headline_length` (`engagement_rate`는 있으면 함께 표시)\n"
        "- 신규 데이터: `title, type, topic_category, channel, posting_hour, has_emoji, headline_length`"
    )

if not past_file or not new_file:
    st.info("왼쪽 사이드바에서 과거 성과 데이터와 신규 콘텐츠 데이터를 모두 업로드하면 대시보드가 표시됩니다.")
    st.stop()

try:
    past_df = load_past(past_file)
    new_df = load_new(new_file)
except DataValidationError as e:
    st.error(str(e))
    st.stop()

if past_df.empty:
    st.error("과거 성과 데이터가 비어 있습니다.")
    st.stop()
if new_df.empty:
    st.error("신규 콘텐츠 데이터가 비어 있습니다.")
    st.stop()

clean = past_df.drop_duplicates(subset="content_id", keep="first").copy()

results = [pipeline.diagnose_one(clean, row) for _, row in new_df.iterrows()]
candidates = pipeline.detect_strategic_candidates(clean) if include_strategy else None

html_doc = dashboard_html.render_dashboard_html(
    clean,
    new_df,
    results,
    candidates=candidates,
    past_filename=past_file.name,
    new_filename=new_file.name,
)

components.html(html_doc, height=1400, scrolling=True)
