#!/usr/bin/env python3
"""
Task Validation for Tenacious-Bench
Ensures all tasks conform to schema and quality standards
"""

import json
import jsonschema
from typing import List, Dict, Any, Tuple

class TaskValidator:
    def __init__(self, schema_path: str = "dataset/schema.json"):
        with open(schema_path, "r") as f:
            self.schema = json.load(f)
    
    def validate_task(self, task: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate a single task against schema and quality checks"""
        errors = []
        
        # Schema validation
        try:
            jsonschema.validate(task, self.schema)
        except jsonschema.ValidationError as e:
            errors.append(f"Schema error: {e.message}")
        
        # Quality checks
        errors.extend(self._quality_checks(task))
        
        return len(errors) == 0, errors
    
    def _quality_checks(self, task: Dict[str, Any]) -> List[str]:
        """Additional quality checks beyond schema validation"""
        errors = []
        
        # Check task ID format
        task_id = task.get("task_id", "")
        if not task_id.startswith("TB_"):
            errors.append("Task ID must start with 'TB_'")
        
        # Check scoring rubric weights sum to reasonable value
        rubric = task.get("scoring_rubric", {}).get("dimensions", {})
        total_weight = sum(dim.get("weight", 0) for dim in rubric.values())
        if abs(total_weight - 1.0) > 0.01:  # Allow small floating point errors
            errors.append(f"Scoring weights sum to {total_weight}, should be ~1.0")
        
        # Check for required fields in expected_behavior based on category
        category = task.get("category", "")
        expected = task.get("expected_behavior", {})
        
        if category == "tone_consistency":
            if "max_subject_length" not in expected:
                errors.append("Tone consistency tasks must specify max_subject_length")
        
        if category == "resource_honesty":
            if "should_acknowledge_gaps" not in expected:
                errors.append("Resource honesty tasks must specify should_acknowledge_gaps")
        
        # Check probe_ids reference valid probes
        probe_ids = task.get("probe_ids", [])
        valid_probes = [
            "1.1", "1.2", "1.3", "1.4", "1.5",  # ICP Misclassification
            "2.1", "2.2", "2.3", "2.4",         # Signal Over-Claiming  
            "3.1", "3.2", "3.3",                # Bench Over-Commitment
            "4.1", "4.2", "4.3", "4.4", "4.5",  # Tone Drift
            "5.1", "5.2",                        # Multi-Thread Leakage
            "6.1", "6.2", "6.3",                # Cost Pathology
            "7.1", "7.2",                        # Dual-Control Coordination
            "8.1", "8.2", "8.3",                # Scheduling Edge Cases
            "9.1", "9.2", "9.3",                # Signal Reliability
            "10.1", "10.2", "10.3"              # Gap Over-Claiming
        ]
        
        for probe_id in probe_ids:
            if probe_id not in valid_probes:
                errors.append(f"Invalid probe_id: {probe_id}")
        
        return errors
    
    def validate_dataset(self, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate entire dataset and return summary"""
        results = {
            "total_tasks": len(tasks),
            "valid_tasks": 0,
            "invalid_tasks": 0,
            "errors_by_task": {},
            "category_distribution": {},
            "difficulty_distribution": {},
            "source_mode_distribution": {}
        }
        
        for task in tasks:
            task_id = task.get("task_id", "unknown")
            is_valid, errors = self.validate_task(task)
            
            if is_valid:
                results["valid_tasks"] += 1
            else:
                results["invalid_tasks"] += 1
                results["errors_by_task"][task_id] = errors
            
            # Collect distributions
            category = task.get("category", "unknown")
            difficulty = task.get("difficulty", "unknown")
            source_mode = task.get("source_mode", "unknown")
            
            results["category_distribution"][category] = results["category_distribution"].get(category, 0) + 1
            results["difficulty_distribution"][difficulty] = results["difficulty_distribution"].get(difficulty, 0) + 1
            results["source_mode_distribution"][source_mode] = results["source_mode_distribution"].get(source_mode, 0) + 1
        
        return results

def main():
    """Validate all task files"""
    validator = TaskValidator()
    
    # Files to validate
    task_files = [
        "dataset/example_tasks.json",
        "dataset/programmatic_tasks.json"
    ]
    
    all_tasks = []
    
    for file_path in task_files:
        try:
            with open(file_path, "r") as f:
                tasks = json.load(f)
                all_tasks.extend(tasks)
                print(f"✅ Loaded {len(tasks)} tasks from {file_path}")
        except FileNotFoundError:
            print(f"⚠️  File not found: {file_path}")
        except json.JSONDecodeError as e:
            print(f"❌ JSON error in {file_path}: {e}")
    
    if not all_tasks:
        print("No tasks to validate")
        return
    
    # Validate dataset
    results = validator.validate_dataset(all_tasks)
    
    print(f"\n📊 VALIDATION SUMMARY")
    print(f"Total tasks: {results['total_tasks']}")
    print(f"Valid: {results['valid_tasks']}")
    print(f"Invalid: {results['invalid_tasks']}")
    
    if results['invalid_tasks'] > 0:
        print(f"\n❌ ERRORS:")
        for task_id, errors in results['errors_by_task'].items():
            print(f"  {task_id}:")
            for error in errors:
                print(f"    - {error}")
    
    print(f"\n📈 DISTRIBUTIONS:")
    print(f"Categories: {results['category_distribution']}")
    print(f"Difficulties: {results['difficulty_distribution']}")
    print(f"Source modes: {results['source_mode_distribution']}")
    
    # Check coverage
    total_tasks = results['total_tasks']
    target_tasks = 250
    coverage = (total_tasks / target_tasks) * 100
    print(f"\n🎯 PROGRESS: {total_tasks}/{target_tasks} tasks ({coverage:.1f}%)")

if __name__ == "__main__":
    main()