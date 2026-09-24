const state = { jobs: [], resumes: [], latestResult: null };

const $ = (selector) => document.querySelector(selector);
const escapeHtml = (value) => String(value ?? "")
  .replaceAll("&", "&amp;").replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");

function toast(message) {
  const element = $("#toast");
  element.textContent = message;
  element.classList.add("show");
  window.clearTimeout(toast.timer);
  toast.timer = window.setTimeout(() => element.classList.remove("show"), 2200);
}

function currentJob(selectId = "#job-select") {
  return state.jobs.find((job) => job.job_id === $(selectId).value);
}

function populateJobSelect(selector) {
  const select = $(selector);
  select.innerHTML = state.jobs.map((job) =>
    `<option value="${escapeHtml(job.job_id)}">${escapeHtml(job.title)} · ${escapeHtml(job.location)}</option>`
  ).join("");
}

function renderJobDetail() {
  const job = currentJob();
  if (!job) return;
  const skills = job.required_skills.split("|").map((skill) => `<span>${escapeHtml(skill)}</span>`).join("");
  $("#job-detail").innerHTML = `${escapeHtml(job.description)}
    <div class="job-meta"><span>${escapeHtml(job.min_education)}及以上</span><span>${escapeHtml(job.min_years)}年以上</span>${skills}</div>`;
}

function populateResumes() {
  const select = $("#sample-select");
  select.innerHTML += state.resumes.map((resume) =>
    `<option value="${escapeHtml(resume.resume_id)}">${escapeHtml(resume.name)} · ${escapeHtml(resume.target_role)}</option>`
  ).join("");
}

function updateCharCount() {
  $("#char-count").textContent = `${$("#resume-text").value.trim().length} 字`;
}

function scoreColor(score) {
  if (score >= 80) return "#0f7957";
  if (score >= 65) return "#3b8f72";
  if (score >= 50) return "#d19031";
  return "#b05748";
}

function renderResult(job, result) {
  state.latestResult = { job, result, generated_at: new Date().toLocaleString("zh-CN") };
  const dimensions = [
    ["文本相似度", result.scores.semantic, "40%"],
    ["技能覆盖", result.scores.skill, "35%"],
    ["经验匹配", result.scores.experience, "15%"],
    ["学历匹配", result.scores.education, "10%"],
  ];
  const tags = (items, type, emptyText) => items.length
    ? items.map((item) => `<span class="tag ${type}">${escapeHtml(item)}</span>`).join("")
    : `<span class="tag ${type}">${emptyText}</span>`;
  const list = (items) => items.map((item) => `<li>${escapeHtml(item)}</li>`).join("");
  const color = scoreColor(result.total_score);
  $("#result-content").innerHTML = `
    <div class="score-hero">
      <div class="score-ring" style="--score:${result.total_score};background:conic-gradient(${color} calc(var(--score) * 1%),#e7eee9 0)">
        <div class="score-value"><strong>${result.total_score}</strong><span>综合匹配分 / 100</span></div>
      </div>
      <div class="score-copy"><span class="decision-label">${escapeHtml(result.recommendation)}</span><h2>${escapeHtml(result.decision)}</h2>
        <p>目标岗位：${escapeHtml(job.title)}。评分用于辅助初筛，建议结合面试与材料核验。</p></div>
    </div>
    <div class="dimension-grid">${dimensions.map(([name, score, weight]) => `
      <div class="dimension"><div class="dimension-head"><span>${name} · 权重 ${weight}</span><strong>${score}</strong></div>
      <div class="bar"><i style="width:${score}%"></i></div></div>`).join("")}</div>
    <div class="result-section"><h3>已匹配技能 · ${result.matched_skills.length}/${result.required_skills.length}</h3>
      <div class="tag-list">${tags(result.matched_skills, "match", "暂无明确匹配")}</div></div>
    <div class="result-section"><h3>待补充技能</h3>
      <div class="tag-list">${tags(result.missing_skills, "missing", "无明显技能缺口")}</div></div>
    <div class="insight-grid">
      <div class="insight"><strong>✓ 匹配亮点</strong><ul>${list(result.strengths)}</ul></div>
      <div class="insight"><strong>! 复核要点</strong><ul>${list(result.risks)}</ul></div>
    </div>
    <div class="result-foot"><span>本地生成 · 不含敏感人口属性</span><button id="download-result" class="ghost-button">导出 JSON 结果</button></div>`;
  $("#empty-result").classList.add("hidden");
  $("#result-content").classList.remove("hidden");
  $("#download-result").addEventListener("click", downloadResult);
}

async function requestJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok || !data.ok) throw new Error(data.error || "请求失败");
  return data;
}

async function runMatch() {
  const button = $("#match-button");
  const resumeText = $("#resume-text").value.trim();
  if (!resumeText) { toast("请先输入或选择一份简历"); return; }
  button.disabled = true;
  button.querySelector("span").textContent = "正在分析…";
  try {
    const data = await requestJson("/api/match", { job_id: $("#job-select").value, resume_text: resumeText });
    renderResult(data.job, data.result);
    toast("分析完成，结果已在本地生成");
  } catch (error) {
    toast(error.message);
  } finally {
    button.disabled = false;
    button.querySelector("span").textContent = "开始智能分析";
  }
}

async function runRank() {
  const button = $("#rank-button");
  button.disabled = true;
  try {
    const data = await requestJson("/api/rank", { job_id: $("#rank-job-select").value });
    $("#rank-summary").textContent = `已完成 ${data.results.length} 份匿名简历评分 · 当前岗位：${data.job.title} · 前 3 名建议优先复核`;
    $("#rank-summary").classList.remove("hidden");
    $("#rank-body").innerHTML = data.results.map((item) => `<tr>
      <td><span class="rank-number">${item.rank}</span></td><td><strong>${escapeHtml(item.name)}</strong><br><small>${escapeHtml(item.resume_id)}</small></td>
      <td>${escapeHtml(item.target_role)}</td><td><span class="score-pill">${item.total_score}</span></td>
      <td>${item.matched_skills.length}/${item.required_skills.length}</td><td>${escapeHtml(item.recommendation)}</td></tr>`).join("");
    toast("批量排名已生成");
  } catch (error) {
    toast(error.message);
  } finally {
    button.disabled = false;
  }
}

function downloadResult() {
  if (!state.latestResult) return;
  const blob = new Blob([JSON.stringify(state.latestResult, null, 2)], { type: "application/json;charset=utf-8" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `匹配结果_${state.latestResult.job.title}.json`;
  link.click();
  URL.revokeObjectURL(link.href);
}

function bindEvents() {
  document.querySelectorAll(".nav-item").forEach((button) => button.addEventListener("click", () => {
    document.querySelectorAll(".nav-item,.view-panel").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    $(`#${button.dataset.view}`).classList.add("active");
  }));
  $("#job-select").addEventListener("change", renderJobDetail);
  $("#resume-text").addEventListener("input", updateCharCount);
  $("#sample-select").addEventListener("change", (event) => {
    const resume = state.resumes.find((item) => item.resume_id === event.target.value);
    if (resume) { $("#resume-text").value = resume.full_text; updateCharCount(); }
  });
  $("#file-input").addEventListener("change", async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    if (file.size > 2 * 1024 * 1024) { toast("文件超过 2 MB 限制"); return; }
    $("#resume-text").value = await file.text();
    $("#file-name").textContent = file.name;
    updateCharCount();
  });
  $("#match-button").addEventListener("click", runMatch);
  $("#rank-button").addEventListener("click", runRank);
}

async function init() {
  try {
    const response = await fetch("/api/bootstrap");
    const data = await response.json();
    state.jobs = data.jobs;
    state.resumes = data.resumes;
    $("#job-count").textContent = data.stats.job_count;
    $("#resume-count").textContent = data.stats.resume_count;
    populateJobSelect("#job-select");
    populateJobSelect("#rank-job-select");
    populateResumes();
    renderJobDetail();
    bindEvents();
  } catch (error) {
    toast("初始化失败，请确认本地服务正在运行");
    console.error(error);
  }
}

init();
