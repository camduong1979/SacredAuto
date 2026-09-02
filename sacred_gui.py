"""
Sacred Bot — Config Editor GUI
Tao moi 2026-09-01 | Dung tkinter thuan (built-in, khong can pip them)
Muc dich: Doc / Chinh sua / Luu sacred_config.json mot cach truc quan
Khong lien ket runtime vao bot — chi doc/ghi file JSON
"""
# --- OLD CODE (REPLACED) ---
# import tkinter as tk
# from tkinter import ttk, messagebox
# import json
# import os
# import copy
# ---------------------------
import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import copy
import threading
import time
import keyboard
import pydirectinput
try:
    from sacred_bot import SacredBotMemory
except Exception as _e:
    SacredBotMemory = None

# Duong dan config tuong doi voi file nay
_HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(_HERE, "sacred_config.json")


class SacredConfigGUI:
    """GUI chinh sua sacred_config.json."""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Sacred Bot — Config Editor")
        # --- OLD CODE (REPLACED) ---
        # self.root.geometry("660x540")
        # self.root.resizable(True, True)
        #
        # self.config: dict = {}
        # self._vars: dict = {}
        #
        # self._build_toolbar()
        # self._build_notebook()
        # self._build_statusbar()
        # self.load_config()
        # ---------------------------
        self.root.geometry("680x620")
        self.root.resizable(True, True)

        self.config: dict = {}
        self._vars: dict = {}

        # Bot Runtime Controller
        self.bot = None
        self.bot_thread = None
        self.quest_thread = None
        self.quest_running = False
        self._is_closing = False

        self._build_toolbar()
        self._build_hud_panel()
        self._build_notebook()
        self._build_statusbar()
        self.load_config()

        # Khoi chay lang nghe Quest va Live HUD polling
        self._start_quest_listener()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._poll_hud()

    # ------------------------------------------------------------------
    # BUILD UI
    # ------------------------------------------------------------------
    def _build_toolbar(self):
        bar = tk.Frame(self.root, bd=1, relief=tk.RAISED)
        bar.pack(fill=tk.X, padx=4, pady=2)
        tk.Button(bar, text="Load Config", width=11,
                  command=self.load_config).pack(side=tk.LEFT, padx=2, pady=2)
        tk.Button(bar, text="Save Config", width=11,
                  command=self.save_config,
                  bg="#4CAF50", fg="white",
                  font=("TkDefaultFont", 9, "bold")).pack(side=tk.LEFT, padx=2, pady=2)

        # Main Bot Start/Stop
        self.btn_start = tk.Button(bar, text="▶ START BOT", width=12,
                                   command=self.start_bot,
                                   bg="#007ACC", fg="white",
                                   font=("TkDefaultFont", 9, "bold"))
        self.btn_start.pack(side=tk.LEFT, padx=(8, 2), pady=2)

        self.btn_stop = tk.Button(bar, text="⏹ STOP BOT", width=12,
                                  command=self.stop_bot,
                                  bg="#F44336", fg="white",
                                  font=("TkDefaultFont", 9, "bold"))
        self.btn_stop.pack(side=tk.LEFT, padx=2, pady=2)

        # Farm Quest Start/Stop (Doc lap voi Bot)
        self.btn_start_quest = tk.Button(bar, text="⚡ START QUEST", width=13,
                                         command=self.start_quest,
                                         bg="#FF9800", fg="white",
                                         font=("TkDefaultFont", 9, "bold"))
        self.btn_start_quest.pack(side=tk.LEFT, padx=(8, 2), pady=2)

        self.btn_stop_quest = tk.Button(bar, text="⏹ STOP QUEST", width=12,
                                        command=self.stop_quest,
                                        bg="#757575", fg="white",
                                        font=("TkDefaultFont", 9, "bold"))
        self.btn_stop_quest.pack(side=tk.LEFT, padx=2, pady=2)

    def _build_hud_panel(self):
        """Khu vuc Live HUD hien thi trang thai Bot thoi gian thuc tren GUI."""
        hud_frame = tk.LabelFrame(self.root, text=" Live HUD Status ", font=("TkDefaultFont", 9, "bold"), padx=6, pady=4)
        hud_frame.pack(fill=tk.X, padx=6, pady=3)

        # --- HÀNG 1: Trạng thái tổng quan (Game, Bot, Quest) ---
        row1_frame = tk.Frame(hud_frame)
        row1_frame.pack(fill=tk.X, pady=2)

        self.lbl_game_status = tk.Label(row1_frame, text="Game: NOT CONNECTED", font=("TkDefaultFont", 9, "bold"),
                                        bg="#E0E0E0", fg="#555", width=20, relief=tk.RIDGE, bd=2)
        self.lbl_game_status.pack(side=tk.LEFT, padx=3, pady=2)

        self.lbl_bot_status = tk.Label(row1_frame, text="Bot: STOPPED", font=("TkDefaultFont", 9, "bold"),
                                       bg="#FFCDD2", fg="#C62828", width=13, relief=tk.RIDGE, bd=2)
        self.lbl_bot_status.pack(side=tk.LEFT, padx=3, pady=2)

        self.lbl_quest_status = tk.Label(row1_frame, text="Quest: OFF", font=("TkDefaultFont", 9, "bold"),
                                         bg="#EEEEEE", fg="#757575", width=15, relief=tk.RIDGE, bd=2)
        self.lbl_quest_status.pack(side=tk.LEFT, padx=3, pady=2)

        # --- HÀNG 2: Thông số chi tiết (HP, Target, Event) ---
        row2_frame = tk.Frame(hud_frame)
        row2_frame.pack(fill=tk.X, pady=2)

        self.lbl_hp_status = tk.Label(row2_frame, text="HP: --%", font=("TkDefaultFont", 9),
                                      width=11, relief=tk.SUNKEN, bd=1, anchor=tk.W, padx=3)
        self.lbl_hp_status.pack(side=tk.LEFT, padx=3, pady=2)

        self.lbl_target_status = tk.Label(row2_frame, text="Target: None", font=("TkDefaultFont", 9),
                                          width=16, relief=tk.SUNKEN, bd=1, anchor=tk.W, padx=3)
        self.lbl_target_status.pack(side=tk.LEFT, padx=3, pady=2)

        self.lbl_event_status = tk.Label(row2_frame, text="Event: Cho khoi chay", font=("TkDefaultFont", 9),
                                         relief=tk.SUNKEN, bd=1, anchor=tk.W, padx=3)
        self.lbl_event_status.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3, pady=2)

    def _build_notebook(self):
        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill=tk.BOTH, expand=True, padx=6, pady=4)
        self._tab_global()
        self._tab_potion()
        self._tab_combat()
        self._tab_buff()
        self._tab_quest()
        self._tab_hotkeys()
        self._tab_ai()

    def _build_statusbar(self):
        self.status_var = tk.StringVar(value="San sang")
        tk.Label(self.root, textvariable=self.status_var,
                 bd=1, relief=tk.SUNKEN, anchor=tk.W,
                 fg="#333").pack(fill=tk.X, side=tk.BOTTOM, padx=4, pady=2)

    # ------------------------------------------------------------------
    # TAB: FARM QUEST
    # ------------------------------------------------------------------
    def _tab_quest(self):
        f = ttk.Frame(self.nb)
        self.nb.add(f, text="  Farm Quest  ")
        f.columnconfigure(0, weight=1)

        v_en = tk.BooleanVar()
        tk.Checkbutton(f, text="Bat tinh nang Farm Quest Macro", variable=v_en,
                       font=("TkDefaultFont", 10, "bold")).grid(
            row=0, column=0, columnspan=3, sticky=tk.W, padx=12, pady=8)
        self._vars["quest.enabled"] = v_en

        lf = ttk.LabelFrame(f, text="Cấu hình phím & Delay Macro")
        lf.grid(row=1, column=0, columnspan=3, sticky="ew", padx=10, pady=4)

        tk.Label(lf, text="Phím kích hoạt (Trigger Key):").grid(
            row=0, column=0, sticky=tk.W, padx=10, pady=5)
        v_k = tk.StringVar(value="n")
        tk.Entry(lf, textvariable=v_k, width=8).grid(
            row=0, column=1, sticky=tk.W, padx=6)
        self._vars["quest.trigger_key"] = v_k

        tk.Label(lf, text="Delay sau Ctrl+X (s):").grid(
            row=1, column=0, sticky=tk.W, padx=10, pady=5)
        v_d1 = tk.StringVar(value="0.1")
        tk.Spinbox(lf, from_=0.01, to=2.0, increment=0.05,
                   textvariable=v_d1, width=8).grid(
            row=1, column=1, sticky=tk.W, padx=6)
        self._vars["quest.delay_step1"] = v_d1

        tk.Label(lf, text="Delay sau Click Trái (s):").grid(
            row=2, column=0, sticky=tk.W, padx=10, pady=5)
        v_d2 = tk.StringVar(value="0.1")
        tk.Spinbox(lf, from_=0.01, to=2.0, increment=0.05,
                   textvariable=v_d2, width=8).grid(
            row=2, column=1, sticky=tk.W, padx=6)
        self._vars["quest.delay_step2"] = v_d2

        tk.Label(lf, text="Delay sau Enter / Chu kỳ lặp (s):").grid(
            row=3, column=0, sticky=tk.W, padx=10, pady=5)
        v_d3 = tk.StringVar(value="0.4")
        tk.Spinbox(lf, from_=0.05, to=5.0, increment=0.05,
                   textvariable=v_d3, width=8).grid(
            row=3, column=1, sticky=tk.W, padx=6)
        self._vars["quest.delay_step3"] = v_d3

        tk.Label(f,
                 text="* Hướng dẫn Farm Quest:\n"
                      "  Giữ hoặc nhấn phím kích hoạt trong game để tự động thực hiện:\n"
                      "    1. Nhấn Ctrl+X (mở hội thoại NPC / quest)\n"
                      "    2. Click chuột trái vào vị trí chỉ định\n"
                      "    3. Nhấn Enter để hoàn tất hoặc nhận thưởng",
                 fg="#444", justify=tk.LEFT).grid(row=2, column=0, columnspan=3,
                                                  sticky=tk.W, padx=12, pady=10)

    # ------------------------------------------------------------------
    # TAB: GLOBAL
    # ------------------------------------------------------------------
    def _tab_global(self):
        f = ttk.Frame(self.nb)
        self.nb.add(f, text="  Global  ")
        tk.Label(f, text="Toggle Key (bat / tat bot):").grid(
            row=0, column=0, sticky=tk.W, padx=12, pady=10)
        v = tk.StringVar()
        tk.Entry(f, textvariable=v, width=10).grid(
            row=0, column=1, sticky=tk.W, padx=6)
        self._vars["global.toggle_key"] = v
        tk.Label(f, text="(Nhan phim nay trong game de bat/tat bot)",
                 fg="gray").grid(row=1, column=0, columnspan=3,
                                 sticky=tk.W, padx=12)

    # ------------------------------------------------------------------
    # TAB: POTION
    # ------------------------------------------------------------------
    def _tab_potion(self):
        f = ttk.Frame(self.nb)
        self.nb.add(f, text="  Potion  ")

        v_en = tk.BooleanVar()
        tk.Checkbutton(f, text="Bat Auto Potion", variable=v_en,
                       font=("TkDefaultFont", 10, "bold")).grid(
            row=0, column=0, columnspan=2, sticky=tk.W, padx=12, pady=8)
        self._vars["potion.enabled"] = v_en

        tk.Label(f, text="Nguong HP uong mau (%):").grid(
            row=1, column=0, sticky=tk.W, padx=12, pady=5)
        v_th = tk.StringVar()
        tk.Spinbox(f, from_=1, to=99, increment=1,
                   textvariable=v_th, width=8).grid(
            row=1, column=1, sticky=tk.W, padx=6)
        self._vars["potion.threshold_percent"] = v_th

        tk.Label(f, text="Phim uong mau (key):").grid(
            row=2, column=0, sticky=tk.W, padx=12, pady=5)
        v_k = tk.StringVar()
        tk.Entry(f, textvariable=v_k, width=10).grid(
            row=2, column=1, sticky=tk.W, padx=6)
        self._vars["potion.key"] = v_k

        tk.Label(f, text="(Cooldown cung 0.8s — xem BotEngine.py action_worker)",
                 fg="gray").grid(row=3, column=0, columnspan=3,
                                 sticky=tk.W, padx=12, pady=4)

    # ------------------------------------------------------------------
    # TAB: COMBAT
    # ------------------------------------------------------------------
    def _tab_combat(self):
        f = ttk.Frame(self.nb)
        self.nb.add(f, text="  Combat  ")
        f.columnconfigure(0, weight=1)

        # AUTO ATTACK CHECKBOX
        lf_aa = ttk.LabelFrame(f, text="Auto Attack")
        lf_aa.grid(row=0, column=0, columnspan=4,
                   sticky="ew", padx=10, pady=10)
        lf_aa.columnconfigure(0, weight=1)

        v_aa = tk.BooleanVar()
        tk.Checkbutton(
            lf_aa,
            text="Tu dong click chuot trai khi phat hien target (hover quai)",
            variable=v_aa,
            font=("TkDefaultFont", 10, "bold")
        ).grid(row=0, column=0, columnspan=2, sticky=tk.W, padx=8, pady=6)
        self._vars["combat.auto_attack"] = v_aa

        tk.Label(lf_aa,
                 text="Tat -> bot chi nhan dien, KHONG click chuot. Nguoi choi tu danh bang phim Z.",
                 fg="gray").grid(row=1, column=0, columnspan=2,
                                 sticky=tk.W, padx=8, pady=(0, 6))

        # COMBAT RADAR
        lf_r = ttk.LabelFrame(f, text="CombatRadar — Pixel Scan")
        lf_r.grid(row=1, column=0, columnspan=4,
                  sticky="ew", padx=10, pady=4)

        radar_fields = [
            ("Radar Center X (px):", "combat.radar_center_x"),
            ("Radar Center Y (px):", "combat.radar_center_y"),
            ("Scan Width (px):",     "combat.scan_width"),
            ("Scan Height (px):",    "combat.scan_height"),
        ]
        for row_idx, (label, key) in enumerate(radar_fields):
            tk.Label(lf_r, text=label).grid(
                row=row_idx, column=0, sticky=tk.W, padx=10, pady=4)
            v = tk.StringVar()
            tk.Entry(lf_r, textvariable=v, width=8).grid(
                row=row_idx, column=1, sticky=tk.W, padx=6)
            self._vars[key] = v

    # ------------------------------------------------------------------
    # TAB: BUFF SYSTEM
    # ------------------------------------------------------------------
    def _tab_buff(self):
        f = ttk.Frame(self.nb)
        self.nb.add(f, text="  Auto Buff  ")
        f.columnconfigure(0, weight=1)

        v_en = tk.BooleanVar()
        tk.Checkbutton(f, text="Bat toan bo Auto Buff System",
                       variable=v_en,
                       font=("TkDefaultFont", 10, "bold")).grid(
            row=0, column=0, columnspan=4, sticky=tk.W, padx=12, pady=6)
        self._vars["buff.enabled"] = v_en

        buff_labels = {
            "co_buff": "Buff Combo  (co_buff)",
            "ma_buff": "Buff Magic  (ma_buff)",
            "ca_buff": "Buff CA     (ca_buff)",
        }
        self._buff_ids = ["co_buff", "ma_buff", "ca_buff"]

        for i, bid in enumerate(self._buff_ids):
            lf = ttk.LabelFrame(f, text=buff_labels[bid])
            lf.grid(row=i+1, column=0, columnspan=4,
                    sticky="ew", padx=10, pady=4)

            # --- Row 0: Enabled | Interval | Sentinel X | Y ---
            v_e = tk.BooleanVar()
            tk.Checkbutton(lf, text="Bat", variable=v_e).grid(
                row=0, column=0, padx=8, pady=(4, 1), sticky=tk.W)
            self._vars[f"buff.{bid}.enabled"] = v_e

            tk.Label(lf, text="Interval (s):").grid(
                row=0, column=1, padx=4, sticky=tk.W)
            v_i = tk.StringVar()
            tk.Spinbox(lf, from_=5, to=600, textvariable=v_i,
                       width=6).grid(row=0, column=2, padx=4)
            self._vars[f"buff.{bid}.interval"] = v_i

            tk.Label(lf, text="Sentinel X:").grid(
                row=0, column=3, padx=6, sticky=tk.W)
            v_sx = tk.StringVar()
            tk.Entry(lf, textvariable=v_sx, width=6).grid(
                row=0, column=4, padx=4)
            self._vars[f"buff.{bid}.sentinel_x"] = v_sx

            tk.Label(lf, text="Y:").grid(
                row=0, column=5, padx=2, sticky=tk.W)
            v_sy = tk.StringVar()
            tk.Entry(lf, textvariable=v_sy, width=6).grid(
                row=0, column=6, padx=4)
            self._vars[f"buff.{bid}.sentinel_y"] = v_sy

            # --- OLD CODE (REPLACED) ---
            # tk.Label(lf, text="Key").grid(
            #     row=0, column=7, padx=2, sticky=tk.W)
            # v_ke = tk.StringVar()
            # tk.Entry(lf, textvariable=v_sy, width=6).grid(
            #     row=0, column=8, padx=4)
            # self._vars[f"buff.{bid}.sequence_keys"] = v_ke
            # ---------------------------
            tk.Label(lf, text="Key:").grid(
                row=0, column=7, padx=2, sticky=tk.W)
            v_k = tk.StringVar()
            tk.Entry(lf, textvariable=v_k, width=6).grid(
                row=0, column=8, padx=4)
            self._vars[f"buff.{bid}.first_key"] = v_k

            # --- Row 1: Only In Combat | Sentinel Enabled ---
            v_oic = tk.BooleanVar()
            tk.Checkbutton(lf, text="Only In Combat", variable=v_oic).grid(
                row=1, column=0, columnspan=2, padx=8, pady=(1, 4), sticky=tk.W)
            self._vars[f"buff.{bid}.only_in_combat"] = v_oic

            v_se = tk.BooleanVar()
            tk.Checkbutton(lf, text="Sentinel Enabled", variable=v_se).grid(
                row=1, column=2, columnspan=3, padx=4, pady=(1, 4), sticky=tk.W)
            self._vars[f"buff.{bid}.sentinel_enabled"] = v_se

        tk.Label(f,
                 text="(Chinh sua sequence / mode -> edit truc tiep sacred_config.json)",
                 fg="gray").grid(row=len(self._buff_ids)+1, column=0,
                                 columnspan=4, sticky=tk.W, padx=12, pady=4)


    # ------------------------------------------------------------------
    # TAB: HOTKEYS (read-only)
    # ------------------------------------------------------------------
    def _tab_hotkeys(self):
        f = ttk.Frame(self.nb)
        self.nb.add(f, text="  Hotkeys  ")
        tk.Label(f,
                 text="Danh sach Combo (Chi xem — chinh sua trong sacred_config.json):").pack(
            anchor=tk.W, padx=10, pady=6)

        cols = ("name", "trigger_key")
        tree = ttk.Treeview(f, columns=cols, show="headings", height=10)
        tree.heading("name", text="Ten Combo")
        tree.heading("trigger_key", text="Phim kich hoat")
        tree.column("name", width=250)
        tree.column("trigger_key", width=130, anchor=tk.CENTER)

        sb = ttk.Scrollbar(f, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True,
                  padx=(10, 0), pady=4)
        sb.pack(side=tk.LEFT, fill=tk.Y, pady=4, padx=(0, 10))
        self._combo_tree = tree

    # ------------------------------------------------------------------
    # TAB: AI SYSTEM
    # ------------------------------------------------------------------
    def _tab_ai(self):
        f = ttk.Frame(self.nb)
        self.nb.add(f, text="  AI (YOLO)  ")

        v_en = tk.BooleanVar()
        tk.Checkbutton(f, text="Bat AI Module (YOLOv8 + CUDA)",
                       variable=v_en,
                       font=("TkDefaultFont", 10, "bold")).grid(
            row=0, column=0, columnspan=2, sticky=tk.W, padx=12, pady=8)
        self._vars["ai.enabled"] = v_en

        ai_fields = [
            ("Center X (px):",    "ai.center_x",   1),
            ("Center Y (px):",    "ai.center_y",   2),
            ("Scan Size (px):",   "ai.scan_size",  3),
            ("Confidence:",       "ai.conf",       4),
            ("Safe Box W (px):",  "ai.safe_box_w", 5),
            ("Safe Box H (px):",  "ai.safe_box_h", 6),
        ]
        for label, key, row in ai_fields:
            tk.Label(f, text=label).grid(
                row=row, column=0, sticky=tk.W, padx=12, pady=4)
            v = tk.StringVar()
            tk.Entry(f, textvariable=v, width=10).grid(
                row=row, column=1, sticky=tk.W, padx=6)
            self._vars[key] = v

        tk.Label(f,
                 text="(AI chi active trong Sacred_yolo.py — khong dung trong sacred_mele_memory.py)",
                 fg="gray").grid(row=7, column=0, columnspan=3,
                                 sticky=tk.W, padx=12, pady=6)

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------
    def _set(self, key: str, value):
        var = self._vars.get(key)
        if var is None:
            return
        try:
            if isinstance(var, tk.BooleanVar):
                var.set(bool(value))
            else:
                var.set(str(value))
        except Exception:
            pass

    def _get_str(self, key: str, default: str = "") -> str:
        var = self._vars.get(key)
        return var.get() if var else default

    def _get_bool(self, key: str, default: bool = False) -> bool:
        var = self._vars.get(key)
        return var.get() if isinstance(var, tk.BooleanVar) else default

    def _get_int(self, key: str, default: int = 0) -> int:
        raw = self._get_str(key, str(default))
        try:
            return int(raw)
        except ValueError:
            raise ValueError(f"'{key}' phai la so nguyen (nhan: '{raw}')")

    def _get_float(self, key: str, default: float = 0.0) -> float:
        raw = self._get_str(key, str(default))
        try:
            return float(raw)
        except ValueError:
            raise ValueError(f"'{key}' phai la so thuc (nhan: '{raw}')")

    # ------------------------------------------------------------------
    # LOAD CONFIG
    # ------------------------------------------------------------------
    def load_config(self):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as fp:
                self.config = json.load(fp)
            self._fill_widgets()
            self.status_var.set(f"Da load: {CONFIG_PATH}")
        except FileNotFoundError:
            messagebox.showerror("Loi", f"Khong tim thay file:\n{CONFIG_PATH}")
            self.status_var.set("Khong tim thay sacred_config.json")
        except Exception as e:
            messagebox.showerror("Loi Load", str(e))
            self.status_var.set(f"Loi load: {e}")

    def _fill_widgets(self):
        cfg = self.config

        # Global
        g = cfg.get("global", {})
        self._set("global.toggle_key", g.get("toggle_key", "d"))

        # Potion
        pot = cfg.get("potion_system", {})
        self._set("potion.enabled",          pot.get("enabled", True))
        self._set("potion.threshold_percent", pot.get("threshold_percent", 30))
        self._set("potion.key",              pot.get("key", "space"))

        # Combat
        com = cfg.get("combat_system", {})
        self._set("combat.auto_attack",    com.get("auto_attack", True))
        self._set("combat.radar_center_x", com.get("radar_center_x", 947))
        self._set("combat.radar_center_y", com.get("radar_center_y", 790))
        self._set("combat.scan_width",     com.get("scan_width", 20))
        self._set("combat.scan_height",    com.get("scan_height", 3))

        # Buff
        buff_sys = cfg.get("auto_buff_system", {})
        self._set("buff.enabled", buff_sys.get("enabled", False))
        for buff in buff_sys.get("buffs", []):
            bid = buff.get("id", "")
            if bid:
                self._set(f"buff.{bid}.enabled",          buff.get("enabled", False))
                self._set(f"buff.{bid}.interval",         buff.get("interval", 30))
                self._set(f"buff.{bid}.sentinel_x",       buff.get("sentinel_x", 0))
                self._set(f"buff.{bid}.sentinel_y",       buff.get("sentinel_y", 0))
                self._set(f"buff.{bid}.only_in_combat",   buff.get("only_in_combat", True))
                self._set(f"buff.{bid}.sentinel_enabled", buff.get("sentinel_enabled", False))
                # --- OLD CODE (REPLACED) ---
                # (chua load first key sequence)
                # ---------------------------
                seq = buff.get("sequence", [])
                first_key = seq[0].get("key", "") if seq and isinstance(seq, list) and len(seq) > 0 and isinstance(seq[0], dict) else ""
                self._set(f"buff.{bid}.first_key", first_key)

        # --- OLD CODE (REPLACED: chua load quest_system) ---
        # --------------------------------------------------
        # Quest System
        qst = cfg.get("quest_system", {})
        self._set("quest.enabled",     qst.get("enabled", True))
        self._set("quest.trigger_key", qst.get("trigger_key", "n"))
        self._set("quest.delay_step1", qst.get("delay_step1", 0.1))
        self._set("quest.delay_step2", qst.get("delay_step2", 0.1))
        self._set("quest.delay_step3", qst.get("delay_step3", 0.4))

        # Hotkeys treeview
        for row in self._combo_tree.get_children():
            self._combo_tree.delete(row)
        for combo in cfg.get("hotkey_system", {}).get("combos", []):
            self._combo_tree.insert("", tk.END, values=(
                combo.get("name", ""),
                combo.get("trigger_key", ""),
            ))

        # AI
        ai = cfg.get("ai_system", {})
        self._set("ai.enabled",    ai.get("enabled", True))
        self._set("ai.center_x",   ai.get("center_x", 958))
        self._set("ai.center_y",   ai.get("center_y", 510))
        self._set("ai.scan_size",  ai.get("scan_size", 600))
        self._set("ai.conf",       ai.get("conf", 0.45))
        self._set("ai.safe_box_w", ai.get("safe_box_w", 50))
        self._set("ai.safe_box_h", ai.get("safe_box_h", 120))

    # ------------------------------------------------------------------
    # SAVE CONFIG
    # ------------------------------------------------------------------
    def save_config(self):
        try:
            cfg = copy.deepcopy(self.config)

            # Global
            cfg.setdefault("global", {})["toggle_key"] = self._get_str("global.toggle_key", "d")

            # Potion
            cfg.setdefault("potion_system", {}).update({
                "enabled":           self._get_bool("potion.enabled", True),
                "threshold_percent": self._get_int("potion.threshold_percent", 30),
                "key":               self._get_str("potion.key", "space"),
            })

            # Combat
            cfg.setdefault("combat_system", {}).update({
                "auto_attack":    self._get_bool("combat.auto_attack", True),
                "radar_center_x": self._get_int("combat.radar_center_x", 947),
                "radar_center_y": self._get_int("combat.radar_center_y", 790),
                "scan_width":     self._get_int("combat.scan_width", 20),
                "scan_height":    self._get_int("combat.scan_height", 3),
            })

            # Buff
            cfg.setdefault("auto_buff_system", {})["enabled"] = self._get_bool("buff.enabled", False)
            for buff in cfg.get("auto_buff_system", {}).get("buffs", []):
                bid = buff.get("id", "")
                if bid:
                    buff["enabled"]          = self._get_bool(f"buff.{bid}.enabled", False)
                    buff["interval"]         = self._get_int(f"buff.{bid}.interval", 30)
                    buff["sentinel_x"]       = self._get_int(f"buff.{bid}.sentinel_x", 0)
                    buff["sentinel_y"]       = self._get_int(f"buff.{bid}.sentinel_y", 0)
                    buff["only_in_combat"]   = self._get_bool(f"buff.{bid}.only_in_combat", True)
                    buff["sentinel_enabled"] = self._get_bool(f"buff.{bid}.sentinel_enabled", False)
                    # --- OLD CODE (REPLACED) ---
                    # (chua save first key sequence)
                    # ---------------------------
                    first_key = self._get_str(f"buff.{bid}.first_key", "")
                    seq = buff.get("sequence", [])
                    if seq and isinstance(seq, list) and len(seq) > 0 and isinstance(seq[0], dict):
                        seq[0]["key"] = first_key

            # AI
            cfg.setdefault("ai_system", {}).update({
                "enabled":    self._get_bool("ai.enabled", True),
                "center_x":   self._get_int("ai.center_x", 958),
                "center_y":   self._get_int("ai.center_y", 510),
                "scan_size":  self._get_int("ai.scan_size", 600),
                "conf":       self._get_float("ai.conf", 0.45),
                "safe_box_w": self._get_int("ai.safe_box_w", 50),
                "safe_box_h": self._get_int("ai.safe_box_h", 120),
            })

            # --- OLD CODE (REPLACED: chua save quest_system) ---
            # --------------------------------------------------
            # Quest System
            cfg.setdefault("quest_system", {}).update({
                "enabled":     self._get_bool("quest.enabled", True),
                "trigger_key": self._get_str("quest.trigger_key", "n"),
                "delay_step1": self._get_float("quest.delay_step1", 0.1),
                "delay_step2": self._get_float("quest.delay_step2", 0.1),
                "delay_step3": self._get_float("quest.delay_step3", 0.4),
            })

            with open(CONFIG_PATH, "w", encoding="utf-8") as fp:
                json.dump(cfg, fp, indent=4, ensure_ascii=False)

            self.config = cfg
            if self.bot and self.bot.is_running:
                self.bot.reload_all_configs()
            self.status_var.set(f"Da luu: {CONFIG_PATH}")
            messagebox.showinfo(
                "Da luu",
                "Config da duoc luu thanh cong!\n\n"
                "Bot se tu nap lai khi bat bang phim toggle hoac da dang chay.",
            )

        except ValueError as e:
            messagebox.showerror("Gia tri khong hop le", str(e))
            self.status_var.set(f"Loi gia tri: {e}")
        except Exception as e:
            messagebox.showerror("Loi Save", str(e))
            self.status_var.set(f"Loi luu: {e}")

    # ------------------------------------------------------------------
    # BOT RUNTIME & HUD CONTROLLER
    # ------------------------------------------------------------------
    def start_bot(self):
        """Khoi chay hoac kich hoat Bot Engine (Tu dong dung Quest Macro neu dang bat)."""
        if SacredBotMemory is None:
            messagebox.showerror("Loi", "Khong the nap module SacredBotMemory tu sacred_bot.py!")
            return

        try:
            # Tu dong tat Farm Quest de tranh xung dot
            if self.quest_running:
                self.stop_quest()

            if self.bot is None:
                self.bot = SacredBotMemory()
                self.bot.is_running = True
                self.bot_thread = threading.Thread(target=self._bot_run_loop, daemon=True, name="GUI_BotThread")
                self.bot_thread.start()
            else:
                self.bot.reload_all_configs()
                self.bot.is_running = True
                if self.bot_thread is None or not self.bot_thread.is_alive():
                    self.bot.exit_event.clear()
                    self.bot_thread = threading.Thread(target=self._bot_run_loop, daemon=True, name="GUI_BotThread")
                    self.bot_thread.start()

            self.status_var.set("Đã gửi lệnh bật Bot (Running)")
        except Exception as e:
            messagebox.showerror("Lỗi Start Bot", str(e))
            self.status_var.set(f"Lỗi start bot: {e}")

    def stop_bot(self):
        """Tam dung Bot Engine."""
        if self.bot:
            self.bot.is_running = False
            if self.bot.combat_state:
                self.bot.combat_state.release_target()
            if self.bot.hotkey_sys:
                self.bot.hotkey_sys.release_all_inputs()
            pydirectinput.mouseUp(button='left')
            self.bot.last_event_msg = "Bot nghỉ ngơi"

        self.status_var.set("Đã dừng Bot (Stopped)")

    # ------------------------------------------------------------------
    # FARM QUEST CONTROLLER (DOC LAP VOI MAIN BOT)
    # ------------------------------------------------------------------
    def start_quest(self):
        """Khoi chay che do Farm Quest (Tu dong dung Bot neu dang chay)."""
        # Tu dong dung Bot de tranh xung dot thao tac
        if self.bot and self.bot.is_running:
            self.stop_bot()

        self.quest_running = True
        trig_key = self._get_str("quest.trigger_key", "n")
        self.status_var.set(f"Đã BẬT Farm Quest Macro (Nhấn / giữ phím '{trig_key}' trong game)")

    def stop_quest(self):
        """Tat che do Farm Quest."""
        self.quest_running = False
        self.status_var.set("Đã TẮT Farm Quest Macro")

    def _bot_run_loop(self):
        """Vong lap chay bot tren thread rieng."""
        try:
            self.bot.run()
        except Exception as e:
            print(f"[BOT RUNTIME ERROR]: {e}")

    def _start_quest_listener(self):
        """Thread lang nghe phím trigger cua Quest Macro (Ctrl+X -> Left Click -> Enter)."""
        if self.quest_thread and self.quest_thread.is_alive():
            return
        self.quest_thread = threading.Thread(target=self._quest_worker, daemon=True, name="QuestWorker")
        self.quest_thread.start()

    def _quest_worker(self):
        """Worker thuc thi chuoi thao tac Quest Macro khi che do Farm Quest dang BAT."""
        pydirectinput.FAILSAFE = False
        while not self._is_closing:
            try:
                if self.quest_running:
                    trig_key = self._get_str("quest.trigger_key", "n").strip().lower()
                    if not trig_key:
                        trig_key = "n"
                    d1 = self._get_float("quest.delay_step1", 0.1)
                    d2 = self._get_float("quest.delay_step2", 0.1)
                    d3 = self._get_float("quest.delay_step3", 0.4)

                    if keyboard.is_pressed(trig_key):
                        pydirectinput.keyDown('ctrl')
                        pydirectinput.press('x')
                        pydirectinput.keyUp('ctrl')
                        time.sleep(d1)
                        pydirectinput.click(button='left')
                        time.sleep(d2)
                        pydirectinput.press('enter')
                        time.sleep(d3)
            except Exception:
                pass
            time.sleep(0.02)

    def _poll_hud(self):
        """Cap nhat giao dien Live HUD thoi gian thuc."""
        if self._is_closing:
            return

        try:
            # 1. Main Bot Status
            if self.bot:
                if self.bot.game_connected:
                    self.lbl_game_status.config(text="Game: CONNECTED", bg="#C8E6C9", fg="#2E7D32")
                else:
                    self.lbl_game_status.config(text="Game: NOT CONNECTED", bg="#E0E0E0", fg="#555")

                if self.bot.is_running:
                    self.lbl_bot_status.config(text="Bot: RUNNING", bg="#C8E6C9", fg="#2E7D32")
                else:
                    self.lbl_bot_status.config(text="Bot: STOPPED", bg="#FFCDD2", fg="#C62828")

                with self.bot._data_lock:
                    hp = self.bot.shared_data.get('hp_percent', 100.0)
                self.lbl_hp_status.config(text=f"HP: {hp:5.1f}%")

                target_str = "None"
                if self.bot.combat_state and self.bot.combat_state.target_detected:
                    target_str = f"LOCK: {self.bot.combat_state.target_locked_id}"
                self.lbl_target_status.config(text=f"Target: {target_str}")

                event_txt = getattr(self.bot, 'last_event_msg', 'San sang')
                self.lbl_event_status.config(text=f"Event: {event_txt}")
            else:
                self.lbl_game_status.config(text="Game: NOT CONNECTED", bg="#E0E0E0", fg="#555")
                self.lbl_bot_status.config(text="Bot: STOPPED", bg="#FFCDD2", fg="#C62828")
                self.lbl_hp_status.config(text="HP: --%")
                self.lbl_target_status.config(text="Target: None")
                self.lbl_event_status.config(text="Event: Cho khoi chay")

            # 2. Quest Macro HUD Status
            if self.quest_running:
                trig_key = self._get_str("quest.trigger_key", "n")
                self.lbl_quest_status.config(text=f"Quest: ON ('{trig_key}')", bg="#FFE0B2", fg="#E65100")
            else:
                self.lbl_quest_status.config(text="Quest: OFF", bg="#EEEEEE", fg="#757575")

        except Exception:
            pass

        self.root.after(100, self._poll_hud)

    def _on_close(self):
        """Don dep tai nguyen khi dong GUI."""
        self._is_closing = True
        if self.bot:
            self.bot.exit_event.set()
            if self.bot.cooldown_hook and getattr(self.bot.cooldown_hook, 'is_hooked', False):
                try:
                    self.bot.cooldown_hook.uninstall()
                except Exception:
                    pass
            if self.bot.hotkey_sys:
                try:
                    self.bot.hotkey_sys.release_all_inputs()
                except Exception:
                    pass
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = SacredConfigGUI(root)
    root.mainloop()
