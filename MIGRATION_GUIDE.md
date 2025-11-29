# 資料庫遷移指南：Task-User 關聯

## 📋 變更摘要

此次更新修復了一個重要的安全問題：**Task 未關聯到 User，導致任何人都可以查看、下載或刪除其他人的任務**。

## 🔧 已修改的檔案

### 1. 資料庫模型
- **[api/models/task.py](api/models/task.py)** - 新增 `user_id` 欄位和與 User 的關聯
- **[api/models/user.py](api/models/user.py)** - 新增與 Task 的反向關聯

### 2. 服務層
- **[api/services/task_service.py](api/services/task_service.py)** - 所有查詢方法都支援 `user_id` 過濾

### 3. API 路由
- **[api/routes/tasks.py](api/routes/tasks.py)** - 所有端點都加入了權限驗證
- **[api/routes/tts.py](api/routes/tts.py)** - 創建 task 時記錄 `user_id`

## 🔒 安全改進

### 修復前的問題
```python
# ❌ 任何人都可以查看所有 tasks
GET /v1/tts/tasks  # 沒有權限檢查

# ❌ 任何人都可以下載任何 task 的音檔
GET /v1/tts/download/{task_id}  # 沒有檢查是否為 owner

# ❌ 任何人都可以刪除任何 task
DELETE /v1/tts/tasks/{task_id}  # 沒有權限檢查
```

### 修復後的保護
```python
# ✅ 只能查看自己的 tasks
GET /v1/tts/tasks
# 需要 Authorization header，只返回當前用戶的 tasks

# ✅ 只能下載自己的音檔
GET /v1/tts/download/{task_id}
# 檢查 task.user_id == current_user.id

# ✅ 只能刪除自己的 task
DELETE /v1/tts/tasks/{task_id}
# 檢查 task.user_id == current_user.id
```

## 📊 資料庫變更

### Tasks 表新增欄位

```sql
ALTER TABLE tasks ADD COLUMN user_id INTEGER NOT NULL;
ALTER TABLE tasks ADD FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
CREATE INDEX ix_tasks_user_id ON tasks(user_id);
```

### 關聯關係

```
User (1) ----< (N) Task
  └─ 一個 User 可以有多個 Tasks
  └─ 刪除 User 時會自動刪除其所有 Tasks (CASCADE)
```

## 🚀 遷移步驟

### 選項 1: 使用 Python 遷移腳本（推薦）

```bash
# 執行自動遷移腳本
uv run python migrations/migrate_add_user_id.py
```

此腳本會：
1. ✅ 檢查 `user_id` 欄位是否已存在
2. ✅ 備份現有資料到 `tasks_backup`
3. ✅ 重建 tasks 表並加入 `user_id` 欄位
4. ✅ 將現有 tasks 指派給 user_id = 1
5. ✅ 建立必要的索引和外鍵約束

### 選項 2: 手動 SQL 遷移

```bash
# 使用 SQLite CLI
sqlite3 ./data/indextts.db < migrations/add_user_id_to_tasks.sql
```

### 選項 3: 刪除並重建資料庫（僅開發環境）

```bash
# ⚠️ 警告：這會刪除所有資料！
rm ./data/indextts.db

# 重新啟動 API，資料庫會自動重建
uv run python run_api.py
```

## ⚠️ 重要注意事項

### 1. 現有資料處理

如果你的資料庫中已有 tasks：
- 所有現有的 tasks 會被指派給 `user_id = 1`
- **請確保 ID 為 1 的使用者存在**
- 或手動修改遷移腳本中的 user_id

### 2. 確認遷移成功

執行遷移後，檢查資料庫：

```bash
sqlite3 ./data/indextts.db

# 檢查 tasks 表結構
.schema tasks

# 應該看到：
# user_id INTEGER NOT NULL
# FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE

# 檢查現有資料
SELECT id, user_id, status FROM tasks LIMIT 5;

# 清理備份表（確認無誤後）
DROP TABLE tasks_backup;
```

### 3. API 行為變更

#### 變更前
```javascript
// 所有用戶看到相同的 tasks 列表
GET /v1/tts/tasks
Response: [task1, task2, task3, ...]  // 所有用戶的 tasks
```

#### 變更後
```javascript
// 每個用戶只看到自己的 tasks
GET /v1/tts/tasks
Headers: { Authorization: "Bearer <token>" }
Response: [task1, task2]  // 只有當前用戶的 tasks
```

### 4. 前端需要的調整

所有 task 相關的 API 現在都**需要**認證：

```javascript
// ❌ 錯誤：沒有提供 token
fetch('/v1/tts/tasks')
// → 401 Unauthorized

// ✅ 正確：提供 token
fetch('/v1/tts/tasks', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
})
```

## 🧪 測試

### 1. 測試權限隔離

```bash
# 註冊兩個用戶
curl -X POST http://localhost:8000/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user1@test.com","password":"password123"}'

curl -X POST http://localhost:8000/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user2@test.com","password":"password123"}'

# User1 創建一個 task
# 然後用 User2 的 token 嘗試訪問
# 應該得到 404 Not Found
```

### 2. 測試查詢過濾

```bash
# User1 登入並創建 tasks
TOKEN1=$(curl -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user1@test.com","password":"password123"}' \
  | jq -r '.access_token')

# User2 登入
TOKEN2=$(curl -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user2@test.com","password":"password123"}' \
  | jq -r '.access_token')

# User1 查看 tasks（應該只看到自己的）
curl http://localhost:8000/v1/tts/tasks \
  -H "Authorization: Bearer $TOKEN1"

# User2 查看 tasks（應該只看到自己的）
curl http://localhost:8000/v1/tts/tasks \
  -H "Authorization: Bearer $TOKEN2"
```

## 📝 回滾計畫

如果遷移出現問題，可以回滾：

```sql
-- 恢復備份
DROP TABLE tasks;
ALTER TABLE tasks_backup RENAME TO tasks;
```

或使用 Python 腳本中的自動回滾機制（遷移失敗時會自動執行）。

## ✅ 檢查清單

遷移前：
- [ ] 備份現有資料庫
- [ ] 確認至少有一個用戶存在（user_id = 1）
- [ ] 記錄現有 tasks 數量

遷移後：
- [ ] 檢查 tasks 表結構（user_id 欄位存在）
- [ ] 檢查外鍵約束已建立
- [ ] 檢查索引已建立
- [ ] 測試 API 端點（需要認證）
- [ ] 測試權限隔離（用戶只能看到自己的 tasks）
- [ ] 清理 tasks_backup 表

## 🆘 常見問題

### Q: 遷移失敗，顯示 "FOREIGN KEY constraint failed"
A: 確保所有 tasks 的 user_id 都對應到存在的 users。檢查並手動修正。

### Q: 現有的 tasks 應該屬於誰？
A: 預設會指派給 user_id = 1。你可以修改遷移腳本或事後手動調整。

### Q: 可以跳過遷移直接刪除資料庫嗎？
A: 如果是開發環境且資料不重要，可以直接刪除 `./data/indextts.db` 重新開始。

### Q: 遷移後 API 測試失敗？
A: 確認所有 task 相關的 API 請求都包含了 `Authorization: Bearer <token>` header。

## 📚 相關文件

- [API_AUTH_DOCUMENTATION.md](API_AUTH_DOCUMENTATION.md) - API 認證流程說明
- [api/models/task.py](api/models/task.py) - Task 模型定義
- [api/models/user.py](api/models/user.py) - User 模型定義
