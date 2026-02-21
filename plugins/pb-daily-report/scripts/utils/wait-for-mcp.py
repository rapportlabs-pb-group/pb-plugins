#!/usr/bin/env python3
"""
MCP 로딩 대기 및 상태 확인 스크립트
Claude Code의 MCP 연결이 준비될 때까지 대기
"""

import time
import subprocess
import logging
import sys
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def check_mcp_status(max_attempts=20, wait_seconds=15):
    """MCP 상태를 확인하고 로딩 완료까지 대기"""
    
    logging.info("🔍 Checking MCP connection status...")
    
    for attempt in range(1, max_attempts + 1):
        try:
            logging.info(f"📡 MCP connection attempt {attempt}/{max_attempts}")
            
            # BigQuery 연결 테스트 (가장 빠른 검증)
            result = subprocess.run(
                ['claude', '/pb-test'],
                capture_output=True,
                text=True,
                timeout=120,
                input='bigquery\n'
            )
            
            if result.returncode == 0:
                logging.info("✅ MCP connections are ready!")
                return True
            else:
                logging.warning(f"⚠️ MCP not ready yet, attempt {attempt}")
                logging.debug(f"Error: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            logging.warning(f"⏰ Timeout on attempt {attempt}")
        except Exception as e:
            logging.error(f"💥 Error on attempt {attempt}: {str(e)}")
        
        if attempt < max_attempts:
            logging.info(f"⏳ Waiting {wait_seconds} seconds before retry...")
            time.sleep(wait_seconds)
    
    logging.error("❌ MCP connections failed to load after maximum attempts")
    return False

def execute_with_mcp_ready():
    """MCP가 준비된 후 PB 리포트 실행"""
    
    logging.info("🚀 Starting PB Report with MCP readiness check")
    
    # MCP 상태 확인
    if not check_mcp_status():
        logging.error("❌ Cannot proceed - MCP connections not ready")
        sys.exit(1)
    
    # 추가 안정성을 위한 짧은 대기
    logging.info("⏳ Additional 30-second stabilization wait...")
    time.sleep(30)
    
    # PB 리포트 실행
    logging.info("📊 Executing PB Daily Report...")
    try:
        result = subprocess.run(
            ['claude', '/pb-report'],
            capture_output=True,
            text=True,
            timeout=600  # 10분 타임아웃
        )
        
        if result.returncode == 0:
            logging.info("✅ PB Report completed successfully!")
            logging.info(f"Output: {result.stdout}")
        else:
            logging.error(f"❌ PB Report failed: {result.stderr}")
            sys.exit(1)
            
    except subprocess.TimeoutExpired:
        logging.error("⏰ PB Report execution timed out")
        sys.exit(1)
    except Exception as e:
        logging.error(f"💥 PB Report execution error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    execute_with_mcp_ready()