"""E2E テスト: 全機能網羅

実行方法:
    # サーバー起動後
    BASE_URL=http://localhost:18080 pytest tests/e2e/ -v --browser chromium

テスト対象機能:
    - ページ表示・UI レイアウト
    - テーマ切替（ライト / ダーク）
    - 言語切替（日本語 / 英語）
    - サイドバー開閉
    - 個別ファイルアップロード（TXT / Markdown）
    - 一括アップロード進捗表示（SSE）
    - プロジェクト作成・削除
    - アップロード先プロジェクト選択
    - ドキュメント一覧表示・絞り込みフィルター
    - ドキュメント削除
    - コンテキストチップ追加 / 削除
    - チャット送信と進捗ステータスバー
    - 会話履歴リスト・セッション読込・削除
    - 詳細フィルター（wing / room / content_type）
    - 新規チャット
"""
import io
import os
import time

import pytest
from playwright.sync_api import Page, expect

BASE_URL = os.environ.get("BASE_URL", "http://localhost:18080")
TIMEOUT = 10_000  # ms


# ===================================================================
# ヘルパー
# ===================================================================

def navigate_to_app(page: Page) -> None:
    """アプリのトップページに移動し、初期ロードを待つ。"""
    page.goto(BASE_URL)
    page.wait_for_load_state("networkidle", timeout=15_000)


def upload_text_file_api(filename: str, content: str, project: str = "") -> None:
    """API 経由でテキストファイルをアップロードする（UI 操作の前提条件設定用）。"""
    import requests
    resp = requests.post(
        f"{BASE_URL}/api/documents",
        files={"file": (filename, io.BytesIO(content.encode("utf-8")), "text/plain")},
        data={"wing": "specifications", "room": "test-room", "project": project},
        timeout=30,
    )
    resp.raise_for_status()


# ===================================================================
# TC01: ページ表示
# ===================================================================

class TestPageDisplay:
    """ページの基本表示を確認する。"""

    def test_title_is_spec_copilot(self, page: Page):
        """ブラウザタイトルが 'Spec Copilot' であること。"""
        navigate_to_app(page)
        expect(page).to_have_title("Spec Copilot")

    def test_sidebar_visible(self, page: Page):
        """サイドバーが表示されていること。"""
        navigate_to_app(page)
        expect(page.locator(".sidebar")).to_be_visible()

    def test_welcome_screen_visible(self, page: Page):
        """ウェルカム画面が表示されていること。"""
        navigate_to_app(page)
        expect(page.locator("#welcomeEl, .welcome").first).to_be_visible()

    def test_upload_area_visible(self, page: Page):
        """アップロードエリアが表示されていること。"""
        navigate_to_app(page)
        expect(page.locator("#uploadArea")).to_be_visible()

    def test_bulk_upload_btn_visible(self, page: Page):
        """一括アップロードボタンが表示されていること。"""
        navigate_to_app(page)
        expect(page.locator("#bulkUploadBtn")).to_be_visible()

    def test_model_select_populated(self, page: Page):
        """モデル選択リストにオプションが表示されること。"""
        navigate_to_app(page)
        page.wait_for_function(
            "document.querySelector('#modelSelect')?.options?.length > 1",
            timeout=TIMEOUT,
        )
        expect(page.locator("#modelSelect")).to_be_visible()

    def test_send_button_visible(self, page: Page):
        """送信ボタンが表示されていること。"""
        navigate_to_app(page)
        expect(page.locator("#sendBtn")).to_be_visible()

    def test_fileInput_accepts_image_extensions(self, page: Page):
        """fileInput が画像拡張子を accept していること。"""
        navigate_to_app(page)
        accept = page.locator("#fileInput").get_attribute("accept") or ""
        assert ".png" in accept
        assert ".drawio" in accept


# ===================================================================
# TC02: テーマ切替
# ===================================================================

class TestThemeToggle:
    """テーマ切替機能を確認する。"""

    def test_default_theme_applied(self, page: Page):
        """初期テーマが設定されていること。"""
        navigate_to_app(page)
        theme = page.locator("html").get_attribute("data-theme")
        assert theme in ("light", "dark")

    def test_toggle_changes_theme(self, page: Page):
        """テーマトグルボタンを押すとテーマが切り替わること。"""
        navigate_to_app(page)
        before = page.locator("html").get_attribute("data-theme")
        page.locator("#themeToggleBtn").click()
        after = page.locator("html").get_attribute("data-theme")
        assert before != after

    def test_toggle_twice_restores_theme(self, page: Page):
        """2回押すと元のテーマに戻ること。"""
        navigate_to_app(page)
        original = page.locator("html").get_attribute("data-theme")
        page.locator("#themeToggleBtn").click()
        page.locator("#themeToggleBtn").click()
        assert page.locator("html").get_attribute("data-theme") == original


# ===================================================================
# TC03: 言語切替
# ===================================================================

class TestLanguageToggle:
    """言語切替機能を確認する。"""

    def test_default_language_applied(self, page: Page):
        """デフォルト言語が設定されていること。"""
        navigate_to_app(page)
        assert page.locator("html").get_attribute("lang") in ("ja", "en")

    def test_switch_to_english(self, page: Page):
        """英語に切り替えると lang 属性が 'en' になること。"""
        navigate_to_app(page)
        page.locator("#languageSelect").select_option("en")
        page.wait_for_timeout(300)
        expect(page.locator("html")).to_have_attribute("lang", "en")

    def test_switch_back_to_japanese(self, page: Page):
        """日本語に切り替えると lang 属性が 'ja' になること。"""
        navigate_to_app(page)
        page.locator("#languageSelect").select_option("ja")
        page.wait_for_timeout(300)
        expect(page.locator("html")).to_have_attribute("lang", "ja")


# ===================================================================
# TC04: サイドバー開閉
# ===================================================================

class TestSidebarToggle:
    """サイドバーの開閉を確認する。"""

    def test_toggle_collapses_sidebar(self, page: Page):
        """トグルボタンでサイドバーが折りたたまれること。"""
        navigate_to_app(page)
        page.locator("#sidebarToggleBtn").click()
        page.wait_for_timeout(200)
        assert "collapsed" in (page.locator(".sidebar").get_attribute("class") or "")

    def test_toggle_expands_sidebar(self, page: Page):
        """再度トグルするとサイドバーが展開されること。"""
        navigate_to_app(page)
        page.locator("#sidebarToggleBtn").click()
        page.wait_for_timeout(100)
        page.locator("#sidebarToggleBtn").click()
        page.wait_for_timeout(200)
        assert "collapsed" not in (page.locator(".sidebar").get_attribute("class") or "")


# ===================================================================
# TC05: プロジェクト CRUD
# ===================================================================

class TestProjectCRUD:
    """プロジェクトの作成と削除を確認する。"""

    def test_open_project_dialog(self, page: Page):
        """プロジェクト追加ボタンでダイアログが開くこと。"""
        navigate_to_app(page)
        page.locator("#addProjectBtn").click()
        page.wait_for_timeout(300)
        assert page.locator("#projectDialogBackdrop").get_attribute("hidden") is None

    def test_cancel_closes_dialog(self, page: Page):
        """キャンセルボタンでダイアログが閉じること。"""
        navigate_to_app(page)
        page.locator("#addProjectBtn").click()
        page.wait_for_timeout(200)
        page.locator("#projectDialogCancel").click()
        page.wait_for_timeout(200)
        assert page.locator("#projectDialogBackdrop").get_attribute("hidden") is not None

    def test_create_project_appears_in_list(self, page: Page):
        """プロジェクト作成後にドキュメントリストに表示されること。"""
        navigate_to_app(page)
        project_name = f"E2EProject-{int(time.time())}"
        page.locator("#addProjectBtn").click()
        page.wait_for_timeout(200)
        page.locator("#projectDialogInput").fill(project_name)
        page.locator("#projectDialogCreate").click()
        page.wait_for_timeout(1000)
        expect(page.locator("#docList")).to_contain_text(project_name, timeout=TIMEOUT)

    def test_project_appears_in_upload_select(self, page: Page):
        """作成プロジェクトがアップロード先選択に表示されること。"""
        navigate_to_app(page)
        project_name = f"SelectProject-{int(time.time())}"
        page.locator("#addProjectBtn").click()
        page.wait_for_timeout(200)
        page.locator("#projectDialogInput").fill(project_name)
        page.locator("#projectDialogCreate").click()
        page.wait_for_timeout(1000)
        expect(page.locator("#uploadProjectSelect")).to_contain_text(project_name, timeout=TIMEOUT)

    def test_escape_closes_dialog(self, page: Page):
        """Escape キーでダイアログが閉じること。"""
        navigate_to_app(page)
        page.locator("#addProjectBtn").click()
        page.wait_for_timeout(200)
        page.locator("#projectDialogInput").press("Escape")
        page.wait_for_timeout(200)
        assert page.locator("#projectDialogBackdrop").get_attribute("hidden") is not None


# ===================================================================
# TC06: 個別ファイルアップロード
# ===================================================================

class TestFileUpload:
    """個別ファイルアップロード機能を確認する。"""

    def test_upload_txt_shows_in_doclist(self, page: Page):
        """テキストファイルをアップロードするとドキュメントリストに表示されること。"""
        navigate_to_app(page)
        filename = f"e2e-upload-{int(time.time())}.txt"
        with page.expect_file_chooser() as fc_info:
            page.locator("#uploadArea").click()
        fc_info.value.set_files(
            {"name": filename, "mimeType": "text/plain", "buffer": b"E2E test content"}
        )
        expect(page.locator("#uploadProgress")).to_be_visible(timeout=TIMEOUT)
        expect(page.locator("#docList")).to_contain_text(filename, timeout=TIMEOUT)

    def test_upload_progress_bar_shown(self, page: Page):
        """アップロード中に進捗バーが表示されること。"""
        navigate_to_app(page)
        filename = f"progress-{int(time.time())}.md"
        with page.expect_file_chooser() as fc_info:
            page.locator("#uploadArea").click()
        fc_info.value.set_files(
            {"name": filename, "mimeType": "text/markdown", "buffer": b"# Test"}
        )
        expect(page.locator("#uploadProgress")).to_be_visible(timeout=TIMEOUT)

    def test_upload_multiple_files(self, page: Page):
        """複数ファイルを一括アップロードできること。"""
        navigate_to_app(page)
        ts = int(time.time())
        files = [
            {"name": f"multi-a-{ts}.txt", "mimeType": "text/plain", "buffer": b"File A"},
            {"name": f"multi-b-{ts}.txt", "mimeType": "text/plain", "buffer": b"File B"},
        ]
        with page.expect_file_chooser() as fc_info:
            page.locator("#uploadArea").click()
        fc_info.value.set_files(files)
        doc_list = page.locator("#docList")
        expect(doc_list).to_contain_text(files[0]["name"], timeout=TIMEOUT)
        expect(doc_list).to_contain_text(files[1]["name"], timeout=TIMEOUT)

    def test_upload_to_project(self, page: Page):
        """プロジェクト選択後アップロードすると、そのプロジェクト配下に表示されること。"""
        navigate_to_app(page)
        project_name = f"UploadProj-{int(time.time())}"
        page.locator("#addProjectBtn").click()
        page.wait_for_timeout(200)
        page.locator("#projectDialogInput").fill(project_name)
        page.locator("#projectDialogCreate").click()
        page.wait_for_timeout(1000)

        page.locator("#uploadProjectSelect").select_option(
            label=f"アップロード先: {project_name}"
        )
        filename = f"proj-file-{int(time.time())}.txt"
        with page.expect_file_chooser() as fc_info:
            page.locator("#uploadArea").click()
        fc_info.value.set_files(
            {"name": filename, "mimeType": "text/plain", "buffer": b"project content"}
        )
        page.wait_for_timeout(2000)
        project_el = page.locator(f".doc-project:has-text('{project_name}')")
        expect(project_el).to_contain_text(filename, timeout=TIMEOUT)


# ===================================================================
# TC07: ドキュメント管理
# ===================================================================

class TestDocumentManagement:
    """ドキュメントの表示・フィルタ・削除を確認する。"""

    def test_document_appears_after_api_upload(self, page: Page):
        """API でアップロード後リロードするとリストに表示されること。"""
        navigate_to_app(page)
        filename = f"api-upload-{int(time.time())}.txt"
        upload_text_file_api(filename, "リスト表示テスト")
        page.reload()
        page.wait_for_load_state("networkidle")
        expect(page.locator("#docList")).to_contain_text(filename, timeout=TIMEOUT)

    def test_doc_filter_shows_matching_files(self, page: Page):
        """ファイル名フィルターで一致するファイルが表示されること。"""
        navigate_to_app(page)
        unique = f"filtertest-{int(time.time())}"
        upload_text_file_api(f"{unique}.txt", "フィルターテスト")
        page.reload()
        page.wait_for_load_state("networkidle")
        page.locator("#docFilter").fill(unique)
        page.wait_for_timeout(300)
        expect(page.locator("#docList")).to_contain_text(unique, timeout=TIMEOUT)

    def test_doc_delete_removes_from_list(self, page: Page):
        """削除ボタンを押すとリストから消えること。"""
        navigate_to_app(page)
        filename = f"delete-me-{int(time.time())}.txt"
        upload_text_file_api(filename, "削除テスト")
        page.reload()
        page.wait_for_load_state("networkidle")

        del_btn = page.locator(f".doc-item:has-text('{filename}') .doc-del").first
        del_btn.click(timeout=TIMEOUT)
        page.wait_for_timeout(1000)
        expect(page.locator("#docList")).not_to_contain_text(filename, timeout=TIMEOUT)


# ===================================================================
# TC08: コンテキストチップ
# ===================================================================

class TestContextChips:
    """コンテキストチップの追加・削除を確認する。"""

    def test_add_context_chip(self, page: Page):
        """⊕ ボタンでコンテキストチップが追加されること。"""
        navigate_to_app(page)
        filename = f"ctx-{int(time.time())}.txt"
        upload_text_file_api(filename, "コンテキストテスト")
        page.reload()
        page.wait_for_load_state("networkidle")

        add_btn = page.locator(
            f".doc-item:has-text('{filename}') button:not(.doc-del)"
        ).first
        add_btn.click(timeout=TIMEOUT)
        page.wait_for_timeout(300)
        expect(page.locator("#contextChips")).to_contain_text(filename, timeout=TIMEOUT)

    def test_remove_context_chip(self, page: Page):
        """✕ ボタンでコンテキストチップが削除されること。"""
        navigate_to_app(page)
        filename = f"ctx-rm-{int(time.time())}.txt"
        upload_text_file_api(filename, "削除テスト")
        page.reload()
        page.wait_for_load_state("networkidle")

        add_btn = page.locator(
            f".doc-item:has-text('{filename}') button:not(.doc-del)"
        ).first
        add_btn.click(timeout=TIMEOUT)
        page.wait_for_timeout(300)

        remove_btn = page.locator(f".context-chip:has-text('{filename}') .context-chip-remove")
        remove_btn.click(timeout=TIMEOUT)
        page.wait_for_timeout(300)
        expect(page.locator("#contextChips")).not_to_contain_text(filename, timeout=TIMEOUT)


# ===================================================================
# TC09: 一括アップロード進捗
# ===================================================================

class TestBulkUpload:
    """一括アップロードの進捗表示を確認する。"""

    def test_bulk_upload_shows_progress_area(self, page: Page):
        """一括アップロード実行時に進捗エリアが表示されること。"""
        navigate_to_app(page)
        page.locator("#bulkUploadBtn").click()
        expect(page.locator("#bulkProgress")).to_be_visible(timeout=TIMEOUT)

    def test_bulk_upload_button_reenabled_after_complete(self, page: Page):
        """一括アップロード完了後にボタンが再有効化されること。"""
        navigate_to_app(page)
        btn = page.locator("#bulkUploadBtn")
        btn.click()
        expect(btn).to_be_enabled(timeout=30_000)

    def test_bulk_upload_respects_project_selection(self, page: Page):
        """プロジェクト選択後に一括アップロードを実行しても正常完了すること。"""
        navigate_to_app(page)
        project_name = f"BulkProj-{int(time.time())}"
        page.locator("#addProjectBtn").click()
        page.wait_for_timeout(200)
        page.locator("#projectDialogInput").fill(project_name)
        page.locator("#projectDialogCreate").click()
        page.wait_for_timeout(1000)

        page.locator("#uploadProjectSelect").select_option(
            label=f"アップロード先: {project_name}"
        )
        page.locator("#bulkUploadBtn").click()
        expect(page.locator("#bulkUploadBtn")).to_be_enabled(timeout=30_000)


# ===================================================================
# TC10: チャット進捗ステータスバー
# ===================================================================

class TestChatProgress:
    """チャット進捗ステータスバーを確認する。"""

    def test_status_bar_appears_on_send(self, page: Page):
        """送信時にステータスバーが表示されること。"""
        navigate_to_app(page)
        page.locator("#inputEl").fill("テスト質問")
        page.locator("#sendBtn").click()
        expect(page.locator(".chat-status-bar")).to_be_visible(timeout=TIMEOUT)

    def test_welcome_hides_after_send(self, page: Page):
        """送信後にウェルカム画面が非表示になること。"""
        navigate_to_app(page)
        page.locator("#inputEl").fill("テスト")
        page.locator("#sendBtn").click()
        page.wait_for_timeout(500)
        expect(page.locator("#welcomeEl, .welcome").first).not_to_be_visible(timeout=TIMEOUT)

    def test_user_message_shown_in_chat(self, page: Page):
        """送信メッセージがチャット画面に表示されること。"""
        navigate_to_app(page)
        message = f"E2E chat {int(time.time())}"
        page.locator("#inputEl").fill(message)
        page.locator("#sendBtn").click()
        page.wait_for_timeout(300)
        expect(page.locator("#messagesEl")).to_contain_text(message, timeout=TIMEOUT)

    def test_input_reenabled_after_response(self, page: Page):
        """回答（またはエラー）後に入力欄が再有効化されること。"""
        navigate_to_app(page)
        page.locator("#inputEl").fill("テスト")
        page.locator("#sendBtn").click()
        expect(page.locator("#inputEl")).to_be_enabled(timeout=30_000)

    def test_enter_key_sends_message(self, page: Page):
        """Enter キーでメッセージが送信されること。"""
        navigate_to_app(page)
        message = f"Enter-{int(time.time())}"
        input_el = page.locator("#inputEl")
        input_el.fill(message)
        input_el.press("Enter")
        page.wait_for_timeout(300)
        expect(page.locator("#messagesEl")).to_contain_text(message, timeout=TIMEOUT)

    def test_shift_enter_adds_newline(self, page: Page):
        """Shift+Enter で改行が入ること（送信されないこと）。"""
        navigate_to_app(page)
        input_el = page.locator("#inputEl")
        input_el.fill("行1")
        input_el.press("Shift+Enter")
        input_el.type("行2")
        # 送信されていないこと（welcomeEl が表示のまま）
        expect(page.locator("#welcomeEl, .welcome").first).to_be_visible(timeout=3000)


# ===================================================================
# TC11: 会話履歴
# ===================================================================

class TestChatHistory:
    """会話履歴の表示・操作を確認する。"""

    def test_new_chat_btn_shows_welcome(self, page: Page):
        """新しい会話ボタンを押すとウェルカム画面に戻ること。"""
        navigate_to_app(page)
        page.locator("#inputEl").fill("こんにちは")
        page.locator("#sendBtn").click()
        page.wait_for_timeout(500)
        page.evaluate("document.getElementById('newChatBtn').click()")
        page.wait_for_timeout(300)
        expect(page.locator("#welcomeEl, .welcome").first).to_be_visible(timeout=TIMEOUT)

    def test_history_badge_visible(self, page: Page):
        """会話履歴バッジが表示されること。"""
        navigate_to_app(page)
        expect(page.locator("#historyBadge")).to_be_visible()

    def test_history_item_appears_after_chat(self, page: Page):
        """メッセージ送信後に履歴リストにセッションが追加されること。"""
        navigate_to_app(page)
        page.locator("#inputEl").fill("履歴テスト")
        page.locator("#sendBtn").click()
        page.wait_for_timeout(3000)
        items = page.locator("#historyList .history-item")
        expect(items.first).to_be_visible(timeout=TIMEOUT)


# ===================================================================
# TC12: 詳細フィルター
# ===================================================================

class TestAdvancedFilter:
    """詳細フィルターの操作を確認する。"""

    def _open_advanced_scope(self, page: Page) -> None:
        """詳細フィルターの <details> を開く。"""
        details = page.locator("#advancedScope")
        if details.get_attribute("open") is None:
            page.locator("#advancedScopeSummary").click()
            page.wait_for_timeout(200)

    def test_content_type_filter_visible(self, page: Page):
        """コンテンツ種別フィルターが表示されていること。"""
        navigate_to_app(page)
        self._open_advanced_scope(page)
        expect(page.locator("#contentTypeFilter")).to_be_visible()

    def test_room_filter_visible(self, page: Page):
        """room フィルター入力欄が表示されていること。"""
        navigate_to_app(page)
        self._open_advanced_scope(page)
        expect(page.locator("#roomFilter")).to_be_visible()

    def test_content_type_filter_updates_summary(self, page: Page):
        """コンテンツ種別を選択するとスコープサマリーが更新されること。"""
        navigate_to_app(page)
        self._open_advanced_scope(page)
        page.locator("#contentTypeFilter").select_option("text")
        page.wait_for_timeout(200)
        expect(page.locator("#advancedScopeSummary")).not_to_have_text("詳細フィルタ: すべて")

    def test_room_filter_updates_summary(self, page: Page):
        """room フィルターに入力するとスコープサマリーに反映されること。"""
        navigate_to_app(page)
        self._open_advanced_scope(page)
        page.locator("#roomFilter").fill("テストルーム")
        page.wait_for_timeout(200)
        expect(page.locator("#advancedScopeSummary")).to_contain_text("テストルーム")
