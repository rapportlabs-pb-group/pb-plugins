/***************************************************
 * 회사 휴일 시트 일괄 생성 유틸리티
 *
 * 사용법: 아무 브랜드의 Apps Script 에디터에서 실행
 *   1. 이 파일 내용을 Apps Script에 붙여넣기
 *   2. setupAllBrandHolidays() 실행
 *   3. 실행 후 이 코드 삭제 (일회성)
 *
 * 각 브랜드 스프레드시트에 '휴일' 탭을 생성하고
 * 2025~2026년 한국 공휴일을 자동 입력합니다.
 ***************************************************/

var BRAND_SPREADSHEETS = {
  '노어':       '1q0CsxQXe3W-Y6xDcgNY-uT1oBDH_IZgrK-Gm7uTl8YE',
  '퀸즈셀렉션':  '1CqbglHwEFrQzYUPA4oHyrv7doG3pAtE3tUs68wfaN4w',
  '베르다':      '1Z8S1gl1bjc0YaQmIQU3_QhvpA8xxCEYHtedMuOM2wco',
  '지재':       '1MDEQrx_o9YqFmwbiSTDYiG4cJ0tvBpXuUiIYXog15AI',
  '다나앤페타':   '1JkTrLc7uhEfMpHIFUZ2EvwFy3Kp76AGa-h9pagPwz5k',
  '마치마라':    '11tIOjKJ0WKvUcMh8M6Z2TpOdU3n9JkO71ukoDPuzPRY'
};

var HOLIDAY_SHEET_NAME = '휴일';

/**
 * 한국 공휴일 목록 (2025~2026)
 * [날짜, 휴일명]
 * 회사 자체 휴일은 아래 목록에 추가하세요.
 */
function getHolidayList() {
  return [
    // ===== 2025년 =====
    ['2025-01-01', '신정'],
    ['2025-01-28', '설날 연휴'],
    ['2025-01-29', '설날'],
    ['2025-01-30', '설날 연휴'],
    ['2025-03-01', '삼일절'],
    ['2025-03-03', '삼일절 대체휴일'],
    ['2025-05-05', '어린이날'],
    ['2025-05-06', '석가탄신일'],
    ['2025-06-06', '현충일'],
    ['2025-08-15', '광복절'],
    ['2025-10-03', '개천절'],
    ['2025-10-05', '추석 연휴'],
    ['2025-10-06', '추석'],
    ['2025-10-07', '추석 연휴'],
    ['2025-10-08', '추석 대체휴일'],
    ['2025-10-09', '한글날'],
    ['2025-12-25', '성탄절'],

    // ===== 2026년 =====
    ['2026-01-01', '신정'],
    ['2026-02-12', '회사 방학'],
    ['2026-02-13', '회사 방학'],
    ['2026-02-15', '설날 연휴'],
    ['2026-02-16', '설날'],
    ['2026-02-17', '설날 연휴'],
    ['2026-02-18', '설날 대체휴일'],
    ['2026-02-19', '회사 방학'],
    ['2026-02-20', '회사 방학'],
    ['2026-03-01', '삼일절'],
    ['2026-03-02', '삼일절 대체휴일'],
    ['2026-05-05', '어린이날'],
    ['2026-05-24', '석가탄신일'],
    ['2026-05-25', '석가탄신일 대체휴일'],
    ['2026-06-06', '현충일'],
    ['2026-08-15', '광복절'],
    ['2026-08-17', '광복절 대체휴일'],
    ['2026-09-24', '추석 연휴'],
    ['2026-09-25', '추석'],
    ['2026-09-26', '추석 연휴'],
    ['2026-10-03', '개천절'],
    ['2026-10-05', '개천절 대체휴일'],
    ['2026-10-09', '한글날'],
    ['2026-12-25', '성탄절']
  ];
}

/**
 * 6개 브랜드 스프레드시트에 '휴일' 탭 일괄 생성
 */
function setupAllBrandHolidays() {
  var brands = Object.keys(BRAND_SPREADSHEETS);
  var holidays = getHolidayList();
  var results = [];

  for (var i = 0; i < brands.length; i++) {
    var brandName = brands[i];
    var sheetId = BRAND_SPREADSHEETS[brandName];

    try {
      var result = createHolidaySheet(sheetId, brandName, holidays);
      results.push(result);
    } catch (e) {
      results.push('[실패] ' + brandName + ': ' + e.message);
    }
  }

  Logger.log('===== 휴일 시트 생성 결과 =====');
  for (var j = 0; j < results.length; j++) {
    Logger.log(results[j]);
  }
}

/**
 * 개별 스프레드시트에 휴일 시트 생성
 */
function createHolidaySheet(spreadsheetId, brandName, holidays) {
  var ss = SpreadsheetApp.openById(spreadsheetId);
  var sheet = ss.getSheetByName(HOLIDAY_SHEET_NAME);

  if (sheet) {
    sheet.clear();
  } else {
    sheet = ss.insertSheet(HOLIDAY_SHEET_NAME);
  }

  // 헤더
  sheet.getRange(1, 1).setValue('날짜');
  sheet.getRange(1, 2).setValue('휴일명');
  sheet.getRange(1, 1, 1, 2)
    .setFontWeight('bold')
    .setBackground('#4a86c8')
    .setFontColor('#ffffff');

  // 데이터 입력
  if (holidays.length > 0) {
    sheet.getRange(2, 1, holidays.length, 2).setValues(holidays);
  }

  // A열 날짜 서식
  sheet.getRange(2, 1, holidays.length, 1).setNumberFormat('yyyy-mm-dd');

  // 열 너비 조정
  sheet.setColumnWidth(1, 120);
  sheet.setColumnWidth(2, 160);

  // 시트를 맨 뒤로 이동
  var sheetCount = ss.getSheets().length;
  ss.moveActiveSheet(sheetCount);

  return '[완료] ' + brandName + ' (' + holidays.length + '개 휴일 입력)';
}
