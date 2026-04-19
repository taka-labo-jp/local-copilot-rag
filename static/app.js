/* ===================================================
   Spec Copilot — app.js
   ファイルアップロード / チャット(SSE) / 履歴管理
   =================================================== */

marked.setOptions({ breaks: true, gfm: true });

// ---- DOM 参照 ----
const messagesEl     = document.getElementById("messagesEl");
const welcomeEl      = document.getElementById("welcomeEl");
const inputEl        = document.getElementById("inputEl");
const sendBtn        = document.getElementById("sendBtn");
const modelSelect    = document.getElementById("modelSelect");
const sessionTitle   = document.getElementById("sessionTitle");
const languageSelect = document.getElementById("languageSelect");
const themeToggleBtn = document.getElementById("themeToggleBtn");
const historyList    = document.getElementById("historyList");
const historyBadge   = document.getElementById("historyBadge");
const docList        = document.getElementById("docList");
const docBadge       = document.getElementById("docBadge");
const contextBar     = document.getElementById("contextBar");
const docFilter      = document.getElementById("docFilter");
const fileInput      = document.getElementById("fileInput");
const uploadArea     = document.getElementById("uploadArea");
const uploadProgress = document.getElementById("uploadProgress");
const uploadBar      = document.getElementById("uploadBar");
const uploadStatus   = document.getElementById("uploadStatus");
const bulkUploadBtn  = document.getElementById("bulkUploadBtn");
const addProjectBtn  = document.getElementById("addProjectBtn");
const uploadProjectSelect = document.getElementById("uploadProjectSelect");
const projectDialogBackdrop = document.getElementById("projectDialogBackdrop");
const projectDialogInput = document.getElementById("projectDialogInput");
const projectDialogCancel = document.getElementById("projectDialogCancel");
const projectDialogCreate = document.getElementById("projectDialogCreate");
const newChatBtn     = document.getElementById("newChatBtn");
const toastContainer = document.getElementById("toastContainer");
const reasoningModeToggle = document.getElementById("reasoningModeToggle");
const wingFilter = document.getElementById("wingFilter");
const roomFilter = document.getElementById("roomFilter");
const contentTypeFilter = document.getElementById("contentTypeFilter");
const advancedScopeSummary = document.getElementById("advancedScopeSummary");
const contextChips = document.getElementById("contextChips");
const retrievalPanel = document.getElementById("retrievalPanel");
const retrievalToggle = document.getElementById("retrievalToggle");
const retrievalMeta = document.getElementById("retrievalMeta");
const retrievalBody = document.getElementById("retrievalBody");
const sidebar = document.querySelector(".sidebar");
const sidebarToggleBtn = document.getElementById("sidebarToggleBtn");
const resizeHandle = document.getElementById("resizeHandle");

// セクション開閉
const docSectionToggle     = document.getElementById("docSectionToggle");
const docSectionBody       = document.getElementById("docSectionBody");
const historySectionToggle = document.getElementById("historySectionToggle");
const historySectionBody   = document.getElementById("historySectionBody");

// ---- 状態 ----
let currentSessionId = null;
let isStreaming = false;
let allDocs = [];
let allProjects = [];
let selectedContexts = [];
let draggingDocId = null;
let sidebarWidth = Number(localStorage.getItem("spec-copilot.sidebarWidth") || 300);
let sidebarCollapsed = localStorage.getItem("spec-copilot.sidebarCollapsed") === "1";
let currentLang = localStorage.getItem("spec-copilot.lang") || "ja";
let currentTheme = localStorage.getItem("spec-copilot.theme") || "";

const DEFAULT_SIDEBAR_WIDTH = 300;
const MIN_SIDEBAR_WIDTH = 200;
const MAX_SIDEBAR_WIDTH = 600;
const COLLAPSE_THRESHOLD = 160;

const I18N = {
  ja: {
    newChat: "新しい会話",
    docs: "仕様書",
    history: "会話履歴",
    toolsSummary: "アップロードと整理",
    uploadDrop: "アップロード / ドロップ",
    bulkUpload: "一括アップロード（フォルダ再帰）",
    bulkUploadNote: "対象フォルダ: bulk_uploads（再帰）",
    uploadTargetUnclassified: "アップロード先: 未分類",
    uploadTargetProject: "アップロード先: {name}",
    addProject: "プロジェクト追加",
    filterByFilename: "ファイル名で絞込...",
    retrievalLog: "検索診断ログ",
    retrievalCount: "{count}件",
    welcomeTitle: "仕様書 RAG チャット",
    welcomeDesc: "仕様書ファイル（Word / Excel / PDF など）をサイドバーからアップロードし、内容について質問してください。",
    welcomeSubDesc: "GitHub Copilot SDK がローカル知識ベースを検索し、仕様に基づいた回答を生成します。",
    reasoningModeLabel: "推論あり",
    reasoningModeTitle: "推論ありモード: 仕様書を踏まえた設計提案・スキーマ検討を許可します",
    modelLoading: "読み込み中...",
    advancedFilterAll: "詳細フィルタ: すべて",
    advancedFilterPrefix: "詳細フィルタ",
    wingAll: "対象wing: すべて",
    roomPlaceholder: "対象room（任意）",
    typeAll: "対象種別: すべて",
    typeText: "テキスト",
    typeTable: "表",
    typeImage: "画像",
    typeVisualPage: "ページOCR",
    contextTitle: "読み込むコンテキスト（⊕ ボタンまたは右クリックで追加）",
    contextEmpty: "未選択（全仕様書を対象）",
    inputPlaceholder: "仕様について質問してください… (Enter で送信 / Shift+Enter で改行)",
    send: "送信",
    projectDialogTitle: "プロジェクト追加",
    projectDialogHelp: "仕様書を整理するためのプロジェクト名を入力してください。",
    projectDialogPlaceholder: "例: 新サービスA",
    cancel: "キャンセル",
    create: "作成",
    copyAnswer: "回答をコピー",
    copyFailed: "コピーに失敗しました",
    contextAdded: "コンテキストに追加: {name}",
    contextAddedCount: "コンテキストに追加: {count}件",
    sidebarOpen: "サイドバーを開く",
    sidebarClose: "サイドバーを折りたたむ",
    retrievalNoLogs: "この会話では検索ログがまだありません。",
    retrievalFetchFailed: "取得失敗",
    retrievalFetchError: "retrievalログ取得失敗",
    retrievalLimit: "取得上限: {count}件",
    retrievalHit: "ヒット: {count}件",
    retrievalLatency: "検索時間: {ms}ms",
    retrievalVectorHit: "ベクトル候補: {count}件",
    retrievalKeywordHit: "キーワード一致: {count}件",
    retrievalWing: "対象wing: {value}",
    retrievalRoom: "対象room: {value}",
    retrievalType: "対象種別: {value}",
    retrievalFiles: "対象ファイル: {value}",
    modelFetchZero: "モデル取得0件",
    modelFetchFallback: "モデル取得失敗、フォールバック使用:",
    chatError: "エラー: {message}",
    chatNoResponse: "（応答がありませんでした）",
    historyFetchFailed: "履歴取得失敗",
    advancedFilterWing: "wing: {value}",
    advancedFilterRoom: "room: {value}",
    advancedFilterType: "種別: {value}",
    projectFetchFailed: "プロジェクト取得失敗",
    projectCreated: "プロジェクトを作成: {name}",
    createFailed: "作成失敗: {message}",
    movedToProject: "移動しました: {project}",
    moveFailed: "移動失敗: {message}",
    deleteSessionDone: "削除しました",
    sessionLoadFailed: "セッション読み込み失敗: {message}",
    deleteFailed: "削除失敗: {message}",
    projectDeleted: "プロジェクトを削除: {name}",
    projectDeleteFailed: "プロジェクト削除失敗: {message}",
    noRegistration: "まだ登録なし",
    unclassified: "未分類",
    noDocsInProject: "仕様書はまだありません",
    docDeleteTitle: "削除",
    addProjectContext: "このプロジェクトをコンテキストに追加",
    deleteEmptyProject: "空のプロジェクトを削除",
    addGroupContext: "この分類をコンテキストに追加",
    addDocContext: "この仕様書をコンテキストに追加",
    registeredCount: "登録: {count}件",
    docsCount: "{count}件",
    fileGroupWord: "Word",
    fileGroupExcel: "Excel",
    fileGroupPpt: "PowerPoint",
    fileGroupPdf: "PDF",
    fileGroupStructured: "JSON/XML",
    fileGroupArchive: "ePub/ZIP",
    fileGroupOther: "その他",
    uploadOverwrite: "（上書き: {overwritten}件, 削除チャンク: {deleted}件）",
    docListFetchFailed: "ドキュメント一覧取得失敗",
    docDeleteDone: "🗑️ {name} を削除しました",
    uploadDone: "完了",
    uploadDoneItem: "✅ {name} — {count}件登録 {overwrite}",
    uploadFailedItem: "❌ {name}: {message}",
    bulkUploadDone: "一括アップロード完了: {uploaded}/{total} 件（失敗: {failed}）",
    bulkUploadFailed: "一括アップロード失敗: {message}",
    modelLabelJp: "日本語",
    modelLabelEn: "English",
    themeSwitch: "テーマ切替",
    languageSwitch: "言語",
  },
  en: {
    newChat: "New chat",
    docs: "Documents",
    history: "History",
    toolsSummary: "Upload and organize",
    uploadDrop: "Upload / Drop",
    bulkUpload: "Bulk upload (recursive folder)",
    bulkUploadNote: "Target folder: bulk_uploads (recursive)",
    uploadTargetUnclassified: "Upload target: Unclassified",
    uploadTargetProject: "Upload target: {name}",
    addProject: "Add project",
    filterByFilename: "Filter by filename...",
    retrievalLog: "Retrieval diagnostics",
    retrievalCount: "{count} items",
    welcomeTitle: "Specification RAG Chat",
    welcomeDesc: "Upload specification files (Word / Excel / PDF, etc.) from the sidebar and ask questions.",
    welcomeSubDesc: "GitHub Copilot SDK searches the local knowledge base and generates spec-grounded answers.",
    reasoningModeLabel: "Reasoning",
    reasoningModeTitle: "Reasoning mode: allows design proposals and schema discussions grounded in documents.",
    modelLoading: "Loading...",
    advancedFilterAll: "Advanced filter: All",
    advancedFilterPrefix: "Advanced filter",
    wingAll: "Wing: All",
    roomPlaceholder: "Room (optional)",
    typeAll: "Content type: All",
    typeText: "Text",
    typeTable: "Table",
    typeImage: "Image",
    typeVisualPage: "Page OCR",
    contextTitle: "Context for retrieval (add with ⊕ button or right-click)",
    contextEmpty: "None selected (all documents are used)",
    inputPlaceholder: "Ask about specs... (Enter to send / Shift+Enter for newline)",
    send: "Send",
    projectDialogTitle: "Add project",
    projectDialogHelp: "Enter a project name to organize documents.",
    projectDialogPlaceholder: "e.g. New Service A",
    cancel: "Cancel",
    create: "Create",
    copyAnswer: "Copy answer",
    copyFailed: "Failed to copy",
    contextAdded: "Added to context: {name}",
    contextAddedCount: "Added to context: {count} files",
    sidebarOpen: "Open sidebar",
    sidebarClose: "Collapse sidebar",
    retrievalNoLogs: "No retrieval logs in this chat yet.",
    retrievalFetchFailed: "Failed",
    retrievalFetchError: "Failed to fetch retrieval logs",
    retrievalLimit: "Requested: {count}",
    retrievalHit: "Hits: {count}",
    retrievalLatency: "Latency: {ms}ms",
    retrievalVectorHit: "Vector hits: {count}",
    retrievalKeywordHit: "Keyword matches: {count}",
    retrievalWing: "Wing: {value}",
    retrievalRoom: "Room: {value}",
    retrievalType: "Type: {value}",
    retrievalFiles: "Files: {value}",
    modelFetchZero: "No models returned",
    modelFetchFallback: "Failed to load models. Using fallback:",
    chatError: "Error: {message}",
    chatNoResponse: "(No response returned)",
    historyFetchFailed: "Failed to load history",
    advancedFilterWing: "wing: {value}",
    advancedFilterRoom: "room: {value}",
    advancedFilterType: "type: {value}",
    projectFetchFailed: "Failed to load projects",
    projectCreated: "Project created: {name}",
    createFailed: "Create failed: {message}",
    movedToProject: "Moved to: {project}",
    moveFailed: "Move failed: {message}",
    deleteSessionDone: "Deleted",
    sessionLoadFailed: "Failed to load session: {message}",
    deleteFailed: "Delete failed: {message}",
    projectDeleted: "Project deleted: {name}",
    projectDeleteFailed: "Project delete failed: {message}",
    noRegistration: "No documents yet",
    unclassified: "Unclassified",
    noDocsInProject: "No documents yet",
    docDeleteTitle: "Delete",
    addProjectContext: "Add this project to context",
    deleteEmptyProject: "Delete empty project",
    addGroupContext: "Add this category to context",
    addDocContext: "Add this document to context",
    registeredCount: "Registered: {count}",
    docsCount: "{count}",
    fileGroupWord: "Word",
    fileGroupExcel: "Excel",
    fileGroupPpt: "PowerPoint",
    fileGroupPdf: "PDF",
    fileGroupStructured: "JSON/XML",
    fileGroupArchive: "ePub/ZIP",
    fileGroupOther: "Others",
    uploadOverwrite: "(overwrite: {overwritten}, deleted chunks: {deleted})",
    docListFetchFailed: "Failed to load documents",
    docDeleteDone: "🗑️ Deleted: {name}",
    uploadDone: "Done",
    uploadDoneItem: "✅ {name} — {count} chunks {overwrite}",
    uploadFailedItem: "❌ {name}: {message}",
    bulkUploadDone: "Bulk upload completed: {uploaded}/{total} (failed: {failed})",
    bulkUploadFailed: "Bulk upload failed: {message}",
    modelLabelJp: "Japanese",
    modelLabelEn: "English",
    themeSwitch: "Toggle theme",
    languageSwitch: "Language",
  },
};

function t(key, vars = {}) {
  const dict = I18N[currentLang] || I18N.ja;
  const base = dict[key] ?? I18N.ja[key] ?? key;
  return base.replace(/\{(\w+)\}/g, (_, k) => String(vars[k] ?? ""));
}

function escapeHtml(str) {
  return String(str)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function getContentTypeLabel(ct) {
  const map = {
    text: t("typeText"),
    table: t("typeTable"),
    image: t("typeImage"),
    visual_page: t("typeVisualPage"),
  };
  return map[ct] || ct;
}

function getFileGroupLabel(groupKey) {
  const map = {
    word: t("fileGroupWord"),
    excel: t("fileGroupExcel"),
    ppt: t("fileGroupPpt"),
    pdf: t("fileGroupPdf"),
    structured: t("fileGroupStructured"),
    archive: t("fileGroupArchive"),
    other: t("fileGroupOther"),
  };
  return map[groupKey] || groupKey;
}

function applyStaticTranslations() {
  const setText = (id, value) => {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
  };

  setText("docSectionLabel", t("docs"));
  setText("toolsSummary", t("toolsSummary"));
  setText("uploadLabel", t("uploadDrop"));
  setText("bulkUploadBtn", t("bulkUpload"));
  setText("bulkUploadNote", t("bulkUploadNote"));
  setText("addProjectBtn", t("addProject"));
  setText("historySectionLabel", t("history"));
  setText("newChatLabel", t("newChat"));
  setText("retrievalTitle", t("retrievalLog"));
  setText("retrievalMeta", t("retrievalCount", { count: 0 }));
  setText("welcomeTitle", t("welcomeTitle"));
  setText("welcomeDesc", t("welcomeDesc"));
  setText("welcomeSubDesc", t("welcomeSubDesc"));
  setText("reasoningModeLabel", t("reasoningModeLabel"));
  setText("contextTitle", t("contextTitle"));
  setText("projectDialogTitle", t("projectDialogTitle"));
  setText("projectDialogHelp", t("projectDialogHelp"));
  setText("projectDialogCancel", t("cancel"));
  setText("projectDialogCreate", t("create"));

  const docFilterInput = document.getElementById("docFilter");
  if (docFilterInput) docFilterInput.placeholder = t("filterByFilename");

  const input = document.getElementById("inputEl");
  if (input) input.placeholder = t("inputPlaceholder");

  const send = document.getElementById("sendBtn");
  if (send) send.title = t("send");

  if (modelSelect && modelSelect.options.length === 1 && modelSelect.options[0].value === "") {
    modelSelect.options[0].textContent = t("modelLoading");
  }

  const mode = document.getElementById("modeToggleLabel");
  if (mode) mode.title = t("reasoningModeTitle");

  const dialogInput = document.getElementById("projectDialogInput");
  if (dialogInput) dialogInput.placeholder = t("projectDialogPlaceholder");

  const theme = document.getElementById("themeToggleBtn");
  if (theme) theme.title = t("themeSwitch");

  const lang = document.getElementById("languageSelect");
  if (lang) lang.title = t("languageSwitch");

  if (wingFilter) {
    wingFilter.title = t("wingAll");
    if (wingFilter.options.length > 0 && wingFilter.options[0].value === "") {
      wingFilter.options[0].textContent = t("wingAll");
    }
  }
  if (roomFilter) {
    roomFilter.placeholder = t("roomPlaceholder");
  }
  if (contentTypeFilter) {
    contentTypeFilter.title = t("typeAll");
    if (contentTypeFilter.options[0]) contentTypeFilter.options[0].textContent = t("typeAll");
    if (contentTypeFilter.options[1]) contentTypeFilter.options[1].textContent = t("typeText");
    if (contentTypeFilter.options[2]) contentTypeFilter.options[2].textContent = t("typeTable");
    if (contentTypeFilter.options[3]) contentTypeFilter.options[3].textContent = t("typeImage");
    if (contentTypeFilter.options[4]) contentTypeFilter.options[4].textContent = t("typeVisualPage");
  }
}

function applyTheme(nextTheme, persist = true) {
  currentTheme = nextTheme;
  document.documentElement.dataset.theme = currentTheme;
  if (persist) {
    localStorage.setItem("spec-copilot.theme", currentTheme);
  }
  if (themeToggleBtn) {
    themeToggleBtn.textContent = currentTheme === "light" ? "🌙" : "☀️";
  }
}

function initTheme() {
  if (!currentTheme) {
    currentTheme = window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
  }
  applyTheme(currentTheme, false);
  themeToggleBtn?.addEventListener("click", () => {
    applyTheme(currentTheme === "light" ? "dark" : "light");
  });
}

function applyLanguage(lang, persist = true) {
  const oldDefaultTitles = [I18N.ja.newChat, I18N.en.newChat];
  currentLang = lang === "en" ? "en" : "ja";
  document.documentElement.lang = currentLang;
  if (persist) {
    localStorage.setItem("spec-copilot.lang", currentLang);
  }
  if (languageSelect) {
    languageSelect.value = currentLang;
    if (languageSelect.options[0]) languageSelect.options[0].textContent = t("modelLabelJp");
    if (languageSelect.options[1]) languageSelect.options[1].textContent = t("modelLabelEn");
  }
  applyStaticTranslations();
  if (oldDefaultTitles.includes(sessionTitle.textContent || "")) {
    sessionTitle.textContent = t("newChat");
  }
  renderProjectSelect();
  buildDocList(allDocs, docFilter.value);
  renderContextChips();
  updateAdvancedScopeSummary();
}

function initLanguage() {
  applyLanguage(currentLang, false);
  languageSelect?.addEventListener("change", () => {
    applyLanguage(languageSelect.value);
  });
}

// ====================================================
// ユーティリティ
// ====================================================

function showToast(msg, type = "info") {
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = msg;
  toastContainer.appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

function scrollToBottom() {
  messagesEl.scrollTo({ top: messagesEl.scrollHeight, behavior: "smooth" });
}

function setInputEnabled(enabled) {
  inputEl.disabled = !enabled;
  sendBtn.disabled = !enabled || !inputEl.value.trim();
  isStreaming = !enabled;
}

async function copyTextSafely(text) {
  if (!text) return false;
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch {
    // fallback に進む
  }

  try {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.left = "-9999px";
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    const ok = document.execCommand("copy");
    ta.remove();
    return !!ok;
  } catch {
    return false;
  }
}

function addCopyButtonToBubble(bubble, textGetter) {
  if (!bubble || bubble.querySelector(".copy-answer-btn")) return;
  const btn = document.createElement("button");
  btn.className = "copy-answer-btn";
  btn.type = "button";
  btn.title = t("copyAnswer");
  btn.textContent = "⧉";
  btn.addEventListener("click", async () => {
    const ok = await copyTextSafely(textGetter() || "");
    if (ok) {
      btn.textContent = "✓";
      setTimeout(() => { btn.textContent = "⧉"; }, 900);
    } else {
      showToast(t("copyFailed"), "error");
    }
  });
  bubble.appendChild(btn);
}

function addContextFile(filename) {
  if (!filename) return;
  if (selectedContexts.includes(filename)) return;
  selectedContexts.push(filename);
  renderContextChips();
  showToast(t("contextAdded", { name: filename }), "success");
}

function addContextFiles(filenames) {
  const added = [];
  for (const filename of filenames || []) {
    if (!filename || selectedContexts.includes(filename)) continue;
    selectedContexts.push(filename);
    added.push(filename);
  }
  renderContextChips();
  if (added.length) {
    showToast(t("contextAddedCount", { count: added.length }), "success");
  }
}

function removeContextFile(filename) {
  selectedContexts = selectedContexts.filter((f) => f !== filename);
  renderContextChips();
}

function syncContextListWithDocs() {
  const names = new Set(allDocs.map((d) => d.filename));
  selectedContexts = selectedContexts.filter((f) => names.has(f));
}

function renderContextChips() {
  if (!contextChips) return;

  if (!selectedContexts.length) {
    contextChips.innerHTML = `<span class="context-empty">${escapeHtml(t("contextEmpty"))}</span>`;
    contextBar?.classList.add("is-empty");
  } else {
    contextBar?.classList.remove("is-empty");
    contextChips.innerHTML = selectedContexts
      .map((name) => `
        <span class="context-chip" title="${escapeHtml(name)}">
          <span class="context-chip-name">${escapeHtml(name)}</span>
          <button class="context-chip-remove" data-file="${escapeHtml(name)}" type="button" aria-label="${escapeHtml(t("cancel"))}">✕</button>
        </span>
      `)
      .join("");
  }

  contextChips.querySelectorAll(".context-chip-remove").forEach((btn) => {
    btn.addEventListener("click", () => removeContextFile(btn.dataset.file || ""));
  });
}

function applySidebarWidth(width) {
  sidebarWidth = Math.max(MIN_SIDEBAR_WIDTH, Math.min(MAX_SIDEBAR_WIDTH, Math.round(width || DEFAULT_SIDEBAR_WIDTH)));
  document.documentElement.style.setProperty("--sidebar-w", `${sidebarWidth}px`);
  localStorage.setItem("spec-copilot.sidebarWidth", String(sidebarWidth));
}

function setSidebarCollapsed(collapsed) {
  sidebarCollapsed = !!collapsed;
  sidebar?.classList.toggle("collapsed", sidebarCollapsed);
  if (sidebarToggleBtn) {
    sidebarToggleBtn.textContent = sidebarCollapsed ? "▶" : "◀";
    sidebarToggleBtn.setAttribute("aria-label", sidebarCollapsed ? t("sidebarOpen") : t("sidebarClose"));
  }
  localStorage.setItem("spec-copilot.sidebarCollapsed", sidebarCollapsed ? "1" : "0");
}

function initSidebarUi() {
  applySidebarWidth(sidebarWidth);
  setSidebarCollapsed(sidebarCollapsed);

  sidebarToggleBtn?.addEventListener("click", () => {
    setSidebarCollapsed(!sidebarCollapsed);
  });

  resizeHandle?.addEventListener("dblclick", () => {
    applySidebarWidth(DEFAULT_SIDEBAR_WIDTH);
    setSidebarCollapsed(false);
  });

  resizeHandle?.addEventListener("mousedown", (event) => {
    event.preventDefault();
    const onMove = (moveEvent) => {
      document.body.classList.add("is-resizing");
      const nextWidth = moveEvent.clientX;
      if (nextWidth <= COLLAPSE_THRESHOLD) {
        setSidebarCollapsed(true);
        return;
      }
      if (sidebarCollapsed) {
        setSidebarCollapsed(false);
      }
      applySidebarWidth(nextWidth);
    };

    const onUp = () => {
      document.body.classList.remove("is-resizing");
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };

    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  });
}

// ====================================================
// セクション開閉
// ====================================================

function initSectionToggle(toggleBtn, bodyEl) {
  toggleBtn.addEventListener("click", () => {
    if (sidebarCollapsed) {
      setSidebarCollapsed(false);
      return;
    }
    const expanded = toggleBtn.getAttribute("aria-expanded") === "true";
    toggleBtn.setAttribute("aria-expanded", String(!expanded));
  });
}

initSectionToggle(docSectionToggle, docSectionBody);
initSectionToggle(historySectionToggle, historySectionBody);
if (retrievalToggle) {
  retrievalToggle.addEventListener("click", () => {
    const expanded = retrievalToggle.getAttribute("aria-expanded") === "true";
    retrievalToggle.setAttribute("aria-expanded", String(!expanded));
  });
}

function renderRetrievalLogs(items) {
  if (!retrievalPanel || !retrievalMeta || !retrievalBody) return;

  retrievalPanel.hidden = false;
  retrievalToggle?.setAttribute("aria-expanded", "false");
  retrievalMeta.textContent = t("retrievalCount", { count: items.length });

  if (!items.length) {
    retrievalBody.innerHTML = `<div class="retrieval-item-query" style="color:var(--text-muted)">${escapeHtml(t("retrievalNoLogs"))}</div>`;
    return;
  }

  retrievalBody.innerHTML = items.map((item) => {
    const d = item.diagnostics || {};
    const tags = [
      t("retrievalLimit", { count: item.requested_k }),
      t("retrievalHit", { count: item.result_count }),
      t("retrievalLatency", { ms: item.latency_ms }),
      t("retrievalVectorHit", { count: d.vector_hit_count ?? 0 }),
      t("retrievalKeywordHit", { count: d.keyword_match_count ?? 0 }),
    ];

    if (item.wing) tags.push(t("retrievalWing", { value: item.wing }));
    if (item.room) tags.push(t("retrievalRoom", { value: item.room }));
    if (item.content_type) {
      const label = getContentTypeLabel(item.content_type);
      tags.push(t("retrievalType", { value: label }));
    }
    if ((item.source_files || []).length) {
      tags.push(t("retrievalFiles", { value: item.source_files.join(currentLang === "ja" ? "、" : ", ") }));
    }

    const tagHtml = tags.map((t) => `<span class="retrieval-tag">${escapeHtml(t)}</span>`).join("");

    return `
      <article class="retrieval-item">
        <div class="retrieval-item-head">${item.call_index} / ${new Date(item.created_at).toLocaleTimeString(currentLang === "ja" ? "ja-JP" : "en-US")}</div>
        <div class="retrieval-item-query">${escapeHtml(item.query)}</div>
        <div class="retrieval-tags">${tagHtml}</div>
      </article>
    `;
  }).join("");
}

async function loadRetrievalLogs(sessionId) {
  if (!retrievalPanel || !sessionId) {
    if (retrievalPanel) retrievalPanel.hidden = true;
    return;
  }

  try {
    const res = await fetch(`/api/history/${sessionId}/retrievals`);
    if (!res.ok) throw new Error(t("retrievalFetchError"));
    const items = await res.json();
    renderRetrievalLogs(items);
  } catch (e) {
    retrievalPanel.hidden = false;
    retrievalMeta.textContent = t("retrievalFetchFailed");
    retrievalBody.innerHTML = `<div class="retrieval-item-query" style="color:var(--danger)">${escapeHtml(e.message)}</div>`;
  }
}

// ====================================================
// モデル一覧の動的ロード (T2)
// ====================================================

async function loadModels() {
  try {
    const res = await fetch("/api/models");
    if (!res.ok) throw new Error(res.statusText);
    const models = await res.json();
    modelSelect.innerHTML = "";
    for (const m of models) {
      const opt = document.createElement("option");
      opt.value = m.id;
      opt.textContent = m.id;
      // claude-sonnet-4.5 をデフォルト選択
      if (m.id === "claude-sonnet-4.5") opt.selected = true;
      modelSelect.appendChild(opt);
    }
    if (models.length === 0) throw new Error(t("modelFetchZero"));
  } catch (e) {
    console.warn(t("modelFetchFallback"), e);
    modelSelect.innerHTML = `
      <option value="claude-sonnet-4.5" selected>claude-sonnet-4.5</option>
      <option value="claude-opus-4.5">claude-opus-4.5</option>
      <option value="gpt-4.1">gpt-4.1</option>
    `;
  }
}

// ====================================================
// メッセージ描画
// ====================================================

function appendMessage(role, contentOrEl) {
  const msg = document.createElement("div");
  msg.className = `msg ${role}`;

  const avatar = document.createElement("div");
  avatar.className = "msg-avatar";
  avatar.textContent = role === "user" ? "👤" : "🤖";

  const bubble = document.createElement("div");
  bubble.className = "msg-bubble";

  if (typeof contentOrEl === "string") {
    if (role === "assistant") {
      bubble.innerHTML = marked.parse(contentOrEl);
      bubble.dataset.raw = contentOrEl;
      addCopyButtonToBubble(bubble, () => bubble.dataset.raw || "");
    } else {
      bubble.textContent = contentOrEl;
    }
  } else {
    bubble.appendChild(contentOrEl);
  }

  msg.appendChild(avatar);
  msg.appendChild(bubble);
  messagesEl.appendChild(msg);
  scrollToBottom();
  return bubble;
}

function showTyping() {
  const dots = document.createElement("div");
  dots.className = "typing-dots";
  dots.id = "typingDots";
  ["", "", ""].forEach(() => {
    const s = document.createElement("span");
    dots.appendChild(s);
  });
  return appendMessage("assistant", dots);
}

function removeTyping() {
  const el = document.getElementById("typingDots");
  if (el) el.closest(".msg")?.remove();
}

// ====================================================
// チャット送信
// ====================================================

async function sendMessage() {
  const text = inputEl.value.trim();
  if (!text || isStreaming) return;

  inputEl.value = "";
  inputEl.style.height = "auto";
  setInputEnabled(false);

  welcomeEl.style.display = "none";
  messagesEl.style.display = "flex";

  appendMessage("user", text);
  const botBubble = appendMessage("assistant", "");
  showTyping();

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: text,
        session_id: currentSessionId,
        model: modelSelect.value,
        reasoning_mode: reasoningModeToggle.checked,
        wing: wingFilter?.value || null,
        room: roomFilter?.value?.trim() || null,
        content_type: contentTypeFilter?.value || null,
        context_files: selectedContexts,
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || res.statusText);
    }

    removeTyping();
    let accumulated = "";
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buf = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });

      const lines = buf.split("\n");
      buf = lines.pop();

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        let ev;
        try { ev = JSON.parse(line.slice(6)); } catch { continue; }

        if (ev.type === "session_id") {
          currentSessionId = ev.session_id;
        } else if (ev.type === "delta") {
          accumulated += ev.content;
          botBubble.innerHTML = marked.parse(accumulated);
          botBubble.dataset.raw = accumulated;
          addCopyButtonToBubble(botBubble, () => botBubble.dataset.raw || "");
          scrollToBottom();
        } else if (ev.type === "error") {
          showToast(t("chatError", { message: ev.message }), "error");
        } else if (ev.type === "done") {
          if (!currentSessionId) currentSessionId = ev.session_id;
          await loadHistory();
          await loadRetrievalLogs(currentSessionId);
        }
      }
    }

    if (!accumulated) {
      botBubble.textContent = t("chatNoResponse");
    } else {
      botBubble.dataset.raw = accumulated;
      addCopyButtonToBubble(botBubble, () => botBubble.dataset.raw || "");
    }

  } catch (e) {
    removeTyping();
    botBubble.textContent = `⚠️ ${t("chatError", { message: e.message })}`;
    showToast(e.message, "error");
  } finally {
    setInputEnabled(true);
    inputEl.focus();
  }
}

// ====================================================
// 会話履歴
// ====================================================

async function loadHistory() {
  try {
    const res = await fetch("/api/history");
    const sessions = await res.json();
    renderHistoryList(sessions);
  } catch (e) {
    console.error(t("historyFetchFailed"), e);
  }
}

function renderProjectSelect() {
  if (!uploadProjectSelect) return;
  uploadProjectSelect.title = t("uploadTargetUnclassified");
  const selected = uploadProjectSelect.value;
  uploadProjectSelect.innerHTML = `<option value="">${escapeHtml(t("uploadTargetUnclassified"))}</option>`;
  for (const p of allProjects) {
    const opt = document.createElement("option");
    opt.value = p.name;
    opt.textContent = t("uploadTargetProject", { name: p.name });
    uploadProjectSelect.appendChild(opt);
  }
  uploadProjectSelect.value = allProjects.some((p) => p.name === selected) ? selected : "";
}

function updateAdvancedScopeSummary() {
  if (!advancedScopeSummary) return;
  const labels = [];
  const wing = wingFilter?.value?.trim() || "";
  const room = roomFilter?.value?.trim() || "";
  const ct = contentTypeFilter?.value || "";

  if (wing) labels.push(t("advancedFilterWing", { value: wing }));
  if (room) labels.push(t("advancedFilterRoom", { value: room }));
  if (ct) {
    labels.push(t("advancedFilterType", { value: getContentTypeLabel(ct) }));
  }
  advancedScopeSummary.textContent = labels.length
    ? `${t("advancedFilterPrefix")}: ${labels.join(" / ")}`
    : t("advancedFilterAll");
}

async function loadProjects() {
  try {
    const res = await fetch("/api/documents/projects");
    if (!res.ok) throw new Error(t("projectFetchFailed"));
    allProjects = await res.json();
    renderProjectSelect();
  } catch (e) {
    console.error(e);
  }
}

async function createProject() {
  const name = (projectDialogInput?.value || "").trim();
  if (!name.trim()) return;
  try {
    const res = await fetch("/api/documents/projects", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || t("createFailed", { message: "" }));
    showToast(t("projectCreated", { name: data.name }), "success");
    closeProjectDialog();
    await Promise.all([loadProjects(), loadDocuments()]);
  } catch (e) {
    showToast(t("createFailed", { message: e.message }), "error");
  }
}

function openProjectDialog() {
  if (!projectDialogBackdrop || !projectDialogInput) return;
  projectDialogBackdrop.hidden = false;
  projectDialogInput.value = "";
  setTimeout(() => projectDialogInput.focus(), 0);
}

function closeProjectDialog() {
  if (!projectDialogBackdrop || !projectDialogInput) return;
  projectDialogBackdrop.hidden = true;
  projectDialogInput.value = "";
}

async function moveDocumentToProject(docId, project) {
  try {
    const res = await fetch(`/api/documents/${docId}/project`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || res.statusText);
    showToast(t("movedToProject", { project: project || t("unclassified") }), "success");
    await loadDocuments();
  } catch (e) {
    showToast(t("moveFailed", { message: e.message }), "error");
  }
}

function renderHistoryList(sessions) {
  historyList.innerHTML = "";
  historyBadge.textContent = sessions.length;
  for (const s of sessions) {
    const item = document.createElement("div");
    item.className = "history-item" + (s.id === currentSessionId ? " active" : "");
    item.dataset.id = s.id;

    const titleEl = document.createElement("span");
    titleEl.className = "h-title";
    titleEl.textContent = s.title;

    const delBtn = document.createElement("button");
    delBtn.className = "h-del";
    delBtn.title = t("docDeleteTitle");
    delBtn.innerHTML = "✕";
    delBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      deleteSession(s.id);
    });

    item.appendChild(titleEl);
    item.appendChild(delBtn);
    item.addEventListener("click", () => loadSession(s.id, s.title));
    historyList.appendChild(item);
  }
}

async function loadSession(sessionId, title) {
  currentSessionId = sessionId;
  sessionTitle.textContent = title;

  try {
    const res = await fetch(`/api/history/${sessionId}`);
    if (!res.ok) throw new Error(t("retrievalFetchFailed"));
    const msgs = await res.json();

    welcomeEl.style.display = "none";
    messagesEl.style.display = "flex";
    messagesEl.innerHTML = "";

    for (const m of msgs) {
      appendMessage(m.role, m.content);
    }
    await loadRetrievalLogs(sessionId);
    renderHistoryList(await (await fetch("/api/history")).json());
  } catch (e) {
    showToast(t("sessionLoadFailed", { message: e.message }), "error");
  }
}

async function deleteSession(sessionId) {
  try {
    await fetch(`/api/history/${sessionId}`, { method: "DELETE" });
    if (currentSessionId === sessionId) startNewChat();
    await loadHistory();
    showToast(t("deleteSessionDone"), "success");
  } catch (e) {
    showToast(t("deleteFailed", { message: e.message }), "error");
  }
}

async function deleteProject(projectId, projectName) {
  try {
    const res = await fetch(`/api/documents/projects/${projectId}`, { method: "DELETE" });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || res.statusText);
    showToast(t("projectDeleted", { name: projectName }), "success");
    await Promise.all([loadProjects(), loadDocuments()]);
  } catch (e) {
    showToast(t("projectDeleteFailed", { message: e.message }), "error");
  }
}

function startNewChat() {
  currentSessionId = null;
  sessionTitle.textContent = t("newChat");
  messagesEl.innerHTML = "";
  messagesEl.style.display = "none";
  welcomeEl.style.display = "flex";
  inputEl.value = "";
  if (retrievalPanel) retrievalPanel.hidden = true;
  document.querySelectorAll(".history-item").forEach(el => el.classList.remove("active"));
}

// ====================================================
// ドキュメント管理 (T4)
// ====================================================

const FILE_GROUPS = [
  { key: "word",  label: "📝 Word",       icon: "📝", exts: [".docx", ".doc"] },
  { key: "excel", label: "📊 Excel",      icon: "📊", exts: [".xlsx", ".xls"] },
  { key: "ppt",   label: "📐 PowerPoint", icon: "📐", exts: [".pptx", ".ppt"] },
  { key: "pdf",   label: "📄 PDF",        icon: "📄", exts: [".pdf"] },
  { key: "structured", label: "🧩 JSON/XML", icon: "🧩", exts: [".json", ".xml"] },
  { key: "archive", label: "🗜 ePub/ZIP", icon: "🗜", exts: [".epub", ".zip"] },
  { key: "other", label: "📎 その他",     icon: "📎", exts: [] },
];

function getGroupKey(filename) {
  const ext = filename.slice(filename.lastIndexOf(".")).toLowerCase();
  for (const g of FILE_GROUPS) {
    if (g.exts.includes(ext)) return g.key;
  }
  return "other";
}

function buildDocList(docs, filterText = "") {
  docList.innerHTML = "";
  docBadge.textContent = docs.length;

  if (docs.length === 0 && allProjects.length === 0) {
    docList.innerHTML = `<div style="font-size:11px;color:var(--text-muted);padding:6px 8px;">${escapeHtml(t("noRegistration"))}</div>`;
    return;
  }

  const lower = filterText.toLowerCase();
  const docProjectNames = Array.from(new Set(docs.map((d) => (d.project || "").trim()).filter(Boolean)));
  const managedProjectNames = allProjects.map((p) => p.name);
  const projectMap = new Map(allProjects.map((p) => [p.name, p]));
  const projectNames = ["", ...Array.from(new Set([...managedProjectNames, ...docProjectNames]))];

  for (const projectName of projectNames) {
    const projectDocs = docs.filter((d) => (d.project || "") === projectName);
    const projectInfo = projectMap.get(projectName);

    const projectEl = document.createElement("div");
    projectEl.className = "doc-project";
    projectEl.dataset.project = projectName;

    const projectHeader = document.createElement("div");
    projectHeader.className = "doc-project-header";
    projectHeader.innerHTML = `
      <span>📂</span>
      <span class="doc-project-name">${escapeHtml(projectName || t("unclassified"))}</span>
      <span class="doc-group-count">${projectDocs.length}</span>
      <span class="doc-project-actions"></span>
    `;
    const projectActions = projectHeader.querySelector(".doc-project-actions");
    const addProjectContextBtn = document.createElement("button");
    addProjectContextBtn.className = "doc-action-btn";
    addProjectContextBtn.type = "button";
    addProjectContextBtn.title = t("addProjectContext");
    addProjectContextBtn.textContent = "⊕";
    addProjectContextBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      addContextFiles(projectDocs.map((d) => d.filename));
    });
    projectActions?.appendChild(addProjectContextBtn);
    if (projectInfo && projectDocs.length === 0) {
      const deleteProjectBtn = document.createElement("button");
      deleteProjectBtn.className = "doc-action-btn doc-del";
      deleteProjectBtn.type = "button";
      deleteProjectBtn.title = t("deleteEmptyProject");
      deleteProjectBtn.textContent = "✕";
      deleteProjectBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        deleteProject(projectInfo.id, projectInfo.name);
      });
      projectActions?.appendChild(deleteProjectBtn);
    }
    projectHeader.addEventListener("click", () => {
      projectEl.classList.toggle("collapsed");
    });
    projectHeader.addEventListener("contextmenu", (e) => {
      e.preventDefault();
      addContextFiles(projectDocs.map((d) => d.filename));
    });
    projectHeader.addEventListener("dragover", (e) => {
      if (!draggingDocId) return;
      e.preventDefault();
      projectEl.classList.add("doc-project-drop");
    });
    projectHeader.addEventListener("dragleave", () => {
      projectEl.classList.remove("doc-project-drop");
    });
    projectHeader.addEventListener("drop", async (e) => {
      if (!draggingDocId) return;
      e.preventDefault();
      projectEl.classList.remove("doc-project-drop");
      const docId = Number(draggingDocId);
      draggingDocId = null;
      await moveDocumentToProject(docId, projectName);
    });

    const projectBody = document.createElement("div");
    projectBody.className = "doc-project-body";

    if (!projectDocs.length) {
      projectBody.innerHTML = `<div style="font-size:11px;color:var(--text-muted);padding:8px 10px;">${escapeHtml(t("noDocsInProject"))}</div>`;
      projectEl.appendChild(projectHeader);
      projectEl.appendChild(projectBody);
      docList.appendChild(projectEl);
      continue;
    }

    const grouped = {};
    FILE_GROUPS.forEach((g) => { grouped[g.key] = []; });
    for (const d of projectDocs) {
      const key = getGroupKey(d.filename);
      grouped[key].push(d);
    }

    for (const g of FILE_GROUPS) {
      const items = grouped[g.key];
      if (items.length === 0) continue;

      const visible = lower ? items.filter((d) => d.filename.toLowerCase().includes(lower)) : items;
      if (!visible.length && lower) continue;

      const groupEl = document.createElement("div");
      groupEl.className = "doc-group";
      const header = document.createElement("div");
      header.className = "doc-group-header";
      header.innerHTML = `
        <span>${g.icon}</span>
        <span class="doc-group-label">${escapeHtml(getFileGroupLabel(g.key))}</span>
        <span class="doc-group-count">${visible.length}/${items.length}</span>
        <span class="doc-group-actions"></span>
        <svg class="doc-group-chevron" width="10" height="10" viewBox="0 0 10 10" fill="none">
          <path d="M2 3.5l3 3 3-3" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      `;
      const groupActions = header.querySelector(".doc-group-actions");
      const addGroupContextBtn = document.createElement("button");
      addGroupContextBtn.className = "doc-action-btn";
      addGroupContextBtn.type = "button";
      addGroupContextBtn.title = t("addGroupContext");
      addGroupContextBtn.textContent = "⊕";
      addGroupContextBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        addContextFiles(items.map((d) => d.filename));
      });
      groupActions?.appendChild(addGroupContextBtn);
      header.addEventListener("click", () => {
        groupEl.classList.toggle("collapsed");
      });
      header.addEventListener("contextmenu", (e) => {
        e.preventDefault();
        addContextFiles(items.map((d) => d.filename));
      });

      const itemsEl = document.createElement("div");
      itemsEl.className = "doc-group-items";

      for (const d of items) {
        const item = document.createElement("div");
        item.className = "doc-item" + (lower && !d.filename.toLowerCase().includes(lower) ? " hidden" : "");
        item.draggable = true;
        item.dataset.docId = String(d.id);
        item.title = `${d.filename}\n${t("registeredCount", { count: d.drawer_count })}\n${d.created_at ? new Date(d.created_at).toLocaleString(currentLang === "ja" ? "ja-JP" : "en-US") : ""}`;

        item.addEventListener("dragstart", () => {
          draggingDocId = String(d.id);
          item.classList.add("dragging");
        });
        item.addEventListener("dragend", () => {
          draggingDocId = null;
          item.classList.remove("dragging");
          document.querySelectorAll(".doc-project-drop").forEach((el) => el.classList.remove("doc-project-drop"));
        });

        const delBtn = document.createElement("button");
        delBtn.className = "doc-action-btn doc-del";
        delBtn.title = t("docDeleteTitle");
        delBtn.textContent = "✕";
        delBtn.addEventListener("click", (e) => {
          e.stopPropagation();
          deleteDocument(d.id, d.filename);
        });

        const addContextBtn = document.createElement("button");
        addContextBtn.className = "doc-action-btn";
        addContextBtn.type = "button";
        addContextBtn.title = t("addDocContext");
        addContextBtn.textContent = "⊕";
        addContextBtn.addEventListener("click", (e) => {
          e.stopPropagation();
          addContextFile(d.filename);
        });

        item.addEventListener("contextmenu", (e) => {
          e.preventDefault();
          addContextFile(d.filename);
        });

        item.innerHTML = `
          <span class="doc-icon">${g.icon}</span>
          <span class="doc-name">${d.filename}</span>
          <span class="doc-drawers">${t("docsCount", { count: d.drawer_count })}</span>
          <span class="doc-item-actions"></span>
        `;
        const itemActions = item.querySelector(".doc-item-actions");
        itemActions?.appendChild(addContextBtn);
        itemActions?.appendChild(delBtn);
        itemsEl.appendChild(item);
      }

      groupEl.appendChild(header);
      groupEl.appendChild(itemsEl);
      projectBody.appendChild(groupEl);
    }

    projectEl.appendChild(projectHeader);
    projectEl.appendChild(projectBody);
    docList.appendChild(projectEl);
  }
}

function refreshScopeOptions() {
  if (!wingFilter) return;

  const selected = wingFilter.value;
  const wings = Array.from(new Set(allDocs.map(d => d.wing).filter(Boolean))).sort();
  wingFilter.innerHTML = `<option value="">${escapeHtml(t("wingAll"))}</option>`;
  for (const wing of wings) {
    const opt = document.createElement("option");
    opt.value = wing;
    opt.textContent = `${t("advancedFilterWing", { value: wing })}`;
    wingFilter.appendChild(opt);
  }
  wingFilter.value = wings.includes(selected) ? selected : "";
  updateAdvancedScopeSummary();
}

async function loadDocuments() {
  try {
    const res = await fetch("/api/documents");
    allDocs = await res.json();
    syncContextListWithDocs();
    buildDocList(allDocs, docFilter.value);
    refreshScopeOptions();
    renderContextChips();
  } catch (e) {
    console.error(t("docListFetchFailed"), e);
  }
}

async function deleteDocument(docId, filename) {
  try {
    const res = await fetch(`/api/documents/${docId}`, { method: "DELETE" });
    if (!res.ok) throw new Error((await res.json()).detail || res.statusText);
    showToast(t("docDeleteDone", { name: filename }), "success");
    await loadDocuments();
  } catch (e) {
    showToast(t("deleteFailed", { message: e.message }), "error");
  }
}

// ====================================================
// ドキュメントアップロード
// ====================================================

async function uploadFiles(files) {
  const fileArray = Array.from(files || []);
  if (fileArray.length === 0) return;

  uploadProgress.style.display = "block";
  uploadBar.value = 0;
  uploadStatus.textContent = "";

  for (let i = 0; i < fileArray.length; i++) {
    const file = fileArray[i];
    const project = uploadProjectSelect?.value || "";
    uploadStatus.textContent = `${i + 1}/${fileArray.length}: ${file.name}`;
    const formData = new FormData();
    formData.append("file", file);
    formData.append("project", project);

    try {
      const res = await fetch("/api/documents", { method: "POST", body: formData });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || res.statusText);
      const overwrite = data.overwritten_count > 0
        ? t("uploadOverwrite", { overwritten: data.overwritten_count, deleted: data.deleted_chunks })
        : "";
      showToast(t("uploadDoneItem", { name: file.name, count: data.drawer_count, overwrite }), "success");
    } catch (e) {
      showToast(t("uploadFailedItem", { name: file.name, message: e.message }), "error");
    }

    uploadBar.value = Math.round(((i + 1) / fileArray.length) * 100);
  }

  uploadStatus.textContent = t("uploadDone");
  setTimeout(() => { uploadProgress.style.display = "none"; }, 1500);
  await loadDocuments();
}

async function uploadBulkFromFolder() {
  if (!bulkUploadBtn) return;
  bulkUploadBtn.disabled = true;

  try {
    const res = await fetch("/api/documents/bulk-upload", { method: "POST" });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || res.statusText);

    showToast(
      t("bulkUploadDone", { uploaded: data.uploaded, total: data.total, failed: data.failed }),
      data.failed > 0 ? "warn" : "success",
    );

    for (const r of data.results || []) {
      if (r.status === "failed") {
        showToast(`❌ ${r.filename}: ${r.reason}`, "error");
      }
    }
  } catch (e) {
    showToast(t("bulkUploadFailed", { message: e.message }), "error");
  } finally {
    bulkUploadBtn.disabled = false;
    await loadDocuments();
  }
}

// ====================================================
// 検索フィルター
// ====================================================

docFilter.addEventListener("input", () => {
  buildDocList(allDocs, docFilter.value);
});

wingFilter?.addEventListener("change", updateAdvancedScopeSummary);
roomFilter?.addEventListener("input", updateAdvancedScopeSummary);
contentTypeFilter?.addEventListener("change", updateAdvancedScopeSummary);

// ====================================================
// イベントリスナー
// ====================================================

inputEl.addEventListener("input", () => {
  inputEl.style.height = "auto";
  inputEl.style.height = Math.min(inputEl.scrollHeight, 180) + "px";
  sendBtn.disabled = isStreaming || !inputEl.value.trim();
});

inputEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});

sendBtn.addEventListener("click", sendMessage);
newChatBtn.addEventListener("click", startNewChat);
if (bulkUploadBtn) {
  bulkUploadBtn.addEventListener("click", uploadBulkFromFolder);
}

fileInput.addEventListener("change", async (e) => {
  await uploadFiles(e.target.files);
  fileInput.value = "";
});

uploadArea.addEventListener("dragover", (e) => {
  e.preventDefault();
  uploadArea.classList.add("drag-over");
});
uploadArea.addEventListener("dragleave", () => uploadArea.classList.remove("drag-over"));
uploadArea.addEventListener("drop", (e) => {
  e.preventDefault();
  uploadArea.classList.remove("drag-over");
  uploadFiles(e.dataTransfer.files);
});

if (addProjectBtn) {
  addProjectBtn.addEventListener("click", openProjectDialog);
}

if (projectDialogCancel) {
  projectDialogCancel.addEventListener("click", closeProjectDialog);
}

if (projectDialogCreate) {
  projectDialogCreate.addEventListener("click", createProject);
}

if (projectDialogInput) {
  projectDialogInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      createProject();
    }
    if (e.key === "Escape") {
      e.preventDefault();
      closeProjectDialog();
    }
  });
}

if (projectDialogBackdrop) {
  projectDialogBackdrop.addEventListener("click", (e) => {
    if (e.target === projectDialogBackdrop) closeProjectDialog();
  });
}

// ====================================================
// 初期化
// ====================================================

(async () => {
  initTheme();
  initLanguage();
  initSidebarUi();
  await Promise.all([loadModels(), loadHistory(), loadProjects(), loadDocuments()]);
  renderContextChips();
  updateAdvancedScopeSummary();
})();
