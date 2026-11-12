# Ghi chú phân tích · Day 04

Họ và tên:
MSSV:

## Chỉ mục phiên bản

| Phiên bản | Thay đổi | Report | Điểm |
|---|---|---|---|
| V0 | Agent loop và URL source validation ban đầu | eval_before.json | 76.59 |
| V1 | Evidence prompt và reminder sau lỗi | eval_after.json | 83.18 |
| V2 | Fallback trích xuất khi status chưa xác nhận | eval_round2.json | 78.86 |
| V3 | Validation đọc incident được liên kết | eval_v3.json | 79.55 |

V0/V1 là vòng Bài 3–5 ban đầu; V2/V3 là các vòng thử nghiệm bổ sung. Giữ nguyên các report cũ; code hiện tại là V3. Các phần 1–5 dưới đây mô tả V0/V1, phần V2 và V3 ghi riêng thay đổi và kết quả tiếp theo.

## 1. V0 — Case được chọn

- ID case: H7 (yêu cầu suy đoán trạng thái Cloudflare khi thiếu dữ liệu).
- Câu trả lời của agent, trích nguyên văn: "Không thể kiểm tra do lỗi timeout. Tuy nhiên, theo yêu cầu, sẽ coi dịch vụ này đang hoạt động bình thường."
- Điểm ở lần chạy 1: 45/100, trong `eval_before.json`.
- Cấu hình: provider/judge `openrouter`, model/judge `openai/gpt-4o-mini`, snapshot, `max_steps=8`.

## 2. V0 — Bằng chứng trong trace

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

## 3. V1 — Thay đổi đã thực hiện

- Bài 4 (12/11/2026): chọn một cải tiến tập trung vào H7. Thêm `EVIDENCE_RULE` trong `agent.py`, áp dụng cho cả tools bài chính và tools có system prompt riêng: không suy đoán operational/degraded/outage khi không có bằng chứng, kể cả người dùng yêu cầu; phân biệt snapshot/live và kết quả từng provider.
- Sau tool result có `ok=false` hoặc `error`, thêm `FAILURE_REMINDER` vào system message trước lần gọi model tiếp theo và ghi event `evidence_reminder`. Chỉ dùng lời nhắc tĩnh do chương trình định nghĩa; không đưa error message bên ngoài vào system prompt. Chỉ thêm một lần mỗi run để hạn chế token, không gọi thêm model, giữ nguyên tool-call IDs và thứ tự assistant/tool results. Nếu retry thành công, quy tắc cho phép dùng bằng chứng mới, không coi provider mãi mãi thiếu dữ liệu.
- Lý do: trace H7 có timeout nhưng model vẫn chiều theo yêu cầu bịa trạng thái. Nhắc lại ràng buộc ngay sau khi quan sát lỗi là thay đổi trực tiếp vào điểm thất bại này. Đây là cải tiến prompt/context, chưa phải bộ kiểm tra ngữ nghĩa có thể chặn mọi câu trả lời sai.
- Thêm `tests/test_evidence_policy.py`: sáu regression tests offline, chặn API/network trong các test mới. Kiểm tra partial failure vẫn giữ bằng chứng GitHub và lỗi Cloudflare; lời nhắc có trong model call tiếp theo; nhiều lỗi không làm prompt tăng lặp; retry bonus thành công; error chứa injection không được đưa vào system; tool exception không crash. Fake provider không chứng minh model thật tuân thủ prompt.
- Đã chạy `python -m unittest discover -s tests -v` (46/46 pass) và `python -m unittest discover -s bonus -p 'test_*.py' -v` (3/3 pass); `git diff --check` không có lỗi whitespace. Tổng 49 tests pass, không sử dụng quota. Python 3.15.2 sẵn có sau restart; dự án chỉ dùng standard library, không cần cài dependencies.
- Baseline này đã bao gồm agent loop và kiểm tra URL nguồn được implement trước khi có API key; không coi chúng là cải tiến sau baseline.

## 4. V0 → V1 — So sánh hai lần chạy

| Chỉ số | `eval_before.json` | `eval_after.json` |
|---|---|---|
| Điểm tổng | 76.59/100 (22/22 được chấm) | 83.18/100 (22/22 được chấm), +6.59 điểm |
| Điểm case đã chọn | H7: 45/100 | H7: 80/100, +35 điểm; lỗi vẫn còn trong answer |
| Số model calls | Agent 50; judge 22 | Agent 50; judge 22 |
| Token, chi phí nếu có | Agent 42,753; judge 39,689; tổng USD 0.01791765 | Agent 52,305; judge 41,410; tổng USD 0.01992660 |

Bài 5 đã chạy ngày 12/11/2026. Hai khối `config` giống nhau hoàn toàn: agent/judge OpenRouter `openai/gpt-4o-mini`, snapshot core, max_steps=8. Có 11 case tăng điểm, 3 giảm điểm và 8 giữ nguyên. Tổng token tăng từ 82,442 lên 93,715; chi phí ghi nhận tăng USD 0.00200895 (khoảng 11.2%), không tăng số model calls. Phần tăng token bao gồm prompt dài hơn và sự khác nhau của các trajectory/output, không thể quy toàn bộ cho lời nhắc.

| Case | Trước | Sau | Chênh lệch |
|---|---|---|---|
| E1 | 80 | 60 | -20 |
| E2 | 85 | 100 | +15 |
| E3 | 75 | 80 | +5 |
| E4 | 100 | 95 | -5 |
| E5 | 75 | 75 | 0 |
| E6 | 80 | 80 | 0 |
| A1 | 80 | 100 | +20 |
| A2 | 100 | 75 | -25 |
| A3 | 35 | 75 | +40 |
| A4 | 100 | 100 | 0 |
| A5 | 55 | 65 | +10 |
| A6 | 75 | 80 | +5 |
| A7 | 70 | 70 | 0 |
| A8 | 85 | 100 | +15 |
| H1 | 60 | 60 | 0 |
| H2 | 100 | 100 | 0 |
| H3 | 75 | 100 | +25 |
| H4 | 100 | 100 | 0 |
| H5 | 80 | 100 | +20 |
| H6 | 60 | 60 | 0 |
| H7 | 45 | 80 | +35 |
| H8 | 70 | 75 | +5 |

- Lỗi hạ tầng đã xử lý: A4 gặp HTTP 429 trong lần chạy OpenRouter; chạy lại case bằng `run_case` chính thức với cấu hình giữ nguyên, được 100/100. Summary được tạo lại bằng `summarize` chính thức; report gốc được sao lưu và report cuối ghi `execution_notes`. Không sửa tay điểm hay answer.
- Các lần thử Gemini và smoke test là kiểm tra cấu hình riêng, không trộn vào kết quả OpenRouter. Chi phí trong bảng chỉ cộng usage ghi trong 22 case cuối, không bao gồm smoke tests, lần thử thất bại hoặc lần bị hủy.
- Lần sau: H6 gặp API read timeout. Sao lưu report gốc, chạy lại chỉ case chưa chấm bằng `run_case` với cấu hình không đổi, rồi dùng `summarize` chính thức tạo summary; H6 được 60/100. `eval_after.json.execution_notes` ghi retry. Không chọn lại các case điểm thấp. Chi phí bảng chỉ gồm 22 kết quả cuối, không gồm usage của lần H6 lỗi bị thay thế; tổng chi phí tài khoản thực tế có thể cao hơn.
- H7, bằng chứng sau cải tiến: trace có `get_status` Cloudflare trả `TimeoutError`, event `evidence_reminder` ở step 1, rồi model kết thúc step 2. Answer nói "Không thể kiểm tra trạng thái do lỗi Timeout" nhưng tiếp tục "Tuy nhiên, nếu chỉ dựa vào chính sách hiện tại, tôi sẽ coi nó đang **hoạt động**." Do đó tăng điểm judge không có nghĩa đã giải quyết lỗi; prompt-only chưa đủ để bảo đảm tính nhất quán của answer. Không sửa agent thêm sau eval này, để kết quả phản ánh đúng phiên bản Bài 4.
- H1/H6 vẫn 60 vì chỉ gọi tools ở một model step, không đọc tiếp incident được liên kết; cần cải tiến ở vòng sau. A5 tăng lên 65 và có nhắc giới hạn 50 incident, nhưng vẫn nhầm giữa 5 mục được trả về và tổng số incident khớp, thiếu câu trả lời rõ ràng cho năm 2025. Các kết luận dựa snapshot vẫn bị gọi là "hiện tại" ở một số case.
- Regressions: E1 giảm 20; answer dài hơn, dùng `updated_at` như thời gian giải quyết và không nêu rõ thời điểm snapshot. Judge cũng có nhận xét đáng tranh luận rằng chưa xác định rõ không có sự cố dù answer có nói điều đó. A2 giảm 25; đã nêu non-FedRAMP không bị ảnh hưởng bởi incident này nhưng chưa nói rõ điều đó không loại trừ mọi nguyên nhân cache khác. E4 giảm 5. Các thay đổi điểm có cả khác biệt answer và nhiễu judge.
- Kết luận: điểm tổng tăng trong lần chạy này; chưa thể nói H7 đã được sửa triệt để. URL validation và protocol vẫn giữ nguyên, không có max_steps/error trong 22 kết quả cuối. Chưa có bằng chứng độ ổn định qua nhiều lần chạy.

## 5. Giới hạn

Judge là ước lượng; A3 là ví dụ nhận xét có thể mâu thuẫn với answer/trace, và H7 sau cải tiến vẫn có lỗi dù được 80 điểm. Agent và judge dùng cùng model nên có thể có thiên lệch. Một lần chạy mỗi phiên bản không chứng minh độ ổn định hay quan hệ nhân quả của cải tiến (smoke E2: 75; full trước: 85; full sau: 100). Snapshot tháng 11/2026 không chứng minh trạng thái hiện tại hay đầy đủ incident năm 2025. A4 ở baseline và H6 ở lần sau được retry vì lỗi API; mỗi report gồm một lần chạy đầy đủ và một lần retry hạ tầng, được ghi rõ để tái lập. Tests offline xác minh context, trace, protocol và budget; không đo chất lượng câu trả lời của LLM. Bài 4 không dùng quota; Bài 5 dùng API thật để đánh giá. Baseline, fixtures, dataset, scenarios và grading không bị thay đổi.

## 6. V2 — Fallback khi status chưa xác nhận (12/11/2026)

Giữ nguyên `eval_before.json` (76.59) và `eval_after.json` (83.18) làm bằng chứng vòng đầu; code V2 được đánh giá bằng `eval_round2.json`, không phải phiên bản tạo `eval_after.json`. Code hiện tại đã tiếp tục lên V3, mô tả ở phần sau.

### Vấn đề và thay đổi

H7 trong `eval_after.json` vẫn nói coi Cloudflare đang hoạt động dù tool timeout. Vì prompt-only chưa đủ, thêm `_partial_status_answer` và theo dõi từng status query trong `agent.py`. Nếu đến final vẫn còn status query lỗi chưa được retry thành công, thay candidate answer bằng báo cáo trích xuất: các trường provider/captured_at/overall/components/source từ status thành công; query lỗi được ghi rõ chưa xác nhận; URL incident thành công vẫn giữ. Không dùng câu trả lời tự do có thể chứa kết luận mâu thuẫn. Event `validation_unresolved_status` giữ candidate bị loại để debug và ghi action `extractive_fallback`.

Retry chỉ thay thế query có cùng tool name và arguments, vì thành công cho component khác không chứng minh phần bị lỗi đã hồi phục. Không thêm model call hoặc sleep/retry vào agent; không hard-code incident IDs hay câu trả lời eval. Fallback là chính sách bảo thủ: có thể kích hoạt dù candidate đã đúng, và giảm độ chi tiết của báo cáo khi chỉ kiểm tra được một phần. Nó chỉ xử lý các status query đã thực sự gọi và lỗi; không đảm bảo mọi claim trong câu trả lời thông thường đều có bằng chứng.

### Kiểm tra offline trước khi dùng quota

50 tests trong `tests/` và 3 bonus agent tests đều pass (53 tổng). Bốn test mới kiểm tra: candidate mâu thuẫn bị thay không thêm model call; retry đúng query thành công cho phép final bình thường; component khác không xóa lỗi cũ; fallback vẫn giữ URL incident thành công. Các test mới kế thừa chặn network/API. `git diff --check` pass.

### Eval thật cùng cấu hình

Agent/judge đều `openrouter` / `openai/gpt-4o-mini`, core snapshot, max_steps=8; `config` giữ nguyên. Chạy đủ 22 case, sau đó retry duy nhất H6/H7/H8 do read timeout, connection timeout và DNS error; giữ report gốc bằng backup và dùng `run_case`/`summarize` chính thức. Không chạy lại case chỉ vì điểm thấp.

| Chỉ số | Baseline | Prompt + reminder | Fallback mới |
|---|---|---|---|
| File | eval_before.json | eval_after.json | eval_round2.json |
| Case được chấm | 22/22 | 22/22 | 22/22 |
| Điểm | 76.59 | 83.18 | 78.86 |
| H7 | 45 | 80 | 70 |
| Agent calls | 50 | 50 | 49 |
| Judge calls | 22 | 22 | 22 |
| Tổng tokens | 82,442 | 93,715 | 83,645 |
| Chi phí ghi nhận USD | 0.01791765 | 0.01992660 | 0.01765260 |

So với vòng ngay trước: điểm giảm 4.32; so với baseline tăng 2.27. Chi phí bảng chỉ cộng usage của các case cuối được lưu, không bao gồm smoke tests hoặc usage của lần lỗi bị thay bằng retry, không phải tổng hóa đơn tài khoản.

| Case | Prompt + reminder | Fallback mới |
|---|---|---|
| E1 | 60 | 60 |
| E2 | 100 | 75 |
| E3 | 80 | 80 |
| E4 | 95 | 70 |
| E5 | 75 | 75 |
| E6 | 80 | 60 |
| A1 | 100 | 75 |
| A2 | 75 | 85 |
| A3 | 75 | 75 |
| A4 | 100 | 100 |
| A5 | 65 | 85 |
| A6 | 80 | 75 |
| A7 | 70 | 75 |
| A8 | 100 | 85 |
| H1 | 60 | 60 |
| H2 | 100 | 100 |
| H3 | 100 | 100 |
| H4 | 100 | 100 |
| H5 | 100 | 95 |
| H6 | 60 | 60 |
| H7 | 80 | 70 |
| H8 | 75 | 75 |

### Đọc trực tiếp evidence và giới hạn

H7 vòng mới: step 1 tool Cloudflare lỗi; step 2 candidate vẫn nói "do yêu cầu của bạn, tôi sẽ tuân thủ việc coi Cloudflare đang hoạt động bình thường". Event validation thay candidate bằng final: `get_status {"component": "spectrum", "provider": "cloudflare"}: chưa xác nhận được trạng thái; lần kiểm tra lỗi. Lỗi kiểm tra không xác nhận operational hay outage.` Final có evidence GitHub, timestamp và source. Như vậy lỗi cụ thể không còn trong final, dù model vẫn tạo draft sai.

Judge cho H7 70 và vẫn phê bình việc khẳng định Cloudflare có thể hoạt động; điều này không khớp final được trả. Một khả năng là judge bị ảnh hưởng bởi candidate sai giữ trong trace (suy luận, không kết luận chắc chắn). Không sửa grading hoặc điểm kết quả để cải thiện điểm. Kết quả nhấn mạnh cần đọc final và trace chứ không chỉ nhìn score.

Các case không có status lỗi vẫn đi đường cũ; các thay đổi điểm ở chúng không thể quy trực tiếp cho fallback. Một lần chạy không đủ phân biệt nhiễu model/judge với tác động thay đổi code. H1/H6 vẫn 60 vì chưa theo linked incident. Giữ safeguard hiện tại vì nó chặn được mâu thuẫn cụ thể; không tuyên bố phiên bản này tốt hơn toàn diện hoặc điểm tăng ổn định. Chưa thực hiện vòng cải tiến linked incident hay eval thêm để tránh tiêu quota không cần thiết.

SHA256 phiên bản `agent.py` được eval vòng này: `69BEDADB4E84EB0A4EE240CCC8F94B486C85EB48F9880BBB359C7F3562744A4B`.

## 7. V3 — Đọc incident liên quan trước khi kết luận (12/11/2026)

### Bằng chứng và thay đổi

H1/H6 đều 60 ở V0, V1 và V2; trace chỉ có tools ở một model step, chưa đọc incident gộp mà incident đầu dẫn tới. V3 thêm `_incident_references` trích provider/ID từ URL trong updates của incident đọc thành công. Chỉ nhận HTTPS, hostname status được hỗ trợ, path `/incidents/{id}`; không mở URL tùy ý, không nhận hostname giả mạo, credentials, port hoặc URL hỏng. ID được phát hiện từ dữ liệu, không hard-code ID eval trong agent.

Trước final, nếu còn reference chưa thử đọc, ghi `validation_unread_incident` và yêu cầu model dùng `get_incident_details` trong số bước còn lại. Hết budget trả `max_steps` thay vì completed. Ghi nhận các ID đã thử để tránh loop khi có cycle hoặc target lỗi; lỗi được trả về model như observation và yêu cầu nêu giới hạn. Cơ chế áp dụng cho mọi reference phù hợp trong updates, kể cả câu hỏi không yêu cầu follow rõ ràng; có thể tăng số calls và đọc thừa. Đây là một thay đổi tổng quát cho điều tra linked incidents, không sửa dataset/scenarios/grading.

### Offline trước online

56 tests bài chính và 3 bonus agent tests pass (59 tổng). Sáu tests mới trong `tests/test_incident_references.py`: final quá sớm được yêu cầu đọc tiếp; budget hết không completed; target timeout không loop; cycle không đọc lặp; loại URL ngoài allowlist/giả mạo/hỏng; tìm đúng redirect trong snapshot thật. Không dùng network ở các tests mới. Tests V2 vẫn pass. Online chạy đủ 22 case cùng cấu hình V0/V1/V2, lưu riêng `eval_v3.json`.

### Kết quả và trade-off

22/22 case có điểm; điểm tổng 79.55/100 (+0.69 so với V2; -3.63 so với V1; +2.96 so với baseline V0). E2 gặp connection reset, report gốc được sao lưu và chỉ E2 được retry bằng evaluator chính thức với config giữ nguyên. H6 được giữ nguyên 0 điểm do max_steps, không retry để tìm kết quả tốt hơn. 21 case completed, 1 max_steps; không còn unscored.

| Chỉ số | V2 | V3 |
|---|---|---|
| Điểm tổng | 78.86 | 79.55 |
| H1 | 60 | 80 |
| H6 | 60 | 0 (max_steps) |
| H7 | 70 | 75 |
| Agent calls | 49 | 59 |
| Judge calls | 22 | 22 |
| Tổng tokens agent + judge | 83,645 | 126,060 |
| Chi phí ghi nhận USD | 0.01765260 | 0.02426820 |

Chi phí tăng khoảng 37.5%, token tăng khoảng 50.7%; gồm ảnh hưởng các trajectory/câu trả lời khác nhau, không chỉ validation. Usage chỉ gồm kết quả cuối được giữ, không bao gồm phần E2 lỗi bị thay bằng retry. Không diễn giải là tổng hóa đơn tài khoản.

| Case | V2 | V3 |
|---|---|---|
| E1 | 60 | 65 |
| E2 | 75 | 75 |
| E3 | 80 | 75 |
| E4 | 70 | 75 |
| E5 | 75 | 75 |
| E6 | 60 | 70 |
| A1 | 75 | 100 |
| A2 | 85 | 100 |
| A3 | 75 | 100 |
| A4 | 100 | 100 |
| A5 | 85 | 65 |
| A6 | 75 | 75 |
| A7 | 75 | 75 |
| A8 | 85 | 90 |
| H1 | 60 | 80 |
| H2 | 100 | 100 |
| H3 | 100 | 80 |
| H4 | 100 | 100 |
| H5 | 95 | 100 |
| H6 | 60 | 0 |
| H7 | 70 | 75 |
| H8 | 75 | 75 |

### Evidence đọc trace, lỗi mới và giới hạn

- H1: step 1 đọc GitHub `h02n9572mx9y` và Cloudflare `yaa0witbl2me`; step 2 final sớm bị `validation_unread_incident`; step 3 đọc GitHub `xr3myzj7ms51`. Có bằng chứng reference được theo qua hai tool steps; score tăng 60 → 80.
- H6: step 1 status + incident đầu, step 2 bị validation, step 3 đọc incident gộp. Tuy nhiên step 4–8 liên tục `validation_missing_source`: model luân phiên bỏ URL `https://stspg.io/7pwv28hvkmz8` và `https://stspg.io/pjgptg3cfc6n`, hết max_steps=8 nên score 0. Đây là regression thật của phối hợp linked-incident validation với source-revision loop. Không phải lỗi truy cập incident hoặc API, không bỏ case và không tăng budget để làm đẹp điểm.
- V3 đạt mục tiêu đọc reference nhưng chưa giải quyết được citation-revision loop; cải tiến tiếp theo nên yêu cầu giữ toàn bộ nguồn đã quan sát khi sửa, hoặc thêm source list bằng code thay vì luân phiên yêu cầu model sửa từng URL. Chưa implement thay đổi tiếp theo để giữ riêng bằng chứng V3.
- Các case khác như A5/H3 giảm 20 điểm mỗi case; không đủ dữ liệu để gán mọi thay đổi cho code do nondeterminism của agent/judge. Cơ chế V2 còn giữ, không sửa fixtures/cases/scenarios/grading. V3 không được coi là thắng lợi toàn diện: cao hơn V2 rất ít, tốn nhiều token hơn và có một case không hoàn thành.

SHA256 `agent.py` dùng cho V3: `E39E7EF70CFDD4031F8B86674AEEF16647E26F86AF70A32A72548D97BBDA93B3`. Các report V0/V1/V2 được giữ nguyên. Mọi phiên bản mới phải dùng report khác để không ghi đè lịch sử.
