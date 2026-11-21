# Scoring guide: keyword và thành phần ảnh hưởng đến điểm

Tài liệu này là phần **vận hành** của rubric v1.1 trong `docs/SCORING_PILOT.md`: chỉ ra, với từng thang điểm (`event_label`, `sentiment`, `fear`), những **keyword** và **thành phần** của bài báo quyết định điểm, kèm bằng chứng đo được từ tập phát triển.

| Mục | Giá trị |
|---|---|
| Phiên bản | Guide v0.1 (draft), tương thích rubric v1.1 |
| Ngày | 2026-11-21 |
| Đối tượng | Rater (người) và người viết prompt LLM; nội dung tiếng Việt, tên field tiếng Anh |
| Quy tắc ưu tiên | Nếu guide mâu thuẫn `SCORING_PILOT.md`, **`SCORING_PILOT.md` thắng** |
| Đổi điểm số | Thêm hoặc bớt cue ở bảng chuẩn (mục 4.2) là thay đổi rubric, phải nâng lên v1.2. Sửa bảng bằng chứng không cần nâng phiên bản |

Mỗi quy tắc trong guide mang một nhãn nguồn:

| Nhãn | Ý nghĩa |
|---|---|
| **[v1.1]** | Trích hoặc áp dụng trực tiếp từ rubric v1.1 |
| **[QS]** | Quan sát từ tập phát triển (hai rater, rubric v1.0); mô tả hành vi rater, chưa phải quy tắc |
| **[ĐX]** | Đề xuất mới, chưa kiểm chứng; chỉ có hiệu lực sau khi chủ đồ án duyệt và kiểm tra trên mẫu seed 43 |

## 0. Cách dùng và giới hạn của bằng chứng

1. Keyword là **tín hiệu hỗ trợ phán đoán**, không phải bộ phân loại tự động. Luôn đọc ngữ cảnh: cùng một từ có thể là cue hoặc không (mục 4.3).
2. Nguồn số liệu: tập phát triển `data/pilot/` (seed 42, 300 bài, hai rater, chấm theo rubric v1.0) và toàn bộ `data/news/*.jsonl` (124.179 dòng tại thời điểm tính). Số liệu trong guide là **thống kê mô tả in-sample**, không dùng như xác suất.
3. Cỡ mẫu nhỏ: nhiều keyword chỉ có 1 đến 5 bài trong tập phát triển. Cột `n` luôn được ghi; đừng suy diễn từ n < 5.
4. Rater 1 không ghi `notes`; chỉ rater 2 có ghi chú (26/61 bài fear >= 1). Quy ước rater suy ra từ ghi chú của rater 2 và từ chỗ hai rater trùng nhau.
5. Cách khớp keyword: Unicode NFC, chữ thường, chuỗi `title + " . " + summary`, khớp theo ranh giới từ, không bỏ dấu. Điểm trung bình ghi dạng `h1/h2` (rater 1 / rater 2).

## 1. Quy trình chấm một bài và các thành phần ảnh hưởng

Thứ tự chấm: (1) `event_label` theo 10 bước [v1.1]; (2) `sentiment`; (3) `fear` kèm cue; (4) ghi `notes`. Chỉ dùng title và summary [v1.1].

| Thành phần của bài | event_label | sentiment | fear |
|---|---|---|---|
| Chủ thể (một công ty, thị trường, cơ quan quản lý, vĩ mô) | **Quyết định chính** (bước 3 đến 9) | Xác định "nhà đầu tư nào" chịu tác động | Cue phải nói về rủi ro của nhà đầu tư [v1.1 rule 4] |
| Sự kiện **đứng đầu tiêu đề** | Quyết định bước 8 [v1.1] | Quyết định dấu khi tín hiệu hỗn hợp [QS] | Không ảnh hưởng |
| Chiều tác động lên giá hoặc lợi nhuận | Không | **Quyết định dấu** | Không (độc lập, rule 6) |
| Mức độ cực đoan (sập phiên, giảm sàn liên tiếp, đình chỉ giao dịch) | Không | Quyết định ±2 so với ±1 (mục 3.3) | Quyết định mức 3 đến 4 nếu có cue |
| **Cue ngôn ngữ** (thận trọng, lo ngại, rủi ro...) | Không | Không | **Bắt buộc có** để fear >= 1 [v1.1] |
| Phủ định hoặc cue đã được giải quyết | Không | Không | Cue không tính (mục 5) |
| Nguồn phát ngôn (trích dẫn, quan điểm đối lập) | Không | Không | Cue của bên khác chỉ tính khi bài đồng tình (mục 5) |
| Thể loại (PR, explainer, bản tin tổng hợp) | `other` hoặc `market_commentary` (mục 2.2) | 0 | 0 |
| Con số đơn thuần (%, tỷ đồng, điểm) | Không | Có thể quyết định dấu | **Không bao giờ là cue** [v1.1 rule 2] |

## 2. event_label

### 2.1 Keyword theo thứ tự quy trình

Cột "Bằng chứng" là `k/n`: trong n bài chứa keyword, k bài **cả hai rater** chọn đúng nhãn đó (tập phát triển). Keyword yếu (k/n < 60%) chỉ để tham khảo, không dùng một mình.

| Bước [v1.1] | Nhãn | Keyword mạnh (bằng chứng `k/n`, hoặc định nghĩa rubric) | Keyword yếu hoặc dễ nhầm |
|---|---|---|---|
| 1 | `other` | giải thưởng, kỷ niệm, "... là gì?", "bạn hiểu gì về...", đại lý phân phối, cảnh báo lừa đảo | Dấu "?" trong tiêu đề **không** quyết định (mục 4.3) |
| 2 | `public_health_disaster` | đại dịch, dịch bệnh, đợt dịch, bão, lũ (sự kiện chính của bài) | "covid" 0/6 (chỉ là bối cảnh của bài lợi nhuận); "dịch" đứng riêng không dùng được vì trùng âm tiết trong "giao dịch" (61 bài) |
| 3 | `regulation_legal` | xử phạt 7/7, vi phạm 8/8, khởi tố 3/3, Ủy ban Chứng khoán 6/8, thanh tra 2/3, diện cảnh báo, kiểm soát, hạn chế giao dịch, đình chỉ giao dịch, nghị định, thông tư | giải trình (cơ quan yêu cầu giải trình): rater từng chọn `corporate_action`, xem mục 7 |
| 4 | `macro_policy` | GDP, đầu tư công, FDI, ngân sách, thu nội địa, giảm thuế VAT (chính sách cấp quốc gia) | "thuế" 2/24: **không** là cue khi nằm trong "lợi nhuận sau thuế", "lãi trước thuế", LNST (đó là `corporate_earnings`) |
| 4 | `monetary_credit` | Ngân hàng Nhà nước 3/3, thống đốc, lãi suất, room tín dụng, tỷ giá điều hành | "thanh khoản" 0/5 (thường là nhận định thị trường, bước 9) |
| 5 | `real_estate_bond_credit` | trái phiếu 5/7, nợ xấu (chủ đề chính của bài) | "bất động sản" 0/7: nhắc lĩnh vực khi nói về hoạt động một công ty hoặc PR thì **không** thuộc bước 5 |
| 6 | `global_geopolitics` | Fed, thuế quan Mỹ, chiến tranh, giá vàng thế giới, giá dầu thế giới | "Trung Quốc" 1/4, "giá dầu" 0/3: thường chỉ là bối cảnh (bước 8 hoặc 9) |
| 7 | `fund_flow` | bán ròng 8/11, mua ròng 5/8, tự doanh 6/8, ETF (dòng tiền tổng hợp) | "khối ngoại" 5/13 và "quỹ" 5/12: xuất hiện cả trong bản tin thị trường (bước 9) |
| 8 | `corporate_earnings` | lãi ròng 6/7, cùng kỳ 10/12, báo lãi 5/7, doanh thu 11/16, lợi nhuận 16/24, kết quả kinh doanh, LNST | "quý" 18/32 (quá chung) |
| 8 | `corporate_action` | đăng ký mua 4/4, đăng ký bán 5/5, chốt quyền 6/6, HĐQT 10/12, cổ tức 13/19, tỷ lệ 14/21, phát hành 6/10, bổ nhiệm 2/3 | "niêm yết" 2/11: rater chia đều giữa nhiều nhãn, quyết định theo sự kiện đứng đầu tiêu đề |
| 9 | `market_commentary` | góc nhìn 12/13, chứng quyền 7/8, tin vắn 4/4, nhịp đập thị trường, VN-Index 17/26, nhận định, khuyến nghị | "phái sinh" 2/7 (báo cáo phái sinh hằng ngày thuộc bước 9 theo rubric, nhưng rater từng chọn nhãn khác); "phiên" 24/50 (quá chung) |
| 10 | `other` | Không khớp bước nào | |

Keyword không có `k/n` lấy từ định nghĩa nhãn trong rubric; tập phát triển chưa có đủ bài (n < 3) để kiểm chứng.

### 2.2 Quy ước đã quan sát

| Tình huống | Quy ước | Nhãn nguồn |
|---|---|---|
| Bản tin tổng hợp, lịch sự kiện, tin vắn, "đọc gì trước giờ giao dịch" | `market_commentary`, sentiment 0, fear 0 (tin vắn 4/4; ba bài "đọc gì..." đều fear 0/0) | [QS] |
| PR, giải thưởng, kỷ niệm công ty, đại lý dự án | `other`, 0, 0 | [QS] + [v1.1 bước 1] |
| Quỹ hoặc cổ đông lớn mua, bán **một** cổ phiếu | `corporate_action` (không phải `fund_flow`); sentiment mua +1, bán −1 | [v1.1 bước 7] + [QS] |
| Kế hoạch lợi nhuận kèm cổ tức (vd. FPT) | Sự kiện đứng đầu tiêu đề quyết định: kế hoạch lợi nhuận -> `corporate_earnings` | [v1.1 bước 8] |
| Cổ tức kèm lợi nhuận giảm | `corporate_action`, sentiment 0 (tín hiệu hỗn hợp) | [QS] |
| Doanh nghiệp bị truy thu, cưỡng chế thuế, phạt hành chính | `regulation_legal` (cơ quan xử lý một doanh nghiệp cụ thể) | [v1.1 bước 3] |
| Bài ghi "phân vân giữa hai nhãn" | Theo thứ tự bước; ghi nhãn còn lại vào `notes` | [v1.1] |

### 2.3 Keyword gây nhầm (false friends)

| Keyword | Vì sao nhầm | Cách xử lý |
|---|---|---|
| "thuế" trong "lãi sau thuế" | Một rater chọn `macro_policy` cho 5 bài lợi nhuận ("sau thuế", "trước thuế") | `corporate_earnings` (bước 8) |
| "dịch" | Trùng âm tiết trong "giao dịch" | Chỉ dùng "đại dịch", "dịch bệnh", "dịch covid", "đợt dịch" |
| "bất động sản" | Là bối cảnh hoặc PR của công ty | Bước 5 chỉ khi bất động sản, trái phiếu doanh nghiệp hoặc nợ xấu là chủ đề chính |
| "khối ngoại", "quỹ" | Có trong bản tin thị trường | `fund_flow` chỉ khi dòng tiền là nội dung chính của tiêu đề |

## 3. sentiment

Sentiment đo **chiều tác động của thông tin lên nhà đầu tư vào thực thể hoặc thị trường mà bài nói tới** (-2 đến +2). Thang này đã đạt alpha 0.778 ở vòng 1 và được giữ nguyên [v1.1].

### 3.1 Keyword định hướng dấu

Cột điểm là trung bình `h1/h2` trên các bài chứa keyword; "cùng dấu" là tỷ lệ bài mà cả hai rater cùng dấu đúng chiều kỳ vọng.

| Dấu | Keyword | n | Điểm TB | Cùng dấu |
|---|---|---|---|---|
| + | kỷ lục | 5 | 1.20 / 1.00 | 100% |
| + | tích cực | 8 | 1.00 / 1.00 | 100% |
| + | cổ tức bằng tiền | 2 | 1.00 / 1.00 | 100% |
| + | chia cổ tức | 6 | 0.83 / 0.83 | 67% |
| + | hồi phục | 6 | 0.67 / 0.83 | 83% |
| + | tăng điểm | 8 | 0.62 / 0.75 | 75% |
| + | báo lãi | 7 | 0.71 / 0.86 | 71% |
| + | mua vào (nội bộ, cổ đông lớn) | 8 | 0.75 / 1.00 | 62% |
| − | vi phạm | 8 | −1.12 / −1.00 | 88% |
| − | xử phạt | 7 | −1.00 / −0.86 | 86% |
| − | bị phạt | 5 | −1.00 / −0.80 | 80% |
| − | cưỡng chế | 2 | −1.00 / −1.00 | 100% |
| − | giảm sàn | 3 | −1.33 / −1.33 | 67% |
| − | bán ra (nội bộ, cổ đông lớn) | 4 | −1.00 / −0.75 | 75% |
| − | giảm điểm | 8 | −0.88 / −0.75 | 75% |
| − | bán ròng | 11 | −0.55 / −0.55 | 73% |
| − | thoái vốn | 2 | −1.00 / −1.00 | 100% |

### 3.2 Keyword **phụ thuộc ngữ cảnh** (không chấm theo từ khóa)

| Keyword | n | Điểm TB | Vì sao không đọc được dấu từ từ khóa |
|---|---|---|---|
| tăng mạnh | 10 | 0.50 / 0.80 (cùng dấu 60%) | Tăng của giá khác tăng của chi phí hoặc nợ |
| tăng trần | 5 | 0.20 / 0.40 (40%) | Có thể nằm trong bài giải trình hoặc cảnh báo |
| bứt phá | 2 | 0.00 / 0.00 | Thường nằm trong nhận định có điều kiện |
| tăng trưởng | 13 | 0.46 / 0.69 (46%) | Tăng trưởng của cái gì, so với kỳ vọng nào |
| lãi ròng | 7 | 0.43 / 0.57 (57%) | "Lãi ròng giảm" cũng chứa từ này |
| giảm mạnh | 8 | −0.75 / −0.12 (38%) | Rater bất đồng: mô tả giá hay mô tả khối lượng |
| sụt giảm | 4 | −0.50 / +0.25 (50%) | Tương tự |
| lỗ | 8 | −0.12 / −0.25 (38%) | Thường là "lãi/lỗ" chung chung |
| thanh tra | 3 | −1.00 / −0.33 (33%) | Mức độ nghiêm trọng khác nhau |

### 3.3 Mức ±2 và quy ước dòng tiền

- Cả hai rater cùng chấm |s| = 2 ở 5/300 bài, **đều là −2**: sập phiên ("bất ngờ sụp đổ cuối phiên"), VN-Index giảm hơn 4% ("giảm mạnh nhất thế giới"), doanh nghiệp bị đình chỉ giao dịch, giảm sàn 20 phiên liên tiếp, phải giải trình với Ủy ban Chứng khoán [QS].
- **+2 chưa bao giờ được cả hai rater cùng chọn.** Các bài một rater chấm +2, rater kia +1: lãi gấp nhiều lần cùng kỳ (gấp 4, gấp 12, tăng 182%), "báo lãi khủng", "thiết lập đỉnh mới" [QS].
- Khi phân vân giữa +1 và +2 (hoặc −1 và −2): **chọn mức thấp hơn và ghi cả hai vào `notes`** [v1.1 rule 7].
- Bài có tiêu đề về **dòng tiền tổng hợp** (tự doanh, khối ngoại, ETF): dấu theo chiều ròng, độ lớn 1. Trong 11 bài chứa "mua ròng" hoặc "bán ròng" và được gán `fund_flow`, hai rater trùng điểm sentiment ở cả 11 [QS].
- Tín hiệu hỗn hợp trong một bài (vd. lãi cả năm kỷ lục nhưng quý 4 giảm 35%): theo sự kiện đứng đầu tiêu đề; nếu vẫn phân vân chọn mức thấp hơn [QS + v1.1 rule 7].
- Lợi nhuận giảm nêu thẳng thừng: sentiment âm, **fear 0** [v1.1 rule 2].

## 4. fear

Fear đo **mức báo động, bất định hoặc ngại mất mát mà từ ngữ của bài thể hiện**, độc lập với sentiment [v1.1]. Fear > 0 bắt buộc có cue chép nguyên văn vào `notes`; bài chấm >= 1 mà không có cue là không hợp lệ [v1.1].

### 4.1 Bức tranh phân bố (tập phát triển)

- 207/300 bài cả hai rater chấm 0; 48 bài cả hai chấm >= 1; 93 bài ít nhất một rater chấm >= 1.
- Vì dương tính hiếm, alpha rất nhạy với vài chục bài có fear thật; quy mô mẫu và phương án dự phòng xem `SCORING_PILOT.md` mục 4.

### 4.2 Bảng cue chuẩn [v1.1] kèm bằng chứng

Đây là lexicon **chính thức**. Cột "TB dev" là điểm trung bình `h1/h2` trên các bài tập phát triển có chứa cue; "Corpus" là số bài chứa cue trong toàn bộ dữ liệu. Dấu "—" nghĩa là chưa đo hoặc không có bài.

| Mức | Cue | n dev | TB dev | Corpus |
|---|---|---|---|---|
| 1 | thận trọng | 3 | 0.67 / 0.67 | 1.446 |
| 1 | cẩn trọng | 0 | — | 252 |
| 1 | dè dặt | 1 | 0.00 / 0.00 | 58 |
| 1 | cần lưu ý | 0 | — | 114 |
| 1 | áp lực | 2 | 1.50 / 1.00 | 2.460 |
| 1 | rung lắc | 1 | 1.00 / 1.00 | 928 |
| 1 | biến động mạnh | 1 | 1.00 / 1.00 | 375 |
| 1 | bất định | 0 | — | 61 |
| 2 | lo ngại | 2 | 1.00 / 0.50 | 390 |
| 2 | lo lắng | 0 | — | 108 |
| 2 | rủi ro | 2 | 2.00 / 1.50 | 1.933 |
| 2 | nguy cơ | 1 | 2.00 / 1.00 | 360 |
| 2 | bi quan | 2 | 1.50 / 1.00 | 582 |
| 2 | đáng lo | 1 | 1.00 / 0.00 | 31 |
| 2 | bất ổn | 1 | 2.00 / 1.00 | 163 |
| 2 | suy thoái | 1 | 2.00 / 1.00 | 95 |
| 2 | điều chỉnh sâu | 1 | 2.00 / 2.00 | 58 |
| 3 | bán tháo | 1 | 2.00 / 2.00 | 314 |
| 3 | call margin | 0 | — | 65 |
| 3 | nguy cơ vỡ nợ (đo theo "vỡ nợ") | 0 | — | 26 |
| 3 | giảm sàn hàng loạt, lo ngại mang tính hệ thống | — | — | — |
| 3 | sụp đổ (trong một phiên) | 1 | 3.00 / 3.00 | 48 |
| 4 | hoảng loạn | 2 | 2.50 / 2.00 | 78 |
| 4 | khủng hoảng | 0 | — | 211 |
| 4 | ngừng giao dịch, dừng giao dịch (khẩn cấp, toàn thị trường) | 0 | — | 42 và 37 |
| 4 | lan truyền | 0 | — | 43 |
| 4 | biện pháp khẩn cấp | — | — | — |

Đọc bảng:

- Có 19/300 bài chứa ít nhất một cue chuẩn. Trong 19 bài đó, 15 bài cả hai rater chấm >= 1 và 17 bài ít nhất một rater chấm >= 1: **độ chính xác cao** (79% và 89%).
- Hai bài chứa cue nhưng cả hai rater chấm 0 là ví dụ thật cho hai quy tắc loại trừ: "dè dặt" trong "bsr **sau thời gian dè dặt**... đã phản ánh sự lạc quan" (cue đã được giải quyết, rule 3) và "công ty vẫn cân nhắc **thận trọng**" khi nói về việc mời cổ đông lớn (không nói về rủi ro của nhà đầu tư, rule 4).
- Mức điểm của cue là **mức mặc định**. Quan sát: "lo ngại" (mức 2) và "bán tháo" (mức 3) từng được chấm thấp hơn một bậc (n = 2 và 1); xem mục 7.

### 4.3 Cụm từ **không** là cue khi đứng một mình

| Cụm hoặc dấu hiệu | Bằng chứng | Quy tắc |
|---|---|---|
| giảm mạnh | 8 bài: chỉ 25% cả hai rater >= 1, 50% cả hai = 0; corpus 3.832 bài | Mô tả biến động giá, **không** phải cue; cần cue riêng đi kèm |
| sụt giảm | 4 bài: 25% / 50% tương tự | Như trên |
| xả, xả hàng | 5 bài: fear TB 0.60 / 0.00 | Mô tả bán ròng (sentiment −1), fear 0 |
| phân hóa, đảo chiều | phân hóa: 4/4 bài cả hai = 0; đảo chiều: 0/3 bài cả hai >= 1 | Không phải cue |
| Dấu "?" trong tiêu đề | 30 bài: chỉ 8 cả hai >= 1, 17 cả hai = 0 | Không phải cue; nhiều là tiêu đề explainer hoặc mô tả tuần |
| Con số (%, điểm, tỷ đồng) | [v1.1 rule 2] | Không bao giờ là cue |
| Thông báo xử phạt, cưỡng chế thuế, khởi tố, đình chỉ giao dịch **không kèm** từ ngữ lo ngại | Xem mục 4.4 | `regulation_legal`, sentiment −1, **fear 0** |

### 4.4 Phát hiện quan trọng: lexicon v1.1 không phủ phần lớn bài fear dương của vòng 1

- Trong 48 bài cả hai rater chấm >= 1, chỉ **15 bài** (31%) chứa cue chuẩn; **33 bài** (69%) không chứa cue nào (khớp theo chuỗi). Với 93 bài ít nhất một rater chấm >= 1, độ phủ chỉ 17 bài (18%).
- 33 bài đó gồm: 14 bài kiểu chế tài hoặc giải trình (phạt hành chính, cưỡng chế thuế, khởi tố, đình chỉ giao dịch, giải trình), 5 bài tiêu đề có dấu "?", 7 bài bản tin thị trường dùng từ như "giảm sâu", "giằng co", "đen tối", "bấp bênh", "vượt bão", "điều chỉnh", 7 bài hỗn hợp (vd. "thế khó của PNJ", "ôm tiền chờ đợi").
- Nhóm xử phạt là cụm lớn nhất: 9 bài chứa "phạt" hoặc "vi phạm" (gồm "xử phạt", "bị phạt"), 7 bài cả hai rater chấm fear >= 1, sentiment trung bình −1.00. Rubric v1.1 (rule 2 và rule 6) xử lý nhóm này là **sentiment −1, fear 0**, vì thông tin đã được `sentiment` và `event_label = regulation_legal` mô tả; nếu cũng tính vào fear thì fear sẽ trùng lặp với sentiment trong mô hình dự báo.
- Hệ quả: nếu rater tuân thủ v1.1 đúng chữ, tỷ lệ bài fear >= 1 sẽ giảm mạnh so với vòng 1 (ước lượng thô: các bài chứa cue chuẩn chỉ chiếm 19/300 = 6%). Cần chuẩn bị phương án dự phòng nhị phân của mục 4 `SCORING_PILOT.md`.
- **Không** thêm từ vào lexicon dựa trên tập phát triển: bằng chứng mỏng (các cụm thị trường chỉ có 1 đến 2 bài mỗi cụm) và có nguy cơ overfit. Thay vào đó dùng quy ước ghi "phân vân" bên dưới để thu bằng chứng độc lập trên mẫu seed 43.

### 4.5 Quy ước ghi "phân vân" để làm bằng chứng cho v1.2 [ĐX]

Khi rater cảm thấy bài có fear nhưng không tìm được cue trong bảng 4.2 (hoặc phân vân 0 và 1): chấm mức **thấp hơn** [v1.1 rule 7] và ghi vào `notes` theo mẫu:

```
torn 0/1: <cụm từ nguyên văn khiến phân vân>
```

Sau vòng 2, gom các cụm `torn`. Một cụm được đề cử vào v1.2 khi: xuất hiện >= 5 bài trong mẫu seed 43 **và** >= 60% các bài chứa cụm đó được cả hai rater (khi chấm lại có cue mở rộng) cùng chấm >= 1. Ngưỡng này được khai báo trước khi nhìn dữ liệu seed 43.

## 5. Phủ định, cường độ và nguồn phát ngôn (áp dụng cho cả ba thang)

| Mẫu | Xử lý | Nguồn |
|---|---|---|
| Phủ định: "không đáng lo ngại" | Cue không tính; chấm theo cue còn lại, nếu không có thì 0 | [v1.1 rule 3] |
| Đã giải quyết: "đã đi qua vùng hoảng loạn", "sau thời gian dè dặt... lạc quan" | Cue không tính | [v1.1 rule 3] + [QS] |
| Cue nói về chính sách hoặc cân nhắc nội bộ của công ty, không phải rủi ro của nhà đầu tư | Không tính ("công ty vẫn cân nhắc thận trọng") | [v1.1 rule 4] + [QS] |
| Cảnh báo ngoài đầu tư (lừa đảo, an toàn) | `other`, 0, 0 | [v1.1 rule 4] |
| Quan điểm đối lập: "một số lo ngại, nhưng..." | Chấm ở mức thấp hơn | [v1.1 rule 5] |
| Fear cùng lúc với sentiment dương (hồi phục "có thể là bẫy") | Chấm hai thang độc lập | [v1.1 rule 6] |
| Phân vân giữa hai mức | Chọn mức thấp hơn, ghi cả hai | [v1.1 rule 7] |
| Quá khứ hoặc kết quả sau đó | Chấm theo chữ trong bài, không tra giá hoặc tin về sau | [v1.1 rule 1 và 9] |

## 6. Bảng tra nhanh

```
1. Có liên quan đầu tư? Không -> other / 0 / 0.
2. event_label: đi từ bước 2 đến 10, dừng ở bước khớp đầu tiên.
3. sentiment: chiều tác động lên nhà đầu tư của chủ thể chính.
   - Phạt, bán ròng, giảm sàn, sập phiên -> âm.
   - Lãi, cổ tức bằng tiền, mua vào, hồi phục -> dương.
   - Tín hiệu hỗn hợp -> theo sự kiện đứng đầu tiêu đề.
   - Phân vân giữa hai mức -> mức thấp hơn.
4. fear: tìm cue trong bảng 4.2.
   - Không có cue -> 0.
   - Có cue: kiểm tra phủ định, đã giải quyết, đúng chủ thể (nhà đầu tư).
   - Chép cue nguyên văn vào notes; mức = mức của cue; phân vân -> thấp hơn.
5. Phạt, cưỡng chế, khởi tố, giảm mạnh, xả, dấu "?" -> KHÔNG phải cue.
6. Cảm thấy có fear mà không có cue -> chấm 0, ghi "torn 0/1: <cụm>".
```

| Tình huống thường gặp | event_label | sentiment | fear |
|---|---|---|---|
| Doanh nghiệp bị xử phạt hành chính | `regulation_legal` | −1 | 0 |
| Tự doanh, khối ngoại bán ròng | `fund_flow` | −1 | 0 |
| Cổ đông lớn mua một cổ phiếu | `corporate_action` | +1 | 0 |
| Chia cổ tức bằng tiền | `corporate_action` | +1 | 0 |
| Lãi ròng quý tăng, nêu thẳng | `corporate_earnings` | +1 | 0 |
| Bản tin tổng hợp, tin vắn | `market_commentary` | 0 | 0 |
| PR, giải thưởng, explainer | `other` | 0 | 0 |
| "Nhà đầu tư lo ngại bán tháo" | tùy chủ thể | −1 hoặc −2 | 2 đến 3 (có cue) |

## 7. Các điểm cần calibration trước vòng 2

Những điểm bên dưới là chỗ rubric v1.1 và hành vi rater ở vòng 1 chưa khớp; cần chốt trong buổi calibration 20 bài và ghi lại quyết định vào guide.

| # | Điểm cần chốt | Bằng chứng | Gợi ý xử lý [ĐX] |
|---|---|---|---|
| 1 | Bước 5 (trái phiếu, bất động sản) đứng trước bước 8 (một công ty) | Trái phiếu doanh nghiệp: rater từng chọn `real_estate_bond_credit`; "bất động sản" 0/7 | Bước 5 áp dụng khi **công cụ nợ hoặc thị trường bất động sản là chủ đề chính**, kể cả của một công ty; công ty mở rộng sang bất động sản -> bước 8 |
| 2 | "giải trình" với cơ quan quản lý | 2 bài sentiment −2 / −2: rater 1 chọn `corporate_action` cả hai bài; rater 2 chọn `regulation_legal` ở một bài và `market_commentary` ở bài kia | Theo bước 3: `regulation_legal`; fear 0 nếu không có cue |
| 3 | Đình chỉ giao dịch **một** cổ phiếu | 1 bài: fear 2/1, sentiment −2/−2 | `regulation_legal`; fear 0 nếu không có cue (lexicon mức 4 chỉ cho dừng giao dịch khẩn cấp toàn thị trường) |
| 4 | "lo ngại" (mức 2) và "bán tháo" (mức 3) bị chấm thấp hơn một bậc | n = 2 và 1 | Giữ nguyên mức của bảng 4.2; thu thêm bằng chứng ở vòng 2 |
| 5 | Báo cáo phái sinh hằng ngày | Ở 3/7 bài, một trong hai rater chọn `corporate_earnings` | Bước 9 (`market_commentary`); lưu ý các bài này là mô tả kỹ thuật, không có lợi nhuận công ty |
| 6 | Dịch bệnh là bối cảnh hay là sự kiện | "dịch kiểm soát tốt, cổ phiếu hàng không tăng mạnh": hai rater khác nhau | Bước 2 chỉ khi dịch bệnh **là** sự kiện; ở đây sự kiện là giá cổ phiếu -> `market_commentary` |
| 7 | +2 cho tăng trưởng lợi nhuận lớn | Hai rater bất đồng +1 vs +2 ở 8 bài | Dùng +1 theo rule 7 trừ khi cả hai cùng thấy +2 |

## Phụ lục A. Phương pháp và khả năng tái lập

- Dữ liệu: `data/pilot/pilot_annotation.csv`, `human1.csv`, `human2.csv` (đã làm sạch `id`; xem `DATA.md` về lỗi Excel làm hỏng `id` dài) và `data/news/*.jsonl`. Thư mục `data/pilot/` bị git-ignore nên chỉ chủ đồ án chạy lại được.
- Khớp keyword: biểu thức `(?<!\w)<cue>(?!\w)` trên văn bản NFC, chữ thường, ghép `title + " . " + summary`.
- Thống kê dùng: số bài chứa keyword; điểm TB theo từng rater; tỷ lệ cả hai rater cùng điều kiện (>= 1 hoặc cùng nhãn).
- Giới hạn: một tập 300 bài, hai rater, rubric v1.0; không có kiểm định thống kê cho từng keyword. Dùng bảng để định hướng calibration, **không** dùng để huấn luyện hoặc chấm tự động.

## Phụ lục B. Nhật ký thay đổi

| Phiên bản | Ngày | Thay đổi |
|---|---|---|
| v0.1 | 2026-11-21 | Bản đầu: bảng keyword theo thang, quy ước quan sát, phát hiện về độ phủ lexicon, danh sách calibration |
