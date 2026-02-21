# PB 리오더 시스템 기술 문서

> **Version:** 4.9 (2026-02-05)
> **Status:** Multi-Brand Production Ready (Noir, Queens Selection, Verda, Zizae, Dana&Peta, Marchmara)

## 1. 시스템 개요

### 1.1 목적
재고 최적화를 위한 수요 예측 시스템. 과거 판매 데이터를 기반으로 향후 14/21/30/60/90일 수요를 예측하고 최적 발주량을 산출.

### 1.2 핵심 특징
- **Monte Carlo 시뮬레이션**: 확률 분포 기반 수요 예측
- **SPV(Sales Per View) 기반 가치 평가**: 카테고리 대비 상대적 효율성 분석
- **휴리스틱 폴백**: 통계 데이터 부족 시 적응형 예측
- **가용 재고 계산**: 물리적 재고 + 입고예정 - 예약배송
- **Price Down 제외**: 시즌오프 할인 상품 BigQuery 쿼리에서 제외 (`price_down_excluded` CTE)
- **차수별 예측**: 리오더 차수에 따라 예측 기간 및 수량 상한 차등 적용
- **동적 시즌 계산**: 현재 월 기준 자동 시즌 판별 (하드코딩 제거)
- **동적 차수 계산**: 품번 시즌코드 기반 당시즌/과년차 차수 자동 판별
- **시즌 기반 품번 필터링**: 당시즌 + 직전 시즌 품번만 리오더 대상 포함
- **쿼리 날짜 검증**: query_executed_at으로 데이터 신선도 확인

### 1.3 핵심 공식
```
available_stock = physical_stock + in_transit - reserved
reorder_qty = MAX(0, forecast - available_stock)
```

---

## 2. 아키텍처

### 2.1 데이터 흐름
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   데이터 소스    │ → │   예측 엔진      │ → │   의사결정      │
│ (판매/재고/상품) │    │ (통계/휴리스틱)  │    │ (발주량 산출)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                                              │
         ▼                                              ▼
┌─────────────────┐                          ┌─────────────────┐
│   가용 재고      │                          │   자동화 출력   │
│ (BigQuery 계산) │                          │ (Sheets/Slack)  │
└─────────────────┘                          └─────────────────┘
```

### 2.2 멀티 브랜드 데이터 소스

#### 공통 테이블
| 테이블 | 용도 |
|--------|------|
| `damoa-lake.logistics_owned.stockDetail_raw` | 물리적 재고 (전 브랜드 공통) |
| `damoa-lake.logistics_owned.daily_inventory_transaction` | 리오더 차수 계산 (inbound 컬럼) |
| `damoa-lake.ms_order.order_shipment_estimate` | 예약 배송 정보 |
| `damoa-lake.ms_product.product_item` | 상품 마스터 |
| `damoa-lake.ms_order.order_line` | 주문 라인 |
| `damoa-mart.biz_analytics.product_funnel_daily` | 일별 판매 퍼널 |

#### 브랜드별 Master 테이블
| 브랜드 | Master 테이블 | 브랜드 코드 |
|--------|---------------|-------------|
| Noir | `damoa-lake.pb2_owned.noor_master` | NR |
| Queens Selection | `damoa-lake.pb2_owned.queens_master` | QU |
| Verda | `damoa-lake.pb2_owned.verda_master` | VD |
| Zizae | `damoa-lake.pb1_owned.zizae_master` | ZE |
| Dana&Peta | `damoa-lake.pb1_owned.dana_master` | DN |

### 2.3 레거시 PB 브랜드 데이터 소스 (참고용)
| 테이블 | 용도 |
|--------|------|
| `damoa-lake.ms_product.product` | 상품 마스터 |
| `damoa-mart.m_products.leaf_category_map` | 카테고리 매핑 |
| `damoa-mart.base.snap_order_rds` | 주문 스냅샷 |
| `damoa-mart.pb1.pb1_real_stock_*` | 실시간 재고 |

---

## 3. 핵심 알고리즘

### 3.1 파라미터 정의
```sql
-- 동적 날짜 범위 (372일 = 1년 + 1주)
DECLARE START_DATE DATE DEFAULT DATE_SUB(CURRENT_DATE(), INTERVAL 372 DAY);
DECLARE RELATIVE_SPV_THRESHOLD FLOAT64 DEFAULT 0.65;  -- SPV 하한 임계값
DECLARE HIGH_SPV_MULTIPLIER FLOAT64 DEFAULT 1.3;      -- 고SPV 판정 기준
DECLARE HEURISTIC_DAYS INT64 DEFAULT 14;              -- 휴리스틱 커버리지 일수
DECLARE HEURISTIC_SPV_MIN FLOAT64 DEFAULT 0.90;       -- SPV 스케일 하한
DECLARE HEURISTIC_SPV_MAX FLOAT64 DEFAULT 1.10;       -- SPV 스케일 상한
```

### 3.2 Monte Carlo 시뮬레이션
- **난수 생성**: Mersenne Twister 알고리즘 사용
- **시뮬레이션 횟수**: 기간별 1,000회 반복
- **예측 기간**: 조건별 14일(기본) 또는 21일(5차+ & SPV>1.3 & 시즌잔여>30일)
- **분위수 산출**: 30%(보수적), 50%(보통), 90%(공격적)

```sql
-- 예측 기간별 난수 배열 생성 (차수별)
CREATE TEMP FUNCTION integral_14d() RETURNS ARRAY<float64>
LANGUAGE js OPTIONS (library = ['gs://rec-monte/mersenne-twister.js'])
AS "
  var MT = new MersenneTwister();
  var result = [];
  for(var i=0; i<14*1000; ++i) result.push(MT.random());
  return result;
";

CREATE TEMP FUNCTION integral_21d() RETURNS ARRAY<float64>
LANGUAGE js OPTIONS (library = ['gs://rec-monte/mersenne-twister.js'])
AS "
  var MT = new MersenneTwister();
  var result = [];
  for(var i=0; i<21*1000; ++i) result.push(MT.random());
  return result;
";
```

### 3.3 역오차함수 (erfinv)
정규분포 역변환을 위한 수치 근사:
```sql
CREATE TEMPORARY FUNCTION erfinv(prob FLOAT64) RETURNS FLOAT64
LANGUAGE js AS "
  const a=0.147;
  const b=2/(Math.PI*a)+Math.log(1-prob**2)/2;
  const sqrt1=Math.sqrt(b**2-Math.log(1-prob**2)/a);
  const sqrt2=Math.sqrt(sqrt1-b);
  return sqrt2*Math.sign(prob);
";
```

### 3.4 예측 레벨 분류
| 레벨 | 조건 | 예측 방법 |
|------|------|-----------|
| Statistical | 충분한 과거 데이터 존재 | Monte Carlo 시뮬레이션 |
| Heuristic (High-SPV) | 높은 SPV, 통계 예측 없음 | 7일 판매 × 2 |
| Heuristic (Adaptive-14d) | 그 외 | 14일 가중평균 기반 |

---

## 4. 예측 로직 상세

### 4.1 통계적 예측 (Statistical Forecasts)
```
1. 과거 데이터 컨텍스트 그룹화
   - 상품 유형 (신상품/기존상품)
   - 카테고리
   - ISO 주차
   - 7일/14일 판매 구간(bin)

2. 그룹별 통계량 계산
   - 중앙값 (median_daily_sales)
   - 표준편차 (stddev_daily_sales)

3. Monte Carlo 시뮬레이션
   - 역오차함수로 정규분포 샘플링
   - 기간별 누적 판매량 시뮬레이션

4. 분위수 기반 예측치 산출
   - 30분위: conservative_forecast
   - 50분위: normal_forecast
   - 90분위: aggressive_forecast
```

### 4.2 휴리스틱 예측 (Heuristic)
```
base_h_14d = 14 × (0.7 × 7일평균 + 0.3 × 14일평균)
spv_scale = CLAMP(1.0 + 0.2 × (relative_spv - 1.0), 0.9, 1.1)
lower_guard = 0.8 × 14일판매
upper_guard = MIN(1.5 × 14일판매, 90일판매 × 14/90 × 1.2)
final = CLAMP(base_h_14d × spv_scale, lower_guard, upper_guard)
```

### 4.3 SPV (Sales Per View) 지표
```sql
relative_spv_index = sku_spv_past_14d / avg_category_spv
```
- `> 1.3`: High-SPV 상품 (공격적 재고)
- `< 0.65`: 저효율 상품 (필터링)

---

## 5. 발주량 산출

### 5.1 공식
```
reorder_qty = CEIL((forecast - available_stock) / 5) × 5
```
- 5개 단위로 올림 (MOQ: Minimum Order Quantity)
- 음수는 0으로 처리

### 5.2 예측 시나리오
| 시나리오 | 분위수 | 용도 |
|----------|--------|------|
| Conservative | 30% | 안전 재고, 리스크 최소화 |
| Normal | 50% | 표준 발주 |
| Aggressive | 90% | 프로모션, 시즌 대비 |

---

## 6. 출력 스키마 (전 브랜드 공통)

### 6.1 컬럼 구조
| Index | Column | 설명 |
|-------|--------|------|
| A | product_item_code | SKU 코드 |
| B | vendor_category | 발주처 구분 (동대문, 해외 등) |
| C | base_category_name | 카테고리 |
| D | current_stock | 현재 재고 |
| ... | ... | ... |
| Y | reorder_qty | 최종 발주량 |

### 6.2 주요 컬럼
```sql
SELECT
  product_item_code,           -- SKU 코드
  vendor_category,             -- 발주처 구분
  base_category_name,          -- 카테고리
  physical_stock,              -- 물리적 재고
  in_transit_qty,              -- 입고예정 수량
  reserved_qty,                -- 예약배송 수량
  available_stock,             -- 가용 재고
  forecast,                    -- 예측 수요
  reorder_qty                  -- 발주량
FROM {brand}_reorder_results
WHERE reorder_qty > 0
```

### 6.3 브랜드별 쿼리 파일
| 브랜드 | 쿼리 파일 | 버전 |
|--------|-----------|------|
| Noir | `noir_reorder_v1.7.sql` | v1.7 |
| Queens Selection | `queens_reorder_v1.6.sql` | v1.6 |
| Verda | `verda_reorder_v1.6.sql` | v1.6 |
| Zizae | `zizae_reorder_v1.7.sql` | v1.7 |
| Dana&Peta | `danapeta_reorder_v1.6.sql` | v1.6 |
| Marchmara | `marchmara_reorder_v1.7.sql` | v1.7 |

---

## 7. 자동화 시스템 (Apps Script)

### 7.1 실행 조건 (전 브랜드 공통)
| 조건 | 설명 |
|------|------|
| **실행 요일** | 월~금 (평일만) |
| **스킵 요일** | 토/일 (주말) |
| **회사 휴일 스킵** | 각 브랜드 스프레드시트 `휴일` 탭의 A열 날짜와 일치 시 스킵 |
| **트리거** | 매일 오전 10시 |

#### 휴일 관리
- 각 브랜드 스프레드시트에 `휴일` 시트 탭이 존재
- A열: 날짜 (`yyyy-MM-dd`), B열: 휴일명 (참고용)
- `isCompanyHoliday(ss, todayStr)` 함수가 주말 체크 직후 실행
- 시트가 없거나 비어있으면 휴일이 아닌 것으로 처리 (안전 폴백)
- 휴일 일괄 관리: `scripts/setup_holidays.js` 또는 Google Sheets API (`gcloud`)

### 7.2 프로세스 흐름 (4단계)
```
1. getReorderItems()          → BigQuery 쿼리 실행
2. appendToReorderLogSheet()  → '5.2 리오더 내역' 기록
3. archiveReorderItems()      → reorder_archive 아카이브
4. postSlackNotification()    → Slack 알림
```

### 7.3 브랜드별 Apps Script
| 브랜드 | 스크립트 파일 | 버전 | Spreadsheet ID |
|--------|--------------|------|----------------|
| Noir | `리오더 프로세스.js` | v1.7 | `1q0CsxQXe3W-Y6xDcgNY-uT1oBDH_IZgrK-Gm7uTl8YE` |
| Queens Selection | `리오더 프로세스.js` | v1.4 | `1CqbglHwEFrQzYUPA4oHyrv7doG3pAtE3tUs68wfaN4w` |
| Verda | `리오더 프로세스.js` | v1.4 | `1Z8S1gl1bjc0YaQmIQU3_QhvpA8xxCEYHtedMuOM2wco` |
| Zizae | `리오더 프로세스.js` | v1.4 | `1MDEQrx_o9YqFmwbiSTDYiG4cJ0tvBpXuUiIYXog15AI` |
| Dana&Peta | `리오더 프로세스.js` | v1.3 | `1JkTrLc7uhEfMpHIFUZ2EvwFy3Kp76AGa-h9pagPwz5k` |
| Marchmara | `리오더 프로세스.js` | v1.4 | `11tIOjKJ0WKvUcMh8M6Z2TpOdU3n9JkO71ukoDPuzPRY` |

### 7.4 Slack 설정 (전 브랜드 공통)
| 설정 | 값 |
|------|-----|
| Channel ID | `C0ABHFXMLP5` |
| Subteam ID | `S02675SMW3Z` |
| Mention Users | `U09F2EE35RR`, `U09SDNSAC9H` |

### 7.5 출력 대상
| 대상 | 시트/채널 | 용도 |
|------|-----------|------|
| 5.2 리오더 내역 | A:날짜, C:바코드, AA:수량 | 발주 요청 |
| reorder_archive | 28 columns | 이력 보관 |
| Slack | 공통 채널 | 실시간 알림 |

### 7.6 컬럼 구조 (30 Columns)
| 범위 | 컬럼 수 | 설명 |
|------|--------|------|
| A-AA | 27개 | BigQuery 쿼리 결과 |
| AB-AD | 3개 | Apps Script 계산 (date, product_code, qty) |

**핵심 컬럼 인덱스**:
- `QUERY_EXECUTED_AT`: 26 (AA열)
- `SEASONALITY_WEIGHT`: 27 (AB열)
- `SEASONALITY_SOURCE`: 28 (AC열)
- `REORDER_QTY`: 29 (AD열)
### 7.7 Price Down 제외 로직 (BigQuery CTE 기반)

**목적**: pb_price_down 프로젝트에서 시즌오프 할인 처리된 상품이 리오더 대상이 되는 것을 방지

**구현 위치**: BigQuery 쿼리 (`price_down_excluded` CTE)

**이전 방식 (Apps Script, 제거됨)**: E/F등급 + 60일 할인이력 기반 스프레드시트 조회
**현재 방식 (BigQuery CTE)**: 시즌오프 기간에 실제 Price Down API 성공 기록 기반 제외

**제외 조건**:
- 시즌오프 기간 (1~2월: FW 상품, 7~8월: SS 상품)
- Price Down API 실행 성공 (`api_action IN ('POST', 'DELETE→POST')`, `api_result = 'success'`)
- 취소되지 않은 건 (`selection_reason`이 'cancelled'로 시작하지 않음)
- 해당 상품의 가장 최근 기록 기준 (`ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY dt DESC)`)

**쿼리 구현**:
```sql
price_down_excluded AS (
  SELECT product_id AS item_id
  FROM (
    SELECT product_id, __product_season__, selection_reason,
      api_action, api_result, dt,
      ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY dt DESC) AS rn
    FROM `damoa-lake.pb1_owned.price_down_history_sheet`
    WHERE product_id IS NOT NULL
  )
  WHERE rn = 1
    AND api_action IN ('POST', 'DELETE→POST')
    AND api_result = 'success'
    AND (selection_reason IS NULL OR NOT STARTS_WITH(selection_reason, 'cancelled'))
    AND TRIM(__product_season__) LIKE CASE
      WHEN EXTRACT(MONTH FROM CURRENT_DATE()) IN (7, 8) THEN '%SS'
      WHEN EXTRACT(MONTH FROM CURRENT_DATE()) IN (1, 2) THEN '%FW'
      ELSE 'NO_MATCH_NOT_SEASON_OFF'
    END
)
```

**적용 위치**: `current_product_status` CTE에서 `WHERE NOT EXISTS` 필터

**시즌오프 동작**:
| 현재 월 | 제외 대상 | 비고 |
|---------|----------|------|
| 1~2월 | FW 시즌 Price Down 상품 | 시즌오프 |
| 7~8월 | SS 시즌 Price Down 상품 | 시즌오프 |
| 3~6월, 9~12월 | 없음 | 시즌오프 아님 |

### 7.8 동적 차수 계산 및 시즌 품번 필터링 (v1.8/v1.7+)

**문제점**: 기존 차수 계산은 현재 시즌 내 입고 횟수만 카운트. 과년차 품번(예: 25F/W 품번이 26S/S에 리오더)이 시즌 전환 시 차수가 0으로 리셋되어, 이미 검증된 상품에 초도~4차 규칙(10장 상한, 14일 예측)이 다시 적용됨.

**해결책 1: 동적 차수 (reorder_history)**

품번의 시즌코드(5번째 자리)와 연도(3-4번째 자리)를 파싱하여 당시즌 품번 여부를 판별:

```sql
-- 직전 시즌 시작일 (2개 시즌만 스캔)
DECLARE PREV_SEASON_START DATE DEFAULT (
  CASE
    WHEN CURRENT_MONTH >= 9 THEN DATE(CURRENT_YEAR, 3, 1)        -- F/W → 직전 S/S
    WHEN CURRENT_MONTH <= 2 THEN DATE(CURRENT_YEAR - 1, 3, 1)    -- F/W(1~2월) → 직전 S/S
    ELSE DATE(CURRENT_YEAR - 1, 9, 1)                             -- S/S → 직전 F/W
  END
);

-- 품번 시즌 판별 (예: NR25F001 → 연도=25, 시즌=F)
CASE
  WHEN SUBSTR(barcode, 5, 1) IN ('F', 'W', 'D')
       AND SAFE_CAST(SUBSTR(barcode, 3, 2) AS INT64) = MOD(EXTRACT(YEAR FROM SEASON_START), 100)
       AND CURRENT_MONTH IN (9,10,11,12,1,2)
  THEN TRUE  -- 당시즌 품번
  WHEN SUBSTR(barcode, 5, 1) IN ('S', 'M', 'H')
       AND SAFE_CAST(SUBSTR(barcode, 3, 2) AS INT64) = MOD(CURRENT_YEAR, 100)
       AND CURRENT_MONTH BETWEEN 3 AND 8
  THEN TRUE  -- 당시즌 품번
  ELSE FALSE -- 과년차/직전 시즌 품번
END AS is_current_season_product

-- 동적 차수 결정
CASE
  WHEN is_current_season_product THEN season_reorder_order  -- 시즌 차수
  ELSE total_reorder_order                                   -- 누적 차수
END AS reorder_order
```

**해결책 2: 시즌 품번 필터링 (reorderable_products)**

모든 브랜드에서 당시즌 + 직전 시즌 품번만 리오더 대상에 포함:

```sql
reorderable_products AS (
  SELECT DISTINCT barcode AS product_item_code, vendor_category
  FROM master_table
  WHERE barcode IS NOT NULL AND barcode != ''
    AND (
      -- 당시즌 품번 (예: F/W 시즌 → 25F/W/D)
      (SAFE_CAST(SUBSTR(barcode, 3, 2) AS INT64) = MOD(EXTRACT(YEAR FROM SEASON_START), 100)
       AND CASE
             WHEN CURRENT_MONTH IN (9,10,11,12,1,2) THEN SUBSTR(barcode, 5, 1) IN ('F','W','D')
             ELSE SUBSTR(barcode, 5, 1) IN ('S','M','H')
           END)
      OR
      -- 직전 시즌 품번 (예: F/W 시즌 → 25S/M/H)
      (SAFE_CAST(SUBSTR(barcode, 3, 2) AS INT64) = MOD(EXTRACT(YEAR FROM PREV_SEASON_START), 100)
       AND CASE
             WHEN CURRENT_MONTH IN (9,10,11,12,1,2) THEN SUBSTR(barcode, 5, 1) IN ('S','M','H')
             ELSE SUBSTR(barcode, 5, 1) IN ('F','W','D')
           END)
    )
)
```

**시즌코드 매핑**:
| 시즌 | 코드 | 설명 |
|------|------|------|
| F/W | F, W, D | Fall, Winter, December |
| S/S | S, M, H | Spring, Summer (M/H는 브랜드별 변형) |

**동작 예시 (1월 30일, F/W 시즌 기준)**:
| 품번 | reorderable | is_current_season | 적용 차수 |
|------|-------------|-------------------|-----------|
| NR25F001 | 당시즌 F/W | TRUE | 시즌 차수 |
| NR25S001 | 직전 S/S | FALSE | 누적 차수 (리셋 안 됨) |
| NR24F001 | 제외 (2시즌 밖) | - | - |

### 7.9 동적 시즌 계산 (v1.2+)

**목적**: 하드코딩된 시즌 날짜로 인한 reorder_order=0 문제 해결

**계산 로직**:
```sql
-- 현재 월 기준 자동 시즌 판별
CASE
  WHEN EXTRACT(MONTH FROM CURRENT_DATE()) BETWEEN 9 AND 12 THEN
    -- 9~12월: F/W 시즌 (올해 09-01 ~ 다음해 02-28)
    (CONCAT(CAST(EXTRACT(YEAR FROM CURRENT_DATE()) AS STRING), '-09-01'),
     CONCAT(CAST(EXTRACT(YEAR FROM CURRENT_DATE()) + 1 AS STRING), '-02-28'))
  WHEN EXTRACT(MONTH FROM CURRENT_DATE()) BETWEEN 1 AND 2 THEN
    -- 1~2월: F/W 시즌 계속 (작년 09-01 ~ 올해 02-28)
    (CONCAT(CAST(EXTRACT(YEAR FROM CURRENT_DATE()) - 1 AS STRING), '-09-01'),
     CONCAT(CAST(EXTRACT(YEAR FROM CURRENT_DATE()) AS STRING), '-02-28'))
  ELSE
    -- 3~8월: S/S 시즌 (올해 03-01 ~ 08-31)
    (CONCAT(CAST(EXTRACT(YEAR FROM CURRENT_DATE()) AS STRING), '-03-01'),
     CONCAT(CAST(EXTRACT(YEAR FROM CURRENT_DATE()) AS STRING), '-08-31'))
END
```

### 7.10 쿼리 날짜 검증 (v1.6+)

**목적**: BigQuery 쿼리가 오늘 실행되었는지 검증하여 stale 데이터 방지

**검증 로직**:
```javascript
function validateQueryExecutedDate(row) {
  var queryDate = row[COLUMN_CONFIG.QUERY_EXECUTED_AT];  // index 24, Y열
  var today = Utilities.formatDate(new Date(), 'Asia/Seoul', 'yyyy-MM-dd');
  if (queryDate !== today) {
    throw new Error('Query date mismatch: expected ' + today + ', got ' + queryDate);
  }
}
```

**Fallback**: 검증 실패 시 Slack으로 경고 메시지 전송 (발주 데이터 없음)

### 7.11 Heuristics 계절성 가중치 (v1.7/v1.6+)

**목적**: 시즌 말(1-2월)에 Heuristics 예측이 최근 판매량의 단순 배수를 적용하여 과재고 발생 방지

**문제점**:
- Statistical 예측: ISO week 기반 계절성 반영 ✅
- Heuristics 예측: 계절성 미반영 → 시즌 말 과재고 위험 ❌

**해결책: Hybrid Approach**

ISO week 기반 계절성 팩터 우선 사용, 데이터 부족 시 시즌 진행도 기반 감쇠로 폴백

**파라미터**:
```sql
DECLARE MIN_ISOWEEK_SAMPLES INT64 DEFAULT 14;        -- ISO week factor 사용 최소 샘플
DECLARE SEASON_DECAY_RATE FLOAT64 DEFAULT 0.25;      -- 시즌 말 최대 감쇠율 (25%)
DECLARE SEASONALITY_WEIGHT_MIN FLOAT64 DEFAULT 0.70; -- 계절성 가중치 하한
DECLARE SEASONALITY_WEIGHT_MAX FLOAT64 DEFAULT 1.50; -- 계절성 가중치 상한 (피크 시즌 반영)
```

**계절성 가중치 결정 로직**:
```sql
-- 1차: ISO week 기반 팩터 (데이터 충분 시)
isoweek_factor = (해당 주차 일평균 판매) / (연간 일평균 판매)
  → 범위: [0.70, 1.50] (피크 시즌 증가, 시즌 말 감소)
  → 조건: 해당 주차 샘플 ≥ 14일

-- 2차: 시즌 진행도 기반 감쇠 (폴백)
decay_factor = 1.0 - (0.25 × 시즌 진행률)
  → 시즌 시작: 1.0 (감쇠 없음)
  → 시즌 종료: 0.75 (25% 감쇠)

-- 최종 가중치
seasonality_weight = COALESCE(isoweek_factor, decay_factor)
```

**적용 대상**:
- Heuristic (High-SPV): `sales_past_7_days × 2 × seasonality_weight`
- Heuristic (Adaptive): `base_forecast × spv_scale × seasonality_weight`
- Statistical: 변경 없음 (이미 ISO week 컨텍스트 반영)

**자동 계산 메커니즘**:

쿼리 실행 시 4개 CTE가 순차적으로 ISO week factor를 자동 계산:
```sql
category_isoweek_stats     → 카테고리별 주차 판매 통계
category_annual_baseline   → 카테고리 시즌 평균
isoweek_seasonality        → ISO week factor = (주차 평균) / (시즌 평균)
season_progress_factor     → 폴백용 시즌 진행도 감쇠
```

**시즌별 자동 감지**:
| 실행 시점 | 시즌 | SEASON_START | SEASON_END |
|----------|------|--------------|------------|
| 9월~2월 | F/W | 9월 1일 | 다음해 2월 28일 |
| 3월~8월 | S/S | 3월 1일 | 8월 31일 |

**시즌별 계절성 팩터 비교**:
| 시즌 | 피크 시기 | 피크 Factor | 시즌 말 Factor |
|------|----------|-------------|----------------|
| F/W | 11월 (Week 45-47) | 1.50-1.62 → **1.50** | 0.77-0.84 |
| S/S | 4월 (Week 15-16) | 1.25-1.26 | 0.79-0.89 |

**디버깅 컬럼**:
- `seasonality_weight`: 적용된 가중치 값
- `seasonality_source`: 'ISO Week' 또는 'Season Progress'

---

### 7.12 보수적 발주 로직 (v1.6+)

**목적**: 장기 재고 상품 및 시즌 말 과재고 방지

**로직 (우선순위 순)**:
1. 시즌 전환기(시즌 초/말 30일) + 기존상품(출시 28일+) + 추천 10장 이하 → 0장 처리 (v1.7+)
2. 출시 70일(10주) 이상 + 추천 수량 5장 → 0장 처리

**시즌 전환기 정의**:
- 시즌 말: `DATE_DIFF(SEASON_END, CURRENT_DATE(), DAY) <= 30`
- 시즌 초: `DATE_DIFF(CURRENT_DATE(), SEASON_START, DAY) <= 30`
- 시즌 초를 포함하는 이유: 시즌 전환 시 이전 시즌 상품이 리오더 대상에 포함될 수 있음

**구현 (SQL)**:
```sql
-- 보수적 발주: (1) 시즌 전환기 기존상품 10장 이하 → 0장, (2) 출시 70일+ & 5장 → 0장
CASE
  WHEN (DATE_DIFF(SEASON_END, CURRENT_DATE(), DAY) <= 30
        OR DATE_DIFF(CURRENT_DATE(), SEASON_START, DAY) <= 30)
    AND f.product_type = '기존상품'
    AND (CASE WHEN f.apply_qty_cap THEN LEAST(f.raw_forecast, REORDER_QTY_CAP) ELSE f.raw_forecast END) <= 10
  THEN 0
  WHEN IFNULL(f.days_since_launch, 0) >= 70
    AND (CASE WHEN f.apply_qty_cap THEN LEAST(f.raw_forecast, REORDER_QTY_CAP) ELSE f.raw_forecast END) = 5
  THEN 0
  ELSE CASE WHEN f.apply_qty_cap THEN LEAST(f.raw_forecast, REORDER_QTY_CAP) ELSE f.raw_forecast END
END AS normal_forecast
```

**Note**: 시즌 전환기 규칙은 신상품(출시 28일 미만)에는 적용되지 않음 — 신상품은 시즌 전환기에도 발주 유지

**출력 형식**:
- `product_type` 컬럼에 출시일수 포함: "기존상품(85일)", "신상품(15일)"
- `days_since_launch`는 별도 컬럼 대신 product_type에 통합하여 컬럼 수 유지

### 7.14 예측 기간 로직 (v1.2+ → v1.7+ 개선)

**목적**: 검증 없는 초기 대량 베팅 방지 + 시즌 말 과재고 방지

**예측 기간 결정 (우선순위 순)**:

| 우선순위 | 조건 | 예측 기간 | 비고 |
|---------|------|----------|------|
| 1 | 초도~4차 (reorder_order ≤ 4) | 14일 | 검증 중 |
| 2 | 시즌 전환기 (시즌 초/말 30일 이내) | 14일 | 시즌 전환기 과재고 방지 (v1.7+) |
| 3 | SPV > 1.3배 (relative_spv_index > 1.3) | 21일 | 고효율 상품만 3주 (v1.7+) |
| 4 | 그 외 | 14일 | 기본값 |

**수량 상한** (초도~4차):
- 기본: 10장
- 예외 해제: High-SPV (`relative_spv_index > 1.3`) AND 판매 속도 (`sales_past_7_days >= 7`)

**v1.7 변경점**:
- 기존: 5차+ 무조건 21일 → **변경**: 5차+에서 SPV 1.3배 초과일 때만 21일
- 신규: 시즌 전환기(초/말 30일) 무조건 14일 강제

---

## 8. 버전 히스토리

| 버전 | 날짜 | 변경사항 |
|------|------|----------|
| v4.9 | 2026-02-05 | Price Down CTE `api_action` 조건 확장: `'POST'` → `IN ('POST', 'DELETE→POST')` — 삭제 후 재등록(163건) 포함 |
| v4.8 | 2026-02-05 | Price Down 제외 로직 BigQuery CTE로 이전 (Apps Script 제거), 시즌오프 할인 상품 기반 제외, Marchmara 쿼리 테이블 추가 |
| v4.7 | 2026-02-04 | 회사 휴일 스킵 로직 추가 (`휴일` 시트 기반), 다나앤페타 Spreadsheet ID 수정, 마치마라 브랜드 테이블 추가, 스크립트 파일명 최신화 |
| v4.6 | 2026-01-30 | 동적 차수 계산 (품번 시즌코드 기반 당시즌/과년차 판별), 시즌 품번 필터링 (당시즌+직전 시즌), PREV_SEASON_START 파라미터 추가 |
| v4.5 | 2026-01-30 | 시즌 전환기 확대 (시즌 말 → 시즌 초/말 30일), 이전 시즌 상품 리오더 방지 |
| v4.4 | 2026-01-29 | 예측 기간 SPV 기반 전환 (5차+ 무조건 21일 → SPV>1.3만 21일), 시즌 말 30일 14일 강제, 시즌 말 기존상품 10장 이하 발주 제외 |
| v4.3 | 2026-01-20 | Heuristics 계절성 가중치 추가 (ISO week 팩터 + 시즌 진행도 폴백), 시즌 말 과재고 방지 |
| v4.2 | 2026-01-14 | 보수적 발주 로직 (70일+/5장→0), Price Down 60일, extractPbCode 정규식 개선, product_type 출시일수 표시 |
| v4.1 | 2026-01-12 | 쿼리 성능 최적화 (372일 동적 날짜, Context 사전 필터링) |
| v4.0 | 2026-01-09 | 동적 시즌 계산, 쿼리 날짜 검증, 차수별 예측 로직 추가 |
| v3.1 | 2026-01-08 | Price Down 제외 로직 추가 (E/F등급 + 할인이력), Zizae/Dana&Peta 브랜드 추가 |
| v3.0 | 2025-12-10 | 멀티 브랜드 지원 (Noir, Queens Selection, Verda), Slack 설정 통일 |
| v2.0 | 2025-12-10 | Noir 브랜드 통합, 자동화 완성 |
| v1.3 | 2025-12-10 | 평일만 실행 조건 추가 |
| v1.1 | 2025-12-10 | vendor_category 추가 |
| v1.0 | 2025-12-09 | Noir 초기 버전 |
| v23.1 | 2025-12 | PB: Heuristic 14d coverage 내재화 |
| v23.0 | 2025-11 | PB: Monte Carlo 시뮬레이션 도입 |
