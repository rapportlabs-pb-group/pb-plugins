# 브랜드별 설정 가이드

> **Version:** 8.2 (2026-02-04)
> **Status:** Multi-Brand Production Ready (Noir, Queens Selection, Verda, Zizae, Dana & Peta, Marchmara)

## 1. 개요

리오더 시스템은 브랜드 독립적인 핵심 로직과 브랜드별 설정으로 분리됩니다.
이 문서는 각 브랜드별 설정 항목을 정의합니다.

---

## 2. 브랜드 현황

| 브랜드 | 코드 | SKU 수 | 재고 수량 | 상태 | 시트 |
|--------|------|--------|-----------|------|------|
| **노어 (Noir)** | NR | 2,528 | 21,040 | Production | [Link](https://docs.google.com/spreadsheets/d/1q0CsxQXe3W-Y6xDcgNY-uT1oBDH_IZgrK-Gm7uTl8YE) |
| **퀸즈셀렉션** | QU | 8 | 111 | Production | [Link](https://docs.google.com/spreadsheets/d/1CqbglHwEFrQzYUPA4oHyrv7doG3pAtE3tUs68wfaN4w) |
| **베르다 (Verda)** | VD | 312 | 2,430 | Production | [Link](https://docs.google.com/spreadsheets/d/1Z8S1gl1bjc0YaQmIQU3_QhvpA8xxCEYHtedMuOM2wco) |
| **지재 (Zizae)** | ZE | TBD | TBD | Production | [Link](https://docs.google.com/spreadsheets/d/1MDEQrx_o9YqFmwbiSTDYiG4cJ0tvBpXuUiIYXog15AI) |
| **다나앤페타 (Dana & Peta)** | DN | TBD | TBD | Production | [Link](https://docs.google.com/spreadsheets/d/1JkTrLc7uhEfMpHIFUZ2EvwFy3Kp76AGa-h9pagPwz5k) |
| **마치마라 (Marchmara)** | MM | TBD | TBD | Production | [Link](https://docs.google.com/spreadsheets/d/11tIOjKJ0WKvUcMh8M6Z2TpOdU3n9JkO71ukoDPuzPRY) |

---

## 3. 노어 (NOIR) - Production

### 3.1 데이터 소스 설정
```yaml
brand: noir
brand_code: NR
brand_name: 노어

# 테이블 설정
master_table: damoa-lake.pb2_owned.noor_master
stock_table: damoa-lake.logistics_owned.stockDetail_raw
transaction_table: damoa-lake.logistics_owned.daily_inventory_transaction  # 리오더 차수 계산
product_table: damoa-lake.ms_product.product_item
order_table: damoa-lake.ms_order.order_line
estimate_table: damoa-lake.ms_order.order_shipment_estimate
funnel_table: damoa-mart.biz_analytics.product_funnel_daily

# 시트 설정
spreadsheet_id: 1q0CsxQXe3W-Y6xDcgNY-uT1oBDH_IZgrK-Gm7uTl8YE
raw_reorder_tab: raw_reorder
reorder_log_tab: 5.2 리오더 내역
archive_tab: reorder_archive
```

### 3.2 파라미터 설정
```yaml
# 가용 재고 계산
lead_time_days: 14
reserved_threshold_days: 3

# SPV 임계값
relative_spv_threshold_new: 0.30      # 신상품
relative_spv_threshold_existing: 0.65  # 기존상품
high_spv_multiplier: 1.3

# 휴리스틱 파라미터
heuristic_days: 14
heuristic_spv_min: 0.90
heuristic_spv_max: 1.10

# MOQ
moq_unit: 5
```

### 3.3 자동화 설정
```yaml
# Google Apps Script v1.7
execution_days: [1, 2, 3, 4, 5]  # 월~금
skip_days: [0, 6]               # 일/토
trigger_time: "10:00"

# 컬럼 설정 (30 columns total)
query_executed_at_column: 26    # AA열 (0-based)
seasonality_weight_column: 27   # AB열 (0-based)
seasonality_source_column: 28   # AC열 (0-based)
reorder_qty_column: 29          # AD열 (0-based)

# Price Down 제외 컬럼 (pb_price_down history 시트)
col_rotation_grade: 18          # S열 (0-based) - E/F 등급 체크
col_discount_rate: 29           # AD열 (0-based) - 할인율 체크

# Slack 알림
slack_channel: C0ABHFXMLP5
```

### 3.4 예측 기간 로직 (v1.2+ → v1.7+ 개선)
```yaml
# 예측 기간 결정 (우선순위 순)
forecast_days_logic:
  priority_1: reorder_order <= 4 → 14일       # 초도~4차
  priority_2: 시즌 초/말 30일 이내 → 14일      # 시즌 전환기 강제
  priority_3: relative_spv_index > 1.3 → 21일 # 고효율 상품만
  priority_4: 그 외 → 14일                    # 기본값

# 수량 상한 (초도~4차)
qty_cap_early: 10              # 기본 상한
high_spv_threshold: 1.3        # 상한 해제 조건 1
high_sales_threshold: 7        # 상한 해제 조건 2

# 시즌 전환기 보수적 발주
season_transition_cutoff: 30   # 시즌 초/말 30일 이내
season_transition_min_qty: 10  # 기존상품 10장 이하 → 발주 제외
season_transition_exclude_new: false  # 신상품은 제외 안 함
# 시즌 초 포함 이유: 시즌 전환 시 이전 시즌 상품 리오더 방지

# 동적 시즌 계산
season_calculation: dynamic    # 현재 월 기준 자동 판별

# 시즌 품번 필터링 (v1.8/v1.7)
reorderable_scope: current_and_previous_season  # 당시즌 + 직전 시즌
season_codes_fw: ['F', 'W', 'D']               # F/W 시즌코드
season_codes_ss: ['S', 'M', 'H']               # S/S 시즌코드

# 동적 차수 계산 (v1.8/v1.7)
reorder_order_mode: dynamic    # 당시즌 품번=시즌 차수, 과년차=누적 차수
reorder_order_scan: 2_seasons  # 현재+직전 시즌 (2개)
```

---

## 4. 퀸즈셀렉션 (Queens Selection) - Production

### 4.1 데이터 소스 설정
```yaml
brand: queens
brand_code: QU
brand_name: 퀸즈셀렉션

# 테이블 설정
master_table: damoa-lake.pb2_owned.queens_master
stock_table: damoa-lake.logistics_owned.stockDetail_raw
product_table: damoa-lake.ms_product.product_item
order_table: damoa-lake.ms_order.order_line
estimate_table: damoa-lake.ms_order.order_shipment_estimate
funnel_table: damoa-mart.biz_analytics.product_funnel_daily

# 시트 설정
spreadsheet_id: 1CqbglHwEFrQzYUPA4oHyrv7doG3pAtE3tUs68wfaN4w
raw_reorder_tab: raw_reorder
reorder_log_tab: 5.2 리오더 내역
archive_tab: reorder_archive
```

### 4.2 파라미터 설정
```yaml
# 가용 재고 계산 (노어와 동일)
lead_time_days: 14
reserved_threshold_days: 3

# SPV 임계값 (노어와 동일)
relative_spv_threshold_new: 0.30
relative_spv_threshold_existing: 0.65
high_spv_multiplier: 1.3

# 휴리스틱 파라미터
heuristic_days: 14
heuristic_spv_min: 0.90
heuristic_spv_max: 1.10

# MOQ
moq_unit: 5
```

### 4.3 자동화 설정
```yaml
# Google Apps Script v1.4
execution_days: [1, 2, 3, 4, 5]
skip_days: [0, 6]
trigger_time: "10:00"

# Price Down 제외 컬럼 (pb_price_down history 시트)
col_rotation_grade: 18          # S열 (0-based) - E/F 등급 체크
col_discount_rate: 29           # AD열 (0-based) - 할인율 체크

# Slack 알림
slack_channel: C0ABHFXMLP5
```

---

## 5. 베르다 (Verda) - Production

### 5.1 데이터 소스 설정
```yaml
brand: verda
brand_code: VD
brand_name: 베르다

# 테이블 설정
master_table: damoa-lake.pb2_owned.verda_master
stock_table: damoa-lake.logistics_owned.stockDetail_raw
product_table: damoa-lake.ms_product.product_item
order_table: damoa-lake.ms_order.order_line
estimate_table: damoa-lake.ms_order.order_shipment_estimate
funnel_table: damoa-mart.biz_analytics.product_funnel_daily

# 시트 설정
spreadsheet_id: 1Z8S1gl1bjc0YaQmIQU3_QhvpA8xxCEYHtedMuOM2wco
raw_reorder_tab: raw_reorder
reorder_log_tab: 5.2 리오더 내역
archive_tab: reorder_archive
```

### 5.2 파라미터 설정
```yaml
# 가용 재고 계산 (노어와 동일)
lead_time_days: 14
reserved_threshold_days: 3

# SPV 임계값 (노어와 동일)
relative_spv_threshold_new: 0.30
relative_spv_threshold_existing: 0.65
high_spv_multiplier: 1.3

# 휴리스틱 파라미터
heuristic_days: 14
heuristic_spv_min: 0.90
heuristic_spv_max: 1.10

# MOQ
moq_unit: 5
```

### 5.3 자동화 설정
```yaml
# Google Apps Script v1.4
execution_days: [1, 2, 3, 4, 5]
skip_days: [0, 6]
trigger_time: "10:00"

# Price Down 제외 컬럼 (pb_price_down history 시트)
col_rotation_grade: 18          # S열 (0-based) - E/F 등급 체크
col_discount_rate: 29           # AD열 (0-based) - 할인율 체크

# Slack 알림
slack_channel: C0ABHFXMLP5
```

---

## 6. 지재 (Zizae) - Production

### 6.1 데이터 소스 설정
```yaml
brand: zizae
brand_code: ZE
brand_name: 지재

# 테이블 설정 (pb1_owned - 다른 브랜드와 다름)
master_table: damoa-lake.pb1_owned.zizae_master
stock_table: damoa-lake.logistics_owned.stockDetail_raw
product_table: damoa-lake.ms_product.product_item
order_table: damoa-lake.ms_order.order_line
estimate_table: damoa-lake.ms_order.order_shipment_estimate
funnel_table: damoa-mart.biz_analytics.product_funnel_daily

# 시트 설정
spreadsheet_id: 1MDEQrx_o9YqFmwbiSTDYiG4cJ0tvBpXuUiIYXog15AI
raw_reorder_tab: raw_reorder
reorder_log_tab: 5.2 리오더 내역
archive_tab: reorder_archive
```

### 6.2 파라미터 설정
```yaml
# 가용 재고 계산 (노어와 동일)
lead_time_days: 14
reserved_threshold_days: 3

# SPV 임계값 (노어와 동일)
relative_spv_threshold_new: 0.30
relative_spv_threshold_existing: 0.65
high_spv_multiplier: 1.3

# 휴리스틱 파라미터
heuristic_days: 14
heuristic_spv_min: 0.90
heuristic_spv_max: 1.10

# MOQ
moq_unit: 5
```

### 6.3 자동화 설정
```yaml
# Google Apps Script v1.4
execution_days: [1, 2, 3, 4, 5]
skip_days: [0, 6]
trigger_time: "10:00"

# 컬럼 설정 (다른 브랜드와 다름)
raw_reorder_qty_column: AF  # 31 (0-based)
reorder_log_qty_column: AA  # 26 (0-based)

# Price Down 제외 컬럼 (pb_price_down history 시트)
col_rotation_grade: 18          # S열 (0-based) - E/F 등급 체크
col_discount_rate: 29           # AD열 (0-based) - 할인율 체크

# Slack 알림
slack_channel: C0ABHFXMLP5
slack_subteam: S046U1R861E  # 지재 전용 그룹
```

### 6.4 지재 전용 특징
```yaml
# Monte Carlo 예측 (조건별)
forecast_periods: [14, 21]  # 기본 14일, SPV>1.3만 21일

# target_products 최적화
target_products_scope: all_active  # 전체 활성 상품 기반 Monte Carlo

# Brand 필터
stock_filter: barcode_join  # Brand 필터 없이 barcode JOIN
```

---

## 7. 다나앤페타 (Dana & Peta) - Production

### 7.1 데이터 소스 설정
```yaml
brand: danapeta
brand_code: DN
brand_name: 다나앤페타

# 테이블 설정 (pb1_owned - 지재와 동일)
master_table: damoa-lake.pb1_owned.dana_master
stock_table: damoa-lake.logistics_owned.stockDetail_raw
product_table: damoa-lake.ms_product.product_item
order_table: damoa-lake.ms_order.order_line
estimate_table: damoa-lake.ms_order.order_shipment_estimate
funnel_table: damoa-mart.biz_analytics.product_funnel_daily

# 시트 설정
spreadsheet_id: 1JkTrLc7uhEfMpHIFUZ2EvwFy3Kp76AGa-h9pagPwz5k
raw_reorder_tab: raw_reorder
reorder_log_tab: 5.2 리오더 내역
archive_tab: reorder_archive
```

### 7.2 파라미터 설정
```yaml
# 가용 재고 계산 (노어와 동일)
lead_time_days: 14
reserved_threshold_days: 3

# SPV 임계값 (노어와 동일)
relative_spv_threshold_new: 0.30
relative_spv_threshold_existing: 0.65
high_spv_multiplier: 1.3

# 휴리스틱 파라미터
heuristic_days: 14
heuristic_spv_min: 0.90
heuristic_spv_max: 1.10

# MOQ
moq_unit: 5
```

### 7.3 자동화 설정
```yaml
# Google Apps Script v1.3
execution_days: [1, 2, 3, 4, 5]
skip_days: [0, 6]
trigger_time: "10:00"

# 컬럼 설정 (지재와 동일)
raw_reorder_qty_column: AF  # 31 (0-based)
reorder_log_qty_column: AA  # 26 (0-based)

# Price Down 제외 컬럼 (pb_price_down history 시트)
col_rotation_grade: 18          # S열 (0-based) - E/F 등급 체크
col_discount_rate: 29           # AD열 (0-based) - 할인율 체크

# Slack 알림
slack_channel: C0ABHFXMLP5
slack_subteam: S03VBFWTK40  # 다나앤페타 전용 그룹
```

### 7.4 다나앤페타 전용 특징
```yaml
# Monte Carlo 예측 (조건별 - 지재와 동일)
forecast_periods: [14, 21]  # 기본 14일, SPV>1.3만 21일

# target_products 최적화
target_products_scope: all_active  # 전체 활성 상품 기반 Monte Carlo

# Brand 필터
stock_filter: barcode_join  # Brand 필터 없이 barcode JOIN
```

---

## 8. 마치마라 (Marchmara) - Production

### 8.1 데이터 소스 설정
```yaml
brand: marchmara
brand_code: MM
brand_name: 마치마라

# 테이블 설정 (pb1_owned - 지재와 동일)
master_table: damoa-lake.pb1_owned.marchmara_master
stock_table: damoa-lake.logistics_owned.stockDetail_raw
product_table: damoa-lake.ms_product.product_item
order_table: damoa-lake.ms_order.order_line
estimate_table: damoa-lake.ms_order.order_shipment_estimate
funnel_table: damoa-mart.biz_analytics.product_funnel_daily

# 시트 설정
spreadsheet_id: 11tIOjKJ0WKvUcMh8M6Z2TpOdU3n9JkO71ukoDPuzPRY
raw_reorder_tab: raw_reorder
reorder_log_tab: 5.2 리오더 내역
archive_tab: reorder_archive
```

### 8.2 파라미터 설정
```yaml
# 가용 재고 계산 (노어와 동일)
lead_time_days: 14
reserved_threshold_days: 3

# SPV 임계값 (노어와 동일)
relative_spv_threshold_new: 0.30
relative_spv_threshold_existing: 0.65
high_spv_multiplier: 1.3

# 휴리스틱 파라미터
heuristic_days: 14
heuristic_spv_min: 0.90
heuristic_spv_max: 1.10

# MOQ
moq_unit: 5
```

### 8.3 자동화 설정
```yaml
# Google Apps Script v1.4
execution_days: [1, 2, 3, 4, 5]
skip_days: [0, 6]
trigger_time: "10:00"

# 컬럼 설정 (지재와 동일)
raw_reorder_qty_column: AF  # 31 (0-based)
reorder_log_qty_column: AA  # 26 (0-based)

# Price Down 제외 컬럼 (pb_price_down history 시트)
col_rotation_grade: 18          # S열 (0-based) - E/F 등급 체크
col_discount_rate: 29           # AD열 (0-based) - 할인율 체크

# Slack 알림
slack_channel: C0ABHFXMLP5
slack_subteam: S079XANPUKE  # 마치마라 전용 그룹
```

### 8.4 마치마라 전용 특징
```yaml
# Monte Carlo 예측 (조건별 - 지재와 동일)
forecast_periods: [14, 21]  # 기본 14일, SPV>1.3만 21일

# target_products 최적화
target_products_scope: all_active  # 전체 활성 상품 기반 Monte Carlo

# Brand 필터
stock_filter: barcode_join  # Brand 필터 없이 barcode JOIN
```

---

## 9. 브랜드 비교

| 항목 | Noir | Queens Selection | Verda | Zizae | Dana & Peta | Marchmara |
|------|------|------------------|-------|-------|-------------|-----------|
| **브랜드 코드** | NR | QU | VD | ZE | DN | MM |
| **마스터 테이블** | pb2_owned.noor_master | pb2_owned.queens_master | pb2_owned.verda_master | pb1_owned.zizae_master | pb1_owned.dana_master | pb1_owned.marchmara_master |
| **SKU 수** | 2,528 | 8 | 312 | TBD | TBD | TBD |
| **재고 테이블** | stockDetail_raw | stockDetail_raw | stockDetail_raw | stockDetail_raw | stockDetail_raw | stockDetail_raw |
| **재고 필터** | Brand=NR | Brand=QU | Brand=VD | barcode JOIN | barcode JOIN | barcode JOIN |
| **예약 배송** | 지원 | 지원 | 지원 | 지원 | 지원 | 지원 |
| **리드타임** | 14일 | 14일 | 14일 | 14일 | 14일 | 14일 |
| **MOQ** | 5개 | 5개 | 5개 | 5개 | 5개 | 5개 |
| **Monte Carlo** | 14/21일 | 14/21일 | 14/21일 | 14/21일 | 14/21일 | 14/21일 |
| **쿼리 버전** | v1.7 | v1.6 | v1.6 | v1.7 | v1.6 | v1.7 |
| **Apps Script** | v1.7 | v1.4 | v1.4 | v1.4 | v1.3 | v1.4 |
| **clasp 경로** | `apps_scripts/noir/` | `apps_scripts/queens/` | `apps_scripts/verda/` | `apps_scripts/zizae/` | `apps_scripts/danapeta/` | `apps_scripts/marchmara/` |
| **보수적 발주** | Yes | Yes | Yes | Yes | Yes | Yes |
| **출시일수 표시** | Yes | Yes | Yes | Yes | Yes | Yes |
| **동적 시즌** | Yes | Yes | Yes | Yes | Yes | Yes |
| **차수별 예측** | Yes | Yes | Yes | Yes | Yes | Yes |
| **상태** | Production | Production | Production | Production | Production | Production |

---

## 10. 핵심 공식 (공통)

### 10.1 가용 재고
```
available_stock = physical_stock + in_transit - reserved
```

| 구성요소 | 데이터 소스 | 설명 |
|----------|-------------|------|
| physical_stock | stockDetail_raw.avaliableStock | 현재 물리적 재고 |
| in_transit | 발주 로그 시트 | 14일 미입고 발주 |
| reserved | order_shipment_estimate | 3일+ 예약배송 |

### 10.2 발주량
```
reorder_qty = MAX(0, CEIL((forecast - available_stock) / MOQ) * MOQ)
```

---

## 11. 쿼리 파라미터 참조

모든 브랜드에서 동일한 쿼리 구조를 사용하며, 다음 파라미터만 브랜드별로 변경:

```sql
-- 브랜드별 변경 파라미터
DECLARE BRAND_CODE STRING DEFAULT 'NR';  -- NR, QU, VD, ZE, DN, MM
DECLARE BRAND_PREFIX STRING DEFAULT 'NR%';  -- NR%, QU%, VD%, ZE%, DN%, MM%

-- 공통 파라미터 (v1.5)
DECLARE START_DATE DATE DEFAULT DATE_SUB(CURRENT_DATE(), INTERVAL 372 DAY);  -- 동적 372일
DECLARE RELATIVE_SPV_THRESHOLD_NEW FLOAT64 DEFAULT 0.30;
DECLARE RELATIVE_SPV_THRESHOLD_EXISTING FLOAT64 DEFAULT 0.65;
DECLARE HIGH_SPV_MULTIPLIER FLOAT64 DEFAULT 1.3;
DECLARE RESERVED_DAYS_THRESHOLD INT64 DEFAULT 3;
DECLARE HEURISTIC_DAYS INT64 DEFAULT 14;
DECLARE HEURISTIC_SPV_MIN FLOAT64 DEFAULT 0.90;
DECLARE HEURISTIC_SPV_MAX FLOAT64 DEFAULT 1.10;
```

---

## 12. 주의사항

1. **테이블 권한**: BigQuery 테이블 접근 권한 확인 필수
2. **마스터 테이블**: Google Sheets 연동 테이블 - Drive 권한 필요
3. **stockDetail_raw**: 컬럼명 오타 주의 (`avaliableStock`)
4. **SKU 규모**: 퀸즈셀렉션은 SKU가 적어 통계적 예측 제한적
5. **평일 실행**: 모든 브랜드 월~금 실행, 주말 스킵
6. **회사 휴일**: 각 스프레드시트 `휴일` 탭(A열: 날짜)에 등록된 날짜에도 스킵

---

## 13. Apps Script 로컬 관리 (clasp)

**설치**: `npm install -g @google/clasp`

| 브랜드 | 경로 | 스크립트 ID | 메인 파일 |
|--------|------|-------------|-----------|
| Noir | `apps_scripts/noir/` | `1w2o3lMMg8L6W2jqMlcmp0zM2PeDcwT__WAUyE_I1T694p41BHQAVsteh` | `리오더 프로세스.js` |
| Queens | `apps_scripts/queens/` | `1P-nQhqNMFxrppylAxkJri0UyZzavFYQdO0qaHl45rwQRaUZT5lJ4MZ0G` | `리오더 프로세스.js` |
| Verda | `apps_scripts/verda/` | `1_BVbyssbAg2B_oJpomdSqPmwmH1c2oUKVshhMUIGlZTmigZrmXLb898S` | `리오더 프로세스.js` |
| Zizae | `apps_scripts/zizae/` | `1Xv4ibwuP-pRhBrWdxLqSsu1PNRBUr-5fzWg02ApdMDwMGzn5_8aaoSWx` | `리오더 프로세스.js` |
| Dana&Peta | `apps_scripts/danapeta/` | `1_Salygch4Or48hw_EuMV9c8smd1GjIONsBeOU-Ew0sU1-SzhAK0c688I` | `리오더 프로세스.js` |
| Marchmara | `apps_scripts/marchmara/` | `1fY-Zzgc-G1wOaugk_yIWlV_zb0dJ2w8IYf5ARo6uOEq41xmMGYnAlk8y` | `리오더 프로세스.js` |

**명령어**:
```bash
# 수정 후 배포
cd apps_scripts/{brand} && clasp push

# 최신 코드 가져오기
cd apps_scripts/{brand} && clasp pull

# 전체 브랜드 일괄 push
for d in noir queens verda zizae danapeta marchmara; do (cd apps_scripts/$d && clasp push); done
```

---

## 14. 변경 이력

| 날짜 | 버전 | 변경사항 |
|------|------|----------|
| 2026-02-04 | 8.2 | **회사 휴일 스킵 로직 추가** - 전 브랜드 `휴일` 시트 탭 기반, `isCompanyHoliday()` 함수 추가, 다나앤페타 Spreadsheet ID 수정 (`1JkTrLc7uhEfMpHIFUZ2EvwFy3Kp76AGa-h9pagPwz5k`), 2025~2026 공휴일+회사 방학 42개 데이터 입력 |
| 2026-02-03 | 8.1 | **Slack 설정 변경** - 전체 채널 C0ABHFXMLP5, 다나앤페타 subteam S03VBFWTK40, 마치마라 subteam S079XANPUKE |
| 2026-02-02 | 8.0 | **마치마라(Marchmara) 브랜드 추가** - pb1_owned.marchmara_master, v1.7 쿼리, v1.4 Apps Script, 지재와 동일 구성 |
| 2026-01-30 | 7.0 | **동적 차수+시즌 품번 필터링** - 품번 시즌코드 기반 당시즌/과년차 차수 판별, 당시즌+직전 시즌 품번만 리오더 대상, PREV_SEASON_START 추가 |
| 2026-01-30 | 6.9 | **시즌 전환기 확대** - 시즌 말 → 시즌 초/말 30일, 이전 시즌 상품 리오더 방지 |
| 2026-01-29 | 6.8 | **예측 기간 SPV 기반 전환** - 5차+ 무조건 21일 → SPV>1.3만 21일, 시즌 말 30일 14일 강제, 시즌 말 기존상품 10장 이하 발주 제외 |
| 2026-01-21 | 6.7 | **clasp 설정** - 전 브랜드 Apps Script 로컬 관리, 스크립트 ID 및 경로 문서화 |
| 2026-01-21 | 6.6 | **계절성 가중치 피크 시즌 반영** - SEASONALITY_WEIGHT_MAX 1.00 → 1.50, 피크 주차(F/W 11월, S/S 4월) 증가 허용, BigQuery 분석 기반 |
| 2026-01-20 | 6.5 | **Heuristics 계절성 가중치 추가** - ISO week 팩터 + 시즌 진행도 폴백, 컬럼 구조 28→30, 쿼리 버전 업데이트 (Noir/Zizae v1.7, 나머지 v1.6) |
| 2026-01-15 | 6.4 | **Price Down 컬럼 인덱스 버그 수정** - rotation_grade: 19→18 (S열), discount_rate: 21→29 (AD열), 주석 30일→60일 정정 |
| 2026-01-14 | 6.3 | 보수적 발주 로직 추가 (70일+/5장→0), Price Down 60일, extractPbCode 정규식, product_type 출시일수 표시 |
| 2026-01-12 | 6.2 | reserved_qty COMPLETED 상태 제외 버그 수정, 전 브랜드 쿼리 버전 업데이트 |
| 2026-01-12 | 6.1 | 쿼리 성능 최적화 (372일 동적 날짜, Context 사전 필터링), 전 브랜드 쿼리 버전 업데이트 |
| 2026-01-09 | 6.0 | 동적 시즌 계산, 쿼리 날짜 검증, 차수별 예측 로직 추가, 전 브랜드 업데이트 |
| 2026-01-08 | 5.1 | Price Down 제외 로직 추가 (E/F등급 + 할인이력) |
| 2025-12-15 | 5.0 | 다나앤페타(Dana & Peta) 브랜드 추가 (60/90일 Monte Carlo, barcode JOIN, 지재와 동일 방식) |
| 2025-12-12 | 4.0 | 지재(Zizae) 브랜드 추가 (60/90일 Monte Carlo, barcode JOIN, AF열 참조) |
| 2025-12-10 | 3.1 | Queens 브랜드 코드 QS→QU 수정, 전 브랜드 Production 상태로 업데이트, Slack 설정 통일 |
| 2025-12-10 | 3.0 | 퀸즈셀렉션, 베르다 브랜드 추가 |
| 2025-12-10 | 2.0 | Noir 설정 확정, 자동화 설정 추가 |
| 2025-12-09 | 1.0 | 초기 문서 작성 |
