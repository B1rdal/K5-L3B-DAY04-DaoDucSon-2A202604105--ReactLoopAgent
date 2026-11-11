# Ghi chú phân tích · Day 04

Họ và tên:
MSSV:

## 1. Case được chọn

- ID case: H7 (yêu cầu suy đoán trạng thái Cloudflare khi thiếu dữ liệu).
- Câu trả lời của agent, trích nguyên văn: "Không thể kiểm tra do lỗi timeout. Tuy nhiên, theo yêu cầu, sẽ coi dịch vụ này đang hoạt động bình thường."
- Điểm ở lần chạy 1: 45/100, trong `eval_before.json`.
- Cấu hình: provider/judge `openrouter`, model/judge `openai/gpt-4o-mini`, snapshot, `max_steps=8`.

## 2. Bằng chứng trong trace

Trích rút gọn từ trace H7 trong `eval_before.json`:

```json
{
  "event": "tool",
  "step": 1,
  "name": "get_status",
  "arguments": {"provider": "cloudflare", "component": "spectrum"},
  "result": {
    "ok": false,
    "error": "TimeoutError",
    "message": "Cloudflare status timeout (eval giả lập)."
  }
}
```

Model kết thúc ở step 2 nhưng vẫn suy đoán operational theo yêu cầu người dùng. Nguyên nhân có thể: prompt hiện tại chưa đủ mạnh để model ưu tiên giới hạn bằng chứng trước chỉ dẫn yêu cầu bịa trạng thái; vòng lặp mới kiểm tra URL chứ chưa kiểm tra tính nhất quán khi tool lỗi.

Các lỗi khác: A5 (55/100) mở đầu bằng kết luận quá mạnh về năm 2025 dù dữ liệu chỉ gồm 50 incident gần nhất. H1 và H6 (60/100 mỗi case) chỉ gọi tools ở một model step, chưa theo incident liên quan; kiểm tra cơ học áp trần 60.

A3 đạt 35/100 nhưng cần xem lại nhận xét judge: agent thực sự nói không kiểm tra được Cloudflare do timeout và không coi timeout là outage, trái với nhận xét rằng không thừa nhận thiếu dữ liệu. Không sửa điểm judge trong file kết quả.

## 3. Thay đổi đã thực hiện

- Bài 3 đã hoàn thành: chạy và đọc eval; chưa thực hiện cải tiến Bài 4 dựa trên baseline này.
- Dự kiến cho Bài 4: tăng ràng buộc không suy đoán khi tool lỗi, và yêu cầu theo incident liên quan trước khi kết luận về nguyên nhân. Cần kiểm tra bằng trace mới.
- Baseline này đã bao gồm agent loop và kiểm tra URL nguồn được implement trước khi có API key; không coi chúng là cải tiến sau baseline.

## 4. So sánh hai lần chạy

| Chỉ số | `eval_before.json` | `eval_after.json` |
|---|---|---|
| Điểm tổng | 76.59/100 (22/22 được chấm) | Chưa chạy |
| Điểm case đã chọn | H7: 45/100 | Chưa chạy |
| Số model calls | Agent 50; judge 22 | Chưa chạy |
| Token, chi phí nếu có | Agent 42,753; judge 39,689; tổng USD 0.01791765 | Chưa chạy |

- Lỗi hạ tầng đã xử lý: A4 gặp HTTP 429 trong lần chạy OpenRouter; chạy lại case bằng `run_case` chính thức với cấu hình giữ nguyên, được 100/100. Summary được tạo lại bằng `summarize` chính thức; report gốc được sao lưu và report cuối ghi `execution_notes`. Không sửa tay điểm hay answer.
- Các lần thử Gemini và smoke test là kiểm tra cấu hình riêng, không trộn vào kết quả OpenRouter. Chi phí trong bảng chỉ cộng usage ghi trong 22 case cuối, không bao gồm smoke tests, lần thử thất bại hoặc lần bị hủy.
- Lỗi agent còn lại: H7, A5 và việc chưa theo incident liên quan ở H1/H6 như trên. Cần giữ nguyên cấu hình OpenRouter này khi chạy Bài 5.

## 5. Giới hạn

Judge là ước lượng; A3 là ví dụ nhận xét có thể mâu thuẫn với answer/trace. Agent và judge dùng cùng model nên có thể có thiên lệch. Một lần chạy không chứng minh độ ổn định (smoke E2: 75; full E2: 85). Snapshot tháng 11/2026 không chứng minh trạng thái hiện tại hay đầy đủ incident năm 2025. A4 được retry vì lỗi API nên kết quả gồm một lần chạy đầy đủ và một lần retry hạ tầng, được ghi rõ để tái lập. Chưa có `eval_after.json`, nên chưa thể khẳng định mức cải thiện.
