# User Management Guide

## 概述

此 API 提供完整的使用者管理功能（CRUD），僅限管理員使用。

## 預設管理員帳號

系統啟動時會自動建立預設管理員帳號：

```
Email: admin@example.com
Password: test123
Username: admin
```

⚠️ **重要**: 請在正式環境中立即修改此密碼！

---

## 🔐 認證要求

所有使用者管理端點都需要：
1. **有效的 JWT Token**
2. **管理員權限** (`isAdmin: true`)

### 取得 Admin Token

```bash
curl -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "test123"
  }'
```

回應：
```json
{
  "accessToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "tokenType": "bearer",
  "expiresIn": 604800,
  "user": {
    "id": 1,
    "email": "admin@example.com",
    "username": "admin",
    "isAdmin": true,
    ...
  }
}
```

---

## 📋 API 端點

### 1. 列出所有使用者

**端點**: `GET /v1/users`

**Query Parameters**:
- `page`: 頁碼（從 1 開始，預設: 1）
- `pageSize`: 每頁筆數（1-100，預設: 20）

**範例**:
```bash
curl http://localhost:8000/v1/users?page=1&pageSize=20 \
  -H "Authorization: Bearer <admin-token>"
```

**回應**:
```json
{
  "users": [
    {
      "id": 1,
      "email": "admin@example.com",
      "username": "admin",
      "displayName": "Administrator",
      "isActive": true,
      "isVerified": true,
      "isAdmin": true,
      "totalGenerations": 0,
      "createdAt": "2025-01-29T10:00:00Z",
      "lastLoginAt": "2025-01-29T15:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "pageSize": 20
}
```

---

### 2. 建立新使用者

**端點**: `POST /v1/users`

**Request Body**:
```json
{
  "email": "newuser@example.com",
  "password": "password123",
  "username": "newuser",          // 可選
  "displayName": "New User",      // 可選
  "isAdmin": false,               // 可選，預設 false
  "isVerified": false             // 可選，預設 false
}
```

**範例**:
```bash
curl -X POST http://localhost:8000/v1/users \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepass123",
    "username": "user1",
    "displayName": "User One",
    "isVerified": true
  }'
```

**回應** (201 Created):
```json
{
  "id": 2,
  "email": "user@example.com",
  "username": "user1",
  "displayName": "User One",
  "isActive": true,
  "isVerified": true,
  "isAdmin": false,
  "totalGenerations": 0,
  "createdAt": "2025-01-29T16:00:00Z",
  "lastLoginAt": null
}
```

---

### 3. 取得使用者詳情

**端點**: `GET /v1/users/{user_id}`

**範例**:
```bash
curl http://localhost:8000/v1/users/2 \
  -H "Authorization: Bearer <admin-token>"
```

**回應**:
```json
{
  "id": 2,
  "email": "user@example.com",
  "username": "user1",
  "displayName": "User One",
  "isActive": true,
  "isVerified": true,
  "isAdmin": false,
  "totalGenerations": 5,
  "createdAt": "2025-01-29T16:00:00Z",
  "lastLoginAt": "2025-01-29T17:00:00Z"
}
```

---

### 4. 更新使用者

**端點**: `PATCH /v1/users/{user_id}`

**Request Body** (所有欄位都是可選的):
```json
{
  "email": "newemail@example.com",
  "username": "newusername",
  "displayName": "New Display Name",
  "isActive": true,
  "isVerified": true,
  "isAdmin": false
}
```

**範例**:
```bash
curl -X PATCH http://localhost:8000/v1/users/2 \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "displayName": "Updated User Name",
    "isVerified": true
  }'
```

**回應**:
```json
{
  "id": 2,
  "email": "user@example.com",
  "displayName": "Updated User Name",
  "isVerified": true,
  ...
}
```

---

### 5. 設定使用者密碼

**端點**: `POST /v1/users/{user_id}/password`

**Request Body**:
```json
{
  "newPassword": "newsecurepass123"
}
```

**範例**:
```bash
curl -X POST http://localhost:8000/v1/users/2/password \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "newPassword": "newpass123456"
  }'
```

**回應**:
```json
{
  "message": "Password updated successfully"
}
```

---

### 6. 刪除使用者

**端點**: `DELETE /v1/users/{user_id}`

**⚠️ 警告**:
- 此操作無法復原
- 會同時刪除使用者的所有 tasks（CASCADE）
- 管理員無法刪除自己的帳號

**範例**:
```bash
curl -X DELETE http://localhost:8000/v1/users/2 \
  -H "Authorization: Bearer <admin-token>"
```

**回應**:
```json
{
  "message": "User user@example.com deleted successfully"
}
```

---

## 🚫 錯誤回應

### 403 Forbidden - 非管理員嘗試訪問
```json
{
  "detail": "Admin access required"
}
```

### 404 Not Found - 使用者不存在
```json
{
  "detail": "User not found"
}
```

### 400 Bad Request - Email 或 Username 已存在
```json
{
  "detail": "Email already registered"
}
```
或
```json
{
  "detail": "Username already taken"
}
```

### 400 Bad Request - 嘗試刪除自己
```json
{
  "detail": "Cannot delete your own account"
}
```

---

## 🧪 測試

運行測試腳本：

```bash
# 確保 API 服務正在運行
uv run python run_api.py

# 在另一個終端運行測試
python test_user_management.py
```

---

## 📊 資料庫 Schema

### Users 表結構

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    username VARCHAR(50) UNIQUE,
    display_name VARCHAR(100),
    is_active BOOLEAN NOT NULL DEFAULT 1,
    is_verified BOOLEAN NOT NULL DEFAULT 0,
    is_admin BOOLEAN NOT NULL DEFAULT 0,
    last_login_at TIMESTAMP,
    total_generations INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
```

### User-Task 關聯

每個 Task 都必須關聯到一個 User：

```sql
CREATE TABLE tasks (
    id VARCHAR(32) PRIMARY KEY,
    user_id INTEGER NOT NULL,
    ...
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

刪除 User 時，其所有 Tasks 會被自動刪除（CASCADE）。

---

## 🔧 前端整合範例

### JavaScript/TypeScript

```typescript
class UserManagementAPI {
  constructor(private baseURL: string, private adminToken: string) {}

  async listUsers(page: number = 1, pageSize: number = 20) {
    const response = await fetch(
      `${this.baseURL}/v1/users?page=${page}&pageSize=${pageSize}`,
      {
        headers: {
          Authorization: `Bearer ${this.adminToken}`,
        },
      }
    );
    return response.json();
  }

  async createUser(userData: {
    email: string;
    password: string;
    username?: string;
    displayName?: string;
    isAdmin?: boolean;
    isVerified?: boolean;
  }) {
    const response = await fetch(`${this.baseURL}/v1/users`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${this.adminToken}`,
      },
      body: JSON.stringify(userData),
    });
    return response.json();
  }

  async updateUser(userId: number, updates: Partial<{
    email: string;
    username: string;
    displayName: string;
    isActive: boolean;
    isVerified: boolean;
    isAdmin: boolean;
  }>) {
    const response = await fetch(`${this.baseURL}/v1/users/${userId}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${this.adminToken}`,
      },
      body: JSON.stringify(updates),
    });
    return response.json();
  }

  async deleteUser(userId: number) {
    const response = await fetch(`${this.baseURL}/v1/users/${userId}`, {
      method: 'DELETE',
      headers: {
        Authorization: `Bearer ${this.adminToken}`,
      },
    });
    return response.json();
  }
}

// 使用範例
const api = new UserManagementAPI('http://localhost:8000', adminToken);

// 列出使用者
const users = await api.listUsers(1, 20);

// 建立使用者
const newUser = await api.createUser({
  email: 'test@example.com',
  password: 'securepass123',
  displayName: 'Test User',
  isVerified: true,
});

// 更新使用者
await api.updateUser(2, { displayName: 'Updated Name' });

// 刪除使用者
await api.deleteUser(2);
```

---

## 🔒 安全最佳實踐

1. **立即更改預設管理員密碼**
   ```bash
   # 登入後使用 change-password API
   curl -X POST http://localhost:8000/v1/auth/change-password \
     -H "Authorization: Bearer <admin-token>" \
     -H "Content-Type: application/json" \
     -d '{
       "currentPassword": "test123",
       "newPassword": "your-secure-password-here"
     }'
   ```

2. **設定強密碼策略**
   - 最少 8 個字元
   - 建議包含大小寫字母、數字、特殊符號

3. **定期審查管理員帳號**
   - 列出所有管理員：`GET /v1/users?pageSize=100` 並過濾 `isAdmin: true`
   - 移除不再需要的管理員權限

4. **使用 HTTPS**
   - 正式環境務必使用 HTTPS
   - 考慮使用 Nginx 或 Caddy 作為反向代理

5. **設定環境變數**
   ```bash
   # .env
   JWT_SECRET_KEY=your-very-secure-random-string-here
   JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440  # 1天
   ```

---

## 📝 相關文件

- [API_AUTH_DOCUMENTATION.md](API_AUTH_DOCUMENTATION.md) - API 認證流程
- [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) - 資料庫遷移指南
