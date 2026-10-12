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
CURRENT_VERSION = "v1.3"

class AECPApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"AECP - Altimece Encrypt Control Protocol ({CURRENT_VERSION})")
        self.geometry("1100x900")
        self.resizable(True, True)

        # 設定の初期化と読み込み
        self.init_directories()
        self.config_data = self.load_config()

        # 自端末情報
        self.hostname = socket.gethostname()
        self.my_ipv4 = self.get_local_ipv4()
        
        # セッションフラグと現在開いているファイルパス
        self.is_host_active = False
        self.is_client_connected = False
        self.current_open_filepath = None

        # UI構築
        self.setup_menu()
        self.setup_ui()

    def init_directories(self):
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)

    def load_config(self):
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "shared_dir": "", 
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
        file_menu.add_command(label="共有フォルダを開く", command=self.menu_open_dir)
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
        path = self.config_data.get("shared_dir", "")
        if path and os.path.exists(path):
            os.startfile(path)
        else:
            messagebox.showwarning("警告", "有効な共有ディレクトリパスが設定されていません。")

    def menu_clear_logs(self):
        for console in [self.host_console, self.client_console]:
            console.delete("0.0", "end")
        for chat in [self.host_chat_box, self.client_chat_box]:
            chat.delete("0.0", "end")

    def menu_about(self):
        messagebox.showinfo("ソフトウェア情報", f"Altimece Encrypt Control Protocol (AECP)\nVersion {CURRENT_VERSION}\nCopyright 2026 Altice-Works Co., Ltd.")

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

        host_dir_frame = ctk.CTkFrame(tab, corner_radius=10)
        host_dir_frame.pack(fill="x", padx=5, pady=(0, 5), anchor="n")

        ctk.CTkLabel(host_dir_frame, text="📁 共有ディレクトリ操作パネル (ホスト)", font=("Helvetica", 11, "bold")).pack(anchor="w", padx=10, pady=(5, 2))
        
        row1 = ctk.CTkFrame(host_dir_frame, fg_color="transparent")
        row1.pack(fill="x", padx=10, pady=5)

        self.host_dir_entry = ctk.CTkEntry(row1, width=720, height=30, placeholder_text="共有ディレクトリのパスを指定...")
        self.host_dir_entry.pack(side="left", padx=(0, 8), expand=True, fill="x")
        self.host_dir_entry.insert(0, self.config_data.get("shared_dir", ""))

        def browse_host():
            path = filedialog.askdirectory()
            if path:
                self.host_dir_entry.delete(0, "end")
                self.host_dir_entry.insert(0, path)
                self.save_config("shared_dir", path)

        def create_host():
            path = self.host_dir_entry.get().strip()
            if not path:
                messagebox.showerror("エラー", "パスを入力してください。")
                return
            try:
                os.makedirs(path, exist_ok=True)
                self.save_config("shared_dir", path)
                messagebox.showinfo("成功", f"ディレクトリを作成しました:\n{path}")
            except Exception as e:
                messagebox.showerror("エラー", f"作成失敗: {e}")

        ctk.CTkButton(row1, text="参照", width=70, height=30, command=browse_host).pack(side="left", padx=(0, 5))
        ctk.CTkButton(row1, text="作成", width=70, height=30, fg_color="#2b5282", hover_color="#214166", command=create_host).pack(side="left")

        ctrl_frame = ctk.CTkFrame(tab, corner_radius=10)
        ctrl_frame.pack(fill="x", padx=5, pady=5)

        ctk.CTkLabel(ctrl_frame, text="セッションマスターパスワード:", font=("Helvetica", 11, "bold")).pack(anchor="w", padx=10, pady=(5, 2))
        self.host_pass_entry = ctk.CTkEntry(ctrl_frame, show="*", height=30)
        self.host_pass_entry.pack(fill="x", padx=10, pady=(0, 8))
        self.host_pass_entry.insert(0, self.config_data.get("session_password", "AECP_SECRET_2026"))

        self.btn_host_toggle = ctk.CTkButton(ctrl_frame, text="🚀 セッションルームを開設 (ホスト開始)", fg_color="#2b8252", hover_color="#216641", height=38, font=("Helvetica", 12, "bold"), command=self.toggle_host_session)
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

    # ==================== クライアントモードタブ構築 (ディレクトリ指定削除) ====================
    def setup_client_tab(self):
        tab = self.tab_client

        ctrl_frame = ctk.CTkFrame(tab, corner_radius=10)
        ctrl_frame.pack(fill="x", padx=5, pady=5, anchor="n")

        ctk.CTkLabel(ctrl_frame, text="接続方法の選択:", font=("Helvetica", 11, "bold")).pack(anchor="w", padx=10, pady=(5, 2))
        self.client_mode_seg = ctk.CTkSegmentedButton(ctrl_frame, values=["IPアドレス接続", "ユーザー名認証"], command=self.on_client_mode_change)
        self.client_mode_seg.pack(fill="x", padx=10, pady=(0, 5))
        saved_mode = self.config_data.get("connect_mode", "IPアドレス")
        self.client_mode_seg.set(saved_mode)

        self.client_dynamic_frame = ctk.CTkFrame(ctrl_frame, fg_color="transparent")
        self.client_dynamic_frame.pack(fill="x", padx=10, pady=2)
        self.build_client_dynamic_inputs(saved_mode)

        ctk.CTkLabel(ctrl_frame, text="セッションマスターパスワード:", font=("Helvetica", 11, "bold")).pack(anchor="w", padx=10, pady=(2, 2))
        self.client_pass_entry = ctk.CTkEntry(ctrl_frame, show="*", height=30)
        self.client_pass_entry.pack(fill="x", padx=10, pady=(0, 8))
        self.client_pass_entry.insert(0, self.config_data.get("session_password", "AECP_SECRET_2026"))

        self.btn_client_toggle = ctk.CTkButton(ctrl_frame, text="🔗 セッションに接続 (ログイン)", fg_color="#2b8252", hover_color="#216641", height=38, font=("Helvetica", 12, "bold"), command=self.toggle_client_session)
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

    def on_client_mode_change(self, mode):
        self.save_config("connect_mode", mode)
        self.build_client_dynamic_inputs(mode)

    def build_client_dynamic_inputs(self, mode):
        for widget in self.client_dynamic_frame.winfo_children():
            widget.destroy()

        if mode == "IPアドレス接続":
            ctk.CTkLabel(self.client_dynamic_frame, text="接続先ホストの IPv4 アドレス:", font=("Helvetica", 11, "bold")).pack(anchor="w", pady=(0, 2))
            self.client_ip_entry = ctk.CTkEntry(self.client_dynamic_frame, height=30)
            self.client_ip_entry.pack(fill="x")
            self.client_ip_entry.insert(0, self.config_data.get("host_ip", "127.0.0.1"))
        else:
            row = ctk.CTkFrame(self.client_dynamic_frame, fg_color="transparent")
            row.pack(fill="x")

            sub1 = ctk.CTkFrame(row, fg_color="transparent")
            sub1.pack(side="left", fill="x", expand=True, padx=(0, 10))
            ctk.CTkLabel(sub1, text="ユーザー名:", font=("Helvetica", 11, "bold")).pack(anchor="w", pady=(0, 2))
            self.client_user_entry = ctk.CTkEntry(sub1, height=30)
            self.client_user_entry.pack(fill="x")
            self.client_user_entry.insert(0, self.config_data.get("username", ""))

            sub2 = ctk.CTkFrame(row, fg_color="transparent")
            sub2.pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(sub2, text="接続パスワード:", font=("Helvetica", 11, "bold")).pack(anchor="w", pady=(0, 2))
            self.client_conn_pass_entry = ctk.CTkEntry(sub2, show="*", height=30)
            self.client_conn_pass_entry.pack(fill="x")
            self.client_conn_pass_entry.insert(0, self.config_data.get("connect_password", ""))

    # ==================== コマンド処理システム ====================
    def handle_command(self, cmd_text, is_host=True):
        parts = cmd_text.strip().split()
        if not parts:
            return
        cmd = parts[0].lower()

        name = "Host" if is_host else self.config_data.get("display_name", "User")
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        self.append_log(f"[{timestamp}] [{name}] > {cmd_text}", is_host)

        def log_sys(msg):
            sys_line = f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [CMD_SYSTEM] {msg}"
            self.append_log(sys_line, is_host)

        try:
            # クライアント側でディレクトリが指定されていない場合のチェック
            current_dir = self.host_dir_entry.get().strip() if is_host else self.config_data.get("shared_dir", "")

            if cmd == "help":
                log_sys("=== AECP Command List ===")
                log_sys("  dir / ls : ディレクトリツリーを表示")
                log_sys("  cat <ファイル名> : 指定したファイルの内容をターミナルに出力")
                log_sys("  disconnect : セッションを切断")
                log_sys("  ip-connect <ターゲットIPv4> <パスワード> : IPとパスワードで接続")
                log_sys("  username-connect <username> <パスワード> : ユーザー名とパスワードで接続")
                log_sys("  open <パス または ファイル名> : ファイルを開いてエディターに読み込む")
                log_sys("  close : 開いているファイルを閉じる")
                log_sys("  help : コマンドリストを表示")

            elif cmd in ("dir", "ls"):
                if not current_dir or not os.path.exists(current_dir):
                    log_sys(f"エラー: 有効な共有ディレクトリが設定されていません（ホスト側の設定をご確認ください）: {current_dir}")
                else:
                    log_sys(f"--- Directory Tree: {current_dir} ---")
                    for root, dirs, files in os.walk(current_dir):
                        level = root.replace(current_dir, "").count(os.sep)
                        indent = " " * 4 * level
                        log_sys(f"{indent}{os.path.basename(root)}/")
                        sub_indent = " " * 4 * (level + 1)
                        for f in files:
                            log_sys(f"{sub_indent}{f}")

            elif cmd == "cat":
                if len(parts) >= 2:
                    filepath = " ".join(parts[1:])
                    full_path = filepath if os.path.isabs(filepath) else os.path.join(current_dir, filepath)
                    if os.path.exists(full_path) and os.path.isfile(full_path):
                        with open(full_path, "r", encoding="utf-8") as f:
                            file_content = f.read()
                        log_sys(f"=== Cat: {full_path} ===\n{file_content}")
                    else:
                        log_sys(f"ファイルが見つかりません: {full_path}")
                else:
                    log_sys("構文エラー: cat <ファイル名>")

            elif cmd == "disconnect":
                if is_host:
                    if self.is_host_active:
                        self.toggle_host_session()
                        log_sys("ホストセッションを切断しました。")
                else:
                    if self.is_client_connected:
                        self.toggle_client_session()
                        log_sys("クライアントセッションを切断しました。")

            elif cmd == "ip-connect":
                if len(parts) >= 3:
                    target_ip = parts[1]
                    pwd = parts[2]
                    if not is_host:
                        self.client_mode_seg.set("IPアドレス接続")
                        self.build_client_dynamic_inputs("IPアドレス接続")
                        self.client_ip_entry.delete(0, "end")
                        self.client_ip_entry.insert(0, target_ip)
                        self.client_pass_entry.delete(0, "end")
                        self.client_pass_entry.insert(0, pwd)
                        if not self.is_client_connected:
                            self.toggle_client_session()
                        log_sys(f"IP: {target_ip} で接続処理を実行しました。")
                    else:
                        log_sys("ホストモードではクライアント接続コマンドを実行できません。")
                else:
                    log_sys("構文エラー: ip-connect <ターゲットIPv4> <パスワード>")

            elif cmd == "username-connect":
                if len(parts) >= 3:
                    username = parts[1]
                    pwd = parts[2]
                    if not is_host:
                        self.client_mode_seg.set("ユーザー名認証")
                        self.build_client_dynamic_inputs("ユーザー名認証")
                        self.client_user_entry.delete(0, "end")
                        self.client_user_entry.insert(0, username)
                        self.client_conn_pass_entry.delete(0, "end")
                        self.client_conn_pass_entry.insert(0, pwd)
                        self.client_pass_entry.delete(0, "end")
                        self.client_pass_entry.insert(0, pwd)
                        if not self.is_client_connected:
                            self.toggle_client_session()
                        log_sys(f"User: {username} で接続処理を実行しました。")
                    else:
                        log_sys("ホストモードではクライアント接続コマンドを実行できません。")
                else:
                    log_sys("構文エラー: username-connect <username> <パスワード>")

            elif cmd == "open":
                if len(parts) >= 2:
                    filepath = " ".join(parts[1:])
                    full_path = filepath if os.path.isabs(filepath) else os.path.join(current_dir, filepath)
                    if os.path.exists(full_path) and os.path.isfile(full_path):
                        self.current_open_filepath = full_path
                        with open(full_path, "r", encoding="utf-8") as f:
                            content = f.read()
                        editor = self.host_file_editor if is_host else self.client_file_editor
                        editor.delete("0.0", "end")
                        editor.insert("0.0", content)
                        log_sys(f"ファイルを開きました: {full_path}")
                    else:
                        log_sys(f"ファイルが見つかりません: {full_path}")
                else:
                    log_sys("構文エラー: open <フルファイルパス または ファイル名>")

            elif cmd == "close":
                self.current_open_filepath = None
                editor = self.host_file_editor if is_host else self.client_file_editor
                editor.delete("0.0", "end")
                log_sys("エディターを閉じました。")

            else:
                line = f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{name}] [CMD]: {cmd_text}"
                self.append_log(line, is_host)
                log_sys("コマンドをネットワークログに送信しました。")

        except Exception as e:
            log_sys(f"[ERROR] コマンド実行中にエラーが発生しました: {e}")

    # ==================== ファイル実ファイル保存ロジック ====================
    def save_shared_file(self, mode):
        is_h = (mode == "Host")
        if is_h and not self.is_host_active:
            messagebox.showwarning("警告", "ホストセッションが開始されていません。")
            return
        if not is_h and not self.is_client_connected:
            messagebox.showwarning("警告", "セッションに接続していません。")
            return

        editor = self.host_file_editor if is_h else self.client_file_editor
        content = editor.get("0.0", "end-1c")
        d = self.host_dir_entry.get().strip() if is_h else self.config_data.get("shared_dir", "")

        if not d or not os.path.exists(d):
            messagebox.showerror("エラー", "有効な共有ディレクトリが設定されていません。")
            return

        target_file = self.current_open_filepath
        if not target_file:
            target_file = os.path.join(d, "default_workspace.txt")
            self.current_open_filepath = target_file

        try:
            with open(target_file, "w", encoding="utf-8") as f:
                f.write(content)

            name = "Host" if is_h else self.config_data.get("display_name", "User")
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            line = f"[{timestamp}] [{name}] [FILE_SYNC]: Saved to real file ({os.path.basename(target_file)})."
            self.append_log(line, is_h)
            
            messagebox.showinfo("成功", f"実ファイルに保存しました:\n{target_file}")
        except Exception as e:
            messagebox.showerror("エラー", f"ファイルの保存に失敗しました: {e}")

    # ==================== 通信・同期ロジック ====================
    def get_target_file(self, is_host=True):
        if is_host:
            d = self.host_dir_entry.get().strip()
        else:
            d = self.config_data.get("shared_dir", "")
        return os.path.join(d, "aecp_server.enc") if d else ""

    def toggle_host_session(self):
        if not self.is_host_active:
            target = self.get_target_file(is_host=True)
            if not target or not os.path.exists(os.path.dirname(target)):
                messagebox.showerror("エラー", "有効な共有ディレクトリを指定してください。")
                return

            pwd = self.host_pass_entry.get()
            self.save_config("session_password", pwd)
            # ホスト側のディレクトリパスを config にも保存
            self.save_config("shared_dir", self.host_dir_entry.get().strip())

            self.is_host_active = True
            self.btn_host_toggle.configure(text="⏹ セッションルームを閉じる", fg_color="#a83232", hover_color="#802424")

            key = self.derive_key(pwd)
            init_log = f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [SERVER] HOST_STARTED: Room initialized.\n"
            try:
                enc = self.encrypt_data(init_log.encode('utf-8'), key)
                with open(target, "wb") as f:
                    f.write(enc)
            except Exception as e:
                messagebox.showerror("エラー", f"初期化失敗: {e}")
                self.is_host_active = False
                self.btn_host_toggle.configure(text="🚀 セッションルームを開設 (ホスト開始)", fg_color="#2b8252", hover_color="#216641")
                return

            threading.Thread(target=self.sync_loop, args=(True,), daemon=True).start()
            self.host_console.insert("end", "[Host] セッションを開設しました。\n")
        else:
            self.is_host_active = False
            self.btn_host_toggle.configure(text="🚀 セッションルームを開設 (ホスト開始)", fg_color="#2b8252", hover_color="#216641")
            self.host_console.insert("end", "[Host] セッションを閉じました。\n")

    def toggle_client_session(self):
        if not self.is_client_connected:
            target = self.get_target_file(is_host=False)
            if not target or not os.path.exists(os.path.dirname(target)):
                messagebox.showerror("エラー", "有効な共有ディレクトリが設定されていません（ホスト側の共有ディレクトリパスをご確認ください）。")
                return

            display_name = self.config_data.get("display_name", "User")
            pwd = self.client_pass_entry.get().strip()

            self.is_client_connected = True
            self.btn_client_toggle.configure(text="🔌 セッションから切断", fg_color="#a83232", hover_color="#802424")

            try:
                key = self.derive_key(pwd)
                with open(target, "rb") as f:
                    enc = f.read()
                existing = self.decrypt_data(enc, key).decode('utf-8')
                
                login_line = f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{display_name}] AUTH: Connected to session.\n"
                new_data = self.encrypt_data((existing + login_line).encode('utf-8'), key)
                with open(target, "wb") as f:
                    f.write(new_data)
            except Exception as e:
                messagebox.showerror("認証エラー", f"接続失敗（パスワード不一致等）: {e}")
                self.is_client_connected = False
                self.btn_client_toggle.configure(text="🔗 セッションに接続 (ログイン)", fg_color="#2b8252", hover_color="#216641")
                return

            threading.Thread(target=self.sync_loop, args=(False,), daemon=True).start()
            self.client_console.insert("end", "[Client] セッションに接続しました。\n")
        else:
            self.is_client_connected = False
            self.btn_client_toggle.configure(text="🔗 セッションに接続 (ログイン)", fg_color="#2b8252", hover_color="#216641")
            self.client_console.insert("end", "[Client] 切断しました。\n")

    def append_log(self, text_line, is_host=True):
        target = self.get_target_file(is_host)
        pwd = self.host_pass_entry.get() if is_host else self.client_pass_entry.get()
        key = self.derive_key(pwd)

        try:
            with open(target, "rb") as f:
                enc = f.read()
            existing = self.decrypt_data(enc, key).decode('utf-8')
            
            new_content = existing + text_line + "\n"
            new_enc = self.encrypt_data(new_content.encode('utf-8'), key)
            with open(target, "wb") as f:
                f.write(new_enc)
        except Exception as e:
            messagebox.showerror("エラー", f"送信失敗: {e}")

    def send_host_message(self):
        if not self.is_host_active: return
        msg = self.host_msg_entry.get().strip()
        if not msg: return
        line = f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [Host] [MSG]: {msg}"
        self.append_log(line, True)
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
        self.append_log(line, False)
        self.client_msg_entry.delete(0, "end")

    def send_client_command(self):
        cmd = self.client_cmd_entry.get().strip()
        if not cmd: return
        self.handle_command(cmd, is_host=False)
        self.client_cmd_entry.delete(0, "end")

    def sync_loop(self, is_host=True):
        while (is_host and self.is_host_active) or (not is_host and self.is_client_connected):
            try:
                target = self.get_target_file(is_host)
                pwd = self.host_pass_entry.get() if is_host else self.client_pass_entry.get()
                key = self.derive_key(pwd)

                if target and os.path.exists(target):
                    with open(target, "rb") as f:
                        enc = f.read()
                    text = self.decrypt_data(enc, key).decode('utf-8')

                    console = self.host_console if is_host else self.client_console
                    curr_term = console.get("0.0", "end-1c")
                    if text.strip() != curr_term.strip():
                        console.delete("0.0", "end")
                        console.insert("0.0", text)
                        console.see("end")

                    chat_box = self.host_chat_box if is_host else self.client_chat_box
                    chat_lines = [line for line in text.splitlines() if "[MSG]" in line or "AUTH" in line or "HOST_STARTED" in line]
                    chat_text = "\n".join(chat_lines)
                    curr_chat = chat_box.get("0.0", "end-1c")
                    if chat_text.strip() != curr_chat.strip():
                        chat_box.delete("0.0", "end")
                        chat_box.insert("0.0", chat_text)
                        chat_box.see("end")
            except Exception:
                pass
            time.sleep(1.5)

if __name__ == "__main__":
    app = AECPApp()
    app.mainloop()
