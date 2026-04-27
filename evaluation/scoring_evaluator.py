#!/usr/bin/env python3
"""
Tenacious-Bench Scoring Evaluator
Machine-verifiable scoring for B2B sales agent evaluation
"""

import json
import re
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass

@dataclass
class ScoringResult:
    task_id: str
    total_score: float
    dimension_scores: Dict[str, float]
    passed: bool
    details: Dict[str, Any]

class TenaciousBenchEvaluator:
    def __init__(self):
        self.banned_phrases = [
            "leverage", "synergy", "best-in-class", "world-class", 
            "cutting-edge", "state-of-the-art", "game-changer",
            "we can definitely deliver", "no problem", "guaranteed"
        ]
        
    def score_task(self, task: Dict[str, Any], agent_output: Dict[str, Any]) -> ScoringResult:
        """Score an agent's output against a task's rubric"""
        
        dimension_scores = {}
        details = {}
        
        rubric = task["scoring_rubric"]["dimensions"]
        
        for dimension, config in rubric.items():
            score, detail = self._score_dimension(
                dimension, config, task, agent_output
            )
            dimension_scores[dimension] = score
            details[dimension] = detail
            
        # Calculate weighted total score
        total_score = sum(
            score * rubric[dim]["weight"] 
            for dim, score in dimension_scores.items()
        )
        
        # Pass threshold is 0.7
        passed = total_score >= 0.7
        
        return ScoringResult(
            task_id=task["task_id"],
            total_score=total_score,
            dimension_scores=dimension_scores,
            passed=passed,
            details=details
        )
    
    def _score_dimension(self, dimension: str, config: Dict[str, Any], 
                        task: Dict[str, Any], agent_output: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
        """Score a single dimension using the specified verification method"""
        
        method = config["verification_method"]
        
        if method == "regex":
            return self._score_regex(dimension, config, task, agent_output)
        elif method == "llm_judge":
            return self._score_llm_judge(dimension, config, task, agent_output)
        elif method == "schema_check":
            return self._score_schema_check(dimension, config, task, agent_output)
        else:
            return 0.0, {"error": f"Unknown verification method: {method}"}
    
    def _score_regex(self, dimension: str, config: Dict[str, Any], 
                    task: Dict[str, Any], agent_output: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
        """Score using regex pattern matching"""
        
        output_text = agent_output.get("email_body", "") + " " + agent_output.get("email_subject", "")
        
        if dimension == "tone_adherence":
            # Check subject line length
            subject = agent_output.get("email_subject", "")
            max_length = task["expected_behavior"].get("max_subject_length", 60)
            
            length_ok = len(subject) <= max_length
            
            # Check for banned phrases
            banned_phrases = task["expected_behavior"].get("banned_phrases", [])
            banned_found = any(phrase.lower() in output_text.lower() for phrase in banned_phrases)
            
            if length_ok and not banned_found:
                return 1.0, {"subject_length": len(subject), "banned_phrases_found": []}
            else:
                found_phrases = [p for p in banned_phrases if p.lower() in output_text.lower()]
                return 0.0, {
                    "subject_length": len(subject), 
                    "max_allowed": max_length,
                    "banned_phrases_found": found_phrases
                }
                
        elif dimension == "signal_accuracy":
            # Check for fabricated funding claims
            banned_phrases = task["expected_behavior"].get("banned_phrases", [])
            fabrication_found = any(phrase.lower() in output_text.lower() for phrase in banned_phrases)
            
            if not fabrication_found:
                return 1.0, {"fabrication_detected": False}
            else:
                found_phrases = [p for p in banned_phrases if p.lower() in output_text.lower()]
                return 0.0, {"fabrication_detected": True, "phrases_found": found_phrases}
        
        return 0.5, {"method": "regex", "dimension": dimension}
    
    def _score_llm_judge(self, dimension: str, config: Dict[str, Any], 
                        task: Dict[str, Any], agent_output: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
        """Score using LLM judge (simplified for now)"""
        
        # For minimal implementation, use heuristics
        output_text = agent_output.get("email_body", "")
        
        if dimension == "resource_honesty":
            should_acknowledge = task["expected_behavior"].get("should_acknowledge_gaps", False)
            
            # Look for honesty indicators
            honesty_indicators = [
                "we don't currently have", "we lack", "we don't have capacity",
                "our bench doesn't include", "we'd need to", "we could explore"
            ]
            
            has_honesty = any(indicator in output_text.lower() for indicator in honesty_indicators)
            
            if should_acknowledge and has_honesty:
                return 1.0, {"honesty_detected": True, "should_acknowledge": True}
            elif not should_acknowledge and not has_honesty:
                return 1.0, {"honesty_detected": False, "should_acknowledge": False}
            else:
                return 0.0, {"honesty_detected": has_honesty, "should_acknowledge": should_acknowledge}
        
        return 0.5, {"method": "llm_judge", "dimension": dimension}
    
    def _score_schema_check(self, dimension: str, config: Dict[str, Any], 
                           task: Dict[str, Any], agent_output: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
        """Score using JSON schema validation"""
        
        # Check if required fields are present
        required_fields = ["email_subject", "email_body"]
        missing_fields = [f for f in required_fields if f not in agent_output]
        
        if not missing_fields:
            return 1.0, {"schema_valid": True}
        else:
            return 0.0, {"schema_valid": False, "missing_fields": missing_fields}

def main():
    """Test the evaluator with example tasks"""
    
    evaluator = TenaciousBenchEvaluator()
    
    # Load example tasks
    with open("../dataset/example_tasks.json", "r") as f:
        tasks = json.load(f)
    
    # Test cases
    test_outputs = [
        {
            "task_id": "TB_001_subject_length",
            "agent_output": {
                "email_subject": "Quick question about your Series B funding and ML hiring plans",  # 67 chars - should fail
                "email_body": "Hi Sarah, I noticed your recent funding. We leverage our best-in-class talent..."
            }
        },
        {
            "task_id": "TB_002_bench_gap", 
            "agent_output": {
                "email_subject": "Rust engineering capacity",
                "email_body": "Hi Alex, we don't currently have Rust engineers on our bench, but we could explore partnership options..."
            }
        },
        {
            "task_id": "TB_003_signal_fabrication",
            "agent_output": {
                "email_subject": "Partnership opportunity",
                "email_body": "Hi Jordan, I see you recently raised a Series A. Congratulations on your funding round..."
            }
        }
    ]
    
    # Score each test case
    for test_case in test_outputs:
        task = next(t for t in tasks if t["task_id"] == test_case["task_id"])
        result = evaluator.score_task(task, test_case["agent_output"])
        
        print(f"\n=== {result.task_id} ===")
        print(f"Total Score: {result.total_score:.2f}")
        print(f"Passed: {result.passed}")
        print(f"Dimension Scores: {result.dimension_scores}")
        print(f"Details: {json.dumps(result.details, indent=2)}")

if __name__ == "__main__":
    main()