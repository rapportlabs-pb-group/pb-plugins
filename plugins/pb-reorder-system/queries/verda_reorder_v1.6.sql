-- ##################################################################################
-- # 베르다(Verda) 리오더 최적화 분석 v1.6
-- # 가용 재고 기반 (Available Stock = Physical + In-Transit - Reserved)
-- #
-- # 변경사항 (from v1.5):
-- #   1. Heuristics 계절성 가중치 추가
-- #      - ISO week 기반 카테고리별 계절성 팩터 (데이터 충분 시)
-- #      - 시즌 진행도 기반 감쇠 폴백 (데이터 부족 시)
-- #      - Heuristic (High-SPV) 및 Heuristic (Adaptive)에 적용
-- #      - 시즌 말(1-2월) 과재고 방지 목적
-- #
-- # 유지사항 (from v1.5):
-- #   - reserved_qty: COMPLETED 상태 제외
-- #   - 보수적 발주: 출시 70일+ & 추천 5장 → 0장
-- #   - 날짜 범위: 372일 (동적)
-- #   - Context 사전 필터링, 카테고리 기반 필터링
-- #   - Monte Carlo 시뮬레이션, 리오더 차수별 예측 기간 (14일/21일)
-- #   - 수량 상한: 초도~4차 최대 10장 (예외: High-SPV & 일1개+)
-- #
-- # Note: in_transit_qty는 여전히 Python에서 Sheets 연동 필요
-- ##################################################################################

-- STEP 1: 파라미터 및 UDF 정의
DECLARE START_DATE DATE DEFAULT DATE_SUB(CURRENT_DATE(), INTERVAL 372 DAY);
DECLARE RELATIVE_SPV_THRESHOLD_NEW FLOAT64 DEFAULT 0.30;
DECLARE RELATIVE_SPV_THRESHOLD_EXISTING FLOAT64 DEFAULT 0.65;
DECLARE HIGH_SPV_MULTIPLIER FLOAT64 DEFAULT 1.3;
DECLARE BRAND_CODE STRING DEFAULT 'VD';
DECLARE RESERVED_DAYS_THRESHOLD INT64 DEFAULT 3;

DECLARE CURRENT_MONTH INT64 DEFAULT EXTRACT(MONTH FROM CURRENT_DATE());
DECLARE CURRENT_YEAR INT64 DEFAULT EXTRACT(YEAR FROM CURRENT_DATE());

DECLARE SEASON_START DATE DEFAULT (
  CASE
    WHEN CURRENT_MONTH >= 9 THEN DATE(CURRENT_YEAR, 9, 1)
    WHEN CURRENT_MONTH <= 2 THEN DATE(CURRENT_YEAR - 1, 9, 1)
    ELSE DATE(CURRENT_YEAR, 3, 1)
  END
);

DECLARE SEASON_END DATE DEFAULT (
  CASE
    WHEN CURRENT_MONTH >= 9 THEN DATE(CURRENT_YEAR + 1, 2, 28)
    WHEN CURRENT_MONTH <= 2 THEN DATE(CURRENT_YEAR, 2, 28)
    ELSE DATE(CURRENT_YEAR, 8, 31)
  END
);

-- [NEW v1.7] 직전 시즌 시작일 (과년차 품번 누적 차수 계산용, 2개 시즌만)
DECLARE PREV_SEASON_START DATE DEFAULT (
  CASE
    WHEN CURRENT_MONTH >= 9 THEN DATE(CURRENT_YEAR, 3, 1)
    WHEN CURRENT_MONTH <= 2 THEN DATE(CURRENT_YEAR - 1, 3, 1)
    ELSE DATE(CURRENT_YEAR - 1, 9, 1)
  END
);

DECLARE REORDER_QTY_CAP INT64 DEFAULT 10;
DECLARE DAILY_VELOCITY_THRESHOLD INT64 DEFAULT 7;
DECLARE HEURISTIC_SPV_MIN FLOAT64 DEFAULT 0.90;
DECLARE HEURISTIC_SPV_MAX FLOAT64 DEFAULT 1.10;

-- Seasonality parameters (v1.6)
DECLARE MIN_ISOWEEK_SAMPLES INT64 DEFAULT 14;        -- ISO week factor 사용 최소 샘플
DECLARE SEASON_DECAY_RATE FLOAT64 DEFAULT 0.25;      -- 시즌 말 최대 감쇠율 (25%)
DECLARE SEASONALITY_WEIGHT_MIN FLOAT64 DEFAULT 0.70; -- 계절성 가중치 하한
DECLARE SEASONALITY_WEIGHT_MAX FLOAT64 DEFAULT 1.50; -- 계절성 가중치 상한 (피크 시즌 반영)

CREATE TEMP FUNCTION integral_14d() RETURNS ARRAY<float64>
LANGUAGE js OPTIONS (library = ['gs://rec-monte/mersenne-twister.js']) AS """
  var MT = new MersenneTwister();
  var result = [];
  for(var i=0; i<14*1000; ++i) result.push(MT.random());
  return result;
""";

CREATE TEMP FUNCTION integral_21d() RETURNS ARRAY<float64>
LANGUAGE js OPTIONS (library = ['gs://rec-monte/mersenne-twister.js']) AS """
  var MT = new MersenneTwister();
  var result = [];
  for(var i=0; i<21*1000; ++i) result.push(MT.random());
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
product_funnel_filtered AS (
  SELECT dt, item_id, quantity, gmv, vcnt
  FROM `damoa-mart.biz_analytics.product_funnel_daily`
  WHERE dt >= START_DATE
),

-- [NEW] Price Down 제외: 시즌오프 할인 상품
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
),

-- [CHANGED v1.7] 당시즌 + 직전 시즌 품번만 포함
reorderable_products AS (
  SELECT DISTINCT
    barcode AS product_item_code,
    vendor_category
  FROM `damoa-lake.pb2_owned.verda_master`
  WHERE barcode IS NOT NULL AND barcode != ''
    AND (
      (SAFE_CAST(SUBSTR(barcode, 3, 2) AS INT64) = MOD(EXTRACT(YEAR FROM SEASON_START), 100)
       AND CASE
             WHEN CURRENT_MONTH IN (9,10,11,12,1,2) THEN SUBSTR(barcode, 5, 1) IN ('F', 'W', 'D')
             ELSE SUBSTR(barcode, 5, 1) IN ('S', 'M', 'H')
           END)
      OR
      (SAFE_CAST(SUBSTR(barcode, 3, 2) AS INT64) = MOD(EXTRACT(YEAR FROM PREV_SEASON_START), 100)
       AND CASE
             WHEN CURRENT_MONTH IN (9,10,11,12,1,2) THEN SUBSTR(barcode, 5, 1) IN ('S', 'M', 'H')
             ELSE SUBSTR(barcode, 5, 1) IN ('F', 'W', 'D')
           END)
    )
),

verda_physical_stock AS (
  SELECT
    sd.item_code AS mall_product_code,
    sd.available_stock AS physical_stock,
    rp.vendor_category
  FROM `damoa-lake.ms_order.stock_detail_raw` sd
  JOIN reorderable_products rp ON sd.item_code = rp.product_item_code
  WHERE sd.brand = BRAND_CODE
),

-- [CHANGED v1.7] 과년차 품번 누적 차수: 현재+직전 시즌 (2개 시즌)
reorder_history AS (
  SELECT
    barcode AS product_item_code,
    COUNTIF(date BETWEEN SEASON_START AND SEASON_END) - 1 AS season_reorder_order,
    COUNT(*) - 1 AS total_reorder_order,
    CASE
      WHEN SUBSTR(barcode, 5, 1) IN ('F', 'W', 'D')
           AND SAFE_CAST(SUBSTR(barcode, 3, 2) AS INT64) = MOD(EXTRACT(YEAR FROM SEASON_START), 100)
           AND CURRENT_MONTH IN (9,10,11,12,1,2)
      THEN TRUE
      WHEN SUBSTR(barcode, 5, 1) IN ('S', 'M', 'H')
           AND SAFE_CAST(SUBSTR(barcode, 3, 2) AS INT64) = MOD(CURRENT_YEAR, 100)
           AND CURRENT_MONTH BETWEEN 3 AND 8
      THEN TRUE
      ELSE FALSE
    END AS is_current_season_product
  FROM `damoa-lake.logistics_owned.daily_inventory_transaction`
  WHERE inbound > 0
    AND date BETWEEN PREV_SEASON_START AND SEASON_END
    AND barcode LIKE 'VD%'
  GROUP BY barcode
),

latest_shipment_estimate AS (
  SELECT order_line_id, estimate_shipment_at
  FROM (
    SELECT
      order_line_id,
      estimate_shipment_at,
      ROW_NUMBER() OVER (PARTITION BY order_line_id ORDER BY cdc_timestamp DESC) AS rn
    FROM `damoa-lake.ms_order.order_shipment_estimate`
  )
  WHERE rn = 1
),

-- [CHANGED v1.5] COMPLETED 상태 제외
reserved_qty_by_sku AS (
  SELECT
    pi.product_item_code AS mall_product_code,
    SUM(ol.quantity) AS reserved_qty
  FROM `damoa-lake.ms_order.order_line` ol
  JOIN `damoa-lake.ms_product.product_item` pi ON ol.product_item_id = pi.id
  JOIN latest_shipment_estimate ose ON ol.id = ose.order_line_id
  WHERE
    pi.product_item_code LIKE 'VD%'
    AND ol.purchase_state = 'PAID'
    AND ol.delivery_state NOT IN ('SHIPPED', 'DELIVERED', 'CANCELLED', 'COMPLETED')
    AND ose.estimate_shipment_at >= CURRENT_DATE() + RESERVED_DAYS_THRESHOLD
  GROUP BY pi.product_item_code
),

target_products AS (
  SELECT
    p.id AS product_id,
    p.created_at,
    p.mall_product_code,
    c.depth2_category_name || '/' || c.depth3_category_name AS base_category_name
  FROM `damoa-lake.ms_product.product` AS p
  JOIN `damoa-mart.m_products.leaf_category_map` AS c ON p.leaf_category_id = c.leaf_category_id
  JOIN `damoa-lake.ms_product.product_item` pi ON p.id = pi.product_id
  WHERE pi.product_item_code IN (SELECT mall_product_code FROM verda_physical_stock)
),

brand_categories AS (
  SELECT DISTINCT base_category_name
  FROM target_products
  WHERE base_category_name IS NOT NULL
),

category_matched_products AS (
  SELECT
    p.id AS product_id,
    p.created_at,
    p.mall_product_code,
    c.depth2_category_name || '/' || c.depth3_category_name AS base_category_name
  FROM `damoa-lake.ms_product.product` AS p
  JOIN `damoa-mart.m_products.leaf_category_map` AS c ON p.leaf_category_id = c.leaf_category_id
  WHERE c.depth2_category_name || '/' || c.depth3_category_name IN (SELECT base_category_name FROM brand_categories)
),

category_daily_sales AS (
  SELECT
    c.calendar_date AS dt,
    p.product_id AS item_id,
    IFNULL(s.quantity, 0) AS quantity
  FROM (SELECT DISTINCT product_id FROM category_matched_products) p
  CROSS JOIN (
    SELECT calendar_date FROM UNNEST(GENERATE_DATE_ARRAY(START_DATE, CURRENT_DATE())) AS calendar_date
  ) c
  LEFT JOIN product_funnel_filtered s ON p.product_id = s.item_id AND c.calendar_date = s.dt
),

current_product_status AS (
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
      AND pi.product_item_code IN (SELECT mall_product_code FROM verda_physical_stock)
    GROUP BY 1
  )
  SELECT
    stock.mall_product_code,
    stock.vendor_category,
    IFNULL(p.base_category_name, 'No Category') AS base_category_name,
    stock.physical_stock,
    IFNULL(r.reserved_qty, 0) AS reserved_qty,
    CASE
      WHEN p.created_at IS NULL THEN 'No Category'
      WHEN DATE_DIFF(CURRENT_DATE(), DATE(p.created_at), DAY) < 28 THEN '신상품'
      ELSE '기존상품'
    END AS product_type,
    DATE_DIFF(CURRENT_DATE(), DATE(p.created_at), DAY) AS days_since_launch,
    EXTRACT(ISOWEEK FROM CURRENT_DATE()) AS decision_isoweek,
    IFNULL(s.sales_past_7_days, 0) AS sales_past_7_days,
    IFNULL(s.sales_past_14_days, 0) AS sales_past_14_days,
    LPAD(CAST(FLOOR(IFNULL(s.sales_past_7_days, 0) / 5) AS STRING), 2, '0') AS sales_past_7_days_bin,
    LPAD(CAST(FLOOR(IFNULL(s.sales_past_14_days, 0) / 10) AS STRING), 2, '0') AS sales_past_14_days_bin,
    s.sku_spv_past_14d,
    -- [CHANGED v1.7] 동적 차수: 당시즌 품번=시즌 차수, 과년차=누적 차수
    CASE
      WHEN IFNULL(rh.is_current_season_product, TRUE) THEN IFNULL(rh.season_reorder_order, 0)
      ELSE IFNULL(rh.total_reorder_order, 0)
    END AS reorder_order
  FROM verda_physical_stock stock
  JOIN `damoa-lake.ms_product.product_item` pi ON stock.mall_product_code = pi.product_item_code
  LEFT JOIN target_products p ON pi.product_id = p.product_id
  LEFT JOIN sku_recent_performance s ON stock.mall_product_code = s.product_item_code
  LEFT JOIN reserved_qty_by_sku r ON stock.mall_product_code = r.mall_product_code
  LEFT JOIN reorder_history rh ON stock.mall_product_code = rh.product_item_code
  WHERE NOT EXISTS (
    SELECT 1 FROM price_down_excluded pd WHERE pd.item_id = pi.product_id
  )
  QUALIFY ROW_NUMBER() OVER(PARTITION BY stock.mall_product_code ORDER BY s.sales_past_14_days DESC) = 1
),

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
    AND s.product_item_code IN (SELECT mall_product_code FROM verda_physical_stock)
  GROUP BY 1
),

category_spv_benchmark AS (
  SELECT
    p.base_category_name,
    SAFE_DIVIDE(SUM(s.gmv), SUM(s.vcnt)) AS avg_category_spv
  FROM product_funnel_filtered s
  JOIN category_matched_products p ON s.item_id = p.product_id
  WHERE s.vcnt > 0
  GROUP BY 1
),

statistical_forecasts_14d AS (
  WITH historical_performance_with_context AS (
    SELECT
      CASE WHEN DATE_DIFF(s.dt, DATE(p.created_at), DAY) < 28 THEN '신상품' ELSE '기존상품' END AS product_type,
      p.base_category_name,
      EXTRACT(ISOWEEK FROM s.dt) AS decision_isoweek,
      LPAD(CAST(FLOOR(SUM(s.quantity) OVER (PARTITION BY s.item_id ORDER BY s.dt ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) / 5) AS STRING), 2, '0') AS sales_past_7_days_bin,
      LPAD(CAST(FLOOR(SUM(s.quantity) OVER (PARTITION BY s.item_id ORDER BY s.dt ROWS BETWEEN 13 PRECEDING AND CURRENT ROW) / 10) AS STRING), 2, '0') AS sales_past_14_days_bin,
      s.quantity AS daily_quantity,
      s.item_id
    FROM category_daily_sales s
    JOIN category_matched_products p ON s.item_id = p.product_id
  ),
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
  p0 AS (SELECT p FROM UNNEST(integral_14d()) p),
  p1 AS (
    SELECT
      h.*,
      CEIL(ROW_NUMBER() OVER (PARTITION BY h.product_type, h.base_category_name, h.decision_isoweek, h.sales_past_7_days_bin, h.sales_past_14_days_bin) / 14) AS g,
      p.p AS prob,
      IF(h.median_daily_sales = 0 AND p.p < 0.5, 0,
        ROUND(GREATEST(0, SQRT(2) * h.stddev_daily_sales * erfinv(2 * p.p - 1) + h.median_daily_sales))) AS result
    FROM p0 p CROSS JOIN context_group_stats h
  ),
  p2 AS (
    SELECT product_type, base_category_name, decision_isoweek, sales_past_7_days_bin, sales_past_14_days_bin, g, SUM(result) AS result
    FROM p1 GROUP BY 1, 2, 3, 4, 5, 6
  )
  SELECT product_type, base_category_name, decision_isoweek, sales_past_7_days_bin, sales_past_14_days_bin,
    APPROX_QUANTILES(result, 100)[OFFSET(50)] AS normal_forecast_14d
  FROM p2 GROUP BY 1, 2, 3, 4, 5
),

statistical_forecasts_21d AS (
  WITH historical_performance_with_context AS (
    SELECT
      CASE WHEN DATE_DIFF(s.dt, DATE(p.created_at), DAY) < 28 THEN '신상품' ELSE '기존상품' END AS product_type,
      p.base_category_name,
      EXTRACT(ISOWEEK FROM s.dt) AS decision_isoweek,
      LPAD(CAST(FLOOR(SUM(s.quantity) OVER (PARTITION BY s.item_id ORDER BY s.dt ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) / 5) AS STRING), 2, '0') AS sales_past_7_days_bin,
      LPAD(CAST(FLOOR(SUM(s.quantity) OVER (PARTITION BY s.item_id ORDER BY s.dt ROWS BETWEEN 13 PRECEDING AND CURRENT ROW) / 10) AS STRING), 2, '0') AS sales_past_14_days_bin,
      s.quantity AS daily_quantity,
      s.item_id
    FROM category_daily_sales s
    JOIN category_matched_products p ON s.item_id = p.product_id
  ),
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
  p0 AS (SELECT p FROM UNNEST(integral_21d()) p),
  p1 AS (
    SELECT
      h.*,
      CEIL(ROW_NUMBER() OVER (PARTITION BY h.product_type, h.base_category_name, h.decision_isoweek, h.sales_past_7_days_bin, h.sales_past_14_days_bin) / 21) AS g,
      p.p AS prob,
      IF(h.median_daily_sales = 0 AND p.p < 0.5, 0,
        ROUND(GREATEST(0, SQRT(2) * h.stddev_daily_sales * erfinv(2 * p.p - 1) + h.median_daily_sales))) AS result
    FROM p0 p CROSS JOIN context_group_stats h
  ),
  p2 AS (
    SELECT product_type, base_category_name, decision_isoweek, sales_past_7_days_bin, sales_past_14_days_bin, g, SUM(result) AS result
    FROM p1 GROUP BY 1, 2, 3, 4, 5, 6
  )
  SELECT product_type, base_category_name, decision_isoweek, sales_past_7_days_bin, sales_past_14_days_bin,
    APPROX_QUANTILES(result, 100)[OFFSET(50)] AS normal_forecast_21d
  FROM p2 GROUP BY 1, 2, 3, 4, 5
),

-- [NEW v1.6] ISO week 기반 계절성 CTEs
category_isoweek_stats AS (
  SELECT
    cmp.base_category_name,
    EXTRACT(ISOWEEK FROM cds.dt) AS isoweek,
    SUM(cds.quantity) AS total_sales,
    COUNT(DISTINCT cds.dt) AS sample_days
  FROM category_daily_sales cds
  JOIN category_matched_products cmp ON cds.item_id = cmp.product_id
  GROUP BY 1, 2
),

category_annual_baseline AS (
  SELECT
    base_category_name,
    SAFE_DIVIDE(SUM(total_sales), SUM(sample_days)) AS avg_daily_sales
  FROM category_isoweek_stats
  GROUP BY 1
),

isoweek_seasonality AS (
  SELECT
    w.base_category_name,
    w.isoweek,
    CASE
      WHEN w.sample_days >= MIN_ISOWEEK_SAMPLES THEN
        LEAST(SEASONALITY_WEIGHT_MAX, GREATEST(SEASONALITY_WEIGHT_MIN,
          SAFE_DIVIDE(SAFE_DIVIDE(w.total_sales, w.sample_days), b.avg_daily_sales)
        ))
      ELSE NULL
    END AS isoweek_factor,
    w.sample_days
  FROM category_isoweek_stats w
  JOIN category_annual_baseline b ON w.base_category_name = b.base_category_name
),

season_progress_factor AS (
  SELECT
    SAFE_DIVIDE(
      DATE_DIFF(CURRENT_DATE(), SEASON_START, DAY),
      DATE_DIFF(SEASON_END, SEASON_START, DAY)
    ) AS progress,
    1.0 - (SEASON_DECAY_RATE * SAFE_DIVIDE(
      DATE_DIFF(CURRENT_DATE(), SEASON_START, DAY),
      DATE_DIFF(SEASON_END, SEASON_START, DAY)
    )) AS decay_factor
),

high_spv_candidates AS (
  SELECT s.mall_product_code
  FROM current_product_status s
  LEFT JOIN category_spv_benchmark b ON s.base_category_name = b.base_category_name
  WHERE s.sales_past_7_days > 0
    AND IFNULL(SAFE_DIVIDE(s.sku_spv_past_14d, b.avg_category_spv), 0) > HIGH_SPV_MULTIPLIER
),

combined_forecasts AS (
  SELECT
    s.mall_product_code, s.vendor_category, s.base_category_name, s.physical_stock, s.reserved_qty,
    s.product_type, s.days_since_launch, s.decision_isoweek, s.sales_past_7_days, s.sales_past_14_days,
    s.sales_past_7_days_bin, s.sales_past_14_days_bin, s.sku_spv_past_14d, s.reorder_order,
    s_long.sales_past_30_days, s_long.sales_past_60_days, s_long.sales_past_90_days, s_long.sales_past_180_days,
    b.avg_category_spv,
    IFNULL(SAFE_DIVIDE(s.sku_spv_past_14d, b.avg_category_spv), 0) AS relative_spv_index,
    CASE WHEN s.reorder_order <= 4 THEN 14
         WHEN (DATE_DIFF(SEASON_END, CURRENT_DATE(), DAY) <= 30 OR DATE_DIFF(CURRENT_DATE(), SEASON_START, DAY) <= 30) THEN 14
         WHEN IFNULL(SAFE_DIVIDE(s.sku_spv_past_14d, b.avg_category_spv), 0) > HIGH_SPV_MULTIPLIER THEN 21
         ELSE 14 END AS forecast_days,
    CASE
      WHEN h.mall_product_code IS NOT NULL AND IFNULL(st14.normal_forecast_14d, 0) = 0 THEN 'Heuristic (High-SPV)'
      WHEN st14.normal_forecast_14d IS NOT NULL OR st21.normal_forecast_21d IS NOT NULL THEN 'Statistical'
      ELSE 'Heuristic (Adaptive)'
    END AS forecast_level,
    CASE WHEN s.reorder_order <= 4 THEN IFNULL(st14.normal_forecast_14d, 0)
         WHEN (DATE_DIFF(SEASON_END, CURRENT_DATE(), DAY) <= 30 OR DATE_DIFF(CURRENT_DATE(), SEASON_START, DAY) <= 30) THEN IFNULL(st14.normal_forecast_14d, 0)
         WHEN IFNULL(SAFE_DIVIDE(s.sku_spv_past_14d, b.avg_category_spv), 0) > HIGH_SPV_MULTIPLIER THEN IFNULL(st21.normal_forecast_21d, 0)
         ELSE IFNULL(st14.normal_forecast_14d, 0) END AS statistical_forecast,
    CASE
      WHEN s.reorder_order <= 4 THEN 14.0 * (0.7 * SAFE_DIVIDE(s.sales_past_7_days, 7.0) + 0.3 * SAFE_DIVIDE(s.sales_past_14_days, 14.0))
      WHEN (DATE_DIFF(SEASON_END, CURRENT_DATE(), DAY) <= 30 OR DATE_DIFF(CURRENT_DATE(), SEASON_START, DAY) <= 30) THEN 14.0 * (0.7 * SAFE_DIVIDE(s.sales_past_7_days, 7.0) + 0.3 * SAFE_DIVIDE(s.sales_past_14_days, 14.0))
      WHEN IFNULL(SAFE_DIVIDE(s.sku_spv_past_14d, b.avg_category_spv), 0) > HIGH_SPV_MULTIPLIER THEN 21.0 * (0.7 * SAFE_DIVIDE(s.sales_past_7_days, 7.0) + 0.3 * SAFE_DIVIDE(s.sales_past_14_days, 14.0))
      ELSE 14.0 * (0.7 * SAFE_DIVIDE(s.sales_past_7_days, 7.0) + 0.3 * SAFE_DIVIDE(s.sales_past_14_days, 14.0))
    END AS heuristic_forecast_base,
    LEAST(HEURISTIC_SPV_MAX, GREATEST(HEURISTIC_SPV_MIN, 1.0 + 0.20 * (IFNULL(SAFE_DIVIDE(s.sku_spv_past_14d, b.avg_category_spv), 1.0) - 1.0))) AS spv_scale,
    -- [NEW v1.6] 계절성 가중치
    COALESCE(isw.isoweek_factor, spf.decay_factor) AS seasonality_weight,
    CASE
      WHEN isw.isoweek_factor IS NOT NULL THEN 'ISO Week'
      ELSE 'Season Progress'
    END AS seasonality_source
  FROM current_product_status s
  LEFT JOIN current_product_status_longterm s_long ON s.mall_product_code = s_long.mall_product_code
  LEFT JOIN statistical_forecasts_14d st14 ON s.product_type = st14.product_type AND s.base_category_name = st14.base_category_name AND s.decision_isoweek = st14.decision_isoweek AND s.sales_past_7_days_bin = st14.sales_past_7_days_bin AND s.sales_past_14_days_bin = st14.sales_past_14_days_bin
  LEFT JOIN statistical_forecasts_21d st21 ON s.product_type = st21.product_type AND s.base_category_name = st21.base_category_name AND s.decision_isoweek = st21.decision_isoweek AND s.sales_past_7_days_bin = st21.sales_past_7_days_bin AND s.sales_past_14_days_bin = st21.sales_past_14_days_bin
  LEFT JOIN high_spv_candidates h ON s.mall_product_code = h.mall_product_code
  LEFT JOIN category_spv_benchmark b ON s.base_category_name = b.base_category_name
  LEFT JOIN isoweek_seasonality isw ON s.base_category_name = isw.base_category_name AND s.decision_isoweek = isw.isoweek
  CROSS JOIN season_progress_factor spf
),

final_forecasts AS (
  SELECT *,
    CAST(ROUND(CASE
      -- [CHANGED v1.6] High-SPV: 계절성 가중치 적용
      WHEN forecast_level = 'Heuristic (High-SPV)' THEN sales_past_7_days * 2 * seasonality_weight
      -- Statistical: 변경 없음 (이미 ISO week 컨텍스트 반영)
      WHEN forecast_level = 'Statistical' THEN statistical_forecast
      -- [CHANGED v1.6] Adaptive: 계절성 가중치 적용
      ELSE heuristic_forecast_base * spv_scale * seasonality_weight
    END) AS INT64) AS raw_forecast,
    CASE
      WHEN reorder_order >= 5 THEN FALSE
      WHEN relative_spv_index > HIGH_SPV_MULTIPLIER AND sales_past_7_days >= DAILY_VELOCITY_THRESHOLD THEN FALSE
      ELSE TRUE
    END AS apply_qty_cap
  FROM combined_forecasts
)

SELECT
  f.mall_product_code, f.vendor_category, f.base_category_name, f.physical_stock, f.reserved_qty,
  CONCAT(f.product_type, '(', CAST(IFNULL(f.days_since_launch, 0) AS STRING), '일)') AS product_type,
  f.reorder_order, f.forecast_days, f.decision_isoweek,
  f.sales_past_7_days, f.sales_past_14_days, f.sales_past_7_days_bin, f.sales_past_14_days_bin,
  f.sku_spv_past_14d, f.avg_category_spv, f.relative_spv_index, f.forecast_level,
  f.raw_forecast AS forecast_before_cap,
  -- 보수적 발주: (1) 시즌 말 30일 이내 & 기존상품 & 10장 이하 → 0장, (2) 출시 70일+ & 추천 5장 → 0장
  CASE
    WHEN (DATE_DIFF(SEASON_END, CURRENT_DATE(), DAY) <= 30 OR DATE_DIFF(CURRENT_DATE(), SEASON_START, DAY) <= 30)
      AND f.product_type = '기존상품'
      AND (CASE WHEN f.apply_qty_cap THEN LEAST(f.raw_forecast, REORDER_QTY_CAP) ELSE f.raw_forecast END) <= 10
    THEN 0
    WHEN IFNULL(f.days_since_launch, 0) >= 70
      AND (CASE WHEN f.apply_qty_cap THEN LEAST(f.raw_forecast, REORDER_QTY_CAP) ELSE f.raw_forecast END) = 5
    THEN 0
    ELSE CASE WHEN f.apply_qty_cap THEN LEAST(f.raw_forecast, REORDER_QTY_CAP) ELSE f.raw_forecast END
  END AS normal_forecast,
  f.apply_qty_cap,
  IFNULL(f.sales_past_30_days, 0) AS sales_past_30_days,
  IFNULL(f.sales_past_60_days, 0) AS sales_past_60_days,
  IFNULL(f.sales_past_90_days, 0) AS sales_past_90_days,
  IFNULL(f.sales_past_180_days, 0) AS sales_past_180_days,
  CURRENT_DATETIME('Asia/Seoul') AS query_executed_at,
  -- [NEW v1.6] 계절성 디버깅 컬럼 (기존 인덱스 유지를 위해 맨 뒤 배치)
  ROUND(f.seasonality_weight, 3) AS seasonality_weight,
  f.seasonality_source
FROM final_forecasts f
WHERE (f.product_type = '신상품' AND f.relative_spv_index >= RELATIVE_SPV_THRESHOLD_NEW)
   OR (f.product_type <> '신상품' AND f.relative_spv_index >= RELATIVE_SPV_THRESHOLD_EXISTING)
ORDER BY normal_forecast DESC;
