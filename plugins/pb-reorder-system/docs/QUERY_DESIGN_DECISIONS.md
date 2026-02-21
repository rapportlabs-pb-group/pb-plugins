# Query Design Decisions

> **Version:** 5.2 (2026-02-05)
> **Status:** Multi-Brand Production Ready (6 Brands)
> **변경사항:** Price Down CTE `api_action` 조건 확장 (`DELETE→POST` 포함)

## 1. Overview

이 문서는 PB 리오더 쿼리들의 설계 결정사항과 브랜드별 구현 차이점을 정리합니다.

### 1.1 쿼리 현황
| 브랜드 | 쿼리 파일 | 버전 | 상태 |
|--------|-----------|------|------|
| Noir | `noir_reorder_v1.7.sql` | v1.7 | Production |
| Queens Selection | `queens_reorder_v1.6.sql` | v1.6 | Production |
| Verda | `verda_reorder_v1.6.sql` | v1.6 | Production |
| Zizae | `zizae_reorder_v1.7.sql` | v1.7 | Production |
| Dana&Peta | `danapeta_reorder_v1.6.sql` | v1.6 | Production |
| Marchmara | `marchmara_reorder_v1.7.sql` | v1.7 | Production |

---

## 2. AI Review Summary

### 2.1 참여 AI
- **Codex (GPT-5.1)**: 코드 정확성, Join 로직, 성능 분석
- **Gemini**: 비즈니스 로직, 데이터 무결성, 엣지 케이스
- **Claude**: 종합 분석 및 최종 결정

### 2.2 리뷰 결과 요약

| 이슈 | Codex | Gemini | 최종 결정 |
|------|-------|--------|-----------|
| 예측 기간 스케일 불일치 | 🟡 Medium | 🔴 Critical | ✅ **v1.2+ 차수별 14/21일 적용** |
| 주문 상태 필터 불충분 | 🟡 Recommend | 🟠 High | ✅ **현행 유지** |
| 신상품 SPV 필터링 | 🟡 Recommend | 🟠 High | ✅ **Option B 채택** |
| Monte Carlo 재현성 | - | 🟡 Medium | 🔵 선택적 |
| Reserved 3일 임계값 | ✅ OK | ✅ 권장 | ✅ **v2.3 채택** |
| delivery_state 필터 | ✅ 권장 | ✅ 권장 | 🔵 모니터링 후 결정 |

---

## 3. Design Decision #1: Reserved Quantity (v2.3)

### 3.1 현재 구현
```sql
WITH latest_est AS (
  SELECT order_line_id, estimate_shipment_at
  FROM (
    SELECT order_line_id, estimate_shipment_at,
           ROW_NUMBER() OVER (PARTITION BY order_line_id
                              ORDER BY updated_at DESC, created_at DESC) AS rn
    FROM order_shipment_estimate
  )
  WHERE rn = 1
)
SELECT pi.product_item_code, SUM(ol.quantity) AS reserved_qty
FROM order_line ol
JOIN product_item pi ON ol.product_item_id = pi.id
JOIN latest_est ose ON ol.id = ose.order_line_id
WHERE pi.product_item_code LIKE 'NR%'
  AND ol.purchase_state = 'PAID'
  AND ose.estimate_shipment_at >= CURRENT_DATE() + 3
GROUP BY pi.product_item_code;
```

### 3.2 AI 분석 (v2.3 검토)

| 질문 | Codex | Gemini |
|------|-------|--------|
| delivery_state 필터 추가? | ✅ 권장 | ✅ 필수 |
| 3일 임계값 적절? | ✅ OK | ✅ 적절 |
| ROW_NUMBER 방식? | ✅ 정확 | ✅ 정확 |
| NULL 처리? | 🟡 검토 | 🟡 검토 |
| v2.2 vs v2.3? | v2.3 선호 | **v2.3 안전** |

### 3.3 최종 결정

**v2.3 채택 이유 (과재고 방지 우선):**
- v2.2 (전체 pending): 높은 Reserved → 낮은 Available → 조기 발주 → **과재고 위험**
- v2.3 (3일+ only): 낮은 Reserved → 높은 Available → 지연 발주 → **과재고 방지**

**결론: ✅ v2.3 적용, delivery_state 필터는 모니터링 후 결정**

---

## 4. Design Decision #2: Forecast Time Horizon

### 4.1 현재 구현 (v1.7+ SPV 기반 예측)

```sql
-- 예측 기간 선택 (우선순위 순)
CASE
  WHEN s.reorder_order <= 4 THEN 14                              -- 1순위: 초도~4차
  WHEN DATE_DIFF(SEASON_END, CURRENT_DATE(), DAY) <= 30 THEN 14 -- 2순위: 시즌 말
  WHEN IFNULL(SAFE_DIVIDE(s.sku_spv_past_14d, b.avg_category_spv), 0) > HIGH_SPV_MULTIPLIER THEN 21  -- 3순위: SPV>1.3
  ELSE 14                                                        -- 4순위: 기본값
END AS forecast_days

-- Statistical forecast도 동일 조건 적용
CASE
  WHEN s.reorder_order <= 4 THEN IFNULL(st14.normal_forecast_14d, 0)
  WHEN DATE_DIFF(SEASON_END, CURRENT_DATE(), DAY) <= 30 THEN IFNULL(st14.normal_forecast_14d, 0)
  WHEN ... > HIGH_SPV_MULTIPLIER THEN IFNULL(st21.normal_forecast_21d, 0)
  ELSE IFNULL(st14.normal_forecast_14d, 0)
END AS statistical_forecast
```

### 4.2 설계 의도 (v1.7+ SPV 기반 예측)

**조건별 보수적 설계:**

```
┌─────────────────────────────────────────────────────────────────┐
│  Forecast Strategy (v1.7+ 우선순위 기반)                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1순위: 초도~4차 → 14일                                        │
│    - 수량 상한: 10장 (예외: High-SPV & 일판매 1+)              │
│    - 이유: 신상품 초반 과재고 방지                              │
│                                                                 │
│  2순위: 시즌 전환기 (초/말 30일) → 14일                        │
│    - 시즌 말: SEASON_END까지 30일 이내                         │
│    - 시즌 초: SEASON_START로부터 30일 이내                     │
│    - 이유: 시즌 전환기 과재고 방지, 이전 시즌 상품 보호        │
│                                                                 │
│  3순위: SPV > 1.3배 → 21일                                     │
│    - 대상: 카테고리 평균 대비 판매효율 1.3배 초과 상품          │
│    - 이유: 고효율 상품만 3주 예측 허용                          │
│                                                                 │
│  4순위: 그 외 → 14일                                           │
│    - 기존: 5차+ 무조건 21일 → 변경: 14일 (보수적)              │
│                                                                 │
│  핵심 변경 (v1.7):                                              │
│    - 기존: reorder_order 기반 (≤4차 14일, 5차+ 21일)           │
│    - 변경: SPV 기반 (>1.3배만 21일, 나머지 14일)               │
│    - 추가: 시즌 말 30일 무조건 14일 강제                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**핵심 원칙: 과재고 방지 > 품절 방지**

**결론: ✅ v1.7+ SPV 기반 예측 + 시즌 말 강제 적용 완료**

---

## 5. Design Decision #3: Order State Filter

### 5.1 현재 구현

```sql
WHERE o.purchase_state <> 'WAIT'
```

### 5.2 설계 의도 (확정)

**현행 유지 이유:**

```
┌─────────────────────────────────────────────────────────────────┐
│  Order State Flow                                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  WAIT (결제대기) → 제외 (아직 확정 안 됨)                       │
│                                                                 │
│  PAID/SHIPPING/DELIVERED → 포함 (출고됨)                        │
│                                                                 │
│  CANCEL/REFUND/RETURN → 포함해도 OK                             │
│    이유: 반품 시 재고로 복귀 → 가용수량에 반영됨                │
│    결과: 이중 카운팅 없음                                       │
│                                                                 │
│  ※ Gemini 경고 (모니터링 필요):                                 │
│     - Pre-shipment Cancellation 비율이 높으면 수요 과대 추정    │
│     - 현재는 취소 비율 낮아서 OK                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**결론: ✅ 수정 불필요 (현행 유지, 취소 비율 모니터링)**

---

## 6. Design Decision #4: New Product SPV Threshold

### 6.1 최종 결정: ✅ Option B 채택

```sql
-- 신상품: 0.30 threshold (낮은 허들)
-- 기존상품: 0.65 threshold (표준)
WHERE (c.product_type = '신상품' AND c.relative_spv_index >= 0.30)
   OR (c.product_type <> '신상품' AND c.relative_spv_index >= 0.65)
```

**선택 이유:**
1. 간단하고 명확
2. 최소 품질 기준 유지 (Option A 대비)
3. Edge case 없음 (Option C 대비)
4. 향후 필요시 C로 업그레이드 가능

---

## 7. Design Decision #5: vendor_category (v2.9)

### 7.1 구현
```sql
SELECT
  nm.vendor_category,  -- 발주처 구분
  ...
FROM noor_master nm
JOIN ...
```

### 7.2 목적
- 발주처별 분류 (동대문, 해외 등)
- 발주 우선순위 결정 지원
- 리드타임 차별화 기반

**결론: ✅ v2.9에서 추가 완료**

---

## 8. Design Decision #6: 평일 실행 (v2.10)

### 8.1 구현
```javascript
// Apps Script v1.3
var dayOfWeek = today.getDay();
if (dayOfWeek === 0 || dayOfWeek === 6) {
  Logger.log('[스킵] 주말에는 실행하지 않습니다.');
  return;
}
```

### 8.2 목적
- 주말 불필요 발주 방지
- 동대문 사입처 휴무일 고려
- 운영 효율성 향상

**결론: ✅ v2.10에서 추가 완료**

---

## 9. Minor Considerations

### 9.1 Monte Carlo 재현성
**현재:** 시드 없음 (비결정적)
**권장:** 날짜 기반 시드 (선택적)
**결론:** 🔵 운영 안정화 후 검토

### 9.2 erfinv 정밀도
**현재:** prob ≈ ±1일 때 수치 불안정 가능
**권장:** 범위 제한 추가 (선택적)
**결론:** 🔵 실제 문제 발생 시 수정

### 9.3 NULL estimate_shipment_at 처리
**현재:** JOIN으로 제외됨 (reserved에 미포함)
**과재고 방지 관점:** NULL = 즉시출고 가정 → 제외 OK
**결론:** ✅ 현행 유지

---

## 10. Design Decision #7: 브랜드별 Master Table 일관성 (v3.1)

### 10.1 설계 원칙

모든 브랜드에서 동일한 쿼리 구조를 사용:
- Master 테이블 (`{brand}_master`)을 통한 품번 필터링
- `vendor_category`는 master 테이블에서 조회
- `stockDetail_raw.Brand` 필터 제거 (master JOIN으로 충분)

### 10.2 공통 CTE 구조

```sql
-- Step 1: Master 테이블에서 리오더 가능 품번 + vendor_category 조회
reorderable_products AS (
  SELECT DISTINCT
    barcode AS product_item_code,
    vendor_category
  FROM `damoa-lake.pb2_owned.{brand}_master`
  WHERE barcode IS NOT NULL AND barcode != ''
),

-- Step 2: 재고 테이블과 JOIN (Brand 필터 불필요)
{brand}_physical_stock AS (
  SELECT
    sd.itemCode AS mall_product_code,
    sd.avaliableStock AS physical_stock,
    rp.vendor_category
  FROM `damoa-lake.logistics_owned.stockDetail_raw` sd
  JOIN reorderable_products rp ON sd.itemCode = rp.product_item_code
  -- Note: master JOIN으로 품번 필터링되므로 Brand 조건 불필요
),
```

### 10.3 브랜드별 설정

| 브랜드 | Master Table | 브랜드 코드 |
|--------|--------------|-------------|
| Noir | `noor_master` | NR |
| Queens Selection | `queens_master` | QU |
| Verda | `verda_master` | VD |
| Zizae | `zizae_master` | ZE |
| Dana&Peta | `dana_master` | DN |

**Note:** Queens Selection의 브랜드 코드는 `QU` (이전 `QS`에서 변경)

### 10.4 이전 우회 방식 (제거됨)

이전에는 master 테이블 권한 문제로 `stockDetail_raw.Brand` 직접 필터를 사용했으나,
일관성을 위해 모든 브랜드에서 master 테이블 사용 방식으로 통일.

### 10.5 장점

1. **일관성**: 모든 브랜드에서 동일한 쿼리 구조
2. **vendor_category**: master 테이블에서 실제 값 조회
3. **품번 관리**: master 테이블 기반 리오더 가능 품번 필터링
4. **유지보수**: 브랜드 추가 시 파라미터만 변경

**결론: ✅ 모든 브랜드 Master Table 사용으로 일관성 확보**

---

## 11. Design Decision #8: 동적 시즌 계산 (v4.0)

### 11.1 문제점 (기존)
```sql
-- 하드코딩된 날짜 (매 시즌 수동 변경 필요)
DECLARE SEASON_START_DATE DATE DEFAULT '2025-09-01';
DECLARE SEASON_END_DATE DATE DEFAULT '2026-02-28';
```

### 11.2 해결책 (v1.2)
```sql
-- 현재 월 기준 자동 시즌 판별
DECLARE current_month INT64 DEFAULT EXTRACT(MONTH FROM CURRENT_DATE());
DECLARE current_year INT64 DEFAULT EXTRACT(YEAR FROM CURRENT_DATE());

-- 동적 시즌 날짜 계산
DECLARE SEASON_START_DATE DATE DEFAULT (
  CASE
    WHEN current_month >= 9 THEN DATE(current_year, 9, 1)       -- 9~12월: F/W
    WHEN current_month <= 2 THEN DATE(current_year - 1, 9, 1)   -- 1~2월: 작년 F/W
    ELSE DATE(current_year, 3, 1)                               -- 3~8월: S/S
  END
);

DECLARE SEASON_END_DATE DATE DEFAULT (
  CASE
    WHEN current_month >= 9 THEN DATE(current_year + 1, 2, 28)  -- 9~12월: 다음해 2월
    WHEN current_month <= 2 THEN DATE(current_year, 2, 28)      -- 1~2월: 올해 2월
    ELSE DATE(current_year, 8, 31)                              -- 3~8월: 8월
  END
);
```

### 11.3 시즌 구분 규칙

| 현재 월 | 시즌 | 시작일 | 종료일 |
|---------|------|--------|--------|
| 9~12월 | F/W | 09-01 (올해) | 02-28 (다음해) |
| 1~2월 | F/W (계속) | 09-01 (작년) | 02-28 (올해) |
| 3~8월 | S/S | 03-01 (올해) | 08-31 (올해) |

**결론: ✅ 하드코딩 제거, 자동 시즌 판별로 운영 편의성 향상**

---

## 12. Design Decision #9: 쿼리 날짜 검증 (v4.0)

### 12.1 문제점
- BigQuery 쿼리가 오래된 데이터를 반환할 가능성
- 스케줄러 오류로 쿼리가 실행되지 않았을 때 감지 불가

### 12.2 해결책 (v1.2+)

**쿼리에서 실행 날짜 출력:**
```sql
SELECT
  ...,
  CURRENT_DATE() AS query_executed_at  -- Y열 (index 24)
FROM ...
```

**Apps Script에서 검증 (v1.6):**
```javascript
function getReorderItems(ss) {
  var sheet = ss.getSheetByName(CONFIG.SHEET_RAW_REORDER);
  var data = sheet.getDataRange().getValues();

  // 쿼리 실행 날짜 검증 (Y열, index 24)
  var queryDate = data[1][CONFIG.RAW_REORDER.QUERY_EXECUTED_AT];
  var today = Utilities.formatDate(new Date(), CONFIG.TIMEZONE, 'yyyy-MM-dd');

  if (queryDate !== today) {
    Logger.log('[경고] 쿼리 날짜 불일치: ' + queryDate + ' vs 오늘: ' + today);
    // Slack 경고 알림 발송
    postSlackWarning('쿼리 날짜 불일치: 데이터가 최신이 아닐 수 있습니다.');
  }

  // ... 처리 계속
}
```

### 12.3 핵심 컬럼 인덱스

| 컬럼 | 인덱스 | 열 | 용도 |
|------|--------|-----|------|
| `query_executed_at` | 24 | Y열 | 쿼리 실행 날짜 |
| `reorder_qty` | 27 | AB열 | 리오더 수량 |

**결론: ✅ 데이터 신선도 검증으로 운영 안정성 향상**

---

## 13. Design Decision #10: 예측 기간 로직 (v1.2 → v1.7 개선)

### 13.1 배경
- 초기 리오더(초도~4차)는 상품 검증 기간
- 기존: 5차+ 무조건 21일 → 잘 안 팔리는 상품도 3주 예측하여 과재고 위험
- v1.7: SPV 기반으로 전환, 시즌 말 강제 14일 추가

### 13.2 구현 (v1.7+)
```sql
-- 예측 기간 결정 (우선순위 순)
CASE
  WHEN s.reorder_order <= 4 THEN 14                              -- 1순위: 초도~4차
  WHEN DATE_DIFF(SEASON_END, CURRENT_DATE(), DAY) <= 30 THEN 14 -- 2순위: 시즌 말
  WHEN IFNULL(SAFE_DIVIDE(s.sku_spv_past_14d, b.avg_category_spv), 0) > HIGH_SPV_MULTIPLIER THEN 21  -- 3순위: SPV>1.3
  ELSE 14                                                        -- 4순위: 기본값
END AS forecast_days
```

### 13.3 수량 상한 (초도~4차)

| 조건 | 상한 | 비고 |
|------|------|------|
| 일반 상품 | 10장 | 검증 기간 |
| High-SPV (`relative_spv_index > 1.3`) AND 빠른 판매 (`sales_past_7_days >= 7`) | 무제한 | 고효율 상품 |

### 13.4 설계 원칙

```
┌─────────────────────────────────────────────────────────────────┐
│  예측 기간 전략 (v1.7+)                                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1순위: 초도~4차 → 14일                                        │
│    - 수량 상한: 10장 (예외 조건 충족 시 해제)                   │
│    - 목적: 신상품 과재고 방지                                   │
│                                                                 │
│  2순위: 시즌 전환기 (초/말 30일) → 14일                        │
│    - 목적: 시즌 전환기 과재고 방지 (이전 시즌 상품 포함)       │
│                                                                 │
│  3순위: SPV > 1.3배 → 21일                                     │
│    - 목적: 고효율 상품만 3주 예측 허용                          │
│                                                                 │
│  4순위: 그 외 → 14일                                           │
│    - 변경: 기존 5차+ 21일 → 14일 (보수적)                      │
│                                                                 │
│  예외 조건 (수량 상한 해제, 초도~4차만)                         │
│    - High-SPV: relative_spv_index > 1.3                         │
│    - 빠른 판매: sales_past_7_days >= 7                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**결론: ✅ SPV 기반 예측 + 시즌 전환기 강제로 과재고 방지 강화**

---

## 14. Design Decision #11: Price Down 상품 제외 (v1.4 → CTE 이전)

### 14.1 배경
- pb_price_down 프로젝트에서 시즌오프 시 악성재고 할인 판매
- 할인 후 일시적 판매량 증가 → 리오더 시스템이 "좋은 상품"으로 오인
- **문제**: 할인 처리된 상품이 리오더 대상이 되면 안 됨

### 14.2 이전 구현 (Apps Script, 제거됨)

- `getExcludedPbCodes()`: pb_price_down 스프레드시트 history 탭 조회
- `extractPbCode()`: product_item_code에서 pb_code 추출
- 제외 조건: E/F등급 OR 최근 60일 할인이력
- **단점**: 외부 스프레드시트 의존, 느린 실행, 로직 분산

### 14.3 현재 구현 (BigQuery CTE, 2026-02-05~)

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

**적용 위치**: `current_product_status` CTE
```sql
WHERE NOT EXISTS (
  SELECT 1 FROM price_down_excluded pd WHERE pd.item_id = pi.product_id
)
```

### 14.4 제외 조건 변경

| 항목 | 이전 (Apps Script) | 현재 (BigQuery CTE) |
|------|-------------------|-------------------|
| 데이터 소스 | pb_price_down Google Sheets | `damoa-lake.pb1_owned.price_down_history_sheet` |
| 제외 기준 | E/F등급 OR 60일 할인이력 | 시즌오프 Price Down API 성공 기록 (`POST`, `DELETE→POST`) |
| 적용 시점 | Apps Script 실행 시 | BigQuery 쿼리 실행 시 |
| 시즌오프 판별 | 없음 (항상 적용) | 1~2월 FW / 7~8월 SS만 적용 |

### 14.5 시즌오프 동작

| 현재 월 | 제외 대상 시즌 | `__product_season__` 매칭 |
|---------|--------------|-------------------------|
| 1~2월 | F/W 시즌 상품 | `%FW` |
| 7~8월 | S/S 시즌 상품 | `%SS` |
| 3~6월, 9~12월 | 없음 | `NO_MATCH_NOT_SEASON_OFF` |

**결론: ✅ BigQuery CTE로 이전하여 외부 의존성 제거, 로직 일원화**

---

## 15. Design Decision #12: 쿼리 성능 최적화 (v1.5)

### 15.1 문제점
- 카테고리 기반 Monte Carlo로 데이터 풀 확장 후 쿼리 성능 저하
- CROSS JOIN으로 인한 대량 행 생성 (products × dates × context groups)
- 불필요한 context group까지 Monte Carlo 계산 수행

### 15.2 최적화 1: 동적 날짜 범위 (372일)

**기존:**
```sql
DECLARE START_DATE DATE DEFAULT '2023-01-01';  -- 고정 ~730일
```

**변경:**
```sql
DECLARE START_DATE DATE DEFAULT DATE_SUB(CURRENT_DATE(), INTERVAL 372 DAY);  -- 동적 1년+1주
```

**효과:**
- 날짜 범위 49% 감소 (730일 → 372일)
- 1년 이상의 시즌성 데이터 확보
- 불필요한 오래된 데이터 제외

### 15.3 최적화 2: Context 사전 필터링

**목적:** 타겟 상품에 필요한 context group만 Monte Carlo 계산

**구현:**
```sql
-- 타겟 상품의 context group 추출
target_context_groups AS (
  SELECT DISTINCT
    product_type,
    base_category_name,
    decision_isoweek,
    sales_past_7_days_bin,
    sales_past_14_days_bin
  FROM current_product_status
  WHERE base_category_name != 'No Category'
),

-- context_group_stats에서 EXISTS 필터 추가
context_group_stats AS (
  SELECT
    h.product_type,
    h.base_category_name,
    h.decision_isoweek,
    h.sales_past_7_days_bin,
    h.sales_past_14_days_bin,
    APPROX_QUANTILES(h.daily_quantity, 100)[OFFSET(50)] AS median_daily_sales,
    STDDEV(h.daily_quantity) AS stddev_daily_sales
  FROM historical_performance_with_context h
  WHERE h.sales_past_14_days_bin IS NOT NULL
    AND EXISTS (
      SELECT 1 FROM target_context_groups t
      WHERE t.product_type = h.product_type
        AND t.base_category_name = h.base_category_name
        AND t.decision_isoweek = h.decision_isoweek
        AND t.sales_past_7_days_bin = h.sales_past_7_days_bin
        AND t.sales_past_14_days_bin = h.sales_past_14_days_bin
    )
  GROUP BY 1, 2, 3, 4, 5
  HAVING COUNT(h.item_id) >= 14
),
```

**효과:**
- 전체 context group 대신 필요한 것만 계산
- Monte Carlo CROSS JOIN 행 수 대폭 감소 (예상 90%+)
- 쿼리 실행 시간 단축

### 15.4 적용 버전

| 브랜드 | 이전 버전 | 최적화 버전 |
|--------|-----------|-------------|
| Noir | v1.4 | v1.5 |
| Queens | v1.3 | v1.4 |
| Verda | v1.3 | v1.4 |
| Zizae | v1.4 | v1.5 |
| Dana&Peta | v1.3 | v1.4 |

**결론: ✅ 372일 동적 날짜 + Context 필터링으로 쿼리 성능 대폭 개선**

---

## 16. Design Decision #13: COMPLETED 상태 제외 (v1.6/v1.5)

### 16.1 문제점

`reserved_qty_by_sku` CTE에서 `delivery_state` 필터링 시 COMPLETED 상태 누락:

```sql
-- 기존 (v1.5/v1.4)
AND ol.delivery_state NOT IN ('SHIPPED', 'DELIVERED', 'CANCELLED')
```

**문제**: COMPLETED는 배송 완료 상태이므로 reserved에서 제외되어야 함. 배송 완료된 주문이 reserved_qty에 포함되면 가용재고가 과소 계산됨.

### 16.2 해결책

```sql
-- 수정 (v1.6/v1.5)
AND ol.delivery_state NOT IN ('SHIPPED', 'DELIVERED', 'CANCELLED', 'COMPLETED')
```

### 16.3 delivery_state 상태 정리

| 상태 | 의미 | Reserved 제외 |
|------|------|---------------|
| SHIPPED | 출고됨 | ✅ 제외 |
| DELIVERED | 배송됨 | ✅ 제외 |
| CANCELLED | 취소됨 | ✅ 제외 |
| COMPLETED | 배송완료 | ✅ 제외 (v1.6 추가) |
| (기타) | 미출고 | ❌ Reserved에 포함 |

### 16.4 적용 버전

| 브랜드 | 이전 버전 | 수정 버전 |
|--------|-----------|-----------|
| Noir | v1.5 | v1.6 |
| Queens | v1.4 | v1.5 |
| Verda | v1.4 | v1.5 |
| Zizae | v1.5 | v1.6 |
| Dana&Peta | v1.4 | v1.5 |

**결론: ✅ COMPLETED 상태 제외로 reserved_qty 정확도 향상**

---

## 17. Design Decision #14: 보수적 발주 로직 (v1.6)

### 17.1 배경

- 출시 후 오래 지난 상품이 최소 발주량(5장)으로 계속 추천됨
- 이런 상품은 수요가 낮아 추가 발주 시 과재고 위험

### 17.2 해결책

**조건:**
- 출시일로부터 70일(10주) 이상 경과
- 추천 수량이 정확히 5장 (최소 MOQ)

**처리:**
- 해당 조건 충족 시 추천 수량을 0장으로 변경

### 17.3 구현

```sql
-- days_since_launch 계산 (current_product_status CTE)
DATE_DIFF(CURRENT_DATE(), DATE(p.created_at), DAY) AS days_since_launch,

-- 보수적 발주 로직 (final SELECT)
CASE
  WHEN IFNULL(f.days_since_launch, 0) >= 70
    AND (CASE WHEN f.apply_qty_cap THEN LEAST(f.raw_forecast, REORDER_QTY_CAP) ELSE f.raw_forecast END) = 5
  THEN 0
  ELSE CASE WHEN f.apply_qty_cap THEN LEAST(f.raw_forecast, REORDER_QTY_CAP) ELSE f.raw_forecast END
END AS normal_forecast,

-- product_type에 출시일수 포함
CONCAT(f.product_type, '(', CAST(IFNULL(f.days_since_launch, 0) AS STRING), '일)') AS product_type,
```

### 17.4 출력 형식

기존 컬럼 구조를 유지하면서 출시일수 정보를 제공하기 위해 `product_type` 컬럼에 일수를 통합:

| 기존 | 변경 후 |
|------|---------|
| 기존상품 | 기존상품(85일) |
| 신상품 | 신상품(15일) |

**장점:**
- 별도 컬럼 추가 없이 정보 제공
- 기존 28컬럼 구조 유지
- Apps Script 수정 불필요

**결론: ✅ 장기 재고 상품의 과재고 방지**

---

## 18. Design Decision #15: extractPbCode 정규식 개선 (v1.6)

### 18.1 배경

기존 `extractPbCode()` 함수는 underscore 기반 분할 방식을 사용:
- `'NR25F001_BLACK_FREE'.split('_')[0]` → `'NR25F001'` ✅
- `'D2_VD25S001_WHITE_M'.split('_')[0]` → `'D2'` ❌ (prefix 있는 경우 실패)

### 18.2 해결책

정규식 패턴 매칭으로 변경:

```javascript
function extractPbCode(productItemCode) {
  // 정규식으로 pb_code 패턴 추출: {브랜드코드}{연도}{시즌}{3자리숫자}
  // 예: NR25F001, QU25S002, VD24W003, ZE25F001, DN25S001
  var pattern = /(NR|QU|VD|ZE|DN)\d{2}[A-Z]\d{3}/;
  var match = productItemCode.match(pattern);
  return match ? match[0] : null;
}
```

### 18.3 테스트 케이스

| 입력 | 기존 결과 | 정규식 결과 |
|------|-----------|-------------|
| NR25F001_BLACK_FREE | NR25F001 ✅ | NR25F001 ✅ |
| D2_VD25S001_WHITE_M | D2 ❌ | VD25S001 ✅ |
| QU25S002-RED-L | QU25S002-RED-L ❌ | QU25S002 ✅ |

**결론: ✅ Price Down CTE 이전으로 해당 함수 제거됨 (2026-02-05). 이 섹션은 참고용으로 유지.**

---

## 19. Design Decision #16: Price Down 제외 기간 확장 (v1.6)

### 19.1 배경

기존 30일 제외 기간이 짧아 할인 효과 소멸 전 리오더 대상에 재진입하는 경우 발생

### 19.2 해결책

제외 기간을 30일 → 60일로 확장:

```javascript
// CONFIG 설정
var CONFIG = {
  ...
  EXCLUSION_DAYS: 60,  // 기존 30일 → 60일
  ...
};
```

**결론: ✅ Price Down CTE 이전으로 60일 기간 조건 대신 시즌오프 기반 제외로 변경됨 (2026-02-05). 이 섹션은 참고용으로 유지.**

---

## 20. Design Decision #17: Heuristics 계절성 가중치 (v1.7/v1.6)

### 20.1 배경

| 구분 | Statistics | Heuristics |
|------|------------|------------|
| 계절성 | ISO week 기반 그룹화 ✅ | 없음 ❌ |
| 1월(시즌 말) | 주차별 수요 감소 반영 | 단순 x2 배수 → 과재고 위험 |

**문제**: Heuristics가 시즌 말에도 최근 판매량의 단순 배수 적용 → 보수적 재고 관리 불가

### 20.2 해결책: Hybrid Approach

ISO week 기반 계절성 팩터 우선, 데이터 부족 시 시즌 진행도 감쇠로 폴백

**장점**:
- Statistics와 동일한 ISO week 기반 방법론 사용
- 데이터 부족 시에도 시즌 진행도로 안전하게 감쇠
- 카테고리별 계절 패턴 반영

### 20.3 구현

**새 파라미터**:
```sql
DECLARE MIN_ISOWEEK_SAMPLES INT64 DEFAULT 14;        -- ISO week factor 사용 최소 샘플
DECLARE SEASON_DECAY_RATE FLOAT64 DEFAULT 0.25;      -- 시즌 말 최대 감쇠율
DECLARE SEASONALITY_WEIGHT_MIN FLOAT64 DEFAULT 0.70; -- 계절성 가중치 하한
DECLARE SEASONALITY_WEIGHT_MAX FLOAT64 DEFAULT 1.50; -- 계절성 가중치 상한 (피크 시즌 반영)
```

**새 CTE (4개)**:
```sql
-- 1. 카테고리별 ISO week 통계
category_isoweek_stats AS (
  SELECT base_category_name, EXTRACT(ISOWEEK FROM dt) AS isoweek,
    SUM(quantity) AS total_sales, COUNT(DISTINCT dt) AS sample_days
  FROM category_daily_sales cds
  JOIN category_matched_products cmp ON cds.item_id = cmp.product_id
  GROUP BY 1, 2
),

-- 2. 카테고리 연간 베이스라인
category_annual_baseline AS (
  SELECT base_category_name,
    SAFE_DIVIDE(SUM(total_sales), SUM(sample_days)) AS avg_daily_sales
  FROM category_isoweek_stats GROUP BY 1
),

-- 3. ISO week 계절성 팩터
isoweek_seasonality AS (
  SELECT w.base_category_name, w.isoweek,
    CASE WHEN w.sample_days >= MIN_ISOWEEK_SAMPLES THEN
      LEAST(SEASONALITY_WEIGHT_MAX, GREATEST(SEASONALITY_WEIGHT_MIN,
        SAFE_DIVIDE(SAFE_DIVIDE(w.total_sales, w.sample_days), b.avg_daily_sales)))
    ELSE NULL END AS isoweek_factor
  FROM category_isoweek_stats w
  JOIN category_annual_baseline b ON w.base_category_name = b.base_category_name
),

-- 4. 시즌 진행도 감쇠 팩터 (폴백)
season_progress_factor AS (
  SELECT 1.0 - (SEASON_DECAY_RATE * SAFE_DIVIDE(
    DATE_DIFF(CURRENT_DATE(), SEASON_START, DAY),
    DATE_DIFF(SEASON_END, SEASON_START, DAY)
  )) AS decay_factor
),
```

**combined_forecasts 수정**:
```sql
-- 계절성 가중치 추가
COALESCE(isw.isoweek_factor, spf.decay_factor) AS seasonality_weight,
CASE WHEN isw.isoweek_factor IS NOT NULL THEN 'ISO Week' ELSE 'Season Progress' END AS seasonality_source

-- JOIN 추가
LEFT JOIN isoweek_seasonality isw ON s.base_category_name = isw.base_category_name
  AND s.decision_isoweek = isw.isoweek
CROSS JOIN season_progress_factor spf
```

**final_forecasts 수정**:
```sql
CAST(ROUND(CASE
  WHEN forecast_level = 'Heuristic (High-SPV)' THEN sales_past_7_days * 2 * seasonality_weight
  WHEN forecast_level = 'Statistical' THEN statistical_forecast  -- 변경 없음
  ELSE heuristic_forecast_base * spv_scale * seasonality_weight
END) AS INT64) AS raw_forecast
```

### 20.4 예상 효과 (1월 20일 기준)

**시즌 진행률**: 78% (142일/181일)

| 시나리오 | 기존 | 변경 후 | 감쇠율 |
|----------|------|---------|--------|
| ISO week 3 factor = 0.72 | 14개 | 10개 | -28% |
| 데이터 부족 (폴백) | 14개 | 11개 | -20% |

### 20.5 적용 버전

| 브랜드 | 이전 버전 | 새 버전 |
|--------|-----------|---------|
| Noir | v1.6 | v1.7 |
| Queens | v1.5 | v1.6 |
| Verda | v1.5 | v1.6 |
| Zizae | v1.6 | v1.7 |
| Dana&Peta | v1.5 | v1.6 |

### 20.6 자동 계산 메커니즘

ISO week factor는 쿼리 실행 시 자동 계산됨:

```sql
-- 4개 CTE 순차 계산
category_isoweek_stats     → 카테고리별 주차 판매 통계 (SUM, COUNT)
category_annual_baseline   → 카테고리 시즌 평균 (AVG)
isoweek_seasonality        → factor = (주차 평균) / (시즌 평균), CLAMP [0.70, 1.50]
season_progress_factor     → 폴백: 1.0 - (0.25 × 시즌 진행률)
```

**시즌 자동 감지**:
```sql
SEASON_START = CASE
  WHEN CURRENT_MONTH >= 9 THEN 9월 1일     -- F/W
  WHEN CURRENT_MONTH <= 2 THEN 전년 9월 1일 -- F/W 연속
  ELSE 3월 1일                              -- S/S
END
```

### 20.7 시즌별 계절성 팩터 비교 (BigQuery 분석 기반)

**F/W 시즌 (2025-2026)**:
| ISO Week | 시기 | Raw Factor | 적용 Factor |
|----------|------|------------|-------------|
| 34-35 | 8월 말 | 0.78 | 0.78 |
| 42-44 | 10월 | 1.01-1.11 | 1.01-1.11 |
| **45-47** | **11월 피크** | **1.51-1.62** | **1.50** (capped) |
| 2-3 | 1월 시즌말 | 0.77-0.84 | 0.77-0.84 |

**S/S 시즌 (2025)**:
| ISO Week | 시기 | Raw Factor | 적용 Factor |
|----------|------|------------|-------------|
| 10-13 | 3월 | 0.87-0.99 | 0.87-0.99 |
| **15-16** | **4월 피크** | **1.25-1.26** | **1.25-1.26** |
| 27-30 | 7월 | 1.02-1.13 | 1.02-1.13 |
| 31-35 | 8월 시즌말 | 0.79-0.93 | 0.79-0.93 |

**시즌별 요약**:
| 시즌 | 피크 Factor | 시즌말 Factor | MAX=1.50 충분? |
|------|-------------|---------------|----------------|
| F/W | 1.51-1.62 | 0.77-0.84 | ✅ (피크 약간 제한) |
| S/S | 1.25-1.26 | 0.79-0.89 | ✅ (제한 없음) |

**결론: ✅ 양방향 계절성 반영 (피크 시즌 증가 + 시즌 말 감소)**

---

## 21. Design Decision #18: 동적 차수 계산 및 시즌 품번 필터링 (v1.8/v1.7)

### 21.1 문제점

기존 `reorder_history` CTE는 현재 시즌(`SEASON_START ~ SEASON_END`) 내 입고 횟수만 카운트:

```sql
-- 기존: 시즌 범위 내만
COUNT(*) - 1 AS reorder_order
WHERE date BETWEEN SEASON_START AND SEASON_END
```

**문제**: 과년차 품번(예: `NR25F001`)이 새 시즌(26S/S)에 리오더될 때 차수가 0으로 리셋 → 이미 검증된 상품에 초도~4차 규칙(10장 상한, 14일 예측)이 다시 적용됨.

추가로, 4개 브랜드(Noir, Queens, Verda, Dana&Peta)의 `reorderable_products`에는 시즌/연도 필터가 없어 모든 품번이 리오더 대상에 포함되었음.

### 21.2 해결책

**변경 1: `PREV_SEASON_START` 파라미터 추가**

```sql
DECLARE PREV_SEASON_START DATE DEFAULT (
  CASE
    WHEN CURRENT_MONTH >= 9 THEN DATE(CURRENT_YEAR, 3, 1)       -- F/W → 직전 S/S
    WHEN CURRENT_MONTH <= 2 THEN DATE(CURRENT_YEAR - 1, 3, 1)   -- F/W(1~2월) → 직전 S/S
    ELSE DATE(CURRENT_YEAR - 1, 9, 1)                            -- S/S → 직전 F/W
  END
);
```

**변경 2: `reorderable_products` 시즌 필터링**

모든 브랜드에서 당시즌 + 직전 시즌 품번만 포함. 품번 5번째 자리 시즌코드와 3-4번째 자리 연도로 판별.

시즌코드: F/W/D (F/W), S/M/H (S/S)

**변경 3: `reorder_history` 동적 차수**

```sql
-- 현재+직전 시즌 스캔 (2개 시즌, 약 12개월)
WHERE date BETWEEN PREV_SEASON_START AND SEASON_END

-- 품번이 당시즌인지 판별
is_current_season_product = (품번 연도+시즌코드가 현재 시즌과 일치)

-- 동적 차수 결정
CASE
  WHEN is_current_season_product THEN season_reorder_order  -- 시즌 차수
  ELSE total_reorder_order                                   -- 누적 차수
END AS reorder_order
```

### 21.3 설계 의도

```
┌─────────────────────────────────────────────────────────────────┐
│  동적 차수 전략                                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  당시즌 품번 (is_current_season_product = TRUE):                │
│    → 시즌 차수 사용 (기존과 동일)                               │
│    → 초도~4차 보수적 규칙 적용                                  │
│                                                                 │
│  과년차/직전 시즌 품번 (is_current_season_product = FALSE):      │
│    → 누적 차수 사용 (리셋 방지)                                 │
│    → 이미 검증된 상품이므로 상한 해제                           │
│                                                                 │
│  리오더 대상 범위:                                               │
│    → 당시즌 + 직전 시즌 품번만 (2개 시즌)                       │
│    → 2시즌 이전 품번은 자동 제외                                │
│    → 성능: 약 12개월 스캔 (전체 히스토리 대비 제한적)           │
│                                                                 │
│  핵심 원칙: 검증된 상품은 보수적 제약 면제                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 21.4 적용 버전

| 브랜드 | 이전 버전 | 새 버전 |
|--------|-----------|---------|
| Noir | v1.7 | v1.7 (v1.8 태그) |
| Queens | v1.6 | v1.6 (v1.7 태그) |
| Verda | v1.6 | v1.6 (v1.7 태그) |
| Zizae | v1.7 | v1.7 (v1.8 태그) |
| Dana&Peta | v1.6 | v1.6 (v1.7 태그) |

**결론: ✅ 과년차 품번 차수 리셋 방지 + 2시즌 범위 품번 필터링으로 정확도 향상**

---

## 22. Change Log

| 날짜 | 버전 | 변경사항 |
|------|------|----------|
| 2026-02-05 | 5.2 | **Price Down CTE api_action 확장** - `'POST'` → `IN ('POST', 'DELETE→POST')`, 삭제 후 재등록 상품(163건)도 제외 대상에 포함 |
| 2026-02-05 | 5.1 | **Price Down CTE 이전** - Apps Script 제거, BigQuery `price_down_excluded` CTE로 이전, 시즌오프(1~2월 FW/7~8월 SS) 기반 제외, extractPbCode/getExcludedPbCodes 함수 제거, Marchmara 추가 |
| 2026-01-30 | 5.0 | **동적 차수+시즌 품번 필터링** - 품번 시즌코드 기반 당시즌/과년차 차수 판별, reorderable_products 당시즌+직전 시즌 필터, PREV_SEASON_START 추가 |
| 2026-01-30 | 4.9 | **시즌 전환기 확대** - 시즌 말 → 시즌 초/말 30일, 이전 시즌 상품 리오더 방지 |
| 2026-01-29 | 4.8 | **예측 기간 SPV 기반 전환** - 5차+ 무조건 21일 → SPV>1.3만 21일, 시즌 말 30일 14일 강제, 시즌 말 기존상품 10장 이하 발주 제외 |
| 2026-01-21 | 4.7 | **계절성 가중치 피크 시즌 반영** - SEASONALITY_WEIGHT_MAX 1.00 → 1.50 (피크 주차 50% 증가 허용), BigQuery 분석 기반 수정 |
| 2026-01-20 | 4.6 | **계절성 가중치 보수적 조정** - SEASONALITY_WEIGHT_MAX 1.20 → 1.00 (감소만 적용, 증가 없음), 과재고 방지 강화 |
| 2026-01-20 | 4.5 | **Heuristics 계절성 가중치 추가** - ISO week 팩터 + 시즌 진행도 폴백, 시즌 말 과재고 방지, 전 브랜드 쿼리 버전 업데이트 |
| 2026-01-15 | 4.4 | **Price Down 컬럼 인덱스 버그 수정** - rotation_grade: 19→18 (S열), discount_rate: 21→29 (AD열), 주석 30일→60일 정정 |
| 2026-01-14 | 4.3 | 보수적 발주 로직 (70일+/5장→0), extractPbCode 정규식 개선, Price Down 60일 확장, product_type 출시일수 표시 |
| 2026-01-12 | 4.2 | reserved_qty COMPLETED 상태 제외 버그 수정, 전 브랜드 쿼리 버전 업데이트 (Noir/Zizae v1.6, 나머지 v1.5) |
| 2026-01-12 | 4.1 | 쿼리 성능 최적화 (372일 동적 날짜, Context 사전 필터링), 전 브랜드 쿼리 버전 업데이트 |
| 2026-01-09 | 4.0 | 동적 시즌 계산, 쿼리 날짜 검증, 차수별 예측 로직, Price Down 제외 문서화 |
| 2026-01-08 | 3.3 | Price Down 상품 제외 로직 추가 |
| 2025-12-15 | 3.2 | Zizae, Dana&Peta 브랜드 추가 |
| 2025-12-10 | 3.1 | Queens 브랜드 코드 QU 확정, 전 브랜드 Production 상태 |
| 2025-12-10 | 3.0 | Queens/Verda 쿼리 추가, Master Table 우회 전략 문서화 |
| 2025-12-10 | 2.0 | v2.9/v2.10 결정사항 추가, 문서 구조 개선 |
| 2025-12-10 | 1.2 | Reserved v2.3 AI 리뷰 결과 추가 |
| 2025-12-10 | 1.1 | SPV Threshold Option B 확정, AI 피드백 반영 |
| 2025-12-09 | 1.0 | 초기 문서 작성, AI 리뷰 결과 정리 |
