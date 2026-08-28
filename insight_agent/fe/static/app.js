// 바닐라 JS SPA -- 빌드 도구/프레임워크 없이 4개 탭(PRD/트레이스/HITL/HOTL)을 구현한다.

const state = {
  activeTab: "prd",
  approvalStatus: "pending",
  selectedRunId: null,
  drilldownGroupBy: null,
  drilldownEntityId: null,
};

// ---- 공통 유틸 -----------------------------------------------------------

async function api(path, options) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const body = await res.json();
  if (!res.ok) throw new Error(body.error || `요청 실패: ${res.status}`);
  return body;
}

function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "text") node.textContent = v;
    else if (k === "html") node.innerHTML = v;
    else node.setAttribute(k, v);
  }
  for (const child of children) node.appendChild(child);
  return node;
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

// 아주 작은 markdown -> html 변환기. prd.md에서 쓰는 문법(#/##, 표, 목록, **, `, >, ```)만 지원한다.
function renderMarkdown(md) {
  const lines = md.split("\n");
  let html = "";
  let i = 0;
  let inList = false;
  let inCode = false;

  const inlineFmt = (s) =>
    escapeHtml(s)
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/`([^`]+)`/g, "<code>$1</code>");

  const closeList = () => { if (inList) { html += "</ul>"; inList = false; } };

  while (i < lines.length) {
    const line = lines[i];

    if (line.trim().startsWith("```")) {
      if (!inCode) { closeList(); html += "<pre>"; inCode = true; }
      else { html += "</pre>"; inCode = false; }
      i++; continue;
    }
    if (inCode) { html += escapeHtml(line) + "\n"; i++; continue; }

    if (line.startsWith("# ")) { closeList(); html += `<h1>${inlineFmt(line.slice(2))}</h1>`; i++; continue; }
    if (line.startsWith("## ")) { closeList(); html += `<h2>${inlineFmt(line.slice(3))}</h2>`; i++; continue; }
    if (line.startsWith("> ")) { closeList(); html += `<blockquote>${inlineFmt(line.slice(2))}</blockquote>`; i++; continue; }

    if (line.startsWith("- ")) {
      if (!inList) { html += "<ul>"; inList = true; }
      html += `<li>${inlineFmt(line.slice(2))}</li>`;
      i++; continue;
    }
    closeList();

    if (line.startsWith("|")) {
      const tableLines = [];
      while (i < lines.length && lines[i].startsWith("|")) { tableLines.push(lines[i]); i++; }
      const rows = tableLines
        .filter((l) => !/^\|[\s-]*\|$/.test(l.replace(/[-\s|]/g, (c) => (c === "|" ? "|" : ""))) && !/^\|(\s*-+\s*\|)+$/.test(l))
        .map((l) => l.split("|").slice(1, -1).map((c) => c.trim()));
      if (rows.length) {
        html += "<table><thead><tr>" + rows[0].map((c) => `<th>${inlineFmt(c)}</th>`).join("") + "</tr></thead><tbody>";
        for (const r of rows.slice(1)) {
          html += "<tr>" + r.map((c) => `<td>${inlineFmt(c)}</td>`).join("") + "</tr>";
        }
        html += "</tbody></table>";
      }
      continue;
    }

    if (line.trim() === "") { i++; continue; }
    html += `<p>${inlineFmt(line)}</p>`;
    i++;
  }
  closeList();
  return html;
}

// ---- 탭 전환 --------------------------------------------------------------

function setupTabs() {
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById(`tab-${btn.dataset.tab}`).classList.add("active");
      state.activeTab = btn.dataset.tab;
      onTabShown(btn.dataset.tab);
    });
  });
}

function onTabShown(tab) {
  if (tab === "prd") loadPrd();
  if (tab === "trace") loadRuns();
  if (tab === "hitl") loadApprovals();
  if (tab === "hotl") loadHotl();
  if (tab === "priority") loadPriority();
}

// ---- PRD 탭 ---------------------------------------------------------------

async function loadPrd() {
  const { markdown } = await api("/api/prd");
  document.getElementById("prd-content").innerHTML = renderMarkdown(markdown);
}

// ---- 트레이스 탭 ------------------------------------------------------------

async function loadRuns() {
  const runs = await api("/api/runs");
  const list = document.getElementById("run-list");
  list.innerHTML = "";
  if (!runs.length) {
    list.appendChild(el("div", { class: "status-text", text: "아직 실행 기록이 없습니다." }));
    return;
  }
  for (const run of runs) {
    const item = el("div", {
      class: "list-item" + (run.run_id === state.selectedRunId ? " active" : ""),
      text: `${run.product_id || "(product 미상)"} · ${run.step_count}단계`,
    });
    item.addEventListener("click", () => {
      state.selectedRunId = run.run_id;
      document.querySelectorAll(".list-item").forEach((n) => n.classList.remove("active"));
      item.classList.add("active");
      loadRunDetail(run.run_id);
    });
    list.appendChild(item);
  }
}

async function loadRunDetail(runId) {
  const records = await api(`/api/runs/${runId}`);
  const container = document.getElementById("run-detail");
  container.innerHTML = "";
  for (const rec of records) {
    const step = el("div", { class: "timeline-step" });
    step.appendChild(el("div", { class: "step-name", text: rec.step }));
    step.appendChild(el("pre", { text: JSON.stringify(rec.output, null, 2) }));
    container.appendChild(step);
  }
}

// ---- HITL 탭 ---------------------------------------------------------------

function setupHitlSubtabs() {
  document.querySelectorAll(".subtab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".subtab-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state.approvalStatus = btn.dataset.status;
      loadApprovals();
    });
  });
}

async function loadApprovals() {
  const items = await api(`/api/approvals?status=${state.approvalStatus}`);
  const body = document.getElementById("approval-body");
  body.innerHTML = "";
  for (const [idx, item] of items.entries()) {
    const report = item.report;
    const tr = el("tr");
    tr.style.setProperty("--i", idx);
    tr.appendChild(el("td", { text: item.approval_id }));
    tr.appendChild(el("td", { text: `${report.model_name} (${report.product_id})` }));
    tr.appendChild(el("td", { text: report.category }));
    tr.appendChild(el("td", {
      html: `<span class="badge badge-critical">${report.critical_defect_count}건</span>`,
    }));
    tr.appendChild(el("td", { text: report.latest_market_share_pct != null ? `${report.latest_market_share_pct}%` : "-" }));
    tr.appendChild(el("td", { text: report.narrative_summary || "-" }));

    const actionCell = el("td");
    if (state.approvalStatus === "pending") {
      const approveBtn = el("button", { text: "승인" });
      approveBtn.addEventListener("click", async () => {
        await api(`/api/approvals/${item.approval_id}/approve`, { method: "POST" });
        loadApprovals();
      });
      const rejectBtn = el("button", { text: "반려" });
      rejectBtn.addEventListener("click", async () => {
        const reason = prompt("반려 사유를 입력하세요", "") || "";
        await api(`/api/approvals/${item.approval_id}/reject`, {
          method: "POST",
          body: JSON.stringify({ reason }),
        });
        loadApprovals();
      });
      actionCell.appendChild(approveBtn);
      actionCell.appendChild(rejectBtn);
    } else if (item.rejected_reason) {
      actionCell.textContent = `사유: ${item.rejected_reason}`;
    }
    tr.appendChild(actionCell);
    body.appendChild(tr);
  }
  if (!items.length) {
    body.appendChild(el("tr", {}, [el("td", { colspan: "7", class: "status-text", text: "해당 상태의 건이 없습니다." })]));
  }
}

// ---- HOTL 탭 ---------------------------------------------------------------

async function loadHotl() {
  const snapshot = await api("/api/hotl");
  document.getElementById("hotl-message").textContent = snapshot.message || "";

  const alertBody = document.getElementById("hotl-alert-body");
  alertBody.innerHTML = "";
  for (const [idx, a] of (snapshot.alerts || []).entries()) {
    const tr = el("tr");
    tr.style.setProperty("--i", idx);
    tr.appendChild(el("td", { text: a.region }));
    tr.appendChild(el("td", { text: a.category }));
    tr.appendChild(el("td", { text: a.quarter }));
    tr.appendChild(el("td", { html: `<span class="badge badge-critical">${a.delta_pp}%p</span>` }));
    alertBody.appendChild(tr);
  }
  if (!(snapshot.alerts || []).length) {
    alertBody.appendChild(el("tr", {}, [el("td", { colspan: "4", class: "status-text", text: "현재 알림이 없습니다." })]));
  }

  const trendBody = document.getElementById("hotl-trend-body");
  trendBody.innerHTML = "";
  for (const [idx, t] of (snapshot.trend || []).slice(-40).entries()) {
    const tr = el("tr");
    tr.style.setProperty("--i", idx);
    tr.appendChild(el("td", { text: t.region }));
    tr.appendChild(el("td", { text: t.category }));
    tr.appendChild(el("td", { text: t.quarter }));
    tr.appendChild(el("td", { text: t.market_share_est_pct.toFixed(1) }));
    trendBody.appendChild(tr);
  }
}

document.getElementById("hotl-refresh-btn").addEventListener("click", async () => {
  await api("/api/hotl/refresh", { method: "POST" });
  loadHotl();
});

// ---- 우선조치 대시보드 탭 ----------------------------------------------------

function fmtNum(n) {
  if (n === null || n === undefined) return "-";
  return Number(n).toLocaleString("ko-KR", { maximumFractionDigits: 2 });
}

function skeletonBars(count) {
  const rows = Array.from({ length: count }, () => '<div class="skeleton-block"></div>').join("");
  return `<div class="skeleton-bars">${rows}</div>`;
}

function skeletonBlock(heightPx) {
  return `<div class="skeleton-block" style="height:${heightPx}px;width:100%;"></div>`;
}

async function loadPriority() {
  const groupBy = document.getElementById("priority-groupby").value;
  const topN = document.getElementById("priority-topn").value || 10;
  document.getElementById("priority-group-col-header").textContent = groupBy;
  document.getElementById("priority-drilldown").style.display = "none";

  const msg = document.getElementById("priority-message");
  const barContainer = document.getElementById("priority-barchart");
  msg.textContent = "";
  barContainer.innerHTML = skeletonBars(5); // 레이아웃 형태를 흉내낸 스켈레톤 -- 빈 텍스트보다 완성도 있게 로딩을 보여준다
  try {
    const outcome = await api(`/api/priority?group_by=${groupBy}&top_n=${topN}`);
    renderPriorityBarChart(outcome.group_by, outcome.ranking);
    renderPriorityTable(outcome.group_by, outcome.ranking);
  } catch (err) {
    barContainer.innerHTML = "";
    msg.textContent = `오류: ${err.message}`;
  }
}

// 순위 랭킹을 숫자 표(아래 renderPriorityTable)뿐 아니라 그래프로도 보여준다 --
// 외부 차트 라이브러리 없이 순수 SVG로 그린 수평 막대그래프.
function renderPriorityBarChart(groupBy, ranking) {
  const container = document.getElementById("priority-barchart");
  container.innerHTML = "";
  if (!ranking.length) return;

  const rowHeight = 32;
  const labelWidth = 110;
  const width = 720;
  const chartWidth = width - labelWidth - 140;
  const height = ranking.length * rowHeight + 12;

  const maxScore = Math.max(1, ...ranking.map((r) => r.impact_score || 0));

  const svgNs = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(svgNs, "svg");
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.setAttribute("width", "100%");
  svg.setAttribute("height", String(height));

  const bars = []; // [barEl, finalWidth][] -- 렌더 직후 0 -> 최종값으로 전환해 자라나는 모션을 준다

  ranking.forEach((row, i) => {
    const y = i * rowHeight + 6;
    const score = Math.max(0, row.impact_score || 0);
    const barW = Math.max(1, (score / maxScore) * chartWidth);

    const label = document.createElementNS(svgNs, "text");
    label.setAttribute("x", "4");
    label.setAttribute("y", String(y + rowHeight / 2 - 8));
    label.setAttribute("class", "chart-bar-label");
    label.textContent = String(row[groupBy]);
    svg.appendChild(label);

    const bar = document.createElementNS(svgNs, "rect");
    bar.setAttribute("x", String(labelWidth));
    bar.setAttribute("y", String(y));
    bar.setAttribute("width", "0");
    bar.setAttribute("height", String(rowHeight - 12));
    bar.setAttribute("rx", "3");
    bar.setAttribute("class", "chart-bar");
    bar.style.transitionDelay = `${i * 45}ms`;
    svg.appendChild(bar);
    bars.push([bar, barW]);

    const value = document.createElementNS(svgNs, "text");
    value.setAttribute("x", String(labelWidth + barW + 6));
    value.setAttribute("y", String(y + rowHeight / 2 - 8));
    value.setAttribute("class", "chart-bar-value");
    value.textContent = row.impact_score != null ? fmtNum(row.impact_score) : "표본 부족";
    svg.appendChild(value);
  });

  container.appendChild(svg);
  // width:0 상태를 강제로 한 번 레이아웃시킨 뒤 최종값으로 바꿔야 transition이
  // 인식된다. requestAnimationFrame은 탭이 백그라운드(비가시)면 실행이 미뤄질
  // 수 있어(예: 이 브라우저 패널이 화면에 그려지지 않는 상황) 대신 동기적인
  // reflow 강제(getBoundingClientRect)를 쓴다 -- 탭 가시성과 무관하게 항상 먹힌다.
  void svg.getBoundingClientRect();
  bars.forEach(([bar, finalWidth]) => bar.setAttribute("width", String(finalWidth)));
}

// product_id/equipment_id/factory_code는 ID만 봐서는 알아보기 어려워, domain.py가
// dim_company_product/dim_equipment에서 붙여준 이름 필드를 표에 보여준다.
function labelFor(groupBy, row) {
  if (groupBy === "product_id") {
    return row.model_name ? `${row.model_name} (${row.company_name})` : "-";
  }
  if (groupBy === "equipment_id") {
    return row.equipment_name ? `${row.equipment_name} · ${row.factory_name}` : "-";
  }
  if (groupBy === "factory_code") {
    return row.factory_name || "-";
  }
  return "-";
}

function renderPriorityTable(groupBy, ranking) {
  const body = document.getElementById("priority-body");
  body.innerHTML = "";

  ranking.forEach((row, idx) => {
    const tr = el("tr");
    tr.style.setProperty("--i", idx);
    tr.classList.add("row-clickable");
    // "월별 추이" 버튼은 없앴다 -- 대신 행 자체를 클릭하면 드릴다운(라인차트+
    // what-if)이 열린다. 액션 버튼(.priority-actions) 클릭까지 드릴다운으로
    // 잡히지 않도록 그 영역 클릭은 무시한다.
    tr.addEventListener("click", (e) => {
      if (e.target.closest(".priority-actions")) return;
      loadPriorityDrilldown(groupBy, row[groupBy]);
    });
    tr.appendChild(el("td", { text: String(idx + 1) }));
    tr.appendChild(el("td", { text: row[groupBy] }));
    tr.appendChild(el("td", { text: labelFor(groupBy, row) }));
    tr.appendChild(el("td", { text: fmtNum(row.impact_score) }));

    let correlationText = "-"; // equipment_id/factory_code 롤업에는 상관계수 개념 자체가 없다
    if (groupBy === "product_id") {
      correlationText = row.correlation != null ? row.correlation.toFixed(4) : "표본 부족";
    }
    tr.appendChild(el("td", { text: correlationText }));
    tr.appendChild(el("td", { text: fmtNum(row.cumulative_revenue_krw) }));

    const sampleText = groupBy === "product_id"
      ? `${row.matched_months ?? "-"}개월`
      : `제품 ${row.scored_product_count ?? "-"}/${row.product_count ?? "-"}`;
    tr.appendChild(el("td", { text: sampleText }));

    const actionCell = el("td", { class: "priority-actions" });

    if (groupBy === "product_id") {
      const reportBtn = el("button", { text: "원인 리포트 발행 요청" });
      reportBtn.addEventListener("click", async () => {
        reportBtn.disabled = true;
        reportBtn.textContent = "요청 중...";
        try {
          const outcome = await api("/api/run", {
            method: "POST",
            body: JSON.stringify({ product_id: row.product_id }),
          });
          reportBtn.textContent = `완료: ${outcome.status}`;
        } catch (err) {
          reportBtn.disabled = false;
          reportBtn.textContent = "원인 리포트 발행 요청";
          alert(`리포트 발행 요청 실패: ${err.message}`);
        }
      });
      actionCell.appendChild(reportBtn);
    }
    tr.appendChild(actionCell);
    body.appendChild(tr);
  });

  if (!ranking.length) {
    body.appendChild(el("tr", {}, [
      el("td", { colspan: "8", class: "status-text", text: "데이터가 없습니다." }),
    ]));
  }
}

const GROUP_LABEL = { product_id: "product_id", equipment_id: "equipment_id", factory_code: "factory_code" };

async function loadPriorityDrilldown(groupBy, entityId) {
  const container = document.getElementById("priority-drilldown");
  const title = document.getElementById("priority-drilldown-title");
  const chart = document.getElementById("priority-chart");
  container.style.display = "block";
  title.textContent = `${GROUP_LABEL[groupBy]}: ${entityId}`;
  chart.innerHTML = skeletonBlock(240);
  state.drilldownGroupBy = groupBy;
  state.drilldownEntityId = entityId;
  try {
    const rows = await api(`/api/priority/monthly/${entityId}?group_by=${groupBy}`);
    chart.innerHTML = "";
    chart.appendChild(renderDualLineChart(rows));
  } catch (err) {
    chart.textContent = `오류: ${err.message}`;
  }
  loadWhatIf(groupBy, entityId); // 목표 불량률 미지정 -> 서버가 과거 최저 불량률을 기본값으로 계산
}

// ---- 매출 영향 what-if (회귀분석) -------------------------------------------

async function loadWhatIf(groupBy, entityId, targetDefectRatePct) {
  const summary = document.getElementById("whatif-summary");
  const chart = document.getElementById("whatif-chart");
  summary.innerHTML = skeletonBars(3);
  chart.innerHTML = skeletonBlock(240);
  try {
    const targetQs = targetDefectRatePct != null ? `&target_defect_rate_pct=${targetDefectRatePct}` : "";
    const [projection, rows] = await Promise.all([
      api(`/api/priority/revenue-projection/${entityId}?group_by=${groupBy}${targetQs}`),
      api(`/api/priority/monthly/${entityId}?group_by=${groupBy}`),
    ]);
    document.getElementById("whatif-target").value = projection.target_defect_rate_pct ?? "";
    summary.innerHTML = renderWhatIfSummary(projection, groupBy);
    chart.appendChild(renderWhatIfChart(rows, projection));
  } catch (err) {
    summary.textContent = `오류: ${err.message}`;
  }
}

function renderWhatIfSummary(p, groupBy) {
  if (p.matched_months < 2 || p.slope_krw_per_pp == null) {
    return `<p class="status-text">매칭된 월(${p.matched_months}개)이 부족하거나 불량률/매출 변동이 없어 회귀분석을 할 수 없습니다.</p>`;
  }
  const direction = p.slope_krw_per_pp < 0 ? "감소" : "증가";
  const deltaSign = p.revenue_delta_krw >= 0 ? "+" : "";
  const confidence = p.r_squared == null ? "-" : `${(p.r_squared * 100).toFixed(1)}%`;
  const approxNote = groupBy === "product_id"
    ? ""
    : `<p class="status-text">※ ${GROUP_LABEL[groupBy]} 단위 매출은 이 축을 거친 제품군의 매출 합계로 근사한 값입니다 (특정 월 실제 생산 배정은 반영하지 않음).</p>`;
  return `
    <p>불량률 1%p당 매출 약 <strong>${fmtNum(Math.abs(p.slope_krw_per_pp))}원 ${direction}</strong> 경향
    (현재 평균 불량률 ${p.current_avg_defect_rate_pct}%, 평균 매출 ${fmtNum(p.current_avg_revenue_krw)}원)</p>
    <p>목표 불량률 <strong>${p.target_defect_rate_pct}%</strong>로 낮추면 예상 매출:
    <strong>${fmtNum(p.projected_revenue_krw)}원</strong>
    (${deltaSign}${fmtNum(p.revenue_delta_krw)}원, ${deltaSign}${p.revenue_delta_pct}%)</p>
    <p class="status-text">회귀선 설명력(R²): ${confidence} · 매칭 월수: ${p.matched_months}개월 --
    상관관계일 뿐 인과관계가 아니며, R²이 낮거나 표본이 적을수록 신뢰도가 낮습니다.</p>
    ${approxNote}
  `;
}

// defect_rate_pct(x) vs revenue_krw(y) 산점도 + 회귀직선 + 목표 지점을 순수 SVG로 그린다.
function renderWhatIfChart(rows, projection) {
  const width = 720;
  const height = 240;
  const padding = 44;

  if (!rows.length) {
    return el("div", { class: "status-text", text: "매칭된 월별 데이터가 없습니다." });
  }

  const xs = rows.map((r) => r.defect_rate_pct);
  const ys = rows.map((r) => r.revenue_krw);
  const allXs = [...xs, projection.target_defect_rate_pct].filter((v) => v != null);
  const allYs = [...ys, projection.projected_revenue_krw].filter((v) => v != null);

  const xMin = Math.min(...allXs);
  const xMax = Math.max(...allXs);
  const yMin = Math.min(...allYs);
  const yMax = Math.max(...allYs);

  const scaleX = (v) => {
    if (xMax === xMin) return width / 2;
    return padding + ((v - xMin) / (xMax - xMin)) * (width - 2 * padding);
  };
  const scaleY = (v) => {
    if (yMax === yMin) return height / 2;
    return height - padding - ((v - yMin) / (yMax - yMin)) * (height - 2 * padding);
  };

  const svgNs = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(svgNs, "svg");
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.setAttribute("width", "100%");
  svg.setAttribute("height", String(height));

  const xAxis = document.createElementNS(svgNs, "line");
  xAxis.setAttribute("x1", String(padding));
  xAxis.setAttribute("y1", String(height - padding));
  xAxis.setAttribute("x2", String(width - padding));
  xAxis.setAttribute("y2", String(height - padding));
  xAxis.setAttribute("class", "chart-axis");
  svg.appendChild(xAxis);

  if (projection.slope_krw_per_pp != null) {
    const line = document.createElementNS(svgNs, "line");
    line.setAttribute("x1", String(scaleX(xMin)));
    line.setAttribute("y1", String(scaleY(projection.slope_krw_per_pp * xMin + projection.intercept_krw)));
    line.setAttribute("x2", String(scaleX(xMax)));
    line.setAttribute("y2", String(scaleY(projection.slope_krw_per_pp * xMax + projection.intercept_krw)));
    line.setAttribute("class", "chart-trendline");
    svg.appendChild(line);
  }

  xs.forEach((x, i) => {
    const dot = document.createElementNS(svgNs, "circle");
    dot.setAttribute("cx", String(scaleX(x)));
    dot.setAttribute("cy", String(scaleY(ys[i])));
    dot.setAttribute("r", "4");
    dot.setAttribute("class", "chart-dot");
    svg.appendChild(dot);
  });

  if (projection.target_defect_rate_pct != null && projection.projected_revenue_krw != null) {
    const target = document.createElementNS(svgNs, "circle");
    target.setAttribute("cx", String(scaleX(projection.target_defect_rate_pct)));
    target.setAttribute("cy", String(scaleY(projection.projected_revenue_krw)));
    target.setAttribute("r", "6");
    target.setAttribute("class", "chart-dot-target");
    svg.appendChild(target);
  }

  const xLabel = document.createElementNS(svgNs, "text");
  xLabel.setAttribute("x", String(width / 2));
  xLabel.setAttribute("y", String(height - 6));
  xLabel.setAttribute("class", "chart-axis-label");
  xLabel.setAttribute("text-anchor", "middle");
  xLabel.textContent = "불량률(%)";
  svg.appendChild(xLabel);

  const wrapper = el("div");
  wrapper.appendChild(svg);
  const legend = el("div", { class: "chart-legend" });
  legend.appendChild(el("span", { class: "legend-item legend-dot", text: "실제 관측월" }));
  legend.appendChild(el("span", { class: "legend-item legend-target", text: "목표 시나리오" }));
  wrapper.appendChild(legend);
  return wrapper;
}

document.getElementById("whatif-recalc-btn").addEventListener("click", () => {
  const target = document.getElementById("whatif-target").value;
  if (state.drilldownEntityId && target !== "") {
    loadWhatIf(state.drilldownGroupBy, state.drilldownEntityId, target);
  }
});

// 외부 차트 라이브러리 없이 순수 SVG로 불량률/시장점유율 이중축 라인차트를 그린다.
function renderDualLineChart(rows) {
  if (!rows.length) {
    return el("div", { class: "status-text", text: "매칭된 월별 데이터가 없습니다 (표본 부족)." });
  }

  const width = 720;
  const height = 240;
  const padding = 36;

  const months = rows.map((r) => String(r.sales_month).slice(0, 7));
  const defect = rows.map((r) => r.defect_rate_pct);
  const share = rows.map((r) => r.market_share_est_pct);

  const scaleX = (i) => padding + (i * (width - 2 * padding)) / Math.max(1, rows.length - 1);
  const scaleY = (v, min, max) => {
    if (max === min) return height / 2;
    return height - padding - ((v - min) / (max - min)) * (height - 2 * padding);
  };

  const dMin = Math.min(...defect);
  const dMax = Math.max(...defect);
  const sMin = Math.min(...share);
  const sMax = Math.max(...share);

  const defectPoints = defect.map((v, i) => `${scaleX(i)},${scaleY(v, dMin, dMax)}`).join(" ");
  const sharePoints = share.map((v, i) => `${scaleX(i)},${scaleY(v, sMin, sMax)}`).join(" ");

  const svgNs = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(svgNs, "svg");
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  svg.setAttribute("width", "100%");
  svg.setAttribute("height", String(height));

  const axis = document.createElementNS(svgNs, "line");
  axis.setAttribute("x1", String(padding));
  axis.setAttribute("y1", String(height - padding));
  axis.setAttribute("x2", String(width - padding));
  axis.setAttribute("y2", String(height - padding));
  axis.setAttribute("class", "chart-axis");
  svg.appendChild(axis);

  const defectLine = document.createElementNS(svgNs, "polyline");
  defectLine.setAttribute("points", defectPoints);
  defectLine.setAttribute("class", "chart-line chart-line-defect");
  svg.appendChild(defectLine);

  const shareLine = document.createElementNS(svgNs, "polyline");
  shareLine.setAttribute("points", sharePoints);
  shareLine.setAttribute("class", "chart-line chart-line-share");
  svg.appendChild(shareLine);

  const labelStep = Math.max(1, Math.ceil(months.length / 8));
  months.forEach((m, i) => {
    if (i % labelStep !== 0) return;
    const text = document.createElementNS(svgNs, "text");
    text.setAttribute("x", String(scaleX(i)));
    text.setAttribute("y", String(height - padding + 14));
    text.setAttribute("class", "chart-axis-label");
    text.setAttribute("text-anchor", "middle");
    text.textContent = m;
    svg.appendChild(text);
  });

  const wrapper = el("div");
  wrapper.appendChild(svg);
  const legend = el("div", { class: "chart-legend" });
  legend.appendChild(el("span", {
    class: "legend-item legend-defect",
    text: `불량률 (${dMin.toFixed(1)}~${dMax.toFixed(1)}%)`,
  }));
  legend.appendChild(el("span", {
    class: "legend-item legend-share",
    text: `시장점유율 (${sMin.toFixed(1)}~${sMax.toFixed(1)}%)`,
  }));
  wrapper.appendChild(legend);
  return wrapper;
}

document.getElementById("priority-groupby").addEventListener("change", loadPriority);
document.getElementById("priority-refresh-btn").addEventListener("click", loadPriority);

// ---- 상단 바: 제품 선택 + 분석 실행 ------------------------------------------

async function loadProducts() {
  const products = await api("/api/products");
  const select = document.getElementById("product-select");
  for (const p of products) {
    select.appendChild(el("option", { value: p.product_id, text: `${p.model_name} (${p.product_id})` }));
  }
}

document.getElementById("run-btn").addEventListener("click", async () => {
  const productId = document.getElementById("product-select").value;
  const statusEl = document.getElementById("run-status");
  if (!productId) { statusEl.textContent = "제품을 먼저 선택하세요."; return; }
  statusEl.textContent = "실행 중...";
  try {
    const outcome = await api("/api/run", { method: "POST", body: JSON.stringify({ product_id: productId }) });
    statusEl.textContent = `완료: ${outcome.status} (run ${outcome.run_id})`;
    if (state.activeTab === "trace") loadRuns();
    if (state.activeTab === "hitl") loadApprovals();
  } catch (err) {
    statusEl.textContent = `오류: ${err.message}`;
  }
});

// ---- 초기화 ----------------------------------------------------------------

setupTabs();
setupHitlSubtabs();
loadProducts();
loadPrd();
