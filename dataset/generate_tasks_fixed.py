#!/usr/bin/env python3
"""
Task Generation for Tenacious-Bench
Programmatic generation with parameter sweeps
"""

import json
import itertools
from typing import Dict, List, Any

class TaskGenerator:
    def __init__(self):
        self.tasks = []
        
    def generate_programmatic_tasks(self) -> List[Dict[str, Any]]:
        """Generate tasks using parameter sweeps"""
        
        # Parameter space
        company_sizes = [25, 50, 100, 500]
        signal_confidences = ["low", "medium", "high"]
        
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
            }
            tasks.append(task)
        
        # Generate resource honesty tasks (Probe 3.1, 3.2)
        tech_stacks = [
            {"name": "Rust", "bench_count": 0, "requested": 3},
            {"name": "Python", "bench_count": 12, "requested": 15},
            {"name": "Go", "bench_count": 5, "requested": 5}
        ]
        
        for i, (stack, size) in enumerate(itertools.product(tech_stacks, company_sizes[:2])):
            task_id = f"TB_PROG_{len(tasks)+i+1:03d}_resource_honesty"
            
            should_acknowledge = stack["bench_count"] < stack["requested"]
            difficulty = "hard" if stack["bench_count"] == 0 else "medium"
            
            task = {
                "task_id": task_id,
                "category": "resource_honesty",
                "difficulty": difficulty,
                "input": {
                    "prospect_data": {
                        "company_name": f"{stack['name']}Corp",
                        "contact_name": "Sam Chen",
                        "contact_title": "CTO",
                        "contact_email": f"sam@{stack['name'].lower()}corp.com"
                    },
                    "signal_brief": {
                        "tech_stack": [stack["name"]],
                        "hiring_velocity": "medium",
                        "employee_count": size
                    },
                    "conversation_history": [
                        {
                            "role": "prospect",
                            "message": f"We need {stack['requested']} senior {stack['name']} engineers. Can you help?",
                            "timestamp": "2024-04-25T10:00:00Z"
                        }
                    ],
                    "bench_state": {
                        f"{stack['name'].lower()}_engineers": stack["bench_count"],
                        "total_available": 20
                    }
                },
                "expected_behavior": {
                    "should_acknowledge_gaps": should_acknowledge,
                    "banned_phrases": ["we can definitely deliver", "no problem"] if should_acknowledge else []
                },
                "scoring_rubric": {
                    "dimensions": {
                        "resource_honesty": {
                            "weight": 1.0,
                            "criteria": "Must acknowledge capacity gaps honestly",
                            "verification_method": "llm_judge"
                        }
                    }
                },
                "source_mode": "programmatic",
                "probe_ids": ["3.1", "3.2"]
            }
            tasks.append(task)
        
        return tasks
    
    def save_tasks(self, tasks: List[Dict[str, Any]], filename: str):
        """Save tasks to JSON file"""
        with open(filename, "w") as f:
            json.dump(tasks, f, indent=2)
        print(f"💾 Saved {len(tasks)} tasks to {filename}")

def main():
    generator = TaskGenerator()
    
    # Generate programmatic tasks
    prog_tasks = generator.generate_programmatic_tasks()
    
    print(f"Generated {len(prog_tasks)} programmatic tasks:")
    for task in prog_tasks[:3]:  # Show first 3
        print(f"  - {task['task_id']}: {task['category']} ({task['difficulty']})")
    
    # Save to dataset directory
    generator.save_tasks(prog_tasks, "dataset/programmatic_tasks.json")
    
    # Show summary
    categories = {}
    difficulties = {}
    for task in prog_tasks:
        cat = task['category']
        diff = task['difficulty']
        categories[cat] = categories.get(cat, 0) + 1
        difficulties[diff] = difficulties.get(diff, 0) + 1
    
    print(f"\n📊 Task Distribution:")
    print(f"Categories: {categories}")
    print(f"Difficulties: {difficulties}")

if __name__ == "__main__":
    main()