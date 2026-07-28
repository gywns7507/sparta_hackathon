"""
reach(도달수) 활용 분석 — 지금까지 프로젝트는 ctr·engagement_rate만 진단축으로 쓰고
reach는 결측치(C070) 처리 대상으로만 언급됐을 뿐 실제 성과 진단에는 한 번도 쓰이지 않았음.

company-info.md 정의: reach는 "콘텐츠가 노출된 순 사용자 수"(규모 지표)이고, ctr의 분모가 되는
노출과는 별개 개념. 반면 engagement_rate = (좋아요+댓글+공유)/reach × 100 으로 이미 reach를
분모로 정규화한 "비율" 지표다 — 그래서 engagement_rate가 reach와 다시 강하게 상관된다면
이는 정의상 당연한 결과가 아니라(오히려 규모가 커질수록 참여 "비율"은 희석되는 게 일반적 통념),
실제로 확인해볼 가치가 있는 경험적 패턴이다.

이 스크립트는 3단계로 확인한다:
  1. reach와 ctr/engagement_rate의 원시 상관관계
  2. reach 자체가 type/channel/posting_hour(=이미 검증된 성과 축들)에 따라 체계적으로 다른지
  3. type+channel을 통제한 뒤에도(편상관) reach-성과 관계가 남는지 — 남는다면 "형식이 원래
     도달도 잘 되고 성과도 좋다"는 confound만으로는 설명 안 되는 독립적 신호라는 뜻

사용법:
    py scripts/reach_analysis.py
"""
import numpy as np
import pandas as pd
from scipy import stats

past = pd.read_csv("data/past_content_performance.csv")
clean = past.drop_duplicates(subset="content_id", keep="first").copy()
reach_ok = clean.dropna(subset=["reach"]).copy()  # C070(reach 결측) 제외

print(f"=== [1] reach 원시 상관관계 (결측 제외, n={len(reach_ok.dropna(subset=['ctr']))}) ===")
for target in ["ctr", "engagement_rate"]:
    sub = reach_ok.dropna(subset=[target])
    r, p = stats.pearsonr(sub["reach"], sub[target])
    print(f"  reach vs {target}: r={r:.3f}, p={p:.4g} (n={len(sub)})")


def anova(data, col, target):
    groups = [g.values for _, g in data.groupby(col)[target]]
    f, p = stats.f_oneway(*groups)
    grand_mean = data[target].mean()
    ss_between = sum(len(g) * (g.mean() - grand_mean) ** 2 for g in groups)
    ss_total = ((data[target] - grand_mean) ** 2).sum()
    return f, p, ss_between / ss_total


print("\n=== [2] reach가 type/channel/posting_hour에 따라 체계적으로 다른가 ===")
for col in ["type", "channel", "posting_hour"]:
    f, p, eta2 = anova(reach_ok, col, "reach")
    sig = "유의함" if p < 0.05 else "유의하지 않음"
    means = reach_ok.groupby(col)["reach"].mean().round(0).to_dict()
    print(f"  [{col}] F={f:.2f}, p={p:.4f}, eta2={eta2:.3f} -> {sig}")
    print(f"    그룹 평균 reach: {means}")

print("\n=== [3] type+channel 통제 후에도 reach-성과 관계가 남는가 (편상관) ===")
print("(reach를 type+channel로 회귀한 잔차 vs ctr/engagement_rate를 같은 방식으로 회귀한 잔차의 상관)")


def residualize(data, target_col):
    dummies = pd.get_dummies(data[["type", "channel"]], drop_first=True)
    X = np.column_stack([np.ones(len(data)), dummies.values.astype(float)])
    y = data[target_col].values.astype(float)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return y - X @ beta


for target in ["ctr", "engagement_rate"]:
    sub = reach_ok.dropna(subset=[target]).copy()
    reach_resid = residualize(sub, "reach")
    target_resid = residualize(sub, target)
    r, p = stats.pearsonr(reach_resid, target_resid)
    raw_r, _ = stats.pearsonr(sub["reach"], sub[target])
    print(f"  reach~{target} | 원시 r={raw_r:.3f} -> type+channel 통제 후 편상관 r={r:.3f}, p={p:.4g} (n={len(sub)})")
