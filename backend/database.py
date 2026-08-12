"""
看得见的声音 - 数据访问层
SQLite 持久化：学习记录（含录音二进制 BLOB）、用户进度。

设计要点：
- 学习记录与用户进度在同一事务内更新，保证一致性（有记录必有进度）
- 列表/统计接口绝不携带 BLOB，录音通过 /api/learning-records/{id}/audio 按需拉取
- 时间戳统一存 created_at（ISO8601 UTC），接口层映射为前端 createdAt
"""
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Optional

DB_PATH = "pronunciation.db"

# 12 个发音单元（与 main.py /api/pronunciation-units 保持一致）
DEFAULT_UNITS = [
    {"id": "ma", "pinyin": "mā", "character": "妈"},
    {"id": "ba", "pinyin": "bā", "character": "八"},
    {"id": "pa", "pinyin": "pā", "character": "趴"},
    {"id": "ta", "pinyin": "tā", "character": "他"},
    {"id": "yi", "pinyin": "yī", "character": "一"},
    {"id": "wu", "pinyin": "wǔ", "character": "五"},
    {"id": "yu", "pinyin": "yú", "character": "鱼"},
    {"id": "mao", "pinyin": "māo", "character": "猫"},
    {"id": "gou", "pinyin": "gǒu", "character": "狗"},
    {"id": "niao", "pinyin": "niǎo", "character": "鸟"},
    {"id": "ma_t2", "pinyin": "má", "character": "麻"},
    {"id": "ma_t3", "pinyin": "mǎ", "character": "马"},
]


def _now() -> str:
    """当前时间（ISO8601 UTC）"""
    return datetime.now(timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = "pronunciation.db") -> None:
    """初始化数据库：建表（幂等）"""
    global DB_PATH
    DB_PATH = db_path
    conn = _connect()
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS learning_records (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                unit_id TEXT NOT NULL,
                pinyin TEXT NOT NULL,
                character TEXT NOT NULL,
                score REAL NOT NULL,
                accuracy REAL NOT NULL,
                fluency REAL NOT NULL,
                pronunciation REAL NOT NULL,
                duration REAL NOT NULL DEFAULT 0,
                feedback TEXT NOT NULL DEFAULT '',
                audio_blob BLOB,
                audio_type TEXT NOT NULL DEFAULT 'audio/webm',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS user_progress (
                user_id TEXT PRIMARY KEY,
                total_units INTEGER NOT NULL DEFAULT 12,
                completed_units INTEGER NOT NULL DEFAULT 0,
                total_practice INTEGER NOT NULL DEFAULT 0,
                average_score REAL NOT NULL DEFAULT 0,
                last_practice_at TEXT NOT NULL DEFAULT '',
                unit_progress TEXT NOT NULL DEFAULT '[]'
            );

            CREATE INDEX IF NOT EXISTS idx_records_user ON learning_records(user_id, created_at);
            """
        )
        conn.commit()
    finally:
        conn.close()


def _default_progress(user_id: str) -> dict:
    """构造新用户的默认进度（覆盖全部单元）"""
    return {
        "userId": user_id,
        "totalUnits": len(DEFAULT_UNITS),
        "completedUnits": 0,
        "totalPractice": 0,
        "averageScore": 0.0,
        "lastPracticeAt": "",
        "unitProgress": [
            {
                "unitId": u["id"],
                "pinyin": u["pinyin"],
                "character": u["character"],
                "bestScore": 0,
                "practiceCount": 0,
                "lastPracticeAt": "",
                "status": "not_started",
            }
            for u in DEFAULT_UNITS
        ],
    }


def _row_to_progress(row: sqlite3.Row) -> dict:
    unit_progress = json.loads(row["unit_progress"] or "[]")
    return {
        "userId": row["user_id"],
        "totalUnits": row["total_units"],
        "completedUnits": row["completed_units"],
        "totalPractice": row["total_practice"],
        "averageScore": row["average_score"],
        "lastPracticeAt": row["last_practice_at"],
        "unitProgress": unit_progress,
    }


def _record_to_dict(row: sqlite3.Row) -> dict:
    """记录 → 前端字段格式（不含 BLOB，附 audioUrl 指向音频流接口）"""
    return {
        "id": row["id"],
        "userId": row["user_id"],
        "unitId": row["unit_id"],
        "pinyin": row["pinyin"],
        "character": row["character"],
        "score": row["score"],
        "accuracy": row["accuracy"],
        "fluency": row["fluency"],
        "pronunciation": row["pronunciation"],
        "duration": row["duration"],
        "feedback": row["feedback"],
        "audioUrl": f"/api/learning-records/{row['id']}/audio",
        "createdAt": row["created_at"],
    }


def _upsert_progress(conn: sqlite3.Connection, progress: dict) -> None:
    conn.execute(
        """
        INSERT OR REPLACE INTO user_progress
            (user_id, total_units, completed_units, total_practice, average_score, last_practice_at, unit_progress)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            progress["userId"],
            progress["totalUnits"],
            progress["completedUnits"],
            progress["totalPractice"],
            progress["averageScore"],
            progress["lastPracticeAt"],
            json.dumps(progress["unitProgress"], ensure_ascii=False),
        ),
    )


def create_learning_record(
    user_id: str,
    unit_id: str,
    pinyin: str,
    character: str,
    score: float,
    accuracy: float,
    fluency: float,
    pronunciation: float,
    duration: float,
    feedback: str,
    audio_blob: Optional[bytes],
    audio_type: str = "audio/webm",
) -> str:
    """写学习记录 + 同一事务内同步更新用户进度，返回 record_id"""
    record_id = uuid.uuid4().hex
    created_at = _now()
    conn = _connect()
    try:
        conn.execute("BEGIN")
        # 1. 写入学习记录（含录音二进制）
        conn.execute(
            """
            INSERT INTO learning_records
                (id, user_id, unit_id, pinyin, character, score, accuracy, fluency,
                 pronunciation, duration, feedback, audio_blob, audio_type, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record_id, user_id, unit_id, pinyin, character, score, accuracy,
                fluency, pronunciation, duration, feedback, audio_blob, audio_type, created_at,
            ),
        )

        # 2. 读取或初始化用户进度
        row = conn.execute(
            "SELECT * FROM user_progress WHERE user_id = ?", (user_id,)
        ).fetchone()
        progress = _row_to_progress(row) if row else _default_progress(user_id)

        # 3. 更新进度（逻辑迁移自前端 addLearningRecord）
        progress["totalPractice"] += 1
        progress["lastPracticeAt"] = created_at

        unit = next((u for u in progress["unitProgress"] if u["unitId"] == unit_id), None)
        if unit is None:
            unit = {
                "unitId": unit_id,
                "pinyin": pinyin,
                "character": character,
                "bestScore": 0,
                "practiceCount": 0,
                "lastPracticeAt": "",
                "status": "not_started",
            }
            progress["unitProgress"].append(unit)

        unit["practiceCount"] += 1
        unit["lastPracticeAt"] = created_at
        if score >= 80 and unit["status"] != "completed":
            unit["status"] = "completed"
        elif unit["status"] == "not_started":
            unit["status"] = "in_progress"
        if score > unit["bestScore"]:
            unit["bestScore"] = score

        # 完成单元数按状态重算，避免增量维护出错
        progress["completedUnits"] = sum(
            1 for u in progress["unitProgress"] if u["status"] == "completed"
        )
        # 平均分 = 该用户全部记录的平均分（SQL 聚合）
        avg = conn.execute(
            "SELECT AVG(score) FROM learning_records WHERE user_id = ?", (user_id,)
        ).fetchone()[0]
        progress["averageScore"] = round(avg, 1) if avg else 0.0

        _upsert_progress(conn, progress)
        conn.commit()
        return record_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_learning_records(user_id: str, limit: int = 20) -> list[dict]:
    """获取指定用户的学习记录（不含 BLOB）"""
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT * FROM learning_records WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [_record_to_dict(r) for r in rows]
    finally:
        conn.close()


def get_all_learning_records(limit: int = 100) -> list[dict]:
    """获取全部用户的学习记录（后台管理用，不含 BLOB）"""
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT * FROM learning_records ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [_record_to_dict(r) for r in rows]
    finally:
        conn.close()


def get_audio(record_id: str) -> Optional[tuple[bytes, str]]:
    """按记录 id 获取录音二进制与 MIME 类型；不存在返回 None"""
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT audio_blob, audio_type FROM learning_records WHERE id = ?",
            (record_id,),
        ).fetchone()
        if row is None or row["audio_blob"] is None:
            return None
        return (row["audio_blob"], row["audio_type"] or "audio/webm")
    finally:
        conn.close()


def get_user_progress(user_id: str) -> dict:
    """获取用户进度；用户不存在时初始化默认进度"""
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT * FROM user_progress WHERE user_id = ?", (user_id,)
        ).fetchone()
        if row is None:
            progress = _default_progress(user_id)
            _upsert_progress(conn, progress)
            conn.commit()
            return progress
        return _row_to_progress(row)
    finally:
        conn.close()


def update_user_progress(user_id: str, progress: dict) -> None:
    """手动更新用户进度（兼容原接口）"""
    conn = _connect()
    try:
        conn.execute("BEGIN")
        data = {
            "userId": user_id,
            "totalUnits": progress.get("totalUnits", len(DEFAULT_UNITS)),
            "completedUnits": progress.get("completedUnits", 0),
            "totalPractice": progress.get("totalPractice", 0),
            "averageScore": progress.get("averageScore", 0.0),
            "lastPracticeAt": progress.get("lastPracticeAt", ""),
            "unitProgress": progress.get("unitProgress", []),
        }
        _upsert_progress(conn, data)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_stats() -> dict:
    """后台统计卡片数据（SQL 聚合，不拉全表）"""
    conn = _connect()
    try:
        total_users = conn.execute(
            "SELECT COUNT(DISTINCT user_id) FROM learning_records"
        ).fetchone()[0]
        total_records = conn.execute(
            "SELECT COUNT(*) FROM learning_records"
        ).fetchone()[0]
        today = datetime.now().strftime("%Y-%m-%d")
        today_records = conn.execute(
            "SELECT COUNT(*) FROM learning_records WHERE date(created_at) = ?",
            (today,),
        ).fetchone()[0]
        avg_row = conn.execute("SELECT AVG(score) FROM learning_records").fetchone()[0]
        avg_score = round(avg_row, 1) if avg_row else 0.0

        completed = total = 0
        for r in conn.execute(
            "SELECT total_units, completed_units FROM user_progress"
        ).fetchall():
            total += r["total_units"]
            completed += r["completed_units"]
        completion_rate = round(completed / total * 100) if total else 0

        return {
            "totalUsers": total_users,
            "totalRecords": total_records,
            "todayRecords": today_records,
            "averageScore": avg_score,
            "completionRate": completion_rate,
        }
    finally:
        conn.close()
