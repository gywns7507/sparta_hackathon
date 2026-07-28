import pathlib
import sys

import streamlit as st

DATA_DIR = pathlib.Path(__file__).parent / "[10] 마케팅 공통" / "data"
DEFAULT_PAST_PATH = DATA_DIR / "past_content_performance.csv"
DEFAULT_NEW_PATH = DATA_DIR / "new_content_info.csv"

SCRIPTS_DIR = pathlib.Path(__file__).parent / "[10] 마케팅 공통" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import pipeline  # noqa: E402
import dashboard_native  # noqa: E402
import reach_analysis  # noqa: E402
import regression_analysis  # noqa: E402
from data_loading import DataValidationError, load_new, load_past  # noqa: E402

st.set_page_config(page_title="콘텐츠 성과 예측 대시보드", layout="wide")

st.title("콘텐츠 성과 예측 대시보드")

with st.expander("데이터 교체 (선택) — 업로드하지 않으면 저장소의 샘플 데이터를 사용합니다"):
    col1, col2 = st.columns(2)
    with col1:
        past_file = st.file_uploader("과거 콘텐츠 성과 데이터 (CSV/Excel)", type=["csv", "xlsx", "xls"], key="past")
    with col2:
        new_file = st.file_uploader("신규 콘텐츠 정보 (CSV/Excel)", type=["csv", "xlsx", "xls"], key="new")
    include_strategy = st.checkbox("전략 기획안 포함 (Challenge)", value=True)
    st.caption(
        "**필수 컬럼**\n\n"
        "- 과거 데이터: `content_id, title, type, topic_category, channel, ctr, "
        "posting_hour, has_emoji, headline_length` (`engagement_rate`·`reach`는 있으면 함께 활용)\n"
        "- 신규 데이터: `title, type, topic_category, channel, posting_hour, has_emoji, headline_length`"
    )

try:
    past_df = load_past(past_file or DEFAULT_PAST_PATH)
    new_df = load_new(new_file or DEFAULT_NEW_PATH)
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
past_name = past_file.name if past_file else DEFAULT_PAST_PATH.name
new_name = new_file.name if new_file else DEFAULT_NEW_PATH.name

st.caption(f"현재 데이터: 학습 {past_name}({len(clean)}건) · 진단 {new_name}({len(new_df)}건)"
           + ("" if past_file and new_file else " — 샘플 데이터"))

results = [pipeline.diagnose_one(clean, row) for _, row in new_df.iterrows()]
candidates = pipeline.detect_strategic_candidates(clean) if include_strategy else None
reach_result = reach_analysis.compute(clean)
regression_result = regression_analysis.compute(clean)

tab_names = ["개요", "신규 콘텐츠 진단", "reach 분석", "다변량 회귀분석"]
if include_strategy:
    tab_names.append("발행 전략 기획안")
tabs = st.tabs(tab_names)

with tabs[0]:
    dashboard_native.render_overview(clean, new_df, regression_result, include_strategy)
with tabs[1]:
    dashboard_native.render_diagnosis(results)
with tabs[2]:
    dashboard_native.render_reach(reach_result)
with tabs[3]:
    dashboard_native.render_regression(regression_result)
if include_strategy:
    with tabs[4]:
        dashboard_native.render_strategy(candidates)
