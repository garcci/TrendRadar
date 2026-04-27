# -*- coding: utf-8 -*-
"""QuotaMonitor 端到端测试"""

import json
import os
import tempfile
from datetime import datetime, timedelta


class TestQuotaMonitor:
    def __init__(self):
        self.tmpdir = tempfile.mkdtemp(prefix="e2e_qm_")
        os.makedirs(f"{self.tmpdir}/evolution", exist_ok=True)
        from evolution.quota_monitor import QuotaMonitor
        self.monitor = QuotaMonitor(self.tmpdir)

    def _write_usage(self, records):
        path = f"{self.tmpdir}/evolution/ai_provider_usage.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)

    def test_get_usage_today(self):
        today = datetime.now().strftime("%Y-%m-%d")
        self._write_usage([
            {"provider": "google_gemini", "timestamp": f"{today}T10:00:00", "task_type": "generate", "tokens_used": 100, "cost": 0, "latency": 1.0, "success": True},
            {"provider": "google_gemini", "timestamp": f"{today}T11:00:00", "task_type": "generate", "tokens_used": 200, "cost": 0, "latency": 1.2, "success": True},
        ])
        usage = self.monitor.get_usage_today()
        assert "google_gemini" in usage, "google_gemini should be in usage"
        assert usage["google_gemini"] == 300, f"Expected 300, got {usage['google_gemini']}"
        return True

    def test_get_usage_today_empty(self):
        self._write_usage([])
        usage = self.monitor.get_usage_today()
        assert usage == {}, "Empty usage should return empty dict"
        return True

    def test_get_quota_status(self):
        today = datetime.now().strftime("%Y-%m-%d")
        self._write_usage([
            {"provider": "google_gemini", "timestamp": f"{today}T10:00:00", "task_type": "generate", "tokens_used": 100, "cost": 0, "latency": 1.0, "success": True},
        ])
        statuses = self.monitor.get_quota_status()
        assert len(statuses) == 4, f"Expected 4 providers, got {len(statuses)}"
        gemini = next((s for s in statuses if s.provider == "Google Gemini"), None)
        assert gemini is not None, "Google Gemini status should exist"
        assert gemini.used == 100, f"Expected used=100, got {gemini.used}"
        return True

    def test_quota_status_warning(self):
        today = datetime.now().strftime("%Y-%m-%d")
        self._write_usage([
            {"provider": "google_gemini", "timestamp": f"{today}T10:00:00", "task_type": "generate", "tokens_used": 800, "cost": 0, "latency": 1.0, "success": True},
        ])
        statuses = self.monitor.get_quota_status()
        gemini = next((s for s in statuses if s.provider == "Google Gemini"), None)
        assert gemini.status == "warning", f"Expected warning, got {gemini.status}"
        return True

    def test_quota_status_critical(self):
        today = datetime.now().strftime("%Y-%m-%d")
        self._write_usage([
            {"provider": "google_gemini", "timestamp": f"{today}T10:00:00", "task_type": "generate", "tokens_used": 1300, "cost": 0, "latency": 1.0, "success": True},
        ])
        statuses = self.monitor.get_quota_status()
        gemini = next((s for s in statuses if s.provider == "Google Gemini"), None)
        assert gemini.status == "critical", f"Expected critical, got {gemini.status}"
        return True

    def test_generate_report(self):
        today = datetime.now().strftime("%Y-%m-%d")
        self._write_usage([
            {"provider": "cloudflare_workers_ai", "timestamp": f"{today}T10:00:00", "task_type": "summarize", "tokens_used": 500, "cost": 0, "latency": 0.5, "success": True},
        ])
        report = self.monitor.generate_report()
        assert "Cloudflare Workers AI" in report, "Report should mention Cloudflare Workers AI"
        assert "免费AI额度监控报告" in report, "Report should have title"
        return True

    def test_check_alerts(self):
        today = datetime.now().strftime("%Y-%m-%d")
        self._write_usage([
            {"provider": "google_gemini", "timestamp": f"{today}T10:00:00", "task_type": "generate", "tokens_used": 1300, "cost": 0, "latency": 1.0, "success": True},
        ])
        alerts = self.monitor.check_alerts()
        assert any("🔴" in a for a in alerts), "Should have critical alert"
        return True

    def test_check_alerts_normal(self):
        today = datetime.now().strftime("%Y-%m-%d")
        self._write_usage([
            {"provider": "google_gemini", "timestamp": f"{today}T10:00:00", "task_type": "generate", "tokens_used": 100, "cost": 0, "latency": 1.0, "success": True},
        ])
        alerts = self.monitor.check_alerts()
        assert any("✅" in a for a in alerts), "Should have normal alert"
        return True

    def test_record_usage(self):
        path = f"{self.tmpdir}/evolution/ai_provider_usage.json"
        if os.path.exists(path):
            os.remove(path)
        self.monitor.record_usage("google_gemini", "generate", 150, 0, 1.0, True)
        assert os.path.exists(path), "Usage file should be created"
        with open(path, "r", encoding="utf-8") as f:
            records = json.load(f)
        assert len(records) == 1, f"Expected 1 record, got {len(records)}"
        assert records[0]["provider"] == "google_gemini", "Provider mismatch"
        return True

    def test_get_daily_cost(self):
        today = datetime.now().strftime("%Y-%m-%d")
        self._write_usage([
            {"provider": "deepseek", "timestamp": f"{today}T10:00:00", "task_type": "generate", "tokens_used": 1_000_000, "cost": 1.0, "latency": 2.0, "success": True},
        ])
        from evolution.quota_monitor import get_daily_cost
        cost = get_daily_cost(self.tmpdir)
        assert cost > 0, f"Expected positive cost, got {cost}"
        return True

    def run_all(self):
        results = []
        passed = 0
        for name in dir(self):
            if name.startswith("test_"):
                try:
                    self.__getattribute__(name)()
                    results.append({"name": name, "status": "PASS"})
                    passed += 1
                except Exception as e:
                    results.append({"name": name, "status": "FAIL", "error": str(e)})
        return {"all_passed": passed == len(results), "passed": passed, "failed": len(results) - passed, "results": results}
