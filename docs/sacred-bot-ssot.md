# 📖 Sacred Bot — SSOT (Single Source of Truth)

> **Phiên bản:** v2.5 (Sacred_Bot.py & sacred_mele_memory.py)  
> **Cập nhật lần cuối:** 2026-08-29  
> **Target Game:** Sacred (sacred.exe) — Windows  
> **Yêu cầu:** Python 3.x · Administrator privileges · CUDA GPU (cho AI mode)

---

## 📋 Mục lục

1. [Tổng quan dự án](#1-tổng-quan-dự-án)
2. [Kiến trúc hệ thống](#2-kiến-trúc-hệ-thống)
3. [Cấu trúc file](#3-cấu-trúc-file)
4. [Module spec chi tiết](#4-module-spec-chi-tiết)
   - [SacredBot (Main)](#41-sacredbot---sacred_botpy)
   - [AutoPotion](#42-autopotion---autopotionclasspy)
   - [DangerSystem](#43-dangersystem---dangersystemclasspy)
   - [HotKeySystem](#44-hotkeysystem---hotkeysetsclasspy)
   - [CombatRadar](#45-combatradarcombatradarclasspyy)
   - [VoiceAssistant](#46-voiceassistant---voiceassistantpy)
   - [YOLOManager](#47-yolomanager---yolomanagerclasspyy)
   - [SacredUtils](#48-sacredutils---sacredutilspy)
   - [SkillManager (Deprecated)](#49-skillmanager-deprecated---skillmanagerclasspy)
   - [SkillCooldownManager](#410-skillcooldownmanager---skillcooldownclasspy)
   - [SacredMeleMemory](#411-sacredmelememory---sacred_mele_memorypy)
   - [SacredYoloBot](#412-sacredyolobot---sacred_yolopy)
5. [Cấu hình — sacred_config.json](#5-cấu-hình--sacred_configjson)
6. [Memory Map](#6-memory-map)
7. [Luồng dữ liệu & Threading](#7-luồng-dữ-liệu--threading)
8. [Cơ chế Target & Xác nhận Quái chết Đa Tầng](#8-cơ-chế-target--xác-nhận-quái-chết-đa-tầng)
9. [Hotkey & Combo System](#9-hotkey--combo-system)
10. [Dependencies](#10-dependencies)
11. [Hướng dẫn khởi chạy](#11-hướng-dẫn-khởi-chạy)
12. [Biến quan trọng & Hằng số](#12-biến-quan-trọng--hằng-số)
13. [Lưu ý & Known Issues](#13-lưu-ý--known-issues)

---

## 1. Tổng quan dự án

**SacredAuto** là bot tự động hoá cho game **Sacred** (game nhập vai hành động), hoạt động bằng cách:

| Kỹ thuật | Mô tả |
|---|---|
| **Memory Reading** | Đọc trực tiếp RAM game qua `pymem` để lấy HP, Threat |
| **Screen Vision** | Quét pixel màn hình (CombatRadar) để phát hiện thanh máu quái |
| **AI (YOLO)** | Dùng YOLOv8 + GPU để nhận diện quái vật (optional, dùng ở `YOLOManagerClass`) |
| **Input Simulation** | Mô phỏng phím/chuột bằng `pydirectinput` để điều khiển nhân vật |
| **Voice Feedback** | Thông báo giọng nói tiếng Việt qua Google TTS + `pygame` |

---

## 2. Kiến trúc hệ thống

```
┌─────────────────────────────────────────────────────────┐
│                      Sacred_Bot.py                      │
│                    (SacredBot - Main)                   │
│                                                         │
│  ┌──────────────────┐    ┌──────────────────────────┐  │
│  │  sensor_worker   │    │     action_worker         │  │
│  │  (Thread, 100ms) │    │     (Thread, 20ms)        │  │
│  │                  │    │                           │  │
│  │  AutoPotion  ──► │    │ ◄── shared_data (Lock)   │  │
│  │  DangerSystem──► │    │                           │  │
│  └──────────────────┘    │  CombatRadar              │  │
│         │                │  HotKeySystem             │  │
│         ▼                │  VoiceAssistant           │  │
│    shared_data           └──────────────────────────┘  │
│    (thread-safe)                                        │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │            main loop (100ms)                     │  │
│  │  - connect_game()   - toggle ON/OFF (key: D)     │  │
│  │  - ESC = exit       - winsound.Beep feedback     │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘

          ▼ Kết nối Memory ▼
     ┌────────────────────┐
     │   sacred.exe RAM   │
     │  HP addr / Threat  │
     └────────────────────┘
```

---

## 3. Cấu trúc file

```
SacredAuto/
├── BotEngine.py            ← [NEW 2026-09-01] Backend Core Base Class (Lifecycle, Workers, Shared State)
├── BuffScheduler.py        ← [NEW 2026-09-01] Module điều phối Auto Buff độc lập (Timer Gate & No Post-Cast Verify)
├── PotionPump.py           ← [NEW 2026-09-01] Module tự động bơm máu độc lập
├── CombatStateManager.py   ← [NEW 2026-09-01] Module quản lý Threat, Combat State & Safe Clear Timer
├── sacred_mele_memory.py   ← Entry point Melee Bot (Kế thừa BotEngine, Memory Hover Targeting)
├── sacred_config.json      ← SSOT cấu hình toàn bộ hệ thống
├── requirements.txt        ← Danh sách thư viện
├── Run_Sacred_Bot.bat      ← Shortcut chạy bot (Admin)
│
├── AutoPotionClass.py      ← Module đọc HP, EXP từ RAM
├── DangerSystemClass.py    ← Module đọc Threat, Monster IDs & Mouse Hover ID
├── HotKeySetClass.py       ← Module hotkey macro (Hỗ trợ Rising & Falling Edge / on_release)
├── CombatRadarClass.py     ← Module phát hiện quái bằng pixel scan
├── VoiceAssistant.py       ← Module thông báo giọng nói (Google TTS)
├── SacredUtils.py          ← Hàm tiện ích dùng chung (pointer resolver)
├── YOLOManagerClass.py     ← Module AI nhận diện quái (YOLOv8 + CUDA)
├── SkillCooldownClass.py   ← Module Hook ASM & đọc Memory Cooldown Skill (00562B13)
├── Sacred_Bot.py           ← Entry point chính (v2 - legacy)
├── Sacred_yolo.py          ← Entry point YOLO AI Bot
│
├── best.pt                 ← YOLO model đã train (sacred creep)
├── yolov8n.pt              ← YOLO pretrained base model
├── google_voice_cache/     ← Cache file .mp3 giọng nói (auto-generated)
├── docs/                   ← Tài liệu dự án
└── archive/                ← Thư mục lưu trữ rác/file/thư mục cũ (scratches/legacy/datasets/runs)
```

---

## 4. Module spec chi tiết

### 4.1 `SacredBot` — `Sacred_Bot.py`

**Vai trò:** Controller trung tâm, khởi tạo và điều phối tất cả module.

#### Constructor `__init__`

| Thuộc tính | Kiểu | Mô tả |
|---|---|---|
| `config` | `dict` | Toàn bộ config từ `sacred_config.json` |
| `voice` | `VoiceAssistant` | Instance trợ lý giọng nói |
| `pm` | `pymem.Pymem` | Kết nối process game |
| `module_addr` | `int` | Base address của `sacred.exe` |
| `radar` | `CombatRadar` | Module phát hiện quái |
| `potion_sys` | `AutoPotion` | Module đọc & uống máu |
| `danger_sys` | `DangerSystem` | Module đọc Threat |
| `hotkey_sys` | `HotKeySystem` | Module macro hotkey |
| `game_connected` | `bool` | Trạng thái kết nối game |
| `is_running` | `bool` | Bot đang chạy hay dừng |
| `exit_event` | `threading.Event` | Signal thoát toàn bộ thread |
| `_data_lock` | `threading.Lock` | Bảo vệ `shared_data` |
| `shared_data` | `dict` | Buffer chia sẻ giữa 2 thread |
| `is_in_combat` | `bool` | Đang trong trạng thái chiến đấu |
| `safe_start_time` | `float` | Mốc thời gian bắt đầu đếm Safe (giây thực) |
| `buff_queue` | `dict` | Khởi tạo danh sách 3 loại buff (CA/MA/CO) kèm trạng thái, timer riêng |
| `last_buff_finish_time` | `float` | Mốc thời gian hoàn tất lượt cast buff gần nhất |
| `last_buff_cast_delay` | `float` | Thời gian cast delay của buff vừa thi triển (giây) |
| `last_speak_time` | `float` | Chống spam voice khi bơm máu |
| `is_pressing` | `bool` | Trạng thái giữ chuột trái |

#### Methods

| Method | Mô tả |
|---|---|
| `load_config()` | Đọc `sacred_config.json`, trả về `dict` (hoặc `{}` nếu lỗi) |
| `connect_game()` | Kết nối pymem, khởi tạo tất cả module, trả về `bool` |
| `sensor_worker()` | **Thread 1:** Đọc HP + Threat mỗi 100ms, ghi vào `shared_data` |
| `action_worker()` | **Thread 2:** Logic chiến đấu (buff, potion, hotkey) mỗi 20ms |
| `run()` | Khởi động 2 thread + vòng lặp chính (toggle, exit) |

#### State Machine — `is_in_combat`

```
           threat > 0                     threat == 0 + safe_timer > 3s
[SAFE] ─────────────────► [COMBAT] ─────────────────────────────────► [SAFE]
         voice: "Có quái."  (buff mỗi BUFF_INTERVAL giây)            voice: "Clear."
```

---

### 4.2 `AutoPotion` — `AutoPotionClass.py`

**Vai trò:** Đọc HP và EXP hiện tại của nhân vật từ RAM game.

#### Memory Address

| Hằng số | Giá trị | Mô tả |
|---|---|---|
| `BASE_OFFSET` | `0x006D5C40` | Offset từ module base tới con trỏ HP & EXP |
| `OFFSETS` | `[0x4, 0x4, 0x4D8]` | Chuỗi pointer 3 tầng đọc Máu |
| `EXP_OFFSETS` | `[0x4, 0x4, 0x3B4]` | Chuỗi pointer 3 tầng đọc Kinh nghiệm (EXP) |

#### Cách tính HP & Đọc EXP

```
static_base  = module_addr + 0x006D5C40

# HP:
hp_addr      = get_pointer_address(pm, static_base, [0x4, 0x4, 0x4D8])
curr_hp      = pm.read_int(hp_addr)
max_hp       = pm.read_int(hp_addr - 4)   -- Max HP nằm trước 4 bytes
hp_percent   = (curr_hp / max_hp) * 100

# EXP:
exp_addr     = get_pointer_address(pm, static_base, [0x4, 0x4, 0x3B4])
total_exp    = pm.read_int(exp_addr)
```

#### API

| Method | Returns | Mô tả |
|---|---|---|
| `get_hp_percent()` | `float or None` | Trả về % HP (0–100), `None` nếu lỗi |
| `get_exp()` | `int or None` | Trả về tổng điểm kinh nghiệm (EXP) hiện tại của nhân vật |

---

### 4.3 `DangerSystem` — `DangerSystemClass.py`

**Vai trò:** Đọc "Threat Level" từ RAM, quét danh sách ID quái vật hiện hữu và đọc ID đối tượng đang hover dưới chuột.

#### Memory Address

| Hằng số | Giá trị | Mô tả |
|---|---|---|
| `BASE_OFFSET` | `0x013E9FA4` | Base Quái / Threat |
| `OFFSETS` | `[0xD38]` | Pointer Threat level (hoặc `[0xCC0]`) |
| `MONSTER_STRUCT_SIZE` | `0x88` (136 bytes) | Bước nhảy (stride) giữa các struct quái |
| `MONSTER_START_OFFSET` | `0xE30` | Offset struct quái đầu tiên |
| `MOUSE_HOVER_BASE` | `0x008DDB5C` | Base chuột trỏ đối tượng |
| `MOUSE_HOVER_OFFSET` | `0x6C` | Offset ID đối tượng dưới trỏ chuột |

#### API

| Method | Returns | Mô tả |
|---|---|---|
| `get_threat_level()` | `int` | Giá trị threat (0 = an toàn, > 0 = có quái) |
| `get_monster_ids(max_monsters=10)` | `set[int]` | Quét danh sách ID các con quái đang sống trong RAM |
| `get_mouse_hover_id()` | `int` | Đọc ID đối tượng dưới chuột (0: trống, 1: bản thân, > 1: NPC/quái) |
| `is_hovering_monster(monster_ids=None)` | `tuple[bool, int]` | Trả về `(is_monster, hover_id)` xác nhận chuột trỏ đúng quái |

---

### 4.4 `HotKeySystem` — `HotKeySetClass.py`

**Vai trò:** Quản lý hệ thống macro — thực thi chuỗi phím/chuột theo config.

#### Concepts

- **Combo:** Một tập hành động tuần tự (`sequence`) được đặt tên (`name`) và bind phím (`trigger_key`).
- **Edge Detection:** Chỉ trigger khi phím vừa được nhấn xuống (rising edge), không trigger liên tục khi giữ phím.
- **Bot-triggered combo:** Bot gọi trực tiếp `run_combo('buff')` không cần người nhấn phím.

#### Action Types trong `sequence`

| `action` | Tham số mở rộng | Mô tả |
|---|---|---|
| `press` | `key`, `wait` | Nhấn phím an toàn (keyUp → keyDown → delay 30ms → keyUp) |
| `click_right` | `hold` (mặc định 0.20s), `wait` | Click chuột phải kèm thời gian giữ chuột (`hold`) chuẩn Sweet Spot |
| `click_left` | `hold` (mặc định 0.20s), `wait` | Click chuột trái kèm thời gian giữ chuột (`hold`) |
| `right_down` / `mouse_down_right` | `wait` | Nhấn giữ chuột phải (không nhả) |
| `right_up` / `mouse_up_right` | `wait` | Nhả chuột phải |
| `left_down` / `mouse_down_left` | `wait` | Nhấn giữ chuột trái (không nhả) |
| `left_up` / `mouse_up_left` | `wait` | Nhả chuột trái |

#### API

| Method | Mô tả |
|---|---|
| `run_combo(name)` | Kích hoạt combo theo tên — dùng cho bot tự động |
| `run_check()` | Kiểm tra input người dùng — gọi mỗi 20ms trong `action_worker` |
| `_press_key(key)` | Nhấn phím an toàn (tránh stuck key) |
| `_run_sequence(seq)` | Thực thi danh sách step trong combo |

---

### 4.5 `CombatRadar` — `CombatRadarClass.py`

**Vai trò:** Phát hiện sự hiện diện của quái bằng cách quét pixel vùng thanh HP quái trên màn hình.

#### Nguyên lý

Chụp ảnh vùng nhỏ xung quanh `radar_center_x, radar_center_y` → phân tích từng pixel → tìm màu đặc trưng của thanh HP quái.

#### Màu nhận diện

| Màu | RGB Condition | Ý nghĩa |
|---|---|---|
| **WHITE** | R>250, G>250, B>250 | Thanh HP quái đầy |
| **YELLOW** | R>240, G>240, 100 < B < 150 | Thanh HP quái vàng |
| **RED** | 110 ≤ R ≤ 185, G < 95, B < 95 | Thanh HP quái đỏ (đang tấn công) |

> **Lưu ý:** Class này có method `is_target_detected()` nhưng **không được gọi trong `Sacred_Bot.py`** — `Sacred_Bot` dùng `DangerSystem` từ Memory thay thế. CombatRadar chỉ active trong các version AI bot.

#### Config keys dùng

```json
"combat_system": {
    "radar_center_x": 947,
    "radar_center_y": 790,
    "scan_width": 20,
    "scan_height": 3
}
```

---

### 4.6 `VoiceAssistant` — `VoiceAssistant.py`

**Vai trò:** Phát thông báo giọng nói tiếng Việt bất đồng bộ, không block luồng chính.

#### Kiến trúc

```
Bot Thread                         VoiceAssistant
──────────                         ──────────────
speak("Có quái.") ──► Queue ──►   _worker Thread (daemon)
                                   │
                                   ├── Kiểm tra cache file .mp3
                                   ├── Nếu chưa có → gTTS download
                                   └── pygame.mixer.music.play()
```

#### Caching

- Cache dir: `google_voice_cache/`
- Tên file: Text → alphanumeric, max 50 ký tự. Ví dụ: `Co_quai_.mp3`
- Chỉ tải từ Google 1 lần duy nhất cho mỗi câu nói

#### Queue

| Thuộc tính | Giá trị | Mô tả |
|---|---|---|
| `maxsize` | 3 | Tối đa 3 tin nhắn đang chờ |
| Overflow behavior | Drop (bỏ qua) | Tránh delay dồn khi bot nói quá nhiều |

#### API

| Method | Mô tả |
|---|---|
| `speak(text)` | Đưa vào queue, bỏ qua nếu queue đầy |

---

### 4.7 `YOLOManager` — `YOLOManagerClass.py`

**Vai trò:** Dùng YOLOv8 + CUDA để nhận diện và track quái vật trên màn hình.

> **Lưu ý:** Module này **KHÔNG được dùng** trong `Sacred_Bot.py` hiện tại. Chỉ active trong `AI_Hybrid_Bot.py` / `bot_with_yolo.py`.

#### Target Lock State Machine

```
[SEARCHING]
  Chua co target
  → Tim quai gan tam man hinh nhat
  → Tra ve screen_pos gan nhat
       |
       ▼ confirm_lock(pos)
[TRACKING]
  Co locked_target
  → Moi frame tim quai trong TRACKING_RADIUS
  → Neu tim thay: update locked_target
  → Neu mat > MAX_LOST_FRAMES: reset ve SEARCHING
  → Neu qua MAX_LOCK_DURATION: reset ve SEARCHING
```

#### Hằng số

| Hằng số | Giá trị | Mô tả |
|---|---|---|
| `MAX_LOST_FRAMES` | 5 | Frame mất dấu tối đa trước khi unlock |
| `TRACKING_RADIUS` | 160 px | Bán kính tìm quái cũ khi tracking |
| `MAX_LOCK_DURATION` | 6.0 s | Thời gian lock tối đa (anti-stuck) |

#### Safe Box

Vùng trung tâm bị loại trừ để không target chính mình:

| Key | Giá trị |
|---|---|
| `safe_box_w` | 50 px (chiều ngang) |
| `safe_box_h` | 120 px (chiều dọc) |

**Ngoại lệ:** Nếu quái đang bị lock tiến vào SafeBox thì bỏ qua giới hạn SafeBox để không mất lock khi cận chiến.

#### API

| Method | Mô tả |
|---|---|
| `get_best_target(debug=False)` | Chạy YOLO inference, trả về `(x,y)` screen hoặc `None` |
| `confirm_lock(pos)` | Bắt đầu lock mục tiêu tại `pos` |
| `reset_lock()` | Hủy lock, về trạng thái SEARCHING |
| `ignore_current_target(duration)` | Blacklist target hiện tại trong N giây |

---

### 4.8 `SacredUtils` — `SacredUtils.py`

**Vai trò:** Thư viện hàm tiện ích dùng chung cho các module Memory.

#### `get_pointer_address(pm, base_addr, offsets)`

Giải quyết chuỗi pointer đa tầng trong RAM game.

```python
# Ví dụ với AutoPotion:
# base_addr = module_addr + 0x006D5C40
# offsets   = [0x4, 0x4, 0x4D8]
#
# Bước 1: addr = pm.read_int(base_addr)
# Bước 2: addr = pm.read_int(addr + 0x4)
# Bước 3: return addr + 0x4D8   ← tầng cuối: cộng offset, không đọc tiếp
```

| Param | Type | Mô tả |
|---|---|---|
| `pm` | `pymem.Pymem` | Object kết nối process |
| `base_addr` | `int` | Địa chỉ tĩnh bắt đầu |
| `offsets` | `list[int]` | Danh sách offset, tầng cuối được cộng trực tiếp |
| **Returns** | `int or None` | Địa chỉ cuối cùng, `None` nếu lỗi |

---

### 4.9 `SkillManager` [DEPRECATED] — `SkillManagerClass.py`

> **DEPRECATED:** Toàn bộ code đã được comment out. Module này không được sử dụng.  
> **Ý tưởng ban đầu:** Phát hiện skill sáng màu bằng pixel detection, tự động cast.  
> **Thay thế bởi:** `HotKeySystem` (combo) + `DangerSystem` (threat detection).

---

### 4.10 `SkillCooldownManager` — `SkillCooldownClass.py`

**Vai trò:** Quản lý tự động Inject Hook ASM tại `00562B13` vào bộ nhớ `Sacred.exe`, đọc giá trị Cooldown Skill float chính xác 100% để phục vụ Auto Buff độc lập (Magic & CA).

#### Hook Specification

| Thuộc tính | Giá trị | Mô tả |
|---|---|---|
| `HOOK_ADDR` | `0x00562B13` | Điểm tiêm lệnh nhảy `jmp newmem + 3*NOP` (8 bytes) |
| `ORIGINAL_BYTES` | `D8 6C 0E 12 D9 5C 0E 12` | `fsubr [esi+ecx+12]` + `fstp [esi+ecx+12]` |
| `ALLOC_SIZE` | `2048` bytes | Vùng nhớ cấp phát động trong `Sacred.exe` |
| `PTR_OFFSET` | `+0x100` | Địa chỉ biến lưu con trỏ `cooldownAddressPtr` |

#### API

| Method | Returns | Mô tả |
|---|---|---|
| `install()` | `bool` | Cấp phát bộ nhớ, ghi bytecode hook và kích hoạt chuyển hướng |
| `get_cooldown()` | `float or None` | Đọc giá trị cooldown hiện tại (0.0 = Ready, > 0 = Cooldown) |
| `is_ready()` | `bool` | Trả về `True` nếu cooldown <= 0.001 |
| `is_on_cooldown()` | `bool` | Trả về `True` nếu cooldown > 0.001 |
| `uninstall()` | `None` | Khôi phục 8 bytes mã gốc của game an toàn |

---

### 4.11 `SacredMeleMemory` — `sacred_mele_memory.py`

**Vai trò:** Phiên bản Bot Melee tối ưu hoàn toàn qua đọc bộ nhớ (Zero Screen Scanning), kế thừa `BotEngine` theo mô hình DRY/SOLID. Tự động khóa mục tiêu qua Hover ID + Monster IDs trong RAM và tự động giữ/nhả chuột trái.

#### Các Thread hoạt động

| Thread | Tần suất | Nơi định nghĩa | Vai trò |
|---|---|---|---|
| `sensor_worker` | 50ms (20 FPS) | `BotEngine` | Đọc song song HP, Threat, Danh sách Monster IDs (`get_monster_ids`) và Hover ID (`get_mouse_hover_id`) |
| `action_worker` | 20ms (50 FPS) | `BotEngine` | Điều phối `CombatStateManager`, `BuffScheduler` (Timer Gate, No Post-Cast Verify), `PotionPump` & HotKey |
| `targeting_worker` | 20ms (50 FPS) | `SacredBotMemory` | Nhận diện thay đổi Hover ID, so khớp với Monster IDs, kích hoạt/hủy khóa mục tiêu và đè/nhả chuột trái |

---

### 4.12 `SacredYoloBot` — `Sacred_yolo.py`

**Vai trò:** Phiên bản Bot AI tích hợp **"Mắt AI" (YOLOv8 + CUDA)** kết hợp kiến trúc Multi-layer Confirmation & Unified Mouse Arbiter. Sử dụng mạng nơ-ron nhận diện bbox quái vật $\rightarrow$ di chuyển chuột tối ưu $\rightarrow$ khóa và xác nhận quái chết đa tầng qua RAM (EXP, Hover ID, Threat) và CombatRadar.

#### Các Thread hoạt động

| Thread | Tần suất | Vai trò |
|---|---|---|
| `sensor_worker` | 50ms (20 FPS) | Đọc song song HP, Threat, EXP, Danh sách Monster IDs (`get_monster_ids`) và Hover ID (`get_mouse_hover_id`) |
| `action_worker` | 20ms (50 FPS) | Điều phối Auto Buff độc lập (Fast-Retry + Hook ASM `00562B13`), Bơm máu, Giám sát tăng EXP (quái chết) & Safe Clear |
| `yolo_worker` | 20ms (50 FPS) | Độc lập điều khiển bởi phím `Z` (Bật) / `X` (Tắt). Mở màn hình OpenCV Debug (`debug=True`) $\rightarrow$ YOLO AI quét quái $\rightarrow$ di chuột tới tọa độ tối ưu $\rightarrow$ Xác thực đa tầng (Hover ID / Radar) để khóa mục tiêu và set cờ `target_detected` |
| `mouse_arbiter_worker` | 10ms (100 FPS) | Bộ trọng tài chuột thống nhất: Tự động đè Chuột Trái khi YOLO khóa quái (`target_detected`) và tự động nhả chuột ngay khi quái chết / mất dấu / tắt bằng phím `X` |

---

## 5. Cấu hình — `sacred_config.json`

File cấu hình tập trung duy nhất. **Mọi thay đổi cần chỉnh sửa ở đây, không hard-code trong code.**

### 5.1 Section `global`

| Key | Default | Mô tả |
|---|---|---|
| `selected_class` | `"WoodElf"` | Class nhân vật hiện tại |
| `process_name` | `"sacred.exe"` | Tên tiến trình game |
| `toggle_key` | `"d"` | Phím bật/tắt bot |
| `cast_delay` | `0.5` | Delay giữa các lần cast (s) |

### 5.2 Section `potion_system`

| Key | Default | Mô tả |
|---|---|---|
| `enabled` | `true` | Bật/tắt hệ thống uống máu |
| `threshold_percent` | `30` | Uống máu khi HP < N% |
| `key` | `"space"` | Phím uống máu |

> Cooldown uống máu: **0.8 giây** (hard-code trong `action_worker`)

### 5.3 Section `danger_system`

| Key | Default | Mô tả |
|---|---|---|
| `enabled` | `true` | Bật/tắt |
| `base_pointer_offset` | `20881316` | (thông tin tham khảo, xem Memory Map) |
| `cooldown_after_fight` | `5.0` | Giây chờ sau khi hết quái |

### 5.4 Section `combat_system`

| Key | Default | Mô tả |
|---|---|---|
| `radar_center_x` | `947` | Tâm X quét CombatRadar (pixel màn hình) |
| `radar_center_y` | `790` | Tâm Y quét CombatRadar |
| `scan_width` | `20` | Chiều rộng vùng quét (px) |
| `scan_height` | `3` | Chiều cao vùng quét (px) |
| `melee_hold_mode` | `true` | Giữ chuột trái khi cận chiến |

### 5.5 Section `auto_buff_system` (v2.0 Visual Sentinel + Priority Scheduler)

| Key | Default | Mô tả |
|---|---|---|
| `enabled` | `true` | Bật/tắt toàn bộ hệ thống auto buff |
| `buffs[].id` | `"ca_buff" / "ma_buff" / "co_buff"` | Định danh loại buff |
| `buffs[].name` | String | Tên hiển thị / phát giọng nói |
| `buffs[].enabled` | `true / false` | Bật/tắt riêng từng loại buff |
| `buffs[].interval` | Number (giây) | Chu kỳ thi triển tối thiểu của từng loại buff |
| `buffs[].cast_delay` | Number (giây) | Thời gian nghỉ khôi phục sau khi cast buff |
| `buffs[].sentinel_enabled` | `true` | Bật/tắt kiểm tra màu điểm ảnh trinh sát cho buff này |
| `buffs[].sentinel_x` | Number (pixel) | Tọa độ X của điểm Sentinel trên icon skill |
| `buffs[].sentinel_y` | Number (pixel) | Tọa độ Y của điểm Sentinel trên icon skill |
| `buffs[].tolerance_rgb` | `1` | Dung sai chênh lệch R, G, B cho dải màu xám đen ($R \approx G \approx B$) |
| `buffs[].min_brightness` | `14` | Ngưỡng giới hạn dưới độ sáng của dải xám đen khi Cooldown |
| `buffs[].max_brightness` | `177` | Ngưỡng giới hạn trên độ sáng của dải xám đen khi Cooldown |
| `buffs[].retry_timeout` | `3.0` (giây) | Cửa sổ chờ gác soi màu tối đa khi chiêu chưa hồi |
| `buffs[].sequence` | Array | Chuỗi các phím/chuột thực thi cho buff |

#### Nguyên lý Lập lịch Ưu tiên & Trinh sát Thị giác (Closed-Loop Feedback)
1. **Lọc thô (Timer Gatekeeper):** Buff chỉ được xét khi đếm đủ chu kỳ `interval`.
2. **Lọc tinh (Visual Sentinel):** Đọc màu điểm ảnh $(1\times1\text{ px})$ tại `(sentinel_x, sentinel_y)`. Nếu màu thuộc phổ xám đen ($R \approx G \approx B$) $\Rightarrow$ Skill đang Cooldown/Casting. Ngược lại $\Rightarrow$ Skill Ready.
3. **Chuyển mạch ưu tiên (Context Switching):** Nếu buff hiện tại đến lượt nhưng chưa Ready (tối màu), bot ưu tiên kiểm tra xem có buff nào khác cũng đang đến mốc `interval` và đã Ready để cast trước.
4. **Cửa sổ chờ gác (Non-blocking Retry Window 2–3s):** Nếu không có buff nào khác, bot gác soi màu buff hiện tại tối đa `retry_timeout` giây (không chặn luồng Bơm máu / Hotkey) đến khi chiêu sáng màu để cast ngay.

### 5.6 Section `ai_system`

| Key | Default | Mô tả |
|---|---|---|
| `enabled` | `true` | Bật/tắt YOLO AI |
| `model_path` | `"yolov8n.pt"` | Đường dẫn model YOLO |
| `scan_size` | `600` | Kích thước vùng chụp màn hình (px) |
| `center_x` | `958` | Tâm X vùng scan AI |
| `center_y` | `560` | Tâm Y vùng scan AI |
| `safe_box_w` | `50` | Chiều rộng SafeBox (loại trừ bản thân) |
| `safe_box_h` | `120` | Chiều cao SafeBox |
| `conf` | `0.45` | Ngưỡng confidence YOLO |
| `target_classes` | `["creep","person","dog","horse"]` | Các class quái cần nhắm |

### 5.6 Section `hotkey_system`

| Key | Mô tả |
|---|---|
| `enabled` | Bật/tắt toàn bộ hotkey system |
| `combos[]` | Danh sách combo (xem mục 8) |

### 5.7 Section `classes`

Định nghĩa skill cho từng class nhân vật:

| Class | Skill | Key |
|---|---|---|
| `WoodElf` | Đấm Liên Hoàn (Spam) | `1` |
| `WoodElf` | Hộ Thể (Buff, duration 25s) | `6` |
| `Seraphim` | Sét Xoay (Active) | `2` |

---

## 6. Memory Map

> **Cảnh báo:** Các địa chỉ này dành riêng cho version Sacred đã scan. Cần update thủ công nếu game patch.

### HP & EXP (AutoPotion)

```
sacred.exe  +  0x006D5C40
    → read_int(base)
    → read_int(ptr + 0x4)
    → read_int(ptr2 + 0x4)
    → HP_ADDR  = ptr3 + 0x4D8
    → EXP_ADDR = ptr3 + 0x3B4

pm.read_int(HP_ADDR)     = Current HP (int32)
pm.read_int(HP_ADDR - 4) = Max HP (int32)
pm.read_int(EXP_ADDR)    = Total Character EXP (int32)
```

### Threat Level & Monster Structs (DangerSystem)

```
sacred.exe  +  0x013E9FA4
    → read_int(base)
    → THREAT_ADDR        = ptr + 0xD38 (hoặc 0xCC0)
    → MONSTER_SLOT_0_PTR = ptr + 0xE30
    → MONSTER_SLOT_i_PTR = ptr + 0xE30 + (i * 0x88)  (Stride = 0x88 bytes)

pm.read_int(THREAT_ADDR) = Threat Level (0 = Safe, > 0 = Danger)
pm.read_int(SLOT_i_PTR)  = Monster ID (> 0 khi slot có quái)
```

### Mouse Hover Object ID (DangerSystem)

```
sacred.exe  +  0x008DDB5C
    → read_int(base)
    → HOVER_ADDR = ptr + 0x6C

pm.read_int(HOVER_ADDR)  = Object ID dưới con trỏ chuột
    0   = Trống / Địa hình
    1   = Nhân vật của mình
    > 1 = ID của NPC / Quái vật mục tiêu
```

### Skill Cooldown Hook (SkillCooldownClass)

```
sacred.exe  +  0x00562B13 (Bytecode: D8 6C 0E 12 D9 5C 0E 12)
    → Hook JMP to allocated memory
    → Lưu con trỏ cooldown tại: alloc_addr + 0x100
    → read_float(read_int(alloc_addr + 0x100)) = Cooldown Float (0.0 = Sẵn sàng, > 0 = Cooldown)
```

---

## 7. Luồng dữ liệu & Threading

### Tổng quan Thread

| Thread | Interval | Nhiệm vụ |
|---|---|---|
| `main` (run loop) | 100ms | Toggle ON/OFF, exit detection, reconnect |
| `sensor_worker` | 100ms / 50ms | Đọc HP, Threat, EXP, Monster IDs, Hover ID từ RAM |
| `action_worker` / `combat_worker` | 20ms | Logic buff, potion, EXP monitoring, safe timer |
| `memory_target_worker` | 20ms | So khớp Hover ID với Monster IDs, kích hoạt target lock |
| `mouse_arbiter_worker` | 10ms | Điều phối đè/nhả chuột trái/phải không xung đột |
| `VoiceAssistant._worker` | blocking | Phát audio từ queue |

### Thread-safe Data Flow

```
memory_sensor_worker                     combat_worker / target_worker
────────────────────                     ─────────────────────────────
hp         = potion_sys.get_hp_percent()
exp        = potion_sys.get_exp()
threat     = danger_sys.get_threat_level()
monsters   = danger_sys.get_monster_ids()
hover_id   = danger_sys.get_mouse_hover_id()

with _data_lock:                         with _data_lock:
    shared_data['hp_percent']   = hp         hp       = shared_data['hp_percent']
    shared_data['exp']          = exp        exp      = shared_data['exp']
    shared_data['threat_level'] = threat     threat   = shared_data['threat_level']
    shared_data['monster_ids']  = monsters   monsters = shared_data['monster_ids']
    shared_data['hover_id']     = hover_id   hover_id = shared_data['hover_id']
```

### Reconnect Logic

Khi `game_connected = False` (do exception trong sensor worker):

1. Worker tạm dừng thực thi hành vi game
2. `main loop` phát hiện → gọi `connect_game()` thử lại
3. Nếu thành công → các worker tiếp tục tự động

---

## 8. Cơ chế Target & Xác nhận Quái chết Đa Tầng

> **Nguyên lý cốt lõi:** Khi đánh quái, bot nhận diện quái chết qua sự kiện **tăng EXP** kết hợp cùng trạng thái **Memory ID Entity** để nhả khóa mục tiêu (`target_detected = False`) một cách tức thì và mượt mà.

### 8.1 Cơ chế Xác nhận Quái chết 4 Tầng (Multi-Tier Target Disengagement)

```
                       ┌──────────────────────────────┐
                       │  ĐANG TẤN CÔNG MỤC TIÊU      │
                       │  (target_detected = True)    │
                       └──────────────┬───────────────┘
                                      │
          ┌───────────────────────────┼───────────────────────────┐
          ▼                           ▼                           ▼
┌──────────────────┐        ┌──────────────────┐        ┌──────────────────┐
│  TẦNG 1: EXP     │        │  TẦNG 2: MEMORY  │        │  TẦNG 3: HOVER   │
│  exp > last_exp  │        │  ID biến mất     │        │  hover_id <= 1   │
│  (Quái bị diệt)  │        │  khỏi monster_ids│        │  (Rời trỏ chuột) │
└─────────┬────────┘        └─────────┬────────┘        └─────────┬────────┘
          │                           │                           │
          └───────────────────────────┼───────────────────────────┘
                                      ▼
                       ┌──────────────────────────────┐
                       │   XÁC NHẬN MỤC TIÊU HỦY/CHẾT │
                       │   - target_detected = False  │
                       │   - target_locked_id = 0     │
                       │   - Nhả đè Chuột Trái        │
                       │   - Chuyển sang quái tiếp    │
                       └──────────────────────────────┘
```

1. **Tầng 1 — Giám sát Biến động EXP (`combat_worker`):**
   - Đọc liên tục điểm kinh nghiệm nhân vật từ RAM (`get_exp()`).
   - Khi `last_exp > 0` và `exp > last_exp`: Xác nhận có quái bị tiêu diệt (`+exp_gained EXP!`).
   - Ngay lập tức đặt `self.target_detected = False` và `self.target_locked_id = 0`.
2. **Tầng 2 — Hủy Struct Entity trong RAM (`memory_target_worker`):**
   - Khi quái chết, engine game Sacred thu hồi struct của quái đó.
   - Hàm `get_monster_ids()` không còn chứa `target_locked_id` ➔ Bot nhận diện `target_locked_id not in monster_ids` và tự động nhả target.
3. **Tầng 3 — Trỏ chuột thoát khỏi quái (`Hover ID`):**
   - Khi quái tan biến hoặc người chơi lia chuột đi nơi khác, `hover_id` trở về `<= 1` ➔ Nhả cờ target.
4. **Tầng 4 — Quét sạch Bãi Quái (Safe Clear Timer):**
   - Khi `threat == 0` kéo dài liên tục > 3.0 giây thực (`safe_start_time`), bot phát giọng nói `"Clear."`, đưa `is_in_combat = False` và dọn sạch trạng thái target.

### 8.2 Bộ Trọng tài Chuột Thống nhất (`mouse_arbiter_worker`)

- **Chuột Trái (`mouseDown('left')`):**
  $$\text{should\_left\_down} = \text{target\_detected} \lor \text{keyboard.is\_pressed('z')}$$
  - Khi đè `Z` chạy map: Giữ chuột liên tục không giật lag.
  - Khi chuột chạm vào quái (`target_detected == True`): Tự động đè chuột đánh quái.
  - Khi quái chết (EXP tăng / ID mất): Tự động nhả chuột trái ngay lập tức (nếu không đè `Z`).
- **Chuột Phải (`mouseDown('right')`):**
  - Đồng bộ trực tiếp theo phím `X` của người chơi.

---

## 9. Hotkey & Combo System

### Combo hiện tại (theo config)

| Combo | Trigger | Sequence |
|---|---|---|
| `Combo T` | `T` | key `6` → key `F1` |
| `Combo Y` | `Y` | key `6` → key `F2` |
| `Combo U` | `U` | key `6` → key `F3` → click_right |
| `Combo G` | `G` | key `6` → key `F4` → click_right |
| `Combo V` | `V` | key `6` → key `F5` → click_right |
| `Combo N` | `N` | key `6` → key `F6` → click_right |

> **Lưu ý:** Các hệ thống buff tự động (`ca_buff`, `ma_buff`, `co_buff`) hiện được quản lý độc lập tại section `auto_buff_system`, không còn nằm trong mảng `hotkey_system.combos`.

### Cách thêm combo mới

```json
{
    "name": "TenCombo",
    "trigger_key": "x",
    "sequence": [
        {"action": "press", "key": "1", "wait": 0.1},
        {"action": "click_right", "key": "", "wait": 0.05}
    ]
}
```

> Đặt `"trigger_key": "none"` nếu muốn combo chỉ do bot gọi.

---

## 10. Dependencies

### `requirements.txt`

| Package | Mục đích |
|---|---|
| `pymem` | Đọc bộ nhớ process game |
| `keyboard` | Detect phím bàn phím (global hook) |
| `pydirectinput` | Mô phỏng input Win32 (hoạt động với DirectX game) |
| `mss` | Chụp màn hình nhanh (dùng cho YOLO) |
| `pyautogui` | Chụp màn hình (dùng cho CombatRadar) |
| `numpy` | Xử lý ảnh array |
| `pygame` | Phát audio .mp3 |
| `gtts` | **(cần thêm)** Google Text-to-Speech |
| `torch==2.4.0+cu121` | CUDA 12.1 runtime cho YOLO |
| `torchvision==0.19.0+cu121` | Companion của torch |
| `torchaudio==2.4.0+cu121` | Companion của torch |
| `ultralytics` | **(cần thêm)** YOLOv8 framework |
| `opencv-python` | **(cần thêm)** Xử lý ảnh debug YOLO |

### Cài đặt

```bash
pip install -r requirements.txt

# Cần index riêng cho torch CUDA
pip install torch==2.4.0+cu121 torchvision==0.19.0+cu121 --index-url https://download.pytorch.org/whl/cu121

# Cài thêm các gói còn thiếu trong requirements.txt
pip install gtts ultralytics opencv-python
```

---

## 11. Hướng dẫn khởi chạy

### Cách 1: File .bat (Khuyên dùng)

```
Chuột phải Run_Sacred_Bot.bat → "Run as administrator"
```

### Cách 2: Terminal

```bash
# Bắt buộc chạy với quyền Admin
python Sacred_Bot.py

# Hoặc chạy bản Melee Memory
python sacred_mele_memory.py
```

### Quy trình khởi động

1. Mở game `sacred.exe`
2. Chạy bot bằng quyền **Administrator**
3. Bot tự kết nối → thông báo giọng nói: *"Hệ thống đã sẵn sàng. Chiến thôi đại ca!"*
4. Nhấn phím **`D`** để **BẬT** bot → Beep 1000 Hz
5. Nhấn phím **`D`** lần nữa để **TẮT** bot → Beep 500 Hz
6. Nhấn **`ESC`** để thoát hoàn toàn

### Lỗi thường gặp & Fix

| Lỗi | Nguyên nhân | Fix |
|---|---|---|
| `ProcessNotFound` | Game chưa mở | Mở `sacred.exe` trước |
| `CouldNotOpenProcess` | Thiếu quyền Admin | Chạy lại bằng Run as Administrator |
| `[GOOGLE TTS] Error` | Mất mạng lần đầu | Kiểm tra internet |
| Bot không phản ứng | `is_running = False` | Nhấn `D` để bật bot |
| Giọng nói không có | `pygame.mixer` lỗi | Kiểm tra audio driver / pygame version |

---

## 12. Biến quan trọng & Hằng số

### Timing Constants

| Biến / Hằng | Giá trị | Nguồn | Mô tả |
|---|---|---|---|
| `BUFF_INTERVAL` | 30s | `combat_system.buff_interval` | Chu kỳ buff tự động |
| Potion cooldown | 0.8s | Hard-code `action_worker` | Min thời gian giữa 2 lần uống máu |
| Safe timer | 3.0s | Hard-code `action_worker` | Chờ sau khi threat=0 trước khi nói "Clear" |
| Voice spam guard | 3.0s | Hard-code `action_worker` | Cooldown thông báo "Bơm máu!" |
| Sensor interval | 0.1s / 0.05s | Hard-code `sensor_worker` | Tần suất đọc memory |
| Action interval | 0.02s | Hard-code `action_worker` | Tần suất thực thi logic |
| Main loop interval | 0.1s | Hard-code `run()` | Tần suất poll toggle/exit |
| Toggle debounce | 0.4s | Hard-code `run()` | Tránh double-toggle khi nhấn phím |

### Key Controls Summary

| Phím | Chức năng |
|---|---|
| `D` (config: `toggle_key`) | Bật / Tắt bot |
| `ESC` | Thoát bot hoàn toàn |
| `Z` | Đè để di chuyển / đánh tay mượt mà |
| `X` | Đè để thi triển chiêu chuột phải |
| `T` | Kích hoạt Combo T |
| `Y` | Kích hoạt Combo Y |
| `U` | Kích hoạt Combo U |
| `G` | Kích hoạt Combo G |
| `V` | Kích hoạt Combo V |
| `N` | Kích hoạt Combo N |

---

## 13. Lưu ý & Known Issues

### Design Decisions

**Tại sao không reset `last_buff_time` khi Clear?**

Buff interval được tính liên tục xuyên suốt các bãi quái. Nếu reset khi Clear, buff sẽ trigger ngay khi vào bãi mới và không đồng đều. Thiết kế hiện tại đảm bảo buff cycle ổn định bất kể số lần Clear.

**Tại sao `sensor_worker` tách khỏi `action_worker`?**

Đọc memory (I/O bound) không cần tần suất cao như action logic. Tách 2 thread cho phép `action_worker` chạy nhanh (20ms) mà không bị block bởi memory read (100ms).

**Tại sao YOLO không dùng trong `Sacred_Bot.py`?**

`Sacred_Bot.py` là phiên bản lightweight dùng Memory + Radar thay vì AI. YOLO cần GPU, tốn tài nguyên. Dùng `AI_Hybrid_Bot.py` nếu muốn AI mode.

### Known Issues & TODO

| # | Vấn đề | Trạng thái |
|---|---|---|
| 1 | `CombatRadar` khởi tạo trong `connect_game()` nhưng không được gọi trong `Sacred_Bot.py` | Dead code |
| 2 | `SkillManagerClass.py` hoàn toàn comment out | Deprecated |
| 3 | Memory addresses hard-code → vỡ nếu game patch | Cần update thủ công |
| 4 | `gtts` không có trong `requirements.txt` | Thiếu dependency |
| 5 | `ultralytics` không có trong `requirements.txt` | Thiếu dependency |
| 6 | `opencv-python` không có trong `requirements.txt` | Thiếu dependency |
| 7 | Toggle key `"d"` trong config nhưng `action_worker` lại cũng check toggle key trong `run()` — không xung đột | OK |
| 8 | `VoiceAssistant` chờ `pygame.mixer` busy có thể gây delay nhỏ khi queue đầy | Chấp nhận được |

---

*Tài liệu này là nguồn sự thật duy nhất (SSOT) cho project SacredAuto. Mọi thay đổi kiến trúc phải được phản ánh tại đây.*
