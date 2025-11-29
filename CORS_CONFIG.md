# CORS 跨域設定指南

## 問題說明

前端應用（例如運行在 `http://localhost:3000`）嘗試存取 API（運行在 `http://localhost:8000`）時，瀏覽器會因為**同源政策（Same-Origin Policy）** 而阻擋請求。

**錯誤訊息範例**：
```
Access to fetch at 'http://localhost:8000/v1/auth/login' from origin 'http://localhost:3000'
has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present on the
requested resource.
```

或看到：
```
OPTIONS /v1/auth/login HTTP/1.1" 405 Method Not Allowed
```

## 解決方案

API 已經配置好 CORS 支援，現在會自動處理跨域請求。

---

## 預設設定

**開發環境**（預設）：
- ✅ 允許所有來源 (`*`)
- ✅ 允許所有 HTTP 方法
- ✅ 允許所有 Headers
- ✅ 支援 Credentials（cookies, authorization headers）

**設定位置**: [api/config.py](api/config.py:23-27)

```python
CORS_ORIGINS: List[str] = ["*"]
CORS_ALLOW_CREDENTIALS: bool = True
CORS_ALLOW_METHODS: List[str] = ["*"]
CORS_ALLOW_HEADERS: List[str] = ["*"]
```

---

## 生產環境設定

⚠️ **重要**：生產環境不應該允許所有來源！

### 方法 1: 環境變數（推薦）

建立 `.env` 檔案：

```bash
# CORS 設定
CORS_ORIGINS=["https://your-frontend.com","https://www.your-frontend.com"]
CORS_ALLOW_CREDENTIALS=true
CORS_ALLOW_METHODS=["GET","POST","PUT","PATCH","DELETE","OPTIONS"]
CORS_ALLOW_HEADERS=["*"]
```

**多個域名設定**：
```bash
# JSON 陣列格式
CORS_ORIGINS=["https://app.example.com","https://admin.example.com","https://example.com"]
```

### 方法 2: 修改 config.py

編輯 `api/config.py`：

```python
class Settings(BaseSettings):
    # CORS settings
    CORS_ORIGINS: List[str] = [
        "https://your-frontend.com",
        "https://www.your-frontend.com",
    ]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    CORS_ALLOW_HEADERS: List[str] = ["Content-Type", "Authorization"]
```

---

## 常見場景設定

### 場景 1: 本地開發（前端 + 後端）

前端在 `http://localhost:3000`，後端在 `http://localhost:8000`

**.env**:
```bash
CORS_ORIGINS=["http://localhost:3000"]
```

或允許所有 localhost 端口：
```bash
CORS_ORIGINS=["*"]  # 開發環境可以這樣設定
```

### 場景 2: 前端部署在不同域名

前端：`https://app.mysite.com`
後端：`https://api.mysite.com`

**.env**:
```bash
CORS_ORIGINS=["https://app.mysite.com"]
```

### 場景 3: 多個前端應用

主站 + 管理後台

**.env**:
```bash
CORS_ORIGINS=["https://mysite.com","https://admin.mysite.com","https://mobile.mysite.com"]
```

### 場景 4: 支援子域名

**.env**:
```bash
# 方法 1: 明確列出
CORS_ORIGINS=["https://app.example.com","https://admin.example.com"]

# 方法 2: 允許所有（不安全，僅開發用）
CORS_ORIGINS=["*"]
```

---

## CORS 參數說明

### `CORS_ORIGINS`
**允許的來源列表**

```python
# 允許特定域名
CORS_ORIGINS = ["https://example.com"]

# 允許多個域名
CORS_ORIGINS = ["https://example.com", "https://app.example.com"]

# 允許所有來源（僅開發用）
CORS_ORIGINS = ["*"]
```

### `CORS_ALLOW_CREDENTIALS`
**是否允許發送 Cookies 和 Authorization Headers**

```python
# 允許（需要時設為 True，如 JWT token）
CORS_ALLOW_CREDENTIALS = True

# 不允許
CORS_ALLOW_CREDENTIALS = False
```

⚠️ **注意**：當設為 `True` 時，`CORS_ORIGINS` 不能使用 `["*"]`，必須明確指定域名。

### `CORS_ALLOW_METHODS`
**允許的 HTTP 方法**

```python
# 允許所有方法
CORS_ALLOW_METHODS = ["*"]

# 僅允許特定方法
CORS_ALLOW_METHODS = ["GET", "POST", "OPTIONS"]

# API 常用方法
CORS_ALLOW_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
```

### `CORS_ALLOW_HEADERS`
**允許的 HTTP Headers**

```python
# 允許所有 headers
CORS_ALLOW_HEADERS = ["*"]

# 僅允許特定 headers
CORS_ALLOW_HEADERS = ["Content-Type", "Authorization"]

# 常用 headers
CORS_ALLOW_HEADERS = [
    "Content-Type",
    "Authorization",
    "X-Requested-With",
    "Accept",
]
```

---

## 前端整合範例

### JavaScript Fetch

```javascript
// 登入請求
const response = await fetch('http://localhost:8000/v1/auth/login', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  credentials: 'include', // 重要：允許發送 cookies
  body: JSON.stringify({
    email: 'user@example.com',
    password: 'password123',
  }),
});

// 帶 token 的請求
const response = await fetch('http://localhost:8000/v1/tts/generate', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
  },
  credentials: 'include',
  body: formData,
});
```

### Axios

```javascript
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000',
  withCredentials: true, // 重要：允許發送 cookies
});

// 登入
const response = await api.post('/v1/auth/login', {
  email: 'user@example.com',
  password: 'password123',
});

// 帶 token 的請求
api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
const response = await api.get('/v1/auth/me');
```

---

## 檢查 CORS 設定

### 測試 CORS

```bash
# 測試 OPTIONS preflight request
curl -X OPTIONS http://localhost:8000/v1/auth/login \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -v

# 檢查回應 headers
# 應該看到：
# Access-Control-Allow-Origin: http://localhost:3000
# Access-Control-Allow-Methods: POST, OPTIONS, ...
# Access-Control-Allow-Headers: Content-Type, ...
```

### 瀏覽器開發者工具

1. 開啟 Chrome DevTools (F12)
2. 切換到 Network 標籤
3. 執行 API 請求
4. 查看 Response Headers：
   ```
   Access-Control-Allow-Origin: http://localhost:3000
   Access-Control-Allow-Credentials: true
   Access-Control-Allow-Methods: DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT
   Access-Control-Allow-Headers: *
   ```

---

## 故障排除

### 問題 1: CORS 錯誤仍然出現

**檢查清單**：
1. ✅ 重新啟動 API 服務器
2. ✅ 確認 `.env` 檔案格式正確
3. ✅ 清除瀏覽器快取
4. ✅ 確認前端 origin 在 `CORS_ORIGINS` 列表中

**檢查當前設定**：
```bash
# 查看 API 啟動日誌，確認 CORS 設定已載入
uv run python run_api.py
```

### 問題 2: `CORS_ORIGINS` 環境變數無效

**.env 格式錯誤**：
```bash
# ❌ 錯誤
CORS_ORIGINS=https://example.com,https://app.example.com

# ✅ 正確（JSON 陣列格式）
CORS_ORIGINS=["https://example.com","https://app.example.com"]
```

### 問題 3: 405 Method Not Allowed

**原因**: 瀏覽器發送 OPTIONS 預檢請求，但路由不支援

**解決**: CORS middleware 已經自動處理，重啟服務即可。

### 問題 4: Credentials 無法發送

**前端設定**：
```javascript
// Fetch
credentials: 'include'

// Axios
withCredentials: true
```

**後端設定**：
```bash
CORS_ALLOW_CREDENTIALS=true
# 且不能使用 CORS_ORIGINS=["*"]
```

---

## 安全建議

### ⚠️ 開發環境
```bash
# 可以使用寬鬆設定
CORS_ORIGINS=["*"]
CORS_ALLOW_CREDENTIALS=true
CORS_ALLOW_METHODS=["*"]
CORS_ALLOW_HEADERS=["*"]
```

### ✅ 生產環境
```bash
# 必須明確指定來源
CORS_ORIGINS=["https://your-production-domain.com"]
CORS_ALLOW_CREDENTIALS=true

# 限制允許的方法
CORS_ALLOW_METHODS=["GET","POST","PUT","PATCH","DELETE","OPTIONS"]

# 限制允許的 headers（或使用 "*" 如果需要彈性）
CORS_ALLOW_HEADERS=["Content-Type","Authorization"]
```

### 最佳實踐

1. **永遠不要在生產環境使用 `["*"]`**
2. **明確列出所有允許的域名**
3. **使用 HTTPS**
4. **定期審查 CORS 設定**
5. **記錄 CORS 錯誤並監控**

---

## 相關文件

- [MDN - CORS](https://developer.mozilla.org/zh-TW/docs/Web/HTTP/CORS)
- [FastAPI - CORS](https://fastapi.tiangolo.com/tutorial/cors/)
- [API_AUTH_DOCUMENTATION.md](API_AUTH_DOCUMENTATION.md) - API 認證
