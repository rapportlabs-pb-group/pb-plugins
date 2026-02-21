# PB 리오더 시스템

> **Version:** 5.0 (2026-02-03)
> **Status:** Multi-Brand Production Ready (6 Brands)

Monte Carlo 시뮬레이션 기반 수요 예측 및 자동 발주량 산출 시스템

## Installation (Claude Code Plugin)

```bash
# Add PB marketplace (one-time)
/plugin marketplace add rapportlabs-pb-group/pb-plugins

# Install
/plugin install pb-reorder-system@pb-plugins
```

### Skills

| Skill | Description |
|-------|-------------|
| `/reorder-status` | Check multi-brand reorder system status (versions, last update) |
| `/reorder-deploy` | Deploy Apps Script to all 6 brands via clasp |
| `/reorder-setup` | First-time setup guide (credentials, clasp, BigQuery) |

### Prerequisites

- Google Cloud project with BigQuery access
- Google Apps Script API enabled
- `clasp` CLI installed (`npm install -g @google/clasp`)
- `bq` CLI installed (Google Cloud SDK)

## 지원 브랜드

| 브랜드 | 코드 | SKU 수 | 쿼리 | Apps Script | 상태 |
|--------|------|--------|------|-------------|------|
| **노어 (Noir)** | NR | 2,528 | v1.7 | v1.7 | [Link](https://docs.google.com/spreadsheets/d/1q0CsxQXe3W-Y6xDcgNY-uT1oBDH_IZgrK-Gm7uTl8YE) |
| **퀸즈셀렉션** | QU | 8 | v1.6 | v1.4 | [Link](https://docs.google.com/spreadsheets/d/1CqbglHwEFrQzYUPA4oHyrv7doG3pAtE3tUs68wfaN4w) |
| **베르다 (Verda)** | VD | 312 | v1.6 | v1.4 | [Link](https://docs.google.com/spreadsheets/d/1Z8S1gl1bjc0YaQmIQU3_QhvpA8xxCEYHtedMuOM2wco) |
| **지재 (Zizae)** | ZE | TBD | v1.7 | v1.4 | [Link](https://docs.google.com/spreadsheets/d/1MDEQrx_o9YqFmwbiSTDYiG4cJ0tvBpXuUiIYXog15AI) |
| **다나앤페타 (Dana&Peta)** | DN | TBD | v1.6 | v1.3 | TBD |
| **마치마라 (Marchmara)** | MM | TBD | v1.7 | v1.4 | [Link](https://docs.google.com/spreadsheets/d/11tIOjKJ0WKvUcMh8M6Z2TpOdU3n9JkO71ukoDPuzPRY) |

## 핵심 공식

```
available_stock = physical_stock + in_transit - reserved
reorder_qty = MAX(0, forecast - available_stock)
```

## 주요 기능 (v4.0)

### 1. 차수별 예측 (Reorder Order Logic)
| 차수 | 예측 기간 | 수량 상한 | 비고 |
|------|----------|----------|------|
| 초도~4차 | 14일 | 10장 | 검증 중 |
| 5차+ | 21일 | 제한 없음 | 검증 완료 |

**예외 조건** (초도~4차 상한 해제):
- High-SPV: `relative_spv_index > 1.3`
- 판매 속도: `sales_past_7_days >= 7`

### 2. 동적 시즌 계산
현재 월 기준 자동 시즌 판별:
- **9~12월**: F/W 시즌 (09-01 ~ 02-28)
- **1~2월**: F/W 시즌 계속 (작년 09-01 ~ 올해 02-28)
- **3~8월**: S/S 시즌 (03-01 ~ 08-31)

### 3. Price Down 상품 제외
악성재고가 리오더 대상이 되는 것을 방지:
- E/F 등급 상품 제외
- 최근 60일 이내 할인 이력 상품 제외

### 5. 보수적 발주 로직 (v1.6+)
장기 재고 상품의 과재고 방지:
- 출시 70일(10주) 이상 + 추천 5장 → 0장 처리
- product_type에 출시일수 포함 (예: "기존상품(85일)")

### 4. 쿼리 날짜 검증 (v1.6+)
- `query_executed_at` 컬럼으로 쿼리 실행 날짜 확인
- 오늘 날짜와 불일치 시 Slack 경고 알림

## 프로젝트 구조

```
pb_reorder_system/
├── README.md                    # 프로젝트 개요 (이 파일)
├── CLAUDE.md                    # Claude Code 설정
├── progress.md                  # 개발 진행 상황
│
├── queries/                     # BigQuery SQL 쿼리
│   ├── noir_reorder_v1.7.sql    # Noir 리오더 쿼리
│   ├── queens_reorder_v1.6.sql  # Queens Selection 리오더 쿼리
│   ├── verda_reorder_v1.6.sql   # Verda 리오더 쿼리
│   ├── zizae_reorder_v1.7.sql   # Zizae 리오더 쿼리
│   ├── danapeta_reorder_v1.6.sql # Dana&Peta 리오더 쿼리
│   ├── marchmara_reorder_v1.7.sql # Marchmara 리오더 쿼리
│   └── pb1_reorder_v23.1.sql    # 레거시 PB1 쿼리 (참고용)
│
├── scripts/                     # Google Apps Script (백업)
│   ├── noir_reorder_apps_script.js     # Noir 자동화 (v1.7)
│   ├── queens_reorder_apps_script.js   # Queens 자동화 (v1.4)
│   ├── verda_reorder_apps_script.js    # Verda 자동화 (v1.4)
│   ├── zizae_reorder_apps_script.js    # Zizae 자동화 (v1.4)
│   ├── danapeta_reorder_apps_script.js # Dana&Peta 자동화 (v1.3)
│   └── marchmara_reorder_apps_script.js # Marchmara 자동화 (v1.4)
│
├── apps_scripts/                # clasp 관리 디렉토리
│   ├── noir/                    # Noir Apps Script
│   ├── queens/                  # Queens Apps Script
│   ├── verda/                   # Verda Apps Script
│   ├── zizae/                   # Zizae Apps Script
│   ├── danapeta/                # Dana&Peta Apps Script
│   └── marchmara/               # Marchmara Apps Script
│
└── docs/                        # 상세 문서
    ├── REORDER_SYSTEM.md        # 시스템 기술 문서
    ├── AVAILABLE_STOCK_DESIGN.md # 가용재고 설계 문서
    ├── QUERY_DESIGN_DECISIONS.md # 쿼리 설계 결정사항
    ├── BRAND_CONFIG.md          # 브랜드별 설정 가이드
    └── skills_guide.md          # 개발 스킬 가이드
```

## 기술 스택

- **BigQuery**: 데이터 웨어하우스, SQL 쿼리 실행
- **Google Apps Script**: 자동화 스크립트 (매일 10시 평일 실행)
- **Google Sheets**: 결과 출력, 발주 관리
- **Slack**: 알림 채널 (C0ABHFXMLP5)
- **Monte Carlo Simulation**: Mersenne Twister 알고리즘 기반 수요 예측

## 핵심 개념

| 개념 | 설명 |
|------|------|
| **SPV (Sales Per View)** | 조회당 판매율, 상품 효율성 지표 |
| **vendor_category** | 발주처 구분 (동대문, 해외 등) |
| **Reserved** | 예약 배송 수량 (3일+ 후 출고 예정) |
| **Monte Carlo Forecast** | 확률 분포 기반 수요 예측 |
| **Heuristic Fallback** | 데이터 부족 시 적응형 예측 |
| **Reorder Order (차수)** | 시즌 내 입고 횟수 |

## 빠른 시작

### 1. BigQuery 쿼리 실행

```bash
# Noir 브랜드 리오더 쿼리 실행
bq query --use_legacy_sql=false < queries/noir_reorder_v1.7.sql

# Queens Selection 브랜드
bq query --use_legacy_sql=false < queries/queens_reorder_v1.6.sql

# Verda 브랜드
bq query --use_legacy_sql=false < queries/verda_reorder_v1.6.sql

# Zizae 브랜드
bq query --use_legacy_sql=false < queries/zizae_reorder_v1.7.sql

# Dana&Peta 브랜드
bq query --use_legacy_sql=false < queries/danapeta_reorder_v1.6.sql

# Marchmara 브랜드
bq query --use_legacy_sql=false < queries/marchmara_reorder_v1.7.sql
```

### 2. Apps Script 설정

1. 해당 브랜드의 Google Sheets 열기
2. **확장 프로그램 > Apps Script** 선택
3. `scripts/` 폴더의 해당 스크립트 복사/붙여넣기
4. 트리거 설정: 매일 오전 10시

### 3. 자동화 흐름

```
1. getReorderItems()          → BigQuery 쿼리 실행 + Price Down 제외
2. appendToReorderLogSheet()  → '5.2 리오더 내역' 기록
3. archiveReorderItems()      → reorder_archive 아카이브
4. postSlackNotification()    → Slack 알림
```

## 컬럼 구조 (30 Columns)

| 범위 | 컬럼 수 | 설명 |
|------|--------|------|
| A-Y | 25개 | BigQuery 쿼리 결과 |
| Z-AD | 5개 | Apps Script 계산 (date, product_code, seasonality_weight, seasonality_source, qty) |

**핵심 컬럼 인덱스**:
- `QUERY_EXECUTED_AT`: 24 (Y열)
- `SEASONALITY_WEIGHT`: 27 (AB열)
- `SEASONALITY_SOURCE`: 28 (AC열)
- `REORDER_QTY`: 29 (AD열)

## 주요 데이터 소스

### 공통 테이블

| 테이블 | 용도 |
|--------|------|
| `damoa-lake.logistics_owned.stockDetail_raw` | 물리적 재고 |
| `damoa-lake.logistics_owned.daily_inventory_transaction` | 리오더 차수 계산 |
| `damoa-lake.ms_order.order_shipment_estimate` | 예약 배송 정보 |
| `damoa-lake.ms_product.product_item` | 상품 마스터 |
| `damoa-mart.biz_analytics.product_funnel_daily` | 일별 판매 퍼널 |

### 브랜드별 Master 테이블

| 브랜드 | Master 테이블 |
|--------|---------------|
| Noir | `damoa-lake.pb2_owned.noor_master` |
| Queens Selection | `damoa-lake.pb2_owned.queens_master` |
| Verda | `damoa-lake.pb2_owned.verda_master` |
| Zizae | `damoa-lake.pb1_owned.zizae_master` |
| Dana&Peta | `damoa-lake.pb1_owned.dana_master` |
| Marchmara | `damoa-lake.pb1_owned.marchmara_master` |

## 설계 원칙

1. **과재고 방지 우선**: 품절보다 과재고가 더 위험
2. **평일 자동화**: 월~금에만 실행, 주말 스킵
3. **Master 테이블 기반 필터**: 리오더 가능 품번만 대상
4. **브랜드 독립적 구조**: 공통 로직 + 브랜드별 파라미터

## 문서 가이드

| 문서 | 내용 |
|------|------|
| [REORDER_SYSTEM.md](docs/REORDER_SYSTEM.md) | 전체 시스템 아키텍처 및 알고리즘 |
| [AVAILABLE_STOCK_DESIGN.md](docs/AVAILABLE_STOCK_DESIGN.md) | 가용재고 계산 상세 설계 |
| [QUERY_DESIGN_DECISIONS.md](docs/QUERY_DESIGN_DECISIONS.md) | 쿼리 설계 결정사항 및 AI 리뷰 |
| [BRAND_CONFIG.md](docs/BRAND_CONFIG.md) | 브랜드별 설정 및 파라미터 |

## 버전 히스토리

| 버전 | 날짜 | 변경사항 |
|------|------|----------|
| v5.0 | 2026-02-03 | 마치마라(Marchmara) 브랜드 추가, Slack 채널 C0ABHFXMLP5 통합, 브랜드별 subteam 설정 |
| v4.2 | 2026-01-14 | 보수적 발주 로직 (70일+/5장→0), Price Down 60일, extractPbCode 정규식 개선 |
| v4.1 | 2026-01-12 | 쿼리 성능 최적화 (372일 동적 날짜, Context 사전 필터링) |
| v4.0 | 2026-01-09 | 동적 시즌 계산, 쿼리 날짜 검증, 전 브랜드 적용 |
| v3.1 | 2026-01-08 | Price Down 제외 로직 추가 |
| v3.0 | 2025-12-15 | Dana&Peta 브랜드 추가 (5개 브랜드) |
| v2.5 | 2025-12-12 | Zizae 브랜드 추가, 차수별 예측 적용 |
| v2.0 | 2025-12-10 | 멀티 브랜드 지원 (Noir, Queens, Verda) |
| v1.0 | 2025-12-09 | Noir 초기 버전 |

---

**Maintainer:** PB Team
**Last Updated:** 2026-02-03
