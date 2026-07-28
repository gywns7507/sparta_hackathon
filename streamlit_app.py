import pathlib
import sys

import streamlit as st
import streamlit.components.v1 as components

DATA_DIR = pathlib.Path(__file__).parent / "[10] 마케팅 공통" / "data"
DEFAULT_PAST_PATH = DATA_DIR / "past_content_performance.csv"
DEFAULT_NEW_PATH = DATA_DIR / "new_content_info.csv"

SCRIPTS_DIR = pathlib.Path(__file__).parent / "[10] 마케팅 공통" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import pipeline  # noqa: E402
import dashboard_html  # noqa: E402
from data_loading import DataValidationError, load_new, load_past  # noqa: E402

st.set_page_config(page_title="콘텐츠 성과 예측 리포트", layout="wide")

st.title("콘텐츠 성과 예측 대시보드")
st.caption(
    "저장소에 포함된 샘플 데이터로 대시보드가 바로 표시됩니다. 직접 데이터를 검토하려면 "
    "왼쪽 사이드바에서 파일을 업로드해 교체하세요."
)

with st.sidebar:
    st.header("데이터 업로드 (선택)")
    st.caption("업로드하지 않으면 저장소의 샘플 데이터를 사용합니다.")
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

using_sample_data = not past_file or not new_file
if using_sample_data:
    st.info("샘플 데이터(`[10] 마케팅 공통/data/`)로 대시보드를 표시하고 있습니다. 업로드 시 즉시 교체됩니다.")

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

results = [pipeline.diagnose_one(clean, row) for _, row in new_df.iterrows()]
candidates = pipeline.detect_strategic_candidates(clean) if include_strategy else None

html_doc = dashboard_html.render_dashboard_html(
    clean,
    new_df,
    results,
    candidates=candidates,
    past_filename=past_file.name if past_file else DEFAULT_PAST_PATH.name,
    new_filename=new_file.name if new_file else DEFAULT_NEW_PATH.name,
)

components.html(html_doc, height=1400, scrolling=True)
