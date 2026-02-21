# 가용 재고 (Available Stock) 설계 문서

> **Version:** 4.0 (2026-01-09)
> **Status:** Multi-Brand Production Ready (Noir, Queens Selection, Verda, Zizae, Dana&Peta)
> **변경사항:** 동적 시즌 계산, 쿼리 날짜 검증, 차수별 예측 로직 추가

## 1. 문제 정의

### 1.1 현재 문제점
```
현재: reorder_qty = forecast - physical_stock
문제1: 어제 발주한 상품이 오늘도 리오더에 뜸 (이중 발주)
문제2: 예약 배송 물량을 고려하지 않음 (재고 부족)
```

### 1.2 해결 방향
```
개선: reorder_qty = forecast - available_stock
where: available_stock = physical_stock + in_transit - reserved
```

### 1.3 핵심 원칙: 과재고 방지
**과재고는 리오더에서 가장 위험한 상황**

Auto-Expire 방식의 문제:
```
시나리오: 발주 100개, 14일 후에도 미입고
- Auto-Expire: 미수령=0 처리 → "재고 부족"으로 판단 → 100개 추가 발주
- 결과: 실제 입고 시 200개 도착 → 과재고
```

**해결:** 명시적 입고 확인 (P열 = 완료) 기반 추적

---

## 1.4 멀티 브랜드 지원

| 브랜드 | 코드 | Master 테이블 | SKU 수 | 상태 |
|--------|------|---------------|--------|------|
| **노어 (Noir)** | NR | noor_master | 2,528 | Production |
| **퀸즈셀렉션** | QU | queens_master | 8 | Production |
| **베르다 (Verda)** | VD | verda_master | 312 | Production |
| **지재 (Zizae)** | ZE | zizae_master | TBD | Production |
| **다나앤페타 (Dana&Peta)** | DN | dana_master | TBD | Production |

모든 브랜드에서 동일한 가용 재고 공식 적용:
```
available_stock = physical_stock + in_transit - reserved
```

---

## 2. 데이터 소스

### 2.1 물리적 재고 (Physical Stock)
| 항목 | 값 |
|------|-----|
| 테이블 | `damoa-lake.logistics_owned.stockDetail_raw` |
| 키 | `itemCode` (= product_item_code) |
| 재고 | `avaliableStock` (오타 주의) |
| 브랜드 필터 | `Brand = 'NR'/'QU'/'VD'/'ZE'/'DN'` |
| 업데이트 주기 | **실시간** |

**스키마 (브랜드별 필터):**
```sql
SELECT
  itemCode,           -- SKU 코드 (예: NR25WCA003LVFFF)
  avaliableStock,     -- 현재 물리적 재고
  Brand,              -- 브랜드 코드 (NR, QU, VD, ZE, DN)
  sales_status        -- 판매 상태
FROM `damoa-lake.logistics_owned.stockDetail_raw`
WHERE Brand = '{BRAND_CODE}'  -- NR, QU, VD, ZE, DN
```

### 2.1.1 리오더 가능 품번 필터 (브랜드별 Master 테이블)

| 브랜드 | Master 테이블 | 키 |
|--------|---------------|-----|
| Noir | `damoa-lake.pb2_owned.noor_master` | barcode |
| Queens | `damoa-lake.pb2_owned.queens_master` | barcode |
| Verda | `damoa-lake.pb2_owned.verda_master` | barcode |
| Zizae | `damoa-lake.pb1_owned.zizae_master` | barcode |
| Dana&Peta | `damoa-lake.pb1_owned.dana_master` | barcode |

| 항목 | 값 |
|------|-----|
| 타입 | External Table (Google Sheets 연동) |
| 용도 | 리오더 가능한 품번 목록 관리 |
| **추가 필드** | `vendor_category` (동대문, 해외 등) |

**필터 적용 (공통 패턴):**
```sql
-- 리오더 가능 품번 목록 ({brand}_master 기준) + vendor_category 포함
reorderable_products AS (
  SELECT DISTINCT
    barcode AS product_item_code,
    vendor_category
  FROM `damoa-lake.pb2_owned.{brand}_master`  -- noor_master, queens_master, verda_master
  WHERE barcode IS NOT NULL AND barcode != ''
)

-- stockDetail_raw에서 noor_master에 있는 품번만 추출 (JOIN으로 vendor_category 가져옴)
FROM `damoa-lake.logistics_owned.stockDetail_raw` sd
JOIN reorderable_products rp ON sd.itemCode = rp.product_item_code
WHERE sd.Brand = BRAND_CODE
```

**목적:**
- noor_master에 등록된 품번만 리오더 대상으로 제한
- 단종/미관리 품번의 불필요한 리오더 방지
- **vendor_category를 통해 발주처 구분** (동대문, 해외 등)

### 2.2 미수령발주량 (In-Transit)
| 항목 | 값 |
|------|-----|
| 소스 | Google Sheets 발주 로그 |
| 시트 | `발주(리오더)_동대문` |
| 스프레드시트 ID | `1q0CsxQXe3W-Y6xDcgNY-uT1oBDH_IZgrK-Gm7uTl8YE` |

**컬럼 구조:**
| 열 | 컬럼명 | 용도 |
|----|--------|------|
| A | 브랜드 | 필터 ('노어') |
| C | 최초 발주일 | 발주 시점 |
| D | 바코드 | SKU 코드 (= itemCode) |
| E | 수량 | 발주 수량 |
| P | 완료 | **입고 확인 (TRUE/FALSE)** |

**미수령발주량 계산:**
```python
미수령발주량 = SUM(수량)
WHERE 브랜드 = '노어'
  AND 바코드 = 해당SKU
  AND 완료(P열) != TRUE   # 핵심: 입고 완료되지 않은 건만
```

### 2.3 미발송수량 (Reserved) - Phase 2

| 항목 | 값 |
|------|-----|
| 소스 | BigQuery |
| 테이블 | `damoa-lake.ms_order.order_line` + `order_shipment_estimate` |
| 상태 | **분석 완료, 구현 대기** |

#### 2.3.1 데이터 소스 분석

**주요 테이블:**
- `damoa-lake.ms_order.order_line`: 주문 라인 정보
- `damoa-lake.ms_order.order_shipment_estimate`: 예상 배송일 정보

**키 컬럼:**
| 컬럼 | 테이블 | 설명 |
|------|--------|------|
| `product_item_id` | order_line | SKU ID (product_item 테이블과 조인 필요) |
| `quantity` | order_line | 주문 수량 |
| `delivery_state` | order_line | 배송 상태 |
| `purchase_state` | order_line | 결제 상태 |
| `estimate_shipment_at` | order_shipment_estimate | 예상 배송일 |

#### 2.3.2 Reserved 정의 (v2.3 재정립)

**핵심 변경: "예약 배송"만 Reserved로 카운트**

```
┌─────────────────────────────────────────────────────────────────┐
│  Reserved 정의 (v2.3)                                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  기존 정의 (v2.2):                                              │
│    - delivery_state = 'WAIT' or 'PREPARING' 인 모든 주문        │
│    - 문제: 대부분 1-2일 내 출고됨 → 굳이 reserved 필요?         │
│                                                                 │
│  새로운 정의 (v2.3):                                            │
│    - estimate_shipment_at >= TODAY + 3일 인 주문만              │
│    - 이유: 일반 주문은 물류 처리 시간일 뿐, 재고 점유 아님      │
│    - 3일+ 후 출고 예정 = 진짜 "예약 배송" = 재고 점유           │
│                                                                 │
│  비즈니스 근거:                                                 │
│    - 물류 센터: 1-2일 처리 시간 필요 (주말 제외하면 더 길 수 있음)│
│    - 일반 주문: WAIT/PREPARING 상태는 곧 출고 → 가용재고 무관   │
│    - 예약 배송: 3일+ 후 출고 → 재고를 묶어두는 진짜 예약        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 2.3.3 미발송수량 쿼리 (v2.3)

**권장 쿼리 (예약 배송만 = 3일+ 후 출고):**

```sql
-- 예약 배송 상품 조회 (노어 브랜드)
-- ※ 3일+ 후 출고 예정인 주문만 Reserved로 카운트
-- ※ delivery_state 필터 없음 (날짜 기준으로 판단)
SELECT
    pi.product_item_code AS mall_product_code,
    SUM(ol.quantity) AS reserved_qty
FROM `damoa-lake.ms_order.order_line` ol
JOIN `damoa-lake.ms_product.product_item` pi
    ON ol.product_item_id = pi.id
JOIN `damoa-lake.ms_order.order_shipment_estimate` ose
    ON ol.id = ose.order_line_id
WHERE
    -- 노어 브랜드만
    pi.product_item_code LIKE 'NR%'

    -- 결제 완료된 주문만
    AND ol.purchase_state = 'PAID'

    -- 3일+ 후 출고 예정 (진짜 예약 배송)
    AND ose.estimate_shipment_at >= CURRENT_DATE() + 3

GROUP BY pi.product_item_code
```

**주의사항 (AI 토론 필요):**

| 이슈 | 설명 | 상태 |
|------|------|------|
| **JOIN 중복** | `order_shipment_estimate`가 order_line당 여러 행 가능 | 🔴 확인 필요 |
| **NULL 처리** | `estimate_shipment_at`이 NULL인 경우 처리 | 🔴 확인 필요 |
| **INNER JOIN** | LEFT → INNER로 변경 (예약 정보 없으면 reserved 아님) | 🟡 검토 필요 |

#### 2.3.4 AI 검토 결과 (v2.3 Codex + Gemini)

**v2.3 AI 토론 결과 요약:**

| 질문 | Codex | Gemini | 결론 |
|------|-------|--------|------|
| **delivery_state 필터** | ✅ SHIPPED/DELIVERED 제외 필요 | ✅ 제외 필수 (이중 차감 방지) | ✅ **추가 필요** |
| **3일 threshold** | 🟡 4-5일 또는 영업일 고려 권장 | ✅ 3일 적절 (과재고 방지) | 🟡 **3일 유지, 모니터링** |
| **ROW_NUMBER dedupe** | ✅ 올바른 접근 | ✅ 표준적 방법 | ✅ **현행 유지** |
| **NULL 처리** | 🟡 제외 또는 보수적 기본값 | 🟡 LEFT JOIN + COALESCE 권장 | 🟡 **현행 유지 (INNER JOIN)** |
| **v2.2 vs v2.3** | ✅ v2.3가 과재고 방지에 유리 | ✅ v2.3가 과재고 방지에 유리 | ✅ **v2.3 채택** |

**Codex 상세 피드백:**

```
1. Delivery state: Yes, exclude SHIPPED/DELIVERED (and any canceled/void)
   to avoid double-counting already-fulfilled lines.

2. 3-day threshold: Risky on long weekends/holidays; consider a business-day
   offset or a slightly longer buffer (e.g., 4-5 calendar days or 2-3 business days).

3. ROW_NUMBER: Correct to pick latest estimate per line; ensure updated_at
   reliably reflects most recent estimate event.

4. NULL estimates: Currently excluded by the join + date filter; decide whether
   to treat NULL as "soon" (exclude) or "unknown" (include with default far date).
   For overstock prevention, safer to exclude NULLs from reservation.

5. v2.2 vs v2.3: v2.3 (3+ days only) is safer for overstock prevention because
   it frees near-term orders from reservation.
```

**Gemini 상세 피드백:**

```
1. Delivery State Filter: YES, add it.
   - Relying solely on purchase_state = 'PAID' is risky
   - If order is shipped but remains 'PAID', you'll double-count
   - Fix: AND ol.delivery_state NOT IN ('SHIPPED', 'DELIVERED', 'CANCELLED')

2. 3-Day Threshold: YES, appropriate.
   - Inventory for orders shipping in 48-72 hours is likely in "picking" process
   - Including them would trigger "panic buying" for demand already resolving

3. Deduplication (ROW_NUMBER): Correct.
   - Standard, reliable way to get the latest estimate

4. NULL Handling: Current Risk is HIGH.
   - INNER JOIN drops order lines without estimate (treated as 0 reserved)
   - Recommendation: If missing = "Standard Shipping", current behavior OK
   - Alternative: LEFT JOIN + COALESCE for explicit handling

5. v2.2 vs v2.3: v2.3 is safer for preventing overstock.
   - v2.2: High Reserved → Low Available → Early Reorder → Overstock Risk
   - v2.3: Lower Reserved → Higher Available → Later Reorder → Lower Overstock Risk
```

**최종 결정사항:**

```
┌─────────────────────────────────────────────────────────────────┐
│  v2.3 쿼리 최종 설계                                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. delivery_state 필터 추가 (AI 합의)                          │
│     - SHIPPED, DELIVERED, CANCELLED 제외                        │
│     - 이유: 이미 출고된 건 재고에서 빠짐 → 이중 차감 방지       │
│                                                                 │
│  2. 3일 threshold 유지                                          │
│     - Codex: 4-5일 권장 / Gemini: 3일 OK                        │
│     - 결정: 3일로 시작, 운영 모니터링 후 조정                   │
│                                                                 │
│  3. ROW_NUMBER dedupe 유지                                      │
│     - 두 AI 모두 현재 접근법 승인                               │
│                                                                 │
│  4. NULL 처리 (INNER JOIN 유지)                                 │
│     - estimate 없는 주문 = 일반 배송 = reserved 아님            │
│     - 과재고 방지 관점에서 안전                                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**최종 권장 쿼리 (v2.3 + AI 피드백 반영):**

```sql
-- 예약 배송 상품 조회 (노어 브랜드)
-- v2.3: 3일+ 후 출고 예정인 주문만 Reserved로 카운트
-- AI 피드백 반영: delivery_state 필터 추가, ROW_NUMBER dedupe
WITH latest_est AS (
  SELECT order_line_id, estimate_shipment_at
  FROM (
    SELECT order_line_id, estimate_shipment_at,
           ROW_NUMBER() OVER (PARTITION BY order_line_id
                              ORDER BY updated_at DESC, created_at DESC) AS rn
    FROM `damoa-lake.ms_order.order_shipment_estimate`
  )
  WHERE rn = 1
)
SELECT
  pi.product_item_code AS mall_product_code,
  SUM(ol.quantity) AS reserved_qty
FROM `damoa-lake.ms_order.order_line` ol
JOIN `damoa-lake.ms_product.product_item` pi
  ON ol.product_item_id = pi.id
JOIN latest_est ose ON ol.id = ose.order_line_id
WHERE
    -- 노어 브랜드만
    pi.product_item_code LIKE 'NR%'

    -- 결제 완료된 주문만
    AND ol.purchase_state = 'PAID'

    -- 이미 출고된 건 제외 (AI 합의: 이중 차감 방지)
    AND ol.delivery_state NOT IN ('SHIPPED', 'DELIVERED', 'CANCELLED')

    -- 3일+ 후 출고 예정 (예약 배송만)
    AND ose.estimate_shipment_at >= CURRENT_DATE() + 3

GROUP BY pi.product_item_code;
```

**쿼리 설명:**

| 조건 | 설명 | 근거 |
|------|------|------|
| `pi.product_item_code LIKE 'NR%'` | 노어 브랜드 필터 | 비즈니스 요구 |
| `ol.purchase_state = 'PAID'` | 결제 완료 건만 | 확정된 주문만 |
| `ol.delivery_state NOT IN (...)` | 출고 완료 건 제외 | AI 합의: 이중 차감 방지 |
| `ose.estimate_shipment_at >= TODAY+3` | 3일+ 후 출고 예정 | 예약 배송만 = 재고 점유 |
| `ROW_NUMBER() ... rn = 1` | 최신 estimate만 | 중복 카운팅 방지 |

#### 2.3.5 설계 고려사항 (v2.3 업데이트)

```
┌─────────────────────────────────────────────────────────────────┐
│  Reserved 계산 시 고려사항 (v2.3)                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. 결제 상태 필터 (purchase_state)                             │
│     - PAID: 결제 완료 → 포함                                    │
│     - WAIT: 결제 대기 → 제외 (확정 안 됨)                       │
│     - CANCEL: 취소 → 제외                                       │
│                                                                 │
│  2. 배송 상태 필터 (delivery_state)                             │
│     ※ v2.3에서 제거 (날짜 기준만 사용)                          │
│     ※ 단, SHIPPED/DELIVERED 제외 여부 AI 검토 필요             │
│                                                                 │
│  3. 예약 배송 기준 (v2.3 핵심)                                  │
│     - estimate_shipment_at >= TODAY + 3일                       │
│     - 3일 이내 출고 예정 = 일반 주문 (무시)                     │
│     - 3일+ 후 출고 예정 = 예약 배송 (Reserved)                  │
│                                                                 │
│  4. 비즈니스 근거                                               │
│     - 일반 주문: 1-2일 내 출고 → 재고 점유 아님                 │
│     - 예약 배송: 3일+ 후 출고 → 재고를 묶어둠                   │
│     - 주말/연휴 고려: 영업일 기준으로 하면 더 정확              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

#### 2.3.6 Reserved 포함 여부 결정 흐름 (v2.3)

```
                    ┌─────────────────┐
                    │  주문 생성      │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ purchase_state? │
                    └────────┬────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
     ┌────▼────┐        ┌────▼────┐        ┌────▼────┐
     │  WAIT   │        │  PAID   │        │ CANCEL  │
     │ (대기)  │        │ (완료)  │        │ (취소)  │
     └────┬────┘        └────┬────┘        └────┬────┘
          │                  │                  │
          ▼                  ▼                  ▼
     ❌ 미포함               │              ❌ 미포함
                             │
                    ┌────────▼────────┐
                    │ estimate_shipment_at │
                    │ >= TODAY + 3일? │
                    └────────┬────────┘
                             │
          ┌──────────────────┴──────────────────┐
          │                                     │
     ┌────▼────┐                           ┌────▼────┐
     │  YES    │                           │   NO    │
     │ (3일+)  │                           │ (<3일)  │
     └────┬────┘                           └────┬────┘
          │                                     │
          ▼                                     ▼
     ✅ Reserved                           ❌ 미포함
     (예약 배송)                           (일반 주문)
```

**v2.2 대비 변경점:**
- delivery_state 필터 제거 → estimate_shipment_at 날짜 기준으로 변경
- 3일+ 후 출고 예정만 Reserved로 인식

---

## 3. 가용 재고 공식

### 3.1 전체 공식 (목표)
```
available_stock = physical_stock + 미수령발주량 - 미발송수량

where:
  physical_stock  = 현재 물리적 재고 (창고에 있는 양)
  미수령발주량    = 발주했지만 아직 입고 안 된 양 (들어올 물량) [+]
  미발송수량      = 주문 확정됐지만 아직 출고 안 된 양 (나갈 물량) [-]
```

**개념 정리:**
```
┌─────────────────────────────────────────────────────────┐
│                    가용 재고 구성                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│   현재 재고 (physical)     : 지금 창고에 있는 양        │
│        (+)                                              │
│   미수령발주량 (in_transit): 발주 → 입고 대기 중        │
│        (-)                                              │
│   미발송수량 (reserved)    : 주문 확정 → 출고 대기 중   │
│        (=)                                              │
│   가용 재고 (available)    : 실제 리오더에 쓸 수 있는 양│
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 3.2 Phase 1 (현재 구현)
```
available_stock = physical_stock + 미수령발주량

where:
  physical_stock = stockDetail_raw.avaliableStock
  미수령발주량 = SUM(sheets.수량) WHERE 완료(P열) != TRUE
```

### 3.3 Phase 2 (미발송수량 연동 후) - v2.4 확정
```
available_stock = physical_stock + 미수령발주량 - 미발송수량

where:
  physical_stock = BigQuery (stockDetail_raw)
  미수령발주량   = Google Sheets (P열 != TRUE)
  미발송수량     = BigQuery (3일+ 예약 배송만)
```

**v2.4 Reserved 정의:**
```sql
-- 3일+ 후 출고 예정인 예약 배송만 Reserved로 카운트
WHERE ol.purchase_state = 'PAID'
  AND ol.delivery_state NOT IN ('SHIPPED', 'DELIVERED', 'CANCELLED')
  AND ose.estimate_shipment_at >= CURRENT_DATE() + 3
```

### 3.4 최종 리오더 공식
```python
추천발주량 = MAX(0, forecast - available_stock)
리오더수량 = CEIL(추천발주량 / MOQ) * MOQ
```

---

## 4. 파라미터

| 파라미터 | 값 | 설명 |
|----------|-----|------|
| MOQ | 5 | 최소 주문 단위 |
| BRAND_CODE | 'NR' | 노어 브랜드 코드 |
| BRAND_NAME | '노어' | 시트 필터용 |

**삭제된 파라미터:**
- ~~LEAD_TIME_DAYS~~ (Auto-Expire 폐기로 불필요)

---

## 5. 구현 아키텍처

### 5.1 Phase 1 (현재)
```
┌─────────────────────┐     ┌─────────────────────┐
│  BigQuery           │     │  Google Sheets      │
│  stockDetail_raw    │     │  발주(리오더)_동대문 │
│  (실시간 재고)      │     │  (발주/입고 기록)   │
└─────────┬───────────┘     └─────────┬───────────┘
          │                           │
          │ itemCode                  │ 바코드, 수량, 완료(P열)
          ▼                           ▼
┌─────────────────────────────────────────────────┐
│              Python 통합 스크립트                │
│                                                 │
│  1. BigQuery: physical_stock 조회               │
│  2. Sheets: 미수령발주량 계산 (완료 != TRUE)    │
│  3. available_stock = physical + 미수령발주량   │
│  4. 추천발주량 = forecast - available_stock     │
└─────────────────────────────────────────────────┘
```

### 5.2 Phase 2 (Reserved 포함) - v2.6 확정 (Google Apps Script 기반)

```
┌───────────────────────────────────────────────────────────────────────────────┐
│  Step 1: BigQuery 쿼리 실행 (noir_reorder_v1.1.sql)                           │
│  → Google Sheets 데이터 커넥터로 자동 업데이트 (매일 오전 10시)               │
├───────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  입력:                                                                        │
│    - stockDetail_raw (실시간 재고)                                            │
│    - order_line + order_shipment_estimate (예약 배송)                         │
│    - product_funnel_daily (판매 데이터)                                       │
│                                                                               │
│  출력 (raw_reorder 탭):                                                       │
│    - mall_product_code                                                        │
│    - physical_stock                                                           │
│    - reserved_qty (3일+ 예약 배송만)                                          │
│    - normal_forecast (차수별 14d/21d Monte Carlo P50)                         │
│    - 메타데이터 (SPV, 카테고리, reorder_order 등)                             │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌───────────────────────────────────────────────────────────────────────────────┐
│  Step 2: Google Sheets 내 수식 계산                                           │
├───────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  in_transit_qty 계산 (SUMIFS 수식):                                           │
│    =SUMIFS('발주(리오더)_동대문'!$E:$E,                                       │
│            '발주(리오더)_동대문'!$D:$D, A2,                                   │
│            '발주(리오더)_동대문'!$P:$P, "<>TRUE")                             │
│                                                                               │
│  available_stock 계산:                                                        │
│    = physical_stock + in_transit_qty - reserved_qty                           │
│                                                                               │
│  reorder_qty 계산 (5장 단위 반올림):                                          │
│    = MROUND(MAX(0, normal_forecast - available_stock), 5)                     │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌───────────────────────────────────────────────────────────────────────────────┐
│  Step 3: Google Apps Script (자동화/후처리)                                   │
├───────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  - 리오더 결과 필터링 (reorder_qty > 0인 항목만)                              │
│  - 발주 로그 자동 기록                                                        │
│  - 알림/리포트 생성                                                           │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘
```

**핵심 포인트:**
- BigQuery → Sheets 데이터 커넥터로 자동 동기화 (매일 10시)
- `in_transit_qty`는 Sheets 내 SUMIFS 수식으로 계산
- `available_stock`, `reorder_qty`도 Sheets 수식으로 계산
- Google Apps Script는 자동화/후처리에만 사용 (Python 불필요)

---

## 6. 로그 시트 구조

### 6.1 시트 정보
| 항목 | 값 |
|------|-----|
| 스프레드시트 ID | `1q0CsxQXe3W-Y6xDcgNY-uT1oBDH_IZgrK-Gm7uTl8YE` |
| 시트명 | `reorder_archive` |

### 6.2 컬럼 구조
| 열 | 컬럼명 | 설명 |
|----|--------|------|
| A | 날짜 | 리오더 실행 일자 |
| B | 품번 | SKU 코드 (itemCode) |
| C | 현재재고 | physical_stock (stockDetail_raw) |
| D | 미수령발주량 | 발주 완료 전 물량 (P열 != TRUE) |
| E | 미발송수량 | 출고 대기 물량 (Phase 2) |
| F | 가용재고 | 현재재고 + 미수령발주량 - 미발송수량 |
| G | forecast | 예측 판매량 |
| H | 추천발주량 | MAX(0, forecast - 가용재고) |

### 6.3 샘플 데이터
```
| 날짜       | 품번            | 현재재고 | 미수령발주량 | 미발송수량 | 가용재고 | forecast | 추천발주량 |
|------------|-----------------|---------|-------------|-----------|---------|----------|-----------|
| 2025-12-09 | NR25WCA001NVFFF | 10      | 5           | 3         | 12      | 20       | 10        |
| 2025-12-09 | NR25WNT005IVFFF | 0       | 5           | 0         | 5       | 15       | 10        |
```

---

## 7. 미수령발주량 추적 방식

### 7.1 ~~Auto-Expire 방식~~ (폐기)
```
❌ 문제: 14일 후 자동 만료 → 실제 미입고인데 "입고된 것으로 간주" → 과재고
```

### 7.2 명시적 입고 확인 방식 (채택)
```
✅ 해결: P열(완료) = TRUE 일 때만 입고로 인정
- 담당자가 실제 입고 확인 후 P열을 TRUE로 변경
- 입고 확인 전까지 미수령발주량에 계속 포함
- 과재고 리스크 최소화
```

**장점:**
- 과재고 방지: 실제 입고 전까지 미수령으로 계속 인식
- 명확한 상태 관리: TRUE/FALSE로 입고 여부 명확
- 기존 시트 활용: 추가 테이블 불필요

**운영:**
- 입고 시 담당자가 P열을 TRUE로 변경
- 리오더 시스템은 P열 != TRUE인 건만 미수령으로 계산

---

## 8. 현재 데이터 상태 (2025-12-09)

### 8.1 노어 재고 현황
- 전체 SKU: 2,528개
- 테이블: `stockDetail_raw` (실시간)

### 8.2 미수령발주량 현황 (P열 != TRUE)
- **미입고 품번:** 10개
- **총 미입고 수량:** 34개

| SKU | 미입고 수량 |
|-----|-----------|
| NR25WCA001NVFFF | 5 |
| NR25WNT005IVFFF | 5 |
| NR25WPT011GYFFF | 3 |
| NR25WPT011BRFFF | 3 |
| NR25WPT011BKFFF | 3 |
| NR25WPT012BKFFF | 3 |
| NR25WPT012CGFFF | 3 |
| NR25WPT016BR0XL | 3 |
| NR25WNT001CGFFF | 3 |
| NR25WCA003LVFFF | 3 |

---

## 9. 다음 단계

### Phase 1: MVP ✅ 완료
- [x] 실재고 테이블 연결 확인 (`stockDetail_raw`)
- [x] 발주 로그 시트 연결 확인 (`발주(리오더)_동대문`)
- [x] 미수령발주량 로직 확정 (P열 기반)

### Phase 2: 예약 배송 + BigQuery 쿼리 ✅ 완료
- [x] 예약 배송 데이터 소스 확인 (`order_line` + `order_shipment_estimate`)
- [x] reserved_qty 로직 설계 (3일+ 예약 배송만)
- [x] AI 토론 완료 (Codex + Gemini)
- [x] noir_reorder_v1.1.sql 작성 및 드라이런 검증
- [x] BigQuery 데이터 커넥터 설정 (raw_reorder 탭, 매일 10시)

### Phase 3: Sheets 수식 + Google Apps Script ✅ 완료
- [x] 시트 구조 설계 (raw_reorder + 발주(리오더)_동대문)
- [x] 계산 수식 정의:
  - `in_transit_qty`: SUMIFS (P열 != TRUE)
  - `available_stock`: physical + in_transit - reserved
  - `reorder_qty`: MROUND(MAX(0, forecast - available), 5)
- [x] Google Apps Script 작성 (`noir_reorder_apps_script.js`):
  - [x] 리오더 결과 필터링 (X열 reorder_qty > 0)
  - [x] 발주 탭 자동 기입 (D열 기준 마지막 데이터 행 다음)
  - [x] S2 셀 오늘 날짜 업데이트
  - [x] runSync() 기존 함수 실행
  - [x] reorder_archive 탭 아카이빙 (A열 기준 마지막 행 다음)
  - [x] Slack 알림 발송 (그룹/개인 멘션 포함)

### Phase 4: 고도화 (향후)
- [ ] 장기 미입고 알림 (예: 14일 이상)
- [ ] 대시보드 구축

---

## 10. 참고: AI 분석 결과

### 10.1 Codex 1차 분석
1. 타이밍 기준 명확화 필요
2. In-transit 중복 집계 방지 (입고 매칭)
3. 상태 전이 규칙 정의

### 10.2 Gemini 분석
1. 재고 테이블 신선도 확인 (해결됨: 실시간 테이블 사용)
2. Reserved는 전체 차감 권장 (리드타임 무관)
3. ~~Auto-Expire로 간단한 MVP 가능~~ → 재검토 필요

### 10.3 Codex 2차 분석 (Auto-Expire 재검토)
1. **Auto-Expire 위험:** 과재고 리스크 최대
2. **명시적 로그 권장:** 실제 미수령 잔량 보존 → 과재고 방지
3. **과재고 시뮬레이션:** 명시적 방식이 Auto-Expire보다 안전

### 10.4 최종 결정
- ~~Auto-Expire 방식~~ → **폐기**
- **P열(완료) 기반 명시적 추적** → **채택**
- 예약 배송은 데이터 확보 후 Phase 2에서 추가

---

## 11. Change Log

| 날짜 | 버전 | 변경사항 |
|------|------|----------|
| 2026-01-09 | 4.0 | 동적 시즌 계산, 쿼리 날짜 검증, 차수별 예측 로직, Zizae/Dana&Peta 추가 |
| 2026-01-08 | 3.1 | Price Down 상품 제외 로직 추가 |
| 2025-12-10 | 3.0 | 멀티 브랜드 확장 (Queens Selection, Verda 추가) |
| 2025-12-10 | 2.10 | **평일 실행 제한:** 월~금에만 실행, 주말(토/일) 스킵 로직 추가 |
| 2025-12-10 | 2.9 | **프로세스 단순화:** vendor_category 추가, 5.2 리오더 내역 탭 사용, 동대문 직접 기입/Sync/S2 제거 (7단계→4단계) |
| 2025-12-10 | 2.8 | noor_master 테이블 필터 추가: 리오더 가능 품번만 대상으로 쿼리 |
| 2025-12-10 | 2.7 | Google Apps Script 구현 완료: 발주 탭 기입, 아카이브, Slack 알림, 테스트 함수 |
| 2025-12-10 | 2.6 | 아키텍처 변경: Python → Google Apps Script, Sheets 내 수식 기반 계산으로 단순화 |
| 2025-12-10 | 2.5 | 구현 아키텍처 확정: BigQuery(forecast+reserved) → Sheets(in_transit) → Python(조인) |
| 2025-12-10 | 2.4 | AI 토론 완료 (Codex + Gemini), delivery_state 필터 추가, 최종 쿼리 확정 |
| 2025-12-10 | 2.3 | Reserved 정의 재정립: 예약 배송(3일+ 후 출고)만 포함 |
| 2025-12-10 | 2.2 | Reserved 쿼리 AI 검토 완료 (Codex), JOIN 중복 이슈 해결 |
| 2025-12-10 | 2.1 | Reserved 데이터 소스 분석 추가 (order_line + order_shipment_estimate) |
| 2025-12-09 | 2.0 | Auto-Expire 폐기, P열 기반 명시적 추적 채택 |
| 2025-12-09 | 1.0 | 초기 문서 작성 |

---

## 12. 시트 구조 상세 (v2.6)

### 12.1 스프레드시트 정보
| 항목 | 값 |
|------|-----|
| 스프레드시트 ID | `1q0CsxQXe3W-Y6xDcgNY-uT1oBDH_IZgrK-Gm7uTl8YE` |
| URL | https://docs.google.com/spreadsheets/d/1q0CsxQXe3W-Y6xDcgNY-uT1oBDH_IZgrK-Gm7uTl8YE |

### 12.2 탭 구조

#### 12.2.1 raw_reorder (gid=1776410396)
**역할:** BigQuery 데이터 커넥터 출력 (매일 10시 자동 업데이트)

| 컬럼 | 열 | 타입 | 설명 |
|------|-----|------|------|
| mall_product_code | A | STRING | SKU 코드 (NR...) |
| **vendor_category** | **B** | STRING | **발주처 구분 (동대문, 해외 등)** ← [NEW v2.9] |
| base_category_name | C | STRING | 카테고리 (예: 바지/긴바지) |
| physical_stock | D | INT | 현재 물리적 재고 |
| reserved_qty | E | INT | 예약 배송 수량 (3일+ 후 출고) |
| product_type | F | STRING | 신상품/기존상품 |
| ... | ... | ... | ... |
| forecast_days | Q | INT | 예측 기간 (14일/21일, 차수별) |
| forecast_level | R | STRING | 예측 방법 (Statistical/Heuristic) |
| normal_forecast | S | INT | 차수별 예측 (14d/21d Monte Carlo P50) ← **사용** |
| in_transit_qty | W | INT | 미수령발주량 (Sheets 수식) |
| available_stock | X | INT | 가용재고 (Sheets 수식) |
| reorder_qty | Y | INT | 리오더 추천 수량 (Sheets 수식) |

**※ v2.9 변경사항:** vendor_category 컬럼 추가로 모든 컬럼이 한 칸씩 밀림 (X열 → Y열)

#### 12.2.2 발주(리오더)_동대문 (gid=1291961194)
**역할:** 발주 로그 및 입고 추적 (미수령발주량 SUMIFS 참조용)

| 열 | 컬럼명 | 용도 |
|----|--------|------|
| A | 브랜드 | 필터 ('노어') |
| D | 바코드 | SKU 코드 (mall_product_code와 매칭) |
| E | 수량 | 발주 수량 |
| P | 완료 | 입고 확인 (TRUE = 입고완료, 빈값/FALSE = 미입고) |

**※ v2.9 변경:** Apps Script에서 이 탭에 직접 기입하지 않음 → 5.2 리오더 내역 사용

#### 12.2.3 5.2 리오더 내역 [NEW v2.9]
**역할:** 리오더 실행 기록 (전체 브랜드 통합)

| 열 | 컬럼명 | 용도 |
|----|--------|------|
| A | 날짜 | 리오더 실행 일자 (yyyy-MM-dd) |
| C | 바코드 | SKU 코드 (품번) |
| AA | 수량 | 리오더 추천 수량 |

#### 12.2.4 reorder_archive
**역할:** 리오더 실행 전체 데이터 아카이브

| 컬럼 수 | 구성 |
|---------|------|
| 26 | 실행일자 + raw_reorder A~Y (25개 컬럼, vendor_category 포함) |

### 12.3 계산 수식

#### in_transit_qty (미수령발주량)
```
=SUMIFS('발주(리오더)_동대문'!$E:$E,
        '발주(리오더)_동대문'!$D:$D, A2,
        '발주(리오더)_동대문'!$P:$P, "<>TRUE")
```

#### available_stock (가용재고)
```
= physical_stock + in_transit_qty - reserved_qty
```

#### reorder_qty (리오더 수량, 5장 단위)
```
= MROUND(MAX(0, normal_forecast - available_stock), 5)
```

### 12.4 Forecast 선택 기준 (v1.2+ 차수별)

| 차수 | 예측 기간 | 예측 방법 | 수량 상한 |
|------|----------|----------|----------|
| **초도~4차** | 14일 | Monte Carlo P50 | 10장 |
| **5차+** | 21일 | Monte Carlo P50 | 제한 없음 |

**핵심 원칙:** 과재고 방지 > 품절 방지 (차수별 점진적 확대)

---

## 13. Google Apps Script 상세 (v2.10)

### 13.1 스크립트 파일
| 항목 | 값 |
|------|-----|
| 파일명 | `noir_reorder_apps_script.js` |
| 위치 | `scripts/noir_reorder_apps_script.js` |
| 버전 | v1.6 |

### 13.1.1 실행 조건 [NEW v2.10]
| 조건 | 설명 |
|------|------|
| **실행 요일** | 월~금 (평일만) |
| **스킵 요일** | 토/일 (주말) |

```javascript
// 평일 체크 (0=일요일, 6=토요일)
var dayOfWeek = today.getDay();
if (dayOfWeek === 0 || dayOfWeek === 6) {
  Logger.log('[스킵] 주말에는 리오더 프로세스를 실행하지 않습니다.');
  return;
}
```

### 13.2 설정 (CONFIG)

```javascript
var CONFIG = {
  TIMEZONE: 'Asia/Seoul',
  SPREADSHEET_ID: '1q0CsxQXe3W-Y6xDcgNY-uT1oBDH_IZgrK-Gm7uTl8YE',

  // 탭 이름
  SHEET_RAW_REORDER: 'raw_reorder',
  SHEET_REORDER_LOG: '5.2 리오더 내역',  // [NEW v2.9]
  SHEET_ARCHIVE: 'reorder_archive',

  // 컬럼 인덱스 (0-based) - vendor_category 추가로 +1 밀림
  RAW_REORDER: {
    MALL_PRODUCT_CODE: 0,  // A열: 품번
    VENDOR_CATEGORY: 1,    // B열: vendor_category [NEW v2.9]
    REORDER_QTY: 24        // Y열: 리오더 추천 수량 (X→Y로 밀림)
  },

  // 5.2 리오더 내역 탭 컬럼 [NEW v2.9]
  REORDER_LOG_SHEET: {
    COL_A: 0,   // 날짜
    COL_C: 2,   // 바코드 (품번)
    COL_AA: 26  // 수량 (AA열 = 26번 인덱스)
  },

  // Slack 설정
  SLACK_BOT_TOKEN: '***',
  SLACK_CHANNEL_ID: 'C0ABHFXMLP5',
  SLACK_SUBTEAM_ID: 'S02675SMW3Z',
  SLACK_MENTION_USER_IDS: ['U09F2EE35RR', 'U09SDNSAC9H'],

  // 시트 URL
  SHEET_URL: 'https://docs.google.com/spreadsheets/d/.../edit?gid=1291961194#gid=1291961194'
};
```

### 13.3 주요 함수

| 함수명 | 설명 |
|--------|------|
| `runNoirReorderProcess()` | **메인 함수** - 전체 리오더 프로세스 실행 (4단계) |
| `getReorderItems(ss)` | raw_reorder에서 Y열 > 0인 항목 추출 |
| `appendToReorderLogSheet(ss, items, today)` | **[NEW v2.9]** 5.2 리오더 내역 탭에 기록 |
| `archiveReorderItems(ss, items, today)` | reorder_archive에 저장 (25컬럼, vendor_category 포함) |
| `postSlackNotification(ss, todayStr, items)` | Slack 알림 발송 (멘션 포함) |

**※ v2.9에서 삭제된 함수:**
- ~~`appendToOrderSheet()`~~ - 발주(리오더)_동대문 직접 기입 제거
- ~~`updateS2Cell()`~~ - S2 셀 업데이트 제거
- ~~`runSync()`~~ 호출 제거

### 13.4 테스트 함수

| 함수명 | 설명 |
|--------|------|
| `testGetReorderItems()` | 리오더 대상만 확인 (실제 기입 안함) |
| `testAppendToReorderLogSheet()` | 5.2 리오더 내역 탭 붙여넣기 테스트 (더미 2건) |
| `testArchiveReorderItems()` | 아카이브 탭 붙여넣기 테스트 (더미 1건) |
| `testSlackNotification()` | Slack 알림만 발송 테스트 |

### 13.5 실행 흐름 (v2.9 단순화)

```
runNoirReorderProcess() - 4단계로 단순화
    │
    ├── 1. getReorderItems()
    │       └── raw_reorder에서 Y열 > 0인 항목 추출
    │           (vendor_category 추가로 인덱스 밀림: X→Y)
    │
    ├── 2. appendToReorderLogSheet()  [NEW v2.9]
    │       └── 5.2 리오더 내역 탭에 전체 기록
    │           - A열: 날짜 (yyyy-MM-dd)
    │           - C열: 바코드 (품번)
    │           - AA열: 수량
    │
    ├── 3. archiveReorderItems()
    │       └── reorder_archive 탭에 저장
    │           - A열 기준 마지막 데이터 행 다음부터 기입
    │           - 날짜 + raw_reorder A~Y 컬럼 전체 (25개)
    │
    └── 4. postSlackNotification()
            └── Slack 채널에 알림 발송
                - 메인 메시지: 요약 + 시트 링크 + 멘션
                - 쓰레드: 상세 목록 (20개씩 분할)
```

**※ v2.9 변경사항:**
- 발주(리오더)_동대문 직접 기입 단계 제거
- S2 셀 업데이트 단계 제거
- runSync() 실행 단계 제거
- **7단계 → 4단계로 단순화**

### 13.6 Slack 알림 형식

**메인 메시지:**
```
노어 리오더 완료 (2025-12-10)
━━━━━━━━━━━━━━━━━━━━━━
리오더 요약
• 품번 수: 51개
• 총 수량: 350장
━━━━━━━━━━━━━━━━━━━━━━

시트 바로가기

@그룹 @개인1 @개인2
```

**쓰레드 (상세 목록):**
```
리오더 상세 (1~20)
• NR25WCA001NVFFF: 10장
• NR25WNT005IVFFF: 5장
...
```

### 13.7 트리거 설정

1. Apps Script 에디터 → 시계 아이콘 (트리거)
2. \+ 트리거 추가
3. 설정:
   - 실행할 함수: `runNoirReorderProcess`
   - 이벤트 소스: 시간 기반
   - 트리거 유형: 일 단위 타이머
   - 시간대: 오전 10시 ~ 11시 (BigQuery 동기화 후)

### 13.8 권한 설정 (appsscript.json)

```json
{
  "timeZone": "Asia/Seoul",
  "dependencies": {},
  "exceptionLogging": "STACKDRIVER",
  "runtimeVersion": "V8",
  "oauthScopes": [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/script.external_request"
  ]
}
```

---

## 14. 멀티 브랜드 배포

### 14.1 브랜드별 스프레드시트

| 브랜드 | Spreadsheet ID | Apps Script |
|--------|----------------|-------------|
| Noir | `1q0CsxQXe3W-Y6xDcgNY-uT1oBDH_IZgrK-Gm7uTl8YE` | noir_reorder_apps_script.js (v1.6) |
| Queens | `1CqbglHwEFrQzYUPA4oHyrv7doG3pAtE3tUs68wfaN4w` | queens_reorder_apps_script.js (v1.1) |
| Verda | `1Z8S1gl1bjc0YaQmIQU3_QhvpA8xxCEYHtedMuOM2wco` | verda_reorder_apps_script.js (v1.1) |
| Zizae | `1MDEQrx_o9YqFmwbiSTDYiG4cJ0tvBpXuUiIYXog15AI` | zizae_reorder_apps_script.js (v1.2) |
| Dana&Peta | TBD | danapeta_reorder_apps_script.js (v1.1) |

### 14.2 브랜드별 변경 파라미터

각 브랜드 쿼리에서 변경되는 파라미터:

```sql
-- 브랜드별 변경
DECLARE BRAND_CODE STRING DEFAULT '{NR/QU/VD/ZE/DN}';
DECLARE BRAND_PREFIX STRING DEFAULT '{NR%/QU%/VD%/ZE%/DN%}';

-- 공통 파라미터 (모든 브랜드 동일)
DECLARE START_DATE DATE DEFAULT '2023-01-01';
DECLARE RELATIVE_SPV_THRESHOLD_NEW FLOAT64 DEFAULT 0.30;
DECLARE RELATIVE_SPV_THRESHOLD_EXISTING FLOAT64 DEFAULT 0.65;
DECLARE HIGH_SPV_MULTIPLIER FLOAT64 DEFAULT 1.3;
DECLARE RESERVED_DAYS_THRESHOLD INT64 DEFAULT 3;
DECLARE HEURISTIC_DAYS INT64 DEFAULT 14;
```

### 14.3 Slack 설정 (공통)

모든 브랜드가 동일한 Slack 채널 사용:

| 설정 | 값 |
|------|-----|
| Channel ID | `C0ABHFXMLP5` |
| Subteam ID | `S02675SMW3Z` |
| Mention Users | `U09F2EE35RR`, `U09SDNSAC9H` |

---

## 15. 변경 이력

| 버전 | 날짜 | 변경사항 |
|------|------|----------|
| v4.0 | 2026-01-09 | 동적 시즌 계산, 쿼리 날짜 검증, 차수별 예측 로직, Zizae/Dana&Peta 추가 |
| v3.1 | 2026-01-08 | Price Down 상품 제외 로직 추가 |
| v3.0 | 2025-12-10 | 멀티 브랜드 확장 (Queens Selection, Verda 추가) |
| v2.10 | 2025-12-10 | 평일만 실행 조건 추가 |
| v2.9 | 2025-12-10 | vendor_category 추가, 4단계 프로세스 단순화 |
| v2.8 | 2025-12-10 | Slack 알림 연동 |
| v2.3 | 2025-12-09 | reserved_qty 3일 임계값 적용 |
| v2.0 | 2025-12-09 | Auto-Expire 방식 설계 |
| v1.0 | 2025-12-09 | 초기 문서 작성 |
