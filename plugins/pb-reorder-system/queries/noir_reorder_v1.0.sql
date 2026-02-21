-- ##################################################################################
-- # 노어(Noir) 리오더 최적화 분석 v1.0
-- # 가용 재고 기반 (Available Stock = Physical + In-Transit - Reserved)
-- #
-- # 변경사항 (from pb1_reorder_v23.1):
-- #   1. 재고 소스: pb1_real_stock_250725 → stockDetail_raw (실시간)
-- #   2. 브랜드 필터: Brand = 'NR' (노어)
-- #   3. 가용 재고 개념 도입: current_stock → available_stock
-- #   4. 미수령발주량/미발송수량은 Python에서 Sheets 연동 후 주입
-- #
-- # 사용법:
-- #   이 쿼리는 physical_stock만 계산
-- #   Python 스크립트에서 Sheets 데이터와 조인하여 available_stock 계산
-- ##################################################################################

-- STEP 1: 파라미터 및 UDF 정의
DECLARE START_DATE DATE DEFAULT '2023-01-01';
DECLARE RELATIVE_SPV_THRESHOLD FLOAT64 DEFAULT 0.65;
DECLARE HIGH_SPV_MULTIPLIER FLOAT64 DEFAULT 1.3;
DECLARE BRAND_CODE STRING DEFAULT 'NR';  -- 노어 브랜드

-- [추가] 휴리스틱 파라미터 (과물량 억제용)
DECLARE HEURISTIC_DAYS INT64 DEFAULT 14;
DECLARE HEURISTIC_SPV_MIN FLOAT64 DEFAULT 0.90;
DECLARE HEURISTIC_SPV_MAX FLOAT64 DEFAULT 1.10;

-- 각 예측 기간에 맞는 UDF 생성
CREATE TEMP FUNCTION integral_30d() RETURNS ARRAY<float64>
LANGUAGE js OPTIONS (library = ['gs://rec-monte/mersenne-twister.js']) AS """
  var MT = new MersenneTwister();
  var result = [];
  for(var i=0; i<30*1000; ++i) result.push(MT.random());
  return result;
""";

CREATE TEMPORARY FUNCTION erfinv(prob FLOAT64) RETURNS FLOAT64
LANGUAGE js AS """
  const a=0.147;
  const b=2/(Math.PI*a)+Math.log(1-prob**2)/2;
  const sqrt1=Math.sqrt(b**2-Math.log(1-prob**2)/a);
  const sqrt2=Math.sqrt(sqrt1-b);
  return sqrt2*Math.sign(prob);
""";

WITH
-- ================================================================================
-- 계층 1: 데이터 준비
-- ================================================================================

-- 노어 브랜드 실시간 재고 (stockDetail_raw 사용)
noir_physical_stock AS (
  SELECT
    itemCode AS mall_product_code,
    avaliableStock AS physical_stock  -- 주의: 컬럼명 오타 (avaliable)
  FROM `damoa-lake.logistics_owned.stockDetail_raw`
  WHERE Brand = BRAND_CODE
),

-- 타겟 상품 (노어 브랜드만)
target_products AS (
  SELECT
    p.id AS product_id,
    p.created_at,
    p.mall_product_code,
    c.depth2_category_name || '/' || c.depth3_category_name AS base_category_name
  FROM `damoa-lake.ms_product.product` AS p
  JOIN `damoa-mart.m_products.leaf_category_map` AS c
    ON p.leaf_category_id = c.leaf_category_id
  JOIN `damoa-lake.ms_product.product_item` pi
    ON p.id = pi.product_id
  WHERE pi.product_item_code IN (SELECT mall_product_code FROM noir_physical_stock)
),

product_funnel_filtered AS (
  SELECT dt, item_id, quantity, gmv, vcnt
  FROM `damoa-mart.biz_analytics.product_funnel_daily`
  WHERE dt >= START_DATE
),

complete_daily_sales AS (
  SELECT
    c.calendar_date AS dt,
    p.product_id AS item_id,
    IFNULL(s.quantity, 0) AS quantity
  FROM (SELECT DISTINCT product_id FROM target_products) p
  CROSS JOIN (
    SELECT calendar_date
    FROM UNNEST(GENERATE_DATE_ARRAY(START_DATE, CURRENT_DATE())) AS calendar_date
  ) c
  LEFT JOIN product_funnel_filtered s
    ON p.product_id = s.item_id AND c.calendar_date = s.dt
),

-- 현재 상태 (stockDetail_raw 기반)
current_product_status_30d AS (
  WITH sku_recent_performance AS (
    SELECT
      pi.product_item_code,
      SUM(CASE WHEN o.dt >= DATE_SUB(CURRENT_DATE(), INTERVAL 6 DAY) THEN o.quantity ELSE 0 END) AS sales_past_7_days,
      SUM(o.quantity) AS sales_past_14_days,
      SAFE_DIVIDE(SUM(f.gmv), SUM(f.vcnt)) AS sku_spv_past_14d
    FROM `damoa-mart.base.snap_order_rds` o
    JOIN `damoa-lake.ms_product.product_item` pi ON o.product_item_id = pi.id
    JOIN product_funnel_filtered f ON pi.product_id = f.item_id AND o.dt = f.dt
    WHERE o.dt >= DATE_SUB(CURRENT_DATE(), INTERVAL 13 DAY)
      AND o.purchase_state <> 'WAIT'
      AND pi.product_item_code IN (SELECT mall_product_code FROM noir_physical_stock)
    GROUP BY 1
  )
  SELECT
    stock.mall_product_code,
    IFNULL(p.base_category_name, 'No Category') AS base_category_name,
    stock.physical_stock,  -- 물리적 재고 (가용 재고는 Python에서 계산)
    CASE
      WHEN p.created_at IS NULL THEN 'No Category'
      WHEN DATE_DIFF(CURRENT_DATE(), DATE(p.created_at), DAY) < 28 THEN '신상품'
      ELSE '기존상품'
    END AS product_type,
    EXTRACT(ISOWEEK FROM CURRENT_DATE()) AS decision_isoweek,
    IFNULL(s.sales_past_7_days, 0) AS sales_past_7_days,
    IFNULL(s.sales_past_14_days, 0) AS sales_past_14_days,
    LPAD(CAST(FLOOR(IFNULL(s.sales_past_7_days, 0) / 5) AS STRING), 2, '0') AS sales_past_7_days_bin,
    LPAD(CAST(FLOOR(IFNULL(s.sales_past_14_days, 0) / 10) AS STRING), 2, '0') AS sales_past_14_days_bin,
    s.sku_spv_past_14d
  FROM noir_physical_stock stock
  JOIN `damoa-lake.ms_product.product_item` pi ON stock.mall_product_code = pi.product_item_code
  LEFT JOIN target_products p ON pi.product_id = p.product_id
  LEFT JOIN sku_recent_performance s ON stock.mall_product_code = s.product_item_code
  QUALIFY ROW_NUMBER() OVER(PARTITION BY stock.mall_product_code ORDER BY s.sales_past_14_days DESC) = 1
),

-- 중장기 최근누적
current_product_status_longterm AS (
  SELECT
    s.product_item_code AS mall_product_code,
    SUM(CASE WHEN o.dt >= DATE_SUB(CURRENT_DATE(), INTERVAL 29 DAY) THEN o.quantity ELSE 0 END) AS sales_past_30_days,
    SUM(CASE WHEN o.dt >= DATE_SUB(CURRENT_DATE(), INTERVAL 59 DAY) THEN o.quantity ELSE 0 END) AS sales_past_60_days,
    SUM(CASE WHEN o.dt >= DATE_SUB(CURRENT_DATE(), INTERVAL 89 DAY) THEN o.quantity ELSE 0 END) AS sales_past_90_days,
    SUM(CASE WHEN o.dt >= DATE_SUB(CURRENT_DATE(), INTERVAL 179 DAY) THEN o.quantity ELSE 0 END) AS sales_past_180_days
  FROM `damoa-mart.base.snap_order_rds` o
  JOIN `damoa-lake.ms_product.product_item` s ON o.product_item_id = s.id
  WHERE o.dt >= DATE_SUB(CURRENT_DATE(), INTERVAL 179 DAY)
    AND o.purchase_state <> 'WAIT'
    AND s.product_item_code IN (SELECT mall_product_code FROM noir_physical_stock)
  GROUP BY 1
),

-- 카테고리 SPV 벤치마크
category_spv_benchmark AS (
  SELECT
    p.base_category_name,
    SAFE_DIVIDE(SUM(s.gmv), SUM(s.vcnt)) AS avg_category_spv
  FROM product_funnel_filtered s
  JOIN target_products p ON s.item_id = p.product_id
  WHERE s.vcnt > 0
  GROUP BY 1
),

-- ================================================================================
-- 계층 2: 예측 엔진
-- ================================================================================
statistical_forecasts_30d AS (
  WITH reorder_menu AS (
    WITH historical_performance_with_context AS (
      SELECT
        CASE WHEN DATE_DIFF(s.dt, DATE(p.created_at), DAY) < 28 THEN '신상품' ELSE '기존상품' END AS product_type,
        p.base_category_name,
        EXTRACT(ISOWEEK FROM s.dt) AS decision_isoweek,
        LPAD(CAST(FLOOR(SUM(s.quantity) OVER (PARTITION BY s.item_id ORDER BY s.dt
          ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) / 5) AS STRING), 2, '0') AS sales_past_7_days_bin,
        LPAD(CAST(FLOOR(SUM(s.quantity) OVER (PARTITION BY s.item_id ORDER BY s.dt
          ROWS BETWEEN 13 PRECEDING AND CURRENT ROW) / 10) AS STRING), 2, '0') AS sales_past_14_days_bin,
        s.quantity AS daily_quantity,
        s.item_id
      FROM complete_daily_sales s
      JOIN target_products p ON s.item_id = p.product_id
    ),
    context_group_stats AS (
      SELECT
        product_type,
        base_category_name,
        decision_isoweek,
        sales_past_7_days_bin,
        sales_past_14_days_bin,
        APPROX_QUANTILES(daily_quantity, 100)[OFFSET(50)] AS median_daily_sales,
        STDDEV(daily_quantity) AS stddev_daily_sales
      FROM historical_performance_with_context
      WHERE sales_past_14_days_bin IS NOT NULL
      GROUP BY 1, 2, 3, 4, 5
      HAVING COUNT(item_id) >= 14
    ),
    p0 AS (SELECT p FROM UNNEST(integral_30d()) p),
    p1 AS (
      SELECT
        h.*,
        CEIL(ROW_NUMBER() OVER (
          PARTITION BY h.product_type, h.base_category_name, h.decision_isoweek,
            h.sales_past_7_days_bin, h.sales_past_14_days_bin
        ) / 30) AS g,
        p.p AS prob,
        IF(h.median_daily_sales = 0 AND p.p < 0.5,
          0,
          ROUND(GREATEST(0, SQRT(2) * h.stddev_daily_sales * erfinv(2 * p.p - 1) + h.median_daily_sales))
        ) AS result
      FROM p0 p CROSS JOIN context_group_stats h
    ),
    p2 AS (
      SELECT
        product_type,
        base_category_name,
        decision_isoweek,
        sales_past_7_days_bin,
        sales_past_14_days_bin,
        g,
        SUM(result) AS result
      FROM p1
      GROUP BY 1, 2, 3, 4, 5, 6
    )
    SELECT
      product_type,
      base_category_name,
      decision_isoweek,
      sales_past_7_days_bin,
      sales_past_14_days_bin,
      APPROX_QUANTILES(result, 100)[OFFSET(30)] AS conservative_forecast_30d,
      APPROX_QUANTILES(result, 100)[OFFSET(50)] AS normal_forecast_30d,
      APPROX_QUANTILES(result, 100)[OFFSET(90)] AS aggressive_forecast_30d
    FROM p2
    GROUP BY 1, 2, 3, 4, 5
  )
  SELECT
    s.mall_product_code,
    r.conservative_forecast_30d,
    r.normal_forecast_30d,
    r.aggressive_forecast_30d
  FROM current_product_status_30d s
  JOIN reorder_menu r
    ON s.product_type = r.product_type
    AND s.base_category_name = r.base_category_name
    AND s.decision_isoweek = r.decision_isoweek
    AND s.sales_past_7_days_bin = r.sales_past_7_days_bin
    AND s.sales_past_14_days_bin = r.sales_past_14_days_bin
),

high_spv_candidates AS (
  SELECT s.mall_product_code
  FROM current_product_status_30d s
  LEFT JOIN category_spv_benchmark b ON s.base_category_name = b.base_category_name
  WHERE s.sales_past_7_days > 0
    AND IFNULL(SAFE_DIVIDE(s.sku_spv_past_14d, b.avg_category_spv), 0) > HIGH_SPV_MULTIPLIER
),

-- ================================================================================
-- 계층 3: 최종 의사결정
-- ================================================================================
combined_forecasts AS (
  SELECT
    s30.*,
    s_long.sales_past_30_days,
    s_long.sales_past_60_days,
    s_long.sales_past_90_days,
    s_long.sales_past_180_days,
    b.avg_category_spv,
    IFNULL(SAFE_DIVIDE(s30.sku_spv_past_14d, b.avg_category_spv), 0) AS relative_spv_index,

    -- 예측 소스 레벨
    CASE
      WHEN h.mall_product_code IS NOT NULL AND IFNULL(st30.normal_forecast_30d, 0) = 0 THEN 'Heuristic (High-SPV)'
      WHEN st30.mall_product_code IS NOT NULL THEN 'Statistical'
      ELSE 'Heuristic (Adaptive-14d)'
    END AS forecast_level,

    -- 통계 예측 결과
    st30.conservative_forecast_30d,
    st30.normal_forecast_30d,
    st30.aggressive_forecast_30d,

    -- 휴리스틱 14일 커버리지 (내부 변수)
    CAST(HEURISTIC_DAYS AS FLOAT64)
      * (0.7 * SAFE_DIVIDE(s30.sales_past_7_days, 7.0)
       + 0.3 * SAFE_DIVIDE(s30.sales_past_14_days, 14.0)) AS base_h_14d,
    LEAST(HEURISTIC_SPV_MAX,
      GREATEST(HEURISTIC_SPV_MIN, 1.0 + 0.20 * (IFNULL(SAFE_DIVIDE(s30.sku_spv_past_14d, b.avg_category_spv), 1.0) - 1.0))
    ) AS spv_scale_14d,
    0.8 * s30.sales_past_14_days AS lower_guard_14d,
    LEAST(
      1.5 * s30.sales_past_14_days,
      IFNULL(s_long.sales_past_90_days * (CAST(HEURISTIC_DAYS AS FLOAT64) / 90.0) * 1.2, 9e18)
    ) AS upper_guard_14d

  FROM current_product_status_30d s30
  LEFT JOIN current_product_status_longterm s_long ON s30.mall_product_code = s_long.mall_product_code
  LEFT JOIN statistical_forecasts_30d st30 ON s30.mall_product_code = st30.mall_product_code
  LEFT JOIN high_spv_candidates h ON s30.mall_product_code = h.mall_product_code
  LEFT JOIN category_spv_benchmark b ON s30.base_category_name = b.base_category_name
)

-- ================================================================================
-- 최종 출력
-- Python에서 in_transit_qty, reserved_qty 조인 후 available_stock 계산
-- reorder_qty = MAX(0, forecast - available_stock)
-- ================================================================================
SELECT
  c.mall_product_code,
  c.base_category_name,
  c.physical_stock,  -- 물리적 재고 (Python에서 가용 재고로 변환)
  c.product_type,
  c.decision_isoweek,
  c.sales_past_7_days,
  c.sales_past_14_days,
  c.sales_past_7_days_bin,
  c.sales_past_14_days_bin,
  c.sku_spv_past_14d,
  c.avg_category_spv,
  c.relative_spv_index,
  c.forecast_level,

  -- 30일 예측치
  CAST(ROUND(
    CASE
      WHEN c.forecast_level = 'Heuristic (High-SPV)' THEN c.sales_past_7_days * 2 * 0.7
      WHEN c.forecast_level = 'Statistical' THEN c.conservative_forecast_30d
      ELSE GREATEST(c.lower_guard_14d, LEAST(c.base_h_14d * c.spv_scale_14d, c.upper_guard_14d)) * 0.90
    END
  ) AS INT64) AS conservative_forecast_30d,

  CAST(ROUND(
    CASE
      WHEN c.forecast_level = 'Heuristic (High-SPV)' THEN c.sales_past_7_days * 2
      WHEN c.forecast_level = 'Statistical' THEN c.normal_forecast_30d
      ELSE GREATEST(c.lower_guard_14d, LEAST(c.base_h_14d * c.spv_scale_14d, c.upper_guard_14d))
    END
  ) AS INT64) AS normal_forecast_30d,

  CAST(ROUND(
    CASE
      WHEN c.forecast_level = 'Heuristic (High-SPV)' THEN c.sales_past_7_days * 2 * 1.3
      WHEN c.forecast_level = 'Statistical' THEN c.aggressive_forecast_30d
      ELSE GREATEST(c.lower_guard_14d, LEAST(c.base_h_14d * c.spv_scale_14d, c.upper_guard_14d)) * 1.10
    END
  ) AS INT64) AS aggressive_forecast_30d,

  -- 중장기 판매 실적 (예측용 참고)
  IFNULL(c.sales_past_30_days, 0) AS sales_past_30_days,
  IFNULL(c.sales_past_60_days, 0) AS sales_past_60_days,
  IFNULL(c.sales_past_90_days, 0) AS sales_past_90_days,
  IFNULL(c.sales_past_180_days, 0) AS sales_past_180_days

FROM combined_forecasts c
WHERE c.relative_spv_index >= RELATIVE_SPV_THRESHOLD
ORDER BY c.normal_forecast_30d DESC;
