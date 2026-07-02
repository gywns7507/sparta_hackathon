"""
Streamlit에서 업로드한 CSV/Excel 파일을 pipeline.py가 기대하는 형태(dtype 등)로 검증·정규화한다.
"""
import pandas as pd

PAST_REQUIRED = ["content_id", "title", "type", "topic_category", "channel",
                  "ctr", "posting_hour", "has_emoji", "headline_length"]
NEW_REQUIRED = ["title", "type", "topic_category", "channel",
                 "posting_hour", "has_emoji", "headline_length"]

_BOOL_MAP = {"TRUE": True, "FALSE": False, "1": True, "0": False, "O": True, "X": False}


class DataValidationError(Exception):
    pass


def _read_table(uploaded_file, file_label):
    name = uploaded_file.name.lower()
    try:
        if name.endswith((".xlsx", ".xls")):
            return pd.read_excel(uploaded_file)
        return pd.read_csv(uploaded_file)
    except Exception as e:
        raise DataValidationError(f"{file_label} 파일을 읽지 못했습니다: {e}") from e


def _validate_columns(df, required, file_label):
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise DataValidationError(f"{file_label}에 필수 컬럼이 없습니다: {', '.join(missing)}")


def _normalize_bool(series, file_label):
    if series.dtype == bool:
        return series
    mapped = series.astype(str).str.strip().str.upper().map(_BOOL_MAP)
    if mapped.isna().any():
        bad = sorted(set(series[mapped.isna()].astype(str)))[:5]
        raise DataValidationError(f"{file_label}의 has_emoji 값 중 True/False로 해석할 수 없는 값이 있습니다: {bad}")
    return mapped.astype(bool)


def _normalize_int(df, col, file_label):
    numeric = pd.to_numeric(df[col], errors="coerce")
    if numeric.isna().any():
        raise DataValidationError(f"{file_label}의 {col} 컬럼에 숫자로 변환할 수 없는 값이 있습니다.")
    return numeric.astype(int)


def load_past(uploaded_file):
    df = _read_table(uploaded_file, "과거 성과 데이터")
    _validate_columns(df, PAST_REQUIRED, "과거 성과 데이터")
    df = df.copy()
    df["has_emoji"] = _normalize_bool(df["has_emoji"], "과거 성과 데이터")
    df["posting_hour"] = _normalize_int(df, "posting_hour", "과거 성과 데이터")
    df["headline_length"] = _normalize_int(df, "headline_length", "과거 성과 데이터")
    df["ctr"] = pd.to_numeric(df["ctr"], errors="coerce")
    if df["ctr"].isna().any():
        raise DataValidationError("과거 성과 데이터의 ctr 컬럼에 숫자로 변환할 수 없는 값이 있습니다.")
    if "engagement_rate" in df.columns:
        df["engagement_rate"] = pd.to_numeric(df["engagement_rate"], errors="coerce")
    else:
        df["engagement_rate"] = float("nan")
    if df["content_id"].isna().any():
        raise DataValidationError("과거 성과 데이터의 content_id에 빈 값이 있습니다.")
    return df


def load_new(uploaded_file):
    df = _read_table(uploaded_file, "신규 콘텐츠 데이터")
    _validate_columns(df, NEW_REQUIRED, "신규 콘텐츠 데이터")
    df = df.copy()
    df["has_emoji"] = _normalize_bool(df["has_emoji"], "신규 콘텐츠 데이터")
    df["posting_hour"] = _normalize_int(df, "posting_hour", "신규 콘텐츠 데이터")
    df["headline_length"] = _normalize_int(df, "headline_length", "신규 콘텐츠 데이터")
    return df
