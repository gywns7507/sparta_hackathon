"""
업로드된 과거 성과 데이터(clean)·신규 콘텐츠 진단 결과(results)를 sample-final.html과
같은 카드/게이지 스타일의 HTML 대시보드 문자열로 렌더링한다.

pipeline.py가 계산한 값(diagnose_one 결과, detect_strategic_candidates 결과)을 그대로
입력받아 화면에 옮기는 역할만 하고, 분석 로직은 갖지 않는다.
"""
import html
import math

CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans KR', sans-serif; background: #f4f5f7; color: #1a1a2e; line-height: 1.6; }
.container { max-width: 1080px; margin: 0 auto; padding: 40px 24px; }

.header { background: #fff; border-radius: 12px; padding: 32px 36px; margin-bottom: 24px; border-left: 5px solid #7048e8; box-shadow: 0 1px 4px rgba(0,0,0,.06); }
.header h1 { font-size: 22px; font-weight: 700; margin-bottom: 10px; }
.header-meta { font-size: 13px; color: #6c757d; display: flex; flex-wrap: wrap; gap: 16px; }
.header-meta .verify { color: #2b8a3e; font-weight: 600; }

.stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 24px; }
.stat { background: #fff; border-radius: 10px; padding: 18px; text-align: center; box-shadow: 0 1px 4px rgba(0,0,0,.06); border-top: 4px solid; }
.stat-n { font-size: 30px; font-weight: 800; }
.stat-label { font-size: 12px; color: #666; margin-top: 2px; }
.stat-sub { font-size: 11px; color: #999; margin-top: 4px; }
.c-purple { border-color: #7048e8; color: #7048e8; }
.c-blue { border-color: #4361ee; color: #4361ee; }
.c-green { border-color: #2d6a4f; color: #2d6a4f; }
.c-orange { border-color: #e8590c; color: #e8590c; }

.section { background: #fff; border-radius: 12px; padding: 28px 32px; margin-bottom: 24px; box-shadow: 0 1px 4px rgba(0,0,0,.06); }
.section.lvl-basic { border-top: 4px solid #2d6a4f; }
.section.lvl-challenge { border-top: 4px solid #e63946; }
.section-title { font-size: 15px; font-weight: 700; padding-bottom: 14px; margin-bottom: 20px; border-bottom: 1px solid #eee; display: flex; align-items: center; gap: 8px; }
.section-tag { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .5px; padding: 2px 8px; border-radius: 10px; color: white; }
.tag-basic { background: #2d6a4f; }
.tag-challenge { background: #e63946; }
.note { font-size: 12px; color: #888; margin-bottom: 12px; }

.nc-card { border: 1px solid #ececf3; border-radius: 12px; margin-bottom: 22px; overflow: hidden; }
.nc-head { background: #faf8ff; padding: 18px 22px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; flex-wrap: wrap; }
.nc-num { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #7048e8; margin-bottom: 5px; }
.nc-title { font-size: 16px; font-weight: 800; margin-bottom: 8px; }
.nc-tags { display: flex; flex-wrap: wrap; gap: 6px; }
.tag { font-size: 11px; font-weight: 600; padding: 2px 9px; border-radius: 12px; background: #eef0f5; color: #555; }
.tag.emoji { background: #fff3bf; color: #856404; }
.weak-badge { display: inline-block; font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 6px; background: #ffe3e3; color: #c92a2a; white-space: nowrap; }
.nc-body { padding: 20px 22px; }

.gauge-wrap { display: flex; align-items: center; gap: 18px; margin-bottom: 6px; flex-wrap: wrap; }
.gauge-label { font-size: 12px; color: #888; font-weight: 600; text-transform: uppercase; letter-spacing: .5px; }
.gauge-range { font-size: 28px; font-weight: 900; color: #7048e8; }
.gauge-range.weak { color: #c92a2a; }
.gauge-track { flex: 1; min-width: 200px; background: #f0f2f5; border-radius: 8px; height: 26px; position: relative; overflow: hidden; }
.gauge-fill { position: absolute; top: 0; height: 100%; background: linear-gradient(90deg,#9775fa,#7048e8); border-radius: 8px; }
.gauge-fill.weak { background: linear-gradient(90deg,#ffa8a8,#e03131); }
.gauge-scale { display: flex; justify-content: space-between; font-size: 10px; color: #aaa; margin-top: 3px; margin-bottom: 14px; }
.gauge-basis { font-size: 12px; color: #666; margin-bottom: 16px; }

table { width: 100%; border-collapse: collapse; font-size: 13px; }
thead th { background: #f8f9fa; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .5px; color: #6c757d; padding: 9px 12px; text-align: left; border-bottom: 2px solid #e9ecef; white-space: nowrap; }
tbody td { padding: 9px 12px; border-bottom: 1px solid #f0f2f5; vertical-align: middle; }
.ctr-hi { font-weight: 800; color: #2d6a4f; }
.ctr-mid { font-weight: 700; color: #e8590c; }
.ctr-lo { font-weight: 700; color: #e03131; }
.rank { font-weight: 800; color: #7048e8; }
.range-cell { font-weight: 800; }
.r-hi { color: #2d6a4f; }
.r-mid { color: #e8590c; }
.r-lo { color: #e03131; }

.score-gauge { display: inline-flex; gap: 3px; vertical-align: middle; margin-right: 6px; }
.score-dot { width: 15px; height: 15px; border-radius: 4px; background: #e9ecef; }
.score-dot.c-score-3 { background: #2b8a3e; }
.score-dot.c-score-2 { background: #e8590c; }
.score-dot.c-score-1 { background: #e03131; }
.score-text { font-size: 12px; color: #666; font-weight: 700; vertical-align: middle; }
.verdict { display: inline-block; font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 4px; white-space: nowrap; }
.v-keep { background: #d3f9d8; color: #2b8a3e; }
.v-tune { background: #fff3bf; color: #856404; }
.v-fix { background: #ffe3e3; color: #c92a2a; }

.tip-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 16px; }
.tip { background: #f8f9fa; border-left: 3px solid #4361ee; border-radius: 0 8px 8px 0; padding: 12px 14px; }
.tip-label { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .5px; color: #4361ee; margin-bottom: 4px; }
.tip-body { font-size: 12.5px; color: #333; line-height: 1.55; }
.tip-body b { color: #1a1a2e; }

.priority-note { background: #f8f9fa; border-left: 3px solid #e63946; border-radius: 0 8px 8px 0; padding: 14px 18px; font-size: 13px; color: #444; margin-bottom: 20px; }
.priority-note strong { display: block; font-size: 11px; text-transform: uppercase; letter-spacing: .5px; color: #888; margin-bottom: 4px; }

.proposal { border-radius: 12px; border: 1px solid #e9ecef; margin-bottom: 20px; overflow: hidden; }
.proposal-header { padding: 20px 24px; display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; flex-wrap: wrap; background: #fff8f8; border-bottom: 1px solid #eee; }
.proposal-meta { flex: 1; }
.proposal-num { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #888; margin-bottom: 6px; }
.proposal-title { font-size: 16px; font-weight: 800; margin-bottom: 6px; }
.proposal-sub { font-size: 13px; color: #666; }
.priority-badge { display: flex; flex-direction: column; align-items: center; justify-content: center; border-radius: 10px; padding: 10px 18px; min-width: 90px; text-align: center; }
.priority-badge .pb-label { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .5px; margin-bottom: 2px; }
.priority-badge .pb-score { font-size: 22px; font-weight: 900; }
.pb-p0 { background: #ffe0e3; color: #c9323e; }
.pb-p1 { background: #fff3cd; color: #856404; }

.proposal-body { padding: 0 24px 24px; display: grid; grid-template-columns: 1fr 1fr; grid-auto-rows: 1fr; gap: 14px; }
.prop-section { background: #f8f9fa; border-radius: 8px; padding: 16px; display: flex; flex-direction: column; min-height: 190px; }
.prop-section-title { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .5px; color: #888; margin-bottom: 8px; }
.prop-section-body { font-size: 13px; color: #333; line-height: 1.6; flex: 1; display: flex; flex-direction: column; justify-content: center; }

.score-breakdown { display: flex; flex-direction: column; gap: 6px; }
.score-row { display: flex; justify-content: space-between; align-items: center; font-size: 12px; }
.score-label { display: inline-block; width: 92px; flex-shrink: 0; white-space: nowrap; }
.score-bar-track { background: #e9ecef; border-radius: 3px; height: 8px; flex: 1; margin: 0 10px; }
.score-bar-fill { height: 100%; border-radius: 3px; background: #4361ee; }
.score-val { font-weight: 700; font-size: 13px; color: #333; min-width: 40px; text-align: right; }

.deprioritized { background: #f8f9fa; border-radius: 8px; padding: 14px 18px; font-size: 12.5px; color: #555; margin-top: 8px; }
.deprioritized b { color: #333; }

@media(max-width:700px) {
  .stats-row { grid-template-columns: repeat(2, 1fr); }
  .tip-grid { grid-template-columns: 1fr; }
  .proposal-body { grid-template-columns: 1fr; }
}
"""

AXIS_LABEL = {
    "posting_hour": "발행시간 조정",
    "has_emoji": "이모지 조정",
    "type": "포맷 전환",
    "topic_category": "주제 조정",
    "headline_length": "제목길이 조정",
    "none": "유지",
}

def esc(x):
    return html.escape(str(x))


def _ctr_cls(ctr, lo, hi):
    if ctr >= hi:
        return "ctr-hi"
    if ctr <= lo:
        return "ctr-lo"
    return "ctr-mid"


def _range_cls(ctr_min, overall_mean):
    if ctr_min >= overall_mean:
        return "r-hi"
    if ctr_min >= overall_mean * 0.85:
        return "r-mid"
    return "r-lo"


def _score_dots_html(score, max_score):
    ratio = (score / max_score) if max_score else 0
    if ratio >= 0.66:
        cls = "c-score-3"
    elif ratio >= 0.33:
        cls = "c-score-2"
    else:
        cls = "c-score-1"
    filled = round(score)
    dots = "".join(
        f'<span class="score-dot {cls}"></span>' if i < filled else '<span class="score-dot"></span>'
        for i in range(max_score)
    )
    return f'<span class="score-gauge">{dots}</span><span class="score-text">{filled}/{max_score}</span>'


def _verdict_html(r):
    top = r["suggestions"][0]
    if top["axis"] == "none":
        return '<span class="verdict v-keep">이미 최적 · 유지</span>'
    label = AXIS_LABEL.get(top["axis"], "조건 조정")
    if r["anchor_level"] == "type-relaxed" or r["weak_match"]:
        return f'<span class="verdict v-fix">{esc(label)} (신뢰도 낮음)</span>'
    return f'<span class="verdict v-tune">{esc(label)} 검토</span>'


def _gauge_scale_max(results, clean):
    values = [r["ctr_max"] for r in results]
    if len(clean):
        values.append(clean["ctr"].max())
    top = max(values) if values else 1.0
    scale = math.ceil(top * 1.15 * 2) / 2
    return max(scale, 1.0)


def _condition_tags(row):
    tags = [esc(row["type"]), esc(row["topic_category"]), esc(row["channel"]), f"{esc(row['posting_hour'])}시"]
    tag_html = "".join(f'<span class="tag">{t}</span>' for t in tags)
    if row["has_emoji"]:
        tag_html += '<span class="tag emoji">😀 이모지</span>'
    else:
        tag_html += '<span class="tag">이모지 없음</span>'
    return tag_html


def _stat_block(clean, new_df):
    n_stats = [
        ("c-purple", len(clean), "학습 콘텐츠", "업로드 파일 기준"),
        ("c-blue", len(new_df), "진단 대상", "신규 콘텐츠"),
    ]

    hour_ctr = clean.groupby("posting_hour")["ctr"].mean()
    if len(hour_ctr) >= 2:
        best_h, worst_h = hour_ctr.idxmax(), hour_ctr.idxmin()
        delta = hour_ctr.max() - hour_ctr.min()
        n_stats.append(("c-green", f"{delta:+.2f}%p", "발행 시간대 효과",
                         f"{best_h}시({hour_ctr.max():.2f}%) vs {worst_h}시({hour_ctr.min():.2f}%)"))
    else:
        n_stats.append(("c-green", "N/A", "발행 시간대 효과", "비교할 시간대 부족"))

    emoji_ctr = clean.groupby("has_emoji")["ctr"].mean()
    if True in emoji_ctr.index and False in emoji_ctr.index:
        delta = emoji_ctr[True] - emoji_ctr[False]
        n_stats.append(("c-orange", f"{delta:+.2f}%p", "이모지 효과",
                         f"포함({emoji_ctr[True]:.2f}%) vs 미포함({emoji_ctr[False]:.2f}%)"))
    else:
        n_stats.append(("c-orange", "N/A", "이모지 효과", "포함/미포함 데이터 부족"))

    cells = "".join(
        f'<div class="stat {c}"><div class="stat-n">{esc(n)}</div>'
        f'<div class="stat-label">{esc(label)}</div><div class="stat-sub">{esc(sub)}</div></div>'
        for c, n, label, sub in n_stats
    )
    return f'<div class="stats-row">{cells}</div>'


def _pattern_section(clean):
    tiles = []

    hour_ctr = clean.groupby("posting_hour")["ctr"].mean()
    if len(hour_ctr) >= 2:
        best_h, worst_h = hour_ctr.idxmax(), hour_ctr.idxmin()
        tiles.append(("발행 시간대", f"{best_h}시 평균 CTR {hour_ctr.max():.2f}% vs {worst_h}시 "
                                  f"{hour_ctr.min():.2f}% — <b>{hour_ctr.max()-hour_ctr.min():+.2f}%p</b>"))

    emoji_ctr = clean.groupby("has_emoji")["ctr"].mean()
    if True in emoji_ctr.index and False in emoji_ctr.index:
        tiles.append(("이모지", f"포함 평균 {emoji_ctr[True]:.2f}% vs 미포함 {emoji_ctr[False]:.2f}% — "
                              f"<b>{emoji_ctr[True]-emoji_ctr[False]:+.2f}%p</b>"))

    combo = clean.groupby(["type", "channel"])["ctr"].mean()
    if len(combo) >= 2:
        best_combo, worst_combo = combo.idxmax(), combo.idxmin()
        tiles.append(("유형 × 채널", f"<b>{esc('+'.join(best_combo))}</b>({combo.max():.2f}%) 최상 / "
                                   f"<b>{esc('+'.join(worst_combo))}</b>({combo.min():.2f}%) 최하"))

    if not tiles:
        return ""

    tips = "".join(
        f'<div class="tip"><div class="tip-label">{esc(label)}</div><div class="tip-body">{body}</div></div>'
        for label, body in tiles
    )
    return (
        '<div class="section lvl-basic">'
        '<div class="section-title"><span class="section-tag tag-basic">Basic</span> 🔎 업로드 데이터에서 찾은 핵심 성과 패턴</div>'
        f'<div class="tip-grid">{tips}</div>'
        '</div>'
    )


def _dashboard_table(results, clean):
    overall_mean = clean["ctr"].mean() if len(clean) else 0
    rows = []
    for i, r in enumerate(results, 1):
        row = r["row"]
        rows.append(
            "<tr>"
            f"<td>{i}</td><td>{esc(row['title'])}</td>"
            f"<td>{esc(row['type'])}·{esc(row['topic_category'])}·{esc(row['channel'])}·{esc(row['posting_hour'])}시·"
            f"이모지{'O' if row['has_emoji'] else 'X'}</td>"
            f"<td class=\"range-cell {_range_cls(r['ctr_min'], overall_mean)}\">{r['ctr_min']}~{r['ctr_max']}%</td>"
            f"<td>{r['anchor_n']}건</td>"
            f"<td>{_score_dots_html(int(r['max_score']), 3)}</td>"
            f"<td>{_verdict_html(r)}</td>"
            "</tr>"
        )
    return (
        '<div class="section lvl-basic">'
        '<div class="section-title"><span class="section-tag tag-basic">Basic</span> 🎯 신규 콘텐츠 일괄 진단 대시보드</div>'
        '<table><thead><tr><th>#</th><th>제목</th><th>조건</th><th>예상 CTR</th><th>앵커 후보</th>'
        '<th>서브점수</th><th>판정</th></tr></thead><tbody>' + "".join(rows) + '</tbody></table>'
        '</div>'
    )


def _nc_cards(results, scale_max):
    cards = []
    for i, r in enumerate(results, 1):
        row = r["row"]
        weak = r["weak_match"]
        left = r["ctr_min"] / scale_max * 100
        width = max((r["ctr_max"] - r["ctr_min"]) / scale_max * 100, 1.2)
        mid = scale_max / 2

        weak_badge = '<span class="weak-badge">⚠️ 매칭 신뢰도 낮음</span>' if weak else ""
        basis_prefix = "⚠️ " if weak else "📌 근거: "
        basis = (f"{basis_prefix}앵커 후보 {r['anchor_n']}건({esc(r['note'])}) 중 "
                 f"서브점수 최고 {int(r['max_score'])}/3인 유사 TOP3의 실제 CTR")

        top3_rows = []
        for rank, (_, t) in enumerate(r["top3"].iterrows(), 1):
            eng = f"{t['engagement_rate']}%" if t["engagement_rate"] == t["engagement_rate"] else "N/A(결측)"
            ctr_cls = _ctr_cls(t["ctr"], r["ctr_min"], r["ctr_max"])
            top3_rows.append(
                f'<tr><td class="rank">{rank}</td><td>{esc(t.get("content_id", ""))}</td>'
                f'<td>{esc(t["title"])}</td><td class="{ctr_cls}">{t["ctr"]}%</td>'
                f'<td>{eng}</td><td>서브점수 {int(t["score"])}/3</td></tr>'
            )

        tips = []
        for j, s in enumerate(r["suggestions"], 1):
            label = f"개선 제안 {j}" + (" (근거 약함)" if s["reliability"] == "weak" else "")
            tips.append(f'<div class="tip"><div class="tip-label">{esc(label)}</div>'
                        f'<div class="tip-body">{esc(s["text"])}</div></div>')

        cards.append(f'''
<div class="nc-card">
  <div class="nc-head">
    <div>
      <div class="nc-num">신규 콘텐츠 {i}</div>
      <div class="nc-title">{esc(row["title"])}</div>
      <div class="nc-tags">{_condition_tags(row)}</div>
    </div>
    {weak_badge}
  </div>
  <div class="nc-body">
    <div class="gauge-wrap">
      <span class="gauge-label">예상 CTR 범위</span>
      <span class="gauge-range {'weak' if weak else ''}">{r["ctr_min"]}% ~ {r["ctr_max"]}%</span>
      <div class="gauge-track"><div class="gauge-fill {'weak' if weak else ''}" style="left:{left:.1f}%;width:{width:.1f}%"></div></div>
    </div>
    <div class="gauge-scale"><span>0%</span><span>{mid:.1f}%</span><span>{scale_max:.1f}%</span></div>
    <div class="gauge-basis">{basis}</div>
    <table>
      <thead><tr><th>순위</th><th>id</th><th>제목</th><th>CTR</th><th>인게이지먼트율</th><th>유사 이유</th></tr></thead>
      <tbody>{"".join(top3_rows)}</tbody>
    </table>
    <div class="tip-grid">{"".join(tips)}</div>
  </div>
</div>''')

    return (
        '<div class="section lvl-basic">'
        '<div class="section-title"><span class="section-tag tag-basic">Basic</span> 📋 신규 콘텐츠 개별 진단</div>'
        + "".join(cards) + '</div>'
    )


def _strategy_section(candidates, top_n=2):
    if not candidates:
        return ""
    lines = [
        '<div class="section lvl-challenge">',
        '<div class="section-title"><span class="section-tag tag-challenge">Challenge</span> '
        '⚖️ 콘텐츠 발행 전략 기획안 (자동 생성)</div>',
        '<div class="priority-note"><strong>우선순위 판단 기준</strong>'
        '우선순위 점수 = 임팩트(1~5) × 실행용이도(1~5), 25점 만점. 임팩트는 효과크기(%p)를 구간별로 '
        '매핑하되 통계적으로 유의하지 않으면 무조건 1점. 실행용이도는 개입 성격(일정 조정 vs 조직 프로세스 변경)에 따라 고정.</div>',
    ]
    for i, c in enumerate(candidates[:top_n], 1):
        badge_cls = "pb-p0" if i == 1 else "pb-p1"
        impact_w = c["impact"] / 5 * 100
        feas_w = c["feasibility"] / 5 * 100
        total_w = c["priority"] / 25 * 100
        lines.append(f'''
<div class="proposal">
  <div class="proposal-header">
    <div class="proposal-meta">
      <div class="proposal-num">기획안 {i:02d}</div>
      <div class="proposal-title">{esc(c["title"])}</div>
    </div>
    <div class="priority-badge {badge_cls}"><div class="pb-label">Priority</div><div class="pb-score">{c["priority"]}점</div></div>
  </div>
  <div class="proposal-body">
    <div class="prop-section"><div class="prop-section-title">문제 정의</div><div class="prop-section-body">{esc(c["problem"])}</div></div>
    <div class="prop-section"><div class="prop-section-title">근거 데이터 · 예상 효과</div><div class="prop-section-body">{esc(c["evidence"])} {esc(c["effect"])}</div></div>
    <div class="prop-section"><div class="prop-section-title">전략 제안</div><div class="prop-section-body">{esc(c["strategy"])}</div></div>
    <div class="prop-section"><div class="prop-section-title">우선순위 계산</div><div class="prop-section-body">
      <div class="score-breakdown">
        <div class="score-row"><span class="score-label">임팩트 (1~5)</span><div class="score-bar-track"><div class="score-bar-fill" style="width:{impact_w:.0f}%"></div></div><span class="score-val">{c["impact"]}/5</span></div>
        <div class="score-row"><span class="score-label">실행용이도 (1~5)</span><div class="score-bar-track"><div class="score-bar-fill" style="width:{feas_w:.0f}%"></div></div><span class="score-val">{c["feasibility"]}/5</span></div>
        <div class="score-row" style="font-weight:700"><span class="score-label">총점</span><div class="score-bar-track"><div class="score-bar-fill" style="width:{total_w:.0f}%;background:#e63946"></div></div><span class="score-val" style="color:#e63946">{c["priority"]}/25</span></div>
      </div>
    </div></div>
  </div>
</div>''')

    rest = candidates[top_n:]
    if rest:
        items = "".join(f'<p style="margin-bottom:6px"><b>{esc(c["title"])}</b> ({c["priority"]}점): {esc(c["evidence"])}</p>' for c in rest)
        lines.append(f'<div class="deprioritized"><strong>참고: 탐지됐지만 우선순위 상 채택되지 않은 후보</strong>{items}</div>')

    lines.append('</div>')
    return "".join(lines)


def render_dashboard_html(clean, new_df, results, candidates=None, past_filename="", new_filename=""):
    header = f'''
<div class="header">
  <h1>콘텐츠 성과 예측 리포트 — 업로드 데이터 기준</h1>
  <div class="header-meta">
    <span>📊 학습 파일: {esc(past_filename) or "(업로드된 파일)"}</span>
    <span>🎯 진단 파일: {esc(new_filename) or "(업로드된 파일)"}</span>
    <span class="verify">✅ scripts/pipeline.py 로직으로 실시간 계산</span>
  </div>
</div>'''

    body = [
        header,
        _stat_block(clean, new_df),
        _pattern_section(clean),
        _dashboard_table(results, clean),
        _nc_cards(results, _gauge_scale_max(results, clean)),
    ]
    if candidates:
        body.append(_strategy_section(candidates))

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

    return f'''<!DOCTYPE html>
<html lang="ko" translate="no">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="google" content="notranslate">
<title>콘텐츠 성과 예측 리포트 — 업로드 데이터</title>
<style>{CSS}</style>
</head>
<body>
<div class="container">
{"".join(body)}
</div>
{notranslate_patch}
</body>
</html>'''
