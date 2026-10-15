# 00000014. PHẠM VI REPOSITORY CÔNG KHAI

- **Trạng thái:** Chấp nhận
- **Ngày:** 2026-10-15

## 📌 BỐI CẢNH

Repository công khai cần cung cấp đủ nguồn để dùng, kiểm tra và đóng góp tài nguyên cộng đồng, đồng thời có ranh giới rõ ràng với dữ liệu vận hành nội bộ.

## ✅ QUYẾT ĐỊNH

Phạm vi gồm hồ sơ tổ chức, tài liệu cộng đồng, biểu mẫu, workflow mẫu, nhãn, mẫu ruleset và công cụ kiểm tra, sinh mẫu, phát hành. Người duy trì và actor trong mẫu ruleset là thông tin công khai để đối chiếu quy trình đóng góp.

Không đưa cấu hình vận hành thực tế, danh mục repository riêng tư, dữ liệu team và quyền nội bộ hoặc bộ công cụ nhập, sao lưu, đồng bộ tổ chức vào dự án.

`scripts/rulesets.py` kiểm tra và sinh mẫu tại máy. `scripts/github.py` hỗ trợ GitHub CLI cho quy trình phát hành. Validator kiểm tra các tệp và điểm khởi chạy nằm ngoài phạm vi công khai. Việc áp dụng mẫu lên GitHub thuộc trách nhiệm người quản trị trong từng phạm vi được chọn.

Nguồn của quyết định: [scripts/validation/repository.py](../../scripts/validation/repository.py), [scripts/rulesets.py](../../scripts/rulesets.py), [scripts/github.py](../../scripts/github.py), [AGENTS.md](../../AGENTS.md).

## 🔍 PHƯƠNG ÁN ĐÃ CÂN NHẮC

Nguồn công khai phục vụ tệp cộng đồng mặc định và workflow dùng script tổ chức. Phân định theo chức năng giúp người sử dụng biết tài nguyên nào có thể áp dụng, đồng thời tránh công bố dữ liệu không cần cho bộ tài nguyên.

## ⚖️ HỆ QUẢ

Thay đổi được kiểm tra tại máy và đánh giá qua PR. Người quản trị xác minh cấu hình thực tế sau khi áp dụng mẫu; sự tồn tại của tệp JSON hoặc YAML không chứng minh chính sách đã có hiệu lực trên GitHub.
