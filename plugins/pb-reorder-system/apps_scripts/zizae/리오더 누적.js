/**
 * ============================================================
 * 라포랩스 동대문 사입 관리 + 카카오톡 자동 전송 통합 스크립트
 * ============================================================
 *
 * 동작 순서:
 * 1. runSync() 실행 → 데이터 동기화
 * 2. ★사입자확인시트★ 업데이트 완료
 * 3. 자동으로 각 업체에 카카오톡 전송
 * 4. Slack 알림 전송 (시작/종료/실패)
 */

// ╔════════════════════════════════════════════════════════════╗
// ║                    🔧 주요 설정 (상단)                      ║
// ╚════════════════════════════════════════════════════════════╝

// 카카오톡 관리자 채팅방 ID (브랜드 완료 알림 전송용)
var ADMIN_CHAT_ID = '296621596398969';

// Slack 채널 ID (스레드 알림용)
var SLACK_CHANNEL_ID = 'C0ABHFXMLP5';

// Slack Bot Token (스레드 기능용)
var SLACK_BOT_TOKEN = 'YOUR_SLACK_BOT_TOKEN';

// Slack Webhook URL (fallback용)
var SLACK_WEBHOOK_URL = 'YOUR_SLACK_WEBHOOK_URL';

// ==================== 데이터 동기화 설정 ====================

var SOURCE_SS_ID = '1REQ0yyJX3461gRaQggZP16poY4ExG5Xb7KykbjSkAjA'; // 사입자시트ID
var TARGET_SS_ID = '1MDEQrx_o9YqFmwbiSTDYiG4cJ0tvBpXuUiIYXog15AI'; // 리오더시트ID

var SRC_SHEET_NAME_PURCHASE = '★사입자확인시트★';
var TGT_SHEET_NAME_CUMUL    = '동대문 누적';
var TGT_SHEET_NAME_REORDER  = '발주(리오더)_동대문';

var HEADER_ROWS = 2;
var DATA_START_ROW = HEADER_ROWS + 1;

var COL_A = 1;
var COL_D = 4;
var COL_H = 8;
var COL_O = 15;
var COL_P = 16;

var WIDTH_A_TO_R = 18;
var WIDTH_A_TO_V = 22;

var CHUNK_ROWS_BIG = 1000;
var CHUNK_ROWS_SMALL = 500;
var RETRIES = 5;
var BASE_SLEEP_MS = 400;

// ==================== 카카오톡 전송 설정 ====================

const KAKAO_CONFIG = {
  VENDOR_INFO_SHEET: '업체 정보',
  VENDOR_NAME_COL: 7,
  KAKAO_ID_COL: 17,
  VENDOR_NAME_COL_INFO: 1,
  TARGET_COLUMNS: [1, 3, 7, 8, 9, 10, 11, 12, 13, 18]
};

var IMAGE_ROWS_PER_PAGE = 20;

// ==================== Slack 설정 ====================

const SLACK_CONFIG = {
  WEBHOOK_URL: SLACK_WEBHOOK_URL,
  CHANNEL: SLACK_CHANNEL_ID,
  ENABLED: true,
  BOT_TOKEN: SLACK_BOT_TOKEN,
  USE_THREAD: true
};

// 실패한 전송 항목 저장용 (PropertiesService 사용)
var FAILED_VENDORS_KEY = 'FAILED_VENDORS_LIST';
var SLACK_THREAD_TS_KEY = 'SLACK_THREAD_TS';  // 스레드 ID 저장용

// 진행 상태 저장용 (시간 초과 대비)
var PROGRESS_STATE_KEY = 'KAKAO_PROGRESS_STATE';
var MAX_EXECUTION_TIME_MS = 5 * 60 * 1000;  // 5분 (Google Apps Script 제한: 6분)

// ==================== Slack 알림 함수 ====================

/**
 * Slack API로 메시지 전송 (스레드 지원)
 * @param {string} message - 전송할 메시지
 * @param {string} threadTs - 스레드의 부모 메시지 timestamp (옵션)
 * @returns {string|null} 메시지의 ts (스레드용) 또는 null
 */
function sendSlackMessageWithApi(message, threadTs) {
  if (!SLACK_CONFIG.ENABLED || !SLACK_CONFIG.BOT_TOKEN) {
    Logger.log('⚠️ Slack Bot Token이 설정되지 않았습니다. Webhook으로 전송합니다.');
    return sendSlackMessageWithWebhook(message);
  }

  var payload = {
    'channel': SLACK_CONFIG.CHANNEL,
    'text': message,
    'mrkdwn': true
  };

  // 스레드로 보내기
  if (threadTs) {
    payload['thread_ts'] = threadTs;
  }

  var options = {
    'method': 'post',
    'contentType': 'application/json',
    'headers': {
      'Authorization': 'Bearer ' + SLACK_CONFIG.BOT_TOKEN
    },
    'payload': JSON.stringify(payload),
    'muteHttpExceptions': true
  };

  try {
    var response = UrlFetchApp.fetch('https://slack.com/api/chat.postMessage', options);
    var result = JSON.parse(response.getContentText());

    if (result.ok) {
      Logger.log('✅ Slack API 메시지 전송 성공 (ts: ' + result.ts + ')');
      return result.ts;  // 메시지 timestamp 반환 (스레드용)
    } else {
      Logger.log('❌ Slack API 전송 실패: ' + result.error);
      // 실패 시 Webhook으로 fallback
      return sendSlackMessageWithWebhook(message);
    }
  } catch (error) {
    Logger.log('❌ Slack API 오류: ' + error.toString());
    return sendSlackMessageWithWebhook(message);
  }
}

/**
 * Slack Webhook으로 메시지 전송 (스레드 미지원)
 */
function sendSlackMessageWithWebhook(message, emoji) {
  if (!SLACK_CONFIG.ENABLED || !SLACK_CONFIG.WEBHOOK_URL) {
    Logger.log('⚠️ Slack 알림이 비활성화되어 있거나 Webhook URL이 설정되지 않았습니다.');
    return null;
  }

  emoji = emoji || ':robot_face:';

  var payload = {
    'text': message,
    'icon_emoji': emoji,
    'username': '카카오톡 발송 봇'
  };

  var options = {
    'method': 'post',
    'contentType': 'application/json',
    'payload': JSON.stringify(payload),
    'muteHttpExceptions': true
  };

  try {
    var response = UrlFetchApp.fetch(SLACK_CONFIG.WEBHOOK_URL, options);
    var responseCode = response.getResponseCode();

    if (responseCode === 200) {
      Logger.log('✅ Slack Webhook 메시지 전송 성공');
      return 'webhook';  // Webhook은 ts를 반환하지 않음
    } else {
      Logger.log('❌ Slack Webhook 전송 실패: ' + response.getContentText());
      return null;
    }
  } catch (error) {
    Logger.log('❌ Slack Webhook 오류: ' + error.toString());
    return null;
  }
}

/**
 * Slack 메시지 전송 (자동 선택: API 또는 Webhook)
 */
function sendSlackMessage(message, emoji, threadTs) {
  if (SLACK_CONFIG.BOT_TOKEN && SLACK_CONFIG.USE_THREAD) {
    return sendSlackMessageWithApi(message, threadTs);
  } else {
    return sendSlackMessageWithWebhook(message, emoji);
  }
}

/**
 * 스레드 ts 저장
 */
function saveSlackThreadTs(ts) {
  var props = PropertiesService.getScriptProperties();
  props.setProperty(SLACK_THREAD_TS_KEY, ts || '');
}

/**
 * 스레드 ts 불러오기
 */
function loadSlackThreadTs() {
  var props = PropertiesService.getScriptProperties();
  return props.getProperty(SLACK_THREAD_TS_KEY) || '';
}

/**
 * 스레드 ts 초기화
 */
function clearSlackThreadTs() {
  var props = PropertiesService.getScriptProperties();
  props.deleteProperty(SLACK_THREAD_TS_KEY);
}

/**
 * 시작 알림 전송 (브랜드명 + 카톡 알림 발송 시작)
 */
function sendSlackStartNotification(brandList, vendorCount, todayCount, previousCount) {
  var today = Utilities.formatDate(new Date(), 'Asia/Seoul', 'yyyy-MM-dd HH:mm:ss');
  var brandText = brandList.length > 0 ? '"' + brandList.join('", "') + '"' : '(브랜드 없음)';

  var message = ':speech_balloon: *' + brandText + '* 카톡 알림 발송 시작\n\n';
  message += '`' + today + '`\n';
  message += '*전송 대상:* ' + vendorCount + '개 업체 (오늘 ' + todayCount + ' / 기발주 ' + previousCount + ')';

  // 시작 메시지 전송 후 ts 저장 (스레드용)
  var ts = sendSlackMessage(message, ':speech_balloon:', null);

  if (ts && ts !== 'webhook') {
    saveSlackThreadTs(ts);
    Logger.log('📝 Slack 스레드 ts 저장: ' + ts);
  } else {
    clearSlackThreadTs();
  }
}

/**
 * 종료 알림 전송 (스레드로)
 */
function sendSlackEndNotification(successCount, failCount, failedVendors, totalMessages) {
  var today = Utilities.formatDate(new Date(), 'Asia/Seoul', 'yyyy-MM-dd HH:mm:ss');

  var emoji = failCount > 0 ? ':warning:' : ':white_check_mark:';
  var statusText = failCount > 0 ? '일부 실패' : '완료';

  var message = emoji + ' *발송 ' + statusText + '*\n\n';
  message += '• 업체 수: ' + (successCount + failCount) + '개\n';
  message += '• 성공: ' + successCount + '건\n';
  message += '• 실패: ' + failCount + '건';

  if (failCount > 0 && failedVendors && failedVendors.length > 0) {
    message += '\n\n:x: *실패한 업체:*\n';
    // 최대 10개까지만 표시
    var displayCount = Math.min(failedVendors.length, 10);
    for (var i = 0; i < displayCount; i++) {
      var fv = failedVendors[i];
      if (typeof fv === 'object' && fv.name) {
        message += '• ' + fv.name + ' (' + getFailedTypeText(fv) + ')\n';
      } else {
        message += '• ' + fv + '\n';
      }
    }
    if (failedVendors.length > 10) {
      message += '• ... 외 ' + (failedVendors.length - 10) + '개\n';
    }

    // 재전송 안내 추가
    message += '\n:arrow_forward: `retryFailedVendors()` 실행하여 재전송하세요.';
  }

  // 저장된 스레드 ts 불러와서 스레드로 전송
  var threadTs = loadSlackThreadTs();

  if (threadTs && SLACK_CONFIG.BOT_TOKEN && SLACK_CONFIG.USE_THREAD) {
    sendSlackMessage(message, emoji, threadTs);
    Logger.log('📝 Slack 스레드로 종료 알림 전송 (thread_ts: ' + threadTs + ')');
  } else {
    sendSlackMessage(message, emoji, null);
  }

  // 실패가 있으면 스레드 ts 유지 (재전송 알림이 같은 스레드에 이어지도록)
  if (failCount > 0) {
    Logger.log('📝 실패 건이 있어 스레드 ts 유지 (재전송용)');
  } else {
    clearSlackThreadTs();
  }
}

/**
 * 에러 알림 전송 (스레드로)
 */
function sendSlackErrorNotification(errorMessage) {
  var today = Utilities.formatDate(new Date(), 'Asia/Seoul', 'yyyy-MM-dd HH:mm:ss');

  var message = ':rotating_light: *오류 발생*\n\n';
  message += '`' + today + '`\n\n';
  message += '*에러:* ' + errorMessage;

  // 저장된 스레드 ts 불러와서 스레드로 전송
  var threadTs = loadSlackThreadTs();

  if (threadTs && SLACK_CONFIG.BOT_TOKEN && SLACK_CONFIG.USE_THREAD) {
    sendSlackMessage(message, ':rotating_light:', threadTs);
  } else {
    sendSlackMessage(message, ':rotating_light:', null);
  }

  // 스레드 ts 초기화
  clearSlackThreadTs();
}

/**
 * 재전송 시작 알림 전송 (실패한 업체 재전송)
 */
function sendSlackRetryStartNotification(failedVendors) {
  var today = Utilities.formatDate(new Date(), 'Asia/Seoul', 'yyyy-MM-dd HH:mm:ss');

  var message = ':arrows_counterclockwise: *실패 업체 재전송 시작*\n\n';
  message += '`' + today + '`\n';
  message += '*재전송 대상:* ' + failedVendors.length + '개 업체\n\n';

  // 업체 목록 (최대 10개까지 표시)
  var displayCount = Math.min(failedVendors.length, 10);
  message += '*업체 목록:*' + (failedVendors.length > 10 ? ' (처음 10개)' : '') + '\n';
  for (var i = 0; i < displayCount; i++) {
    var fv = failedVendors[i];
    if (typeof fv === 'object' && fv.name) {
      message += '• ' + fv.name + ' (' + getFailedTypeText(fv) + ')\n';
    } else {
      message += '• ' + fv + '\n';
    }
  }
  if (failedVendors.length > 10) {
    message += '• ... 외 ' + (failedVendors.length - 10) + '개\n';
  }

  // 기존 스레드 ts 불러와서 스레드로 전송 (같은 스레드에 이어서)
  var threadTs = loadSlackThreadTs();

  if (threadTs && SLACK_CONFIG.BOT_TOKEN && SLACK_CONFIG.USE_THREAD) {
    sendSlackMessage(message, ':arrows_counterclockwise:', threadTs);
    Logger.log('📝 Slack 스레드로 재전송 시작 알림 전송 (thread_ts: ' + threadTs + ')');
  } else {
    // 기존 스레드가 없으면 새 메시지로 전송 후 ts 저장
    var ts = sendSlackMessage(message, ':arrows_counterclockwise:', null);
    if (ts && ts !== 'webhook') {
      saveSlackThreadTs(ts);
      Logger.log('📝 Slack 스레드 ts 저장 (재전송): ' + ts);
    }
  }
}

// ==================== 실패 목록 관리 함수 ====================

/**
 * 실패한 업체 목록 저장
 */
function saveFailedVendors(vendors) {
  var props = PropertiesService.getScriptProperties();
  props.setProperty(FAILED_VENDORS_KEY, JSON.stringify(vendors));
}

/**
 * 실패한 업체 목록 불러오기
 * 형식: [{name: "업체명", today: true/false, previous: true/false}, ...]
 */
function loadFailedVendors() {
  var props = PropertiesService.getScriptProperties();
  var stored = props.getProperty(FAILED_VENDORS_KEY);
  if (!stored) return [];

  var parsed = JSON.parse(stored);

  // 이전 형식 (문자열 배열) 호환 처리
  if (parsed.length > 0 && typeof parsed[0] === 'string') {
    return parsed.map(function(name) {
      return { name: name, today: true, previous: true };
    });
  }

  return parsed;
}

/**
 * 실패한 업체 목록 초기화
 */
function clearFailedVendors() {
  var props = PropertiesService.getScriptProperties();
  props.deleteProperty(FAILED_VENDORS_KEY);
}

/**
 * 실패 목록에서 업체 정보 조회
 * @returns {Object|null} {name, today, previous} 또는 null
 */
function getFailedVendorInfo(failedList, vendorName) {
  for (var i = 0; i < failedList.length; i++) {
    if (failedList[i].name === vendorName) return failedList[i];
  }
  return null;
}

/**
 * 실패 목록에 업체 추가/갱신 (실패 유형을 정확히 세팅)
 */
function addOrUpdateFailedVendor(failedList, vendorName, todayFailed, previousFailed) {
  var existing = getFailedVendorInfo(failedList, vendorName);
  if (existing) {
    existing.today = !!todayFailed;
    existing.previous = !!previousFailed;
  } else {
    failedList.push({ name: vendorName, today: !!todayFailed, previous: !!previousFailed });
  }
}

/**
 * 실패 목록에서 업체 제거
 */
function removeFailedVendor(failedList, vendorName) {
  for (var i = 0; i < failedList.length; i++) {
    if (failedList[i].name === vendorName) {
      failedList.splice(i, 1);
      return;
    }
  }
}

/**
 * 실패 목록에서 업체명만 추출
 */
function getFailedVendorNames(failedList) {
  return failedList.map(function(v) { return v.name; });
}

/**
 * 실패 업체의 유형 텍스트 생성 (예: "신규+기발주", "신규", "기발주")
 */
function getFailedTypeText(vendorInfo) {
  var types = [];
  if (vendorInfo.today) types.push('신규');
  if (vendorInfo.previous) types.push('기발주');
  return types.join('+') || '전체';
}

// ==================== 진행 상태 관리 함수 ====================

/**
 * 진행 상태 저장 (시간 초과 대비)
 * @param {Object} state - 진행 상태 객체
 */
function saveProgressState(state) {
  var props = PropertiesService.getScriptProperties();
  props.setProperty(PROGRESS_STATE_KEY, JSON.stringify(state));
}

/**
 * 진행 상태 불러오기
 * @returns {Object|null} 저장된 진행 상태 또는 null
 */
function loadProgressState() {
  var props = PropertiesService.getScriptProperties();
  var stored = props.getProperty(PROGRESS_STATE_KEY);
  return stored ? JSON.parse(stored) : null;
}

/**
 * 진행 상태 초기화
 */
function clearProgressState() {
  var props = PropertiesService.getScriptProperties();
  props.deleteProperty(PROGRESS_STATE_KEY);
}

/**
 * 시간 초과 알림 전송 (스레드로)
 */
function sendSlackTimeoutNotification(completedCount, totalCount, remainingVendors) {
  var today = Utilities.formatDate(new Date(), 'Asia/Seoul', 'yyyy-MM-dd HH:mm:ss');

  var message = ':hourglass: *시간 초과로 중단됨*\n\n';
  message += '`' + today + '`\n\n';
  message += '*진행 상황:* ' + completedCount + '/' + totalCount + ' 업체 완료\n';
  message += '*남은 업체:* ' + remainingVendors.length + '개\n\n';
  message += ':arrow_forward: `resumeKakaoSending()` 실행하여 이어서 전송하세요.';

  // 저장된 스레드 ts 불러와서 스레드로 전송
  var threadTs = loadSlackThreadTs();

  if (threadTs && SLACK_CONFIG.BOT_TOKEN && SLACK_CONFIG.USE_THREAD) {
    sendSlackMessage(message, ':hourglass:', threadTs);
  } else {
    sendSlackMessage(message, ':hourglass:', null);
  }

  // 스레드 ts는 초기화하지 않음 (이어서 전송할 때 사용)
}

/**
 * 시간 초과 임박 여부 확인
 * @param {number} startTime - 시작 시간 (ms)
 * @returns {boolean} 시간 초과 임박 여부
 */
function isTimeoutApproaching(startTime) {
  var elapsed = new Date().getTime() - startTime;
  return elapsed > MAX_EXECUTION_TIME_MS;
}

// ==================== 메인 실행 함수 ====================

/**
 * 데이터 동기화 + 카카오톡 자동 전송
 */
function runSync() {
  try {
    Logger.log('========================================');
    Logger.log('🚀 데이터 동기화 + 카카오톡 전송 시작');
    Logger.log('========================================');

    // Step 1: 데이터 동기화
    var added = appendPurchaseToCumulative();
    updatePurchaseFromReorderFiltered();

    Logger.log('✅ 데이터 동기화 완료: ' + added + '행 추가');

    // Step 2: 카카오톡 자동 전송
    Logger.log('\n📱 카카오톡 전송 시작...');
    sendKakaoMessagesToVendors();

    // 완료 알림
    try {
      SpreadsheetApp.getActive().toast(
        '누적 추가: ' + added + '행\n카카오톡 전송 완료',
        '라포 자동화',
        5
      );
    } catch (_) {}

    Logger.log('\n========================================');
    Logger.log('✅ 모든 작업 완료');
    Logger.log('========================================');

  } catch (e) {
    Logger.log('❌ 에러 발생: ' + e.message + '\n' + (e.stack || ''));

    // Slack 에러 알림
    sendSlackErrorNotification(e.message);

    try {
      SpreadsheetApp.getActive().toast('오류 발생: ' + e.message, '라포 자동화', 5);
    } catch (_) {}

    throw e;
  }
}

/**
 * 데이터 동기화만 실행 (카카오톡 전송 없이)
 */
function runSyncOnly() {
  try {
    var added = appendPurchaseToCumulative();
    updatePurchaseFromReorderFiltered();

    try {
      SpreadsheetApp.getActive().toast('누적 추가: ' + added + '행, 동기화 완료', '라포 자동화', 5);
    } catch (_) {}

    Logger.log('완료');
  } catch (e) {
    Logger.log('에러: ' + e.message + '\n' + (e.stack || ''));
    throw e;
  }
}

// ==================== 데이터 동기화 함수 ====================

/** Step1: 원본 -> 타깃 누적 A:V (D열 not blank만) */
function appendPurchaseToCumulative() {
  var srcSS = withRetry(function(){ return SpreadsheetApp.openById(SOURCE_SS_ID); }, 'open source');
  var tgtSS = withRetry(function(){ return SpreadsheetApp.openById(TARGET_SS_ID); }, 'open target');

  var srcSheet = srcSS.getSheetByName(SRC_SHEET_NAME_PURCHASE);
  var tgtSheet = tgtSS.getSheetByName(TGT_SHEET_NAME_CUMUL);
  if (!srcSheet) throw new Error('원본 시트 없음: ' + SRC_SHEET_NAME_PURCHASE);
  if (!tgtSheet) throw new Error('타깃 시트 없음: ' + TGT_SHEET_NAME_CUMUL);

  var srcLastRow = srcSheet.getLastRow();
  if (srcLastRow < DATA_START_ROW) { Logger.log('[누적] 원본 본문 없음'); return 0; }

  var numRows = srcLastRow - (DATA_START_ROW - 1);
  var values = withRetry(function(){
    return srcSheet.getRange(DATA_START_ROW, COL_A, numRows, WIDTH_A_TO_V).getValues();
  }, 'read source A:V');

  var rows = [];
  var skippedEmpty = 0, skippedNoD = 0;
  for (var i = 0; i < values.length; i++) {
    var row = values[i];
    if (isRowEmpty(row)) { skippedEmpty++; continue; }
    if (isBlank(row[COL_D - 1])) { skippedNoD++; continue; }
    rows.push(row);
  }
  Logger.log('[누적] 빈행 제외: ' + skippedEmpty + ' / D열 비어 제외: ' + skippedNoD);

  if (rows.length === 0) { Logger.log('[누적] 조건 통과 행 없음'); return 0; }

  var tgtWriteRow = Math.max(tgtSheet.getLastRow() + 1, DATA_START_ROW);
  var idx = 0;
  var chunkSize = pickChunkSize(rows.length, WIDTH_A_TO_V);
  while (idx < rows.length) {
    var end = Math.min(idx + chunkSize, rows.length);
    var chunk = rows.slice(idx, end);
    (function(startRow, data){
      withRetry(function(){
        tgtSheet.getRange(startRow, COL_A, data.length, WIDTH_A_TO_V).setValues(data);
        SpreadsheetApp.flush();
        return true;
      }, 'write target A:V chunk');
    })(tgtWriteRow, chunk);
    tgtWriteRow += chunk.length;
    idx = end;
  }
  Logger.log('[누적] 추가된 행 수: ' + rows.length);
  return rows.length;
}

/** Step2: 타깃(리오더) -> 원본 A:R 교체, S:V 초기화, H not blank, O/P != TRUE, H 오름차순 */
function updatePurchaseFromReorderFiltered() {
  var srcSS = withRetry(function(){ return SpreadsheetApp.openById(SOURCE_SS_ID); }, 'open source');
  var tgtSS = withRetry(function(){ return SpreadsheetApp.openById(TARGET_SS_ID); }, 'open target');

  var srcSheet = srcSS.getSheetByName(SRC_SHEET_NAME_PURCHASE);
  var reorderSheet = tgtSS.getSheetByName(TGT_SHEET_NAME_REORDER);
  if (!srcSheet) throw new Error('원본 시트 없음: ' + SRC_SHEET_NAME_PURCHASE);
  if (!reorderSheet) throw new Error('타깃 시트 없음: ' + TGT_SHEET_NAME_REORDER);

  var lastRow = reorderSheet.getLastRow();
  if (lastRow < DATA_START_ROW) {
    clearBodyRange(srcSheet, WIDTH_A_TO_V);
    Logger.log('[동기화] 리오더 본문 없음 → 원본 A:V 초기화');
    return;
  }

  var numRows = lastRow - (DATA_START_ROW - 1);
  var valuesAll = withRetry(function(){
    return reorderSheet.getRange(DATA_START_ROW, COL_A, numRows, WIDTH_A_TO_V).getValues();
  }, 'read reorder A:V');

  var filtered = [];
  for (var i = 0; i < valuesAll.length; i++) {
    var row = valuesAll[i];
    if (!isTrue(row[COL_O - 1]) && !isTrue(row[COL_P - 1]) && !isBlank(row[COL_H - 1])) {
      filtered.push(row.slice(0, WIDTH_A_TO_R));
    }
  }

  clearBodyRange(srcSheet, WIDTH_A_TO_V);

  if (filtered.length === 0) {
    Logger.log('[동기화] 필터 결과 없음 → 원본 초기화 상태 유지(A:V)');
    return;
  }

  var idx = 0;
  var rowPtr = DATA_START_ROW;
  var chunkSize = pickChunkSize(filtered.length, WIDTH_A_TO_R);
  while (idx < filtered.length) {
    var end = Math.min(idx + chunkSize, filtered.length);
    var chunk = filtered.slice(idx, end);
    (function(startRow, data){
      withRetry(function(){
        srcSheet.getRange(startRow, COL_A, data.length, WIDTH_A_TO_R).setValues(data);
        SpreadsheetApp.flush();
        return true;
      }, 'write source A:R chunk');
    })(rowPtr, chunk);
    rowPtr += chunk.length;
    idx = end;
  }

  withRetry(function(){
    var writtenRows = rowPtr - DATA_START_ROW;
    if (writtenRows > 0) {
      srcSheet
        .getRange(DATA_START_ROW, COL_A, writtenRows, WIDTH_A_TO_R)
        .sort([{column: COL_H, ascending: true}]);
      SpreadsheetApp.flush();
    }
    return true;
  }, 'sort by column H');

  Logger.log('[동기화] 원본 A:R 교체 완료(S:V 초기화), 총 행: ' + filtered.length);
}

// ==================== 카카오톡 전송 함수 ====================

/**
 * ★사입자확인시트★의 데이터를 업체별로 카카오톡 전송
 * @param {boolean} retryMode - 실패한 업체만 재전송 모드
 * @param {boolean} resumeMode - 시간 초과로 중단된 지점부터 이어서 전송 모드
 */
function sendKakaoMessagesToVendors(retryMode, resumeMode) {
  retryMode = retryMode || false;  // 기본값: false (일반 모드)
  resumeMode = resumeMode || false;  // 기본값: false

  // 실행 시작 시간 기록 (시간 초과 감지용)
  var executionStartTime = new Date().getTime();

  // 스프레드시트 열기 (재시도 로직 적용)
  var srcSS = withRetry(function() {
    return SpreadsheetApp.openById(SOURCE_SS_ID);
  }, 'open source spreadsheet');

  // 이전 실행에서 남은 임시 시트 정리
  try {
    var allSheets = srcSS.getSheets();
    for (var s = 0; s < allSheets.length; s++) {
      if (allSheets[s].getName().indexOf('TEMP_IMAGE_') === 0) {
        Logger.log('🧹 잔여 임시 시트 삭제: ' + allSheets[s].getName());
        srcSS.deleteSheet(allSheets[s]);
      }
    }
  } catch (e) {
    Logger.log('⚠️ 임시 시트 정리 중 오류 (무시): ' + e.toString());
  }

  var srcSheet = srcSS.getSheetByName(SRC_SHEET_NAME_PURCHASE);
  var vendorInfoSheet = srcSS.getSheetByName(KAKAO_CONFIG.VENDOR_INFO_SHEET);

  if (!srcSheet) {
    Logger.log('❌ 원본 시트를 찾을 수 없습니다: ' + SRC_SHEET_NAME_PURCHASE);
    return;
  }

  if (!vendorInfoSheet) {
    Logger.log('❌ 업체 정보 시트를 찾을 수 없습니다: ' + KAKAO_CONFIG.VENDOR_INFO_SHEET);
    return;
  }

  // KakaoAuto 로그인 확인
  if (!KakaoAuto.isLoggedIn()) {
    Logger.log('❌ 카카오톡 로그인 필요: ' + KakaoAuto.getAuthUrl());
    return;
  }

  // 업체 정보 불러오기
  var vendorData = vendorInfoSheet.getDataRange().getValues();
  var vendorMap = {};

  for (var i = 1; i < vendorData.length; i++) {
    var vendorName = vendorData[i][KAKAO_CONFIG.VENDOR_NAME_COL_INFO - 1];
    var kakaoId = vendorData[i][KAKAO_CONFIG.KAKAO_ID_COL - 1];

    if (vendorName && kakaoId) {
      vendorMap[vendorName] = kakaoId;
    }
  }

  Logger.log('📋 업체 정보 로드: ' + Object.keys(vendorMap).length + '개');

  // ★사입자확인시트★ 데이터 읽기
  var lastRow = srcSheet.getLastRow();
  if (lastRow < DATA_START_ROW) {
    Logger.log('📭 전송할 데이터가 없습니다.');
    return;
  }

  var allData = srcSheet.getRange(1, 1, lastRow, WIDTH_A_TO_V).getValues();
  var dataRows = allData.slice(DATA_START_ROW - 1); // 3번째 행부터 데이터

  // 오늘 날짜 (문자열로 비교하기 위해 yyyy-MM-dd 형식)
  var today = new Date();
  var todayStr = Utilities.formatDate(today, 'Asia/Seoul', 'yyyy-MM-dd');
  Logger.log('🔍 오늘 날짜: ' + todayStr);

  // 업체별로 데이터 그룹화 (오늘 날짜 / 오늘 아닌 날짜 분리)
  var vendorTodayMap = {};      // 오늘 날짜인 주문
  var vendorPreviousMap = {};   // 오늘 날짜가 아닌 주문

  // PropertiesService에서 실패한 업체 목록 불러오기
  var FAILED_VENDORS = loadFailedVendors();

  // 재전송 모드일 경우 FAILED_VENDORS만 처리
  if (retryMode && FAILED_VENDORS.length > 0) {
    var failedNames = getFailedVendorNames(FAILED_VENDORS);
    Logger.log('🔄 재전송 모드: ' + FAILED_VENDORS.length + '개 업체 재시도');
    for (var fi = 0; fi < FAILED_VENDORS.length; fi++) {
      Logger.log('   ' + FAILED_VENDORS[fi].name + ' (' + getFailedTypeText(FAILED_VENDORS[fi]) + ')');
    }

    // Slack 재전송 시작 알림
    sendSlackRetryStartNotification(FAILED_VENDORS);

    // 실패한 업체의 데이터만 다시 그룹화 (오늘/오늘 아닌 날짜 구분)
    for (var i = 0; i < dataRows.length; i++) {
      var row = dataRows[i];
      if (isRowEmpty(row)) continue;

      var vendorName = row[KAKAO_CONFIG.VENDOR_NAME_COL - 1];
      if (!vendorName || !vendorMap[vendorName] || failedNames.indexOf(vendorName) === -1) {
        continue;
      }

      // 최초 발주일 확인 (C열 = index 2)
      var orderDate = row[2]; // C열: 최초 발주일
      var isToday = false;

      if (orderDate && Object.prototype.toString.call(orderDate) === '[object Date]') {
        var orderDateStr = Utilities.formatDate(orderDate, 'Asia/Seoul', 'yyyy-MM-dd');
        isToday = (orderDateStr === todayStr);
      }

      if (isToday) {
        // 오늘 날짜인 주문
        if (!vendorTodayMap[vendorName]) {
          vendorTodayMap[vendorName] = [];
        }
        vendorTodayMap[vendorName].push(row);
      } else {
        // 오늘 날짜가 아닌 주문
        if (!vendorPreviousMap[vendorName]) {
          vendorPreviousMap[vendorName] = [];
        }
        vendorPreviousMap[vendorName].push(row);
      }
    }
  } else {
    // 일반 모드: 모든 업체 처리
    var totalRows = 0;
    var todayRows = 0;
    var previousRows = 0;
    var dateTypeRows = 0;
    var notDateRows = 0;

    for (var i = 0; i < dataRows.length; i++) {
      var row = dataRows[i];
      if (isRowEmpty(row)) continue;

      totalRows++;

      var vendorName = row[KAKAO_CONFIG.VENDOR_NAME_COL - 1];
      if (!vendorName || !vendorMap[vendorName]) {
        continue;
      }

      // 최초 발주일 확인 (C열 = index 2)
      var orderDate = row[2]; // C열: 최초 발주일

      // 처음 3개 행만 디버깅 로그 출력
      if (i < 3) {
        Logger.log('🔍 행 ' + (i + 1) + ' - C열 값: ' + orderDate + ', 타입: ' + Object.prototype.toString.call(orderDate));
      }

      var isToday = false;

      if (orderDate && Object.prototype.toString.call(orderDate) === '[object Date]') {
        dateTypeRows++;
        var orderDateStr = Utilities.formatDate(orderDate, 'Asia/Seoul', 'yyyy-MM-dd');

        // 처음 3개 행만 디버깅 로그 출력
        if (i < 3) {
          Logger.log('   → 날짜 비교: ' + orderDateStr + ' vs 오늘 (' + todayStr + ')');
        }

        isToday = (orderDateStr === todayStr);
      } else {
        notDateRows++;
        // Date 타입이 아닌 경우는 "오늘 아닌 날짜"로 간주
      }

      // 디버깅: 처음 10개 행의 업체명 로그
      if (i < 10) {
        Logger.log('   → 행 ' + (i + 1) + ' 업체명(G열): "' + vendorName + '", 업체정보 존재: ' + (vendorMap[vendorName] ? 'O' : 'X') + ', 날짜: ' + (isToday ? 'TODAY' : 'PREVIOUS'));
      }

      if (isToday) {
        // 오늘 날짜인 주문
        todayRows++;
        if (!vendorTodayMap[vendorName]) {
          vendorTodayMap[vendorName] = [];
        }
        vendorTodayMap[vendorName].push(row);
      } else {
        // 오늘 날짜가 아닌 주문
        previousRows++;
        if (!vendorPreviousMap[vendorName]) {
          vendorPreviousMap[vendorName] = [];
        }
        vendorPreviousMap[vendorName].push(row);
      }
    }

    Logger.log('📊 필터링 결과: 총 ' + totalRows + '행 중 Date 타입 ' + dateTypeRows + '행, 오늘 날짜 ' + todayRows + '행, 이전 날짜 ' + previousRows + '행, Date 아님 ' + notDateRows + '행');

    // 일반 모드일 때는 실패 목록 초기화 (이어서 전송 모드에서는 유지)
    if (!resumeMode) {
      clearFailedVendors();
      FAILED_VENDORS = [];
    }
  }

  // 전송 대상 업체 목록 (오늘 또는 이전 데이터가 있는 업체)
  var allVendors = {};
  for (var v in vendorTodayMap) allVendors[v] = true;
  for (var v in vendorPreviousMap) allVendors[v] = true;

  Logger.log('📨 메시지 전송 대상: ' + Object.keys(allVendors).length + '개 업체');
  Logger.log('   - 오늘 날짜 데이터: ' + Object.keys(vendorTodayMap).length + '개 업체');
  Logger.log('   - 이전 날짜 데이터: ' + Object.keys(vendorPreviousMap).length + '개 업체');

  // 브랜드 목록 수집 및 시작 알림 (일반 모드 + 최초 실행일 때만)
  var brandList = [];
  if (!retryMode && !resumeMode) {
    var brandSet = {};
    for (var i = 0; i < dataRows.length; i++) {
      var row = dataRows[i];
      if (isRowEmpty(row)) continue;

      var brandName = row[0]; // A열 (브랜드명)
      if (brandName) {
        brandSet[brandName] = true;
      }
    }

    brandList = Object.keys(brandSet);

    // Slack 시작 알림 전송 (채널 메인 메시지 - runSync 시에만)
    sendSlackStartNotification(
      brandList,
      Object.keys(allVendors).length,
      Object.keys(vendorTodayMap).length,
      Object.keys(vendorPreviousMap).length
    );

    // 관리자 채팅방에 브랜드 완료 알림 전송
    if (brandList.length > 0 && ADMIN_CHAT_ID) {
      try {
        var brandMessage = '"' + brandList.join('", "') + '" 리스트 완료입니다.';
        var adminResult = KakaoAuto.sendText(ADMIN_CHAT_ID, brandMessage);

        if (adminResult.success) {
          Logger.log('✅ 관리자 채팅방: 브랜드 완료 알림 전송 성공');
          Logger.log('   브랜드: ' + brandList.join(', '));
        } else {
          Logger.log('⚠️ 관리자 채팅방: 알림 전송 실패 - ' + adminResult.error);
        }

        Utilities.sleep(3000);
      } catch (error) {
        Logger.log('⚠️ 관리자 채팅방: 알림 전송 오류 - ' + error.toString());
      }
    }
  }

  // 각 업체에 메시지 전송
  var successCount = 0;
  var failCount = 0;
  var vendorNames = Object.keys(allVendors);
  var startIndex = 0;  // 시작 인덱스 (이어서 전송할 때 사용)
  var timeoutOccurred = false;  // 시간 초과 발생 여부

  // 이어서 전송 모드: 저장된 진행 상태 불러오기
  if (resumeMode) {
    var savedState = loadProgressState();
    if (savedState) {
      startIndex = savedState.lastIndex + 1;
      successCount = savedState.successCount || 0;
      failCount = savedState.failCount || 0;
      FAILED_VENDORS = savedState.failedVendors || [];
      Logger.log('🔄 이어서 전송 모드: ' + startIndex + '번째 업체부터 재시작');
      Logger.log('   이전 진행: 성공 ' + successCount + ', 실패 ' + failCount);
    } else {
      Logger.log('⚠️ 저장된 진행 상태가 없습니다. 처음부터 시작합니다.');
    }

    // 스레드에 이어서 전송 재시작 알림
    var threadTs = loadSlackThreadTs();
    if (threadTs && SLACK_CONFIG.BOT_TOKEN && SLACK_CONFIG.USE_THREAD) {
      var resumeMsg = ':arrow_forward: *시간 초과 후 이어서 전송 재시작*\n\n';
      resumeMsg += '`' + Utilities.formatDate(new Date(), 'Asia/Seoul', 'yyyy-MM-dd HH:mm:ss') + '`\n';
      resumeMsg += '*남은 업체:* ' + (vendorNames.length - startIndex) + '개';
      sendSlackMessage(resumeMsg, ':arrow_forward:', threadTs);
      Logger.log('📝 Slack 스레드로 이어서 전송 시작 알림 전송');
    }
  }

  for (var v = startIndex; v < vendorNames.length; v++) {
    // ============ 시간 초과 체크 ============
    if (isTimeoutApproaching(executionStartTime)) {
      Logger.log('\n⏰ 시간 초과 임박! 진행 상태를 저장하고 중단합니다.');
      Logger.log('   완료: ' + (successCount + failCount) + '/' + vendorNames.length + ' 업체');

      // 남은 업체 목록
      var remainingVendors = vendorNames.slice(v);

      // 진행 상태 저장
      saveProgressState({
        lastIndex: v - 1,
        successCount: successCount,
        failCount: failCount,
        failedVendors: FAILED_VENDORS,
        totalVendors: vendorNames.length,
        savedAt: new Date().toISOString()
      });

      // 실패 목록도 저장 (현재까지 실패한 업체 + 아직 처리 안 된 업체)
      var failedNames = getFailedVendorNames(FAILED_VENDORS);
      var pendingVendors = FAILED_VENDORS.slice(); // 복사
      for (var rv = 0; rv < remainingVendors.length; rv++) {
        if (failedNames.indexOf(remainingVendors[rv]) === -1) {
          pendingVendors.push({ name: remainingVendors[rv], today: true, previous: true });
        }
      }
      saveFailedVendors(pendingVendors);

      // Slack 시간 초과 알림
      sendSlackTimeoutNotification(successCount + failCount, vendorNames.length, remainingVendors);

      timeoutOccurred = true;
      break;  // 루프 중단
    }

    var vendorName = vendorNames[v];
    var kakaoId = vendorMap[vendorName];

    var todayRowsData = vendorTodayMap[vendorName] || [];
    var previousRowsData = vendorPreviousMap[vendorName] || [];
    var todaySuccess = true;
    var previousSuccess = true;

    // 재전송 모드: 실패한 유형만 전송
    var shouldSendToday = true;
    var shouldSendPrevious = true;
    if (retryMode) {
      var failedInfo = getFailedVendorInfo(FAILED_VENDORS, vendorName);
      if (failedInfo) {
        shouldSendToday = failedInfo.today;
        shouldSendPrevious = failedInfo.previous;
      }
    }

    try {
      // ============ 1. 오늘 날짜 데이터 전송 ============
      if (shouldSendToday && todayRowsData.length > 0) {
        Logger.log('\n📅 [TODAY] ' + vendorName + ': ' + todayRowsData.length + '건 처리 시작');

        // 브랜드명 수집
        var todayBrandSet = {};
        for (var i = 0; i < todayRowsData.length; i++) {
          var brandName = todayRowsData[i][0]; // A열
          if (brandName) todayBrandSet[brandName] = true;
        }
        var todayBrandList = Object.keys(todayBrandSet);
        var todayBrandText = todayBrandList.length > 0 ? '"' + todayBrandList.join('", "') + '"' : '';

        // 메시지 생성: "yyyy-MM-dd 신규오더&리오더 주문 전달드립니다."
        var todayMessage = '';
        if (retryMode) {
          todayMessage += '[전송 오류로 다시 보내드립니다.]\n\n';
        }
        todayMessage += todayStr + ' 신규오더&리오더 주문 전달드립니다.\n\n';
        todayMessage += (todayBrandText ? todayBrandText + ' ' : '') + todayRowsData.length + '건 확인 및 납기 일자 확인 부탁드립니다.';

        // 텍스트 전송
        var todayTextResult = KakaoAuto.sendText(kakaoId, todayMessage);
        if (!todayTextResult.success) {
          Logger.log('❌ [TODAY] ' + vendorName + ': 텍스트 전송 실패 - ' + todayTextResult.error);
          todaySuccess = false;
        } else {
          Logger.log('✅ [TODAY] ' + vendorName + ': 텍스트 전송 성공');
          Utilities.sleep(3000);

          // 이미지 전송
          try {
            Logger.log('🖼️ [TODAY] ' + vendorName + ': 이미지 생성 시작...');
            var todayImageBlobs = createTableImages(todayRowsData, KAKAO_CONFIG.TARGET_COLUMNS, vendorName);

            if (todayImageBlobs && todayImageBlobs.length > 0) {
              Logger.log('✅ [TODAY] ' + vendorName + ': 이미지 ' + todayImageBlobs.length + '개 생성 완료');

              for (var imgIdx = 0; imgIdx < todayImageBlobs.length; imgIdx++) {
                var imageBlob = todayImageBlobs[imgIdx];
                var base64 = Utilities.base64Encode(imageBlob.getBytes());
                Logger.log('📤 [TODAY] ' + vendorName + ': 이미지 ' + (imgIdx + 1) + '/' + todayImageBlobs.length + ' 전송 시도...');

                var imageResult = KakaoAuto.sendImage(kakaoId, base64);
                if (imageResult.success) {
                  Logger.log('✅ [TODAY] ' + vendorName + ': 이미지 ' + (imgIdx + 1) + ' 전송 성공');
                } else {
                  Logger.log('⚠️ [TODAY] ' + vendorName + ': 이미지 ' + (imgIdx + 1) + ' 전송 실패 - ' + imageResult.error);
                  todaySuccess = false;
                }
                Utilities.sleep(3000);
              }
            } else {
              Logger.log('❌ [TODAY] ' + vendorName + ': 이미지 생성 실패');
              todaySuccess = false;
            }
          } catch (imageError) {
            Logger.log('❌ [TODAY] ' + vendorName + ': 이미지 처리 오류 - ' + imageError.toString());
            todaySuccess = false;
          }
        }
      }

      // ============ 2. 이전 날짜 데이터 전송 ============
      if (shouldSendPrevious && previousRowsData.length > 0) {
        Logger.log('\n📆 [PREVIOUS] ' + vendorName + ': ' + previousRowsData.length + '건 처리 시작');

        // 브랜드명 수집
        var previousBrandSet = {};
        for (var i = 0; i < previousRowsData.length; i++) {
          var brandName = previousRowsData[i][0]; // A열
          if (brandName) previousBrandSet[brandName] = true;
        }
        var previousBrandList = Object.keys(previousBrandSet);
        var previousBrandText = previousBrandList.length > 0 ? '"' + previousBrandList.join('", "') + '"' : '';

        // 메시지 생성: "브랜드" 기발주 입고 필요건 전달드립니다.
        var previousMessage = '';
        if (retryMode) {
          previousMessage += '[전송 오류로 다시 보내드립니다.]\n\n';
        }
        previousMessage += (previousBrandText ? previousBrandText + ' ' : '') + '기발주 입고 필요건 전달드립니다.\n\n';
        previousMessage += previousRowsData.length + '건 납기 일자 확인 부탁드립니다.';

        // 텍스트 전송
        var previousTextResult = KakaoAuto.sendText(kakaoId, previousMessage);
        if (!previousTextResult.success) {
          Logger.log('❌ [PREVIOUS] ' + vendorName + ': 텍스트 전송 실패 - ' + previousTextResult.error);
          previousSuccess = false;
        } else {
          Logger.log('✅ [PREVIOUS] ' + vendorName + ': 텍스트 전송 성공');
          Utilities.sleep(3000);

          // 이미지 전송
          try {
            Logger.log('🖼️ [PREVIOUS] ' + vendorName + ': 이미지 생성 시작...');
            var previousImageBlobs = createTableImages(previousRowsData, KAKAO_CONFIG.TARGET_COLUMNS, vendorName);

            if (previousImageBlobs && previousImageBlobs.length > 0) {
              Logger.log('✅ [PREVIOUS] ' + vendorName + ': 이미지 ' + previousImageBlobs.length + '개 생성 완료');

              for (var imgIdx = 0; imgIdx < previousImageBlobs.length; imgIdx++) {
                var imageBlob = previousImageBlobs[imgIdx];
                var base64 = Utilities.base64Encode(imageBlob.getBytes());
                Logger.log('📤 [PREVIOUS] ' + vendorName + ': 이미지 ' + (imgIdx + 1) + '/' + previousImageBlobs.length + ' 전송 시도...');

                var imageResult = KakaoAuto.sendImage(kakaoId, base64);
                if (imageResult.success) {
                  Logger.log('✅ [PREVIOUS] ' + vendorName + ': 이미지 ' + (imgIdx + 1) + ' 전송 성공');
                } else {
                  Logger.log('⚠️ [PREVIOUS] ' + vendorName + ': 이미지 ' + (imgIdx + 1) + ' 전송 실패 - ' + imageResult.error);
                  previousSuccess = false;
                }
                Utilities.sleep(3000);
              }
            } else {
              Logger.log('❌ [PREVIOUS] ' + vendorName + ': 이미지 생성 실패');
              previousSuccess = false;
            }
          } catch (imageError) {
            Logger.log('❌ [PREVIOUS] ' + vendorName + ': 이미지 처리 오류 - ' + imageError.toString());
            previousSuccess = false;
          }
        }
      }

      // ============ 결과 처리 ============
      var todayFailed = shouldSendToday && todayRowsData.length > 0 && !todaySuccess;
      var previousFailed = shouldSendPrevious && previousRowsData.length > 0 && !previousSuccess;

      if (!todayFailed && !previousFailed) {
        successCount++;
        // 모두 성공 시 실패 목록에서 제거
        removeFailedVendor(FAILED_VENDORS, vendorName);
      } else {
        failCount++;
        // 실패한 유형만 기록
        addOrUpdateFailedVendor(FAILED_VENDORS, vendorName, todayFailed, previousFailed);
        var failedTypeLog = (todayFailed ? '신규' : '') + (todayFailed && previousFailed ? '+' : '') + (previousFailed ? '기발주' : '');
        Logger.log('⚠️ ' + vendorName + ': 실패 유형 - ' + failedTypeLog);
      }

    } catch (error) {
      Logger.log('❌ ' + vendorName + ' (' + kakaoId + '): 오류 - ' + error.toString());
      failCount++;
      // 예외 발생 시 전체 실패로 기록
      addOrUpdateFailedVendor(FAILED_VENDORS, vendorName, true, true);
    }
  }

  // 시간 초과로 중단된 경우 여기서 종료 (이미 알림 전송됨)
  if (timeoutOccurred) {
    Logger.log('\n⏰ 시간 초과로 중단됨. resumeKakaoSending() 실행하여 이어서 전송하세요.');
    return;
  }

  Logger.log('\n📊 카카오톡 전송 결과: 성공 ' + successCount + '건, 실패 ' + failCount + '건');

  // 정상 완료 시 진행 상태 초기화
  clearProgressState();

  // 실패한 항목 PropertiesService에 저장
  saveFailedVendors(FAILED_VENDORS);

  // Slack 종료 알림 전송
  sendSlackEndNotification(successCount, failCount, FAILED_VENDORS);

  // 실패한 항목 출력
  if (FAILED_VENDORS.length > 0) {
    Logger.log('⚠️ 실패한 업체 목록:');
    for (var i = 0; i < FAILED_VENDORS.length; i++) {
      Logger.log('   ' + (i + 1) + '. ' + FAILED_VENDORS[i].name + ' (' + getFailedTypeText(FAILED_VENDORS[i]) + ')');
    }
    Logger.log('\n💡 재전송하려면 retryFailedVendors() 함수를 실행하세요.');
  } else {
    Logger.log('✅ 모든 업체 전송 완료!');
  }
}

/**
 * 테이블 데이터를 여러 페이지 이미지로 생성 (20행씩)
 */
function createTableImages(rows, targetColumns, vendorName) {
  var blobs = [];
  var total = rows.length;

  for (var start = 0; start < total; start += IMAGE_ROWS_PER_PAGE) {
    var end = Math.min(start + IMAGE_ROWS_PER_PAGE, total);
    var chunkRows = rows.slice(start, end);
    var pageNo = Math.floor(start / IMAGE_ROWS_PER_PAGE) + 1;

    var blob = createTableImage(chunkRows, targetColumns, vendorName, pageNo);
    if (blob) {
      blobs.push(blob);
    }
  }

  return blobs;
}

/**
 * 테이블 데이터를 이미지로 생성 (단일 페이지)
 */
function createTableImage(rows, targetColumns, vendorName, pageNo) {
  // 데이터를 텍스트로 변환하는 헬퍼 함수
  function toTextCell(value) {
    if (value === null || value === '') return '';
    if (Object.prototype.toString.call(value) === '[object Date]') {
      return Utilities.formatDate(value, 'Asia/Seoul', 'yyyy-MM-dd');
    }
    return String(value);
  }

  try {
    Logger.log('  [이미지 ' + pageNo + '] 1/6 스프레드시트 열기...');
    var ss = withRetry(function() {
      return SpreadsheetApp.openById(SOURCE_SS_ID);
    }, 'open spreadsheet for image');

    Logger.log('  [이미지 ' + pageNo + '] 2/6 임시 시트 생성...');
    var tempSheetName = 'TEMP_IMAGE_' + new Date().getTime() + '_' + pageNo;
    var tempSheet = ss.insertSheet(tempSheetName);
    Logger.log('  [이미지 ' + pageNo + '] 임시 시트: ' + tempSheetName);

    Logger.log('  [이미지 ' + pageNo + '] 3/6 데이터 작성 (헤더 + ' + rows.length + '행)...');

    // 헤더 작성 (1번 행)
    var headerRow = ['브랜드', '최초 발주일', '업체', '주소', '사입상품명', '업체 색상', '업체사이즈', '단가(v-)', '단가(v+)', '오더 수량'];
    tempSheet.getRange(1, 1, 1, headerRow.length).setValues([headerRow]);

    // 데이터 작성 (2번 행부터) - 문제가 되는 컬럼(2,8,9,10)은 텍스트로 변환
    var dataRows = [];
    for (var i = 0; i < rows.length; i++) {
      var dataRow = [];
      for (var j = 0; j < targetColumns.length; j++) {
        var v = rows[i][targetColumns[j] - 1];
        var tempColIndex = j + 1; // 1~10

        // 컬럼 2(C), 8(L), 9(M), 10(R)은 텍스트로 변환
        if (tempColIndex === 2 || tempColIndex === 8 || tempColIndex === 9 || tempColIndex === 10) {
          dataRow.push(toTextCell(v));
        } else {
          dataRow.push(v || '');
        }
      }
      dataRows.push(dataRow);
    }
    tempSheet.getRange(2, 1, dataRows.length, headerRow.length).setValues(dataRows);
    Logger.log('  [이미지 ' + pageNo + '] 데이터 작성 완료: ' + headerRow.length + '개 컬럼');

    // 문제가 되는 컬럼들에 TEXT 포맷 강제 적용
    var forceTextCols = [2, 8, 9, 10]; // C, L, M, R 위치
    forceTextCols.forEach(function(col) {
      tempSheet.getRange(1, col, dataRows.length + 1, 1).setNumberFormat('@');
    });
    Logger.log('  [이미지 ' + pageNo + '] TEXT 포맷 강제 적용 완료 (컬럼 2, 8, 9, 10)');

    Logger.log('  [이미지 ' + pageNo + '] 4/6 스타일 적용...');

    // 스타일 적용 - 헤더 행 (회색 배경)
    var headerRange = tempSheet.getRange(1, 1, 1, headerRow.length);
    headerRange.setBackground('#808080')  // 회색 헤더
      .setFontColor('#ffffff')
      .setFontWeight('bold')
      .setFontSize(15)
      .setHorizontalAlignment('center')
      .setVerticalAlignment('middle');
    tempSheet.setRowHeight(1, 35);

    // 데이터 행 스타일 - 모든 행 흰색 배경으로 통일
    var dataRange = tempSheet.getRange(2, 1, dataRows.length, headerRow.length);
    dataRange.setBackground('#ffffff')  // 흰색 배경
      .setFontColor('#000000')          // 검은 글자
      .setFontSize(15)
      .setHorizontalAlignment('center')
      .setVerticalAlignment('middle');

    // 전체 범위에 테두리 적용
    var fullRange = tempSheet.getRange(1, 1, dataRows.length + 1, headerRow.length);
    fullRange.setBorder(true, true, true, true, true, true, '#000000', SpreadsheetApp.BorderStyle.SOLID);

    // 컬럼 너비 설정: 기본 100px, I(사입상품명, index 5)는 200px
    var colWidths = [100, 100, 100, 100, 200, 100, 100, 100, 100, 100];
    for (var i = 0; i < colWidths.length; i++) {
      tempSheet.setColumnWidth(i + 1, colWidths[i]);
    }

    SpreadsheetApp.flush();
    Utilities.sleep(500);
    Logger.log('  [이미지 ' + pageNo + '] 스타일 적용 완료 (헤더: 파란색, 데이터: 흰색 배경)');

    Logger.log('  [이미지 ' + pageNo + '] 5/6 차트 생성 중...');

    // 차트 생성
    var dataRangeForChart = tempSheet.getRange(1, 1, dataRows.length + 1, headerRow.length);

    // 차트 크기 계산
    var chartWidth = 1600;
    var chartHeight = Math.min(1000, (dataRows.length + 1) * 40 + 100);
    Logger.log('  [이미지 ' + pageNo + '] 차트 크기: ' + chartWidth + 'x' + chartHeight);

    var chart = tempSheet.newChart()
      .asTableChart()
      .addRange(dataRangeForChart)
      .setNumHeaders(1)
      .setOption('width', chartWidth)
      .setOption('height', chartHeight)
      .setOption('allowHtml', true)
      .setOption('showRowNumber', false)
      .setOption('sort', 'disable')
      .setOption('page', 'disable')
      .setOption('startPage', 1)
      .setOption('pageSize', dataRows.length + 1)
      .setOption('pagingButtons', 0)
      .setOption('alternatingRowStyle', false)
      .setOption('cssClassNames', {
        'headerRow': 'header-style',
        'tableRow': 'row-style',
        'oddTableRow': 'row-style',
        'selectedTableRow': 'row-style',
        'hoverTableRow': 'row-style',
        'headerCell': 'header-cell',
        'tableCell': 'cell-style'
      })
      .setPosition(1, 1, 0, 0)
      .build();

    tempSheet.insertChart(chart);
    SpreadsheetApp.flush();
    Logger.log('  [이미지 ' + pageNo + '] 차트 렌더링 대기 중 (3초)...');
    Utilities.sleep(3000);

    Logger.log('  [이미지 ' + pageNo + '] 6/6 이미지 추출 중...');
    var charts = tempSheet.getCharts();
    Logger.log('  [이미지 ' + pageNo + '] 차트 개수: ' + charts.length);

    if (charts.length > 0) {
      var imageBlob = charts[0].getAs('image/png');
      Logger.log('  [이미지 ' + pageNo + '] ✅ 이미지 생성 성공: ' + imageBlob.getBytes().length + ' bytes');
      ss.deleteSheet(tempSheet);
      return imageBlob;
    } else {
      Logger.log('  [이미지 ' + pageNo + '] ❌ 차트를 찾을 수 없음');
    }

    ss.deleteSheet(tempSheet);
    return null;

  } catch (error) {
    Logger.log('  [이미지 ' + pageNo + '] ❌ 오류 발생: ' + error.toString());
    Logger.log('  [이미지 ' + pageNo + '] 스택: ' + (error.stack || '없음'));

    // 임시 시트 삭제 시도
    try {
      var ss = SpreadsheetApp.openById(SOURCE_SS_ID);
      var sheets = ss.getSheets();
      for (var i = 0; i < sheets.length; i++) {
        if (sheets[i].getName().indexOf('TEMP_IMAGE_') === 0) {
          ss.deleteSheet(sheets[i]);
        }
      }
    } catch (e) {
      // 무시
    }

    return null;
  }
}

// ==================== 유틸리티 함수 ====================

function withRetry(fn, label) {
  var attempt = 0;
  var lastErr;
  while (attempt < RETRIES) {
    try { return fn(); }
    catch (e) {
      lastErr = e;
      var msg = (e && e.message) ? e.message : String(e);
      if (!isTransientError(msg)) break;
      var sleep = BASE_SLEEP_MS * Math.pow(2, attempt) + Math.floor(Math.random()*200);
      Logger.log('[retry] ' + label + ' - attempt ' + (attempt+1) + ' failed: ' + msg + ' / sleep ' + sleep + 'ms');
      Utilities.sleep(sleep);
      attempt++;
    }
  }
  throw lastErr;
}

function isTransientError(msg) {
  if (!msg) return false;
  var s = msg.toLowerCase();
  return (
    s.indexOf('server error') !== -1 ||
    s.indexOf('internal error') !== -1 ||
    s.indexOf('service invoked too many times') !== -1 ||
    s.indexOf('try again') !== -1
  );
}

function pickChunkSize(nRows, nCols) {
  var cells = nRows * nCols;
  if (cells > 200000) return CHUNK_ROWS_SMALL;
  return CHUNK_ROWS_BIG;
}

function isRowEmpty(row) {
  for (var i = 0; i < row.length; i++) {
    var v = row[i];
    if (!(v === '' || v === null)) return false;
  }
  return true;
}

function isBlank(v) {
  if (v === null || v === '') return true;
  if (Object.prototype.toString.call(v) === '[object Date]') return false;
  if (typeof v === 'number') return false;
  if (typeof v === 'string') return v.trim() === '';
  return false;
}

function isTrue(val) {
  if (val === true) return true;
  if (typeof val === 'string') return val.replace(/\s+/g, '').toUpperCase() === 'TRUE';
  return false;
}

function clearBodyRange(sheet, width) {
  var lastRow = Math.max(sheet.getLastRow(), DATA_START_ROW);
  var bodyRows = lastRow - (DATA_START_ROW - 1);
  if (bodyRows > 0) {
    withRetry(function(){
      sheet.getRange(DATA_START_ROW, COL_A, bodyRows, width).clearContent();
      SpreadsheetApp.flush();
      return true;
    }, 'clear body range');
  }
}

function padEnd(str, targetLength, padString) {
  str = String(str);
  if (str.length >= targetLength) return str;
  padString = String(padString || ' ');
  var padLength = targetLength - str.length;
  var repeated = '';
  while (repeated.length < padLength) {
    repeated += padString;
  }
  return str + repeated.substring(0, padLength);
}

// ==================== 개별 실행 함수 ====================

function runStep1_only() {
  appendPurchaseToCumulative();
}

function runStep2_only() {
  updatePurchaseFromReorderFiltered();
}

function sendKakaoOnly() {
  sendKakaoMessagesToVendors();
}

/**
 * 시간 초과로 중단된 전송을 이어서 실행
 */
function resumeKakaoSending() {
  Logger.log('========================================');
  Logger.log('🔄 중단된 카카오톡 전송 이어서 실행');
  Logger.log('========================================');

  var savedState = loadProgressState();

  if (!savedState) {
    Logger.log('⚠️ 저장된 진행 상태가 없습니다.');
    Logger.log('   새로 시작하려면 sendKakaoMessagesToVendors() 함수를 실행하세요.');
    return;
  }

  Logger.log('📋 저장된 진행 상태:');
  Logger.log('   - 마지막 완료 인덱스: ' + savedState.lastIndex);
  Logger.log('   - 성공: ' + savedState.successCount + '건');
  Logger.log('   - 실패: ' + savedState.failCount + '건');
  Logger.log('   - 전체: ' + savedState.totalVendors + '개 업체');
  Logger.log('   - 저장 시각: ' + savedState.savedAt);
  Logger.log('');

  // 이어서 전송 실행
  sendKakaoMessagesToVendors(false, true);  // resumeMode = true
}

/**
 * 진행 상태 확인
 */
function checkProgressState() {
  Logger.log('========================================');
  Logger.log('📋 카카오톡 전송 진행 상태 확인');
  Logger.log('========================================');

  var savedState = loadProgressState();

  if (!savedState) {
    Logger.log('✅ 저장된 진행 상태가 없습니다. (정상 완료 또는 미실행)');
    return;
  }

  Logger.log('⏸️ 중단된 전송이 있습니다:');
  Logger.log('   - 마지막 완료 인덱스: ' + savedState.lastIndex);
  Logger.log('   - 성공: ' + savedState.successCount + '건');
  Logger.log('   - 실패: ' + savedState.failCount + '건');
  Logger.log('   - 전체: ' + savedState.totalVendors + '개 업체');
  Logger.log('   - 남은 업체: ' + (savedState.totalVendors - savedState.lastIndex - 1) + '개');
  Logger.log('   - 저장 시각: ' + savedState.savedAt);
  Logger.log('');
  Logger.log('💡 이어서 전송하려면 resumeKakaoSending() 함수를 실행하세요.');
  Logger.log('💡 처음부터 다시 시작하려면 clearProgressState() 후 sendKakaoMessagesToVendors()를 실행하세요.');

  Logger.log('========================================');
}

/**
 * 진행 상태 수동 초기화
 */
function clearProgressStateManual() {
  var savedState = loadProgressState();
  clearProgressState();

  if (savedState) {
    Logger.log('✅ 진행 상태 초기화 완료');
    Logger.log('   삭제된 상태: 인덱스 ' + savedState.lastIndex + ', 성공 ' + savedState.successCount + ', 실패 ' + savedState.failCount);
  } else {
    Logger.log('ℹ️ 저장된 진행 상태가 없었습니다.');
  }
}

// ==================== 진단 및 테스트 함수 ====================

/**
 * 카카오톡 연결 상태 확인
 */
function checkKakaoConnection() {
  Logger.log('========================================');
  Logger.log('🔍 카카오톡 연결 상태 확인');
  Logger.log('========================================');

  // 1. KakaoAuto 라이브러리 로드 확인
  try {
    Logger.log('1️⃣ KakaoAuto 라이브러리 체크...');
    var authUrl = KakaoAuto.getAuthUrl();
    Logger.log('✅ KakaoAuto 라이브러리 로드됨');
    Logger.log('   로그인 URL: ' + authUrl);
  } catch (e) {
    Logger.log('❌ KakaoAuto 라이브러리 로드 실패!');
    Logger.log('   에러: ' + e.toString());
    Logger.log('   해결: Apps Script 편집기 > 라이브러리 > 아래 ID 추가');
    Logger.log('   1WtV19dz3dkazbK7ZoimyqRWC-wuG0aY_pxk9FzXXmr9dTwjYGJQ_YcAN');
    return;
  }

  // 2. 로그인 상태 확인
  Logger.log('\n2️⃣ 로그인 상태 체크...');
  var isLoggedIn = KakaoAuto.isLoggedIn();
  Logger.log('   isLoggedIn(): ' + isLoggedIn);

  if (!isLoggedIn) {
    Logger.log('❌ 로그인되지 않음');
    Logger.log('   아래 URL에서 로그인 필요:');
    Logger.log('   ' + KakaoAuto.getAuthUrl());
    return;
  }

  Logger.log('✅ 로그인 확인됨');

  // 3. 서비스 상태 확인
  Logger.log('\n3️⃣ 서비스 상태 체크...');
  try {
    var status = KakaoAuto.getStatus();
    if (status.success) {
      Logger.log('✅ 서비스 정상');
      Logger.log('   봇 이름: ' + status.data.botName);
      Logger.log('   봇 ID: ' + status.data.botId);
    } else {
      Logger.log('❌ 서비스 상태 조회 실패: ' + status.error);
    }
  } catch (e) {
    Logger.log('❌ 서비스 상태 조회 오류: ' + e.toString());
  }

  // 4. 채팅방 목록 조회
  Logger.log('\n4️⃣ 채팅방 목록 조회...');
  try {
    var chatsResult = KakaoAuto.getChats({ limit: 5 });
    if (chatsResult.success) {
      Logger.log('✅ 채팅방 ' + chatsResult.data.length + '개 확인됨 (최대 5개 표시)');
      for (var i = 0; i < Math.min(5, chatsResult.data.length); i++) {
        var chat = chatsResult.data[i];
        Logger.log('   ' + (i + 1) + '. ' + chat.name + ' → ' + chat.id);
      }
    } else {
      Logger.log('❌ 채팅방 조회 실패: ' + chatsResult.error);
    }
  } catch (e) {
    Logger.log('❌ 채팅방 조회 오류: ' + e.toString());
  }

  Logger.log('\n========================================');
  Logger.log('✅ 진단 완료');
  Logger.log('========================================');
}

/**
 * 테스트 메시지 전송 (관리자 채팅방)
 */
function testSendToDefaultChat() {
  var testChatId = ADMIN_CHAT_ID;
  var testMessage = '📢 테스트: ' + Utilities.formatDate(new Date(), 'Asia/Seoul', 'yyyy-MM-dd HH:mm:ss');

  Logger.log('🧪 테스트 메시지 전송 시작');
  Logger.log('채팅방 ID: ' + testChatId);
  Logger.log('메시지: ' + testMessage);

  if (!KakaoAuto.isLoggedIn()) {
    Logger.log('❌ 로그인 필요: ' + KakaoAuto.getAuthUrl());
    return;
  }

  try {
    var result = KakaoAuto.sendText(testChatId, testMessage);
    if (result.success) {
      Logger.log('✅ 전송 성공!');
    } else {
      Logger.log('❌ 전송 실패: ' + result.error);
    }
  } catch (e) {
    Logger.log('❌ 오류 발생: ' + e.toString());
  }
}

/**
 * 업체 정보 확인
 */
function checkVendorInfo() {
  Logger.log('========================================');
  Logger.log('🏢 업체 정보 확인');
  Logger.log('========================================');

  try {
    var srcSS = SpreadsheetApp.openById(SOURCE_SS_ID);
    var vendorInfoSheet = srcSS.getSheetByName(KAKAO_CONFIG.VENDOR_INFO_SHEET);

    if (!vendorInfoSheet) {
      Logger.log('❌ 업체 정보 시트를 찾을 수 없습니다: ' + KAKAO_CONFIG.VENDOR_INFO_SHEET);
      return;
    }

    var vendorData = vendorInfoSheet.getDataRange().getValues();
    Logger.log('📊 전체 행 수: ' + vendorData.length);

    var validCount = 0;
    for (var i = 1; i < vendorData.length; i++) {
      var vendorName = vendorData[i][KAKAO_CONFIG.VENDOR_NAME_COL_INFO - 1];
      var kakaoId = vendorData[i][KAKAO_CONFIG.KAKAO_ID_COL - 1];

      if (vendorName && kakaoId) {
        validCount++;
        if (validCount <= 10) {
          Logger.log('   ' + validCount + '. ' + vendorName + ' → ' + kakaoId);
        }
      }
    }

    Logger.log('\n✅ 유효한 업체 정보: ' + validCount + '개');
    if (validCount > 10) {
      Logger.log('   (처음 10개만 표시)');
    }

  } catch (e) {
    Logger.log('❌ 오류: ' + e.toString());
  }

  Logger.log('========================================');
}

/**
 * 실패한 항목만 재전송
 */
function retryFailedVendors() {
  // PropertiesService에서 실패 목록 불러오기
  var FAILED_VENDORS = loadFailedVendors();

  if (FAILED_VENDORS.length === 0) {
    Logger.log('✅ 재전송할 실패 항목이 없습니다.');
    return;
  }

  Logger.log('========================================');
  Logger.log('🔄 실패한 항목 재전송 시작');
  Logger.log('========================================');
  Logger.log('재전송 대상: ' + FAILED_VENDORS.length + '개 업체');
  for (var i = 0; i < FAILED_VENDORS.length; i++) {
    Logger.log('   ' + (i + 1) + '. ' + FAILED_VENDORS[i].name + ' (' + getFailedTypeText(FAILED_VENDORS[i]) + ')');
  }
  Logger.log('');

  // 재전송 모드로 전송
  sendKakaoMessagesToVendors(true);

  Logger.log('========================================');
  Logger.log('✅ 재전송 완료');
  Logger.log('========================================');
}

/**
 * 실패 목록 확인
 */
function checkFailedVendors() {
  Logger.log('========================================');
  Logger.log('📋 실패한 전송 항목 확인');
  Logger.log('========================================');

  // PropertiesService에서 실패 목록 불러오기
  var FAILED_VENDORS = loadFailedVendors();

  if (FAILED_VENDORS.length === 0) {
    Logger.log('✅ 실패한 항목이 없습니다.');
  } else {
    Logger.log('⚠️ 실패한 업체: ' + FAILED_VENDORS.length + '개');
    for (var i = 0; i < FAILED_VENDORS.length; i++) {
      Logger.log('   ' + (i + 1) + '. ' + FAILED_VENDORS[i].name + ' (' + getFailedTypeText(FAILED_VENDORS[i]) + ')');
    }
    Logger.log('\n💡 재전송하려면 retryFailedVendors() 함수를 실행하세요.');
  }

  Logger.log('========================================');
}

/**
 * 실패 목록 초기화 (수동)
 */
function clearFailedVendorsManual() {
  var FAILED_VENDORS = loadFailedVendors();
  var count = FAILED_VENDORS.length;
  clearFailedVendors(); // PropertiesService에서 삭제
  Logger.log('✅ 실패 목록 초기화: ' + count + '개 항목 제거됨');
}

/**
 * Slack 테스트 메시지 전송 (Webhook)
 */
function testSlackMessage() {
  Logger.log('🧪 Slack Webhook 테스트 메시지 전송...');

  if (!SLACK_CONFIG.WEBHOOK_URL) {
    Logger.log('❌ SLACK_CONFIG.WEBHOOK_URL이 설정되지 않았습니다.');
    Logger.log('   스크립트 상단의 SLACK_CONFIG.WEBHOOK_URL에 Webhook URL을 입력하세요.');
    return;
  }

  var testMessage = ':test_tube: *Slack Webhook 연동 테스트*\n\n';
  testMessage += '`' + Utilities.formatDate(new Date(), 'Asia/Seoul', 'yyyy-MM-dd HH:mm:ss') + '`\n\n';
  testMessage += '카카오톡 발송 봇이 정상적으로 연결되었습니다!\n\n';
  testMessage += '_참고: 스레드 기능을 사용하려면 Bot Token을 설정하세요._';

  sendSlackMessageWithWebhook(testMessage, ':white_check_mark:');
}

/**
 * Slack 스레드 테스트 (Bot Token 필요)
 */
function testSlackThread() {
  Logger.log('🧪 Slack 스레드 테스트...');

  if (!SLACK_CONFIG.BOT_TOKEN) {
    Logger.log('❌ SLACK_CONFIG.BOT_TOKEN이 설정되지 않았습니다.');
    Logger.log('   스레드 기능을 사용하려면 Bot Token을 설정하세요.');
    Logger.log('');
    Logger.log('📋 Bot Token 발급 방법:');
    Logger.log('   1. https://api.slack.com/apps 접속');
    Logger.log('   2. "Create New App" > "From scratch"');
    Logger.log('   3. OAuth & Permissions > Bot Token Scopes에서 추가:');
    Logger.log('      - chat:write');
    Logger.log('      - chat:write.public (public 채널용)');
    Logger.log('   4. "Install to Workspace" 클릭');
    Logger.log('   5. Bot User OAuth Token 복사 (xoxb-로 시작)');
    return;
  }

  // 1. 시작 메시지 전송
  var startMessage = ':test_tube: *스레드 테스트 시작*\n\n';
  startMessage += '`' + Utilities.formatDate(new Date(), 'Asia/Seoul', 'yyyy-MM-dd HH:mm:ss') + '`';

  Logger.log('1️⃣ 시작 메시지 전송...');
  var ts = sendSlackMessageWithApi(startMessage, null);

  if (!ts || ts === 'webhook') {
    Logger.log('❌ 시작 메시지 전송 실패 또는 ts를 받지 못함');
    return;
  }

  Logger.log('✅ 시작 메시지 ts: ' + ts);

  // 2초 대기
  Utilities.sleep(2000);

  // 2. 스레드로 종료 메시지 전송
  var endMessage = ':white_check_mark: *스레드 테스트 완료*\n\n';
  endMessage += '이 메시지는 위 메시지의 스레드로 전송되었습니다!';

  Logger.log('2️⃣ 스레드 메시지 전송...');
  sendSlackMessageWithApi(endMessage, ts);

  Logger.log('✅ 스레드 테스트 완료!');
}
