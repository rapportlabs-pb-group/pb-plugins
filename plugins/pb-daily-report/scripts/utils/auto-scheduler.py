#!/usr/bin/env python3
"""
PB Daily Report Auto Scheduler
자동화 스케줄러 - Claude Code와 연동
"""

import schedule
import time
import subprocess
import logging
from datetime import datetime, timezone, timedelta
import os

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pb-report-scheduler.log'),
        logging.StreamHandler()
    ]
)

class PBReportScheduler:
    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path
        self.kst = timezone(timedelta(hours=9))
        
    def execute_pb_report(self):
        """PB 리포트 실행 (MCP 대기 로직 포함)"""
        try:
            logging.info("🚀 Starting PB Daily Report execution with MCP readiness check...")
            
            # MCP 대기 스크립트 실행
            result = subprocess.run(
                ['/usr/bin/python3', f'{self.workspace_path}/wait-for-mcp.py'],
                cwd=self.workspace_path,
                capture_output=True,
                text=True,
                timeout=900  # 15분 타임아웃 (MCP 로딩 + 실행)
            )
            
            if result.returncode == 0:
                logging.info("✅ PB Report executed successfully")
                logging.info(f"Output: {result.stdout}")
            else:
                logging.error(f"❌ PB Report execution failed: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            logging.error("⏰ PB Report execution timed out")
        except Exception as e:
            logging.error(f"💥 PB Report execution error: {str(e)}")
            
    def test_components(self):
        """컴포넌트 테스트 실행"""
        try:
            logging.info("🧪 Running component tests...")
            
            result = subprocess.run(
                ['claude', 'code', '/pb-test'],
                cwd=self.workspace_path,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                logging.info("✅ Component tests passed")
            else:
                logging.warning(f"⚠️ Component tests had issues: {result.stderr}")
                
        except Exception as e:
            logging.error(f"💥 Component test error: {str(e)}")

def main():
    # 워크스페이스 경로 설정
    workspace = "<project-root>"
    scheduler = PBReportScheduler(workspace)
    
    # 스케줄 설정
    schedule.every().day.at("11:00").do(scheduler.execute_pb_report)  # 매일 11시
    schedule.every().hour.do(scheduler.test_components)  # 매시간 헬스체크
    
    logging.info("📅 PB Report Scheduler started")
    logging.info("⏰ Daily report: 11:00 KST")
    logging.info("🔍 Component tests: Every hour")
    
    # 첫 실행시 테스트
    scheduler.test_components()
    
    # 스케줄러 실행
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # 1분마다 체크
        except KeyboardInterrupt:
            logging.info("🛑 Scheduler stopped by user")
            break
        except Exception as e:
            logging.error(f"💥 Scheduler error: {str(e)}")
            time.sleep(300)  # 5분 후 재시도

if __name__ == "__main__":
    main()