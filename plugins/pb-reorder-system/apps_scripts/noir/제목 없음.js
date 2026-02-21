function diagnoseAccess() {
  var ids = [
    { label: 'SOURCE', id: SOURCE_SS_ID, tabs: ['★사입자확인시트★'] },
    { label: 'TARGET', id: TARGET_SS_ID, tabs: ['동대문 누적', '발주(리오더)_동대문'] }
  ];
  for (var k = 0; k < ids.length; k++) {
    var it = ids[k];
    Logger.log('--- ' + it.label + ' ---');
    try {
      // Drive에서 파일 메타 먼저 접근(권한/ID 문제 즉시 드러남)
      var file = DriveApp.getFileById(it.id);
      Logger.log('File name: ' + file.getName() + ' (inTrash=' + file.isTrashed() + ')');
    } catch (e1) {
      Logger.log('DriveApp.getFileById 실패: ' + e1.message);
      continue; // 다음 항목으로
    }

    try {
      var ss = SpreadsheetApp.openById(it.id);
      var sheets = ss.getSheets().map(function(s){ return s.getName(); });
      Logger.log('Sheet list: ' + sheets.join(', '));
      // 필수 탭 점검
      for (var j = 0; j < it.tabs.length; j++) {
        var need = it.tabs[j];
        var ok = ss.getSheetByName(need) != null;
        Logger.log('Tab "' + need + '": ' + (ok ? 'OK' : 'NOT FOUND'));
      }
    } catch (e2) {
      Logger.log('SpreadsheetApp.openById 실패: ' + e2.message);
    }
  }
  Logger.log('진단 종료');
}

function myFunction() {
  diagnoseAccess();
}