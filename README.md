# Tool doi soat sao ke

Tool desktop Python de doi chieu file giao dich he thong voi file sao ke ngan hang.

## Tinh nang chinh

- Mot man hinh duy nhat, phan ket qua chi mo sau khi chon du 2 file va bam `Do sao ke`
- Hai grid song song `He thong` va `Sao ke`
- Sort theo cot, tim kiem theo cot hoac tren toan bo cot
- Bo loc nhanh: `Tat ca`, `Chi hien khop`, `Chi hien khong khop`, `Chi hien thu`, `Chi hien chi`, `Chi hien thue`
- Co loading overlay trong luc doi soat
- Luu lich su doi soat vao SQLite tai `data/history.sqlite`
- Nut `Mo` o cot dau de nhay/popup sang giao dich doi ung
- Xuat cac dong he thong khong khop ra file Excel moi theo format cot cua file he thong
- Ho tro 3 ngon ngu: Viet Nam mac dinh, English, 中文简体

## Cai dat

```powershell
& 'C:\Program Files\PyManager\python.exe' -m pip install -r requirements.txt
```

## Chay tool

```powershell
& 'C:\Program Files\PyManager\python.exe' main.py
```

## Build exe

```powershell
.\build_exe.bat
```

Sau khi build xong, file exe se nam trong thu muc `dist\ToolDoiSoatSaoKe`.

## Cach doi soat hien tai

- Lay sao ke lam chuan
- Chuan hoa so tien theo VND
- Mapping theo file thuc te:
  - `File he thong -> 金额借方` doi ung `Sao ke -> Có/Credit`
  - `File he thong -> 金额贷方` doi ung `Sao ke -> Nợ/Debit + Fee/Interest + VAT`
- Uu tien khop theo:
  - So tien va huong thu/chi
  - Ma tham chieu xuat hien trong du lieu nhu `FT`, `SK`, `ST`, `LD`, `HB`
  - Do lech ngay giao dich
  - Do giong nhau cua mo ta
- Mau xanh: khop chac
- Mau vang: da co doi ung nhung nen kiem tra lai
- Mau do: chua tim thay doi ung tin cay
