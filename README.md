# Tool Đối Soát Sao Kê Ngân Hàng

## 1. Mục tiêu

Đây là ứng dụng desktop viết bằng Python để đối soát giữa:

- file giao dịch từ hệ thống nội bộ
- file sao kê ngân hàng Techcombank

Mục tiêu của tool:

- xác định các giao dịch đã khớp chắc
- tách các giao dịch cần kiểm tra thủ công
- chỉ ra giao dịch có trong sao kê nhưng chưa thấy trong hệ thống
- chỉ ra giao dịch có trong hệ thống nhưng chưa thấy trong sao kê
- hỗ trợ xuất Excel để kế toán hoặc kiểm soát tiếp tục xử lý

Tool hiện chạy trên Windows, dùng PySide6 cho giao diện và có thể build thành file `.exe`.

README này là tài liệu kỹ thuật và nghiệp vụ cho source hiện tại:

1. mô tả kiến trúc source
2. mô tả tính năng đang có
3. mô tả logic dò hiện tại
4. chốt rule nghiệp vụ đã xác nhận trên dữ liệu mẫu
5. mô tả thiết kế engine mới đề xuất để phát triển tiếp

Nếu cần một tài liệu mô tả nghiệp vụ theo cách dễ đọc, ít thiên về code hơn, xem thêm:

- [docs/NGHIEP_VU_VA_QUY_TAC_DO.md](docs/NGHIEP_VU_VA_QUY_TAC_DO.md)

---

## 2. Công nghệ sử dụng

- Python
- PySide6
- `openpyxl`
- `xlrd`
- SQLite
- PyInstaller

---

## 3. Cấu trúc source hiện tại

```text
main.py
build_exe.bat

app/
  __init__.py
  i18n.py
  logging_utils.py
  models.py
  resource_utils.py

  services/
    __init__.py
    excel_loader.py
    exporter.py
    history_store.py
    reconciliation.py
    utils.py

  ui/
    __init__.py
    chips.py
    components.py
    config.py
    dialogs.py
    main_window.py
    main_window_actions_mixin.py
    main_window_filter_mixin.py
    main_window_scan_mixin.py
    metadata.py
    pages.py
    panels.py
    styles.py
    table_models.py
    widgets.py
    workers.py

tests/
  test_excel_file_kind.py
  test_main_window_scan_flow.py
  test_reconciliation_logic.py
```

### 3.1. Vai trò của từng nhóm file

#### `app/models.py`

Khai báo dataclass cho:

- `BankMetadata`
- `SystemTransaction`
- `BankTransaction`
- `ReconciliationSummary`
- `ReconciliationResult`

Điểm quan trọng:

- mỗi dòng giao dịch đều có:
  - `status`: `matched`, `review`, `unmatched`
  - `match_type`: `exact`, `group`, `none`
  - `group_id`
  - `group_order`
  - `confidence`
  - `match_reason`
- các dòng `review` có thể lưu danh sách ứng viên đối ứng:
  - phía hệ thống: `review_bank_ids`, `review_bank_rows`
  - phía sao kê: `review_system_ids`, `review_system_rows`

#### `app/services/excel_loader.py`

Chịu trách nhiệm:

- nhận diện file đầu vào là file hệ thống hay file sao kê
- đọc workbook Excel
- chuẩn hóa dữ liệu thành `SystemTransaction` và `BankTransaction`
- trích metadata của sao kê

#### `app/services/utils.py`

Chứa các hàm tiện ích:

- chuẩn hóa text
- parse ngày / datetime
- trích token tham chiếu
- trích prefix tham chiếu

Hiện source đang hỗ trợ tốt các prefix/token chính:

- `FT`
- `TT`
- `LD`
- `HB`
- `ST`
- `SK`

#### `app/services/reconciliation.py`

Đây là engine đối soát chính. Vai trò:

- tạo candidate giữa 2 phía
- chạy các vòng match theo mức độ chắc chắn
- gắn `matched`, `review`, `unmatched`
- tạo summary cuối cùng

#### `app/services/exporter.py`

Xuất kết quả đối soát ra Excel.

#### `app/services/history_store.py`

Lưu lịch sử đối soát bằng SQLite.

#### `app/ui/`

Phần UI đã được tách theo hướng dễ bảo trì hơn:

- `main_window.py`
  - điều phối chính
- `main_window_scan_mixin.py`
  - chọn file, scan, bind kết quả, chuyển page
- `main_window_filter_mixin.py`
  - filter, search, summary, row count
- `main_window_actions_mixin.py`
  - lịch sử, popup chi tiết, export
- `pages.py`
  - `StartupPage`, `ResultsPage`
- `chips.py`
  - `ChipButton`, `ChipPalette`
- `panels.py`
  - các panel dùng chung
- `dialogs.py`
  - `PairDialog`, `HistoryDialog`
- `styles.py`
  - stylesheet dùng chung
- `config.py`
  - config UI, header, width cột
- `metadata.py`
  - layout metadata sao kê
- `widgets.py`
  - widget tùy biến và loading overlay
- `workers.py`
  - `ScanWorker`

#### `tests/`

- `test_reconciliation_logic.py`
  - test các rule đối soát
- `test_main_window_scan_flow.py`
  - test regression cho luồng scan và chuyển page
- `test_excel_file_kind.py`
  - test detector file thật trong các bộ mẫu

---

## 4. Tính năng hiện có

### 4.1. Chọn file và dò

Ứng dụng cho phép:

- chọn file hệ thống
- chọn file sao kê
- chọn ngôn ngữ
- bấm `Dò sao kê`

Luồng UI hiện tại dùng 2 màn hình:

- `StartupPage`
- `ResultsPage`

Khi bấm dò:

- app chuyển sang màn hình kết quả
- hiện loading overlay
- tạo `ScanWorker` để đọc file và chạy reconciliation
- toàn bộ cập nhật UI được đưa về GUI thread bằng `Qt.QueuedConnection`

### 4.2. Màn hình kết quả

Màn hình sau khi dò gồm:

- cụm chọn file ở góc trái
- cụm metadata sao kê bên phải
- khu vực `Kết quả dò`
- 2 lưới `Sao kê` và `Hệ thống`
- các filter, chip trạng thái, action bar, popup chi tiết

### 4.3. Bộ lọc

Hiện ứng dụng có:

- chip trạng thái:
  - `Tất cả`
  - `Khớp`
  - `Cần kiểm tra`
  - `Chưa khớp`
- chip `Kiểu đối chiếu`:
  - khi chọn `Khớp`:
    - `Tất cả kiểu`
    - `Khớp lẻ`
    - `Phí/VAT`
    - `Chi + phí/thuế`
  - khi chọn `Cần kiểm tra`:
    - `Tất cả kiểu`
    - `Nhóm n-n`
  - khi chọn `Tất cả` hoặc `Chưa khớp`:
    - ẩn toàn bộ hàng `Kiểu đối chiếu`
  - mỗi chip đều hiển thị luôn số lượng giao dịch theo filter hiện tại
- filter loại giao dịch:
  - `Tất cả giao dịch`
  - `Chỉ hiện thu`
  - `Chỉ hiện chi`
  - `Chỉ hiện thuế`
- filter theo `Mã TCB`
- filter theo ngày
- filter tìm kiếm text

Lưu ý:

- `Phí/VAT` là group match cho nhiều dòng sao kê phí/VAT gộp về 1 dòng hệ thống
- `Chi + phí/thuế` là group match cho 1 dòng sao kê có nhiều cấu phần tiền
  - ví dụ: `chi + phí`
  - hoặc `chi + phí + thuế`
  - và phía hệ thống tách các cấu phần đó thành 2 hoặc 3 dòng
- `Nhóm n-n` là filter cho các cụm review có số dòng hai bên bằng nhau; đây không phải là `matched`
- các giao dịch group/review group trên lưới được hiển thị dạng `collapse/expand`
  - cột đầu tiên là cột expander
  - dòng cha hiển thị tóm tắt nhóm
  - khi mở nhóm thì các dòng con được tô màu nhẹ theo nhóm

### 4.4. Popup chi tiết

Khi click một dòng:

- nếu là `matched exact`, popup hiển thị cặp đối ứng 1-1
- nếu là `matched group`, popup hiển thị nhóm đối ứng
- nếu là `review`, popup hiển thị danh sách ứng viên đối ứng đã lưu trong row metadata

### 4.5. Lịch sử và xuất Excel

Ứng dụng hỗ trợ:

- lưu lịch sử dò
- xem lại lịch sử
- xuất Excel
- tùy chọn `Kèm sheet sao kê`

---

## 5. Luồng xử lý hiện tại

### 5.1. Luồng scan

1. chọn file hệ thống
2. chọn file sao kê
3. bấm `Dò sao kê`
4. app chuyển sang `ResultsPage`
5. hiện scan overlay
6. `ScanWorker` chạy trong thread riêng
7. worker đọc file, load data, chạy reconciliation
8. kết quả được đẩy về GUI thread
9. bind vào 2 bảng, metadata, summary, filter
10. ẩn loading

### 5.2. Luồng threading

Nguyên tắc hiện tại:

- worker chỉ đọc file và tạo data thuần
- worker không tạo hay chạm vào `QWidget`, `QHeaderView`, `QAbstractItemModel`
- toàn bộ bind model/view chỉ chạy ở main thread
- các signal `finished`, `failed`, `thread.finished` dùng `Qt.QueuedConnection`

Mục tiêu:

- tránh lỗi kiểu:
  - `QObject: Cannot create children for a parent that is in a different thread`
  - `QBasicTimer::start: Timers cannot be started from another thread`

### 5.3. Luồng filter

Sau khi đã có `current_result`:

- filter chip, ngày, mã TCB, tìm kiếm sẽ chạy trên dữ liệu đã bind
- filter loading là overlay riêng
- filter loading không được chen vào khi scan overlay đang chạy

---

## 6. Logic đọc và chuẩn hóa dữ liệu

### 6.1. File hệ thống

Loader chuẩn hóa ra:

- `voucher_date`
- `voucher_number`
- `summary`
- `counterpart_account`
- `amount_debit`
- `amount_credit`
- `direction`
- `amount`
- `balance`
- `data_source`
- `normalized_text`
- `reference_tokens`
- `reference_prefixes`

### 6.2. File sao kê

Loader chuẩn hóa ra:

- `requesting_datetime`
- `transaction_date`
- `reference_number`
- `remitter_bank`
- `remitter_account_number`
- `remitter_account_name`
- `description`
- `debit`
- `credit`
- `fee`
- `vat`
- `amount`
- `direction`
- `running_balance`
- `normalized_text`
- `reference_tokens`
- `reference_prefixes`

### 6.3. Nhận diện loại file

`detect_excel_file_kind(path)` hiện được dùng để:

- phân biệt file hệ thống và file sao kê
- chặn file sai loại trước khi vào luồng scan chính

Phần này đã có test với dữ liệu thật:

- `202512`
- `202601`
- `202602`
- `202603`
- `202603.1`

---

## 7. Logic đối soát hiện tại trong source

### 7.1. Dữ liệu mà engine sử dụng

Mỗi giao dịch sau khi load đều có:

- ngày
- chiều giao dịch
- số tiền
- diễn giải chuẩn hóa
- token text
- token tham chiếu
- prefix tham chiếu
- các trường trạng thái đối soát

### 7.2. Các vòng match hiện có

Engine trong `app/services/reconciliation.py` hiện chạy theo thứ tự:

1. `reference`
2. `voucher_unique`
3. `derived_unique`
4. `tax aggregate`
5. `review candidate`

### 7.3. `matched exact`

Một dòng được gắn `matched + exact` khi:

- có cặp đối ứng 1-1
- cùng chiều
- cùng số tiền
- qua được một trong các vòng exact

Khi đó:

- `status = matched`
- `match_type = exact`
- gắn cặp `matched_system_id / matched_bank_id`

### 7.4. `matched group`

Hiện tại source mới có group match chắc cho:

- `Phí/VAT`
- nhóm Homebanking / phí kèm VAT

Mô hình hiện có:

- nhiều dòng bank
- gộp về 1 dòng hệ thống

Tức là bản chất hiện tại là `1-n`, chưa phải engine group tổng quát.

### 7.5. `review`

Các dòng chưa match được nâng sang `review` nếu vẫn còn ứng viên hợp lý.

Điều kiện review hiện tại trong code xoay quanh:

- cùng chiều
- cùng số tiền
- có ít nhất một clue đủ mạnh

Clue đang được dùng:

- có reference token
- hoặc cùng ngày
- hoặc lệch rất ít ngày và text đủ gần
- hoặc là cặp gần nhất lẫn nhau trong tập ứng viên

### 7.6. `unmatched`

Một dòng còn là `unmatched` khi:

- không qua exact match
- không rơi vào tax aggregate group
- không đủ điều kiện để nâng sang `review`

Vì vậy hiện tại `unmatched` vẫn đang chứa 2 loại:

1. thật sự không có đối ứng hợp lý
2. có khả năng là ca `1-n / n-1 / n-n` nhưng engine chưa giải được

---

## 8. Baseline trên dữ liệu mẫu

### 8.1. Tổng quan theo bộ dữ liệu

| Bộ dữ liệu | System matched | System review | System unmatched | Bank matched | Bank review | Bank unmatched |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `202512` | 735 | 44 | 16 | 742 | 43 | 12 |
| `202601` | 502 | 48 | 10 | 509 | 48 | 8 |
| `202602` | 333 | 54 | 7 | 340 | 53 | 7 |
| `202603` | 387 | 19 | 4 | 394 | 19 | 14 |

### 8.2. Nhận xét nhanh

- Số lượng `matched` hiện tại là lớn và tương đối ổn cho các ca `1-1` chắc.
- `review` vẫn còn nhiều ở các cụm amount lặp hoặc thiếu khóa riêng từng dòng.
- `unmatched` chưa hoàn toàn phản ánh "không có đối ứng", vì còn có các ca `1-n / n-1` chưa được engine tổng quát hỗ trợ.

### 8.3. Các ca `1-n / n-1` thật đã xác nhận

Đã xác nhận được nhiều ca thật trong 4 bộ dữ liệu:

- `202512`
  - bank `7` ca
  - system `4` ca
- `202601`
  - bank `3`
  - system `1`
- `202602`
  - bank `2`
  - system `3`
- `202603`
  - bank `2`
  - system `3`

Ví dụ cụ thể trong `202603`:

- system row `79 = bank 350 + 368`
- system row `80 = bank 349 + 369`
- system row `336 = bank 103 + 104`

Kết luận:

- dữ liệu thật có `1-n`
- dữ liệu thật có `n-1`
- source hiện chưa có engine group tổng quát ngoài `Phí/VAT`

### 8.4. Các cụm `n-n` thật trong dữ liệu mẫu

Ví dụ nổi bật trong `202603`:

- amount `70,000,000`
  - system `2`
  - bank `2`
  - nhóm `MOC HOANG GIA`
- amount `100,000,000`
  - system `3`
  - bank `3`
  - lẫn `WUYI`, `LINH AN`, `PHÚ HOA`, `HOANG QUAN`
- amount `450,000,000`
  - system `4`
  - bank `4`
  - nhóm `TẢN VIÊN`
- amount `490,000,000`
  - system `2`
  - bank `2`
  - mô tả bank rất yếu
- amount `500,000,000`
  - system `2`
  - bank `2`
- amount `1,000,000,000`
  - system `3`
  - bank `3`

Các nhóm này không nên auto-match trong trạng thái source hiện tại.

---

## 9. Rule nghiệp vụ đã chốt

### 9.1. Nguyên tắc nền

#### a. Sao kê là nguồn chuẩn chính

Tool đối soát theo hai chiều, nhưng phía sao kê vẫn là nguồn tham chiếu chính khi đánh giá có dòng phát sinh thật ở ngân hàng.

#### b. Không ép khớp cho đủ

Ưu tiên an toàn:

- thiếu bằng chứng thì để `review`
- mơ hồ thật thì để `unmatched`

#### c. `Ngày hệ thống` là tín hiệu mềm

Do hệ thống là nhập tay nên có thể phát sinh tình huống:

- sao kê có giao dịch hôm nay
- vài ngày sau người dùng mới nhập hệ thống

Vì vậy ngày không được coi là điều kiện cứng.

#### d. `n-n` không auto-match

Đây là nguyên tắc an toàn đã chốt.

### 9.2. Mức độ tin cậy của ngày giao dịch

Nên hiểu như sau:

- cùng ngày: rất mạnh
- lệch `1-3` ngày: vẫn hợp lý
- lệch `4-7` ngày: chỉ hợp lý nếu có thêm clue mạnh
- lệch `> 7` ngày: thường không đủ, trừ khi có key cứng

Key mạnh bao gồm:

- `FT`
- `ST`
- `LD`
- invoice
- bill
- contract
- key nghiệp vụ rõ trong mô tả

### 9.3. Các loại tín hiệu dùng để dò

#### a. Tín hiệu cứng

- cùng chiều
- cùng số tiền
- tham chiếu mạnh
- key nghiệp vụ đặc thù

#### b. Tín hiệu mạnh

- ngày trùng
- đối tác trùng hoặc alias hợp lệ
- mô tả rất gần
- invoice / BL / PO / contract trùng

#### c. Tín hiệu mềm

- ngày gần
- mô tả gần
- cùng nhóm nghiệp vụ

### 9.4. Phân loại giao dịch theo nghiệp vụ

#### a. `FT`

Thường là chuyển khoản trực tiếp. Nhóm này nên ưu tiên exact match khi:

- cùng chiều
- cùng amount
- cùng reference hoặc mô tả đủ mạnh

#### b. `TT`

Thường là nộp/rút tiền hoặc giao dịch có mô tả ngắn.

Nhóm này không nên chỉ dựa vào amount, vì mô tả có thể yếu.

#### c. `LD / ST`

Nhóm vay và khế ước. Đây là nhóm có key nghiệp vụ tốt, nên ưu tiên match bằng:

- `ST`
- `LD`
- amount
- ngày

#### d. `HB / Phí / VAT`

Đây là group hiện source đang hỗ trợ chắc.

#### e. Lãi ngân hàng cuối tháng

Đây là nhóm exact tốt nếu nhận diện đúng reference hoặc mô tả.

#### f. Lương

Theo dữ liệu mẫu hiện tại, lương chủ yếu rơi vào:

- `1-n`
- hoặc `n-1`

Chưa thấy pattern `n-n` rõ như nhóm thu khách hàng lặp amount.

#### g. Thu khách hàng / công nợ / logistics lặp amount

Đây là nhóm dễ phát sinh `n-n` nhất trong dữ liệu thật.

### 9.5. Khi nào là `Khớp`

#### `Khớp lẻ`

Một dòng nên được tính là `Khớp` khi:

- có đúng một đối ứng `1-1` rõ ràng
- cùng chiều
- cùng số tiền
- ngày hợp lý
- có thêm bằng chứng hỗ trợ đủ chắc

Ví dụ:

- `FT` chi trực tiếp
- `LD/ST` có đối ứng rõ
- `TT` có cặp rõ
- lãi ngân hàng cuối tháng

#### `Phí/VAT đã khớp`

Một nhóm nên được tính là `Khớp` khi:

- nhiều dòng bank phí/VAT
- tổng đúng bằng một dòng hệ thống
- tổ hợp là duy nhất
- nhóm này đúng nghiệp vụ

Hiện tại đây là group match duy nhất đã được source hỗ trợ chắc.

#### `Khớp group` tổng quát trong tương lai

Về nghiệp vụ, `1-n / n-1` có thể được nâng lên `matched group` nếu:

- tổ hợp là duy nhất
- tổng tiền khớp tuyệt đối
- cùng chiều
- ngày hợp lý
- có thêm clue đủ mạnh

### 9.6. Khi nào là `Cần kiểm tra`

`review` là trạng thái:

- có ứng viên hợp lý
- nhưng chưa đủ chắc để auto-match

Một dòng nên là `review` khi:

- cùng chiều
- cùng số tiền
- cùng ngày hoặc ngày gần
- mô tả / đối tác / reference có liên quan
- nhưng còn hơn một khả năng
- hoặc có clue chưa đủ mạnh để chốt `1-1`

Rule rất quan trọng:

- nếu có ứng viên hợp lý thì không nên đẩy xuống `unmatched` quá sớm

### 9.7. Khi nào là `Chưa khớp`

`unmatched` chỉ nên dùng khi:

- không có ứng viên cùng chiều và amount đủ hợp lý
- hoặc ngày lệch xa, không có clue mạnh
- hoặc là `n-n` mơ hồ thật
- hoặc là ca group mà chưa tìm ra tổ hợp đủ chắc

### 9.8. Quy tắc `1-n / n-1 / n-n`

#### `1-n`

Cho phép lên `matched group` nếu:

- một dòng phía A
- nhiều dòng phía B
- tổng tiền khớp tuyệt đối
- tổ hợp là duy nhất
- có thêm bằng chứng về đối tác / mô tả / key nghiệp vụ

#### `n-1`

Tương tự `1-n`.

#### `n-n`

Không auto-match.

##### `n-n` có key riêng từng dòng

Ví dụ:

- invoice riêng
- BL riêng
- PO riêng
- contract riêng
- mô tả và đối tác đủ tách dòng

Trường hợp này nên là:

- `review`

##### `n-n` mơ hồ thật

Trường hợp:

- số dòng bằng nhau
- amount bằng nhau
- nhưng không có khóa đủ chắc để map `1-1`

Trường hợp này nên là:

- `unmatched`

### 9.9. Thuế và lương có phải `n-n` không

Theo dữ liệu mẫu hiện tại:

- `Phí/VAT` là `1-n`, không phải `n-n`
- `lương` chủ yếu là `1-n` hoặc `n-1`
- `n-n` xuất hiện nhiều hơn ở:
  - thu khách hàng
  - công nợ lặp amount
  - một số nhóm logistics / chi phí lặp dòng

### 9.10. Bảng quyết định trạng thái

#### a. `Khớp`

Gắn `Khớp` khi:

- exact `1-1` rõ ràng
- hoặc group `1-n / n-1` đủ chắc

#### b. `Cần kiểm tra`

Gắn `Cần kiểm tra` khi:

- có ứng viên hợp lý
- nhưng còn mơ hồ
- hoặc là `n-n` có thể giải bằng key riêng

#### c. `Chưa khớp`

Gắn `Chưa khớp` khi:

- không có ứng viên hợp lý
- hoặc là `n-n` mơ hồ thật

---

## 10. Dữ liệu nào được tính là `Khớp`, `Review`, `Chưa khớp`

### 10.1. Dữ liệu được tính là `Khớp`

#### a. `Khớp lẻ`

Gồm các trường hợp:

- hệ thống và bank có cặp `1-1` rõ ràng
- cùng chiều
- cùng số tiền
- ngày phù hợp
- có thêm bằng chứng mạnh

Các nhóm đang có xác suất đúng cao:

- `FT` chi trực tiếp
- `LD/ST` có đối ứng rõ
- `TT` có cặp rõ
- lãi ngân hàng cuối tháng

#### b. `Phí/VAT đã khớp`

Gồm các trường hợp:

- nhiều dòng bank phí/VAT
- tổng bằng một dòng hệ thống
- tổ hợp duy nhất

### 10.2. Dữ liệu được tính là `Cần kiểm tra`

Gồm các trường hợp:

- cùng chiều
- cùng số tiền
- cùng ngày hoặc ngày gần
- có đối tác hoặc mô tả hoặc reference liên quan
- nhưng chưa đủ chắc

Thường rơi vào:

- nhiều ứng viên cùng amount
- mô tả gần đúng nhưng chưa khóa được `1-1`
- `n-n` có thể phân rã nếu trích thêm key

### 10.3. Dữ liệu được tính là `Chưa khớp`

Gồm các trường hợp:

- không có đối ứng cùng amount
- khác chiều
- cùng amount nhưng ngày lệch xa và không có clue mạnh
- `1-n / n-1` mà engine chưa tìm được tổ hợp
- `n-n` mơ hồ thật

---

## 11. Thiết kế engine mới đề xuất

Phần này mô tả kiến trúc engine mới nên đi theo để vừa an toàn, vừa tối ưu hơn cách dò hiện tại.

Mục tiêu:

- không dùng một công thức chung cho mọi giao dịch
- giảm `unmatched` bị sót
- không auto-match bừa ở các ca mơ hồ
- giải được các ca `1-n / n-1` rõ ràng
- gom được các ca `n-n` thành cụm `review`

### 11.1. Nguyên tắc thiết kế

#### a. Rule-based trước, thuật toán tối ưu sau

Engine mới không nên là mô hình black-box.

Thứ tự đúng:

1. phân loại giao dịch theo nghiệp vụ
2. tạo candidate hợp lý
3. chạy thuật toán ghép phù hợp theo từng loại
4. gắn trạng thái theo rule nghiệp vụ

#### b. Tách riêng 3 bài toán

- `1-1`
- `1-n / n-1`
- `n-n`

Không nên trộn cả 3 loại vào một score chung.

#### c. Hai vòng dò

Engine mới nên có:

- vòng 1: bắt exact và group chắc
- vòng 2: rà lại phần `unmatched` để giảm sót

### 11.2. Kiến trúc phase đề xuất

#### Phase 0. Normalize

Chuẩn hóa toàn bộ dữ liệu:

- ngày
- chiều
- amount
- text
- reference
- key nghiệp vụ
- alias đối tác

#### Phase 1. Classify

Phân loại từng dòng vào nhóm nghiệp vụ:

- `FT`
- `TT`
- `LD/ST`
- `HB/VAT`
- lãi ngân hàng
- lương
- thu khách hàng
- logistics / chi phí / khác

#### Phase 2. Build Candidate Index

Tạo chỉ mục để không phải so sánh mọi dòng với mọi dòng:

- theo chiều giao dịch
- theo amount
- theo ngày bucket
- theo đối tác
- theo prefix reference
- theo key nghiệp vụ

#### Phase 3. Exact Match Engine

Xử lý các nhóm exact:

- `FT`
- `LD/ST`
- `TT` rõ
- lãi ngân hàng
- các cặp unique khác

#### Phase 4. Group Match Engine

Xử lý các ca:

- `Phí/VAT`
- `1-n`
- `n-1`

Nhưng chỉ nâng lên `matched group` nếu tổ hợp là duy nhất và đủ chắc.

#### Phase 5. Review Engine

Lấy các dòng còn lại và nâng sang `review` nếu:

- còn ứng viên hợp lý
- hoặc là `n-n` có key riêng từng dòng

#### Phase 6. Recheck Pass

Chỉ chạy trên tập `unmatched`.

Mục tiêu:

- rà lại các ca bị sót
- đặc biệt là:
  - `1-n / n-1` bị sót
  - `n-n` có dữ liệu khá khớp
  - ca ngày lệch vài ngày nhưng có clue mạnh

#### Phase 7. Finalize

Tổng hợp:

- status cuối
- match type
- group id
- confidence
- reason
- review candidates

### 11.3. Thuật toán nên dùng cho từng phase

#### a. Exact `1-1`: weighted bipartite matching

Đối với các nhóm có nhiều ứng viên `1-1` cùng amount, nên dùng:

- `weighted bipartite matching`

Ý tưởng:

- node trái: dòng hệ thống
- node phải: dòng bank
- cạnh nối nếu candidate hợp lý
- trọng số = độ tin cậy

Sau đó lấy tập cạnh tối ưu toàn cục.

Lợi ích:

- tránh match tham lam từng dòng
- giảm ghép nhầm khi có nhiều dòng trùng amount

#### b. `1-n / n-1`: bounded subset matching

Đối với các ca group rõ, nên dùng:

- `bounded subset sum`
- hoặc `meet-in-the-middle` khi số dòng nhỏ

Giới hạn:

- chỉ xét trong cùng chiều
- cùng bucket ngày
- cùng nhóm nghiệp vụ
- cùng đối tác hoặc key gần nhau
- số phần tử tối đa trong tổ hợp nên nhỏ, ví dụ `2-4`

#### c. `n-n`: cluster for review

Đối với `n-n`, không auto-match.

Thay vào đó:

- dựng cụm liên thông theo:
  - amount
  - ngày
  - đối tác
  - key nghiệp vụ
- nếu trong cụm có khóa riêng từng dòng thì gắn `review`
- nếu cụm quá mơ hồ thì giữ `unmatched`

### 11.4. Vòng 1 và vòng 2 nên làm gì

#### Vòng 1

Chỉ làm các việc chắc:

- exact match
- `Phí/VAT`
- group `1-n / n-1` nếu tổ hợp rõ
- review cơ bản

#### Vòng 2

Chỉ xử lý tập `unmatched`.

Mục tiêu:

- kéo các ca bị sót lên `review`
- nâng một số ca `1-n / n-1` rõ lên `matched group`
- rà lại `n-n` để phân biệt:
  - `review`
  - `unmatched`

### 11.5. Quy tắc trạng thái trong engine mới

#### a. `matched + exact`

Khi:

- exact `1-1`
- candidate duy nhất hoặc nghiệm tối ưu rõ

#### b. `matched + group`

Khi:

- `1-n` hoặc `n-1`
- tổ hợp duy nhất
- tổng tiền khớp tuyệt đối
- đủ clue nghiệp vụ

#### c. `review`

Khi:

- còn ứng viên hợp lý
- hoặc `n-n` có thể phân giải bằng key riêng
- hoặc có cluster đối ứng hợp lý nhưng chưa đủ chắc để auto-match

#### d. `unmatched`

Khi:

- không còn ứng viên hợp lý sau vòng 2
- hoặc cụm `n-n` quá mơ hồ

### 11.6. Pseudo-code tổng quát

```text
function reconcile(system_rows, bank_rows):
    normalize(system_rows, bank_rows)
    classify(system_rows, bank_rows)
    index = build_candidate_index(system_rows, bank_rows)

    result = new ReconciliationState()

    phase_exact_reference(index, result)
    phase_exact_unique(index, result)
    phase_exact_weighted_1_to_1(index, result)

    phase_group_tax_vat(index, result)
    phase_group_one_to_many(index, result)
    phase_group_many_to_one(index, result)

    phase_review_basic(index, result)

    unmatched_system = get_unmatched_system_rows(result)
    unmatched_bank = get_unmatched_bank_rows(result)
    phase_recheck(unmatched_system, unmatched_bank, index, result)

    finalize_status(result)
    build_summary(result)
    return result
```

### 11.7. Pseudo-code tạo candidate

```text
function build_candidates(row, opposite_rows):
    candidates = []
    for other in opposite_rows:
        if row.direction != other.direction:
            continue
        if row.amount != other.amount:
            continue

        score = 0

        if same_day(row, other):
            score += 30
        else if near_day(row, other, 3):
            score += 18
        else if near_day(row, other, 7):
            score += 8

        if same_reference(row, other):
            score += 35
        if same_partner_or_alias(row, other):
            score += 20
        if same_business_key(row, other):
            score += 25
        if text_similarity(row, other) >= threshold:
            score += 10

        if score >= candidate_threshold:
            candidates.append((other, score))

    return candidates
```

### 11.8. Pseudo-code `1-1` tối ưu

```text
function phase_exact_weighted_1_to_1(index, result):
    graph = build_bipartite_graph(index)
    matches = maximum_weight_matching(graph)

    for system_row, bank_row, score in matches:
        if score < exact_threshold:
            continue
        mark_matched_exact(system_row, bank_row, score, result)
```

### 11.9. Pseudo-code `1-n / n-1`

```text
function phase_group_one_to_many(index, result):
    for system_row in unmatched_system_rows(result):
        pool = candidate_pool_for_group(system_row, unmatched_bank_rows(result))
        combos = bounded_subset_sum(pool, target=system_row.amount, max_size=4)

        combos = keep_only_reasonable_combos(
            combos,
            same_direction=True,
            date_window_days=3,
            same_business_family=True
        )

        if len(combos) == 1:
            mark_matched_group(system_row, combos[0], result)
        else if len(combos) > 1:
            mark_review_group(system_row, combos, result)
```

### 11.10. Pseudo-code `n-n`

```text
function phase_recheck(unmatched_system, unmatched_bank, index, result):
    clusters = build_nn_clusters(unmatched_system, unmatched_bank)

    for cluster in clusters:
        if cluster_has_line_level_keys(cluster):
            mark_cluster_review(cluster, result)
        else:
            keep_cluster_unmatched(cluster, result)
```

### 11.11. Tại sao thiết kế này phù hợp

Thiết kế này phù hợp với bài toán hiện tại vì:

- giải thích được
- audit được
- không phụ thuộc AI black-box
- tôn trọng tính an toàn của dữ liệu tiền
- hỗ trợ đúng bản chất:
  - `1-1`
  - `1-n / n-1`
  - `n-n`

---

## 12. Những gì source hiện tại làm đúng

- đọc được file mẫu thật
- detector loại file hoạt động đúng trên các bộ mẫu
- scan flow đã ổn định lại sau refactor
- cập nhật UI chạy trên đúng GUI thread
- không còn regression `QObject different thread` trong luồng scan chuẩn
- `Phí/VAT` đã có group match riêng
- popup detail đã hiển thị được cặp, group và review candidate
- UI đã tách nhỏ đáng kể so với phiên bản ban đầu

---

## 13. Hạn chế hiện tại

### 13.1. Engine group còn hẹp

Hiện source mới hỗ trợ chắc `group match` cho `Phí/VAT`.

Chưa có engine tổng quát cho:

- lương
- thưởng
- các khoản bị tách `1-2`, `2-1`
- các cụm chi phí hoặc doanh thu bị chia/gộp khác

### 13.2. `review / unmatched` vẫn cần tinh chỉnh

Hiện tại vẫn còn các case:

- cùng tiền
- cùng ngày hoặc ngày gần
- có thêm clue

nhưng source vẫn có thể để `unmatched` nếu chưa đủ rule nâng sang `review`.

### 13.3. `n-n` chưa được phân loại sâu

Chưa có cơ chế tổng quát để tách:

- `n-n` có thể giải bằng key riêng từng dòng
- `n-n` mơ hồ thật

### 13.4. Rule exact theo từng nhóm nghiệp vụ cần rà kỹ hơn

Các family cần audit tiếp:

- `FT`
- `TT`
- `LD/ST`
- `HB`
- lãi ngân hàng

### 13.5. Dữ liệu phụ trợ chưa đủ phong phú

Hiện source vẫn còn thiếu ở một số điểm:

- alias tên đối tác
- invoice / BL / PO / contract extractor đầy đủ
- một số key phụ như `PPP`, `BHD`
- xử lý gross / net ở các case thu có phí

---

## 14. Backlog kỹ thuật và nghiệp vụ tiếp theo

### 14.1. Ưu tiên số 1: tinh chỉnh `review / unmatched`

Mục tiêu:

- những case có ứng viên hợp lý không bị đỏ quá tay
- nhưng vẫn không auto-match bừa

### 14.2. Ưu tiên số 2: làm `group match` tổng quát cho `1-n / n-1`

Ưu tiên các ca rõ nhất:

- lương
- thưởng
- các khoản tách dòng nhưng tổng tiền và ngày rất rõ

### 14.3. Ưu tiên số 3: audit exact rule theo từng nhóm giao dịch

- `FT`
- `TT`
- `LD/ST`
- `HB`
- lãi cuối tháng

### 14.4. Ưu tiên số 4: tăng dữ liệu phụ trợ

- trích thêm key từ text
- alias tên đối tác
- invoice / BL / PO / contract
- gross / net cho một số case thu có phí

### 14.5. Ưu tiên số 5: khóa bằng test

Cần bổ sung test cho:

- `same amount + near date -> review`
- `direction mismatch -> unmatched`
- `1-n / n-1`
- `n-n không auto-match`
- `n-n có key riêng -> review`
- exact rule cho từng family

---

## 15. Kiến trúc UI hiện tại

Phần UI hiện đã được tách theo hướng dễ bảo trì hơn.

### 15.1. Kiến trúc chính

- `MainWindow`
  - chỉ điều phối
- `page + mixin + component`

### 15.2. Màn hình

- `StartupPage`
  - chỉ chọn file và bắt đầu dò
- `ResultsPage`
  - hiển thị metadata, filter, action, grid

### 15.3. Mixin

- `main_window_scan_mixin.py`
  - chọn file, chạy scan, bind result, chuyển page
- `main_window_filter_mixin.py`
  - filter, search, summary
- `main_window_actions_mixin.py`
  - history, export, detail dialog

### 15.4. Component

- chip/button riêng
- panel riêng
- dialog riêng
- style riêng
- metadata layout riêng

Mục tiêu của kiến trúc hiện tại:

- tránh dồn toàn bộ UI vào một file quá lớn
- dễ chỉnh sửa từng cụm giao diện
- giảm rủi ro style đè lẫn nhau

---

## 16. Kiểm thử hiện có

### 16.1. Test logic đối soát

`tests/test_reconciliation_logic.py`

Bao phủ:

- exact match
- VAT/Homebanking group
- review
- unmatched
- một số regression nghiệp vụ đã sửa

### 16.2. Test scan flow UI

`tests/test_main_window_scan_flow.py`

Bao phủ:

- startup page compact
- scan success -> results page
- scan fail -> quay lại startup
- queued connection
- filter loading không đè scan overlay

### 16.3. Test detector file

`tests/test_excel_file_kind.py`

Bao phủ detector trên dữ liệu thật trong repo.

---

## 17. Cách chạy source

### 17.1. Chạy app

```bash
python main.py
```

### 17.2. Chạy test

```bash
python -m unittest tests.test_reconciliation_logic tests.test_main_window_scan_flow tests.test_excel_file_kind
```

### 17.3. Kiểm tra compile

```bash
python -m compileall app tests
```

### 17.4. Build `.exe`

```bash
build_exe.bat
```

---

## 18. Kết luận hiện trạng

Tính đến thời điểm cập nhật README này:

- kiến trúc UI đã được refactor đủ sạch để tiếp tục phát triển
- scan flow và luồng thread đã được khôi phục ổn định
- detector file mẫu đã được khóa bằng test
- source hiện đối soát ổn cho nhiều ca `1-1` và `Phí/VAT`
- phần còn cần làm tiếp là hoàn thiện logic nghiệp vụ cho:
  - `review / unmatched`
  - `1-n / n-1`
  - exact rule theo từng nhóm giao dịch

Nói ngắn gọn:

- kiến trúc hiện tại đã đủ tốt để phát triển tiếp
- ưu tiên tiếp theo là quay lại hoàn thiện engine dò nghiệp vụ

