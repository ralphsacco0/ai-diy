"""
Sprint Orchestrator (Sequential MVP)

Coordinates sprint execution sequentially for MVP:
- Loads sprint plan file (static/appdocs/sprints/{sprint_id}.json)
- Writes append-only execution log (static/appdocs/sprints/execution_log_{sprint_id}.jsonl)
- Logs key lifecycle events; updates sprint plan status

Note: MVP does not call LLMs yet. It establishes the contract and
streaming/status plumbing. Integration with execution-mode personas
will be layered on after wiring is validated.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from services.ac_test_generator import generate_test_stubs
import re
import csv


SPRINT_DIR = Path("static/appdocs/sprints")
SPRINT_DIR.mkdir(parents=True, exist_ok=True)
BACKLOG_CSV_PATH = Path("static/appdocs/backlog/Backlog.csv")
VISION_DIR = Path("static/appdocs/visions")


@dataclass
class OrchestratorConfig:
    sprint_id: str


class SprintOrchestrator:
    def __init__(self, config: OrchestratorConfig):
        self.sprint_id = config.sprint_id
        self.plan_path = SPRINT_DIR / f"{self.sprint_id}.json"
        self.log_path = SPRINT_DIR / f"execution_log_{self.sprint_id}.jsonl"

    async def run(self) -> None:
        plan = self._load_plan()
        # Mark executing at start
        plan["status"] = "executing"
        self._save_plan(plan)

        await self._log_event("sprint_started", {"sprint_id": self.sprint_id})

        stories: List[str] = plan.get("stories", [])
        # Sequentially iterate stories (MVP)
        # Resolve project name once for artifact paths
        project_name = self._resolve_project_name()

        for story_id in stories:
            await self._log_event("story_started", {"story_id": story_id})
            now = datetime.utcnow().isoformat()
            self._append_story_artifact(project_name, story_id, f"{now} STARTED")
            await self._update_backlog(story_id, {
                "Sprint_ID": self.sprint_id,
                "Execution_Status": "in_progress",
                "Execution_Started_At": now,
                "Last_Event": "story_started",
                "Last_Updated": now,
            })
            # Generate AC→Tests stubs (MVP) and log
            try:
                tests = generate_test_stubs(story_id)
                await self._log_event("tests_generated", {"story_id": story_id, "tests": tests})
            except Exception:
                await self._log_event("tests_generated", {"story_id": story_id, "tests": []})

            # Simulated persona-phase steps (sequential MVP)
            await self._log_event("mike_breakdown", {"story_id": story_id, "summary": "Spec prepared"})
            now = datetime.utcnow().isoformat()
            self._append_story_artifact(project_name, story_id, f"{now} Mike: spec prepared")
            await self._update_backlog(story_id, {
                "Last_Event": "mike_breakdown",
                "Last_Updated": now,
            })
            await asyncio.sleep(0.05)
            await self._log_event("alex_implemented", {"story_id": story_id, "summary": "Changes applied"})
            now = datetime.utcnow().isoformat()
            self._append_story_artifact(project_name, story_id, f"{now} Alex: changes applied")
            await self._update_backlog(story_id, {
                "Last_Event": "alex_implemented",
                "Last_Updated": now,
            })
            await asyncio.sleep(0.05)
            # Use generated tests count if available
            passed = len(tests) if isinstance(tests, list) else 0
            await self._log_event("jordan_tested", {"story_id": story_id, "passed": passed, "failed": 0})
            now = datetime.utcnow().isoformat()
            self._append_story_artifact(project_name, story_id, f"{now} Jordan: tests passed={passed} failed=0")
            await self._update_backlog(story_id, {
                "Last_Event": "jordan_tested",
                "Last_Updated": now,
            })
            # Placeholder for breakdown/implementation/testing phases
            # Keep minimal delay to make streaming observable in UI
            await asyncio.sleep(0.05)
            await self._log_event("story_completed", {"story_id": story_id})
            now = datetime.utcnow().isoformat()
            self._append_story_artifact(project_name, story_id, f"{now} COMPLETED")
            await self._update_backlog(story_id, {
                "Execution_Status": "done",
                "Execution_Completed_At": now,
                "Last_Event": "story_completed",
                "Last_Updated": now,
            })

        # Build simple summary
        summary = {
            "stories_completed": len(stories),
            "stories_failed": 0,
            "tasks_completed": 0,
            "tests_passed": 0,
            "tests_failed": 0,
        }

        await self._log_event("sprint_completed", {"summary": summary})

        # Update plan to completed
        plan["status"] = "completed"
        plan["completed_at"] = datetime.utcnow().isoformat()
        self._save_plan(plan)

    def _load_plan(self) -> Dict:
        if not self.plan_path.exists():
            raise FileNotFoundError(f"Sprint plan not found: {self.plan_path}")
        with open(self.plan_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_plan(self, plan: Dict) -> None:
        # Ensure parent exists
        self.plan_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.plan_path, "w", encoding="utf-8") as f:
            json.dump(plan, f, indent=2)

    async def _log_event(self, event_type: str, data: Dict) -> None:
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "data": data,
        }
        # Ensure parent exists
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")

    @staticmethod
    def tail_events(log_path: Path, last_n: int = 50) -> List[Dict]:
        """Read last N events from a JSONL log file."""
        if not log_path.exists():
            return []
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()[-last_n:]
            return [json.loads(line) for line in lines if line.strip()]
        except Exception:
            return []

    @staticmethod
    async def stream_events(log_path: Path):
        """Async generator yielding SSE lines for new events in log file."""
        # Simple polling tail (MVP)
        position = 0
        while True:
            try:
                if log_path.exists():
                    with open(log_path, "r", encoding="utf-8") as f:
                        f.seek(position)
                        for line in f:
                            if not line.strip():
                                continue
                            yield f"event: update\n"
                            yield f"data: {line.strip()}\n\n"
                        position = f.tell()
                # Heartbeat
                yield "event: heartbeat\ndata: {}\n\n"
            except Exception:
                # On error, send a heartbeat to keep connection
                yield "event: heartbeat\ndata: {}\n\n"
            await asyncio.sleep(0.5)

    async def _update_backlog(self, story_id: str, updates: Dict[str, str]) -> None:
        try:
            if not story_id.startswith("US-"):
                return
            if not BACKLOG_CSV_PATH.exists():
                await self._log_event("backlog_update_skipped", {"story_id": story_id, "reason": "missing_csv"})
                return
            with open(BACKLOG_CSV_PATH, "r", newline='', encoding="utf-8") as f:
                reader = csv.DictReader(f)
                headers = reader.fieldnames or []
                required = [
                    "Story_ID", "Sprint_ID", "Execution_Status",
                    "Execution_Started_At", "Execution_Completed_At",
                    "Last_Event", "Last_Updated"
                ]
                if any(col not in headers for col in required):
                    await self._log_event("backlog_update_skipped", {"story_id": story_id, "reason": "header_missing"})
                    return
                rows = list(reader)
            found = False
            for r in rows:
                if r.get("Story_ID") == story_id:
                    for k, v in updates.items():
                        if k in headers:
                            r[k] = v
                    found = True
                    break
            if not found:
                await self._log_event("backlog_update_skipped", {"story_id": story_id, "reason": "story_not_found"})
                return
            with open(BACKLOG_CSV_PATH, "w", newline='', encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                writer.writerows(rows)
            await self._log_event("backlog_updated", {"story_id": story_id, "updated_fields": list(updates.keys())})
        except Exception as e:
            await self._log_event("backlog_update_skipped", {"story_id": story_id, "reason": f"error:{str(e)}"})

    def _resolve_project_name(self) -> str:
        """Infer project name from latest vision title; fallback to default.
        Produces a safe folder name.
        """
        try:
            latest_file = None
            latest_mtime = -1
            if VISION_DIR.exists():
                for jf in VISION_DIR.glob("*.json"):
                    try:
                        mtime = jf.stat().st_mtime
                        if mtime > latest_mtime:
                            latest_mtime = mtime
                            latest_file = jf
                    except Exception:
                        continue
            title = None
            if latest_file:
                try:
                    with open(latest_file, "r", encoding="utf-8") as f:
                        doc = json.load(f)
                        title = doc.get("title") or doc.get("id")
                except Exception:
                    title = None
            raw = title or "default_project"
            # Sanitize: allow alphanum, dash, underscore. Replace spaces with underscore.
            raw = str(raw).strip().replace(" ", "_")
            safe = re.sub(r"[^A-Za-z0-9_-]", "", raw)
            return safe[:50] or "default_project"
        except Exception:
            return "default_project"

    def _append_story_artifact(self, project_name: str, story_id: str, line: str) -> None:
        """Append a single line to the per-story artifact file."""
        try:
            base = Path("execution-sandbox/client-projects") / project_name / "stories"
            base.mkdir(parents=True, exist_ok=True)
            file_path = base / f"{story_id}.txt"
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(line.rstrip("\n") + "\n")
        except Exception:
            # Artifacts are best-effort; do not crash orchestrator
            pass
