import json
import time
from typing import Dict, List, Any, Optional
from collections import deque
import sqlite3
import os

class MemoryManager:
    """메모리 및 컨텍스트 관리 시스템"""
    
    def __init__(self, db_path: str = "agent_memory.db", max_short_term_size: int = 50):
        self.db_path = db_path
        self.max_short_term_size = max_short_term_size
        
        # 단기 메모리 (대화 컨텍스트)
        self.short_term_memory = deque(maxlen=max_short_term_size)
        
        # 현재 세션 상태
        self.current_session = {
            "session_id": str(int(time.time())),
            "start_time": time.time(),
            "user_preferences": {},
            "active_tasks": [],
            "last_tools_used": []
        }
        
        # 장기 메모리 DB 초기화
        self._init_long_term_memory()
    
    def _init_long_term_memory(self):
        """장기 메모리 데이터베이스 초기화"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 사용자 상호작용 기록 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    timestamp REAL,
                    user_query TEXT,
                    agent_response TEXT,
                    tools_used TEXT,
                    success BOOLEAN
                )
            """)
            
            # 학습된 패턴 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS learned_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_type TEXT,
                    pattern_data TEXT,
                    success_count INTEGER DEFAULT 0,
                    failure_count INTEGER DEFAULT 0,
                    last_updated REAL
                )
            """)
            
            # 사용자 선호도 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    preference_key TEXT UNIQUE,
                    preference_value TEXT,
                    last_updated REAL
                )
            """)
            
            conn.commit()
    
    def add_to_short_term(self, interaction: Dict[str, Any]):
        """단기 메모리에 상호작용 추가"""
        interaction["timestamp"] = time.time()
        self.short_term_memory.append(interaction)
    
    def get_recent_context(self, limit: int = 5) -> List[Dict[str, Any]]:
        """최근 컨텍스트 반환"""
        return list(self.short_term_memory)[-limit:]
    
    def save_interaction(self, user_query: str, agent_response: str, tools_used: List[str], success: bool = True):
        """상호작용을 장기 메모리에 저장"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO interactions 
                (session_id, timestamp, user_query, agent_response, tools_used, success)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                self.current_session["session_id"],
                time.time(),
                user_query,
                agent_response,
                json.dumps(tools_used),
                success
            ))
            conn.commit()
        
        # 단기 메모리에도 추가
        self.add_to_short_term({
            "type": "interaction",
            "user_query": user_query,
            "agent_response": agent_response,
            "tools_used": tools_used,
            "success": success
        })
    
    def learn_pattern(self, pattern_type: str, pattern_data: Dict[str, Any], success: bool):
        """성공/실패 패턴 학습"""
        pattern_json = json.dumps(pattern_data)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 기존 패턴 확인
            cursor.execute("""
                SELECT id, success_count, failure_count 
                FROM learned_patterns 
                WHERE pattern_type = ? AND pattern_data = ?
            """, (pattern_type, pattern_json))
            
            result = cursor.fetchone()
            
            if result:
                # 기존 패턴 업데이트
                pattern_id, success_count, failure_count = result
                if success:
                    success_count += 1
                else:
                    failure_count += 1
                
                cursor.execute("""
                    UPDATE learned_patterns 
                    SET success_count = ?, failure_count = ?, last_updated = ?
                    WHERE id = ?
                """, (success_count, failure_count, time.time(), pattern_id))
            else:
                # 새 패턴 추가
                cursor.execute("""
                    INSERT INTO learned_patterns 
                    (pattern_type, pattern_data, success_count, failure_count, last_updated)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    pattern_type,
                    pattern_json,
                    1 if success else 0,
                    0 if success else 1,
                    time.time()
                ))
            
            conn.commit()
    
    def get_successful_patterns(self, pattern_type: str, limit: int = 10) -> List[Dict[str, Any]]:
        """성공적인 패턴 반환"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT pattern_data, success_count, failure_count
                FROM learned_patterns 
                WHERE pattern_type = ? AND success_count > failure_count
                ORDER BY (success_count - failure_count) DESC
                LIMIT ?
            """, (pattern_type, limit))
            
            patterns = []
            for row in cursor.fetchall():
                patterns.append({
                    "pattern_data": json.loads(row[0]),
                    "success_count": row[1],
                    "failure_count": row[2]
                })
            
            return patterns
    
    def update_user_preference(self, key: str, value: str):
        """사용자 선호도 업데이트"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO user_preferences 
                (preference_key, preference_value, last_updated)
                VALUES (?, ?, ?)
            """, (key, value, time.time()))
            conn.commit()
        
        self.current_session["user_preferences"][key] = value
    
    def get_user_preference(self, key: str, default: str = None) -> Optional[str]:
        """사용자 선호도 조회"""
        # 현재 세션에서 먼저 확인
        if key in self.current_session["user_preferences"]:
            return self.current_session["user_preferences"][key]
        
        # 장기 메모리에서 확인
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT preference_value FROM user_preferences 
                WHERE preference_key = ?
            """, (key,))
            
            result = cursor.fetchone()
            if result:
                self.current_session["user_preferences"][key] = result[0]
                return result[0]
        
        return default
    
    def get_session_context(self) -> Dict[str, Any]:
        """현재 세션 컨텍스트 반환"""
        return {
            "session_info": self.current_session,
            "recent_interactions": self.get_recent_context(),
            "user_preferences": self.current_session["user_preferences"]
        }
    
    def clear_short_term_memory(self):
        """단기 메모리 초기화"""
        self.short_term_memory.clear()
    
    def start_new_session(self):
        """새 세션 시작"""
        self.current_session = {
            "session_id": str(int(time.time())),
            "start_time": time.time(),
            "user_preferences": self.current_session.get("user_preferences", {}),
            "active_tasks": [],
            "last_tools_used": []
        }
        self.clear_short_term_memory() 