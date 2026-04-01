# Tool Đối Soát Sao Kê Ngân Hàng

## 1. Tổng quan

Đây là ứng dụng desktop viết bằng Python để đối soát:

- File giao dịch từ hệ thống nội bộ
- File sao kê ngân hàng Techcombank

Tool hiện chạy trên Windows, có giao diện PySide6, và có thể build thành file `.exe` để sử dụng nội bộ.

Mục tiêu chính:

- Đối chiếu giao dịch giữa hệ thống và sao kê
- Phân loại kết quả thành `matched`, `review`, `unmatched`
- Giúp người dùng rà nhanh các dòng cần kiểm tra
- Xuất kết quả ra Excel để xử lý tiếp

README này mô tả đồng thời 3 lớp nội dung:

1. Tính năng đang có trong source
2. Logic đối soát mà source hiện tại đang thực thi
3. Logic nghiệp vụ đề xuất để nâng cấp source dựa trên dữ liệu mẫu trong `file/202512`, `file/202601`, `file/202602`, `file/202603`

## 2. Công nghệ sử dụng

- Python
- PySide6
- `openpyxl`
- `xlrd`
- SQLite
- PyInstaller

## 3. Cấu trúc source

```text
main.py                         Điểm khởi động ứng dụng
build_exe.bat                   Script build file exe
app/models.py                   Dataclass dữ liệu đối soát
app/i18n.py                     Đa ngôn ngữ
app/logging_utils.py            Cấu hình log theo ngày
app/resource_utils.py           Tìm tài nguyên khi chạy source/exe
app/services/excel_loader.py    Nhận diện và đọc file Excel
app/services/reconciliation.py  Engine đối soát hiện tại
app/services/exporter.py        Xuất Excel
app/services/history_store.py   Lưu lịch sử vào SQLite
app/services/utils.py           Hàm tiện ích, parse, normalize, token
app/ui/main_window.py           Giao diện chính
app/ui/table_models.py          Model/filter cho lưới dữ liệu
app/ui/widgets.py               Widget tùy biến
tests/test_reconciliation_logic.py  Test logic cốt lõi
file/                           Bộ dữ liệu mẫu
data/history.sqlite             Cơ sở dữ liệu lịch sử khi chạy thực tế
data/logs/YYYYMMDD.log          File log theo ngày
```

## 4. Tính năng hiện có trong source

### 4.1. Chọn file và kiểm tra file

- Chọn `File hệ thống` và `File sao kê`
- Hỗ trợ `.xls` và `.xlsx`
- Kiểm tra file có đúng loại hay không trước khi đối soát
- Phát hiện trường hợp người dùng chọn ngược slot `hệ thống` và `sao kê`

### 4.2. Giao diện đối soát

- Giao diện một cửa sổ
- Chỉ hiển thị một lưới dữ liệu tại một thời điểm
- Có thể đổi qua lại giữa lưới `Hệ thống` và `Sao kê`
- Có loading overlay khi đang xử lý
- Có popup chi tiết đối ứng
- Có thể mở và focus sang dòng đối ứng ở lưới còn lại

### 4.3. Bộ lọc và tìm kiếm

Source hiện tại đã có:

- Lọc trạng thái:
  - `all`
  - `matched`
  - `review`
  - `unmatched`
- Lọc loại giao dịch:
  - `all`
  - `income`
  - `expense`
  - `tax`
- Lọc mã tham chiếu hiện hỗ trợ trên UI:
  - `FT`
  - `ST`
  - `SK`
  - `LD`
  - `HB`
- Tìm kiếm theo:
  - tất cả cột
  - một cột cụ thể
- Quick search đồng bộ cho cả hai lưới
- Lọc theo khoảng ngày
- Sắp xếp theo cột thông qua `QSortFilterProxyModel`

### 4.4. Tổng hợp kết quả

- Hiển thị tổng số `matched`, `review`, `unmatched`
- Hiển thị số dòng đang thấy trên lưới / tổng số dòng
- Hiển thị metadata của sao kê:
  - ngân hàng
  - mã số thuế
  - kỳ sao kê
  - số tài khoản
  - tên tài khoản
  - loại tiền
  - loại tài khoản
  - số dư đầu kỳ
  - số dư hiện tại
  - số dư cuối kỳ
  - tổng ghi nợ
  - tổng ghi có
  - tổng phí
  - tổng VAT
  - tổng lệnh ghi nợ
  - tổng lệnh ghi có

### 4.5. Lịch sử và log

- Mỗi lần chạy xong sẽ lưu kết quả tổng hợp vào SQLite
- UI có nút xem lịch sử đối soát gần đây
- Log ghi ra file theo ngày trong `data/logs`

### 4.6. Xuất Excel

Source hiện tại cho phép:

- Xuất theo lưới đang xem:
  - nếu đang xem `Hệ thống` thì xuất lưới hệ thống
  - nếu đang xem `Sao kê` thì xuất lưới sao kê
- Xuất theo đúng bộ lọc hiện tại
- Nếu đang ở chế độ `status = all` thì tô đỏ dòng `unmatched`
- Có tùy chọn đính kèm thêm sheet sao kê gốc

### 4.7. Đa ngôn ngữ

- Tiếng Việt
- English
- 中文简体

## 5. Luồng xử lý hiện tại trong source

### 5.1. Điểm vào

`main.py` đang thực hiện:

- Cấu hình UTF-8 cho stdout/stderr
- Tạo `QApplication`
- Nạp icon nếu có
- Mở `MainWindow`

### 5.2. MainWindow

`app/ui/main_window.py` đang phụ trách:

- Chọn file
- Validate file trước khi đối soát
- Chạy worker thread để tránh treo UI
- Nhận `ReconciliationResult`
- Bind dữ liệu vào lưới
- Áp bộ lọc
- Hiển thị metadata
- Hiển thị popup đối ứng
- Xuất Excel
- Tải lịch sử từ SQLite

### 5.3. Loader

`app/services/excel_loader.py` đang phụ trách:

- Nhận diện file là `system`, `bank`, hay `unknown`
- Đọc file hệ thống `.xls`
- Đọc file sao kê `.xlsx`
- Parse metadata sao kê
- Chuẩn hóa dữ liệu thành `SystemTransaction` và `BankTransaction`

### 5.4. Reconciliation engine

`app/services/reconciliation.py` đang phụ trách:

- Gom nhóm theo `(direction, amount)`
- Chấm điểm từng cặp ứng viên
- Chạy các vòng match:
  - `reference`
  - `voucher_unique`
  - `derived_unique`
  - gom nhóm VAT
  - vòng cuối `scored`
- Gán `matched`, `review`, `unmatched`

### 5.5. Exporter

`app/services/exporter.py` đang phụ trách:

- Tạo workbook mới
- Ghi header và dữ liệu hiển thị
- Tô màu dòng `unmatched` khi cần
- Sao chép thêm sheet sao kê gốc nếu người dùng bật option

### 5.6. History store

`app/services/history_store.py` đang phụ trách:

- Tạo schema SQLite nếu chưa có
- Lưu tổng hợp sau mỗi lần đối soát
- Lấy danh sách lịch sử gần đây

## 6. Định dạng dữ liệu đầu vào

### 6.1. File hệ thống

- Định dạng thiết kế để đọc từ `.xls`
- Các cột bắt buộc mà source hiện kỳ vọng:
  - cột ngày chứng từ
  - cột số chứng từ
  - cột tóm tắt
  - cột tài khoản đối ứng
  - cột số tiền bên Có
  - cột số tiền bên Nợ

Lưu ý:

- Trong code hiện tại, các literal header đang lấy trực tiếp từ file thực tế
- Nếu mở source ở môi trường encoding không chuẩn, các chuỗi header tiếng Trung có thể hiển thị sai hình thức
- Về nghiệp vụ, ý nghĩa thật của các cột vẫn là như trên

#### Cách source đọc file hệ thống hiện tại

- Hàm detect có thể tìm header trong 8 dòng đầu
- Nhưng hàm load hiện tại vẫn giả định header nằm ở dòng đầu tiên
- Chỉ đọc 10 cột đầu tiên
- Bỏ qua dòng rỗng
- Bỏ qua dòng `上期结转`

#### Chuẩn hóa `SystemTransaction`

- `direction = income` nếu `amount_debit > 0` và `amount_credit == 0`
- Ngược lại coi là `expense`
- `amount`:
  - income -> `amount_debit`
  - expense -> `amount_credit`
- Text để tokenize:
  - voucher number
  - summary
  - counterpart account
  - data source

### 6.2. File sao kê

- Định dạng thiết kế để đọc từ `.xlsx`
- Header row được tìm trong 40 dòng đầu
- Các cột quan trọng:
  - `Requesting datetime`
  - `Transaction date`
  - `Reference number`
  - `Description`
  - `Debit`
  - `Credit`
  - `Fee/Interest`
  - `Transaction VAT`

#### Chuẩn hóa `BankTransaction`

- `direction = income` nếu `credit > 0`, ngược lại là `expense`
- `expense_total = abs(debit) + abs(fee) + abs(vat)`
- `amount`:
  - income -> `credit`
  - expense -> `expense_total`

Lưu ý quan trọng:

- Source hiện tại chưa lưu riêng `income_gross` và `income_net`
- Vì vậy các dòng thu có `fee/vat` có thể bị sót nếu hệ thống ghi số net thay vì gross

#### Metadata sao kê được đọc

- Bank name
- Tax code
- From date / To date
- Account number
- Account name
- Currency
- Account type
- Opening / actual / closing balance
- Total debits / credits / fees / VAT
- Total debit / credit transactions

## 7. Token và mã nghiệp vụ đang được source nhận diện

`app/services/utils.py` hiện tại nhận diện các reference token sau:

- `FT`
- `TT`
- `LD`
- `ST`
- `SK`
- `HB`

### Kết quả quét trên 4 bộ data mẫu

Nếu chỉ xét `Reference number` phía bank, các prefix chính xuất hiện là:

- `FT`
- `LD`
- `TT`
- `HB`
- thêm 1 kiểu numeric reference cho lãi ngân hàng:
  - `19135065170012-YYYYMMDD`

Ngoài ra, trong `Description` và `Summary` xuất hiện nhiều mã nghiệp vụ bổ trợ mà source hiện chưa coi là reference mạnh:

- `BHD...`
- `PPP_...`
- `PO...`
- `IV...`
- `LTVN...`
- `YH...`
- `HN-...`
- `HW-...`
- `SA...`
- `BL...`
- `TK...`
- `TBNP...`
- `MST...`
- `HAQZH...`
- `ZGNQZH...`
- `SITGQISG...`
- `SNK...`
- `KMTCBKK...`
- `BKKCB...`
- `NSSLBKHCC...`
- `LMCK...`
- `OT...`
- `IBBIZ...`

Kết luận:

- Không phải mã nào cũng là `reference mạnh`
- Có mã nên coi là `key nhóm nghiệp vụ`
- Có mã chỉ nên coi là `context hỗ trợ`

## 8. Logic đối soát hiện tại trong source

### 8.1. Nguyên tắc tổng quát

Source hiện tại:

- Lấy sao kê ngân hàng làm chuẩn tham chiếu
- Chỉ ghép cặp trong cùng nhóm `(direction, amount)`
- Sau đó tính điểm theo:
  - trùng reference token
  - độ lệch ngày
  - độ giống mô tả
  - có VAT hay không
  - nhóm số tiền có unique hay không

### 8.2. Các pass match hiện tại

1. `reference`
2. `voucher_unique`
3. `derived_unique`
4. `tax aggregate`
5. `scored`

#### Ý nghĩa từng pass

- `reference`: ưu tiên cặp có trùng reference token
- `voucher_unique`: ngày chứng từ trùng ngày, nhóm unique hoặc mutual closest
- `derived_unique`: ngày suy ra từ `SKYYYYMMDD-n` trùng ngày
- `tax aggregate`: gom riêng nhóm chi có VAT
- `scored`: vòng cuối cho các ca còn lại

### 8.3. Trạng thái đầu ra hiện tại

- `matched`
- `review`
- `unmatched`

Source hiện tại chưa có `matched_group` riêng. Nếu cần hỗ trợ group match trong tương lai, nên thêm trường phụ để phân biệt:

- `match_type = exact`
- `match_type = group`

## 9. Kiểm chứng trên data mẫu

Đã dò lại toàn bộ 4 bộ data mẫu và xác nhận:

### 9.1. Các rule hiện rất chắc

- `FT` ở nhóm chi trực tiếp từ hệ thống:
  - `238/238` dòng đúng theo `FT`
- `LD/ST` ở nghiệp vụ vay:
  - `392/392` dòng đúng theo `ST`
- `TT income`:
  - `14/14` dòng là nộp tiền
- `TT expense`:
  - `63/65` dòng khớp trực tiếp là rút tiền
  - `2` dòng còn lại là ca tách dòng
- `HB`:
  - `32/32` dòng `110,000` là phí Homebanking
- Lãi ngân hàng cuối tháng:
  - `3/3` dòng đúng

### 9.2. Các bằng chứng cho group match

Đã tìm thấy:

- `8` dòng bank `unmatched` thực ra bằng tổng `2` dòng system
- `6` dòng system `unmatched` thực ra bằng tổng `2` dòng bank

Ví dụ thật:

- `2025-12-11`:
  - bank `5,958,628,434`
  - system `958,628,434 + 5,000,000,000`
- `2026-01-13`:
  - bank `2,000,000,000`
  - system `1,111,487,842 + 888,512,158`
- `2026-02-04`:
  - bank `23,968,166`
  - system `10,926,017 + 13,042,149`
- `2026-03-25`:
  - system `64,439,000`
  - bank `24,749,000 + 39,690,000`

### 9.3. `Review` không đồng nghĩa với khớp đúng

Trên data mẫu có:

- `36` nhóm lặp số tiền gây mơ hồ
- tổng cộng `154` dòng review nằm trong các nhóm lặp số tiền

Ví dụ thật:

- `VỮNG PHÁT` có 2 dòng cùng số tiền, đúng tên đối tác, đúng ngày, nhưng đang bị đảo invoice
- `PHÚ HOA` bị review sang `HOÀNG QUÂN` chỉ vì cùng số tiền và gần ngày
- `BỐN NAM` bị review sang `Trong Sơn` chỉ vì cùng số tiền và trùng ngày

Kết luận:

- `review` chỉ có nghĩa là `có ứng viên`
- không được xem `review` là `đã khớp`

### 9.4. `Income có fee/vat` không có một công thức duy nhất

Ví dụ:

- `OWEN`:
  - bank `credit 1,174,222,483`
  - `fee -10,000`
  - `vat -1,000`
  - system ghi `1,174,211,483`
  - đây là trường hợp `net = credit + fee + vat`

Nhưng:

- Có dòng `TT` nộp tiền vẫn phải khớp theo `gross = credit`

Kết luận:

- Với `income có fee/vat`, engine phải thử cả `gross` và `net`
- Không được hard-code một công thức duy nhất

## 10. Quy tắc nghiệp vụ đề xuất để áp dụng vào source

Đây là phần spec nghiệp vụ cần chốt trước khi sửa code.

### 10.1. Mục tiêu nghiệp vụ

Tool phải trả lời được 4 câu hỏi:

1. Giao dịch nào đã khớp chắc
2. Giao dịch nào có thể khớp nhưng cần kiểm tra
3. Giao dịch nào có trong sao kê nhưng không có trong hệ thống
4. Giao dịch nào có trong hệ thống nhưng không có trong sao kê

### 10.2. Nguyên tắc chốt nghiệp vụ

- Sao kê vẫn là nguồn tham chiếu chính
- Đối soát phải làm 2 chiều
- Không ép match nếu bằng chứng chưa đủ
- `amount + date` không đủ để tự động kết luận
- Chỉ chấp nhận chênh tiền nếu giải thích được bởi `fee/vat`
- Nếu khác đối tác, khác invoice, khác `ST/BHD/PO/BL/contract` rõ ràng thì không được auto-match

### 10.3. Phân loại giao dịch trước khi match

Engine nên phân giao dịch thành các họ giao dịch:

1. `direct_bank_payment`
2. `loan`
3. `cash_withdrawal`
4. `cash_deposit`
5. `homebanking_fee`
6. `bank_interest`
7. `salary`
8. `customer_receipt`
9. `refund_adjustment`
10. `logistics_import_tax_fee`

### 10.4. Key mạnh và key phụ

#### Key mạnh

Chỉ được coi là key mạnh trong phạm vi nghiệp vụ phù hợp:

- `FT` cho chi trực tiếp
- `ST` cho vay
- `BHD` cho vay
- `TT` cho nộp/rút tiền
- `HB` cho Homebanking
- `19135065170012-YYYYMMDD` cho lãi ngân hàng cuối tháng

#### Key phụ

Dùng để tăng độ tin cậy, gom nhóm, hoặc veto:

- `PPP`
- `SK`
- `invoice / HD / IV`
- `PO`
- `BL`
- `TK`
- `contract`
- `LTVN`
- `YH / HN / HW / SA`
- `HAQZH / ZGNQZH / SITGQISG / SNK / KMTCBKK / BKKCB / NSSLBKHCC / LMCK`

### 10.5. Rule theo từng họ giao dịch

#### A. Direct bank payment

Áp dụng khi:

- Hệ thống là `expense`
- Trong summary có `FT...`

Rule:

- Match exact theo `FT`
- Sau đó kiểm tra thêm `direction`, `amount`, `date`
- Nếu `FT` khớp thì có thể auto-match

Lưu ý:

- Không mở rộng rule này cho tất cả dòng `income`
- Refund có thể tham chiếu đến `FT cũ` trong system nhưng bank lại phát sinh `FT mới`

#### B. Loan

Áp dụng khi thấy:

- `LD...`
- `ST...`
- `BHD...`
- mô tả có `Thu no goc`, `Thu no lai`, `支付银行货款`, `支付银行货款利息`

Rule:

- `ST` hoặc `BHD` là key chính
- `LD` là key phụ
- Match theo:
  - `ST/BHD`
  - loại dòng `gốc/lãi`
  - `direction`
  - `amount`
  - `date`

#### C. Cash withdrawal

Áp dụng khi:

- Bank `TT...` và mô tả là `RÚT TIỀN`
- Hệ thống mô tả `取现金` hoặc `取款`

Rule:

- Ưu tiên `1-1` theo `amount + date`
- Nếu không có `1-1`, cho phép `1-n` hoặc `n-1`
- Có thể gom nhóm rút tiền cùng ngày để đối chiếu 1 dòng hệ thống

#### D. Cash deposit

Áp dụng khi:

- Bank `TT...` và mô tả là `NỘP TIỀN`
- Hệ thống mô tả `存钱`

Rule:

- Ưu tiên `1-1`
- Nếu cần, thử thêm `gross` và `net`
- Nếu cùng ngày có nhiều dòng nộp tiền cùng nghiệp vụ, cho phép match theo nhóm

#### E. Homebanking fee

Áp dụng khi:

- `HB...`
- Mô tả `Thu phí Homebanking`

Rule:

- Gom theo tháng / ngày
- Hiện tại data mẫu là `8 x 110,000 = 880,000`
- Match theo tổng nhóm, không match từng dòng riêng với từng dòng hệ thống

#### F. Bank interest

Áp dụng khi:

- `Reference number = 19135065170012-YYYYMMDD`
- Description chứa `Tra lai so du tren tai khoan`

Rule:

- Match exact theo:
  - loại giao dịch
  - amount
  - ngày cuối tháng
  - mô tả là nhóm lãi ngân hàng

#### G. Salary

Áp dụng khi:

- Description có `PPP_...`
- Hoặc text là `TRẢ LƯƠNG`, `工资`, `奖金`

Rule:

- Ưu tiên group match
- Dùng:
  - ngày
  - tháng lương
  - `PPP`
  - tổng số tiền

Cho phép:

- `1 system = nhiều bank`
- `nhiều system = 1 bank`
- `n-n` chỉ được coi là cụm nghi vấn để rà soát, không được auto-match

#### H. Customer receipt

Áp dụng khi:

- Thu khách hàng
- Thu theo hóa đơn
- Thu theo prepayment
- Chuyển nội bộ của công ty liên quan

Rule:

- Không được chỉ dùng `amount + date`
- Thứ tự ưu tiên:
  1. tên đối tác / alias
  2. invoice / contract / mô tả nghiệp vụ
  3. amount
  4. date
- Nếu có `fee/vat`, phải thử cả `gross` và `net`
- Cho phép `1-1`, `1-n`, `n-1`
- Nếu xuất hiện `n-n` thì chỉ coi là cụm nghi vấn, không được auto-match

#### I. Refund / adjustment

Áp dụng khi:

- text chứa `refund`, `hoàn trả`, `退还`, `wrong payment`, `adjustment`

Rule:

- Không được coi `FT cũ` là key exact duy nhất
- Phải đối thêm:
  - đối tác
  - nghiệp vụ
  - amount
  - date
  - bằng chứng refund

#### J. Logistics / import / tax / local charge

Áp dụng khi có các mã nghiệp vụ:

- `PO`
- `BL`
- `IV`
- `TK`
- `contract`
- `LTVN`
- `YH / HN / HW / SA`
- `HAQZH / ZGNQZH / SITGQISG / SNK / KMTCBKK / BKKCB / NSSLBKHCC / LMCK`

Rule:

- Đây thường là nghiệp vụ theo lô hàng / tờ khai / bill / invoice
- Match theo `group key`, không match chỉ bằng 1 mã đơn lẻ
- `group key` đề xuất:
  - đối tác
  - `PO`
  - `BL`
  - `invoice`
  - `TK`
  - ngày
  - tổng tiền

### 10.6. Rule group match

Engine mới bắt buộc hỗ trợ đầy đủ:

- `1-1`
- `1-n`
- `n-1`

Ngoài ra, engine nên có khả năng phát hiện `n-n` như một cụm nghi vấn để hỗ trợ người dùng rà soát, nhưng không được tự động gắn là khớp.

#### Nghĩa để hiểu

- `1-1`: 1 dòng hệ thống đối 1 dòng bank
- `1-n`: 1 dòng hệ thống đối tổng nhiều dòng bank
- `n-1`: nhiều dòng hệ thống đối 1 dòng bank
- `n-n`: nhiều dòng hệ thống đối nhiều dòng bank trong cùng 1 nhóm nghiệp vụ

#### Nguyên tắc group match

Chỉ được coi là `matched group` khi:

- cùng `direction`
- tổng tiền bằng nhau
- ngày hợp lý
- cùng đối tác hoặc cùng key nhóm nghiệp vụ
- chỉ có 1 tổ hợp hợp lý rõ ràng

Phạm vi áp dụng `matched group`:

- chỉ áp dụng cho `1-n`
- hoặc `n-1`
- không áp dụng cho `n-n`

Nếu có nhiều tổ hợp đều hợp lý:

- để `review`
- không ép chọn 1 tổ hợp bất kỳ

Nếu phát hiện `n-n`:

- không được auto-match
- mặc định coi là `unmatched`
- có thể lưu cờ nội bộ hoặc hiển thị hint để người dùng biết đây là cụm nghi vấn

### 10.7. Rule xếp trạng thái

#### Matched exact

Khi:

- có một cặp `1-1` rõ ràng
- có key mạnh hoặc bằng chứng đầy đủ

#### Matched group

Khi:

- không phải `1-1`
- nhưng có một nhóm đối ứng duy nhất và hợp lý

Giới hạn:

- chỉ áp dụng cho `1-n` hoặc `n-1`
- không áp dụng cho `n-n`

UI hiện tại chưa tách riêng trạng thái này. Đề xuất:

- vẫn hiển thị `matched`
- nhưng lưu thêm `match_type = group`

#### Review

Khi:

- có ứng viên hợp lý
- nhưng chưa đủ bằng chứng để kết luận
- hoặc có nhiều tổ hợp cùng hợp lý

#### Unmatched

Chỉ dùng khi:

- đã thử hết rule hợp lệ mà vẫn không có đối ứng đúng nghiệp vụ

Ngoài ra, trong bản đặc tả an toàn hiện tại:

- mọi trường hợp `n-n` đều mặc định xếp vào `unmatched`
- không được tự động hạ xuống `matched group`

## 11. Triển khai để áp dụng vào source

Phần này mô tả các thay đổi cần làm trong code. Không phải toàn bộ đã tồn tại trong source hiện tại.

### 11.1. `app/models.py`

Nên bổ sung:

- `transaction_family`
- `match_type`
- `party_name`
- `party_name_normalized`
- `business_tokens`
- `group_key`
- `amount_gross`
- `amount_net`
- `evidence_flags`

Ý nghĩa:

- để tách `exact` và `group`
- để lưu key mạnh / key phụ
- để hiển thị popup giải thích rõ hơn

### 11.2. `app/services/utils.py`

Cần bổ sung:

- bộ extractor cho:
  - `BHD`
  - `PPP`
  - `PO`
  - `BL`
  - `IV`
  - `TK`
  - `contract`
  - các mã logistics/import
- hàm normalize tên đối tác / alias
- hàm classify transaction family
- hàm parse reference số học cho lãi ngân hàng

Đề xuất thêm:

- alias map cho tên đối tác
- helper trích xuất invoice set
- helper trích xuất month salary

### 11.3. `app/services/excel_loader.py`

Cần nâng cấp:

- Loader system nên tìm đúng header row thay vì cố định dòng 1
- Bank row nên lưu:
  - `income_gross = credit`
  - `income_net = credit + fee + vat`
  - `expense_total = abs(debit) + abs(fee) + abs(vat)`
- Trích sẵn:
  - party name
  - business tokens
  - transaction family
  - group key sơ bộ

### 11.4. `app/services/reconciliation.py`

Cần đổi từ engine score chung sang engine lai ghép theo lớp:

#### Phase 0. Classify

- Phân loại mỗi dòng vào transaction family

#### Phase 1. Exact match

- `FT` direct payment
- `loan ST/BHD`
- `TT` 1-1 rõ ràng
- `HB`
- `bank interest`

#### Phase 2. Group match

- salary
- logistics/import/tax
- customer receipt bị tách/gộp
- cash withdrawal / deposit bị tách/gộp

#### Phase 3. Review

- giữ lại những ca mơ hồ
- không force match

#### Phase 4. Final unmatched

- đánh dấu những dòng không còn đối ứng hợp lý

#### Veto rules bắt buộc

Không được auto-match nếu:

- khác đối tác rõ ràng
- khác invoice rõ ràng
- khác `ST/BHD/PO/BL/contract` rõ ràng
- khác loại nghiệp vụ rõ ràng

### 11.5. `app/ui/main_window.py`

Đề xuất nâng cấp:

- Cho hiển thị `match_type = exact/group`
- Thêm filter hoặc chip thống kê cho `group match`
- Bổ sung reference filter nếu cần:
  - `TT`
  - `BHD`
- Popup đối ứng nên hiển thị:
  - transaction family
  - match type
  - evidence chính
  - veto nếu có

### 11.6. `app/services/exporter.py`

Đề xuất bổ sung cột xuất:

- `status`
- `match_type`
- `matched_row`
- `confidence`
- `match_reason`

Khi đó file xuất sẽ dùng được cho kế toán / kiểm soát xem lại mà không cần mở app.

### 11.7. `tests/`

Cần bổ sung test cho:

- `1-n`
- `n-1`
- `n-n` candidate detection
- `income net/gross`
- `TT deposit/withdraw`
- `PPP salary`
- `BHD loan`
- `veto party mismatch`
- `veto invoice mismatch`
- `review repeated amount groups`

## 12. Giới hạn hiện tại của source

Những điểm cần ghi rõ để tránh hiểu nhầm:

1. Source hiện tại chủ yếu là engine `1-1`
2. Mới có special case group cho VAT/Homebanking
3. Chưa có engine group tổng quát cho lương, phí, doanh thu bị tách/gộp
4. Chưa xử lý đúng ca `income gross/net`
5. Chưa coi `19135065170012-YYYYMMDD` là key riêng
6. Chưa đưa `PPP`, `BHD`, `PO`, `BL`, `IV`, `TK`, `contract` vào lớp nghiệp vụ
7. Reference filter trên UI hiện chỉ có `FT/ST/SK/LD/HB`
8. File system detect linh hoạt hơn file loader thực tế

## 13. Quy trình sử dụng hiện tại

1. Chạy `main.py`
2. Chọn file hệ thống
3. Chọn file sao kê
4. Bấm `Dò sao kê`
5. Xem tổng hợp
6. Lọc `review` / `unmatched`
7. Mở popup đối ứng để xem căn cứ
8. Xuất Excel theo bộ lọc hiện tại nếu cần

## 14. Cài đặt và chạy source

### Cài thư viện

```powershell
python -m pip install -r requirements.txt
```

### Chạy source

```powershell
python main.py
```

## 15. Build file exe

Script build hiện tại:

```powershell
.\build_exe.bat
```

Script sẽ:

- bật UTF-8
- cài dependencies
- tạo icon từ `logo\logo.png`
- build PyInstaller onefile windowed

File output:

```text
dist\BSRv1.0.exe
```

## 16. Khuyến nghị chốt nghiệp vụ trước khi sửa code

Cần chốt bằng văn bản 4 điểm sau:

1. Có dùng `matched group` nội bộ hay không
2. Những transaction family nào sẽ được support ở phase 1
3. Key nào là `key mạnh`, key nào là `key phụ`
4. Veto rules nào là bắt buộc

Nếu chốt xong 4 điểm này, việc sửa code sẽ an toàn hơn rất nhiều và tránh ghép sai giao dịch liên quan đến tiền.

## 17. Tóm tắt ngắn gọn

Tình hình hiện tại:

- Source đã có UI, loader, export, history, logging, đa ngôn ngữ
- Engine hiện tại làm tốt `FT chi`, `loan ST`, `TT`, `HB`, `lãi ngân hàng`
- Engine hiện tại chưa đủ cho `1-n`, `n-1`, phát hiện `n-n` an toàn, `income gross/net`, và các nghiệp vụ logistics/import/salary/thu khách bị tách-gộp

Spec nghiệp vụ đề xuất:

- Có mã mạnh thì match exact
- Không có mã mạnh thì match theo transaction family và group key
- Có 1 tổ hợp rõ ràng thì `matched`
- Có nhiều tổ hợp hợp lý thì `review`
- Nếu là `n-n` thì không auto-match, mặc định `unmatched`
- Thử hết rule mà vẫn không có đối ứng đúng nghiệp vụ thì `unmatched`

README này được viết để làm tài liệu tham chiếu cho:

- Người vận hành tool
- Người review nghiệp vụ
- Người sửa source
