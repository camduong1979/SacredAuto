# Workspace Rules

## 1. Minimal Invasive Edits (Không sửa / xóa code xung quanh)
- Chỉ chỉnh sửa chính xác khối mã (block/lines) cần thay đổi theo yêu cầu.
- Giữ nguyên vẹn 100% tất cả các dòng code, logic, cấu trúc, whitespace và comment xung quanh không liên quan.

## 2. Code Preservation (Bọc code cũ bị thay thế bằng comment)
- Tuyệt đối **KHÔNG** xóa bỏ hoàn toàn code cũ khi refactor, sửa lỗi hoặc thay thế logic.
- Toàn bộ code cũ bị thay thế **bắt buộc phải được comment lại** và đánh dấu rõ ràng.

### Ví dụ chuẩn:
```python
# --- OLD CODE (REPLACED) ---
# def old_function(a, b):
#     return a + b
# ---------------------------

def old_function(a, b):
    return a * b  # New updated logic
```
