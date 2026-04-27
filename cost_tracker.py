#!/usr/bin/env python3
"""
Cost Tracking for Week 11 Tenacious-Bench
Budget: $10 total
"""

import json
import datetime
from typing import Dict, List
from dataclasses import dataclass, asdict

@dataclass
class CostEntry:
    timestamp: str
    bucket: str  # dataset_authoring, training, evaluation, reserve
    service: str  # openrouter, runpod, colab, etc.
    amount_usd: float
    purpose: str
    model_or_resource: str

class CostTracker:
    def __init__(self, budget_usd: float = 10.0):
        self.budget_usd = budget_usd
        self.entries: List[CostEntry] = []
        self.load_existing()
    
    def log_cost(self, bucket: str, service: str, amount_usd: float, 
                 purpose: str, model_or_resource: str):
        """Log a new cost entry"""
        entry = CostEntry(
            timestamp=datetime.datetime.utcnow().isoformat(),
            bucket=bucket,
            service=service,
            amount_usd=amount_usd,
            purpose=purpose,
            model_or_resource=model_or_resource
        )
        self.entries.append(entry)
        self.save()
        
        # Check budget
        total_spent = self.get_total_spent()
        remaining = self.budget_usd - total_spent
        
        print(f"💰 Cost logged: ${amount_usd:.4f} ({bucket})")
        print(f"📊 Total spent: ${total_spent:.4f} / ${self.budget_usd:.2f}")
        print(f"💳 Remaining: ${remaining:.4f}")
        
        if remaining < 0:
            print("⚠️  BUDGET EXCEEDED!")
        elif remaining < 1.0:
            print("⚠️  Less than $1 remaining")
    
    def get_total_spent(self) -> float:
        return sum(entry.amount_usd for entry in self.entries)
    
    def get_spending_by_bucket(self) -> Dict[str, float]:
        buckets = {}
        for entry in self.entries:
            buckets[entry.bucket] = buckets.get(entry.bucket, 0) + entry.amount_usd
        return buckets
    
    def save(self):
        """Save cost log to JSON file"""
        data = [asdict(entry) for entry in self.entries]
        with open("cost_log.json", "w") as f:
            json.dump(data, f, indent=2)
    
    def load_existing(self):
        """Load existing cost log if it exists"""
        try:
            with open("cost_log.json", "r") as f:
                data = json.load(f)
                self.entries = [CostEntry(**entry) for entry in data]
        except FileNotFoundError:
            self.entries = []
    
    def print_summary(self):
        """Print cost summary"""
        total = self.get_total_spent()
        by_bucket = self.get_spending_by_bucket()
        
        print(f"\n=== COST SUMMARY ===")
        print(f"Total Spent: ${total:.4f} / ${self.budget_usd:.2f}")
        print(f"Remaining: ${self.budget_usd - total:.4f}")
        print(f"\nBy Bucket:")
        for bucket, amount in by_bucket.items():
            print(f"  {bucket}: ${amount:.4f}")
        
        print(f"\nRecent Entries:")
        for entry in self.entries[-5:]:
            print(f"  {entry.timestamp[:19]} | {entry.bucket} | ${entry.amount_usd:.4f} | {entry.purpose}")

def main():
    """Example usage"""
    tracker = CostTracker()
    
    # Example cost entries
    tracker.log_cost(
        bucket="dataset_authoring",
        service="openrouter", 
        amount_usd=0.15,
        purpose="Multi-LLM synthesis for adversarial tasks",
        model_or_resource="qwen3-next-80b"
    )
    
    tracker.print_summary()

if __name__ == "__main__":
    main()