# Nghiệp Vụ Và Quy Tắc Dò Giao Dịch

## 1. Mục đích của tài liệu

Tài liệu này mô tả nghiệp vụ đối soát sao kê theo cách dễ hiểu cho người dùng, kế toán, kiểm soát nội bộ, hoặc người mới tiếp nhận tool.

Tài liệu này **không** mô tả theo kiểu code hay thuật toán chi tiết. Mục tiêu là giúp người đọc hiểu:

- tool đang đối chiếu cái gì
- tool dùng những dấu hiệu nào để dò
- khi nào một giao dịch được coi là khớp
- khi nào một giao dịch chỉ nên đưa vào cần kiểm tra
- khi nào một giao dịch phải giữ là chưa khớp

---

## 2. Mục tiêu của tool

Tool được dùng để đối soát giữa:

- file giao dịch từ hệ thống nội bộ
- file sao kê ngân hàng

Kết quả mong muốn là:

- tìm ra các giao dịch đã khớp chắc
- tách các giao dịch cần người dùng kiểm tra thêm
- chỉ ra các giao dịch có trong sao kê nhưng chưa thấy trong hệ thống
- chỉ ra các giao dịch có trong hệ thống nhưng chưa thấy trong sao kê

Nguyên tắc quan trọng nhất của tool là:

- **không ép khớp cho đủ**
- **ưu tiên an toàn hơn là ghép sai**

---

## 3. Hai nguồn dữ liệu được hiểu như thế nào

### 3.1. Sao kê ngân hàng

Đây là nguồn dữ liệu thực tế phát sinh tại ngân hàng.

Trong nghiệp vụ đối soát hiện tại, sao kê được xem là nguồn chuẩn chính để đối chiếu.

Tool sẽ đọc các thông tin như:

- ngày giao dịch
- số tiền thu hoặc chi
- phí
- VAT
- mã giao dịch
- tên đối tác
- tài khoản đối tác
- nội dung diễn giải

### 3.2. Hệ thống nội bộ

Đây là dữ liệu hạch toán hoặc nhập tay từ phía doanh nghiệp.

Do là dữ liệu nhập tay nên có thể có các khác biệt như:

- nhập chậm hơn vài ngày so với ngày trên sao kê
- mô tả không giống hệt sao kê
- một giao dịch ngoài ngân hàng nhưng trong hệ thống có thể bị tách thành nhiều dòng
- hoặc ngược lại, nhiều giao dịch ngân hàng lại được gom thành một dòng trong hệ thống

Vì vậy, tool **không được xem ngày hệ thống là điều kiện cứng tuyệt đối**.

---

## 4. Ba trạng thái kết quả

### 4.1. Khớp

`Khớp` nghĩa là tool có đủ căn cứ để tin rằng hai bên thực sự là cùng một nghiệp vụ.

Đây là trạng thái có độ tin cậy cao nhất.

### 4.2. Cần kiểm tra

`Cần kiểm tra` nghĩa là tool đã tìm được ứng viên đối ứng hợp lý, nhưng chưa đủ chắc để tự khẳng định là khớp.

Trạng thái này dùng để:

- giảm số giao dịch bị đánh đỏ oan
- nhưng vẫn không ghép sai một cách tự động

### 4.3. Chưa khớp

`Chưa khớp` nghĩa là sau khi đã dò hết các cách hợp lệ, tool vẫn chưa tìm được đối ứng hợp lý hoặc chưa đủ an toàn để kết luận.

Chỉ những giao dịch thật sự chưa có đối ứng phù hợp mới nên nằm ở trạng thái này.

---

## 5. Tool dùng những dấu hiệu nào để dò

Khi đối chiếu, tool sẽ không nhìn vào một yếu tố duy nhất. Tool kết hợp nhiều dấu hiệu:

- chiều giao dịch: thu hoặc chi
- số tiền
- ngày giao dịch
- mã tham chiếu ngân hàng
- mã tham chiếu trích từ mô tả
- tên đối tác
- tài khoản đối tác
- diễn giải giao dịch
- số hóa đơn, hợp đồng, bill, tờ khai, mã khế ước hoặc các key nghiệp vụ khác nếu có

Trong đó:

- **chiều giao dịch** và **số tiền** là nền tảng quan trọng nhất
- **ngày** là dấu hiệu hỗ trợ
- **mô tả, đối tác, mã giao dịch** là dấu hiệu tăng độ tin cậy

---

## 6. Nguyên tắc về ngày giao dịch

Ngày giao dịch phải được hiểu là **tín hiệu mềm**, không phải điều kiện cứng.

Lý do:

- phía hệ thống là dữ liệu nhập tay
- có thể ghi nhận sau vài ngày so với ngày thực tế trên sao kê
- đặc biệt với các khoản phí, lương, công nợ hoặc bút toán nội bộ

Quy tắc nên hiểu như sau:

- cùng ngày: tín hiệu mạnh
- lệch 1 đến 3 ngày: vẫn hoàn toàn hợp lý
- lệch 4 đến 7 ngày: vẫn có thể hợp lý nếu có thêm bằng chứng khác
- lệch trên 7 ngày: thường không nên tự tin, trừ khi có mã hoặc key nghiệp vụ rất rõ

Tóm lại:

- **ngày không đủ để tự khớp**
- nhưng **ngày cũng không nên làm mất cơ hội đối chiếu** nếu các dấu hiệu khác vẫn tốt

---

## 7. Những mô hình đối chiếu cần hiểu

### 7.1. Một dòng hệ thống khớp một dòng sao kê (`1-1`)

Đây là trường hợp đơn giản và an toàn nhất.

Ví dụ:

- hệ thống có một dòng chi
- sao kê có một dòng chi đúng số tiền đó
- ngày và mô tả cũng hợp lý

Nếu đủ bằng chứng, đây là `Khớp`.

### 7.2. Một dòng hệ thống khớp nhiều dòng sao kê (`1-n`)

Đây là trường hợp:

- hệ thống ghi một dòng tổng
- nhưng ngân hàng lại tách ra thành nhiều dòng

Ví dụ hay gặp:

- phí và VAT
- lương bị tách nhiều dòng
- một khoản chi được bank chia ra nhiều bút toán

Nếu tổng tiền bằng nhau và tổ hợp là duy nhất, đây có thể là `Khớp`.

### 7.3. Nhiều dòng hệ thống khớp một dòng sao kê (`n-1`)

Đây là trường hợp ngược lại:

- phía hệ thống tách nhiều dòng
- nhưng sao kê chỉ có một dòng tổng

Ví dụ:

- một khách hàng thanh toán một lần
- nhưng hệ thống hạch toán thành nhiều dòng hóa đơn hoặc nhiều khoản mục

Nếu tổng tiền bằng nhau và tổ hợp là duy nhất, đây cũng có thể là `Khớp`.

### 7.4. Nhiều dòng hệ thống khớp nhiều dòng sao kê (`n-n`)

Đây là trường hợp khó nhất.

Ví dụ:

- hai bên đều có nhiều dòng cùng số tiền
- cùng khoảng ngày
- cùng đối tác hoặc cùng nhóm nghiệp vụ

Trường hợp này phải chia làm hai loại:

- `n-n` có key riêng từng dòng: nên đưa vào `Cần kiểm tra`
- `n-n` mơ hồ thật: phải giữ `Chưa khớp`

Nguyên tắc an toàn:

- **`n-n` không được auto-match**

---

## 8. Nhóm giao dịch đang được hiểu như thế nào

### 8.1. FT

`FT` thường là giao dịch chuyển khoản có mã tham chiếu rõ.

Đây là nhóm có độ tin cậy cao khi:

- cùng chiều
- cùng số tiền
- mã trùng hoặc mô tả rất rõ

### 8.2. TT

`TT` thường là nhóm giao dịch nộp tiền hoặc rút tiền.

Nhóm này có thể có:

- mô tả rất ngắn
- ít thông tin đối tác

Vì vậy cần nhìn thêm:

- số tiền
- ngày
- hướng giao dịch
- ngữ cảnh của mô tả

### 8.3. LD / ST

Đây là nhóm liên quan đến khoản vay, khế ước, gốc và lãi.

Nhóm này có giá trị nghiệp vụ cao, nhưng không phải lúc nào cũng unique theo từng dòng.

Vì vậy:

- `ST` thường được xem là key nhóm mạnh
- `LD` là tín hiệu hỗ trợ
- vẫn phải kết hợp với số tiền, ngày, loại nghiệp vụ gốc hoặc lãi

### 8.4. HB / Phí / VAT

Đây là nhóm phí ngân hàng và VAT.

Trong source hiện tại, đây là một trong các nhóm gộp đang được hỗ trợ chắc:

- nhiều dòng sao kê
- gộp lại thành một dòng hệ thống

Trong giao diện, nhóm này được lọc qua:

- `Kiểu đối chiếu = Phí/VAT`

### 8.5. Một dòng sao kê có chi + phí (+ thuế)

Đây là trường hợp một dòng sao kê có nhiều cấu phần tiền trong cùng một giao dịch:

- chi chính
- phí
- thuế VAT

Phía hệ thống có thể xử lý các cấu phần đó theo hai cách:

- gộp toàn bộ thành một dòng
- hoặc tách thành 2 đến 3 dòng riêng

Nguyên tắc đúng là:

- không được chỉ nhìn `tổng cộng`
- phải hiểu đây là một giao dịch có nhiều cấu phần
- rồi dò xem phía hệ thống đang hạch toán theo kiểu:
  - một dòng tổng
  - hay nhiều dòng cấu phần

Trong giao diện, nhóm này được lọc qua:

- `Kiểu đối chiếu = Chi + phí/thuế`

### 8.6. Lương

Nhóm lương thường không chỉ có `1-1`.

Trong dữ liệu mẫu hiện có, lương chủ yếu rơi vào:

- `1-n`
- hoặc `n-1`

Nghĩa là:

- một dòng hệ thống có thể bằng nhiều dòng bank
- hoặc nhiều dòng hệ thống có thể tương ứng với một cụm bank

### 8.7. Thu khách hàng, công nợ, logistics, các khoản lặp số tiền

Đây là nhóm dễ tạo ra `review` hoặc `n-n`.

Nguyên nhân:

- nhiều dòng trùng số tiền
- mô tả không thống nhất
- tên đối tác bị viết khác nhau
- hóa đơn hoặc key nghiệp vụ chưa được trích ra đầy đủ

Đây là nhóm phải xử lý cẩn thận nhất.

### 8.8. Cách nhìn filter trên giao diện

Để tránh có quá nhiều chip ở phần kết quả, giao diện nên tách làm hai lớp:

- lớp trạng thái chính:
  - `Tất cả`
  - `Khớp`
  - `Cần kiểm tra`
  - `Chưa khớp`
- lớp kiểu đối chiếu:
  - khi đang chọn `Khớp`:
    - `Tất cả kiểu`
    - `Khớp lẻ`
    - `Phí/VAT`
    - `Chi + phí/thuế`
  - khi đang chọn `Cần kiểm tra`:
    - `Tất cả kiểu`
    - `Nhóm n-n`
  - khi đang chọn `Tất cả` hoặc `Chưa khớp`:
    - ẩn toàn bộ lớp `Kiểu đối chiếu`

Mỗi chip trong lớp `Kiểu đối chiếu` nên hiển thị kèm số lượng giao dịch theo bộ lọc hiện tại.

Như vậy:

- giao diện gọn hơn
- nhưng vẫn lọc ra được đúng từng loại nghiệp vụ đặc biệt

Ngoài ra, với các giao dịch dạng nhóm:

- không nên chỉ tô màu cả block như trước
- nên hiển thị dạng `collapse/expand`
- cột đầu tiên là cột mở rộng nhóm
- dòng cha hiển thị thông tin tóm tắt nhóm
- khi mở nhóm thì mới tô màu nhẹ các dòng con bên trong

---

## 9. Khi nào một giao dịch được coi là Khớp

Một giao dịch được coi là `Khớp` khi:

- tìm được đúng đối ứng hoặc đúng tổ hợp đối ứng
- cùng chiều
- số tiền đúng
- ngày hợp lý
- có thêm bằng chứng đủ chắc như mã, đối tác, mô tả, key nghiệp vụ

Hiện nên chia `Khớp` thành hai cách hiểu:

- `Khớp lẻ`: `1-1`
- `Khớp theo nhóm`: `1-n` hoặc `n-1` nhưng tổ hợp là duy nhất và đủ chắc

Điều quan trọng là:

- `Khớp` chỉ dành cho các trường hợp tool có thể giải thích rõ vì sao nó khớp

---

## 10. Khi nào một giao dịch chỉ nên là Cần kiểm tra

Một giao dịch nên vào `Cần kiểm tra` khi:

- có ứng viên hợp lý ở phía bên kia
- nhưng chưa đủ chắc để tự kết luận

Ví dụ:

- cùng chiều
- cùng số tiền
- ngày trùng hoặc gần nhau
- mô tả, đối tác, mã giao dịch có liên quan
- nhưng còn hơn một khả năng

Hoặc:

- là `n-n`
- và hai bên có vẻ có thể ghép được
- nhưng chưa có khóa đủ chắc để map từng dòng

Nguyên tắc:

- `Cần kiểm tra` là vùng đệm an toàn giữa `Khớp` và `Chưa khớp`

---

## 11. Khi nào một giao dịch là Chưa khớp

Một giao dịch chỉ nên là `Chưa khớp` nếu sau khi rà kỹ vẫn không có đối ứng hợp lý.

Các trường hợp điển hình:

- không có dòng nào phía bên kia cùng chiều và cùng số tiền
- có cùng số tiền nhưng ngày lệch quá xa, lại không có clue mạnh nào khác
- khác đối tác rõ ràng
- khác nhóm nghiệp vụ rõ ràng
- là `n-n` mơ hồ thật, không có key đủ để phân tách
- là `1-n / n-1` nhưng chưa tìm được tổ hợp duy nhất và đủ an toàn

Nói cách khác:

- `Chưa khớp` không phải là “tool chưa nghĩ ra”
- mà phải là “tool đã dò hợp lý rồi nhưng vẫn chưa có căn cứ”

---

## 12. Quy trình dò nên hiểu theo hai vòng

### 12.1. Vòng 1

Đây là vòng dò chính.

Mục tiêu:

- bắt các ca khớp chắc
- bắt các group hiện đã hỗ trợ chắc
- tách ra các ca có ứng viên rõ để đưa vào `Cần kiểm tra`

Ở vòng này, tool ưu tiên:

- `1-1`
- `FT`
- `TT`
- `LD/ST`
- `Phí/VAT`

### 12.2. Vòng 2

Đây là vòng rà lại trên phần đang `Chưa khớp`.

Mục tiêu:

- giảm các dòng đỏ bị sót
- rà lại các ca tách hoặc gộp
- rà lại các cụm `n-n` có vẻ hợp lý

Vòng 2 có thể:

- nâng `Chưa khớp` thành `Cần kiểm tra`
- hoặc nâng thành `Khớp theo nhóm` nếu tổ hợp duy nhất và đủ chắc

Nhưng vòng 2 **không** được phép:

- ép `n-n` mơ hồ thành `Khớp`

---

## 13. Cách hiểu đúng về `n-n`

`n-n` không phải lúc nào cũng giống nhau.

### 13.1. `n-n` có key riêng từng dòng

Ví dụ:

- cùng số dòng
- cùng số tiền
- có hóa đơn hoặc key riêng từng dòng

Loại này có thể nâng lên `Cần kiểm tra`.

Sau này nếu engine đủ mạnh, có thể tách được chính xác hơn.

### 13.2. `n-n` mơ hồ thật

Ví dụ:

- hai bên đều có nhiều dòng cùng số tiền
- cùng ngày hoặc gần ngày
- nhưng mô tả và key quá yếu

Loại này phải giữ `Chưa khớp`.

Đây là nguyên tắc an toàn cần giữ để tránh ghép sai tiền.

---

## 14. Một số ví dụ thực tế rút ra từ dữ liệu mẫu

### 14.1. Phí/VAT

Nhiều dòng sao kê `HB`, `phí`, `VAT` có thể gộp lại thành một dòng hệ thống.

Đây là nhóm source hiện đang hỗ trợ chắc nhất ở dạng `Khớp theo nhóm`.

### 14.2. Lương

Có trường hợp:

- một dòng hệ thống bằng hai dòng sao kê

Ví dụ kiểu:

- hệ thống ghi một khoản lương tổng
- sao kê có hai dòng tách nhỏ hơn

Nhóm này không nên để đỏ nếu tổ hợp là duy nhất.

### 14.3. Thu khách hàng hoặc công nợ trùng số tiền

Có nhiều trường hợp:

- cùng số tiền
- cùng ngày
- cùng đối tác hoặc gần giống đối tác
- nhưng nhiều dòng lặp

Nhóm này thường là `review`, không nên tự khớp ngay.

---

## 15. Những nguyên tắc an toàn cần giữ

1. Không dùng một công thức chung cho tất cả loại giao dịch.
2. Không vì cùng tiền mà kết luận là khớp.
3. Không vì lệch vài ngày mà kết luận là không khớp.
4. Không auto-match `n-n`.
5. Chỉ đưa vào `Khớp` khi giải thích được rõ vì sao khớp.
6. Khi còn nghi ngờ, ưu tiên `Cần kiểm tra` hơn là ghép bừa.
7. `Chưa khớp` chỉ giữ cho các ca thật sự chưa có đối ứng hợp lý.

---

## 16. Tóm tắt cách hiểu ngắn gọn

- `Khớp`: có đủ căn cứ
- `Cần kiểm tra`: có ứng viên hợp lý nhưng chưa đủ chắc
- `Chưa khớp`: chưa có đối ứng hợp lý hoặc còn quá mơ hồ

Về mô hình:

- `1-1`: dễ khớp nhất
- `1-n` và `n-1`: có thể khớp nếu tổ hợp là duy nhất
- `n-n`: không tự khớp, chỉ review hoặc chưa khớp

Về ngày:

- ngày hệ thống là tín hiệu mềm
- không nên dùng ngày như điều kiện cứng tuyệt đối

Về mục tiêu:

- tool phải giúp người dùng tìm đúng giao dịch cần xử lý
- chứ không phải ghép cho đủ số lượng

---

## 17. Cách hiển thị nhóm `n-n` trong phần Cần kiểm tra

### 17.1. Mục đích

Trong phần `Cần kiểm tra`, có những trường hợp không phải chỉ là một dòng đối một dòng.

Có những cụm mà:

- phía hệ thống có nhiều dòng
- phía sao kê cũng có nhiều dòng
- số dòng hai bên bằng nhau
- dữ liệu khá khớp nhau về số tiền, ngày hoặc các dấu hiệu khác

Nhóm này không nên hiển thị rời từng dòng như các review thông thường. Nếu hiển thị rời, người dùng rất khó nhìn ra đây là một cụm đang đối chiếu với nhau.

Vì vậy, các trường hợp này nên được gom thành **nhóm `n-n` cần kiểm tra**.

### 17.2. Khi nào được coi là một nhóm `n-n`

Một cụm chỉ nên được gom thành nhóm `n-n` khi có đủ các điều kiện nền sau:

- số dòng phía hệ thống bằng số dòng phía sao kê
- số dòng mỗi bên lớn hơn `1`
- cùng chiều giao dịch
- nằm trong cùng khoảng ngày hợp lý
- cùng một cụm đối tác hoặc cùng một nhóm nghiệp vụ
- các dòng trong cụm có quan hệ amount hợp lý với nhau

Ngoài các điều kiện nền đó, nên có thêm ít nhất một trong các dấu hiệu tăng độ tin cậy:

- cùng đối tác hoặc alias đối tác
- cùng hóa đơn, hợp đồng, bill, PO, BL, tờ khai hoặc key nghiệp vụ khác
- diễn giải gần nhau
- cùng một family giao dịch như lương, thu khách hàng, logistics, công nợ

Nguyên tắc:

- chỉ gom nhóm khi nhìn ở mức cụm thì hai bên thật sự có vẻ đang nói về cùng một nghiệp vụ
- nếu vẫn quá yếu hoặc quá mơ hồ thì giữ là `Chưa khớp`, không gán nhóm

### 17.3. Nhóm `n-n` trong Cần kiểm tra không phải là Khớp

Phải tách rất rõ hai khái niệm:

- `Khớp theo nhóm`
- `Nhóm n-n cần kiểm tra`

`Khớp theo nhóm` là trường hợp tool đã đủ tự tin để kết luận.

`Nhóm n-n cần kiểm tra` là trường hợp tool mới chỉ nhận ra đây là một **cụm đối ứng có khả năng liên quan với nhau**, nhưng chưa đủ chắc để tự khớp.

Vì vậy:

- nhóm `n-n` trong `Cần kiểm tra` vẫn là `review`
- không được hiểu nhầm là tool đã match xong

### 17.4. Cách sắp thứ tự trong lưới

Khi người dùng bấm vào filter `Cần kiểm tra`, các nhóm `n-n` nên được hiển thị theo logic:

1. xếp theo **nhóm**
2. trong từng nhóm, xếp theo **ngày**

Nói dễ hiểu:

- các dòng của cùng một nhóm phải đứng liền nhau
- không được xen kẽ với nhóm khác
- bên trong nhóm thì xếp theo ngày giao dịch để dễ đọc

Như vậy người dùng sẽ nhìn ra ngay:

- nhóm nào gồm những dòng nào
- thứ tự các dòng trong nhóm diễn ra ra sao theo thời gian

### 17.5. Khi click vào một dòng trong nhóm `n-n`

Nếu một dòng thuộc nhóm `n-n`, khi click vào không nên mở kiểu:

- một dòng hệ thống đối một dòng sao kê
- hoặc một dòng đối một nhóm nhỏ như `1-n`

Thay vào đó, phải mở **màn hình chi tiết của cả nhóm `n-n`**.

Màn hình đó nên hiển thị:

- toàn bộ các dòng hệ thống trong nhóm
- toàn bộ các dòng sao kê trong nhóm
- tổng số dòng mỗi bên
- tổng tiền mỗi bên
- khoảng ngày của nhóm
- các dấu hiệu chính khiến tool gom nhóm này

Mục tiêu là để người dùng kiểm tra cả cụm, không phải nhìn từng dòng đơn lẻ.

### 17.6. Nếu có nhiều nhóm thì phân biệt bằng cách nào

Nếu chỉ xếp theo ngày thì chưa đủ. Khi có nhiều nhóm `n-n`, người dùng vẫn cần nhìn ra nhóm nào thuộc nhóm nào.

Cách tốt nhất là dùng đồng thời nhiều dấu hiệu nhận diện:

- mã nhóm
- màu nhẹ riêng cho từng nhóm
- marker hoặc badge nhóm

Ví dụ:

- `R-001`
- `R-002`
- `R-003`

Mỗi nhóm nên có:

- một `mã nhóm` riêng
- một tông màu nền rất nhẹ
- một marker hoặc badge nhỏ để nhìn lướt cũng nhận ra

Không nên chỉ dùng màu, vì nhiều nhóm thì màu một mình sẽ không đủ chắc để phân biệt.

### 17.7. Thông tin nên có trên mỗi nhóm

Mỗi nhóm `n-n` nên có các thông tin nhận diện cơ bản:

- mã nhóm
- số dòng hệ thống
- số dòng sao kê
- tổng tiền hệ thống
- tổng tiền sao kê
- khoảng ngày của nhóm
- đối tác hoặc key chính nếu có

Ví dụ cách hiểu:

- `Nhóm R-001`
- `3 dòng hệ thống / 3 dòng sao kê`
- `Ngày 10/03 đến 12/03`
- `Đối tác: Tản Viên`

Nhìn như vậy người dùng sẽ kiểm tra nhanh hơn rất nhiều so với việc xem từng dòng rời.

### 17.8. Nguyên tắc an toàn cho nhóm `n-n`

Nhóm `n-n` chỉ có mục đích:

- gom đúng các dòng liên quan với nhau
- giúp người dùng rà soát dễ hơn

Nhóm `n-n` không có mục đích:

- tự kết luận là khớp
- ép map từng dòng ngay trong giao diện

Nguyên tắc cuối cùng cần giữ:

- `n-n` có thể được gom nhóm để review
- nhưng **không được tự động chuyển thành Khớp**

### 17.9. Tóm tắt ngắn cho phần này

Trong `Cần kiểm tra`, các cụm `n-n` có đủ căn cứ nên được:

- gom thành một nhóm review
- xếp liền nhau theo nhóm
- sắp theo ngày trong nhóm
- click một dòng thì mở chi tiết của cả nhóm
- phân biệt nhóm bằng `mã nhóm + màu nhẹ + marker`

Đây là cách hiển thị đúng nghiệp vụ và dễ dùng hơn nhiều so với hiển thị từng dòng rời.
