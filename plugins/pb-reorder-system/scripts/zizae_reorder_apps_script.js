/***************************************************
 * Zizae Reorder 자동화 스크립트 (Google Apps Script)
 * 브랜드: 지재
 *
 * 기능:
 *   1. 5.2 리오더 내역 탭에 전체 리오더 기록 (A:날짜, C:바코드, AA:수량)
 *   2. reorder_archive 탭에 아카이빙
 *   3. Slack 알림 발송
 *
 * 변경사항 (v1.4):
 *   - [쿼리 v1.7] seasonality_weight, seasonality_source 컬럼 추가 (Z~AA열)
 *   - REORDER_QTY 인덱스 변경: 27 → 29 (AB열 → AD열)
 *   - rowData 30개 컬럼으로 확장 (A~AD)
 *
 * 변경사항 (v1.3):
 *   - query_executed_at 컬럼 추가 (Y열, 인덱스 24)
 *   - 쿼리 실행 날짜 검증: 오늘 날짜가 아니면 폴백 메시지 발송
 *   - Slack 메시지에 데이터 날짜 표시
 *
 * 변경사항 (v1.2):
 *   - Price Down 상품 제외 로직 추가
 *   - E/F등급 또는 최근 60일 할인 이력 있는 상품 리오더 대상에서 제외
 *
 * 변경사항 (v1.1):
 *   - Slack 유저 멘션 추가 (U0A724SPN2U)
 *
 * 버전: v1.4
 * 작성: 2025-12-12
 ***************************************************/

// ===================== 설정 =====================
var CONFIG = {
  TIMEZONE: 'Asia/Seoul',
  SPREADSHEET_ID: '1MDEQrx_o9YqFmwbiSTDYiG4cJ0tvBpXuUiIYXog15AI',

  // 탭 이름
  SHEET_RAW_REORDER: 'raw_reorder',
  SHEET_REORDER_LOG: '5.2 리오더 내역',
  SHEET_ARCHIVE: 'reorder_archive',

  // 컬럼 인덱스 (0-based)
  // [v1.4] A~AA: 쿼리 출력 (27개), AB~AD: 시트에서 추가 (3개) = 총 30개
  // 쿼리 컬럼: A~Y(기존 25개) + Z(seasonality_weight) + AA(seasonality_source) = 27개
  RAW_REORDER: {
    MALL_PRODUCT_CODE: 0,  // A열: 품번
    VENDOR_CATEGORY: 1,    // B열: vendor_category
    QUERY_EXECUTED_AT: 24, // Y열: 쿼리 실행 시각
    REORDER_QTY: 29        // AD열: 리오더 추천 수량 (시트에서 계산, v1.4 변경)
  },

  // 5.2 리오더 내역 탭 컬럼
  REORDER_LOG_SHEET: {
    COL_A: 0,   // 날짜
    COL_C: 2,   // 바코드 (품번)
    COL_AA: 26  // 수량 (AA열 = 26번 인덱스)
  },

  // Price Down 제외 설정 (v1.2)
  PRICE_DOWN: {
    SHEET_ID: '1D-ildOXLHWx-VRV-w2DRcIOfXompB6BOsPb1PPbv2ig',
    HISTORY_SHEET_NAME: 'history',
    EXCLUSION_DAYS: 60,  // 최근 N일 이내 할인 이력 있으면 제외
    // history 시트 컬럼 인덱스 (0-based)
    COL_DT: 0,             // A: dt (의사결정일)
    COL_PB_CODE: 2,        // C: pb_code
    COL_ROTATION_GRADE: 18, // S: rotation_grade
    COL_DISCOUNT_RATE: 29   // AD: discount_rate
  },

  // Slack 설정
  SLACK_BOT_TOKEN: 'YOUR_SLACK_BOT_TOKEN',
  SLACK_CHANNEL_ID: 'C0ABHFXMLP5',

  // 멘션 대상
  SLACK_SUBTEAM_ID: 'S046U1R861E',
  SLACK_USER_IDS: ['U0A724SPN2U'],  // 추가 멘션할 유저 ID

  // 시트 URL
  SHEET_URL: 'https://docs.google.com/spreadsheets/d/1MDEQrx_o9YqFmwbiSTDYiG4cJ0tvBpXuUiIYXog15AI/edit'
};

// ===================== 메인 함수 =====================

/**
 * 전체 리오더 프로세스 실행
 * 1. 5.2 리오더 내역 탭에 전체 기록
 * 2. 아카이브 저장
 * 3. Slack 알림
 *
 * ※ 평일(월~금)에만 실행, 주말(토/일)은 스킵
 */
function runZizaeReorderProcess() {
  try {
    var today = new Date();
    var todayStr = Utilities.formatDate(today, CONFIG.TIMEZONE, 'yyyy-MM-dd');

    // 평일 체크 (0=일요일, 6=토요일)
    var dayOfWeek = today.getDay();
    if (dayOfWeek === 0 || dayOfWeek === 6) {
      Logger.log('[스킵] 주말에는 리오더 프로세스를 실행하지 않습니다. (' + todayStr + ', 요일: ' + dayOfWeek + ')');
      return;
    }

    var ss = SpreadsheetApp.openById(CONFIG.SPREADSHEET_ID);

    Logger.log('[시작] 지재 리오더 프로세스 (' + todayStr + ')');

    // Step 0: 쿼리 실행 날짜 검증 (v1.3)
    var queryDateInfo = validateQueryExecutedDate(ss);
    if (!queryDateInfo.isToday) {
      Logger.log('[경고] 쿼리 데이터가 오늘 날짜가 아닙니다. 데이터 날짜: ' + queryDateInfo.dateStr);
      postFallbackSlackNotification(todayStr, queryDateInfo.dateStr);
      return;
    }
    Logger.log('[확인] 쿼리 데이터 날짜 확인됨: ' + queryDateInfo.dateStr);

    // Step 1: raw_reorder에서 리오더 대상 추출
    var reorderItems = getReorderItems(ss);

    if (reorderItems.length === 0) {
      Logger.log('[완료] 리오더 대상 없음');
      postSlackNotification(ss, todayStr, [], queryDateInfo);
      return;
    }

    Logger.log('[정보] 리오더 대상: ' + reorderItems.length + '건');

    // Step 2: 5.2 리오더 내역 탭에 전체 기록
    appendToReorderLogSheet(ss, reorderItems, today);

    // Step 3: 아카이브 저장
    archiveReorderItems(ss, reorderItems, today);

    // Step 4: Slack 알림 (v1.3: 데이터 날짜 포함)
    postSlackNotification(ss, todayStr, reorderItems, queryDateInfo);

    Logger.log('[완료] 지재 리오더 프로세스 완료 (' + reorderItems.length + '건 처리)');

  } catch (e) {
    console.error('runZizaeReorderProcess FAILED:', e && e.stack || e);
    throw e;
  }
}

// ===================== Step 0: 쿼리 날짜 검증 (v1.3) =====================

/**
 * raw_reorder 시트의 query_executed_at 컬럼에서 쿼리 실행 날짜 확인
 * 오늘 날짜가 아니면 폴백 처리 필요
 */
function validateQueryExecutedDate(ss) {
  var sheet = ss.getSheetByName(CONFIG.SHEET_RAW_REORDER);
  if (!sheet) {
    return { isToday: false, dateStr: '시트 없음' };
  }

  var data = sheet.getDataRange().getValues();
  if (data.length < 2) {
    return { isToday: false, dateStr: '데이터 없음' };
  }

  // 첫 번째 데이터 행의 query_executed_at 컬럼 확인
  var COL_QUERY_DATE = CONFIG.RAW_REORDER.QUERY_EXECUTED_AT;
  var queryDateValue = data[1][COL_QUERY_DATE];

  if (!queryDateValue) {
    return { isToday: false, dateStr: '날짜 없음' };
  }

  // Date 객체로 변환
  var queryDate;
  if (queryDateValue instanceof Date) {
    queryDate = queryDateValue;
  } else if (typeof queryDateValue === 'string') {
    // DATETIME 형식: "2026-01-09T10:30:00" 또는 "2026-01-09 10:30:00"
    queryDate = new Date(queryDateValue.replace(' ', 'T'));
  } else {
    return { isToday: false, dateStr: String(queryDateValue) };
  }

  var queryDateStr = Utilities.formatDate(queryDate, CONFIG.TIMEZONE, 'yyyy-MM-dd');
  var todayStr = Utilities.formatDate(new Date(), CONFIG.TIMEZONE, 'yyyy-MM-dd');

  return {
    isToday: (queryDateStr === todayStr),
    dateStr: queryDateStr,
    fullDateTime: Utilities.formatDate(queryDate, CONFIG.TIMEZONE, 'yyyy-MM-dd HH:mm:ss')
  };
}

/**
 * 쿼리 날짜가 오늘이 아닐 때 Slack 폴백 메시지 발송
 */
function postFallbackSlackNotification(todayStr, queryDateStr) {
  try {
    ensureSlackChannelJoin(CONFIG.SLACK_CHANNEL_ID);

    // 멘션 문자열 생성 (그룹 + 개인 유저)
    var mentions = '<!subteam^' + CONFIG.SLACK_SUBTEAM_ID + '>';
    if (CONFIG.SLACK_USER_IDS && CONFIG.SLACK_USER_IDS.length > 0) {
      mentions += ' ' + CONFIG.SLACK_USER_IDS.map(function(uid) {
        return '<@' + uid + '>';
      }).join(' ');
    }

    var warningText = ':warning: *지재 리오더 데이터 갱신 필요*\n\n' +
      '━━━━━━━━━━━━━━━━━━━━━━\n' +
      '• 오늘 날짜: *' + todayStr + '*\n' +
      '• 쿼리 데이터 날짜: *' + queryDateStr + '*\n' +
      '━━━━━━━━━━━━━━━━━━━━━━\n\n' +
      '데이터가 최신이 아닙니다.\n' +
      '*테이블을 업데이트*해 주세요.\n\n' +
      '<' + CONFIG.SHEET_URL + '|시트 바로가기>\n\n' +
      mentions;

    var blocks = [
      {
        type: 'header',
        text: { type: 'plain_text', text: '⚠️ 지재 리오더 - 데이터 갱신 필요' }
      },
      {
        type: 'section',
        text: { type: 'mrkdwn', text: warningText }
      }
    ];

    chatPostMessageOrThrow({
      channel: CONFIG.SLACK_CHANNEL_ID,
      text: '지재 리오더 데이터 갱신 필요 (' + todayStr + ')',
      blocks: blocks
    });

    Logger.log('[완료] 폴백 Slack 알림 발송');

  } catch (e) {
    console.error('폴백 Slack 알림 실패:', e && e.message || e);
  }
}

// ===================== Price Down 제외 로직 (v1.2) =====================

/**
 * pb_price_down history 시트에서 제외 대상 pb_code 목록 추출
 * 제외 조건: E/F등급 OR 최근 60일 이내 할인 이력
 */
function getExcludedPbCodes() {
  try {
    var priceDownSS = SpreadsheetApp.openById(CONFIG.PRICE_DOWN.SHEET_ID);
    var historySheet = priceDownSS.getSheetByName(CONFIG.PRICE_DOWN.HISTORY_SHEET_NAME);

    if (!historySheet) {
      Logger.log('[경고] Price Down history 시트를 찾을 수 없습니다. 제외 없이 진행합니다.');
      return {};
    }

    var data = historySheet.getDataRange().getValues();
    if (data.length < 2) return {};

    var excludedPbCodes = {};
    var cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - CONFIG.PRICE_DOWN.EXCLUSION_DAYS);

    var COL_DT = CONFIG.PRICE_DOWN.COL_DT;
    var COL_PB_CODE = CONFIG.PRICE_DOWN.COL_PB_CODE;
    var COL_GRADE = CONFIG.PRICE_DOWN.COL_ROTATION_GRADE;
    var COL_DISCOUNT = CONFIG.PRICE_DOWN.COL_DISCOUNT_RATE;

    // 헤더 제외
    for (var r = 1; r < data.length; r++) {
      var row = data[r];
      var dt = row[COL_DT];
      var pbCode = safeString(row[COL_PB_CODE]);
      var rotationGrade = safeString(row[COL_GRADE]).toUpperCase();
      var discountRate = toNumberOrNull(row[COL_DISCOUNT]);

      if (!pbCode) continue;

      // 날짜 파싱
      var recordDate = null;
      if (dt instanceof Date) {
        recordDate = dt;
      } else if (typeof dt === 'string' && dt.length > 0) {
        recordDate = new Date(dt);
      }

      // 제외 조건 1: E/F 등급 (악성재고)
      var isEFGrade = (rotationGrade === 'E' || rotationGrade === 'F');

      // 제외 조건 2: 최근 60일 이내 할인 이력
      var hasRecentDiscount = false;
      if (recordDate && !isNaN(recordDate.getTime())) {
        hasRecentDiscount = (recordDate >= cutoffDate && discountRate > 0);
      }

      if (isEFGrade || hasRecentDiscount) {
        // 같은 pb_code의 경우 가장 최근 기록 유지
        if (!excludedPbCodes[pbCode] ||
            (recordDate && excludedPbCodes[pbCode].dt < recordDate)) {
          excludedPbCodes[pbCode] = {
            grade: rotationGrade,
            discountRate: discountRate,
            dt: recordDate,
            reason: isEFGrade ? 'E/F등급' : '할인이력'
          };
        }
      }
    }

    Logger.log('[정보] Price Down 제외 대상: ' + Object.keys(excludedPbCodes).length + '개 pb_code');
    return excludedPbCodes;

  } catch (e) {
    Logger.log('[경고] Price Down 시트 읽기 실패: ' + (e.message || e) + '. 제외 없이 진행합니다.');
    return {};
  }
}

/**
 * mall_product_code에서 pb_code 추출
 * 예: 'ZE25F001_BLACK_FREE' → 'ZE25F001'
 *     'D2_ZE25S001_WHITE_M' → 'ZE25S001'
 */
function extractPbCode(mallProductCode) {
  if (!mallProductCode) return '';

  // 패턴: 브랜드(2자리) + 연도(2자리) + 카테고리(1~3자리 알파벳) + 번호(3자리)
  // 예: NR25WDP005, QU25S001, VD25F012, ZE25W001, DN25S001
  var match = mallProductCode.match(/^([A-Z]{2}\d{2}[A-Z]{1,3}\d{3})/);
  if (match) return match[1];

  // 폴백: 기존 언더스코어 분리 방식
  var parts = mallProductCode.split('_');
  if (parts.length === 0) return mallProductCode;

  // D2로 시작하면 두 번째 부분이 pb_code
  if (parts[0] === 'D2' && parts.length > 1) {
    return parts[1];
  }

  // 그 외에는 첫 번째 부분이 pb_code
  return parts[0];
}

// ===================== Step 1: 리오더 대상 추출 =====================

/**
 * raw_reorder 탭에서 리오더 대상 추출
 * AF열(reorder_qty_normal_30d) > 0인 항목만
 * [v1.2] Price Down 상품(E/F등급, 할인이력) 제외
 */
function getReorderItems(ss) {
  var sheet = ss.getSheetByName(CONFIG.SHEET_RAW_REORDER);
  if (!sheet) throw new Error('시트를 찾을 수 없습니다: ' + CONFIG.SHEET_RAW_REORDER);

  var data = sheet.getDataRange().getValues();
  if (data.length < 2) return [];

  // [v1.2] Price Down 제외 대상 로드
  var excludedPbCodes = getExcludedPbCodes();
  var excludedCount = 0;

  var items = [];
  var COL_CODE = CONFIG.RAW_REORDER.MALL_PRODUCT_CODE;
  var COL_VENDOR = CONFIG.RAW_REORDER.VENDOR_CATEGORY;
  var COL_QTY = CONFIG.RAW_REORDER.REORDER_QTY;

  // 헤더 제외, 데이터만
  for (var r = 1; r < data.length; r++) {
    var row = data[r];
    var productCode = safeString(row[COL_CODE]);
    var vendorCategory = safeString(row[COL_VENDOR]);
    var reorderQty = toNumberOrNull(row[COL_QTY]);

    // AF열 값이 0보다 큰 경우만
    if (reorderQty !== null && reorderQty > 0) {
      // [v1.2] Price Down 제외 체크
      var pbCode = extractPbCode(productCode);
      if (excludedPbCodes[pbCode]) {
        var exclusion = excludedPbCodes[pbCode];
        Logger.log('[제외] ' + productCode + ' (pb_code: ' + pbCode + ', 사유: ' + exclusion.reason + ')');
        excludedCount++;
        continue;
      }

      items.push({
        rowData: row.slice(0, 30),  // A~AD (30개 컬럼, v1.4 seasonality 컬럼 추가)
        productCode: productCode,
        vendorCategory: vendorCategory,
        reorderQty: reorderQty
      });
    }
  }

  if (excludedCount > 0) {
    Logger.log('[정보] Price Down 제외: ' + excludedCount + '개 SKU');
  }

  return items;
}

// ===================== Step 2: 5.2 리오더 내역 탭에 기록 =====================

/**
 * 5.2 리오더 내역 탭에 전체 리오더 항목 추가
 * A열: 날짜, C열: 바코드, AA열: 수량
 */
function appendToReorderLogSheet(ss, reorderItems, today) {
  var sheet = ss.getSheetByName(CONFIG.SHEET_REORDER_LOG);
  if (!sheet) throw new Error('시트를 찾을 수 없습니다: ' + CONFIG.SHEET_REORDER_LOG);

  var todayStr = Utilities.formatDate(today, CONFIG.TIMEZONE, 'yyyy-MM-dd');

  // A열 기준 마지막 데이터 행 찾기
  var colA = sheet.getRange('A:A').getValues();
  var lastDataRow = 0;
  for (var i = colA.length - 1; i >= 0; i--) {
    if (colA[i][0] !== '' && colA[i][0] !== null) {
      lastDataRow = i + 1;
      break;
    }
  }
  var startRow = lastDataRow + 1;

  // 추가할 데이터 준비 (A~AA = 27개 컬럼)
  var rowsToAdd = reorderItems.map(function(item) {
    var newRow = new Array(27).fill('');  // A~AA (27개)
    newRow[CONFIG.REORDER_LOG_SHEET.COL_A] = todayStr;          // A열: 날짜
    newRow[CONFIG.REORDER_LOG_SHEET.COL_C] = item.productCode;  // C열: 바코드
    newRow[CONFIG.REORDER_LOG_SHEET.COL_AA] = item.reorderQty;  // AA열: 수량
    return newRow;
  });

  // 일괄 추가
  if (rowsToAdd.length > 0) {
    var range = sheet.getRange(startRow, 1, rowsToAdd.length, rowsToAdd[0].length);
    range.setValues(rowsToAdd);
    Logger.log('[완료] 5.2 리오더 내역 탭에 ' + rowsToAdd.length + '건 추가 (행 ' + startRow + '부터)');
  }
}

// ===================== Step 3: 아카이브 저장 =====================

/**
 * reorder_archive 탭에 리오더 기록 저장
 * 날짜 + raw_reorder의 전체 컬럼
 */
function archiveReorderItems(ss, reorderItems, today) {
  var sheet = ss.getSheetByName(CONFIG.SHEET_ARCHIVE);

  // 시트가 없으면 생성
  if (!sheet) {
    sheet = ss.insertSheet(CONFIG.SHEET_ARCHIVE);
    // 헤더 추가
    var headers = [
      '실행일자',
      'mall_product_code', 'vendor_category', 'base_category_name', 'physical_stock', 'reserved_qty',
      'product_type', 'decision_isoweek', 'sales_past_7_days', 'sales_past_14_days',
      'sales_past_7_days_bin', 'sales_past_14_days_bin', 'sku_spv_past_14d',
      'avg_category_spv', 'relative_spv_index', 'forecast_level',
      'conservative_forecast_30d', 'normal_forecast_30d', 'aggressive_forecast_30d',
      'conservative_forecast_60d', 'conservative_forecast_90d', 'conservative_forecast_180d',
      'sales_past_30_days', 'sales_past_60_days', 'sales_past_90_days', 'sales_past_180_days',
      'reorder_qty_conservative_30d', 'reorder_qty_normal_30d', 'reorder_qty_aggressive_30d',
      'reorder_qty_conservative_60d', 'reorder_qty_conservative_90d', 'reorder_qty_conservative_180d'
    ];
    sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
    Logger.log('[정보] reorder_archive 시트 생성됨');
  }

  var todayStr = Utilities.formatDate(today, CONFIG.TIMEZONE, 'yyyy-MM-dd');

  // A열 기준 마지막 데이터 행 찾기
  var colA = sheet.getRange('A:A').getValues();
  var lastDataRow = 0;
  for (var i = colA.length - 1; i >= 0; i--) {
    if (colA[i][0] !== '' && colA[i][0] !== null) {
      lastDataRow = i + 1;
      break;
    }
  }
  var startRow = lastDataRow + 1;

  // 아카이브 데이터 준비 (날짜 + 전체 컬럼)
  var archiveRows = reorderItems.map(function(item) {
    return [todayStr].concat(item.rowData);
  });

  if (archiveRows.length > 0) {
    var range = sheet.getRange(startRow, 1, archiveRows.length, archiveRows[0].length);
    range.setValues(archiveRows);
    Logger.log('[완료] 아카이브에 ' + archiveRows.length + '건 저장');
  }
}

// ===================== Step 4: Slack 알림 =====================

/**
 * Slack 채널에 리오더 결과 알림 발송
 * [v1.3] queryDateInfo 파라미터 추가 - 데이터 날짜 표시
 */
function postSlackNotification(ss, todayStr, reorderItems, queryDateInfo) {
  try {
    ensureSlackChannelJoin(CONFIG.SLACK_CHANNEL_ID);

    var totalQty = reorderItems.reduce(function(sum, item) {
      return sum + item.reorderQty;
    }, 0);
    var itemCount = reorderItems.length;

    // 메인 메시지 블록 구성 (v1.3: 데이터 날짜 포함)
    var blocks = buildSlackBlocks(todayStr, itemCount, totalQty, queryDateInfo);

    // 메인 메시지 발송
    var mainRes = chatPostMessageOrThrow({
      channel: CONFIG.SLACK_CHANNEL_ID,
      text: '지재 리오더 완료 (' + todayStr + ')',
      blocks: blocks
    });

    var threadTs = mainRes.ts;
    if (!threadTs || reorderItems.length === 0) return;

    // 쓰레드에 상세 목록 발송 (20개씩 분할)
    var chunkSize = 20;
    for (var i = 0; i < reorderItems.length; i += chunkSize) {
      var chunk = reorderItems.slice(i, i + chunkSize);
      var detailLines = chunk.map(function(item) {
        return '• ' + item.productCode + ': ' + item.reorderQty + '장';
      });
      var detailText = detailLines.join('\n');

      var startIdx = i + 1;
      var endIdx = Math.min(i + chunkSize, reorderItems.length);

      chatPostMessageOrThrow({
        channel: CONFIG.SLACK_CHANNEL_ID,
        thread_ts: threadTs,
        text: '*리오더 상세 (' + startIdx + '~' + endIdx + ')*\n' + detailText
      });
    }

    Logger.log('[완료] Slack 알림 발송');

  } catch (e) {
    console.error('Slack 알림 실패:', e && e.message || e);
    // Slack 실패해도 프로세스는 계속
  }
}

/**
 * Slack 메시지 블록 구성
 * [v1.3] queryDateInfo 파라미터 추가 - 데이터 날짜 표시
 */
function buildSlackBlocks(todayStr, itemCount, totalQty, queryDateInfo) {
  var summaryText;
  var dataDateStr = queryDateInfo ? queryDateInfo.fullDateTime : todayStr;

  // 멘션 문자열 생성 (그룹 + 개인 유저)
  var mentions = '<!subteam^' + CONFIG.SLACK_SUBTEAM_ID + '>';
  if (CONFIG.SLACK_USER_IDS && CONFIG.SLACK_USER_IDS.length > 0) {
    mentions += ' ' + CONFIG.SLACK_USER_IDS.map(function(uid) {
      return '<@' + uid + '>';
    }).join(' ');
  }

  if (itemCount > 0) {
    summaryText = '━━━━━━━━━━━━━━━━━━━━━━\n' +
      '*리오더 요약*\n' +
      '• 품번 수: ' + itemCount + '개\n' +
      '• 총 수량: ' + totalQty + '장\n' +
      '• 데이터 기준: ' + dataDateStr + '\n' +
      '━━━━━━━━━━━━━━━━━━━━━━\n\n' +
      '<' + CONFIG.SHEET_URL + '|시트 바로가기>\n\n' +
      mentions;
  } else {
    summaryText = '━━━━━━━━━━━━━━━━━━━━━━\n' +
      '*리오더 대상 없음*\n' +
      '오늘은 리오더할 항목이 없습니다.\n' +
      '• 데이터 기준: ' + dataDateStr + '\n' +
      '━━━━━━━━━━━━━━━━━━━━━━\n\n' +
      mentions;
  }

  return [
    {
      type: 'header',
      text: { type: 'plain_text', text: '지재 리오더 완료 (' + todayStr + ')' }
    },
    {
      type: 'section',
      text: { type: 'mrkdwn', text: summaryText }
    },
    {
      type: 'context',
      elements: [{ type: 'mrkdwn', text: '_상세 목록은 쓰레드를 확인하세요._' }]
    }
  ];
}

// ===================== Slack API 유틸 =====================

function slackApiCall(method, payload) {
  var url = 'https://slack.com/api/' + method;
  var params = {
    method: 'post',
    contentType: 'application/json; charset=utf-8',
    headers: { Authorization: 'Bearer ' + CONFIG.SLACK_BOT_TOKEN },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true
  };
  var res = UrlFetchApp.fetch(url, params);
  return JSON.parse(res.getContentText() || '{}');
}

function chatPostMessageOrThrow(payload) {
  var json = slackApiCall('chat.postMessage', payload);
  if (!json.ok) throw new Error('Slack chat.postMessage 실패: ' + JSON.stringify(json));
  return json;
}

function ensureSlackChannelJoin(channelId) {
  try {
    var res = slackApiCall('conversations.join', { channel: channelId });
    if (!res.ok && res.error !== 'method_not_supported_for_channel_type' && res.error !== 'already_in_channel') {
      console.warn('conversations.join 경고:', res);
    }
  } catch (e) {
    console.warn('conversations.join 실패(무시 가능):', e && e.message || e);
  }
}

// ===================== 공통 유틸 =====================

function safeString(v) {
  if (v === null || v === undefined) return '';
  return String(v).trim();
}

function toNumberOrNull(v) {
  if (v === null || v === undefined || v === '') return null;
  var n = Number(v);
  return isFinite(n) ? n : null;
}

// ===================== 테스트 함수 =====================

/**
 * 테스트: Price Down 제외 대상 확인
 */
function testPriceDownExclusion() {
  var excluded = getExcludedPbCodes();

  Logger.log('=== Price Down 제외 대상 테스트 ===');
  Logger.log('총 제외 pb_code: ' + Object.keys(excluded).length + '개');

  // 등급별 분포
  var byGrade = {E: 0, F: 0};
  var byDiscount = 0;

  for (var code in excluded) {
    var info = excluded[code];
    if (info.reason === 'E/F등급') {
      byGrade[info.grade] = (byGrade[info.grade] || 0) + 1;
    } else {
      byDiscount++;
    }
  }

  Logger.log('E등급: ' + (byGrade.E || 0) + '개');
  Logger.log('F등급: ' + (byGrade.F || 0) + '개');
  Logger.log('할인이력: ' + byDiscount + '개');

  // 처음 10개만 출력
  var codes = Object.keys(excluded).slice(0, 10);
  Logger.log('샘플 (처음 10개):');
  codes.forEach(function(code) {
    var info = excluded[code];
    Logger.log('  - ' + code + ': ' + info.reason + ' (등급: ' + info.grade + ', 할인율: ' + (info.discountRate || 0) + ')');
  });
}

/**
 * 테스트: pb_code 추출 함수 검증
 */
function testExtractPbCode() {
  var testCases = [
    'ZE25F001_BLACK_FREE',
    'ZE25S001_WHITE_M',
    'D2_ZE25F001_BEIGE_L',
    'ZE25W001',
    'ZE_TEST_001_S'
  ];

  Logger.log('=== pb_code 추출 테스트 ===');
  testCases.forEach(function(code) {
    Logger.log(code + ' → ' + extractPbCode(code));
  });
}

/**
 * 테스트: 5.2 리오더 내역 탭에 붙여넣기만 테스트 (2건 더미 데이터)
 */
function testAppendToReorderLogSheet() {
  var ss = SpreadsheetApp.openById(CONFIG.SPREADSHEET_ID);
  var today = new Date();

  // 테스트용 더미 데이터 2건
  var testItems = [
    { productCode: 'ZE_TEST_001', vendorCategory: '동대문', reorderQty: 10 },
    { productCode: 'ZE_TEST_002', vendorCategory: '해외', reorderQty: 15 }
  ];

  appendToReorderLogSheet(ss, testItems, today);
  Logger.log('[테스트 완료] 5.2 리오더 내역 탭에 ' + testItems.length + '건 추가됨');
}

/**
 * 테스트: 아카이브 탭에 붙여넣기만 테스트 (2건 더미 데이터)
 */
function testArchiveReorderItems() {
  var ss = SpreadsheetApp.openById(CONFIG.SPREADSHEET_ID);
  var today = new Date();

  // 테스트용 더미 데이터 (31개 컬럼: A~AE)
  var dummyRowData = new Array(31).fill('TEST');
  dummyRowData[0] = 'ZE_TEST_001';  // A열: 품번
  dummyRowData[1] = '동대문';        // B열: vendor_category

  var testItems = [
    { rowData: dummyRowData, productCode: 'ZE_TEST_001', vendorCategory: '동대문', reorderQty: 10 }
  ];

  archiveReorderItems(ss, testItems, today);
  Logger.log('[테스트 완료] 아카이브에 ' + testItems.length + '건 추가됨');
}

/**
 * 테스트: 리오더 대상만 확인 (실제 기입하지 않음)
 */
function testGetReorderItems() {
  var ss = SpreadsheetApp.openById(CONFIG.SPREADSHEET_ID);
  var items = getReorderItems(ss);

  Logger.log('리오더 대상: ' + items.length + '건');
  items.forEach(function(item, i) {
    Logger.log((i + 1) + '. ' + item.productCode + ': ' + item.reorderQty + '장');
  });
}

/**
 * 테스트: Slack 메시지만 발송
 */
function testSlackNotification() {
  var ss = SpreadsheetApp.openById(CONFIG.SPREADSHEET_ID);
  var today = new Date();
  var todayStr = Utilities.formatDate(today, CONFIG.TIMEZONE, 'yyyy-MM-dd');

  // 테스트용 더미 데이터
  var testItems = [
    { productCode: 'ZE_TEST_001', reorderQty: 10 },
    { productCode: 'ZE_TEST_002', reorderQty: 15 }
  ];

  postSlackNotification(ss, todayStr, testItems);
}
