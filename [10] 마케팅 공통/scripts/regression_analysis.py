"""
CTR에 대한 다변량 회귀분석 — type/channel/posting_hour/has_emoji를 동시에 통제했을 때
각 축의 "독립적" 기여도를 분리해본다.

decisions.md 58번 항목(일원배치 ANOVA)은 다섯 축을 하나씩 따로 검정했는데, 68번 항목에서
"type과 channel은 데이터상 상당 부분 겹쳐(블로그 type은 거의 항상 블로그 channel) 두 축의
유의성이 같은 신호를 중복 반영할 가능성이 있다"고 우려만 남기고 실제로 분리해보지는 않았음.
이 스크립트는 그 우려를 다변량 회귀 + VIF + 블록 단위 부분 F검정으로 직접 검증한다.

외부 회귀 라이브러리(statsmodels 등) 없이 프로젝트 기존 의존성(pandas/numpy/scipy)만으로
계수·표준오차·t값·p값·R²·VIF·중첩모형 F검정을 직접 구현한다 — 블랙박스 없이 계산 과정을 그대로 보여줌.

compute(clean)이 대시보드(scripts/dashboard_native.py)에서 재사용하는 구조화된 결과를 반환하고,
CLI로 직접 실행하면(`py scripts/regression_analysis.py`) 기존과 동일한 콘솔 출력을 그대로 낸다.

사용법:
    py scripts/regression_analysis.py
"""
import numpy as np
import pandas as pd
from scipy import stats

CAT_COLS = ["type", "channel", "posting_hour_cat"]


def _design_matrix(clean, cat_cols, extra_cols=None):
    if cat_cols:
        X_df = pd.get_dummies(clean[cat_cols], drop_first=True, prefix=cat_cols)
    else:
        X_df = pd.DataFrame(index=clean.index)
    for c in (extra_cols or []):
        X_df[c] = clean[c].values
    X_df.insert(0, "intercept", 1.0)
    return X_df.values.astype(float), X_df.columns.tolist()


def _sse_of(X, y):
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    return (resid ** 2).sum(), beta, resid


def compute(clean):
    """clean: content_id 중복 제거된 과거 성과 데이터프레임. 구조화된 결과 dict를 반환."""
    clean = clean.copy()
    clean["posting_hour_cat"] = clean["posting_hour"].astype(str) + "h"
    clean["has_emoji"] = clean["has_emoji"].astype(int)

    y = clean["ctr"].values.astype(float)
    n = len(y)

    X, feature_names = _design_matrix(clean, CAT_COLS, ["has_emoji"])
    k = X.shape[1]
    if n <= k + 2:  # 표본이 파라미터 수 대비 너무 적으면 안정적 추정 불가 — 회귀 생략
        return None

    sse_full, beta, resid = _sse_of(X, y)
    rank = np.linalg.matrix_rank(X)
    dof = n - rank
    sigma2 = sse_full / dof if dof > 0 else float("nan")

    XtX_pinv = np.linalg.pinv(X.T @ X)
    se = np.sqrt(np.maximum(np.diag(XtX_pinv) * sigma2, 0))
    t_vals = np.divide(beta, se, out=np.zeros_like(beta), where=se > 0)
    p_vals = 2 * (1 - stats.t.cdf(np.abs(t_vals), df=dof)) if dof > 0 else np.full_like(beta, np.nan)

    ss_tot = ((y - y.mean()) ** 2).sum()
    r2 = 1 - sse_full / ss_tot if ss_tot > 0 else float("nan")
    adj_r2 = 1 - (1 - r2) * (n - 1) / (n - k) if n > k else float("nan")

    coefficients = [
        {"name": name, "coef": b, "se": s, "t": t, "p": p, "significant": bool(p < 0.05) if p == p else False}
        for name, b, s, t, p in zip(feature_names, beta, se, t_vals, p_vals)
        if name != "intercept"
    ]

    vif = []
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
        v = 1 / (1 - r2_i) if r2_i == r2_i and r2_i < 1 else float("inf")
        vif.append({"name": name, "r2": r2_i, "vif": v})

    blocks = {
        "type": ["type"],
        "channel": ["channel"],
        "posting_hour": ["posting_hour_cat"],
    }
    block_tests = []
    for label, drop in blocks.items():
        remain = [c for c in CAT_COLS if c not in drop]
        X_red, red_names = _design_matrix(clean, remain, ["has_emoji"])
        sse_red, _, _ = _sse_of(X_red, y)
        q = len(feature_names) - len(red_names)
        f_stat = ((sse_red - sse_full) / q) / (sse_full / dof) if dof > 0 and sse_full > 0 else float("nan")
        p = 1 - stats.f.cdf(f_stat, q, dof) if f_stat == f_stat else float("nan")
        block_tests.append({"label": label, "q": q, "dof": dof, "f": f_stat, "p": p,
                             "significant": bool(p < 0.05) if p == p else False})

    X_noemoji, noemoji_names = _design_matrix(clean, CAT_COLS, [])
    sse_noemoji, _, _ = _sse_of(X_noemoji, y)
    q = len(feature_names) - len(noemoji_names)
    f_stat = ((sse_noemoji - sse_full) / q) / (sse_full / dof) if dof > 0 and sse_full > 0 else float("nan")
    p = 1 - stats.f.cdf(f_stat, q, dof) if f_stat == f_stat else float("nan")
    block_tests.append({"label": "has_emoji", "q": q, "dof": dof, "f": f_stat, "p": p,
                         "significant": bool(p < 0.05) if p == p else False})

    return {
        "n": n, "k": k, "rank": rank, "r2": r2, "adj_r2": adj_r2,
        "coefficients": coefficients, "vif": vif, "block_tests": block_tests,
    }


def _print_report(result):
    if result is None:
        print("표본이 너무 적어 다변량 회귀를 생략합니다.")
        return
    print(f"=== [1] CTR ~ type + channel + posting_hour + has_emoji (다변량 회귀, n={result['n']}) ===")
    k = result["k"]
    print(f"rank={result['rank']}", "(완전한 열 랭크)" if result["rank"] == k else f"(⚠ rank<{k}, 다중공선성으로 일부 계수 유일 추정 불가)")
    print(f"R²={result['r2']:.3f}, adj. R²={result['adj_r2']:.3f}\n")

    print(f"{'변수':<24}{'계수':>8}{'SE':>8}{'t':>8}{'p':>9}")
    for c in result["coefficients"]:
        sig = "*" if c["significant"] else ""
        print(f"{c['name']:<24}{c['coef']:>8.3f}{c['se']:>8.3f}{c['t']:>8.2f}{c['p']:>9.4f} {sig}")

    print("\n=== [2] VIF (분산팽창지수) — type/channel 다중공선성 정도 확인 ===")
    print("(VIF>10이면 해당 변수가 다른 변수들로 대부분 설명됨 = 개별 계수를 신뢰하기 어려움)")
    for v in result["vif"]:
        flag = " ⚠ 매우 높음" if v["vif"] > 10 else ""
        print(f"  {v['name']:<22} R²(다른변수로 설명)={v['r2']:.3f}  VIF={v['vif']:.2f}{flag}")

    print("\n=== [3] 블록(축) 단위 부분 F검정 — 개별 더미가 아닌 축 전체의 순수 기여도 ===")
    print("(다중공선성 때문에 개별 더미 계수 p값은 묻힐 수 있어, 축 전체를 통째로 뺐을 때 설명력이 유의하게 줄어드는지로 재확인)")
    for b in result["block_tests"]:
        sig = "유의함" if b["significant"] else "유의하지 않음"
        print(f"  [{b['label']}] F({b['q']},{b['dof']})={b['f']:.3f}, p={b['p']:.4f} -> {sig}")


if __name__ == "__main__":
    past = pd.read_csv("data/past_content_performance.csv")
    clean = past.drop_duplicates(subset="content_id", keep="first").copy()
    _print_report(compute(clean))
