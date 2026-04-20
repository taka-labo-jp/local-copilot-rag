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
const uploadModalOverlay = document.getElementById("uploadModalOverlay");
const uploadModalTitle = document.getElementById("uploadModalTitle");
const uploadModalBar = document.getElementById("uploadModalBar");
const uploadModalPercent = document.getElementById("uploadModalPercent");
const uploadModalStatus = document.getElementById("uploadModalStatus");
const uploadModalCancelBtn = document.getElementById("uploadModalCancelBtn");
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
const premiumToggle = document.getElementById("premiumToggle");
const wingFilter = document.getElementById("wingFilter");
const roomFilter = document.getElementById("roomFilter");
const contentTypeFilter = document.getElementById("contentTypeFilter");
const advancedScopeSummary = document.getElementById("advancedScopeSummary");
const contextChips = document.getElementById("contextChips");
const retrievalPanel = document.getElementById("retrievalPanel");
const retrievalToggle = document.getElementById("retrievalToggle");
const retrievalMeta = document.getElementById("retrievalMeta");
const retrievalBody = document.getElementById("retrievalBody");
const todoWorkflow = document.getElementById("todoWorkflow");
const todoSummaryBadges = document.getElementById("todoSummaryBadges");
const todoSummaryEmptyEl = document.getElementById("todoSummaryEmpty");
const todoOpenBtn = document.getElementById("todoOpenBtn");
const todoDrawerBackdrop = document.getElementById("todoDrawerBackdrop");
const todoDrawerCloseBtn = document.getElementById("todoDrawerCloseBtn");
const todoList = document.getElementById("todoList");
const todoDetail = document.getElementById("todoDetail");
const todoDetailEmpty = document.getElementById("todoDetailEmpty");
const todoPreviewOverlay = document.getElementById("todoPreviewOverlay");
const todoPreviewTitle = document.getElementById("todoPreviewTitle");
const todoPreviewBody = document.getElementById("todoPreviewBody");
const todoPreviewCancelBtn = document.getElementById("todoPreviewCancelBtn");
const todoPreviewConfirmBtn = document.getElementById("todoPreviewConfirmBtn");
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
let isUploading = false;
let allDocs = [];
let allProjects = [];
let selectedContexts = [];
let draggingDocId = null;
let modelLoadRequestSeq = 0;
let sidebarWidth = Number(localStorage.getItem("spec-copilot.sidebarWidth") || 300);
let sidebarCollapsed = localStorage.getItem("spec-copilot.sidebarCollapsed") === "1";
let currentLang = localStorage.getItem("spec-copilot.lang") || "ja";
let currentTheme = localStorage.getItem("spec-copilot.theme") || "";
let currentTodos = [];
let currentTodoId = null;
let currentTodoPreviewMessageId = null;
let currentTodoDetailData = null;
let currentHistorySessions = [];
let todoOverlayConfirmAction = null;

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
    premiumLabel: "プレミアム",
    premiumTitle: "プレミアムリクエスト使用: オフにすると消費量0のモデルのみ表示します",
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
    chatBackendUnavailable: "バックエンドに接続できません。サーバーを起動してください（例: uvicorn app.main:app --host 0.0.0.0 --port 8080）。",
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
    bulkUploadProgress: "{index}/{total}: {filename}",
    bulkUploadStarted: "一括アップロード開始...",
    chatStatusThinking: "✍️ 回答生成中...",
    chatStatusSearching: "🔍 コンテキスト検索中: {query}",
    todoOpenList: "一覧を開く",
    todoStatusDraft: "下書き",
    todoStatusInProgress: "対応中",
    todoStatusReviewRequired: "レビュー待ち",
    todoStatusDone: "完了",
    todoSummaryEmpty: "この会話のTODOはまだありません",
    todoSummaryCount: "この会話のTODO {count}件",
    todoSummaryLoadFailed: "TODOの取得に失敗しました",
    todoPreviewGeneratingTitle: "TODO草案を生成中...",
    todoPreviewGeneratingNote: "回答内容から TODO テンプレートを作成しています。",
    todoPreviewConfirmTitle: "このTODOで作成します。変更があれば編集してください。",
    todoPreviewConfirmButton: "このTODOで作成",
    todoTitleRequired: "タイトルは必須です",
    todoCreated: "TODOを作成しました",
    todoActionFailed: "{action}失敗: {message}",
    todoActionCreate: "TODO作成",
    todoActionPreview: "TODO草案生成",
    todoActionSave: "TODO保存",
    todoActionApprove: "承認",
    todoActionDraft: "AIドラフト生成",
    todoFieldTitle: "タイトル",
    todoFieldDescription: "説明",
    todoFieldAcceptance: "受け入れ条件",
    todoFieldStatus: "ステータス",
    todoSave: "保存",
    todoSaveDone: "保存しました",
    todoApproveDoneButton: "承認して完了",
    todoApproveDone: "承認して完了しました",
    todoApproveHintReady: "レビュー待ちなので承認して完了できます。",
    todoApproveHintNeedReview: "承認して完了は「レビュー待ち」に保存したあとに有効になります。",
    todoDraftButton: "AIドラフト生成",
    todoDraftGenerated: "AIドラフトを生成しました",
    todoDraftModalProgressTitle: "AIドラフトを生成中...",
    todoDraftModalResultTitle: "AIドラフトの生成が完了しました",
    todoDraftModalErrorTitle: "AIドラフト生成に失敗しました",
    todoDraftModalContextTitle: "この情報をもとにドラフトを作成しています",
    todoDraftModalResultBody: "TODOをもとにしたドラフトをチャットに追加しました。内容を確認してください。",
    todoOverlayClose: "閉じる",
    todoOverlayGenerating: "生成中...",
    todoRelatedMessageCount: "関連メッセージ: {count}",
    todoDraftMessageIds: "ドラフト: {ids}",
    todoNone: "なし",
    todoSummaryBreakdown: "下書き {draft} / 対応中 {inProgress} / レビュー待ち {reviewRequired} / 完了 {done}",
    historyTodoBadge: "TODO {count}",
    deleteSessionTodoTitle: "TODOがありますが削除しますか？",
    deleteSessionTodoMessage: "この会話には {count} 件のTODOがあります。削除すると関連するTODOとログも消えます。",
    deleteSessionTodoBreakdown: "ステータス別件数: {summary}",
    deleteSessionTodoItems: "対象TODO",
    deleteSessionConfirm: "削除する",
    approveReviewerTitle: "承認者名を入力してください",
    approveReviewerHelp: "レビュー待ちのTODOを完了にする承認者名を記録します。",
    approveReviewerPlaceholder: "例: reviewer",
    approveReviewerConfirm: "承認して完了",
    approveReviewerRequired: "承認者名は必須です",
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
    premiumLabel: "Premium",
    premiumTitle: "Use premium requests: when off, only models with zero cost are shown.",
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
    chatBackendUnavailable: "Cannot connect to backend. Start the server (e.g. uvicorn app.main:app --host 0.0.0.0 --port 8080).",
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
    bulkUploadProgress: "{index}/{total}: {filename}",
    bulkUploadStarted: "Starting bulk upload...",
    chatStatusThinking: "✍️ Generating answer...",
    chatStatusSearching: "🔍 Searching context: {query}",
    todoOpenList: "Open list",
    todoStatusDraft: "Draft",
    todoStatusInProgress: "In Progress",
    todoStatusReviewRequired: "Review Required",
    todoStatusDone: "Done",
    todoSummaryEmpty: "No TODOs in this chat yet",
    todoSummaryCount: "TODOs in this chat: {count}",
    todoSummaryLoadFailed: "Failed to load TODOs",
    todoPreviewGeneratingTitle: "Generating TODO draft...",
    todoPreviewGeneratingNote: "Building a TODO template from this answer.",
    todoPreviewConfirmTitle: "Create this TODO? Edit if needed.",
    todoPreviewConfirmButton: "Create this TODO",
    todoTitleRequired: "Title is required",
    todoCreated: "TODO created",
    todoActionFailed: "{action} failed: {message}",
    todoActionCreate: "TODO creation",
    todoActionPreview: "TODO draft generation",
    todoActionSave: "TODO save",
    todoActionApprove: "Approval",
    todoActionDraft: "AI draft generation",
    todoFieldTitle: "Title",
    todoFieldDescription: "Description",
    todoFieldAcceptance: "Acceptance Criteria",
    todoFieldStatus: "Status",
    todoSave: "Save",
    todoSaveDone: "Saved",
    todoApproveDoneButton: "Approve and Complete",
    todoApproveDone: "Approved and completed",
    todoApproveHintReady: "This TODO is review-required and can be approved now.",
    todoApproveHintNeedReview: "Approval is enabled after saving status as Review Required.",
    todoDraftButton: "Generate AI Draft",
    todoDraftGenerated: "AI draft generated",
    todoDraftModalProgressTitle: "Generating AI draft...",
    todoDraftModalResultTitle: "AI draft generated",
    todoDraftModalErrorTitle: "Failed to generate AI draft",
    todoDraftModalContextTitle: "Generating draft from this TODO context",
    todoDraftModalResultBody: "A draft based on this TODO has been added to chat.",
    todoOverlayClose: "Close",
    todoOverlayGenerating: "Generating...",
    todoRelatedMessageCount: "Related messages: {count}",
    todoDraftMessageIds: "Drafts: {ids}",
    todoNone: "None",
    todoSummaryBreakdown: "Draft {draft} / In Progress {inProgress} / Review Required {reviewRequired} / Done {done}",
    historyTodoBadge: "TODO {count}",
    deleteSessionTodoTitle: "Delete a session with TODOs?",
    deleteSessionTodoMessage: "This chat has {count} TODOs. Deleting it will also remove related TODOs and logs.",
    deleteSessionTodoBreakdown: "Status breakdown: {summary}",
    deleteSessionTodoItems: "Affected TODOs",
    deleteSessionConfirm: "Delete",
    approveReviewerTitle: "Enter approver name",
    approveReviewerHelp: "The approver name will be recorded when completing this review-required TODO.",
    approveReviewerPlaceholder: "e.g. reviewer",
    approveReviewerConfirm: "Approve and Complete",
    approveReviewerRequired: "Approver name is required",
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

function sanitizeRenderedHtml(html) {
  const template = document.createElement("template");
  template.innerHTML = html;

  const blockedTags = new Set([
    "script",
    "style",
    "iframe",
    "object",
    "embed",
    "link",
    "meta",
    "base",
    "form",
  ]);

  const walker = document.createTreeWalker(template.content, NodeFilter.SHOW_ELEMENT);
  const elements = [];
  while (walker.nextNode()) {
    elements.push(walker.currentNode);
  }

  for (const el of elements) {
    const tag = el.tagName.toLowerCase();
    if (blockedTags.has(tag)) {
      el.remove();
      continue;
    }

    const attrs = Array.from(el.attributes);
    for (const attr of attrs) {
      const name = attr.name.toLowerCase();
      const value = attr.value.trim().toLowerCase();

      if (name.startsWith("on")) {
        el.removeAttribute(attr.name);
        continue;
      }

      if ((name === "href" || name === "src" || name === "xlink:href") && value.startsWith("javascript:")) {
        el.removeAttribute(attr.name);
      }
    }
  }

  return template.innerHTML;
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

function getTodoStatusLabel(status) {
  const map = {
    draft: t("todoStatusDraft"),
    in_progress: t("todoStatusInProgress"),
    review_required: t("todoStatusReviewRequired"),
    done: t("todoStatusDone"),
  };
  return map[status] || status;
}

function getTodoStatusOptions(selected) {
  return [
    { value: "draft", label: t("todoStatusDraft") },
    { value: "in_progress", label: t("todoStatusInProgress") },
    { value: "review_required", label: t("todoStatusReviewRequired") },
  ]
    .map((option) => {
      const selectedAttr = option.value === selected ? "selected" : "";
      return `<option value="${option.value}" ${selectedAttr}>${escapeHtml(option.label)}</option>`;
    })
    .join("");
}

function summarizeTodoStatuses(todos) {
  const counts = { draft: 0, in_progress: 0, review_required: 0, done: 0 };
  for (const todo of todos || []) {
    if (counts[todo.status] != null) counts[todo.status] += 1;
  }
  return counts;
}

function formatTodoStatusBreakdown(counts) {
  return t("todoSummaryBreakdown", {
    draft: counts.draft || 0,
    inProgress: counts.in_progress || 0,
    reviewRequired: counts.review_required || 0,
    done: counts.done || 0,
  });
}

const TODO_STATUS_META = [
  { key: "draft",           label: { ja: "下書き",       en: "Draft"   },           cssClass: "status-draft"           },
  { key: "in_progress",     label: { ja: "対応中",       en: "In Progress" },       cssClass: "status-in_progress"     },
  { key: "review_required", label: { ja: "レビュー待ち", en: "Review Req." },       cssClass: "status-review_required" },
  { key: "done",            label: { ja: "完了",         en: "Done"    },           cssClass: "status-done"            },
];

function renderTodoSummaryBadges(counts) {
  if (!todoSummaryBadges) return;
  const total = Object.values(counts).reduce((s, n) => s + n, 0);
  if (total === 0) {
    todoSummaryBadges.innerHTML = `<span class="todo-summary-empty">${escapeHtml(t("todoSummaryEmpty"))}</span>`;
    return;
  }
  const lang = currentLang === "ja" ? "ja" : "en";
  todoSummaryBadges.innerHTML = TODO_STATUS_META
    .filter((m) => counts[m.key] > 0)
    .map((m) => `<span class="todo-stat-pill ${m.cssClass}">${escapeHtml(m.label[lang])} ${counts[m.key]}</span>`)
    .join("");
}

function setTodoOverlayConfirmAction(action = null, label = "") {
  todoOverlayConfirmAction = action;
  if (!todoPreviewConfirmBtn) return;
  if (!action) {
    todoPreviewConfirmBtn.hidden = true;
    todoPreviewConfirmBtn.disabled = false;
    return;
  }
  todoPreviewConfirmBtn.hidden = false;
  todoPreviewConfirmBtn.disabled = false;
  todoPreviewConfirmBtn.textContent = label;
}

async function handleTodoOverlayConfirm() {
  if (typeof todoOverlayConfirmAction !== "function") return;
  await todoOverlayConfirmAction();
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
  setText("premiumLabel", t("premiumLabel"));
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

  const premiumLabel = document.getElementById("premiumToggleLabel");
  if (premiumLabel) premiumLabel.title = t("premiumTitle");

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
  if (todoOpenBtn) todoOpenBtn.textContent = t("todoOpenList");
  if (todoDrawerCloseBtn) todoDrawerCloseBtn.textContent = t("todoOverlayClose");
  if (todoPreviewCancelBtn) todoPreviewCancelBtn.textContent = t("cancel");
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

// アップロード中の UI 制御ヘルパー
function setUploadUIEnabled(enabled) {
  isUploading = !enabled;
  // メッセージ送信
  inputEl.disabled = !enabled;
  sendBtn.disabled = !enabled;
  // フィルタ・モデル選択
  premiumToggle.disabled = !enabled;
  reasoningModeToggle.disabled = !enabled;
  wingFilter?.disabled ? (wingFilter.disabled = !enabled) : null;
  roomFilter?.disabled ? (roomFilter.disabled = !enabled) : null;
  contentTypeFilter?.disabled ? (contentTypeFilter.disabled = !enabled) : null;
  modelSelect.disabled = !enabled;
  // プロジェクト管理
  uploadProjectSelect.disabled = !enabled;
  addProjectBtn.disabled = !enabled;
  bulkUploadBtn.disabled = !enabled;
  // 仕様書削除ボタン（全て無効化）
  document.querySelectorAll(".doc-del").forEach(el => {
    el.disabled = !enabled;
    el.style.pointerEvents = !enabled ? "none" : "auto";
  });
  // ファイルアップロード
  fileInput.disabled = !enabled;
  uploadArea.disabled = !enabled;
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
  const syncExpandedState = (expanded) => {
    toggleBtn.setAttribute("aria-expanded", String(expanded));
    bodyEl.hidden = !expanded;
  };

  syncExpandedState(toggleBtn.getAttribute("aria-expanded") === "true");

  toggleBtn.addEventListener("click", () => {
    if (sidebarCollapsed) {
      setSidebarCollapsed(false);
      return;
    }
    const expanded = toggleBtn.getAttribute("aria-expanded") === "true";
    syncExpandedState(!expanded);
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
  const requestSeq = ++modelLoadRequestSeq;

  try {
    // 「読み込み中...」状態を表示
    modelSelect.innerHTML = `<option value="" disabled selected>${t("modelLoading")}</option>`;
    modelSelect.disabled = true;
    if (premiumToggle) premiumToggle.disabled = true;

    const usePremium = premiumToggle ? premiumToggle.checked : true;
    const url = usePremium ? "/api/models" : "/api/models?premium=false";
    const res = await fetch(url);
    if (!res.ok) throw new Error(res.statusText);
    const models = await res.json();
    if (requestSeq !== modelLoadRequestSeq) return;

    modelSelect.innerHTML = "";
    let selectedFound = false;
    for (const m of models) {
      const opt = document.createElement("option");
      opt.value = m.id;
      opt.textContent = m.id;
      // claude-sonnet-4.5 をデフォルト選択
      if (m.id === "claude-sonnet-4.5") {
        opt.selected = true;
        selectedFound = true;
      }
      modelSelect.appendChild(opt);
    }
    // デフォルトモデルが利用不可の場合、最初のモデルを選択
    if (!selectedFound && models.length > 0) {
      modelSelect.children[0].selected = true;
    }
    if (models.length === 0) throw new Error(t("modelFetchZero"));
  } catch (e) {
    // 古いリクエストの失敗結果は画面に反映しない
    if (requestSeq !== modelLoadRequestSeq) return;

    console.warn(t("modelFetchFallback"), e);
    modelSelect.innerHTML = `
      <option value="claude-sonnet-4.5" selected>claude-sonnet-4.5</option>
      <option value="claude-opus-4.5">claude-opus-4.5</option>
      <option value="gpt-4.1">gpt-4.1</option>
    `;
  } finally {
    if (requestSeq === modelLoadRequestSeq) {
      modelSelect.disabled = false;
      // アップロード中に入った場合は無効状態を維持する
      if (premiumToggle) premiumToggle.disabled = isUploading;
    }
  }
}

// ====================================================
// メッセージ描画
// ====================================================

function appendMessage(role, contentOrEl, options = {}) {
  const msg = document.createElement("div");
  msg.className = `msg ${role}`;
  if (options.messageId != null) {
    msg.dataset.messageId = String(options.messageId);
  }

  const avatar = document.createElement("div");
  avatar.className = "msg-avatar";
  avatar.textContent = role === "user" ? "👤" : "🤖";

  const bubble = document.createElement("div");
  bubble.className = "msg-bubble";

  if (typeof contentOrEl === "string") {
    if (role === "assistant") {
      bubble.innerHTML = sanitizeRenderedHtml(marked.parse(contentOrEl));
      bubble.dataset.raw = contentOrEl;
      addCopyButtonToBubble(bubble, () => bubble.dataset.raw || "");
    } else {
      bubble.textContent = contentOrEl;
    }
  } else {
    bubble.appendChild(contentOrEl);
  }

  if (role === "assistant" && options.messageId != null && currentSessionId) {
    const actionBar = document.createElement("div");
    actionBar.className = "msg-action-bar";
    const todoBtn = document.createElement("button");
    todoBtn.type = "button";
    todoBtn.className = "msg-todo-btn";
    todoBtn.textContent = "TODO化";
    todoBtn.addEventListener("click", async () => {
      await createTodoFromAnswer(options.messageId);
    });
    actionBar.appendChild(todoBtn);
    bubble.appendChild(actionBar);
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

function normalizeChatErrorMessage(error) {
  const raw = String(error?.message || "").trim();
  const msg = raw || "Unknown error";
  const lower = msg.toLowerCase();
  const unavailable =
    lower.includes("failed to fetch") ||
    lower.includes("networkerror") ||
    lower.includes("connection refused") ||
    lower.includes("err_connection_refused") ||
    lower.includes("load failed");

  if (unavailable) {
    return t("chatBackendUnavailable");
  }
  return msg;
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

  // ステータスバー（回答バブルの直前に挿入）
  const statusBar = document.createElement("div");
  statusBar.className = "chat-status-bar";
  statusBar.textContent = t("chatStatusThinking");
  const botMsg = botBubble.closest(".msg");
  if (botMsg) messagesEl.insertBefore(statusBar, botMsg);

  const clearStatus = () => {
    statusBar.remove();
  };

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
        } else if (ev.type === "status") {
          if (ev.status === "thinking") {
            statusBar.textContent = t("chatStatusThinking");
          } else if (ev.status === "searching") {
            statusBar.textContent = t("chatStatusSearching", { query: ev.query || "" });
          }
        } else if (ev.type === "delta") {
          clearStatus();
          accumulated += ev.content;
          botBubble.innerHTML = sanitizeRenderedHtml(marked.parse(accumulated));
          botBubble.dataset.raw = accumulated;
          addCopyButtonToBubble(botBubble, () => botBubble.dataset.raw || "");
          scrollToBottom();
        } else if (ev.type === "error") {
          showToast(t("chatError", { message: ev.message }), "error");
        } else if (ev.type === "done") {
          if (!currentSessionId) currentSessionId = ev.session_id;
          await loadSession(currentSessionId, sessionTitle.textContent || t("newChat"));
          await loadHistory();
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
    clearStatus();
    const message = normalizeChatErrorMessage(e);
    botBubble.textContent = `⚠️ ${t("chatError", { message })}`;
    showToast(message, "error");
  } finally {
    clearStatus();
    setInputEnabled(true);
    inputEl.focus();
  }
}

function openTodoDrawer() {
  if (!todoDrawerBackdrop) return;
  todoDrawerBackdrop.hidden = false;
  document.body.classList.add("todo-drawer-open");
}

function closeTodoDrawer() {
  if (!todoDrawerBackdrop) return;
  todoDrawerBackdrop.hidden = true;
  document.body.classList.remove("todo-drawer-open");
}

function closeTodoDetail() {
  currentTodoId = null;
  currentTodoDetailData = null;
  renderTodoList(currentTodos);
  if (todoDetail) {
    todoDetail.hidden = true;
    todoDetail.innerHTML = "";
  }
  if (todoDetailEmpty) todoDetailEmpty.hidden = false;
}

function closeTodoPreview() {
  currentTodoPreviewMessageId = null;
  todoOverlayConfirmAction = null;
  if (todoPreviewOverlay) todoPreviewOverlay.hidden = true;
  document.body.classList.remove("todo-preview-open");
  if (todoPreviewBody) {
    todoPreviewBody.innerHTML = `
      <div class="todo-preview-loading">
        <div class="upload-modal-spinner" aria-hidden="true"></div>
        <div class="todo-preview-note">${escapeHtml(t("todoPreviewGeneratingNote"))}</div>
      </div>
    `;
  }
  if (todoPreviewTitle) todoPreviewTitle.textContent = t("todoPreviewGeneratingTitle");
  setTodoOverlayConfirmAction(null);
  if (todoPreviewCancelBtn) {
    todoPreviewCancelBtn.disabled = false;
    todoPreviewCancelBtn.textContent = t("cancel");
  }
}

function showTodoPreviewLoading() {
  if (!todoPreviewOverlay) return;
  todoPreviewOverlay.hidden = false;
  document.body.classList.add("todo-preview-open");
  if (todoPreviewTitle) todoPreviewTitle.textContent = t("todoPreviewGeneratingTitle");
  if (todoPreviewBody) {
    todoPreviewBody.innerHTML = `
      <div class="todo-preview-loading">
        <div class="upload-modal-spinner" aria-hidden="true"></div>
        <div class="todo-preview-note">${escapeHtml(t("todoPreviewGeneratingNote"))}</div>
      </div>
    `;
  }
  setTodoOverlayConfirmAction(null);
  if (todoPreviewCancelBtn) {
    todoPreviewCancelBtn.disabled = false;
    todoPreviewCancelBtn.textContent = t("cancel");
  }
}

function showTodoPreviewForm(preview) {
  if (!todoPreviewBody || !todoPreviewTitle || !todoPreviewConfirmBtn) return;
  todoPreviewTitle.textContent = t("todoPreviewConfirmTitle");
  todoPreviewBody.innerHTML = `
    <div class="todo-preview-form">
      <label>
        ${escapeHtml(t("todoFieldTitle"))}
        <input id="todoPreviewTitleInput" class="todo-select" value="${escapeHtml(preview.title || "")}" />
      </label>
      <label>
        ${escapeHtml(t("todoFieldDescription"))}
        <textarea id="todoPreviewDescriptionInput" class="todo-textarea">${escapeHtml(preview.description || "")}</textarea>
      </label>
      <label>
        ${escapeHtml(t("todoFieldAcceptance"))}
        <textarea id="todoPreviewAcceptanceInput" class="todo-textarea">${escapeHtml(preview.acceptance_criteria || "")}</textarea>
      </label>
    </div>
  `;
  setTodoOverlayConfirmAction(submitTodoPreview, t("todoPreviewConfirmButton"));
}

function showTodoDraftProgressModal({ title, description, acceptanceCriteria, relatedCount }) {
  if (!todoPreviewOverlay || !todoPreviewTitle || !todoPreviewBody) return;
  todoPreviewOverlay.hidden = false;
  document.body.classList.add("todo-preview-open");
  todoPreviewTitle.textContent = t("todoDraftModalProgressTitle");
  todoPreviewBody.innerHTML = `
    <div class="todo-preview-form">
      <div class="todo-preview-note">${escapeHtml(t("todoDraftModalContextTitle"))}</div>
      <label>
        ${escapeHtml(t("todoFieldTitle"))}
        <input class="todo-select" value="${escapeHtml(title || "")}" disabled />
      </label>
      <label>
        ${escapeHtml(t("todoFieldDescription"))}
        <textarea class="todo-textarea" disabled>${escapeHtml(description || "")}</textarea>
      </label>
      <label>
        ${escapeHtml(t("todoFieldAcceptance"))}
        <textarea class="todo-textarea" disabled>${escapeHtml(acceptanceCriteria || "")}</textarea>
      </label>
      <div class="todo-preview-note">${escapeHtml(t("todoRelatedMessageCount", { count: relatedCount }))}</div>
      <div class="todo-preview-loading">
        <div class="upload-modal-spinner" aria-hidden="true"></div>
        <div class="todo-preview-note">${escapeHtml(t("todoOverlayGenerating"))}</div>
      </div>
    </div>
  `;
  setTodoOverlayConfirmAction(null);
  if (todoPreviewCancelBtn) {
    todoPreviewCancelBtn.disabled = true;
    todoPreviewCancelBtn.textContent = t("todoOverlayGenerating");
  }
}

function showTodoDraftResultModal({ success, message }) {
  if (!todoPreviewOverlay || !todoPreviewTitle || !todoPreviewBody) return;
  todoPreviewOverlay.hidden = false;
  document.body.classList.add("todo-preview-open");
  todoPreviewTitle.textContent = success ? t("todoDraftModalResultTitle") : t("todoDraftModalErrorTitle");
  todoPreviewBody.innerHTML = `
    <div class="todo-preview-form">
      <div class="todo-preview-note">${escapeHtml(message)}</div>
    </div>
  `;
  setTodoOverlayConfirmAction(null);
  if (todoPreviewCancelBtn) {
    todoPreviewCancelBtn.disabled = false;
    todoPreviewCancelBtn.textContent = t("todoOverlayClose");
  }
}

function showTodoApprovalModal(todoId) {
  if (!todoPreviewOverlay || !todoPreviewTitle || !todoPreviewBody) return;
  todoPreviewOverlay.hidden = false;
  document.body.classList.add("todo-preview-open");
  todoPreviewTitle.textContent = t("approveReviewerTitle");
  todoPreviewBody.innerHTML = `
    <div class="todo-preview-form">
      <div class="todo-preview-note">${escapeHtml(t("approveReviewerHelp"))}</div>
      <label>
        ${escapeHtml(t("approveReviewerTitle"))}
        <input id="todoApproveReviewerInput" class="todo-select" placeholder="${escapeHtml(t("approveReviewerPlaceholder"))}" value="reviewer" />
      </label>
    </div>
  `;
  setTodoOverlayConfirmAction(async () => {
    const reviewer = document.getElementById("todoApproveReviewerInput")?.value?.trim() || "";
    if (!reviewer) {
      showToast(t("approveReviewerRequired"), "error");
      return;
    }

    if (todoPreviewConfirmBtn) todoPreviewConfirmBtn.disabled = true;
    try {
      const res = await fetch(`/api/history/${currentSessionId}/todos/${todoId}/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ approved_by: reviewer }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || res.statusText);
      closeTodoPreview();
      await loadTodos(currentSessionId);
      await openTodoDetail(todoId);
      showToast(t("todoApproveDone"), "success");
    } catch (e) {
      if (todoPreviewConfirmBtn) todoPreviewConfirmBtn.disabled = false;
      showToast(t("todoActionFailed", { action: t("todoActionApprove"), message: e.message }), "error");
    }
  }, t("approveReviewerConfirm"));
  if (todoPreviewCancelBtn) {
    todoPreviewCancelBtn.disabled = false;
    todoPreviewCancelBtn.textContent = t("cancel");
  }
}

async function confirmDeleteSession(session) {
  if (!session?.todo_count) {
    await deleteSession(session.id, { bypassModal: true });
    return;
  }

  const res = await fetch(`/api/history/${session.id}/todos`);
  const todos = res.ok ? await res.json() : [];
  const counts = summarizeTodoStatuses(todos);
  const titles = todos.slice(0, 5).map((todo) => `<li>${escapeHtml(todo.title)}</li>`).join("");

  if (!todoPreviewOverlay || !todoPreviewTitle || !todoPreviewBody) return;
  todoPreviewOverlay.hidden = false;
  document.body.classList.add("todo-preview-open");
  todoPreviewTitle.textContent = t("deleteSessionTodoTitle");
  todoPreviewBody.innerHTML = `
    <div class="todo-preview-form">
      <div class="todo-preview-note">${escapeHtml(t("deleteSessionTodoMessage", { count: session.todo_count }))}</div>
      <div class="todo-preview-note">${escapeHtml(t("deleteSessionTodoBreakdown", { summary: formatTodoStatusBreakdown(counts) }))}</div>
      <div class="todo-preview-note">${escapeHtml(t("deleteSessionTodoItems"))}</div>
      <ul class="todo-preview-list">${titles || `<li>${escapeHtml(t("todoNone"))}</li>`}</ul>
    </div>
  `;
  setTodoOverlayConfirmAction(async () => {
    if (todoPreviewConfirmBtn) todoPreviewConfirmBtn.disabled = true;
    await deleteSession(session.id, { bypassModal: true });
    closeTodoPreview();
  }, t("deleteSessionConfirm"));
  if (todoPreviewCancelBtn) {
    todoPreviewCancelBtn.disabled = false;
    todoPreviewCancelBtn.textContent = t("cancel");
  }
}

async function submitTodoPreview() {
  if (!currentSessionId || currentTodoPreviewMessageId == null) return;
  const title = document.getElementById("todoPreviewTitleInput")?.value?.trim() || "";
  const description = document.getElementById("todoPreviewDescriptionInput")?.value || "";
  const acceptance = document.getElementById("todoPreviewAcceptanceInput")?.value || "";
  if (!title) {
    showToast(t("todoTitleRequired"), "error");
    return;
  }

  if (todoPreviewConfirmBtn) todoPreviewConfirmBtn.disabled = true;
  try {
    const res = await fetch(`/api/history/${currentSessionId}/todos`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title,
        description,
        acceptance_criteria: acceptance,
        created_from_message_id: Number(currentTodoPreviewMessageId),
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || res.statusText);

    closeTodoPreview();
    await loadTodos(currentSessionId);
    await loadHistory();
    openTodoDrawer();
    await openTodoDetail(data.id);
    showToast(t("todoCreated"), "success");
  } catch (e) {
    if (todoPreviewConfirmBtn) todoPreviewConfirmBtn.disabled = false;
    showToast(t("todoActionFailed", { action: t("todoActionCreate"), message: e.message }), "error");
  }
}

async function createTodoFromAnswer(messageId) {
  if (!currentSessionId) return;
  currentTodoPreviewMessageId = Number(messageId);
  showTodoPreviewLoading();

  try {
    const res = await fetch(`/api/history/${currentSessionId}/todos/preview`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message_id: Number(messageId), model: modelSelect?.value || "claude-sonnet-4.5" }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || res.statusText);
    showTodoPreviewForm(data);
  } catch (e) {
    closeTodoPreview();
    showToast(t("todoActionFailed", { action: t("todoActionPreview"), message: e.message }), "error");
  }
}

function renderTodoList(items) {
  if (!todoList) return;
  currentTodos = items || [];

  if (!currentTodos.length) {
    todoList.innerHTML = '<div class="todo-empty">TODOはまだありません</div>';
    return;
  }

  todoList.innerHTML = currentTodos
    .map((todo) => {
      const active = currentTodoId === todo.id ? " active" : "";
      return `
        <button type="button" class="todo-item${active}" data-todo-id="${todo.id}" data-session-id="${escapeHtml(todo.session_id)}">
          <span class="todo-item-title">${escapeHtml(todo.title)}</span>
          <span class="todo-item-status status-${todo.status}">${escapeHtml(getTodoStatusLabel(todo.status))}</span>
        </button>
      `;
    })
    .join("");

  todoList.querySelectorAll(".todo-item").forEach((el) => {
    el.addEventListener("click", async () => {
      const id = Number(el.dataset.todoId);
      await openTodoDetail(id);
    });
  });
}

async function loadTodos(sessionId) {
  if (!todoWorkflow || !todoList) return;
  if (!sessionId) {
    todoWorkflow.hidden = true;
    renderTodoList([]);
    closeTodoDetail();
    closeTodoDrawer();
    return;
  }

  try {
    const res = await fetch(`/api/history/${sessionId}/todos`);
    if (!res.ok) throw new Error(res.statusText);
    const items = await res.json();
    todoWorkflow.hidden = false;
    const counts = summarizeTodoStatuses(items);
    renderTodoSummaryBadges(counts);
    if (todoOpenBtn) todoOpenBtn.disabled = items.length === 0;
    renderTodoList(items);
  } catch (e) {
    todoWorkflow.hidden = false;
    renderTodoSummaryBadges({ draft: 0, in_progress: 0, review_required: 0, done: 0 });
    if (todoOpenBtn) todoOpenBtn.disabled = true;
    todoList.innerHTML = `<div class="todo-empty" style="color:var(--danger)">TODO取得失敗: ${escapeHtml(e.message)}</div>`;
  }
}

async function openTodoDetail(todoId) {
  if (!currentSessionId || !todoDetail || !todoDetailEmpty) return;

  try {
    const res = await fetch(`/api/history/${currentSessionId}/todos/${todoId}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || res.statusText);

    currentTodoDetailData = data;
    currentTodoId = todoId;
    renderTodoList(currentTodos);
    openTodoDrawer();

    const todo = data.item;
    const relatedMessages = (data.links || []).filter((l) => l.link_type === "message" && l.message_id != null);
    const relatedDrafts = (data.links || []).filter((l) => l.link_type === "draft" && l.message_id != null);

    todoDetailEmpty.hidden = true;
    todoDetail.hidden = false;
    todoDetail.innerHTML = `
      <div class="todo-detail-head">
        <h4>${escapeHtml(todo.title)}</h4>
        <div class="todo-detail-meta">
          <span class="todo-item-status status-${todo.status}">${escapeHtml(getTodoStatusLabel(todo.status))}</span>
          <button id="todoDetailCloseBtn" class="todo-detail-close" type="button">閉じる</button>
        </div>
      </div>
      <label>${escapeHtml(t("todoFieldDescription"))}</label>
      <textarea id="todoDescriptionInput" class="todo-textarea">${escapeHtml(todo.description || "")}</textarea>
      <label>${escapeHtml(t("todoFieldAcceptance"))}</label>
      <textarea id="todoAcceptanceInput" class="todo-textarea">${escapeHtml(todo.acceptance_criteria || "")}</textarea>
      <label>${escapeHtml(t("todoFieldStatus"))}</label>
      <select id="todoStatusSelect" class="todo-select">
        ${getTodoStatusOptions(todo.status)}
      </select>
      <div class="todo-detail-actions">
        <button id="todoDraftBtn" type="button">${escapeHtml(t("todoDraftButton"))}</button>
        ${todo.status === "review_required" ? `<button id="todoApproveBtn" type="button">${escapeHtml(t("todoApproveDoneButton"))}</button>` : ""}
        <button id="todoSaveBtn" class="todo-action-save" type="button">${escapeHtml(t("todoSave"))}</button>
      </div>
      <div class="todo-approve-hint ${todo.status === "review_required" ? "is-ready" : ""}">${escapeHtml(todo.status === "review_required" ? t("todoApproveHintReady") : t("todoApproveHintNeedReview"))}</div>
      <div class="todo-links">
        <div class="todo-links-title">${escapeHtml(t("todoRelatedMessageCount", { count: relatedMessages.length }))}</div>
        <div class="todo-links-title">${escapeHtml(t("todoDraftMessageIds", { ids: relatedDrafts.map((d) => d.message_id).join(", ") || t("todoNone") }))}</div>
      </div>
    `;

    document.getElementById("todoDetailCloseBtn")?.addEventListener("click", closeTodoDetail);
    document.getElementById("todoSaveBtn")?.addEventListener("click", async () => {
      await updateTodo(todo.id);
    });
    document.getElementById("todoApproveBtn")?.addEventListener("click", async () => {
      await approveTodo(todo.id);
    });
    document.getElementById("todoDraftBtn")?.addEventListener("click", async () => {
      await generateTodoDraft(todo.id);
    });
  } catch (e) {
    currentTodoDetailData = null;
    todoDetailEmpty.hidden = false;
    todoDetail.hidden = true;
    showToast(`TODO詳細取得失敗: ${e.message}`, "error");
  }
}

async function updateTodo(todoId) {
  const description = document.getElementById("todoDescriptionInput")?.value || "";
  const acceptance = document.getElementById("todoAcceptanceInput")?.value || "";
  const status = document.getElementById("todoStatusSelect")?.value || "draft";

  const res = await fetch(`/api/history/${currentSessionId}/todos/${todoId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ description, acceptance_criteria: acceptance, status }),
  });
  const data = await res.json();
  if (!res.ok) {
    showToast(t("todoActionFailed", { action: t("todoActionSave"), message: data.detail || res.statusText }), "error");
    return;
  }
  await loadTodos(currentSessionId);
  await openTodoDetail(todoId);
  showToast(t("todoSaveDone"), "success");
}

async function approveTodo(todoId) {
  showTodoApprovalModal(todoId);
}

async function generateTodoDraft(todoId) {
  if (!currentSessionId) return;
  const title = currentTodoDetailData?.item?.title || "";
  const description = document.getElementById("todoDescriptionInput")?.value || currentTodoDetailData?.item?.description || "";
  const acceptanceCriteria = document.getElementById("todoAcceptanceInput")?.value || currentTodoDetailData?.item?.acceptance_criteria || "";
  const relatedCount = (currentTodoDetailData?.links || []).filter((item) => item.link_type === "message").length;

  closeTodoDrawer();
  showTodoDraftProgressModal({ title, description, acceptanceCriteria, relatedCount });

  const model = modelSelect?.value || "claude-sonnet-4.5";
  try {
    const res = await fetch(`/api/history/${currentSessionId}/todos/${todoId}/draft`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model }),
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || res.statusText);
    }

    await Promise.all([
      loadTodos(currentSessionId),
      loadSession(currentSessionId, sessionTitle.textContent || t("newChat")),
    ]);
    showTodoDraftResultModal({ success: true, message: t("todoDraftModalResultBody") });
    showToast(t("todoDraftGenerated"), "success");
  } catch (e) {
    showTodoDraftResultModal({ success: false, message: e.message });
    showToast(t("todoActionFailed", { action: t("todoActionDraft"), message: e.message }), "error");
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
  currentHistorySessions = sessions || [];
  historyList.innerHTML = "";
  historyBadge.textContent = sessions.length;
  for (const s of sessions) {
    const item = document.createElement("div");
    item.className = "history-item" + (s.id === currentSessionId ? " active" : "");
    item.dataset.id = s.id;

    const titleEl = document.createElement("span");
    titleEl.className = "h-title";
    titleEl.textContent = s.title;

    const todoBadge = document.createElement("span");
    if (s.todo_count > 0) {
      todoBadge.className = "h-todo-badge doc-count-badge";
      todoBadge.textContent = `${s.todo_count}件`;
    } else {
      todoBadge.className = "h-todo-badge";
    }

    const delBtn = document.createElement("button");
    delBtn.className = "h-del";
    delBtn.title = t("docDeleteTitle");
    delBtn.innerHTML = "✕";
    delBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      confirmDeleteSession(s);
    });

    item.appendChild(titleEl);
    item.appendChild(todoBadge);
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
      appendMessage(m.role, m.content, { messageId: m.id });
    }
    await Promise.all([
      loadRetrievalLogs(sessionId),
      loadTodos(sessionId),
    ]);
    renderHistoryList(await (await fetch("/api/history")).json());
  } catch (e) {
    showToast(t("sessionLoadFailed", { message: e.message }), "error");
  }
}

async function deleteSession(sessionId, options = {}) {
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
  currentTodoId = null;
  currentTodos = [];
  sessionTitle.textContent = t("newChat");
  messagesEl.innerHTML = "";
  messagesEl.style.display = "none";
  welcomeEl.style.display = "flex";
  inputEl.value = "";
  if (retrievalPanel) retrievalPanel.hidden = true;
  if (todoWorkflow) todoWorkflow.hidden = true;
  closeTodoDetail();
  closeTodoDrawer();
  closeTodoPreview();
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
      <span class="doc-count-badge">${projectDocs.length}</span>
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
        <span class="doc-count-badge">${visible.length}/${items.length}</span>
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
          <span class="doc-drawers doc-count-badge">${t("docsCount", { count: d.drawer_count })}</span>
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

  // モーダル初期化
  uploadModalOverlay.removeAttribute("hidden");
  uploadModalTitle.textContent = "アップロード中...";
  uploadModalBar.value = 0;
  uploadModalPercent.textContent = "0%";
  uploadModalStatus.textContent = "";

  // アップロード開始時に UI を無効化
  setUploadUIEnabled(false);

  let cancelled = false;
  uploadModalCancelBtn.onclick = () => { cancelled = true; };

  for (let i = 0; i < fileArray.length && !cancelled; i++) {
    const file = fileArray[i];
    const project = uploadProjectSelect?.value || "";
    uploadModalStatus.textContent = `${i + 1}/${fileArray.length}: ${file.name}`;
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

    const progress = Math.round(((i + 1) / fileArray.length) * 100);
    uploadModalBar.value = progress;
    uploadModalPercent.textContent = progress + "%";
  }

  if (cancelled) {
    showToast(t("uploadCancelled") || "アップロードがキャンセルされました", "info");
  } else {
    uploadModalStatus.textContent = t("uploadDone");
    uploadModalPercent.textContent = "100%";
  }

  // モーダル閉じるまで待機（1.5秒後に自動閉じる）
  setTimeout(() => {
    uploadModalOverlay.setAttribute("hidden", "");
    uploadProgress.style.display = "none";
  }, cancelled ? 800 : 1500);

  // アップロード完了時に UI を再有効化
  setUploadUIEnabled(true);
  
  await loadDocuments();
}

async function uploadBulkFromFolder() {
  if (!bulkUploadBtn) return;

  // モーダル初期化
  uploadModalOverlay.removeAttribute("hidden");
  uploadModalTitle.textContent = "フォルダアップロード中...";
  uploadModalBar.value = 0;
  uploadModalPercent.textContent = "0%";
  uploadModalStatus.textContent = "";

  // アップロード開始時に UI を無効化
  setUploadUIEnabled(false);

  let cancelled = false;
  uploadModalCancelBtn.onclick = () => { cancelled = true; };

  try {
    const project = uploadProjectSelect?.value || "";
    const formData = new FormData();
    formData.append("project", project);

    const res = await fetch("/api/documents/bulk-upload", { method: "POST", body: formData });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || res.statusText);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buf = "";
    let uploaded = 0;
    let failed = 0;
    let total = 0;

    while (true && !cancelled) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });

      const lines = buf.split("\n");
      buf = lines.pop();

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        let ev;
        try { ev = JSON.parse(line.slice(6)); } catch { continue; }

        if (ev.type === "start") {
          total = ev.total;
          uploadModalStatus.textContent = t("bulkUploadStarted");
        } else if (ev.type === "file_result") {
          total = ev.total || total;
          if (ev.status === "uploaded") {
            uploaded++;
          } else {
            failed++;
          }
          const progress = Math.round(((uploaded + failed) / total) * 100);
          uploadModalBar.value = progress;
          uploadModalPercent.textContent = progress + "%";
          uploadModalStatus.textContent = `${uploaded + failed}/${total}: ${ev.filename}`;
          if (ev.status === "uploaded") {
            showToast(t("uploadDoneItem", { name: ev.filename, count: ev.drawer_count || 0, overwrite: "" }), "success");
          } else {
            showToast(t("uploadFailedItem", { name: ev.filename, message: ev.reason || "" }), "error");
          }
        } else if (ev.type === "done") {
          uploaded = ev.uploaded;
          failed = ev.failed;
          total = ev.total;
          uploadModalBar.value = 100;
          uploadModalPercent.textContent = "100%";
          uploadModalStatus.textContent = t("bulkUploadDone", { uploaded, total, failed });
          showToast(
            t("bulkUploadDone", { uploaded, total, failed }),
            failed > 0 ? "warn" : "success",
          );
        }
      }
    }

    if (cancelled) {
      showToast(t("uploadCancelled") || "アップロードがキャンセルされました", "info");
    }
  } catch (e) {
    uploadModalStatus.textContent = t("bulkUploadFailed", { message: e.message });
    showToast(t("bulkUploadFailed", { message: e.message }), "error");
  } finally {
    // モーダル閉じる
    setTimeout(() => {
      uploadModalOverlay.setAttribute("hidden", "");
    }, cancelled ? 800 : 1500);

    // アップロード完了時に UI を再有効化
    setUploadUIEnabled(true);
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
todoOpenBtn?.addEventListener("click", openTodoDrawer);
todoDrawerCloseBtn?.addEventListener("click", closeTodoDrawer);
if (bulkUploadBtn) {
  bulkUploadBtn.addEventListener("click", uploadBulkFromFolder);
}

todoPreviewCancelBtn?.addEventListener("click", closeTodoPreview);
todoPreviewConfirmBtn?.addEventListener("click", handleTodoOverlayConfirm);

todoDrawerBackdrop?.addEventListener("click", (e) => {
  if (e.target === todoDrawerBackdrop) closeTodoDrawer();
});

todoPreviewOverlay?.addEventListener("click", (e) => {
  if (e.target === todoPreviewOverlay) closeTodoPreview();
});

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

document.addEventListener("keydown", (e) => {
  if (e.key !== "Escape") return;
  if (todoPreviewOverlay && !todoPreviewOverlay.hidden) {
    closeTodoPreview();
    return;
  }
  if (todoDrawerBackdrop && !todoDrawerBackdrop.hidden) {
    closeTodoDrawer();
  }
});

// ====================================================
// 初期化
// ====================================================

// サイドバーのキーボードナビゲーション対応
function initSidebarKeyboardScroll() {
  if (!sidebar) return;

  const getScrollTarget = () => {
    const activeEl = document.activeElement;
    const candidates = [historyList, docList, historySectionBody, docSectionBody]
      .filter((el) => el && !el.hidden);

    for (const el of candidates) {
      const ownerSection = el.closest(".sb-section");
      const ownerToggle = ownerSection?.querySelector(".sb-section-header");
      const expanded = ownerToggle?.getAttribute("aria-expanded") !== "false";
      if (!expanded) continue;
      if (el.matches(":hover") || (activeEl && el.contains(activeEl))) {
        return el;
      }
    }
    return historyList || docList || sidebar;
  };

  sidebar.addEventListener("keydown", (e) => {
    if (e.target && (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA" || e.target.tagName === "SELECT")) {
      return;
    }

    const scrollTarget = getScrollTarget();
    if (!scrollTarget) return;
    const step = 50; // スクロール量（px）
    
    switch(e.key) {
      case "ArrowUp":
        scrollTarget.scrollTop -= step;
        e.preventDefault();
        break;
      case "ArrowDown":
        scrollTarget.scrollTop += step;
        e.preventDefault();
        break;
      case "Home":
        scrollTarget.scrollTop = 0;
        e.preventDefault();
        break;
      case "End":
        scrollTarget.scrollTop = scrollTarget.scrollHeight;
        e.preventDefault();
        break;
      case "PageUp":
        scrollTarget.scrollTop -= scrollTarget.clientHeight;
        e.preventDefault();
        break;
      case "PageDown":
        scrollTarget.scrollTop += scrollTarget.clientHeight;
        e.preventDefault();
        break;
    }
  });
}

(async () => {
  initTheme();
  initLanguage();
  initSidebarUi();
  initSidebarKeyboardScroll();
  premiumToggle?.addEventListener("change", () => loadModels());
  await Promise.all([loadModels(), loadHistory(), loadProjects(), loadDocuments()]);
  renderContextChips();
  updateAdvancedScopeSummary();
})();
