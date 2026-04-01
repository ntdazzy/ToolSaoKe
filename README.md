# Tool Äá»‘i SoÃ¡t Sao KÃª NgÃ¢n HÃ ng

## 1. Tá»•ng quan

ÄÃ¢y lÃ  á»©ng dá»¥ng desktop viáº¿t báº±ng Python Ä‘á»ƒ Ä‘á»‘i soÃ¡t giá»¯a:

- file giao dá»‹ch tá»« há»‡ thá»‘ng ná»™i bá»™
- file sao kÃª ngÃ¢n hÃ ng Techcombank

Má»¥c tiÃªu cá»§a tool:

- xÃ¡c Ä‘á»‹nh cÃ¡c giao dá»‹ch Ä‘Ã£ khá»›p cháº¯c
- tÃ¡ch cÃ¡c giao dá»‹ch cáº§n kiá»ƒm tra thá»§ cÃ´ng
- chá»‰ ra cÃ¡c giao dá»‹ch cÃ³ trong sao kÃª nhÆ°ng chÆ°a tháº¥y trong há»‡ thá»‘ng
- chá»‰ ra cÃ¡c giao dá»‹ch cÃ³ trong há»‡ thá»‘ng nhÆ°ng chÆ°a tháº¥y trong sao kÃª
- há»— trá»£ xuáº¥t Excel Ä‘á»ƒ káº¿ toÃ¡n hoáº·c kiá»ƒm soÃ¡t tiáº¿p tá»¥c xá»­ lÃ½

Tool hiá»‡n cháº¡y trÃªn Windows, dÃ¹ng PySide6 cho giao diá»‡n vÃ  cÃ³ thá»ƒ build thÃ nh file `.exe`.

README nÃ y lÃ  tÃ i liá»‡u ká»¹ thuáº­t vÃ  nghiá»‡p vá»¥ cá»§a source hiá»‡n táº¡i, dÃ¹ng cho 4 má»¥c Ä‘Ã­ch:

1. mÃ´ táº£ Ä‘áº§y Ä‘á»§ kiáº¿n trÃºc source Ä‘ang cháº¡y
2. mÃ´ táº£ tÃ­nh nÄƒng hiá»‡n cÃ³ cá»§a á»©ng dá»¥ng
3. mÃ´ táº£ logic Ä‘á»‘i soÃ¡t hiá»‡n táº¡i trong code
4. chá»‘t cÃ¡c rule nghiá»‡p vá»¥ Ä‘Ã£ xÃ¡c nháº­n trÃªn dá»¯ liá»‡u máº«u Ä‘á»ƒ lÃ m ná»n cho cÃ¡c bÆ°á»›c nÃ¢ng cáº¥p tiáº¿p theo

---

## 2. CÃ´ng nghá»‡ sá»­ dá»¥ng

- Python
- PySide6
- `openpyxl`
- `xlrd`
- SQLite
- PyInstaller

---

## 3. Cáº¥u trÃºc source hiá»‡n táº¡i

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

### 3.1. Vai trÃ² cá»§a tá»«ng nhÃ³m file

#### `app/models.py`

Khai bÃ¡o dataclass cho:

- `BankMetadata`
- `SystemTransaction`
- `BankTransaction`
- `ReconciliationSummary`
- `ReconciliationResult`

Äiá»ƒm quan trá»ng:

- má»—i dÃ²ng giao dá»‹ch Ä‘á»u cÃ³:
  - `status`: `matched`, `review`, `unmatched`
  - `match_type`: `exact`, `group`, `none`
  - `group_id`
  - `group_order`
  - `confidence`
  - `match_reason`
- cÃ¡c dÃ²ng `review` cÃ³ thá»ƒ lÆ°u danh sÃ¡ch á»©ng viÃªn Ä‘á»‘i á»©ng:
  - phÃ­a há»‡ thá»‘ng: `review_bank_ids`, `review_bank_rows`
  - phÃ­a sao kÃª: `review_system_ids`, `review_system_rows`

#### `app/services/excel_loader.py`

Chá»‹u trÃ¡ch nhiá»‡m:

- nháº­n diá»‡n file Ä‘áº§u vÃ o lÃ  file há»‡ thá»‘ng hay file sao kÃª
- Ä‘á»c workbook Excel
- chuáº©n hÃ³a dá»¯ liá»‡u thÃ nh `SystemTransaction` vÃ  `BankTransaction`
- trÃ­ch metadata cá»§a sao kÃª

CÃ¡c Ä‘iá»ƒm Ä‘Ã¡ng chÃº Ã½:

- `detect_excel_file_kind(path)` dÃ¹ng Ä‘á»ƒ cháº·n sai loáº¡i file ngay tá»« Ä‘áº§u
- loader Ä‘Ã£ Ä‘Æ°á»£c test láº¡i trÃªn cÃ¡c bá»™ máº«u trong thÆ° má»¥c `file/`
- phÃ­a bank cÃ³ cÃ¡c cá»™t `debit`, `credit`, `fee`, `vat`, `amount`, `direction`

#### `app/services/utils.py`

Chá»©a cÃ¡c hÃ m tiá»‡n Ã­ch:

- chuáº©n hÃ³a text
- parse ngÃ y / datetime
- trÃ­ch token tham chiáº¿u
- trÃ­ch prefix tham chiáº¿u

Hiá»‡n source Ä‘ang há»— trá»£ tá»‘t cÃ¡c prefix/token chÃ­nh:

- `FT`
- `TT`
- `LD`
- `HB`
- `ST`
- `SK`

#### `app/services/reconciliation.py`

ÄÃ¢y lÃ  engine Ä‘á»‘i soÃ¡t chÃ­nh.

Vai trÃ²:

- táº¡o candidate giá»¯a 2 phÃ­a
- cháº¡y cÃ¡c vÃ²ng match theo má»©c Ä‘á»™ cháº¯c cháº¯n
- gáº¯n `matched`, `review`, `unmatched`
- táº¡o summary cuá»‘i cÃ¹ng

#### `app/services/exporter.py`

Xuáº¥t káº¿t quáº£ Ä‘á»‘i soÃ¡t ra Excel.

#### `app/services/history_store.py`

LÆ°u lá»‹ch sá»­ Ä‘á»‘i soÃ¡t báº±ng SQLite.

#### `app/ui/`

Sau refactor, giao diá»‡n Ä‘Ã£ Ä‘Æ°á»£c tÃ¡ch thÃ nh nhiá»u file nhá» hÆ¡n:

- `main_window.py`
  - chá»‰ cÃ²n vai trÃ² Ä‘iá»u phá»‘i chÃ­nh
- `main_window_scan_mixin.py`
  - chá»n file, scan, bind káº¿t quáº£, chuyá»ƒn page
- `main_window_filter_mixin.py`
  - filter, search, update summary, row count
- `main_window_actions_mixin.py`
  - lá»‹ch sá»­, popup chi tiáº¿t, export
- `pages.py`
  - `StartupPage`, `ResultsPage`
- `chips.py`
  - `ChipButton`, `ChipPalette`
- `panels.py`
  - cÃ¡c panel dÃ¹ng chung
- `dialogs.py`
  - `PairDialog`, `HistoryDialog`
- `styles.py`
  - stylesheet dÃ¹ng chung
- `config.py`
  - config UI, header, width cá»™t, nhÃ£n phá»¥
- `metadata.py`
  - layout metadata sao kÃª
- `widgets.py`
  - widget tÃ¹y biáº¿n vÃ  loading overlay
- `workers.py`
  - `ScanWorker`

#### `tests/`

- `test_reconciliation_logic.py`
  - test cÃ¡c rule Ä‘á»‘i soÃ¡t
- `test_main_window_scan_flow.py`
  - test regression cho luá»“ng scan vÃ  chuyá»ƒn page
- `test_excel_file_kind.py`
  - test detector file tháº­t trong cÃ¡c bá»™ máº«u

---

## 4. TÃ­nh nÄƒng hiá»‡n cÃ³ cá»§a á»©ng dá»¥ng

### 4.1. Chá»n file vÃ  dÃ²

á»¨ng dá»¥ng cho phÃ©p:

- chá»n file há»‡ thá»‘ng
- chá»n file sao kÃª
- chá»n ngÃ´n ngá»¯
- báº¥m `DÃ² sao kÃª`

Luá»“ng UI hiá»‡n táº¡i dÃ¹ng 2 mÃ n hÃ¬nh riÃªng:

- `StartupPage`
- `ResultsPage`

Khi báº¥m dÃ²:

- app chuyá»ƒn sang mÃ n hÃ¬nh káº¿t quáº£
- hiá»‡n loading overlay
- táº¡o `ScanWorker` Ä‘á»ƒ Ä‘á»c file vÃ  cháº¡y reconciliation
- toÃ n bá»™ cáº­p nháº­t UI Ä‘Æ°á»£c Ä‘Æ°a vá» GUI thread báº±ng `Qt.QueuedConnection`

### 4.2. MÃ n hÃ¬nh káº¿t quáº£

MÃ n hÃ¬nh sau khi dÃ² gá»“m:

- cá»¥m chá»n file á»Ÿ gÃ³c trÃ¡i
- cá»¥m metadata sao kÃª bÃªn pháº£i
- khu vá»±c `Káº¿t quáº£ dÃ²`
- 2 lÆ°á»›i `Sao kÃª` vÃ  `Há»‡ thá»‘ng`
- cÃ¡c filter, chip tráº¡ng thÃ¡i, action bar, popup chi tiáº¿t

### 4.3. Metadata sao kÃª

Hiá»ƒn thá»‹:

- tÃªn ngÃ¢n hÃ ng
- sá»‘ tÃ i khoáº£n
- tÃªn tÃ i khoáº£n
- loáº¡i tÃ i khoáº£n
- loáº¡i tiá»n
- mÃ£ sá»‘ thuáº¿
- ká»³ sao kÃª
- sá»‘ dÆ° Ä‘áº§u ká»³ / cuá»‘i ká»³ / hiá»‡n táº¡i
- tá»•ng ghi ná»£ / ghi cÃ³
- tá»•ng phÃ­ / VAT
- tá»•ng sá»‘ lá»‡nh ghi ná»£ / ghi cÃ³

### 4.4. Bá»™ lá»c

á»¨ng dá»¥ng hiá»‡n cÃ³:

- filter tráº¡ng thÃ¡i báº±ng chip:
  - `Táº¥t cáº£`
  - `GD Khá»›p`
  - `PhÃ­/VAT Ä‘Ã£ khá»›p`
  - `Cáº§n kiá»ƒm tra`
  - `ChÆ°a khá»›p`
- filter loáº¡i giao dá»‹ch:
  - `Táº¥t cáº£ giao dá»‹ch`
  - `Chá»‰ hiá»‡n thu`
  - `Chá»‰ hiá»‡n chi`
  - `Chá»‰ hiá»‡n thuáº¿`
- filter theo `MÃ£ TCB`
- filter theo ngÃ y
- filter tÃ¬m kiáº¿m text

LÆ°u Ã½ quan trá»ng:

- `PhÃ­/VAT Ä‘Ã£ khá»›p` hiá»‡n má»›i lÃ  `group match` duy nháº¥t Ä‘Ã£ Ä‘Æ°á»£c code cháº¯c
- tÃªn nÃ y khÃ´ng cÃ³ nghÄ©a lÃ  source Ä‘Ã£ há»— trá»£ Ä‘áº§y Ä‘á»§ má»i loáº¡i `group match`

### 4.5. Popup chi tiáº¿t

Khi click má»™t dÃ²ng:

- náº¿u lÃ  `matched exact`, popup hiá»ƒn thá»‹ cáº·p Ä‘á»‘i á»©ng 1-1
- náº¿u lÃ  `matched group`, popup hiá»ƒn thá»‹ nhÃ³m Ä‘á»‘i á»©ng
- náº¿u lÃ  `review`, popup hiá»ƒn thá»‹ danh sÃ¡ch á»©ng viÃªn Ä‘á»‘i á»©ng Ä‘Ã£ lÆ°u trong row metadata

### 4.6. Lá»‹ch sá»­ vÃ  xuáº¥t Excel

á»¨ng dá»¥ng há»— trá»£:

- lÆ°u lá»‹ch sá»­ dÃ²
- xem láº¡i lá»‹ch sá»­
- xuáº¥t Excel
- tÃ¹y chá»n `KÃ¨m sheet sao kÃª`

### 4.7. Build file `.exe`

Repo cÃ³ sáºµn `build_exe.bat`.

Script build hiá»‡n táº¡i:

- tá»± dÃ² Python tháº­t:
  - Æ°u tiÃªn `py -3.13`
  - rá»“i `py -3`
  - rá»“i fallback `where python`
- trÃ¡nh dÃ¹ng nháº§m `WindowsApps\python.exe`
- cÃ i `requirements.txt`
- táº¡o icon tá»« `logo.png`
- build báº±ng PyInstaller

---

## 5. Luá»“ng xá»­ lÃ½ hiá»‡n táº¡i

### 5.1. Luá»“ng scan

1. chá»n file há»‡ thá»‘ng
2. chá»n file sao kÃª
3. báº¥m `DÃ² sao kÃª`
4. app chuyá»ƒn sang `ResultsPage`
5. hiá»‡n scan overlay
6. `ScanWorker` cháº¡y trong thread riÃªng
7. worker Ä‘á»c file, load data, cháº¡y reconciliation
8. káº¿t quáº£ Ä‘Æ°á»£c Ä‘áº©y vá» GUI thread
9. bind vÃ o 2 báº£ng, metadata, summary, filter
10. áº©n loading

### 5.2. Luá»“ng threading

ÄÃ¢y lÃ  Ä‘iá»ƒm Ä‘Ã£ Ä‘Æ°á»£c sá»­a regression.

NguyÃªn táº¯c hiá»‡n táº¡i:

- worker chá»‰ Ä‘á»c file vÃ  táº¡o data thuáº§n
- worker khÃ´ng táº¡o hay cháº¡m vÃ o `QWidget`, `QHeaderView`, `QAbstractItemModel`
- toÃ n bá»™ bind model/view chá»‰ cháº¡y á»Ÿ main thread
- cÃ¡c signal `finished`, `failed`, `thread.finished` dÃ¹ng `Qt.QueuedConnection`

Má»¥c tiÃªu:

- trÃ¡nh lá»—i kiá»ƒu:
  - `QObject: Cannot create children for a parent that is in a different thread`
  - `QBasicTimer::start: Timers cannot be started from another thread`

### 5.3. Luá»“ng filter

Sau khi Ä‘Ã£ cÃ³ `current_result`:

- filter chip, ngÃ y, mÃ£ TCB, tÃ¬m kiáº¿m sáº½ cháº¡y trÃªn dá»¯ liá»‡u Ä‘Ã£ bind
- filter loading lÃ  overlay riÃªng
- filter loading khÃ´ng Ä‘Æ°á»£c chen vÃ o khi scan overlay Ä‘ang cháº¡y

---

## 6. Logic Ä‘á»c vÃ  chuáº©n hÃ³a dá»¯ liá»‡u

### 6.1. File há»‡ thá»‘ng

Loader chuáº©n hÃ³a ra:

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

### 6.2. File sao kÃª

Loader chuáº©n hÃ³a ra:

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

### 6.3. Nháº­n diá»‡n loáº¡i file

`detect_excel_file_kind(path)` hiá»‡n Ä‘Æ°á»£c dÃ¹ng Ä‘á»ƒ:

- phÃ¢n biá»‡t file há»‡ thá»‘ng vÃ  file sao kÃª
- cháº·n file sai loáº¡i trÆ°á»›c khi vÃ o luá»“ng scan chÃ­nh

Pháº§n nÃ y Ä‘Ã£ cÃ³ test vá»›i dá»¯ liá»‡u tháº­t:

- `202512`
- `202601`
- `202602`
- `202603`
- `202603.1`

---

## 7. Logic Ä‘á»‘i soÃ¡t hiá»‡n táº¡i trong source

Pháº§n nÃ y mÃ´ táº£ Ä‘Ãºng engine hiá»‡n Ä‘ang cháº¡y trong `app/services/reconciliation.py`.

### 7.1. Dá»¯ liá»‡u Ä‘áº§u vÃ o mÃ  engine sá»­ dá»¥ng

Má»—i giao dá»‹ch sau khi load Ä‘á»u Ä‘Æ°á»£c chuáº©n hÃ³a thÃ nh má»™t row cÃ³ cÃ¡c nhÃ³m dá»¯ liá»‡u sau:

#### a. ThÃ´ng tin lÃµi

- ngÃ y
- chiá»u giao dá»‹ch
- sá»‘ tiá»n
- diá»…n giáº£i chuáº©n hÃ³a
- token text

#### b. ThÃ´ng tin tham chiáº¿u

- `reference_number` phÃ­a bank
- token tham chiáº¿u trÃ­ch tá»« mÃ´ táº£
- prefix tham chiáº¿u

VÃ­ dá»¥ prefix Ä‘ang Ä‘Æ°á»£c source nháº­n diá»‡n tá»‘t:

- `FT`
- `TT`
- `LD`
- `ST`
- `HB`
- `SK`

#### c. ThÃ´ng tin tráº¡ng thÃ¡i Ä‘á»‘i soÃ¡t

- `status`
- `match_type`
- `group_id`
- `group_order`
- `confidence`
- `match_reason`
- id Ä‘á»‘i á»©ng hoáº·c danh sÃ¡ch á»©ng viÃªn review

### 7.2. CÃ¡c vÃ²ng match hiá»‡n cÃ³ trong code

Engine hiá»‡n cháº¡y theo thá»© tá»± tá»« cháº¯c Ä‘áº¿n kÃ©m cháº¯c hÆ¡n.

#### a. `reference`

Æ¯u tiÃªn cÃ¡c trÆ°á»ng há»£p cÃ³ khÃ³a tham chiáº¿u máº¡nh.

#### b. `voucher_unique`

DÃ² cÃ¡c trÆ°á»ng há»£p phÃ­a há»‡ thá»‘ng cÃ³ tÃ­n hiá»‡u Ä‘á»§ riÃªng Ä‘á»ƒ ghÃ©p 1-1.

#### c. `derived_unique`

DÃ² báº±ng khÃ³a suy diá»…n tá»« mÃ´ táº£ hoáº·c token.

#### d. `tax aggregate`

Rule group riÃªng cho `PhÃ­/VAT`.

ÄÃ¢y lÃ  rule group Ä‘ang cháº¯c nháº¥t trong source hiá»‡n táº¡i.

#### e. `review candidate`

CÃ¡c dÃ²ng chÆ°a match nhÆ°ng cÃ²n á»©ng viÃªn há»£p lÃ½ sáº½ Ä‘Æ°á»£c nÃ¢ng lÃªn `review`.

### 7.3. Rule `matched exact` hiá»‡n táº¡i

Má»™t dÃ²ng Ä‘Æ°á»£c gáº¯n `matched + exact` khi:

- cÃ³ cáº·p Ä‘á»‘i á»©ng 1-1
- cÃ¹ng chiá»u
- cÃ¹ng sá»‘ tiá»n
- qua Ä‘Æ°á»£c má»™t trong cÃ¡c vÃ²ng exact á»Ÿ trÃªn

Khi Ä‘Ã³:

- `status = matched`
- `match_type = exact`
- gáº¯n cáº·p `matched_system_id / matched_bank_id`

### 7.4. Rule `matched group` hiá»‡n táº¡i

Hiá»‡n táº¡i source má»›i cÃ³ group match cháº¯c cho:

- `PhÃ­/VAT`
- nhÃ³m Homebanking / phÃ­ kÃ¨m VAT

MÃ´ hÃ¬nh hiá»‡n cÃ³ lÃ :

- nhiá»u dÃ²ng bank
- gá»™p vá» 1 dÃ²ng há»‡ thá»‘ng

Tá»©c lÃ  báº£n cháº¥t hiá»‡n táº¡i lÃ  `1-n`, chÆ°a pháº£i engine group tá»•ng quÃ¡t.

Khi match group:

- `status = matched`
- `match_type = group`
- `group_id` Ä‘Æ°á»£c gáº¯n cho cáº£ hai phÃ­a

### 7.5. Rule `review` hiá»‡n táº¡i trong code

CÃ¡c dÃ²ng chÆ°a match Ä‘Æ°á»£c nÃ¢ng sang `review` náº¿u váº«n cÃ²n á»©ng viÃªn há»£p lÃ½.

Äiá»u kiá»‡n review hiá»‡n táº¡i trong code xoay quanh:

- cÃ¹ng chiá»u
- cÃ¹ng sá»‘ tiá»n
- cÃ³ Ã­t nháº¥t má»™t clue máº¡nh hÆ¡n má»©c ngáº«u nhiÃªn

Clue Ä‘ang Ä‘Æ°á»£c dÃ¹ng:

- cÃ³ reference token
- hoáº·c cÃ¹ng ngÃ y
- hoáº·c lá»‡ch ráº¥t Ã­t ngÃ y vÃ  text Ä‘á»§ gáº§n
- hoáº·c lÃ  cáº·p gáº§n nháº¥t láº«n nhau trong táº­p á»©ng viÃªn

Khi gáº¯n `review`:

- row khÃ´ng Ä‘Æ°á»£c coi lÃ  matched
- popup detail cÃ³ thá»ƒ hiá»ƒn thá»‹ danh sÃ¡ch á»©ng viÃªn Ä‘á»‘i á»©ng

### 7.6. Rule `unmatched` hiá»‡n táº¡i trong code

Má»™t dÃ²ng cÃ²n lÃ  `unmatched` khi:

- khÃ´ng qua Ä‘Æ°á»£c exact match
- khÃ´ng rÆ¡i vÃ o tax aggregate group
- khÃ´ng Ä‘á»§ Ä‘iá»u kiá»‡n Ä‘á»ƒ nÃ¢ng sang `review`

VÃ¬ váº­y hiá»‡n táº¡i `unmatched` váº«n Ä‘ang chá»©a 2 loáº¡i:

1. tháº­t sá»± khÃ´ng cÃ³ Ä‘á»‘i á»©ng há»£p lÃ½
2. cÃ³ kháº£ nÄƒng lÃ  ca `1-n / n-1 / n-n` nhÆ°ng engine chÆ°a giáº£i Ä‘Æ°á»£c

ÄÃ¢y lÃ  lÃ½ do vÃ¬ sao `unmatched` hiá»‡n táº¡i chÆ°a hoÃ n toÃ n Ä‘á»“ng nghÄ©a vá»›i â€œkhÃ´ng cÃ³ giao dá»‹ch Ä‘á»‘i á»©ngâ€.

---

## 8. Káº¿t quáº£ baseline trÃªn dá»¯ liá»‡u máº«u

Baseline nÃ y dÃ¹ng Ä‘á»ƒ hiá»ƒu source Ä‘ang cho ra gÃ¬ trÆ°á»›c khi sá»­a tiáº¿p nghiá»‡p vá»¥.

### 8.1. Tá»•ng quan theo bá»™ dá»¯ liá»‡u

| Bá»™ dá»¯ liá»‡u | System matched | System review | System unmatched | Bank matched | Bank review | Bank unmatched |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `202512` | 735 | 44 | 16 | 742 | 43 | 12 |
| `202601` | 502 | 48 | 10 | 509 | 48 | 8 |
| `202602` | 333 | 54 | 7 | 340 | 53 | 7 |
| `202603` | 387 | 19 | 4 | 394 | 19 | 14 |

### 8.2. PhÃ¢n loáº¡i nhanh cÃ¡c dÃ²ng `unmatched`

Khi rÃ  láº¡i cÃ¡c dÃ²ng Ä‘á» theo amount vÃ  ngÃ y, cÃ³ thá»ƒ chia thÃ nh cÃ¡c nhÃ³m:

#### a. KhÃ´ng cÃ³ Ä‘á»‘i á»©ng cÃ¹ng amount

ÄÃ¢y lÃ  nhÃ³m Ä‘á» tháº­t.

#### b. CÃ³ cÃ¹ng amount nhÆ°ng ngÃ y lá»‡ch xa

NhÃ³m nÃ y chÆ°a nÃªn match ngay.

#### c. CÃ³ dáº¥u hiá»‡u lÃ  `1-n / n-1`

NhÃ³m nÃ y hiá»‡n Ä‘ang Ä‘á» vÃ¬ engine chÆ°a cÃ³ group tá»•ng quÃ¡t.

#### d. CÃ³ dáº¥u hiá»‡u lÃ  `n-n`

NhÃ³m nÃ y cáº§n tÃ¡ch tiáº¿p thÃ nh:

- `n-n` cÃ³ key riÃªng tá»«ng dÃ²ng
- `n-n` mÆ¡ há»“ tháº­t

### 8.3. CÃ¡c ca `1-n / n-1` tháº­t Ä‘Ã£ xÃ¡c nháº­n tá»« dá»¯ liá»‡u máº«u

ÄÃ£ xÃ¡c nháº­n Ä‘Æ°á»£c nhiá»u ca tháº­t trong 4 bá»™ dá»¯ liá»‡u:

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

VÃ­ dá»¥ cá»¥ thá»ƒ trong `202603`:

- system row `79 = bank 350 + 368`
- system row `80 = bank 349 + 369`
- system row `336 = bank 103 + 104`

Káº¿t luáº­n:

- dá»¯ liá»‡u tháº­t cÃ³ `1-n`
- dá»¯ liá»‡u tháº­t cÃ³ `n-1`
- source hiá»‡n chÆ°a cÃ³ engine group tá»•ng quÃ¡t ngoÃ i `PhÃ­/VAT`

### 8.4. CÃ¡c cá»¥m `n-n` tháº­t trong dá»¯ liá»‡u máº«u

VÃ­ dá»¥ ná»•i báº­t trong `202603`:

- amount `70,000,000`
  - system `2`
  - bank `2`
  - nhÃ³m `MOC HOANG GIA`
- amount `100,000,000`
  - system `3`
  - bank `3`
  - láº«n `WUYI`, `LINH AN`, `PHÃš HOA`, `HOANG QUAN`
- amount `450,000,000`
  - system `4`
  - bank `4`
  - nhÃ³m `Táº¢N VIÃŠN`
- amount `490,000,000`
  - system `2`
  - bank `2`
  - mÃ´ táº£ bank ráº¥t yáº¿u
- amount `500,000,000`
  - system `2`
  - bank `2`
- amount `1,000,000,000`
  - system `3`
  - bank `3`

CÃ¡c nhÃ³m nÃ y khÃ´ng nÃªn auto-match trong tráº¡ng thÃ¡i source hiá»‡n táº¡i.

---

## 9. Rule nghiá»‡p vá»¥ Ä‘Ã£ chá»‘t

Pháº§n nÃ y lÃ  spec nghiá»‡p vá»¥ Ä‘Ã£ chá»‘t Ä‘á»ƒ tiáº¿p tá»¥c nÃ¢ng cáº¥p engine.

### 9.1. NguyÃªn táº¯c ná»n

#### a. Sao kÃª lÃ  nguá»“n chuáº©n chÃ­nh

Tool Ä‘á»‘i soÃ¡t theo hai chiá»u, nhÆ°ng phÃ­a sao kÃª váº«n lÃ  nguá»“n tham chiáº¿u chÃ­nh khi Ä‘Ã¡nh giÃ¡ cÃ³ dÃ²ng phÃ¡t sinh tháº­t á»Ÿ ngÃ¢n hÃ ng.

#### b. KhÃ´ng Ã©p khá»›p cho Ä‘á»§

Æ¯u tiÃªn an toÃ n:

- thiáº¿u báº±ng chá»©ng thÃ¬ Ä‘á»ƒ `review`
- mÆ¡ há»“ tháº­t thÃ¬ Ä‘á»ƒ `unmatched`

#### c. `NgÃ y há»‡ thá»‘ng` lÃ  tÃ­n hiá»‡u má»m

Do há»‡ thá»‘ng lÃ  nháº­p tay nÃªn cÃ³ thá»ƒ phÃ¡t sinh tÃ¬nh huá»‘ng:

- sao kÃª cÃ³ giao dá»‹ch hÃ´m nay
- vÃ i ngÃ y sau ngÆ°á»i dÃ¹ng má»›i nháº­p há»‡ thá»‘ng

VÃ¬ váº­y ngÃ y khÃ´ng Ä‘Æ°á»£c coi lÃ  Ä‘iá»u kiá»‡n cá»©ng.

#### d. `n-n` khÃ´ng auto-match

ÄÃ¢y lÃ  nguyÃªn táº¯c an toÃ n Ä‘Ã£ chá»‘t.

### 9.2. Má»©c Ä‘á»™ tin cáº­y cá»§a ngÃ y giao dá»‹ch

NÃªn hiá»ƒu nhÆ° sau:

- cÃ¹ng ngÃ y: ráº¥t máº¡nh
- lá»‡ch `1-3` ngÃ y: váº«n há»£p lÃ½
- lá»‡ch `4-7` ngÃ y: chá»‰ há»£p lÃ½ náº¿u cÃ³ thÃªm clue máº¡nh
- lá»‡ch `> 7` ngÃ y: thÆ°á»ng khÃ´ng Ä‘á»§, trá»« khi cÃ³ key cá»©ng

Key máº¡nh bao gá»“m:

- `FT`
- `ST`
- `LD`
- invoice
- bill
- contract
- key nghiá»‡p vá»¥ rÃµ trong mÃ´ táº£

### 9.3. CÃ¡c loáº¡i tÃ­n hiá»‡u dÃ¹ng Ä‘á»ƒ dÃ²

#### a. TÃ­n hiá»‡u cá»©ng

- cÃ¹ng chiá»u
- cÃ¹ng sá»‘ tiá»n
- tham chiáº¿u máº¡nh
- key nghiá»‡p vá»¥ Ä‘áº·c thÃ¹

#### b. TÃ­n hiá»‡u máº¡nh

- ngÃ y trÃ¹ng
- Ä‘á»‘i tÃ¡c trÃ¹ng hoáº·c alias há»£p lá»‡
- mÃ´ táº£ ráº¥t gáº§n
- invoice / BL / PO / contract trÃ¹ng

#### c. TÃ­n hiá»‡u má»m

- ngÃ y gáº§n
- mÃ´ táº£ gáº§n
- cÃ¹ng nhÃ³m nghiá»‡p vá»¥

### 9.4. PhÃ¢n loáº¡i giao dá»‹ch theo nghiá»‡p vá»¥

ÄÃ¢y lÃ  cÃ¡ch nÃªn hiá»ƒu dá»¯ liá»‡u hiá»‡n táº¡i.

#### a. `FT`

ThÆ°á»ng lÃ  chuyá»ƒn khoáº£n trá»±c tiáº¿p.

NhÃ³m nÃ y nÃªn Æ°u tiÃªn exact match khi:

- cÃ¹ng chiá»u
- cÃ¹ng amount
- cÃ¹ng reference hoáº·c mÃ´ táº£ Ä‘á»§ máº¡nh

#### b. `TT`

ThÆ°á»ng lÃ  ná»™p/rÃºt tiá»n hoáº·c giao dá»‹ch cÃ³ mÃ´ táº£ ngáº¯n.

NhÃ³m nÃ y khÃ´ng nÃªn chá»‰ dá»±a vÃ o amount, vÃ¬ mÃ´ táº£ cÃ³ thá»ƒ yáº¿u.

#### c. `LD / ST`

NhÃ³m vay vÃ  kháº¿ Æ°á»›c.

ÄÃ¢y lÃ  nhÃ³m cÃ³ key nghiá»‡p vá»¥ tá»‘t, nÃªn Æ°u tiÃªn match báº±ng:

- `ST`
- `LD`
- amount
- ngÃ y

#### d. `HB / PhÃ­ / VAT`

ÄÃ¢y lÃ  group hiá»‡n source Ä‘ang há»— trá»£ cháº¯c.

#### e. LÃ£i ngÃ¢n hÃ ng cuá»‘i thÃ¡ng

ÄÃ¢y lÃ  nhÃ³m exact tá»‘t náº¿u nháº­n diá»‡n Ä‘Ãºng reference / mÃ´ táº£.

#### f. LÆ°Æ¡ng

Theo dá»¯ liá»‡u máº«u hiá»‡n táº¡i, lÆ°Æ¡ng chá»§ yáº¿u rÆ¡i vÃ o:

- `1-n`
- hoáº·c `n-1`

ChÆ°a tháº¥y pattern `n-n` rÃµ nhÆ° nhÃ³m thu khÃ¡ch hÃ ng láº·p amount.

#### g. Thu khÃ¡ch hÃ ng / cÃ´ng ná»£ / logistics láº·p amount

ÄÃ¢y lÃ  nhÃ³m dá»… phÃ¡t sinh `n-n` nháº¥t trong dá»¯ liá»‡u tháº­t.

### 9.5. Khi nÃ o lÃ  `Khá»›p`

#### `Khá»›p láº»`

Má»™t dÃ²ng nÃªn Ä‘Æ°á»£c tÃ­nh lÃ  `Khá»›p` khi:

- cÃ³ Ä‘Ãºng má»™t Ä‘á»‘i á»©ng 1-1 rÃµ rÃ ng
- cÃ¹ng chiá»u
- cÃ¹ng sá»‘ tiá»n
- ngÃ y há»£p lÃ½
- cÃ³ thÃªm báº±ng chá»©ng há»— trá»£ Ä‘á»§ cháº¯c

VÃ­ dá»¥:

- `FT` chi trá»±c tiáº¿p
- `LD/ST` cÃ³ Ä‘á»‘i á»©ng rÃµ
- `TT` cÃ³ cáº·p rÃµ
- lÃ£i ngÃ¢n hÃ ng cuá»‘i thÃ¡ng

#### `PhÃ­/VAT Ä‘Ã£ khá»›p`

Má»™t nhÃ³m nÃªn Ä‘Æ°á»£c tÃ­nh lÃ  `Khá»›p` khi:

- nhiá»u dÃ²ng bank phÃ­/VAT
- tá»•ng Ä‘Ãºng báº±ng má»™t dÃ²ng há»‡ thá»‘ng
- tá»• há»£p lÃ  duy nháº¥t
- nhÃ³m nÃ y Ä‘Ãºng nghiá»‡p vá»¥

Hiá»‡n táº¡i Ä‘Ã¢y lÃ  group match duy nháº¥t Ä‘Ã£ Ä‘Æ°á»£c source há»— trá»£ cháº¯c.

#### `Khá»›p group` tá»•ng quÃ¡t trong tÆ°Æ¡ng lai

Vá» nghiá»‡p vá»¥, `1-n / n-1` cÃ³ thá»ƒ Ä‘Æ°á»£c nÃ¢ng lÃªn `matched group` náº¿u:

- tá»• há»£p lÃ  duy nháº¥t
- tá»•ng tiá»n khá»›p tuyá»‡t Ä‘á»‘i
- cÃ¹ng chiá»u
- ngÃ y há»£p lÃ½
- cÃ³ thÃªm clue Ä‘á»§ máº¡nh

### 9.6. Khi nÃ o lÃ  `Cáº§n kiá»ƒm tra`

`review` lÃ  tráº¡ng thÃ¡i:

- cÃ³ á»©ng viÃªn há»£p lÃ½
- nhÆ°ng chÆ°a Ä‘á»§ cháº¯c Ä‘á»ƒ auto-match

Má»™t dÃ²ng nÃªn lÃ  `review` khi:

- cÃ¹ng chiá»u
- cÃ¹ng sá»‘ tiá»n
- cÃ¹ng ngÃ y hoáº·c ngÃ y gáº§n
- mÃ´ táº£ / Ä‘á»‘i tÃ¡c / reference cÃ³ liÃªn quan
- nhÆ°ng cÃ²n hÆ¡n má»™t kháº£ nÄƒng
- hoáº·c cÃ³ clue chÆ°a Ä‘á»§ máº¡nh Ä‘á»ƒ chá»‘t 1-1

#### Rule ráº¥t quan trá»ng

Náº¿u cÃ³ á»©ng viÃªn há»£p lÃ½ thÃ¬ khÃ´ng nÃªn Ä‘áº©y xuá»‘ng `unmatched` quÃ¡ sá»›m.

### 9.7. Khi nÃ o lÃ  `ChÆ°a khá»›p`

`unmatched` chá»‰ nÃªn dÃ¹ng khi:

- khÃ´ng cÃ³ á»©ng viÃªn cÃ¹ng chiá»u vÃ  amount Ä‘á»§ há»£p lÃ½
- hoáº·c ngÃ y lá»‡ch xa, khÃ´ng cÃ³ clue máº¡nh
- hoáº·c lÃ  `n-n` mÆ¡ há»“ tháº­t
- hoáº·c lÃ  ca group mÃ  chÆ°a tÃ¬m ra tá»• há»£p Ä‘á»§ cháº¯c

### 9.8. Quy táº¯c `1-n / n-1 / n-n`

#### `1-n`

Cho phÃ©p lÃªn `matched group` náº¿u:

- má»™t dÃ²ng phÃ­a A
- nhiá»u dÃ²ng phÃ­a B
- tá»•ng tiá»n khá»›p tuyá»‡t Ä‘á»‘i
- tá»• há»£p lÃ  duy nháº¥t
- cÃ³ thÃªm báº±ng chá»©ng vá» Ä‘á»‘i tÃ¡c / mÃ´ táº£ / key nghiá»‡p vá»¥

#### `n-1`

TÆ°Æ¡ng tá»± `1-n`.

#### `n-n`

KhÃ´ng auto-match.

##### `n-n` cÃ³ key riÃªng tá»«ng dÃ²ng

VÃ­ dá»¥:

- invoice riÃªng
- BL riÃªng
- PO riÃªng
- contract riÃªng
- mÃ´ táº£ vÃ  Ä‘á»‘i tÃ¡c Ä‘á»§ tÃ¡ch dÃ²ng

TrÆ°á»ng há»£p nÃ y nÃªn lÃ :

- `review`

##### `n-n` mÆ¡ há»“ tháº­t

TrÆ°á»ng há»£p:

- sá»‘ dÃ²ng báº±ng nhau
- amount báº±ng nhau
- nhÆ°ng khÃ´ng cÃ³ khÃ³a Ä‘á»§ cháº¯c Ä‘á»ƒ map 1-1

TrÆ°á»ng há»£p nÃ y nÃªn lÃ :

- `unmatched`

### 9.9. Thuáº¿ vÃ  lÆ°Æ¡ng cÃ³ pháº£i `n-n` khÃ´ng

Theo dá»¯ liá»‡u máº«u hiá»‡n táº¡i:

- `PhÃ­/VAT` lÃ  `1-n`, khÃ´ng pháº£i `n-n`
- `lÆ°Æ¡ng` chá»§ yáº¿u lÃ  `1-n` hoáº·c `n-1`
- `n-n` xuáº¥t hiá»‡n nhiá»u hÆ¡n á»Ÿ:
  - thu khÃ¡ch hÃ ng
  - cÃ´ng ná»£ láº·p amount
  - má»™t sá»‘ nhÃ³m logistics / chi phÃ­ láº·p dÃ²ng

### 9.10. Báº£ng quyáº¿t Ä‘á»‹nh tráº¡ng thÃ¡i

#### a. `Khá»›p`

Gáº¯n `Khá»›p` khi:

- exact 1-1 rÃµ rÃ ng
- hoáº·c group `1-n / n-1` Ä‘á»§ cháº¯c

#### b. `Cáº§n kiá»ƒm tra`

Gáº¯n `Cáº§n kiá»ƒm tra` khi:

- cÃ³ á»©ng viÃªn há»£p lÃ½
- nhÆ°ng cÃ²n mÆ¡ há»“
- hoáº·c lÃ  `n-n` cÃ³ thá»ƒ giáº£i báº±ng key riÃªng

#### c. `ChÆ°a khá»›p`

Gáº¯n `ChÆ°a khá»›p` khi:

- khÃ´ng cÃ³ á»©ng viÃªn há»£p lÃ½
- hoáº·c lÃ  `n-n` mÆ¡ há»“ tháº­t

---

## 10. Dá»¯ liá»‡u nÃ o Ä‘Æ°á»£c tÃ­nh lÃ  `Khá»›p`, `Review`, `ChÆ°a khá»›p`

ÄÃ¢y lÃ  cÃ¡ch hiá»ƒu trá»±c quan Ä‘á»ƒ dÃ¹ng khi kiá»ƒm tra nghiá»‡p vá»¥.

### 10.1. Dá»¯ liá»‡u Ä‘Æ°á»£c tÃ­nh lÃ  `Khá»›p`

#### a. `Khá»›p láº»`

Gá»“m cÃ¡c trÆ°á»ng há»£p:

- há»‡ thá»‘ng vÃ  bank cÃ³ cáº·p 1-1 rÃµ rÃ ng
- cÃ¹ng chiá»u
- cÃ¹ng sá»‘ tiá»n
- ngÃ y phÃ¹ há»£p
- cÃ³ thÃªm báº±ng chá»©ng máº¡nh

CÃ¡c nhÃ³m Ä‘ang cÃ³ xÃ¡c suáº¥t Ä‘Ãºng cao:

- `FT` chi trá»±c tiáº¿p
- `LD/ST` cÃ³ Ä‘á»‘i á»©ng rÃµ
- `TT` cÃ³ cáº·p rÃµ
- lÃ£i ngÃ¢n hÃ ng cuá»‘i thÃ¡ng

#### b. `PhÃ­/VAT Ä‘Ã£ khá»›p`

Gá»“m cÃ¡c trÆ°á»ng há»£p:

- nhiá»u dÃ²ng bank phÃ­/VAT
- tá»•ng báº±ng má»™t dÃ²ng há»‡ thá»‘ng
- tá»• há»£p duy nháº¥t

### 10.2. Dá»¯ liá»‡u Ä‘Æ°á»£c tÃ­nh lÃ  `Cáº§n kiá»ƒm tra`

Gá»“m cÃ¡c trÆ°á»ng há»£p:

- cÃ¹ng chiá»u
- cÃ¹ng sá»‘ tiá»n
- cÃ¹ng ngÃ y hoáº·c ngÃ y gáº§n
- cÃ³ Ä‘á»‘i tÃ¡c hoáº·c mÃ´ táº£ hoáº·c reference liÃªn quan
- nhÆ°ng chÆ°a Ä‘á»§ cháº¯c

ThÆ°á»ng rÆ¡i vÃ o:

- nhiá»u á»©ng viÃªn cÃ¹ng amount
- mÃ´ táº£ gáº§n Ä‘Ãºng nhÆ°ng chÆ°a khÃ³a Ä‘Æ°á»£c 1-1
- `n-n` cÃ³ thá»ƒ phÃ¢n rÃ£ náº¿u trÃ­ch thÃªm key

### 10.3. Dá»¯ liá»‡u Ä‘Æ°á»£c tÃ­nh lÃ  `ChÆ°a khá»›p`

Gá»“m cÃ¡c trÆ°á»ng há»£p:

- khÃ´ng cÃ³ Ä‘á»‘i á»©ng cÃ¹ng amount
- khÃ¡c chiá»u
- cÃ¹ng amount nhÆ°ng ngÃ y lá»‡ch xa vÃ  khÃ´ng cÃ³ clue máº¡nh
- `1-n / n-1` mÃ  engine chÆ°a tÃ¬m Ä‘Æ°á»£c tá»• há»£p
- `n-n` mÆ¡ há»“ tháº­t

---

## 11. Nhá»¯ng gÃ¬ source hiá»‡n táº¡i lÃ m Ä‘Ãºng

- Ä‘á»c Ä‘Æ°á»£c file máº«u tháº­t
- detector loáº¡i file hoáº¡t Ä‘á»™ng Ä‘Ãºng trÃªn cÃ¡c bá»™ máº«u
- scan flow Ä‘Ã£ á»•n Ä‘á»‹nh láº¡i sau refactor
- cáº­p nháº­t UI cháº¡y trÃªn Ä‘Ãºng GUI thread
- khÃ´ng cÃ²n regression `QObject different thread` trong luá»“ng scan chuáº©n
- `PhÃ­/VAT` Ä‘Ã£ cÃ³ group match riÃªng
- popup detail Ä‘Ã£ hiá»ƒn thá»‹ Ä‘Æ°á»£c cáº·p/group/review candidate
- UI Ä‘Ã£ tÃ¡ch nhá» Ä‘Ã¡ng ká»ƒ so vá»›i phiÃªn báº£n ban Ä‘áº§u

---

## 12. Háº¡n cháº¿ hiá»‡n táº¡i

### 12.1. Engine group cÃ²n háº¹p

Hiá»‡n source má»›i há»— trá»£ cháº¯c `group match` cho `PhÃ­/VAT`.

ChÆ°a cÃ³ engine tá»•ng quÃ¡t cho:

- lÆ°Æ¡ng
- thÆ°á»Ÿng
- cÃ¡c khoáº£n bá»‹ tÃ¡ch 1-2, 2-1
- cÃ¡c cá»¥m chi phÃ­ hoáº·c doanh thu bá»‹ chia/gá»™p khÃ¡c

### 12.2. `review / unmatched` váº«n cáº§n tinh chá»‰nh

Hiá»‡n táº¡i váº«n cÃ²n cÃ¡c case:

- cÃ¹ng tiá»n
- cÃ¹ng ngÃ y hoáº·c ngÃ y gáº§n
- cÃ³ thÃªm clue

nhÆ°ng source váº«n cÃ³ thá»ƒ Ä‘á»ƒ `unmatched` náº¿u chÆ°a Ä‘á»§ rule nÃ¢ng sang `review`.

### 12.3. `n-n` chÆ°a Ä‘Æ°á»£c phÃ¢n loáº¡i sÃ¢u

ChÆ°a cÃ³ cÆ¡ cháº¿ tá»•ng quÃ¡t Ä‘á»ƒ tÃ¡ch:

- `n-n` cÃ³ thá»ƒ giáº£i báº±ng key riÃªng tá»«ng dÃ²ng
- `n-n` mÆ¡ há»“ tháº­t

### 12.4. Rule exact theo tá»«ng nhÃ³m nghiá»‡p vá»¥ cáº§n rÃ  ká»¹ hÆ¡n

CÃ¡c family cáº§n audit tiáº¿p:

- `FT`
- `TT`
- `LD/ST`
- `HB`
- lÃ£i ngÃ¢n hÃ ng

### 12.5. Dá»¯ liá»‡u phá»¥ trá»£ chÆ°a Ä‘á»§ phong phÃº

Hiá»‡n source váº«n cÃ²n thiáº¿u á»Ÿ má»™t sá»‘ Ä‘iá»ƒm:

- alias tÃªn Ä‘á»‘i tÃ¡c
- invoice / BL / PO / contract extractor Ä‘áº§y Ä‘á»§
- má»™t sá»‘ key phá»¥ nhÆ° `PPP`, `BHD`
- xá»­ lÃ½ gross / net á»Ÿ cÃ¡c case thu cÃ³ phÃ­

---

## 13. Backlog ká»¹ thuáº­t vÃ  nghiá»‡p vá»¥ tiáº¿p theo

### 13.1. Æ¯u tiÃªn sá»‘ 1: tinh chá»‰nh `review / unmatched`

Má»¥c tiÃªu:

- nhá»¯ng case cÃ³ á»©ng viÃªn há»£p lÃ½ khÃ´ng bá»‹ Ä‘á» quÃ¡ tay
- nhÆ°ng váº«n khÃ´ng auto-match bá»«a

### 13.2. Æ¯u tiÃªn sá»‘ 2: lÃ m `group match` tá»•ng quÃ¡t cho `1-n / n-1`

Æ¯u tiÃªn cÃ¡c ca rÃµ nháº¥t:

- lÆ°Æ¡ng
- thÆ°á»Ÿng
- cÃ¡c khoáº£n tÃ¡ch dÃ²ng nhÆ°ng tá»•ng tiá»n vÃ  ngÃ y ráº¥t rÃµ

### 13.3. Æ¯u tiÃªn sá»‘ 3: audit exact rule theo tá»«ng nhÃ³m giao dá»‹ch

- `FT`
- `TT`
- `LD/ST`
- `HB`
- lÃ£i cuá»‘i thÃ¡ng

### 13.4. Æ¯u tiÃªn sá»‘ 4: tÄƒng dá»¯ liá»‡u phá»¥ trá»£

- trÃ­ch thÃªm key tá»« text
- alias tÃªn Ä‘á»‘i tÃ¡c
- invoice / BL / PO / contract
- gross / net cho má»™t sá»‘ case thu cÃ³ phÃ­

### 13.5. Æ¯u tiÃªn sá»‘ 5: khÃ³a báº±ng test

Cáº§n bá»• sung test cho:

- `same amount + near date -> review`
- `direction mismatch -> unmatched`
- `1-n / n-1`
- `n-n khÃ´ng auto-match`
- `n-n cÃ³ key riÃªng -> review`
- exact rule cho tá»«ng family

---

## 14. Kiáº¿n trÃºc UI hiá»‡n táº¡i

Pháº§n UI hiá»‡n Ä‘Ã£ Ä‘Æ°á»£c tÃ¡ch theo hÆ°á»›ng dá»… báº£o trÃ¬ hÆ¡n.

### 14.1. Kiáº¿n trÃºc chÃ­nh

- `MainWindow`
  - chá»‰ Ä‘iá»u phá»‘i
- `page + mixin + component`

### 14.2. MÃ n hÃ¬nh

- `StartupPage`
  - chá»‰ chá»n file vÃ  báº¯t Ä‘áº§u dÃ²
- `ResultsPage`
  - hiá»ƒn thá»‹ metadata, filter, action, grid

### 14.3. Mixin

- `main_window_scan_mixin.py`
  - chá»n file, cháº¡y scan, bind result, chuyá»ƒn page
- `main_window_filter_mixin.py`
  - filter/search/summary
- `main_window_actions_mixin.py`
  - history/export/detail dialog

### 14.4. Component

- chip/button riÃªng
- panel riÃªng
- dialog riÃªng
- style riÃªng
- metadata layout riÃªng

Má»¥c tiÃªu cá»§a kiáº¿n trÃºc hiá»‡n táº¡i:

- trÃ¡nh dá»“n toÃ n bá»™ UI vÃ o má»™t file ráº¥t lá»›n
- dá»… chá»‰nh sá»­a tá»«ng cá»¥m giao diá»‡n
- giáº£m rá»§i ro style Ä‘Ã¨ láº«n nhau

---

## 15. Kiá»ƒm thá»­ hiá»‡n cÃ³

### 15.1. Test logic Ä‘á»‘i soÃ¡t

`tests/test_reconciliation_logic.py`

Bao phá»§:

- exact match
- VAT/Homebanking group
- review
- unmatched
- má»™t sá»‘ regression nghiá»‡p vá»¥ Ä‘Ã£ sá»­a

### 15.2. Test scan flow UI

`tests/test_main_window_scan_flow.py`

Bao phá»§:

- startup page compact
- scan success -> results page
- scan fail -> quay láº¡i startup
- queued connection
- filter loading khÃ´ng Ä‘Ã¨ scan overlay

### 15.3. Test detector file

`tests/test_excel_file_kind.py`

Bao phá»§ detector trÃªn dá»¯ liá»‡u tháº­t trong repo.

---

## 16. CÃ¡ch cháº¡y source

### 16.1. Cháº¡y app

```bash
python main.py
```

### 16.2. Cháº¡y test

```bash
python -m unittest tests.test_reconciliation_logic tests.test_main_window_scan_flow tests.test_excel_file_kind
```

### 16.3. Kiá»ƒm tra compile

```bash
python -m compileall app tests
```

### 16.4. Build `.exe`

```bash
build_exe.bat
```

---

## 17. Káº¿t luáº­n hiá»‡n tráº¡ng

TÃ­nh Ä‘áº¿n thá»i Ä‘iá»ƒm cáº­p nháº­t README nÃ y:

- kiáº¿n trÃºc UI Ä‘Ã£ Ä‘Æ°á»£c refactor Ä‘á»§ sáº¡ch Ä‘á»ƒ tiáº¿p tá»¥c phÃ¡t triá»ƒn
- scan flow vÃ  luá»“ng thread Ä‘Ã£ Ä‘Æ°á»£c khÃ´i phá»¥c á»•n Ä‘á»‹nh
- detector file máº«u Ä‘Ã£ Ä‘Æ°á»£c khÃ³a báº±ng test
- source hiá»‡n Ä‘á»‘i soÃ¡t á»•n cho nhiá»u ca 1-1 vÃ  `PhÃ­/VAT`
- pháº§n cÃ²n cáº§n lÃ m tiáº¿p lÃ  hoÃ n thiá»‡n logic nghiá»‡p vá»¥ cho:
  - `review / unmatched`
  - `1-n / n-1`
  - exact rule theo tá»«ng nhÃ³m giao dá»‹ch

NÃ³i ngáº¯n gá»n:

- **kiáº¿n trÃºc hiá»‡n táº¡i Ä‘Ã£ Ä‘á»§ tá»‘t Ä‘á»ƒ phÃ¡t triá»ƒn tiáº¿p**
- **Æ°u tiÃªn tiáº¿p theo lÃ  quay láº¡i hoÃ n thiá»‡n engine dÃ² nghiá»‡p vá»¥**

