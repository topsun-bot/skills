(() => {
  "use strict";

  const data = window.DECK_DATA;
  if (!data || !Array.isArray(data.pages) || !data.pages.length) {
    document.body.innerHTML = "<p style='padding:2rem'>deck-data.js 中没有可显示的页面。</p>";
    return;
  }

  const $ = (id) => document.getElementById(id);
  const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[character]));
  const safeUrl = (value) => {
    try {
      const url = new URL(String(value), window.location.href);
      return ["http:", "https:"].includes(url.protocol) ? url.href : "#";
    } catch { return "#"; }
  };
  const state = { index: 0, mode: "explore", fx: true, sound: false, elapsed: 0, timer: null, history: [] };
  const elements = {
    brandTitle: $("brandTitle"), brandSubtitle: $("brandSubtitle"), breadcrumbTitle: $("breadcrumbTitle"), historyBackButton: $("historyBackButton"),
    slide: $("slide"), heroImage: $("heroImage"), generatedVisual: $("generatedVisual"),
    pageNumber: $("pageNumber"), chapter: $("chapter"), pageTitle: $("pageTitle"), pageSubtitle: $("pageSubtitle"), pageClaim: $("pageClaim"),
    hotspots: $("hotspots"), knowledgeCard: $("knowledgeCard"), prevButton: $("prevButton"), nextButton: $("nextButton"),
    presentIndex: $("presentIndex"), presentTotal: $("presentTotal"), progress: $("progress"), timer: $("timer"),
    mapDialog: $("mapDialog"), mapGrid: $("mapGrid"), notesDrawer: $("notesDrawer"), evidenceDrawer: $("evidenceDrawer"),
    notesMeta: $("notesMeta"), notesTitle: $("notesTitle"), visualCue: $("visualCue"), speakerNotes: $("speakerNotes"), transition: $("transition"),
    evidenceMeta: $("evidenceMeta"), evidenceTitle: $("evidenceTitle"), boundary: $("boundary"), sourceList: $("sourceList"), toast: $("toast")
  };

  document.documentElement.lang = data.meta.language || "zh-CN";
  document.title = data.meta.title;
  elements.brandTitle.textContent = data.meta.label || "VISUAL FIELD NOTES";
  elements.brandSubtitle.textContent = data.meta.title;

  function page() { return data.pages[state.index]; }
  function pad(value) { return String(value).padStart(2, "0"); }

  function visualPattern(current) {
    const hue = (state.index * 47 + 162) % 360;
    elements.generatedVisual.style.setProperty("--page-hue", hue);
    elements.generatedVisual.innerHTML = `
      <span class="orbit orbit-a"></span><span class="orbit orbit-b"></span>
      <span class="sketch sketch-a"></span><span class="sketch sketch-b"></span>
      <span class="folio">${escapeHtml(current.id)}</span>`;
  }

  function playTick() {
    if (!state.sound) return;
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextClass) return;
    const context = new AudioContextClass();
    const oscillator = context.createOscillator();
    const gain = context.createGain();
    oscillator.frequency.value = 410;
    gain.gain.setValueAtTime(0.025, context.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.0001, context.currentTime + 0.07);
    oscillator.connect(gain).connect(context.destination);
    oscillator.start(); oscillator.stop(context.currentTime + 0.07);
    oscillator.addEventListener("ended", () => context.close());
  }

  function closeKnowledge() {
    elements.knowledgeCard.hidden = true;
    elements.knowledgeCard.innerHTML = "";
  }

  function openKnowledge(hotspot) {
    const sources = (hotspot.sources || []).map((index) => page().evidence?.[index]).filter(Boolean);
    elements.knowledgeCard.innerHTML = `
      <button class="round-close" type="button" aria-label="关闭知识卡">×</button>
      <p class="dialog-label">${hotspot.targetPage ? "BRANCH" : "DETAIL"}</p>
      <h3>${escapeHtml(hotspot.title)}</h3><strong>${escapeHtml(hotspot.summary)}</strong><p>${escapeHtml(hotspot.detail)}</p>
      ${sources.map((source) => source.url ? `<a href="${escapeHtml(safeUrl(source.url))}" target="_blank" rel="noreferrer">↗ ${escapeHtml(source.label)}</a>` : `<span>↗ ${escapeHtml(source.label)}</span>`).join("")}
      ${hotspot.targetPage ? `<button class="branch-button" type="button">继续深入 →</button>` : ""}`;
    elements.knowledgeCard.hidden = false;
    elements.knowledgeCard.querySelector(".round-close").addEventListener("click", closeKnowledge);
    const branchButton = elements.knowledgeCard.querySelector(".branch-button");
    if (branchButton) branchButton.addEventListener("click", () => goToId(hotspot.targetPage, true));
  }

  function renderHotspots(current) {
    elements.hotspots.innerHTML = "";
    (current.hotspots || []).forEach((hotspot) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `hotspot ${hotspot.targetPage ? "branch" : "local"}`;
      button.style.cssText = `left:${hotspot.x}%;top:${hotspot.y}%;width:${hotspot.w}%;height:${hotspot.h}%`;
      button.setAttribute("aria-label", `${hotspot.title}：${hotspot.summary || "打开解释"}`);
      button.innerHTML = `<span class="hotspot-dot">${hotspot.targetPage ? "↗" : "+"}</span><span class="hotspot-copy"><em>${hotspot.targetPage ? "可继续深入" : "本页图解"}</em><b>${escapeHtml(hotspot.title)}</b><small>${escapeHtml(hotspot.summary)}</small></span>`;
      button.addEventListener("click", () => openKnowledge(hotspot));
      elements.hotspots.appendChild(button);
    });
  }

  function renderDrawers(current) {
    elements.notesMeta.textContent = `第 ${current.id} 页 · 约 ${current.durationSeconds} 秒`;
    elements.notesTitle.textContent = current.title;
    elements.visualCue.textContent = current.visualCue || "先让观众看图，再给出本页结论。";
    elements.speakerNotes.innerHTML = (current.speakerNotes || []).map((item) => `<p>${escapeHtml(item)}</p>`).join("");
    elements.transition.textContent = current.transition || "翻到下一页。";
    elements.evidenceMeta.textContent = `第 ${current.id} 页 · 内容依据`;
    elements.evidenceTitle.textContent = current.title;
    elements.boundary.textContent = current.boundary || "本页未提供额外适用边界。";
    const evidence = current.evidence || [];
    elements.sourceList.innerHTML = evidence.length ? evidence.map((source, index) => `
      ${source.url ? `<a href="${escapeHtml(safeUrl(source.url))}" target="_blank" rel="noreferrer">` : "<div>"}
        <span>${pad(index + 1)}</span><div><strong>${escapeHtml(source.label)}</strong><small>${escapeHtml(source.publisher)}${source.note ? ` · ${escapeHtml(source.note)}` : ""}</small></div><b>↗</b>
      ${source.url ? "</a>" : "</div>"}`).join("") : "<p class='empty-state'>本页依据来自提供的材料，尚未附加外部链接。</p>";
  }

  function renderMap() {
    elements.mapGrid.innerHTML = data.pages.map((item, index) => `
      <button type="button" data-index="${index}" class="${index === state.index ? "current" : ""}">
        <span class="map-art" style="--map-hue:${(index * 47 + 162) % 360}"><i>${escapeHtml(item.id)}</i></span>
        <small>${escapeHtml(item.chapter || "PAGE")}</small><strong>${escapeHtml(item.title)}</strong>${item.deepDive ? "<em>深入</em>" : ""}
      </button>`).join("");
    elements.mapGrid.querySelectorAll("button").forEach((button) => button.addEventListener("click", () => {
      goTo(Number(button.dataset.index)); elements.mapDialog.close();
    }));
  }

  function renderProgress() {
    elements.progress.innerHTML = data.pages.map((item, index) => `<button type="button" aria-label="前往第${index + 1}页" class="${index === state.index ? "current" : index < state.index ? "passed" : ""}"><span>${escapeHtml(item.id)}</span></button>`).join("");
    elements.progress.querySelectorAll("button").forEach((button, index) => button.addEventListener("click", () => goTo(index)));
  }

  function render() {
    const current = page();
    closeKnowledge(); closeDrawers();
    elements.slide.dataset.layout = current.layout || "left";
    elements.breadcrumbTitle.textContent = current.title;
    elements.pageNumber.textContent = current.id;
    elements.chapter.textContent = current.chapter || "";
    elements.pageTitle.textContent = current.title;
    elements.pageSubtitle.textContent = current.subtitle || "";
    elements.pageClaim.textContent = current.claim || "";
    elements.presentIndex.textContent = current.id;
    elements.presentTotal.textContent = `/ ${pad(data.pages.length)}`;
    elements.prevButton.disabled = state.index === 0;
    elements.nextButton.disabled = state.index === data.pages.length - 1;
    elements.historyBackButton.disabled = state.history.length === 0;
    if (current.image) {
      elements.heroImage.src = current.image;
      elements.heroImage.alt = current.imageAlt || "";
      elements.heroImage.hidden = false;
      elements.generatedVisual.hidden = true;
    } else {
      elements.heroImage.hidden = true;
      elements.generatedVisual.hidden = false;
      visualPattern(current);
    }
    renderHotspots(current); renderDrawers(current); renderProgress(); renderMap();
    if (state.fx) { elements.slide.classList.remove("enter"); requestAnimationFrame(() => elements.slide.classList.add("enter")); }
  }

  function goTo(index, fromBranch = false) {
    if (index < 0 || index >= data.pages.length || index === state.index) return;
    if (fromBranch) state.history.push(state.index);
    state.index = index; playTick(); resetTimer(); render();
  }

  function goToId(id, fromBranch = false) {
    const index = data.pages.findIndex((item) => String(item.id) === String(id));
    if (index >= 0) goTo(index, fromBranch);
  }

  function goBack() {
    if (!state.history.length) return;
    state.index = state.history.pop(); playTick(); resetTimer(); render();
  }

  function setMode(mode) {
    state.mode = mode;
    document.body.dataset.mode = mode;
    $("exploreMode").classList.toggle("active", mode === "explore");
    $("presentMode").classList.toggle("active", mode === "present");
    $("exploreMode").setAttribute("aria-pressed", String(mode === "explore"));
    $("presentMode").setAttribute("aria-pressed", String(mode === "present"));
    closeKnowledge();
  }

  function toggleDrawer(drawer) {
    const open = drawer.getAttribute("aria-hidden") === "false";
    closeDrawers();
    if (!open) { drawer.setAttribute("aria-hidden", "false"); drawer.inert = false; }
  }

  function closeDrawers() {
    elements.notesDrawer.setAttribute("aria-hidden", "true");
    elements.evidenceDrawer.setAttribute("aria-hidden", "true");
    elements.notesDrawer.inert = true;
    elements.evidenceDrawer.inert = true;
  }

  function resetTimer() {
    clearInterval(state.timer); state.timer = null; state.elapsed = 0; elements.timer.textContent = "00:00";
    $("playButton").textContent = "▶ 计时本页";
  }

  function toggleTimer() {
    if (state.timer) { clearInterval(state.timer); state.timer = null; $("playButton").textContent = "▶ 继续计时"; return; }
    $("playButton").textContent = "❚❚ 暂停计时";
    state.timer = setInterval(() => {
      state.elapsed += 1;
      elements.timer.textContent = `${pad(Math.floor(state.elapsed / 60))}:${pad(state.elapsed % 60)}`;
    }, 1000);
  }

  function showToast(message) {
    elements.toast.textContent = message; elements.toast.classList.add("show");
    window.setTimeout(() => elements.toast.classList.remove("show"), 1400);
  }

  async function copyText(text) {
    try { await navigator.clipboard.writeText(text); showToast("已复制"); }
    catch { showToast("浏览器未允许复制"); }
  }

  function pageScript(item) {
    return `${item.id} ${item.title}\n\n${(item.speakerNotes || []).join("\n\n")}\n\n转场：${item.transition || ""}`;
  }

  $("brandButton").addEventListener("click", () => goTo(0));
  $("overviewButton").addEventListener("click", () => { renderMap(); elements.mapDialog.showModal(); });
  elements.historyBackButton.addEventListener("click", goBack);
  $("exploreMode").addEventListener("click", () => setMode("explore"));
  $("presentMode").addEventListener("click", () => setMode("present"));
  $("mapButton").addEventListener("click", () => { renderMap(); elements.mapDialog.showModal(); });
  $("fxButton").addEventListener("click", (event) => { state.fx = !state.fx; event.currentTarget.classList.toggle("active", state.fx); event.currentTarget.setAttribute("aria-pressed", String(state.fx)); document.body.classList.toggle("no-fx", !state.fx); });
  $("soundButton").addEventListener("click", (event) => { state.sound = !state.sound; event.currentTarget.classList.toggle("active", state.sound); event.currentTarget.setAttribute("aria-pressed", String(state.sound)); playTick(); });
  $("fullscreenButton").addEventListener("click", async () => {
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else await document.documentElement.requestFullscreen();
    } catch {
      showToast("当前浏览器未允许全屏");
    }
  });
  elements.prevButton.addEventListener("click", () => goTo(state.index - 1));
  elements.nextButton.addEventListener("click", () => goTo(state.index + 1));
  $("notesButton").addEventListener("click", () => toggleDrawer(elements.notesDrawer));
  $("evidenceButton").addEventListener("click", () => toggleDrawer(elements.evidenceDrawer));
  $("playButton").addEventListener("click", toggleTimer); $("timerButton").addEventListener("click", toggleTimer);
  $("copyPage").addEventListener("click", () => copyText(pageScript(page())));
  $("copyAll").addEventListener("click", () => copyText(data.pages.map(pageScript).join("\n\n---\n\n")));
  document.querySelectorAll("[data-close]").forEach((button) => button.addEventListener("click", () => { const drawer = $(button.dataset.close); drawer.setAttribute("aria-hidden", "true"); drawer.inert = true; }));

  document.addEventListener("keydown", (event) => {
    if (["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement?.tagName)) return;
    if (event.key === "ArrowRight" || event.key === "PageDown") goTo(state.index + 1);
    if (event.key === "ArrowLeft" || event.key === "PageUp") goTo(state.index - 1);
    if (event.key.toLowerCase() === "m" && !elements.mapDialog.open) elements.mapDialog.showModal();
    if (event.key.toLowerCase() === "n") toggleDrawer(elements.notesDrawer);
    if (event.key.toLowerCase() === "r") toggleDrawer(elements.evidenceDrawer);
    if (event.key.toLowerCase() === "x") $("fxButton").click();
    if (event.key.toLowerCase() === "s") $("soundButton").click();
    if (event.key.toLowerCase() === "f") $("fullscreenButton").click();
    if (event.key === "Escape") { closeDrawers(); closeKnowledge(); }
  });

  setMode("explore"); render();
})();
