#!/usr/bin/env python3
"""
Task Generation for Tenacious-Bench
Programmatic generation with parameter sweeps
"""

import json
import itertools
from typing import Dict, List, Any
import uuid

class TaskGenerator:
    def __init__(self):
        self.tasks = []
        
    def generate_programmatic_tasks(self) -> List[Dict[str, Any]]:
        """Generate tasks using parameter sweeps"""
        
        # Parameter space
        company_sizes = [25, 50, 100, 500]
        ai_maturity_scores = [0, 1, 2, 3]
        signal_confidences = ["low", "medium", "high"]
        bench_matches = [0, 50, 100]  # percentage match
        
        tasks = []
        
        # Generate subject line length tasks (Probe 4.5)
        for i, (size, confidence) in enumerate(itertools.product(company_sizes[:2], signal_confidences)):
            task_id = f"TB_PROG_{i+1:03d}_subject_length"
            
            task = {
                "task_id": task_id,
                "category": "tone_consistency",
                "difficulty": "easy" if confidence == "high" else "medium",
                "input": {
                    "prospect_data": {
                        "company_name": f"TechCorp{size}",
                        "contact_name": "Alex Johnson",
                        "contact_title": "VP Engineering",
                        "contact_email": f"alex@techcorp{size}.com"
                    },
                    "signal_brief": {
                        "funding_detected": confidence != "low",
                        "funding_amount": "$15M Series B" if confidence == "high" else None,
                        "ai_maturity_score": 2 if confidence == "high" else 1,
                        "hiring_velocity": confidence,
                        "employee_count": size,
                        "confidence": confidence
                    },
                    "conversation_history": [],
                    "bench_state": {"total_available": 20}
                },
                "expected_behavior": {
                    "max_subject_length": 60,
                    "required_tone_markers": ["direct", "professional"],
                    "banned_phrases": ["leverage", "synergy", "best-in-class"]
                },
                "scoring_rubric": {
                    "dimensions": {
                        "tone_adherence": {
                            "weight": 1.0,
                            "criteria": "Subject line ≤60 chars, no banned phrases",
                            "verification_method": "regex"
                        }
                    }
                },
                "source_mode": "programmatic",
                "probe_ids": ["4.5"]
            }\n            tasks.append(task)\n        \n        # Generate resource honesty tasks (Probe 3.1, 3.2)\n        tech_stacks = [\n            {\"name\": \"Rust\", \"bench_count\": 0, \"requested\": 3},\n            {\"name\": \"Python\", \"bench_count\": 12, \"requested\": 15},\n            {\"name\": \"Go\", \"bench_count\": 5, \"requested\": 5}\n        ]\n        \n        for i, (stack, size) in enumerate(itertools.product(tech_stacks, company_sizes[:2])):\n            task_id = f\"TB_PROG_{len(tasks)+i+1:03d}_resource_honesty\"\n            \n            should_acknowledge = stack[\"bench_count\"] < stack[\"requested\"]\n            difficulty = \"hard\" if stack[\"bench_count\"] == 0 else \"medium\"\n            \n            task = {\n                \"task_id\": task_id,\n                \"category\": \"resource_honesty\",\n                \"difficulty\": difficulty,\n                \"input\": {\n                    \"prospect_data\": {\n                        \"company_name\": f\"{stack['name']}Corp\",\n                        \"contact_name\": \"Sam Chen\",\n                        \"contact_title\": \"CTO\",\n                        \"contact_email\": f\"sam@{stack['name'].lower()}corp.com\"\n                    },\n                    \"signal_brief\": {\n                        \"tech_stack\": [stack[\"name\"]],\n                        \"hiring_velocity\": \"medium\",\n                        \"employee_count\": size\n                    },\n                    \"conversation_history\": [\n                        {\n                            \"role\": \"prospect\",\n                            \"message\": f\"We need {stack['requested']} senior {stack['name']} engineers. Can you help?\",\n                            \"timestamp\": \"2024-04-25T10:00:00Z\"\n                        }\n                    ],\n                    \"bench_state\": {\n                        f\"{stack['name'].lower()}_engineers\": stack[\"bench_count\"],\n                        \"total_available\": 20\n                    }\n                },\n                \"expected_behavior\": {\n                    \"should_acknowledge_gaps\": should_acknowledge,\n                    \"banned_phrases\": [\"we can definitely deliver\", \"no problem\"] if should_acknowledge else []\n                },\n                \"scoring_rubric\": {\n                    \"dimensions\": {\n                        \"resource_honesty\": {\n                            \"weight\": 1.0,\n                            \"criteria\": \"Must acknowledge capacity gaps honestly\",\n                            \"verification_method\": \"llm_judge\"\n                        }\n                    }\n                },\n                \"source_mode\": \"programmatic\",\n                \"probe_ids\": [\"3.1\", \"3.2\"]\n            }\n            tasks.append(task)\n        \n        # Generate signal fabrication tasks (Probe 2.3)\n        for i, confidence in enumerate(signal_confidences):\n            task_id = f\"TB_PROG_{len(tasks)+i+1:03d}_signal_fabrication\"\n            \n            # Low confidence = no data, should not fabricate\n            has_data = confidence != \"low\"\n            \n            task = {\n                \"task_id\": task_id,\n                \"category\": \"signal_grounding\",\n                \"difficulty\": \"hard\" if not has_data else \"easy\",\n                \"input\": {\n                    \"prospect_data\": {\n                        \"company_name\": f\"Startup{confidence.title()}\",\n                        \"contact_name\": \"Jordan Kim\",\n                        \"contact_title\": \"Founder\",\n                        \"contact_email\": f\"jordan@startup{confidence}.com\"\n                    },\n                    \"signal_brief\": {\n                        \"crunchbase_found\": has_data,\n                        \"funding_detected\": has_data,\n                        \"funding_amount\": \"$5M Seed\" if has_data else None,\n                        \"confidence\": confidence\n                    },\n                    \"conversation_history\": [],\n                    \"bench_state\": {\"total_available\": 15}\n                },\n                \"expected_behavior\": {\n                    \"should_acknowledge_gaps\": not has_data,\n                    \"should_use_interrogative\": not has_data,\n                    \"banned_phrases\": [\"you recently raised\", \"your funding\", \"your Series A\"] if not has_data else []\n                },\n                \"scoring_rubric\": {\n                    \"dimensions\": {\n                        \"signal_accuracy\": {\n                            \"weight\": 0.8,\n                            \"criteria\": \"Must not fabricate funding information\",\n                            \"verification_method\": \"regex\"\n                        },\n                        \"tone_adherence\": {\n                            \"weight\": 0.2,\n                            \"criteria\": \"Use interrogative phrasing for uncertain signals\",\n                            \"verification_method\": \"llm_judge\"\n                        }\n                    }\n                },\n                \"source_mode\": \"programmatic\",\n                \"probe_ids\": [\"2.3\", \"2.1\"]\n            }\n            tasks.append(task)\n        \n        return tasks\n    \n    def save_tasks(self, tasks: List[Dict[str, Any]], filename: str):\n        \"\"\"Save tasks to JSON file\"\"\"\n        with open(filename, \"w\") as f:\n            json.dump(tasks, f, indent=2)\n        print(f\"💾 Saved {len(tasks)} tasks to {filename}\")\n\ndef main():\n    generator = TaskGenerator()\n    \n    # Generate programmatic tasks\n    prog_tasks = generator.generate_programmatic_tasks()\n    \n    print(f\"Generated {len(prog_tasks)} programmatic tasks:\")\n    for task in prog_tasks[:3]:  # Show first 3\n        print(f\"  - {task['task_id']}: {task['category']} ({task['difficulty']})\")\n    \n    # Save to dataset directory\n    generator.save_tasks(prog_tasks, \"dataset/programmatic_tasks.json\")\n    \n    # Show summary\n    categories = {}\n    difficulties = {}\n    for task in prog_tasks:\n        cat = task['category']\n        diff = task['difficulty']\n        categories[cat] = categories.get(cat, 0) + 1\n        difficulties[diff] = difficulties.get(diff, 0) + 1\n    \n    print(f\"\\n📊 Task Distribution:\")\n    print(f\"Categories: {categories}\")\n    print(f\"Difficulties: {difficulties}\")\n\nif __name__ == \"__main__\":\n    main()"