# IndexTTS2 API 設定指南

## 快速開始

### 1. 啟動 API 服務

```bash
uv run python run_api.py
```

**啟動時自動執行**：
- ✅ 檢查模型檔案
- ✅ 初始化資料庫（建立表格）
- ✅ **執行 Migrations（自動升級 schema）**
- ✅ Seed 預設資料（建立 admin 帳號）
- ✅ 載入 TTS 模型

### 2. 預設管理員帳號

啟動後會自動建立：

```
Email: admin@example.com
Password: test123
Username: admin
```

⚠️ **請立即修改密碼！**

---

## 資料庫 Migrations

### 自動 Migration（推薦）

**每次啟動 API 時會自動執行**，無需手動操作。

Migration 會：
- ✅ 檢查 schema 變更
- ✅ 新增缺少的欄位（如 tasks.user_id）
- ✅ 保留現有資料
- ✅ 自動指派現有 tasks 給 admin（user_id=1）

### 手動執行 Migration

如果需要單獨執行 migration（不啟動 API）：

```bash
uv run python run_migrations.py
```

**輸出範例**：
```
============================================================
Database Migration Runner
============================================================

Checking for pending migrations...
  Applying migration: add user_id to tasks table...
  Migrating 5 existing tasks to user_id=1 (admin)...
  [OK] Migration complete: user_id column added to tasks

[OK] Applied 1 migration(s): add_user_id_to_tasks
============================================================
[OK] All migrations completed successfully!
============================================================
```

---

## 啟動流程詳解

### 完整啟動順序

```
1. 檢查模型檔案
   ├─ bpe.model
   ├─ gpt.pth
   ├─ config.yaml
   ├─ s2mel.pth
   └─ wav2vec2bert_stats.pt

2. 初始化資料庫
   └─ 建立 users、tasks 表（如果不存在）

3. 執行 Migrations ⭐
   ├─ 檢查 tasks 表是否有 user_id 欄位
   ├─ 如果沒有：
   │  ├─ 建立新表結構（含 user_id + 外鍵）
   │  ├─ 複製現有資料（tasks → user_id=1）
   │  ├─ 替換舊表
   │  └─ 重建索引
   └─ 如果已有：跳過

4. Seed 資料
   ├─ 檢查 admin@example.com 是否存在
   └─ 不存在則建立預設 admin

5. 載入 TTS 模型
   └─ 初始化 IndexTTS2

6. 啟動服務
   └─ http://0.0.0.0:8000
```

---

## Migration 工作原理

### Schema 變更檢測

Migration 腳本會：

1. **檢查欄位是否存在**
   ```sql
   PRAGMA table_info(tasks);
   ```

2. **如果缺少 user_id**，執行遷移：
   ```sql
   -- 1. 建立新表（含 user_id）
   CREATE TABLE tasks_new (..., user_id INTEGER NOT NULL, ...)

   -- 2. 複製資料（指派給 admin）
   INSERT INTO tasks_new SELECT ..., 1 as user_id, ... FROM tasks

   -- 3. 替換表
   DROP TABLE tasks
   ALTER TABLE tasks_new RENAME TO tasks

   -- 4. 重建索引
   CREATE INDEX ix_tasks_user_id ON tasks(user_id)
   ```

3. **如果已經有 user_id**，跳過遷移

### 安全保證

- ✅ **保留所有資料**：不會刪除任何現有資料
- ✅ **冪等性**：重複執行不會出錯
- ✅ **自動檢測**：只執行必要的遷移
- ✅ **事務安全**：失敗會自動 rollback

---

## 常見問題

### Q: 每次啟動都會執行 migration 嗎？

A: 會**檢查**但不一定會**執行**。只有當檢測到 schema 變更時才會執行遷移。

**範例輸出（無需遷移）**：
```
Checking for pending migrations...
[OK] No pending migrations
```

**範例輸出（需要遷移）**：
```
Checking for pending migrations...
  Applying migration: add user_id to tasks table...
  [OK] Migration complete: user_id column added to tasks
[OK] Applied 1 migration(s): add_user_id_to_tasks
```

### Q: 現有的 tasks 會怎麼處理？

A: 所有現有的 tasks 會自動指派給 `user_id=1`（admin 帳號）。

### Q: 如果 migration 失敗怎麼辦？

A: 會自動 rollback，不會破壞資料。可以查看錯誤訊息並手動修復。

### Q: 可以跳過 migration 嗎？

A: 不建議。如果需要，可以暫時註解 `api/main.py` 中的 migration 程式碼，但這會導致 API 功能異常。

### Q: 如何確認 migration 成功？

**方法 1**: 查看啟動日誌
```
Checking for pending migrations...
[OK] No pending migrations  ← 表示已完成
```

**方法 2**: 測試 API
```bash
# 登入
curl -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"test123"}'

# 列出 tasks（需要 user_id 才能運作）
curl http://localhost:8000/v1/tts/tasks \
  -H "Authorization: Bearer <token>"
```

**方法 3**: 手動執行 migration 腳本
```bash
uv run python run_migrations.py
```

---

## 新增 Migration

如果將來需要新增其他 schema 變更，在 `api/database/migrate.py` 中新增：

```python
async def migrate_your_new_migration(session: AsyncSession) -> bool:
    """Description of your migration"""
    # 檢查是否需要執行
    # ...

    # 執行 SQL
    # ...

    return True  # 或 False 如果已執行過

# 在 run_migrations() 中註冊
async def run_migrations(session: AsyncSession) -> None:
    migrations_applied = []

    # 現有的 migration
    if await migrate_add_user_id_to_tasks(session):
        migrations_applied.append("add_user_id_to_tasks")

    # 新的 migration
    if await migrate_your_new_migration(session):
        migrations_applied.append("your_new_migration")

    # ...
```

---

## 環境變數

建立 `.env` 檔案設定環境變數：

```bash
# 資料庫
DATABASE_URL=sqlite+aiosqlite:///./data/indextts.db

# JWT 設定（重要！）
JWT_SECRET_KEY=your-super-secret-random-key-here
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=10080  # 7天

# 伺服器
HOST=0.0.0.0
PORT=8000
DEBUG=False

# 模型設定
MODEL_DIR=./checkpoints
USE_FP16=False
USE_DEEPSPEED=False
USE_CUDA_KERNEL=False

# 任務設定
MAX_CONCURRENT_TASKS=3
TASK_TIMEOUT=300
TASK_RETENTION=3600
CLEANUP_INTERVAL=600

# 檔案設定
OUTPUT_DIR=./outputs/api
MAX_TEXT_LENGTH=500
MAX_AUDIO_SIZE=10485760  # 10MB
```

---

## 故障排除

### 錯誤: `no such column: tasks.user_id`

**原因**: Migration 尚未執行或執行失敗

**解決方式**:
```bash
# 停止 API
# 手動執行 migration
uv run python run_migrations.py

# 重新啟動 API
uv run python run_api.py
```

### 錯誤: `Email already registered`

**原因**: Admin 帳號已存在

**解決方式**: 這是正常的，使用現有的 admin 帳號登入即可。

### 錯誤: `Missing required model files`

**原因**: 模型檔案未正確放置

**解決方式**: 確認 `checkpoints/` 目錄包含所有必要檔案：
```
checkpoints/
├── bpe.model
├── gpt.pth
├── config.yaml
├── s2mel.pth
└── wav2vec2bert_stats.pt
```

---

## 相關文件

- [API_AUTH_DOCUMENTATION.md](API_AUTH_DOCUMENTATION.md) - API 認證流程
- [USER_MANAGEMENT_GUIDE.md](USER_MANAGEMENT_GUIDE.md) - 使用者管理
- [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) - 遷移詳細說明

---

## 總結

✅ **完全自動化**：只需執行 `uv run python run_api.py`，所有設定和遷移都會自動完成

✅ **零停機更新**：未來的 schema 變更只需更新程式碼，啟動時自動遷移

✅ **開發友善**：本地開發可以隨時刪除資料庫重新開始，啟動時會自動重建

✅ **生產就緒**：Migration 安全且經過測試，可用於正式環境
