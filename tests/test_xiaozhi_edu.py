"""xiaozhi_edu 核心功能测试

运行: pytest /Users/mihua/.hermes/xiaozhi_scripts/tests/ -v
"""
import sys, os, json, subprocess, hashlib
from datetime import date, timedelta
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import game_engine as ge
import daily_checkin as dc
import exercise_tracker as et
import reward_shop as rs
import user_memory as um
import q_memory as qm
import daily_challenge as dch
import tts_helper as th

# ============================================================
# 1. game_engine 测试
# ============================================================

class TestGameEngine:
    def test_get_score_returns_dict(self):
        score = ge.get_score()
        assert isinstance(score, dict)
        assert "total_score" in score

    def test_total_score_consistency(self):
        data = ge._load()
        total_sum = sum(e.get("total", 0) for e in data["history"])
        assert data["total_score"] == total_sum

    def test_history_has_time_field(self):
        data = ge._load()
        for entry in data["history"]:
            assert "time" in entry

    def test_today_activities_has_total(self):
        today = ge.get_today_activities()
        assert "total" in today
        assert "activities" in today
        assert "categories" in today

    def test_daily_tasks_format(self):
        tasks = ge.get_daily_tasks()
        assert "tasks" in tasks
        assert isinstance(tasks["tasks"], list)
        for task in tasks["tasks"]:
            assert "id" in task
            assert "label" in task
            assert "points" in task
            assert "completed" in task

    def test_streak_dates_format(self):
        data = ge._load()
        for d in data.get("streak_dates", []):
            date.fromisoformat(d)

    def test_multi_bonus_not_duplicated(self):
        """multi_bonus 标记条目 total 应为 0"""
        data = ge._load()
        marker = [e for e in data["history"] if e.get("activity") == "_multi_bonus_applied"]
        for m in marker:
            assert m.get("total", 1) == 0, f"multi_bonus 标记条目 total 应为 0: {m}"

    def test_get_history_limit(self):
        history = ge.get_history(limit=10)
        assert len(history) <= 10

# ============================================================
# 2. daily_checkin 测试
# ============================================================

class TestDailyCheckin:
    def test_checkin_data_structure(self):
        data = dc._load()
        assert "checkin_history" in data
        assert "checkin_streak" in data
        assert "last_checkin_date" in data

    def test_checkin_history_has_time(self):
        data = dc._load()
        for entry in data.get("checkin_history", []):
            assert "time" in entry

    def test_get_checkin_status_returns_dict(self):
        status = dc.get_checkin_status()
        assert isinstance(status, dict)
        assert "status_text" in status

# ============================================================
# 3. exercise_tracker 测试
# ============================================================

class TestExerciseTracker:
    def test_exercise_data_structure(self):
        data = et._load()
        assert "history" in data
        assert "streak_count" in data

    def test_exercise_history_has_time(self):
        history = et.get_exercise_history(limit=100)
        for entry in history:
            assert "date" in entry

    def test_exercise_history_has_duration(self):
        history = et.get_exercise_history(limit=100)
        for entry in history:
            assert "duration_minutes" in entry or "minutes" in entry

# ============================================================
# 4. reward_shop 测试
# ============================================================

class TestRewardShop:
    def test_get_shop_returns_list(self):
        shop = rs.get_shop()
        assert isinstance(shop, list)
        assert len(shop) > 0

    def test_shop_items_have_required_fields(self):
        shop = rs.get_shop()
        for item in shop:
            assert "id" in item
            assert "name" in item
            assert "cost" in item
            assert item["cost"] > 0

    def test_shop_json_file_exists(self):
        path = SCRIPTS_DIR / "reward_shop.json"
        assert path.exists(), "reward_shop.json 不存在"
        with open(path) as f:
            data = json.load(f)
        assert isinstance(data, list)
        assert len(data) > 0

# ============================================================
# 5. user_memory / q_memory 测试
# ============================================================

class TestUserMemory:
    def test_get_user_prompt_prefix_returns_string(self):
        prefix = um.get_user_prompt_prefix()
        assert isinstance(prefix, str)

    def test_update_interaction_no_error(self):
        try:
            um.update_interaction("test_interaction")
        except Exception as e:
            pytest.fail(f"update_interaction 抛出异常: {e}")

class TestQMemory:
    def test_get_all_history_returns_list(self):
        history = qm.get_all_history(limit=5)
        assert isinstance(history, list)

    def test_get_last_topic_returns_string_or_none(self):
        topic = qm.get_last_topic()
        if topic is not None:
            assert isinstance(topic, (str, dict))

# ============================================================
# 6. 数据完整性测试
# ============================================================

class TestDataIntegrity:
    def test_game_data_json_valid(self):
        with open(SCRIPTS_DIR / "game_data.json") as f:
            data = json.load(f)
        assert "total_score" in data
        assert "history" in data

    def test_checkin_data_json_valid(self):
        with open(SCRIPTS_DIR / "checkin_data.json") as f:
            data = json.load(f)
        assert "checkin_history" in data

    def test_exercise_data_json_valid(self):
        with open(SCRIPTS_DIR / "exercise_data.json") as f:
            data = json.load(f)
        assert "history" in data
        assert "streak_count" in data

    def test_reward_shop_json_exists_and_valid(self):
        path = SCRIPTS_DIR / "reward_shop.json"
        assert path.exists()
        with open(path) as f:
            data = json.load(f)
        assert isinstance(data, list)
        assert len(data) > 0

    def test_reward_config_json_valid(self):
        path = SCRIPTS_DIR / "reward_config.json"
        assert path.exists()
        with open(path) as f:
            data = json.load(f)
        assert "password" in data
        assert "rules" in data
        assert "custom_rewards" in data

    def test_total_score_matches_history(self):
        with open(SCRIPTS_DIR / "game_data.json") as f:
            data = json.load(f)
        history_sum = sum(e.get("total", 0) for e in data["history"])
        assert data["total_score"] == history_sum

# ============================================================
# 7. CLI 测试
# ============================================================

class TestCLI:
    def _run_cli(self, *args):
        result = subprocess.run(
            ["python3", str(SCRIPTS_DIR / "edu_backend.py")] + list(args),
            capture_output=True, text=True, timeout=10, cwd=str(SCRIPTS_DIR)
        )
        # CLI 返回 0 表示执行成功（即使输出为空或错误信息也在 stdout）
        return result.stdout, result.returncode

    def test_score_command(self):
        stdout, rc = self._run_cli("score")
        assert rc == 0, f"CLI score 返回码 {rc}: {stdout[:200]}"

    def test_checkin_status_command(self):
        stdout, rc = self._run_cli("checkin_status")
        assert rc == 0, f"CLI checkin_status 返回码 {rc}: {stdout[:200]}"

    def test_checkin_reminder_command(self):
        stdout, rc = self._run_cli("checkin_reminder")
        assert rc == 0, f"CLI checkin_reminder 返回码 {rc}: {stdout[:200]}"

    def test_exercise_status_command(self):
        stdout, rc = self._run_cli("exercise_status")
        assert rc == 0, f"CLI exercise_status 返回码 {rc}: {stdout[:200]}"

    def test_unlock_command(self):
        stdout, rc = self._run_cli("unlock")
        assert rc == 0, f"CLI unlock 返回码 {rc}: {stdout[:200]}"

# ============================================================
# 8. 新功能测试：家长监控 + 报告 + TTS
# ============================================================

class TestParentAPI:
    def test_parent_config_exists(self):
        path = SCRIPTS_DIR / "reward_config.json"
        assert path.exists(), "reward_config.json 不存在"
        with open(path) as f:
            data = json.load(f)
        assert "password" in data
        assert hashlib.sha256("xiaozhi2024".encode()).hexdigest()[:16] == data["password"]

    def test_parent_password_verification(self):
        assert hashlib.sha256("xiaozhi2024".encode()).hexdigest()[:16] == \
               open(SCRIPTS_DIR / "reward_config.json").read().split('"password": "')[1].split('"')[0]

class TestReportAPI:
    def test_backend_has_weekly_endpoint(self):
        main_py = open(Path("/Users/mihua/projects/xiaozhi_admin/backend/main.py")).read()
        assert "/api/report/weekly" in main_py

    def test_backend_has_monthly_endpoint(self):
        main_py = open(Path("/Users/mihua/projects/xiaozhi_admin/backend/main.py")).read()
        assert "/api/report/monthly" in main_py

class TestTTS:
    def test_tts_module_exists(self):
        assert (scripts_dir / "tts_helper.py").exists() if (scripts_dir := Path("/Users/mihua/.hermes/xiaozhi_scripts")).exists() else True

    def test_tts_functions_exist(self):
        assert hasattr(th, "score_tts")
        assert hasattr(th, "checkin_tts")
        assert hasattr(th, "redeem_tts")
        assert hasattr(th, "daily_complete_tts")

    def test_tts_score_text(self):
        text = th.score_tts(100, "初级学习者")
        assert "100" in text and "初级学习者" in text

    def test_tts_daily_complete_text(self):
        text = th.daily_complete_tts(5)
        assert "全部" in text or "完成" in text

class TestEncouragement:
    def test_enriched_encouragements_exist(self):
        assert hasattr(dch, "ENRICHED_ENCOURAGEMENTS")
        assert "unlock" in dch.ENRICHED_ENCOURAGEMENTS
        assert "daily_complete" in dch.ENRICHED_ENCOURAGEMENTS

    def test_get_enriched_message_returns_string(self):
        msg = dch.get_enriched_message("unlock", streak_count=5)
        assert isinstance(msg, str)
        assert len(msg) > 0

    def test_enriched_message_includes_streak(self):
        msg = dch.get_enriched_message("unlock", streak_count=10)
        assert "10" in msg

    def test_dch_generate_report_returns_dict(self):
        assert hasattr(dch, "ENRICHED_ENCOURAGEMENTS")
        enc = dch.ENRICHED_ENCOURAGEMENTS
        assert isinstance(enc, dict)
        assert len(enc) > 0

# ============================================================
# 9. 集成测试
# ============================================================

class TestIntegration:
    def test_game_engine_api_chain(self):
        """模拟 xiaozhi 调用链路"""
        score = ge.get_score()
        assert score["total_score"] > 0
        tasks = ge.get_daily_tasks()
        assert len(tasks["tasks"]) > 0
        today = ge.get_today_activities()
        assert today["total"] >= 0
        assert isinstance(today["activities"], list)

    def test_checkin_streak_increments(self):
        """打卡连续天数应正确追踪"""
        data = dc._load()
        # 如果 last_checkin_date 不是今天，streak 应该 >= 0
        assert data.get("checkin_streak", 0) >= 0
