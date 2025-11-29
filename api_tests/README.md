# API Tests

此資料夾包含 API 相關的測試檔案。

## 說明

這些測試是針對 IndexTTS2 API 擴充功能的測試，與原始專案的 `tests/` 資料夾分開存放。

## 測試檔案

- `test_api.py` - 基礎 API 測試
- `test_api_new_params.py` - 新參數功能測試
- `test_audio_formats.py` - 音訊格式支援測試
- `test_request_logging.py` - 請求日誌測試
- `test_user_management.py` - 使用者管理 CRUD 測試

## 執行測試

```bash
# 執行所有 API 測試
uv run pytest api_tests/

# 執行特定測試
uv run python api_tests/test_user_management.py
```

## 注意事項

- 這些測試與原始 IndexTTS2 專案的 `tests/` 資料夾無關
- `tests/` 資料夾包含原始專案的 TTS 模型測試
- `api_tests/` 資料夾包含你的 API 擴充功能測試
