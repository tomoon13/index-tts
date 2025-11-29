# IndexTTS2 API 認證流程說明

## 🔐 認證方式

此 API 使用 **JWT (JSON Web Token)** 進行身份驗證，採用 Bearer Token 方式。

---

## 📍 API 端點

**Base URL**: `http://<HOST>:<PORT>` (預設: `http://localhost:8000`)

**API 文件**: `http://<HOST>:<PORT>/docs`

---

## 1️⃣ 使用者註冊

**端點**: `POST /v1/auth/register`

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "password123",
  "username": "myusername",      // 可選，3-50字元，僅限英數字、底線、連字號
  "displayName": "My Name"       // 可選，最多100字元
}
```

**密碼要求**:
- 最少 8 個字元
- 最多 100 個字元

**Response** (201 Created):
```json
{
  "accessToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "tokenType": "bearer",
  "expiresIn": 604800,  // 秒數 (預設7天)
  "user": {
    "id": 1,
    "email": "user@example.com",
    "username": "myusername",
    "displayName": "My Name",
    "isActive": true,
    "isVerified": false,
    "isAdmin": false,
    "totalGenerations": 0,
    "createdAt": "2025-01-29T10:30:00Z",
    "lastLoginAt": null
  }
}
```

**錯誤回應**:
- `400 Bad Request`: Email 已被註冊或 username 已被使用

---

## 2️⃣ 使用者登入

**端點**: `POST /v1/auth/login`

**Request Body**:
```json
{
  "identifier": "admin",
  "password": "test123"
}
```

或使用 email：
```json
{
  "identifier": "admin@example.com",
  "password": "test123"
}
```

> **說明**: `identifier` 欄位可以接受 **username** 或 **email**，系統會自動判斷

**Response** (200 OK):
```json
{
  "accessToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "tokenType": "bearer",
  "expiresIn": 604800,
  "user": {
    "id": 1,
    "email": "user@example.com",
    "username": "myusername",
    "displayName": "My Name",
    "isActive": true,
    "isVerified": false,
    "isAdmin": false,
    "totalGenerations": 5,
    "createdAt": "2025-01-29T10:30:00Z",
    "lastLoginAt": "2025-01-29T15:45:00Z"
  }
}
```

**錯誤回應**:
- `401 Unauthorized`: Username/Email 或密碼錯誤

---

## 3️⃣ 在後續請求中使用 Token

所有需要認證的端點（如 TTS 生成）都需要在 HTTP Header 中攜帶 token：

**Header**:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**範例 (使用 fetch)**:
```javascript
const token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...';

const response = await fetch('http://localhost:8000/v1/tts/generate', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
  },
  body: formData  // multipart/form-data
});
```

**範例 (使用 axios)**:
```javascript
const token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...';

const response = await axios.post(
  'http://localhost:8000/v1/tts/generate',
  formData,
  {
    headers: {
      'Authorization': `Bearer ${token}`,
    }
  }
);
```

---

## 4️⃣ 取得當前使用者資訊

**端點**: `GET /v1/auth/me`

**Headers**: 需要 Authorization

**Response** (200 OK):
```json
{
  "id": 1,
  "email": "user@example.com",
  "username": "myusername",
  "displayName": "My Name",
  "isActive": true,
  "isVerified": false,
  "isAdmin": false,
  "totalGenerations": 10,
  "createdAt": "2025-01-29T10:30:00Z",
  "lastLoginAt": "2025-01-29T15:45:00Z"
}
```

---

## 5️⃣ 驗證 Token 有效性

**端點**: `GET /v1/auth/verify`

**Headers**: 需要 Authorization

**Response** (200 OK):
```json
{
  "authenticated": true,
  "user_id": 1,
  "email": "user@example.com"
}
```

**用途**: 快速檢查 token 是否仍然有效

---

## 6️⃣ 修改密碼

**端點**: `POST /v1/auth/change-password`

**Headers**: 需要 Authorization

**Request Body**:
```json
{
  "currentPassword": "oldpassword123",
  "newPassword": "newpassword456"
}
```

**Response** (200 OK):
```json
{
  "message": "Password changed successfully"
}
```

**錯誤回應**:
- `400 Bad Request`: 當前密碼錯誤

---

## 🚫 錯誤處理

**401 Unauthorized** - 未提供 token 或 token 無效/過期:
```json
{
  "detail": "Not authenticated"
}
```
或
```json
{
  "detail": "Invalid or expired token"
}
```

**403 Forbidden** - 帳號已被停用:
```json
{
  "detail": "User account is deactivated"
}
```

---

## 🔧 前端實作建議

### 1. Token 儲存
```javascript
// 儲存 token
localStorage.setItem('access_token', response.data.access_token);
localStorage.setItem('user', JSON.stringify(response.data.user));

// 讀取 token
const token = localStorage.getItem('access_token');

// 清除 token (登出)
localStorage.removeItem('access_token');
localStorage.removeItem('user');
```

### 2. Axios 攔截器設定
```javascript
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000',
});

// 請求攔截器 - 自動加上 token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// 回應攔截器 - 處理 401 錯誤
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token 過期，清除並導向登入頁
      localStorage.removeItem('access_token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;
```

### 3. Token 過期處理
- Token 預設有效期: **7 天** (604800 秒)
- 建議在收到 401 錯誤時自動導向登入頁
- 或在 app 啟動時檢查 token 是否有效 (使用 `/v1/auth/verify`)

---

## ⚙️ 環境設定

後端可透過環境變數調整 JWT 設定：

```bash
# .env 檔案
JWT_SECRET_KEY=your-super-secret-key-here
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=10080  # 7天 = 60*24*7
```

---

## 📌 需要認證的端點

以下端點**必須**提供有效的 Authorization header:

- ✅ `POST /v1/tts/generate` - 生成語音
- ✅ `GET /v1/auth/me` - 取得使用者資訊
- ✅ `GET /v1/auth/verify` - 驗證 token
- ✅ `POST /v1/auth/change-password` - 修改密碼

以下端點**不需要**認證:

- ❌ `POST /v1/auth/register` - 註冊
- ❌ `POST /v1/auth/login` - 登入
- ❌ `GET /v1/health` - 健康檢查

---

## 📝 常見問題

### Q: Token 會過期嗎？
A: 是的，預設 7 天後過期。過期後需要重新登入取得新的 token。

### Q: 可以同時在多個裝置登入嗎？
A: 可以。每次登入都會生成新的 token，舊 token 在過期前仍然有效。

### Q: 忘記密碼怎麼辦？
A: 目前尚未實作忘記密碼功能，請聯繫管理員。

### Q: 如何登出？
A: 前端只需清除儲存的 token 即可。後端不需要特別的登出 API。

---

## 💡 前端整合範例

### 使用 Username 登入（推薦）

```javascript
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000',
  withCredentials: true,
});

// 使用 username 登入
async function loginWithUsername() {
  try {
    const response = await api.post('/v1/auth/login', {
      identifier: 'admin',      // 使用 username
      password: 'test123',
    });

    const { accessToken, user } = response.data;

    // 儲存 token
    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('user', JSON.stringify(user));

    console.log('Login successful:', user);
    return response.data;
  } catch (error) {
    console.error('Login failed:', error.response?.data?.detail);
    throw error;
  }
}

// 使用 email 登入
async function loginWithEmail() {
  try {
    const response = await api.post('/v1/auth/login', {
      identifier: 'admin@example.com',  // 使用 email
      password: 'test123',
    });

    return response.data;
  } catch (error) {
    console.error('Login failed:', error.response?.data?.detail);
    throw error;
  }
}
```

### 使用 Fetch API

```javascript
// Username 登入
async function login(identifier, password) {
  const response = await fetch('http://localhost:8000/v1/auth/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
    body: JSON.stringify({
      identifier,  // 可以是 username 或 email
      password,
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Login failed');
  }

  const data = await response.json();

  // 儲存 token
  localStorage.setItem('access_token', data.accessToken);
  localStorage.setItem('user', JSON.stringify(data.user));

  return data;
}

// 使用範例
login('admin', 'test123')
  .then(data => console.log('Logged in:', data.user))
  .catch(err => console.error('Login error:', err.message));
```

---

如需更多資訊，請訪問 Swagger 文件：`http://localhost:8000/docs`
