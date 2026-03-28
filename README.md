# Tool Đối Soát Sao Kê Ngân Hàng

## Giới thiệu

Đây là công cụ desktop viết bằng Python dùng để đối chiếu:

- File giao dịch từ hệ thống nội bộ
- File sao kê ngân hàng Techcombank

Mục tiêu của tool là hỗ trợ người dùng kiểm tra xem toàn bộ giao dịch trong file hệ thống có khớp với sao kê ngân hàng hay không, từ đó nhanh chóng phát hiện các dòng:

- Khớp
- Cần kiểm tra lại
- Không khớp

Ứng dụng được thiết kế để có thể chạy nội bộ trên máy Windows, đồng thời có thể build ra file `.exe` để mang sang máy khác sử dụng.

## Mục tiêu của tool

Tool tập trung giải quyết các vấn đề thực tế sau:

- File hệ thống là file nhập tay nên ngày giao dịch có thể không hoàn toàn trùng sao kê.
- Cùng một số tiền có thể lặp lại nhiều lần trong tháng, cần có thêm logic để giảm nhầm lẫn khi dò.
- Người dùng cần nhìn nhanh các giao dịch không khớp để xử lý.
- Cần giữ giao diện dễ dùng cho người không chuyên kỹ thuật.

## Công nghệ sử dụng

- Python
- PySide6: giao diện desktop
- `openpyxl`: đọc/ghi file `.xlsx`
- `xlrd`: đọc file `.xls`
- SQLite: lưu lịch sử đối soát
- PyInstaller: build file `.exe`

## Tính năng chính

- Giao diện một màn hình duy nhất.
- Chỉ hiển thị một lưới dữ liệu tại một thời điểm để tránh rối giao diện.
- Mặc định hiển thị lưới `Hệ thống`.
- Có nút chuyển nhanh để đổi giữa `Hệ thống` và `Sao kê`.
- Khi chưa chọn đủ 2 file và chưa bấm dò, phần kết quả sẽ bị khóa.
- Sau khi chọn đủ file và bấm `Dò sao kê`, phần kết quả sẽ được mở.
- Có loading overlay trong lúc xử lý.
- Có thanh cuộn dọc cho toàn màn hình để ưu tiên hiển thị lưới dữ liệu.
- Hỗ trợ lọc, sắp xếp và tìm kiếm trên lưới.
- Có bộ lọc trạng thái:
  - Tất cả
  - Chỉ hiện khớp
  - Chỉ hiện không khớp
- Có bộ lọc loại giao dịch:
  - Tất cả giao dịch
  - Chỉ hiện thu
  - Chỉ hiện chi
  - Chỉ hiện thuế
- Có bộ lọc mã tham chiếu Techcombank:
  - Tất cả mã TCB
  - FT
  - ST
  - SK
  - LD
  - HB
- Có cột đầu tiên cố định với nút `Mở` để xem giao dịch đối ứng.
- Có lưu lịch sử đối soát sau mỗi lần chạy.
- Có ghi log xử lý để tiện kiểm tra lỗi.
- Hỗ trợ 3 ngôn ngữ:
  - Tiếng Việt mặc định
  - English
  - 中文简体

## Giao diện tổng quan

Giao diện được chia thành các khu vực chính:

### 1. Khu vực chọn file

Người dùng chọn:

- File hệ thống
- File sao kê ngân hàng

Sau đó có thể:

- Chọn ngôn ngữ
- Bấm `Dò sao kê`
- Bấm `Xuất Excel`
- Chọn thêm tùy chọn `Kèm sheet sao kê`

### 2. Khu vực lịch sử đối soát

Hiển thị các lần chạy gần đây, bao gồm:

- Thời gian chạy
- Tên file hệ thống
- Tên file sao kê
- Tổng quan kết quả

### 3. Khu vực thông tin sao kê

Thông tin này được lấy từ file sao kê ngân hàng và chỉ hiển thị sau khi đối soát xong. Các thông tin chính gồm:

- Tên ngân hàng
- Mã số thuế
- Kỳ sao kê
- Số tài khoản
- Tên tài khoản
- Loại tiền
- Loại tài khoản
- Số dư đầu kỳ
- Số dư hiện tại
- Số dư cuối kỳ
- Tổng ghi nợ
- Tổng ghi có
- Tổng phí
- Tổng VAT
- Tổng lệnh ghi nợ
- Tổng lệnh ghi có

### 4. Khu vực kết quả đối soát

Khu vực này là phần quan trọng nhất:

- Chỉ hiển thị một lưới tại một thời điểm
- Mặc định là lưới `Hệ thống`
- Có nút chuyển sang lưới `Sao kê`
- Có bộ lọc trạng thái, loại giao dịch, mã TCB
- Có ô tìm kiếm theo từng lưới
- Có chọn cột tìm kiếm hoặc tìm trên toàn bộ cột
- Có hỗ trợ sort theo cột
- Có scroll trong lưới

## Quy tắc dữ liệu đầu vào

Tool hiện được thiết kế theo đúng format của hai file mẫu/thực tế trong thư mục `File`.

### File hệ thống

- Định dạng: `.xls`
- File mẫu thực tế: `Hệ Thống.xls`

### File sao kê

- Định dạng: `.xlsx`
- File mẫu thực tế: `TRANSACTION_HISTORY__1774658366122.xlsx`

Lưu ý:

- Tool đang giả định cấu trúc cột của hai file đầu vào luôn giống file mẫu.
- Nếu ngân hàng hoặc hệ thống thay đổi format cột, logic đọc file có thể cần cập nhật lại.

## Quy tắc đối soát hiện tại

Tool lấy **file sao kê ngân hàng làm chuẩn**.

Điều này có nghĩa:

- Sao kê là nguồn dữ liệu tham chiếu chính
- File hệ thống được đối chiếu ngược lại theo sao kê
- Ngày giao dịch ở file hệ thống có thể lệch so với sao kê vì là dữ liệu nhập tay

### Các cột được dùng để đối soát

#### Trên file sao kê

Tool chỉ quan tâm các cột:

- `Nợ/Debit`
- `Có/Credit`
- `Phí/Lãi Fee/Interest`
- `Thuế/Transaction VAT`

Diễn giải:

- `Có/Credit` được xem là giao dịch thu
- `Nợ/Debit`, `Fee/Interest`, `Transaction VAT` được xem là giao dịch chi

#### Trên file hệ thống

Tool chỉ quan tâm các cột:

- `金额贷方`
- `金额借方`

Theo dữ liệu thực tế đã xác nhận:

- `金额借方` đối ứng với `Có/Credit`
- `金额贷方` đối ứng với `Nợ/Debit + Fee/Interest + VAT`

### Chuẩn hóa số tiền

Toàn bộ số tiền được chuẩn hóa theo VND để phục vụ việc:

- So sánh số tiền
- Sắp xếp
- Tô màu giá trị âm
- Lọc và dò chính xác hơn

### Logic ghép cặp

Tool ưu tiên ghép cặp dựa trên nhiều tín hiệu kết hợp, không chỉ dựa vào một cột duy nhất. Cụ thể:

- Hướng giao dịch: thu hoặc chi
- Số tiền sau khi chuẩn hóa
- Mã tham chiếu nếu có trong mô tả
- Độ gần nhau của ngày giao dịch
- Mức độ giống nhau của mô tả giao dịch

### Mã tham chiếu Techcombank đang hỗ trợ

Các prefix hiện được nhận diện:

- `FT`: chuyển khoản
- `ST`: chuyển khoản nội bộ hoặc chuyển khoản định kỳ
- `SK`: giao dịch dịch vụ/hệ thống
- `LD`: giao dịch khoản vay
- `HB`: giao dịch ngân hàng điện tử

### Trạng thái đối soát

Mỗi dòng sẽ được gán một trạng thái:

- `Khớp`: tìm được đối ứng đáng tin cậy
- `Cần kiểm tra`: đã có ứng viên phù hợp nhưng nên rà lại
- `Không khớp`: chưa tìm được đối ứng tin cậy

### Ý nghĩa màu sắc

- Màu xanh: khớp
- Màu vàng: cần kiểm tra lại
- Màu đỏ: không khớp

Ngoài ra:

- Các ô số âm trên lưới sẽ hiển thị chữ màu đỏ

## Cách sử dụng

### Bước 1. Chạy ứng dụng

Chạy file `main.py` hoặc chạy file `.exe` sau khi build.

### Bước 2. Chọn file

Tại giao diện chính:

- Chọn file hệ thống
- Chọn file sao kê

Nếu chưa chọn đủ 2 file mà bấm `Dò sao kê`, tool sẽ cảnh báo và phần kết quả vẫn bị khóa.

### Bước 3. Bấm `Dò sao kê`

Sau khi bấm:

- Tool hiển thị loading
- Đọc dữ liệu từ 2 file
- Chuẩn hóa dữ liệu
- Thực hiện ghép cặp và phân loại kết quả
- Hiển thị thông tin sao kê
- Hiển thị kết quả đối soát trên lưới
- Lưu lịch sử vào cơ sở dữ liệu
- Ghi log xử lý

### Bước 4. Xem kết quả

Mặc định tool hiển thị lưới `Hệ thống`.

Người dùng có thể:

- Bấm nút chuyển để xem `Sao kê`
- Lọc `Khớp`, `Không khớp`, `Tất cả`
- Lọc `Thu`, `Chi`, `Thuế`
- Lọc theo mã TCB
- Tìm kiếm theo một cột hoặc toàn bộ cột
- Sort theo cột

### Bước 5. Xem giao dịch đối ứng

Tại cột đầu tiên của lưới có nút `Mở`.

Khi bấm:

- Tool sẽ chọn dòng đối ứng ở lưới còn lại nếu có
- Đồng thời mở popup chi tiết để so sánh nhanh hai bên

### Bước 6. Xuất Excel

Người dùng bấm `Xuất Excel` để xuất dữ liệu của lưới hệ thống theo đúng trạng thái filter hiện tại.

Quy tắc xuất hiện tại:

- Nếu đang chọn `Chỉ hiện không khớp`:
  - File xuất không tô màu
- Nếu đang chọn `Tất cả`:
  - File xuất giữ toàn bộ dữ liệu đang hiển thị
  - Các dòng không khớp sẽ được tô đỏ

Tên file mặc định khi xuất:

- Lấy theo tên file hệ thống đã chọn
- Ví dụ: chọn `Hệ Thống.xls` thì mặc định sẽ gợi ý lưu thành `Hệ Thống.xlsx`

### Tùy chọn kèm sheet sao kê

Nếu bật checkbox `Kèm sheet sao kê` khi xuất:

- File Excel xuất ra sẽ có thêm một sheet chứa toàn bộ nội dung file sao kê gốc

Sheet này chỉ là bản đính kèm dữ liệu gốc:

- Không tô màu theo logic đối soát
- Giữ nguyên nội dung sao kê để tiện đối chiếu thêm

## Lưu lịch sử và log

### Lịch sử đối soát

Mỗi lần chạy xong, tool lưu lịch sử tại:

```text
data/history.sqlite
```

Thông tin lưu gồm:

- Thời gian đối soát
- Tên file hệ thống
- Tên file sao kê
- Số lượng giao dịch khớp
- Số lượng giao dịch cần kiểm tra
- Số lượng giao dịch không khớp

### Log xử lý

Tool ghi log chi tiết tại:

```text
data/logs/tool_doi_soat.log
```

Log được ghi cho các bước như:

- Khởi động ứng dụng
- Chọn file
- Đổi ngôn ngữ
- Bắt đầu đối soát
- Đọc file hệ thống
- Đọc file sao kê
- Ghép cặp giao dịch
- Áp bộ lọc
- Xuất Excel
- Lỗi phát sinh nếu có

## Cài đặt môi trường

### Yêu cầu

- Windows
- Python 3

### Cài thư viện

Nếu máy có `python` trong `PATH`, chạy:

```powershell
python -m pip install -r requirements.txt
```

Nếu máy dùng Python tại đường dẫn như script build hiện tại:

```powershell
"C:\Program Files\PyManager\python.exe" -m pip install -r requirements.txt
```

## Chạy tool từ mã nguồn

```powershell
python main.py
```

Hoặc:

```powershell
"C:\Program Files\PyManager\python.exe" main.py
```

## Build file `.exe`

Chạy script:

```powershell
.\build_exe.bat
```

Script hiện tại sẽ:

- Chuyển console sang UTF-8
- Bật `PYTHONUTF8=1`
- Cài thư viện từ `requirements.txt`
- Build bằng PyInstaller

Tên file build hiện tại:

```text
BSRv1.0
```

Sau khi build xong, file thực thi sẽ nằm tại:

```text
dist\BSRv1.0
```

## Thư mục quan trọng

```text
app/                  Mã nguồn chính của ứng dụng
app/ui/               Giao diện người dùng
app/services/         Xử lý đọc file, đối soát, export, log, history
data/history.sqlite   Cơ sở dữ liệu lưu lịch sử
data/logs/            Thư mục log
File/                 Chứa file mẫu/file thực tế để test
build_exe.bat         Script build file exe
main.py               Điểm khởi động ứng dụng
```

## Lưu ý khi sử dụng

- Tool hiện tối ưu cho đúng format hai file mẫu/thực tế đang có.
- Nếu file đầu vào đổi tên cột hoặc đổi vị trí vùng dữ liệu, cần kiểm tra lại bộ đọc Excel.
- Trạng thái `Cần kiểm tra` không phải là sai chắc chắn, mà là cần người dùng rà thêm.
- Khi nhiều giao dịch có cùng số tiền, tool sẽ cố giảm nhầm bằng cách dùng thêm ngày, mô tả và mã tham chiếu.
- Tuy vậy, với dữ liệu nhập tay, vẫn nên kiểm tra lại các giao dịch nghi ngờ trước khi kết luận cuối cùng.

## Gợi ý quy trình sử dụng thực tế

1. Chọn file hệ thống và file sao kê.
2. Bấm `Dò sao kê`.
3. Kiểm tra nhanh phần tổng quan và thông tin sao kê.
4. Chuyển filter sang `Chỉ hiện không khớp`.
5. Rà từng dòng bằng nút `Mở`.
6. Nếu cần gửi người khác xử lý, dùng `Xuất Excel`.
7. Nếu cần gửi kèm dữ liệu gốc, bật `Kèm sheet sao kê`.

## Phiên bản ngôn ngữ

Ứng dụng hỗ trợ 3 ngôn ngữ:

- Tiếng Việt
- English
- 中文简体

Trong đó:

- Tiếng Việt là ngôn ngữ mặc định
- Nội dung tiếng Việt đã được chỉnh sang dạng có dấu
- Nội dung tiếng Trung được hiển thị bằng chữ Hán để dễ hiểu hơn

## Ghi chú

README này mô tả theo trạng thái hiện tại của ứng dụng trong repository. Nếu có thay đổi thêm về:

- Quy tắc đối soát
- Bộ lọc
- Xuất file
- Tên file build
- Cấu trúc giao diện

thì nên cập nhật lại README để đồng bộ với tool.
