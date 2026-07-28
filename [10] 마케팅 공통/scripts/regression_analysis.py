"""
CTR에 대한 다변량 회귀분석 — type/channel/posting_hour/has_emoji를 동시에 통제했을 때
각 축의 "독립적" 기여도를 분리해본다.

decisions.md 58번 항목(일원배치 ANOVA)은 다섯 축을 하나씩 따로 검정했는데, 68번 항목에서
"type과 channel은 데이터상 상당 부분 겹쳐(블로그 type은 거의 항상 블로그 channel) 두 축의
유의성이 같은 신호를 중복 반영할 가능성이 있다"고 우려만 남기고 실제로 분리해보지는 않았음.
이 스크립트는 그 우려를 다변량 회귀 + VIF + 블록 단위 부분 F검정으로 직접 검증한다.

외부 회귀 라이브러리(statsmodels 등) 없이 프로젝트 기존 의존성(pandas/numpy/scipy)만으로
계수·표준오차·t값·p값·R²·VIF·중첩모형 F검정을 직접 구현한다 — 블랙박스 없이 계산 과정을 그대로 보여줌.

사용법:
    py scripts/regression_analysis.py
"""
import numpy as np
import pandas as pd
from scipy import stats

past = pd.read_csv("data/past_content_performance.csv")
clean = past.drop_duplicates(subset="content_id", keep="first").copy()
clean["posting_hour_cat"] = clean["posting_hour"].astype(str) + "h"
clean["has_emoji"] = clean["has_emoji"].astype(int)

y = clean["ctr"].values.astype(float)
n = len(y)
CAT_COLS = ["type", "channel", "posting_hour_cat"]


def design_matrix(cat_cols, extra_cols=None):
    if cat_cols:
        X_df = pd.get_dummies(clean[cat_cols], drop_first=True, prefix=cat_cols)
    else:
        X_df = pd.DataFrame(index=clean.index)
    for c in (extra_cols or []):
        X_df[c] = clean[c].values
    X_df.insert(0, "intercept", 1.0)
    return X_df.values.astype(float), X_df.columns.tolist()


def sse_of(X):
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    return (resid ** 2).sum(), beta, resid


X, feature_names = design_matrix(CAT_COLS, ["has_emoji"])
k = X.shape[1]
sse_full, beta, resid = sse_of(X)
rank = np.linalg.matrix_rank(X)
dof = n - rank
sigma2 = sse_full / dof

print(f"=== [1] CTR ~ type + channel + posting_hour + has_emoji (다변량 회귀, n={n}) ===")
print(f"설계행렬 shape={X.shape}, rank={rank}", "(완전한 열 랭크)" if rank == k else f"(⚠ rank<{k}, 다중공선성으로 일부 계수 유일 추정 불가)")

XtX_pinv = np.linalg.pinv(X.T @ X)
se = np.sqrt(np.maximum(np.diag(XtX_pinv) * sigma2, 0))
t_vals = np.divide(beta, se, out=np.zeros_like(beta), where=se > 0)
p_vals = 2 * (1 - stats.t.cdf(np.abs(t_vals), df=dof))

ss_tot = ((y - y.mean()) ** 2).sum()
r2 = 1 - sse_full / ss_tot
adj_r2 = 1 - (1 - r2) * (n - 1) / (n - k)
print(f"R²={r2:.3f}, adj. R²={adj_r2:.3f}\n")

print(f"{'변수':<24}{'계수':>8}{'SE':>8}{'t':>8}{'p':>9}")
for name, b, s, t, p in zip(feature_names, beta, se, t_vals, p_vals):
    sig = "*" if p < 0.05 else ""
    print(f"{name:<24}{b:>8.3f}{s:>8.3f}{t:>8.2f}{p:>9.4f} {sig}")

print("\n=== [2] VIF (분산팽창지수) — type/channel 다중공선성 정도 확인 ===")
print("(VIF>10이면 해당 변수가 다른 변수들로 대부분 설명됨 = 개별 계수를 신뢰하기 어려움)")
for i, name in enumerate(feature_names):
    if name == "intercept":
        continue
    others = [j for j in range(len(feature_names)) if j != i]
    b_i, *_ = np.linalg.lstsq(X[:, others], X[:, i], rcond=None)
    pred_i = X[:, others] @ b_i
    x_i = X[:, i]
    ss_res_i = ((x_i - pred_i) ** 2).sum()
    ss_tot_i = ((x_i - x_i.mean()) ** 2).sum()
    r2_i = 1 - ss_res_i / ss_tot_i if ss_tot_i > 0 else float("nan")
    vif = 1 / (1 - r2_i) if r2_i < 1 else float("inf")
    flag = " ⚠ 매우 높음" if vif > 10 else ""
    print(f"  {name:<22} R²(다른변수로 설명)={r2_i:.3f}  VIF={vif:.2f}{flag}")

print("\n=== [3] 블록(축) 단위 부분 F검정 — 개별 더미가 아닌 축 전체의 순수 기여도 ===")
print("(다중공선성 때문에 개별 더미 계수 p값은 묻힐 수 있어, 축 전체를 통째로 뺐을 때 설명력이 유의하게 줄어드는지로 재확인)")
blocks = {
    "type (3개 더미)": ["type"],
    "channel (2개 더미)": ["channel"],
    "posting_hour (3개 더미)": ["posting_hour_cat"],
}
for label, drop in blocks.items():
    remain = [c for c in CAT_COLS if c not in drop]
    X_red, red_names = design_matrix(remain, ["has_emoji"])
    sse_red, _, _ = sse_of(X_red)
    q = len(feature_names) - len(red_names)
    f_stat = ((sse_red - sse_full) / q) / (sse_full / dof)
    p = 1 - stats.f.cdf(f_stat, q, dof)
    sig = "유의함" if p < 0.05 else "유의하지 않음"
    print(f"  [{label}] F({q},{dof})={f_stat:.3f}, p={p:.4f} -> {sig}")

X_noemoji, noemoji_names = design_matrix(CAT_COLS, [])
sse_noemoji, _, _ = sse_of(X_noemoji)
q = len(feature_names) - len(noemoji_names)
f_stat = ((sse_noemoji - sse_full) / q) / (sse_full / dof)
p = 1 - stats.f.cdf(f_stat, q, dof)
sig = "유의함" if p < 0.05 else "유의하지 않음"
print(f"  [has_emoji (1개 변수)] F({q},{dof})={f_stat:.3f}, p={p:.4f} -> {sig}")
