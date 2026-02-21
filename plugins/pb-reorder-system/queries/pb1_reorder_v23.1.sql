-- ##################################################################################
-- # 리오더 최적화 분석 v23.1 + Heuristic(14d coverage) 내재화 (출력 스키마 원본과 동일)
-- # 원본 브랜드: PB (지재)
-- ##################################################################################

-- STEP 1: 파라미터 및 UDF 정의
DECLARE START_DATE DATE DEFAULT '2023-01-01';
DECLARE RELATIVE_SPV_THRESHOLD FLOAT64 DEFAULT 0.65;
DECLARE HIGH_SPV_MULTIPLIER FLOAT64 DEFAULT 1.3;

-- [추가] 휴리스틱 파라미터 (과물량 억제용) — 내부 계산용, 출력엔 포함 안 됨
DECLARE HEURISTIC_DAYS INT64 DEFAULT 14;          -- 휴리스틱 커버리지 일수
DECLARE HEURISTIC_SPV_MIN FLOAT64 DEFAULT 0.90;   -- SPV 스케일 하한
DECLARE HEURISTIC_SPV_MAX FLOAT64 DEFAULT 1.10;   -- SPV 스케일 상한

-- 각 예측 기간에 맞는 UDF 생성 (원본 유지)
CREATE TEMP FUNCTION integral_30d() RETURNS ARRAY<float64>
LANGUAGE js OPTIONS (library = ['gs://rec-monte/mersenne-twister.js']) AS "
  var MT = new MersenneTwister();
  var result = [];
  for(var i=0; i<30*1000; ++i) result.push(MT.random());
  return result;
";

CREATE TEMP FUNCTION integral_60d() RETURNS ARRAY<float64>
LANGUAGE js OPTIONS (library = ['gs://rec-monte/mersenne-twister.js']) AS "
  var MT = new MersenneTwister();
  var result = [];
  for(var i=0; i<60*1000; ++i) result.push(MT.random());
  return result;
";

CREATE TEMP FUNCTION integral_90d() RETURNS ARRAY<float64>
LANGUAGE js OPTIONS (library = ['gs://rec-monte/mersenne-twister.js']) AS "
  var MT = new MersenneTwister();
  var result = [];
  for(var i=0; i<90*1000; ++i) result.push(MT.random());
  return result;
";

CREATE TEMP FUNCTION integral_180d() RETURNS ARRAY<float64>
LANGUAGE js OPTIONS (library = ['gs://rec-monte/mersenne-twister.js']) AS "
  var MT = new MersenneTwister();
  var result = [];
  for(var i=0; i<180*1000; ++i) result.push(MT.random());
  return result;
";

CREATE TEMPORARY FUNCTION erfinv(prob FLOAT64) RETURNS FLOAT64
LANGUAGE js AS "
  const a=0.147;
  const b=2/(Math.PI*a)+Math.log(1-prob**2)/2;
  const sqrt1=Math.sqrt(b**2-Math.log(1-prob**2)/a);
  const sqrt2=Math.sqrt(sqrt1-b);
  return sqrt2*Math.sign(prob);
";

WITH
-- ================================================================================
-- 계층 1: 데이터 준비 (원본 유지)
-- ================================================================================
target_products AS (
  SELECT
    p.id AS product_id,
    p.created_at,
    p.mall_product_code,
    c.depth2_category_name || '/' || c.depth3_category_name AS base_category_name
  FROM damoa-lake.ms_product.product AS p
  JOIN damoa-mart.m_products.leaf_category_map AS c
    ON p.leaf_category_id = c.leaf_category_id
),

product_funnel_filtered AS (
  SELECT dt, item_id, quantity, gmv, vcnt
  FROM damoa-mart.biz_analytics.product_funnel_daily
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

-- 현재 상태 (원본 유지)
current_product_status_30d AS (
  WITH sku_recent_performance AS (
    SELECT
      pi.product_item_code,
      SUM(CASE WHEN o.dt >= DATE_SUB(CURRENT_DATE(), INTERVAL 6 DAY) THEN o.quantity ELSE 0 END) AS sales_past_7_days,
      SUM(o.quantity) AS sales_past_14_days,
      SAFE_DIVIDE(SUM(f.gmv), SUM(f.vcnt)) AS sku_spv_past_14d
    FROM damoa-mart.base.snap_order_rds o
    JOIN damoa-lake.ms_product.product_item pi ON o.product_item_id = pi.id
    JOIN product_funnel_filtered f ON pi.product_id = f.item_id AND o.dt = f.dt
    WHERE o.dt >= DATE_SUB(CURRENT_DATE(), INTERVAL 13 DAY)
      AND o.purchase_state <> 'WAIT'
    GROUP BY 1
  )
  SELECT
    stock.mall_product_code,
    IFNULL(p.base_category_name, 'No Category') AS base_category_name,
    stock.qty AS current_stock,
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
  FROM damoa-mart.pb1.pb1_real_stock_250725 stock
  JOIN damoa-lake.ms_product.product_item pi ON stock.mall_product_code = pi.product_item_code
  LEFT JOIN target_products p ON pi.product_id = p.product_id
  LEFT JOIN sku_recent_performance s ON stock.mall_product_code = s.product_item_code
  QUALIFY ROW_NUMBER() OVER(PARTITION BY stock.mall_product_code ORDER BY s.sales_past_14_days DESC) = 1
),

-- 중장기 최근누적 (원본 유지)
current_product_status_longterm AS (
  SELECT
    s.product_item_code mall_product_code,
    SUM(CASE WHEN o.dt >= DATE_SUB(CURRENT_DATE(), INTERVAL 29 DAY) THEN o.quantity ELSE 0 END) AS sales_past_30_days,
    SUM(CASE WHEN o.dt >= DATE_SUB(CURRENT_DATE(), INTERVAL 59 DAY) THEN o.quantity ELSE 0 END) AS sales_past_60_days,
    SUM(CASE WHEN o.dt >= DATE_SUB(CURRENT_DATE(), INTERVAL 89 DAY) THEN o.quantity ELSE 0 END) AS sales_past_90_days,
    SUM(CASE WHEN o.dt >= DATE_SUB(CURRENT_DATE(), INTERVAL 179 DAY) THEN o.quantity ELSE 0 END) AS sales_past_180_days
  FROM damoa-mart.base.snap_order_rds o
  JOIN damoa-lake.ms_product.product_item s ON o.product_item_id = s.id
  WHERE o.dt >= DATE_SUB(CURRENT_DATE(), INTERVAL 179 DAY)
    AND o.purchase_state <> 'WAIT'
  GROUP BY 1
),

-- 카테고리 SPV 벤치마크 (원본 유지)
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
-- 계층 2: 예측 엔진 (원본 유지)
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

-- 60/90/180일 예측은 현재 비활성화 (필요시 활성화)
statistical_forecasts_60d AS (SELECT mall_product_code, 0 AS conservative_forecast_60d FROM current_product_status_30d WHERE 1=2),
statistical_forecasts_90d AS (SELECT mall_product_code, 0 AS conservative_forecast_90d FROM current_product_status_30d WHERE 1=2),
statistical_forecasts_180d AS (SELECT mall_product_code, 0 AS conservative_forecast_180d FROM current_product_status_30d WHERE 1=2),

high_spv_candidates AS (
  SELECT s.mall_product_code
  FROM current_product_status_30d s
  LEFT JOIN category_spv_benchmark b ON s.base_category_name = b.base_category_name
  WHERE s.sales_past_7_days > 0
    AND IFNULL(SAFE_DIVIDE(s.sku_spv_past_14d, b.avg_category_spv), 0) > HIGH_SPV_MULTIPLIER
),

-- ================================================================================
-- 계층 3: 최종 의사결정 (휴리스틱 14일 커버리지 내부 계산)
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
    st60.conservative_forecast_60d,
    st90.conservative_forecast_90d,
    st180.conservative_forecast_180d,

    -- ===== 휴리스틱 14일 커버리지 (내부 변수) =====
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
  LEFT JOIN statistical_forecasts_60d st60 ON s30.mall_product_code = st60.mall_product_code
  LEFT JOIN statistical_forecasts_90d st90 ON s30.mall_product_code = st90.mall_product_code
  LEFT JOIN statistical_forecasts_180d st180 ON s30.mall_product_code = st180.mall_product_code
  LEFT JOIN high_spv_candidates h ON s30.mall_product_code = h.mall_product_code
  LEFT JOIN category_spv_benchmark b ON s30.base_category_name = b.base_category_name
)

-- ================================================================================
-- 최종 출력 (원본과 동일한 컬럼/순서/별칭 유지)
-- ================================================================================
SELECT
  c.mall_product_code,
  c.base_category_name,
  c.current_stock,
  c.product_type,
  c.decision_isoweek,
  c.sales_past_7_days,
  c.sales_past_14_days,
  c.sales_past_7_days_bin,
  c.sales_past_14_days_bin,
  c.sku_spv_past_14d,
  c.avg_category_spv,
  c.relative_spv_index,

  -- 30일 예측치 (통계 우선, 아니면 휴리스틱 14일)
  CAST(ROUND(
    CASE
      WHEN c.forecast_level = 'Heuristic (High-SPV)' THEN c.sales_past_7_days * 2 * 0.7
      WHEN c.forecast_level = 'Statistical' THEN c.conservative_forecast_30d
      ELSE /* Heuristic (Adaptive-14d) */
        GREATEST(c.lower_guard_14d, LEAST(c.base_h_14d * c.spv_scale_14d, c.upper_guard_14d)) * 0.90
    END
  ) AS INT64) AS conservative_forecast_30d,

  CAST(ROUND(
    CASE
      WHEN c.forecast_level = 'Heuristic (High-SPV)' THEN c.sales_past_7_days * 2
      WHEN c.forecast_level = 'Statistical' THEN c.normal_forecast_30d
      ELSE
        GREATEST(c.lower_guard_14d, LEAST(c.base_h_14d * c.spv_scale_14d, c.upper_guard_14d))
    END
  ) AS INT64) AS normal_forecast_30d,

  CAST(ROUND(
    CASE
      WHEN c.forecast_level = 'Heuristic (High-SPV)' THEN c.sales_past_7_days * 2 * 1.3
      WHEN c.forecast_level = 'Statistical' THEN c.aggressive_forecast_30d
      ELSE
        GREATEST(c.lower_guard_14d, LEAST(c.base_h_14d * c.spv_scale_14d, c.upper_guard_14d)) * 1.10
    END
  ) AS INT64) AS aggressive_forecast_30d,

  -- 중장기 보수적 예측치 (원본 동작 유지)
  CAST(ROUND(COALESCE(c.conservative_forecast_60d, c.sales_past_60_days * 0.5)) AS INT64) AS conservative_forecast_60d,
  CAST(ROUND(COALESCE(c.conservative_forecast_90d, c.sales_past_90_days * 0.5)) AS INT64) AS conservative_forecast_90d,
  CAST(ROUND(COALESCE(c.conservative_forecast_180d, c.sales_past_180_days * 0.5)) AS INT64) AS conservative_forecast_180d,

  -- 주문량 (원본 포맷/컬럼 유지, 휴리스틱 분기에서는 14일 기반 값을 사용)
  CAST(CEIL(GREATEST(0,
    (CASE
      WHEN c.forecast_level = 'Heuristic (High-SPV)' THEN c.sales_past_7_days * 2 * 0.7
      WHEN c.forecast_level = 'Statistical' THEN c.conservative_forecast_30d
      ELSE GREATEST(c.lower_guard_14d, LEAST(c.base_h_14d * c.spv_scale_14d, c.upper_guard_14d)) * 0.90
    END) - c.current_stock
  ) / 5) * 5 AS INT64) AS reorder_qty_conservative_30d,

  CAST(CEIL(GREATEST(0,
    (CASE
      WHEN c.forecast_level = 'Heuristic (High-SPV)' THEN c.sales_past_7_days * 2
      WHEN c.forecast_level = 'Statistical' THEN c.normal_forecast_30d
      ELSE GREATEST(c.lower_guard_14d, LEAST(c.base_h_14d * c.spv_scale_14d, c.upper_guard_14d))
    END) - c.current_stock
  ) / 5) * 5 AS INT64) AS reorder_qty_normal_30d,

  CAST(CEIL(GREATEST(0,
    (CASE
      WHEN c.forecast_level = 'Heuristic (High-SPV)' THEN c.sales_past_7_days * 2 * 1.3
      WHEN c.forecast_level = 'Statistical' THEN c.aggressive_forecast_30d
      ELSE GREATEST(c.lower_guard_14d, LEAST(c.base_h_14d * c.spv_scale_14d, c.upper_guard_14d)) * 1.10
    END) - c.current_stock
  ) / 5) * 5 AS INT64) AS reorder_qty_aggressive_30d,

  CAST(CEIL(GREATEST(0, (COALESCE(c.conservative_forecast_60d, c.sales_past_60_days * 0.5)) - c.current_stock) / 5) * 5 AS INT64) AS reorder_qty_conservative_60d,
  CAST(CEIL(GREATEST(0, (COALESCE(c.conservative_forecast_90d, c.sales_past_90_days * 0.5)) - c.current_stock) / 5) * 5 AS INT64) AS reorder_qty_conservative_90d,
  CAST(CEIL(GREATEST(0, (COALESCE(c.conservative_forecast_180d, c.sales_past_180_days * 0.5)) - c.current_stock) / 5) * 5 AS INT64) AS reorder_qty_conservative_180d,

  c.forecast_level
FROM combined_forecasts c
WHERE c.relative_spv_index >= RELATIVE_SPV_THRESHOLD
ORDER BY reorder_qty_normal_30d DESC;
