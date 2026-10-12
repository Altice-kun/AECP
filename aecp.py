import os
import socket
import hashlib
import threading
import time
import datetime
import json
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend

CONFIG_PATH = "./local_deta/performance/performance.json"
CURRENT_VERSION = "v2.1"
DEFAULT_PORT = 9876

class AECPApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"AECP - Altimece Encrypt Control Protocol ({CURRENT_VERSION}) [TCP Network Edition]")
        self.geometry("1100x900")
        self.resizable(True, True)

        # 設定の初期化と読み込み
        self.init_directories()
        self.config_data = self.load_config()

        # 自端末情報
        self.hostname = socket.gethostname()
        self.my_ipv4 = self.get_local_ipv4()
        
        # セッションフラグと現在開いているファイルパス、ソケット関連
        self.is_host_active = False
        self.is_client_connected = False
        self.current_open_filepath = None
        
        self.server_socket = None
        self.client_socket = None
        self.client_connections = []  # ホスト側が保持する接続中クライアントのリスト
        self.network_logs = []        # 共有ログのリスト

        # UI構築
        self.setup_menu()
        self.setup_ui()

    def init_directories(self):
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        os.makedirs("./local_workspace", exist_ok=True)

    def load_config(self):
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "session_password": "AECP_SECRET_2026", 
            "username": "User_" + socket.gethostname()[:5],
            "display_name": "Altice User",
            "connect_password": "password123",
            "host_ip": "127.0.0.1",
            "connect_mode": "IPアドレス"
        }

    def save_config(self, key, value):
        self.config_data[key] = value
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(self.config_data, f, indent=4, ensure_ascii=False)

    def get_local_ipv4(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(('8.8.8.8', 80))
                return s.getsockname()[0]
        except Exception:
            return '127.0.0.1'

    def derive_key(self, password):
        return hashlib.sha256(password.encode('utf-8')).digest()

    def encrypt_data(self, plaintext_bytes, key):
        iv = os.urandom(16)
        padder = padding.PKCS7(128).padder()
        padded = padder.update(plaintext_bytes) + padder.finalize()
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        ciphertext = cipher.encryptor().update(padded) + cipher.encryptor().finalize()
        return iv + ciphertext

    def decrypt_data(self, encrypted_bytes, key):
        iv = encrypted_bytes[:16]
        ciphertext = encrypted_bytes[16:]
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        padded = cipher.decryptor().update(ciphertext) + cipher.decryptor().finalize()
        unpadder = padding.PKCS7(128).unpadder()
        return unpadder.update(padded) + unpadder.finalize()

    # ==================== メニューバー ====================
    def setup_menu(self):
        menubar = tk.Menu(self)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="ワークスペースフォルダを開く", command=self.menu_open_dir)
        file_menu.add_separator()
        file_menu.add_command(label="終了", command=self.quit)
        menubar.add_cascade(label="ファイル", menu=file_menu)

        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="コンソールログ削除", command=self.menu_clear_logs)
        edit_menu.add_command(label="設定・アカウント情報", command=self.open_settings_dialog)
        menubar.add_cascade(label="編集", menu=edit_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="ソフトウェア情報 (About)", command=self.menu_about)
        menubar.add_cascade(label="ヘルプ", menu=help_menu)

        self.configure(menu=menubar)

    def menu_open_dir(self):
        path = "./local_workspace"
        if os.path.exists(path):
            os.startfile(path)

    def menu_clear_logs(self):
        for console in [self.host_console, self.client_console]:
            console.delete("0.0", "end")
        for chat in [self.host_chat_box, self.client_chat_box]:
            chat.delete("0.0", "end")

    def menu_about(self):
        messagebox.showinfo("ソフトウェア情報", f"Altimece Encrypt Control Protocol (AECP)\nVersion {CURRENT_VERSION} [TCP Network]\nCopyright 2026 Altice-Works Co., Ltd.")

    def open_settings_dialog(self):
        dlg = ctk.CTkToplevel(self)
        dlg.title("アカウント・表示名設定")
        dlg.geometry("400x320")
        dlg.resizable(False, False)
        dlg.grab_set()

        ctk.CTkLabel(dlg, text="ユーザー名 (System Username):", font=("Helvetica", 11, "bold")).pack(anchor="w", padx=20, pady=(15, 2))
        ent_user = ctk.CTkEntry(dlg, width=360, height=30)
        ent_user.pack(padx=20, pady=(0, 10))
        ent_user.insert(0, self.config_data.get("username", ""))

        ctk.CTkLabel(dlg, text="表示名 / ニックネーム (Display Name):", font=("Helvetica", 11, "bold")).pack(anchor="w", padx=20, pady=(0, 2))
        ent_display = ctk.CTkEntry(dlg, width=360, height=30)
        ent_display.pack(padx=20, pady=(0, 10))
        ent_display.insert(0, self.config_data.get("display_name", ""))

        ctk.CTkLabel(dlg, text="接続パスワード (Connect Password):", font=("Helvetica", 11, "bold")).pack(anchor="w", padx=20, pady=(0, 2))
        ent_pass = ctk.CTkEntry(dlg, show="*", width=360, height=30)
        ent_pass.pack(padx=20, pady=(0, 20))
        ent_pass.insert(0, self.config_data.get("connect_password", ""))

        def save_settings():
            self.save_config("username", ent_user.get().strip())
            self.save_config("display_name", ent_display.get().strip())
            self.save_config("connect_password", ent_pass.get().strip())
            messagebox.showinfo("成功", "設定を保存しました。")
            dlg.destroy()

        ctk.CTkButton(dlg, text="設定を保存", width=360, height=35, fg_color="#2b8252", hover_color="#216641", command=save_settings).pack(padx=20)

    # ==================== メインUI構造 ====================
    def setup_ui(self):
        self.tabview = ctk.CTkTabview(self, corner_radius=15)
        self.tabview.pack(fill="both", expand=True, padx=15, pady=15)

        self.tab_host = self.tabview.add("🖥️ ホストモード (Host)")
        self.tab_client = self.tabview.add("💻 クライアントモード (Client)")

        self.setup_host_tab()
        self.setup_client_tab()

    # ==================== ホストモードタブ構築 ====================
    def setup_host_tab(self):
        tab = self.tab_host

        info_frame = ctk.CTkFrame(tab, corner_radius=10)
        info_frame.pack(fill="x", padx=5, pady=(0, 5), anchor="n")
        ctk.CTkLabel(info_frame, text=f"🌐 ホスト接続情報: 自端末IP [{self.my_ipv4}] / ポート [{DEFAULT_PORT}]", font=("Helvetica", 11, "bold")).pack(anchor="w", padx=10, pady=8)

        ctrl_frame = ctk.CTkFrame(tab, corner_radius=10)
        ctrl_frame.pack(fill="x", padx=5, pady=5)

        ctk.CTkLabel(ctrl_frame, text="セッションマスターパスワード:", font=("Helvetica", 11, "bold")).pack(anchor="w", padx=10, pady=(5, 2))
        self.host_pass_entry = ctk.CTkEntry(ctrl_frame, show="*", height=30)
        self.host_pass_entry.pack(fill="x", padx=10, pady=(0, 8))
        self.host_pass_entry.insert(0, self.config_data.get("session_password", "AECP_SECRET_2026"))

        self.btn_host_toggle = ctk.CTkButton(ctrl_frame, text="🚀 TCPサーバー開設 (ホスト開始)", fg_color="#2b8252", hover_color="#216641", height=38, font=("Helvetica", 12, "bold"), command=self.toggle_host_session)
        self.btn_host_toggle.pack(fill="x", padx=10, pady=(0, 10))

        multi_frame = ctk.CTkFrame(tab, fg_color="transparent")
        multi_frame.pack(fill="both", expand=True, padx=0, pady=5)

        left_col = ctk.CTkFrame(multi_frame, fg_color="transparent")
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 5))

        right_col = ctk.CTkFrame(multi_frame, fg_color="transparent")
        right_col.pack(side="right", fill="both", expand=True, padx=(5, 0))

        term_frame = ctk.CTkFrame(left_col, corner_radius=10)
        term_frame.pack(fill="both", expand=True, pady=(0, 5))
        ctk.CTkLabel(term_frame, text="💻 ターミナルパネル (サーバーログ)", font=("Helvetica", 11, "bold")).pack(anchor="w", padx=10, pady=(5, 0))
        self.host_console = ctk.CTkTextbox(term_frame, height=120, font=("Consolas", 10))
        self.host_console.pack(fill="both", expand=True, padx=10, pady=5)
        self.host_console.insert("0.1", "[System] ホストターミナル準備完了...\n")

        chat_frame = ctk.CTkFrame(left_col, corner_radius=10)
        chat_frame.pack(fill="both", expand=True, pady=(5, 0))
        ctk.CTkLabel(chat_frame, text="💬 チャットパネル", font=("Helvetica", 11, "bold")).pack(anchor="w", padx=10, pady=(5, 0))
        self.host_chat_box = ctk.CTkTextbox(chat_frame, height=90, font=("Helvetica", 11))
        self.host_chat_box.pack(fill="both", expand=True, padx=10, pady=5)

        chat_input_row = ctk.CTkFrame(chat_frame, fg_color="transparent")
        chat_input_row.pack(fill="x", padx=10, pady=(0, 8))
        self.host_msg_entry = ctk.CTkEntry(chat_input_row, placeholder_text="チャットメッセージ送信...", height=30)
        self.host_msg_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.host_msg_entry.bind("<Return>", lambda e: self.send_host_message())
        ctk.CTkButton(chat_input_row, text="送信", width=70, height=30, fg_color="#4B5563", hover_color="#374151", command=self.send_host_message).pack(side="left")

        edit_frame = ctk.CTkFrame(right_col, corner_radius=10)
        edit_frame.pack(fill="both", expand=True, pady=(0, 5))
        ctk.CTkLabel(edit_frame, text="📝 編集パネル (共有ファイルエディター)", font=("Helvetica", 11, "bold")).pack(anchor="w", padx=10, pady=(5, 0))
        self.host_file_editor = ctk.CTkTextbox(edit_frame, height=150, font=("Consolas", 11))
        self.host_file_editor.pack(fill="both", expand=True, padx=10, pady=5)
        ctk.CTkButton(edit_frame, text="💾 ファイル変更を保存・同期", fg_color="#2b5282", hover_color="#214166", height=30, command=lambda: self.save_shared_file("Host")).pack(fill="x", padx=10, pady=(0, 8))

        cmd_frame = ctk.CTkFrame(right_col, corner_radius=10)
        cmd_frame.pack(fill="x", pady=(5, 0))
        ctk.CTkLabel(cmd_frame, text="⚡ コマンド入力パネル (helpでコマンド一覧)", font=("Helvetica", 11, "bold")).pack(anchor="w", padx=10, pady=(5, 0))
        
        cmd_input_row = ctk.CTkFrame(cmd_frame, fg_color="transparent")
        cmd_input_row.pack(fill="x", padx=10, pady=(0, 8))
        self.host_cmd_entry = ctk.CTkEntry(cmd_input_row, placeholder_text="コマンド入力 (例: help, cat file.txt ...)", height=30)
        self.host_cmd_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.host_cmd_entry.bind("<Return>", lambda e: self.send_host_command())
        ctk.CTkButton(cmd_input_row, text="実行", width=70, height=30, fg_color="#991B1B", hover_color="#7F1D1D", command=self.send_host_command).pack(side="left")

    # ==================== クライアントモードタブ構築 ====================
    def setup_client_tab(self):
        tab = self.tab_client

        ctrl_frame = ctk.CTkFrame(tab, corner_radius=10)
        ctrl_frame.pack(fill="x", padx=5, pady=5, anchor="n")

        ctk.CTkLabel(ctrl_frame, text="接続先ホストの IPv4 アドレス:", font=("Helvetica", 11, "bold")).pack(anchor="w", padx=10, pady=(5, 2))
        self.client_ip_entry = ctk.CTkEntry(ctrl_frame, height=30)
        self.client_ip_entry.pack(fill="x", padx=10, pady=(0, 5))
        self.client_ip_entry.insert(0, self.config_data.get("host_ip", "127.0.0.1"))

        ctk.CTkLabel(ctrl_frame, text="セッションマスターパスワード:", font=("Helvetica", 11, "bold")).pack(anchor="w", padx=10, pady=(2, 2))
        self.client_pass_entry = ctk.CTkEntry(ctrl_frame, show="*", height=30)
        self.client_pass_entry.pack(fill="x", padx=10, pady=(0, 8))
        self.client_pass_entry.insert(0, self.config_data.get("session_password", "AECP_SECRET_2026"))

        self.btn_client_toggle = ctk.CTkButton(ctrl_frame, text="🔗 TCPサーバーに接続 (ログイン)", fg_color="#2b8252", hover_color="#216641", height=38, font=("Helvetica", 12, "bold"), command=self.toggle_client_session)
        self.btn_client_toggle.pack(fill="x", padx=10, pady=(0, 10))

        multi_frame = ctk.CTkFrame(tab, fg_color="transparent")
        multi_frame.pack(fill="both", expand=True, padx=0, pady=5)

        left_col = ctk.CTkFrame(multi_frame, fg_color="transparent")
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 5))

        right_col = ctk.CTkFrame(multi_frame, fg_color="transparent")
        right_col.pack(side="right", fill="both", expand=True, padx=(5, 0))

        term_frame = ctk.CTkFrame(left_col, corner_radius=10)
        term_frame.pack(fill="both", expand=True, pady=(0, 5))
        ctk.CTkLabel(term_frame, text="💻 ターミナルパネル (同期ログ)", font=("Helvetica", 11, "bold")).pack(anchor="w", padx=10, pady=(5, 0))
        self.client_console = ctk.CTkTextbox(term_frame, height=120, font=("Consolas", 10))
        self.client_console.pack(fill="both", expand=True, padx=10, pady=5)
        self.client_console.insert("0.1", "[System] クライアントターミナル準備完了...\n")

        chat_frame = ctk.CTkFrame(left_col, corner_radius=10)
        chat_frame.pack(fill="both", expand=True, pady=(5, 0))
        ctk.CTkLabel(chat_frame, text="💬 チャットパネル", font=("Helvetica", 11, "bold")).pack(anchor="w", padx=10, pady=(5, 0))
        self.client_chat_box = ctk.CTkTextbox(chat_frame, height=90, font=("Helvetica", 11))
        self.client_chat_box.pack(fill="both", expand=True, padx=10, pady=5)

        chat_input_row = ctk.CTkFrame(chat_frame, fg_color="transparent")
        chat_input_row.pack(fill="x", padx=10, pady=(0, 8))
        self.client_msg_entry = ctk.CTkEntry(chat_input_row, placeholder_text="チャットメッセージ送信...", height=30)
        self.client_msg_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.client_msg_entry.bind("<Return>", lambda e: self.send_client_message())
        ctk.CTkButton(chat_input_row, text="送信", width=70, height=30, fg_color="#4B5563", hover_color="#374151", command=self.send_client_message).pack(side="left")

        edit_frame = ctk.CTkFrame(right_col, corner_radius=10)
        edit_frame.pack(fill="both", expand=True, pady=(0, 5))
        ctk.CTkLabel(edit_frame, text="📝 編集パネル (共有ファイルエディター)", font=("Helvetica", 11, "bold")).pack(anchor="w", padx=10, pady=(5, 0))
        self.client_file_editor = ctk.CTkTextbox(edit_frame, height=150, font=("Consolas", 11))
        self.client_file_editor.pack(fill="both", expand=True, padx=10, pady=5)
        ctk.CTkButton(edit_frame, text="💾 ファイル変更を保存・同期", fg_color="#2b5282", hover_color="#214166", height=30, command=lambda: self.save_shared_file("Client")).pack(fill="x", padx=10, pady=(0, 8))

        cmd_frame = ctk.CTkFrame(right_col, corner_radius=10)
        cmd_frame.pack(fill="x", pady=(5, 0))
        ctk.CTkLabel(cmd_frame, text="⚡ コマンド入力パネル (helpでコマンド一覧)", font=("Helvetica", 11, "bold")).pack(anchor="w", padx=10, pady=(5, 0))
        
        cmd_input_row = ctk.CTkFrame(cmd_frame, fg_color="transparent")
        cmd_input_row.pack(fill="x", padx=10, pady=(0, 8))
        self.client_cmd_entry = ctk.CTkEntry(cmd_input_row, placeholder_text="コマンド入力 (例: help, cat file.txt ...)", height=30)
        self.client_cmd_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.client_cmd_entry.bind("<Return>", lambda e: self.send_client_command())
        ctk.CTkButton(cmd_input_row, text="実行", width=70, height=30, fg_color="#991B1B", hover_color="#7F1D1D", command=self.send_client_command).pack(side="left")

    # ==================== TCPネットワーク通信システム ====================
    def broadcast_message(self, message_str, sender_socket=None):
        """ホストから全クライアント（および自分自身）へ暗号化パケットを送信"""
        self.network_logs.append(message_str)
        self.update_ui_logs(message_str, is_host=True)

        pwd = self.host_pass_entry.get()
        key = self.derive_key(pwd)
        payload = self.encrypt_data(message_str.encode('utf-8'), key)
        packet = len(payload).to_bytes(4, 'big') + payload

        # 全クライアントに送信
        dead_clients = []
        for client_sock in self.client_connections:
            if client_sock != sender_socket:
                try:
                    client_sock.sendall(packet)
                except Exception:
                    dead_clients.append(client_sock)
        for dead in dead_clients:
            if dead in self.client_connections:
                self.client_connections.remove(dead)

    def send_to_network(self, message_str, is_host=True):
        """メッセージやログをネットワーク経由で送信する"""
        if is_host:
            self.broadcast_message(message_str)
        else:
            if not self.is_client_connected or not self.client_socket:
                messagebox.showerror("エラー", "サーバーに接続されていません。")
                return
            try:
                pwd = self.client_pass_entry.get()
                key = self.derive_key(pwd)
                payload = self.encrypt_data(message_str.encode('utf-8'), key)
                packet = len(payload).to_bytes(4, 'big') + payload
                self.client_socket.sendall(packet)
            except Exception as e:
                self.client_console.insert("end", f"[ERROR] 送信失敗: {e}\n")
                self.client_console.see("end")

    def update_ui_logs(self, text_line, is_host=True):
        """UIのターミナルとチャットを更新"""
        for is_h in ([True, False] if is_host else [False]):
            console = self.host_console if is_h else self.client_console
            console.insert("end", text_line + "\n")
            console.see("end")

            chat_box = self.host_chat_box if is_h else self.client_chat_box
            if "[MSG]" in text_line or "AUTH" in text_line or "SERVER" in text_line:
                chat_box.insert("end", text_line + "\n")
                chat_box.see("end")

    def handle_command(self, cmd_text, is_host=True):
        parts = cmd_text.strip().split()
        if not parts:
            return
        cmd = parts[0].lower()

        name = "Host" if is_host else self.config_data.get("display_name", "User")
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        log_msg = f"[{timestamp}] [{name}] > {cmd_text}"
        self.send_to_network(log_msg, is_host)

        def log_sys(msg):
            # 修正箇所: strftime の閉じ括弧抜けを修正
            sys_line = f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [CMD_SYSTEM] {msg}"
            self.send_to_network(sys_line, is_host)

        try:
            workspace_dir = "./local_workspace"

            if cmd == "help":
                log_sys("=== AECP Command List ===")
                log_sys("  dir / ls : ワークスペース内のファイル一覧を表示")
                log_sys("  cat <ファイル名> : 指定したファイルの内容をターミナルに出力")
                log_sys("  disconnect : セッションを切断")
                log_sys("  open <ファイル名> : ワークスペース内のファイルを開く")
                log_sys("  close : 開いているファイルを閉じる")
                log_sys("  help : コマンドリストを表示")

            elif cmd in ("dir", "ls"):
                log_sys(f"--- Workspace Files ({workspace_dir}) ---")
                for f in os.listdir(workspace_dir):
                    log_sys(f"  {f}")

            elif cmd == "cat":
                if len(parts) >= 2:
                    filename = parts[1]
                    full_path = os.path.join(workspace_dir, filename)
                    if os.path.exists(full_path) and os.path.isfile(full_path):
                        with open(full_path, "r", encoding="utf-8") as f:
                            content = f.read()
                        log_sys(f"=== Cat: {filename} ===\n{content}")
                    else:
                        log_sys(f"ファイルが見つかりません: {filename}")
                else:
                    log_sys("構文エラー: cat <ファイル名>")

            elif cmd == "open":
                if len(parts) >= 2:
                    filename = parts[1]
                    full_path = os.path.join(workspace_dir, filename)
                    if os.path.exists(full_path) and os.path.isfile(full_path):
                        self.current_open_filepath = full_path
                        with open(full_path, "r", encoding="utf-8") as f:
                            content = f.read()
                        editor = self.host_file_editor if is_host else self.client_file_editor
                        editor.delete("0.0", "end")
                        editor.insert("0.0", content)
                        log_sys(f"ファイルを開きました: {filename}")
                    else:
                        log_sys(f"ファイルが見つかりません: {filename}")
                else:
                    log_sys("構文エラー: open <ファイル名>")

            elif cmd == "close":
                self.current_open_filepath = None
                editor = self.host_file_editor if is_host else self.client_file_editor
                editor.delete("0.0", "end")
                log_sys("エディターを閉じました。")

            elif cmd == "disconnect":
                if is_host:
                    self.toggle_host_session()
                else:
                    self.toggle_client_session()

        except Exception as e:
            log_sys(f"[ERROR] コマンド実行エラー: {e}")

    # ==================== ファイル保存ロジック ====================
    def save_shared_file(self, mode):
        is_h = (mode == "Host")
        if is_h and not self.is_host_active:
            messagebox.showwarning("警告", "ホストサーバーが開始されていません。")
            return
        if not is_h and not self.is_client_connected:
            messagebox.showwarning("警告", "サーバーに接続していません。")
            return

        editor = self.host_file_editor if is_h else self.client_file_editor
        content = editor.get("0.0", "end-1c")
        workspace_dir = "./local_workspace"

        target_file = self.current_open_filepath
        if not target_file:
            target_file = os.path.join(workspace_dir, "default_workspace.txt")
            self.current_open_filepath = target_file

        try:
            with open(target_file, "w", encoding="utf-8") as f:
                f.write(content)

            name = "Host" if is_h else self.config_data.get("display_name", "User")
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            line = f"[{timestamp}] [{name}] [FILE_SYNC]: Saved to ({os.path.basename(target_file)})."
            self.send_to_network(line, is_h)
            
            messagebox.showinfo("成功", f"ローカルワークスペースに保存しました:\n{target_file}")
        except Exception as e:
            messagebox.showerror("エラー", f"ファイルの保存に失敗しました: {e}")

    # ==================== TCP通信の開始・停止 ====================
    def toggle_host_session(self):
        if not self.is_host_active:
            pwd = self.host_pass_entry.get().strip()
            self.save_config("session_password", pwd)

            try:
                self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.server_socket.bind(('0.0.0.0', DEFAULT_PORT))
                self.server_socket.listen(5)
            except Exception as e:
                messagebox.showerror("エラー", f"TCPサーバーの起動に失敗しました (ポート使用中など):\n{e}")
                return

            self.is_host_active = True
            self.btn_host_toggle.configure(text="⏹ TCPサーバーを停止", fg_color="#a83232", hover_color="#802424")

            threading.Thread(target=self.host_accept_loop, daemon=True).start()
            self.host_console.insert("end", f"[Host] TCPサーバーをポート {DEFAULT_PORT} で開設しました。\n")
        else:
            self.is_host_active = False
            try:
                if self.server_socket:
                    self.server_socket.close()
            except Exception:
                pass
            for sock in self.client_connections:
                try:
                    sock.close()
                except Exception:
                    pass
            self.client_connections.clear()

            self.btn_host_toggle.configure(text="🚀 TCPサーバー開設 (ホスト開始)", fg_color="#2b8252", hover_color="#216641")
            self.host_console.insert("end", "[Host] TCPサーバーを停止しました。\n")

    def host_accept_loop(self):
        """ホストがクライアントからの接続を受け付けるループ"""
        while self.is_host_active:
            try:
                self.server_socket.settimeout(1.0)
                conn, addr = self.server_socket.accept()
                self.client_connections.append(conn)
                threading.Thread(target=self.host_client_handler, args=(conn, addr), daemon=True).start()
            except socket.timeout:
                continue
            except Exception:
                break

    def host_client_handler(self, conn, addr):
        """接続してきたクライアントからのデータを受信するハンドラー"""
        while self.is_host_active:
            try:
                length_bytes = conn.recv(4)
                if not length_bytes:
                    break
                length = int.from_bytes(length_bytes, 'big')
                data = bytearray()
                while len(data) < length:
                    packet = conn.recv(length - len(data))
                    if not packet:
                        break
                    data.extend(packet)

                pwd = self.host_pass_entry.get()
                key = self.derive_key(pwd)
                decrypted = self.decrypt_data(bytes(data), key).decode('utf-8')

                # 全クライアントおよびホストにブロードキャスト
                self.broadcast_message(decrypted, sender_socket=conn)
            except Exception:
                break
        if conn in self.client_connections:
            self.client_connections.remove(conn)
        try:
            conn.close()
        except Exception:
            pass

    def toggle_client_session(self):
        if not self.is_client_connected:
            host_ip = self.client_ip_entry.get().strip()
            pwd = self.client_pass_entry.get().strip()
            display_name = self.config_data.get("display_name", "User")

            if not host_ip:
                messagebox.showerror("エラー", "接続先ホストのIPv4アドレスを入力してください。")
                return

            try:
                self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.client_socket.connect((host_ip, DEFAULT_PORT))
            except Exception as e:
                messagebox.showerror("接続エラー", f"サーバーへの接続に失敗しました:\n{e}")
                return

            self.is_client_connected = True
            self.btn_client_toggle.configure(text="🔌 サーバーから切断", fg_color="#a83232", hover_color="#802424")

            # 接続通知送信
            try:
                login_line = f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{display_name}] AUTH: Connected to TCP server."
                key = self.derive_key(pwd)
                payload = self.encrypt_data(login_line.encode('utf-8'), key)
                packet = len(payload).to_bytes(4, 'big') + payload
                self.client_socket.sendall(packet)
            except Exception as e:
                messagebox.showerror("エラー", f"認証パケットの送信失敗: {e}")

            threading.Thread(target=self.client_receive_loop, daemon=True).start()
            self.client_console.insert("end", f"[Client] ホスト ({host_ip}) に接続しました。\n")
        else:
            self.is_client_connected = False
            try:
                if self.client_socket:
                    self.client_socket.close()
            except Exception:
                pass
            self.btn_client_toggle.configure(text="🔗 TCPサーバーに接続 (ログイン)", fg_color="#2b8252", hover_color="#216641")
            self.client_console.insert("end", "[Client] 切断しました。\n")

    def client_receive_loop(self):
        """クライアントがホストからデータを受信するループ"""
        while self.is_client_connected:
            try:
                length_bytes = self.client_socket.recv(4)
                if not length_bytes:
                    break
                length = int.from_bytes(length_bytes, 'big')
                data = bytearray()
                while len(data) < length:
                    packet = self.client_socket.recv(length - len(data))
                    if not packet:
                        break
                    data.extend(packet)

                pwd = self.client_pass_entry.get()
                key = self.derive_key(pwd)
                decrypted = self.decrypt_data(bytes(data), key).decode('utf-8')

                self.update_ui_logs(decrypted, is_host=False)
            except Exception:
                break

    def send_host_message(self):
        if not self.is_host_active: return
        msg = self.host_msg_entry.get().strip()
        if not msg: return
        line = f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [Host] [MSG]: {msg}"
        self.send_to_network(line, is_host=True)
        self.host_msg_entry.delete(0, "end")

    def send_host_command(self):
        cmd = self.host_cmd_entry.get().strip()
        if not cmd: return
        self.handle_command(cmd, is_host=True)
        self.host_cmd_entry.delete(0, "end")

    def send_client_message(self):
        if not self.is_client_connected: return
        msg = self.client_msg_entry.get().strip()
        if not msg: return
        name = self.config_data.get("display_name", "User")
        line = f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{name}] [MSG]: {msg}"
        self.send_to_network(line, is_host=False)
        self.client_msg_entry.delete(0, "end")

    def send_client_command(self):
        cmd = self.client_cmd_entry.get().strip()
        if not cmd: return
        self.handle_command(cmd, is_host=False)
        self.client_cmd_entry.delete(0, "end")

if __name__ == "__main__":
    app = AECPApp()
    app.mainloop()
