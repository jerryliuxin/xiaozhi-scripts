#!/usr/bin/env python3
"""
Loop Engineering Framework v1.0
================================
A phased execution framework with self-check gates and quality reports.

Usage:
    from loop_engine import LoopEngine, Phase, CheckGate
    
    # Define phases
    phases = [
        Phase(
            name="Design",
            description="Define requirements and architecture",
            check_gates=[
                CheckGate(
                    name="Requirements Complete",
                    check_fn=lambda ctx: all(k in ctx for k in ["requirements", "architecture"]),
                    fail_action="retry"  # retry | abort | skip_to_report
                ),
            ]
        ),
        Phase(
            name="Implementation",
            description="Write the actual code",
            check_gates=[...],
        ),
    ]
    
    # Run the loop
    engine = LoopEngine(task_name="My Project")
    result = engine.run(phases, context={"initial_data": ...})
    
    # Print quality report
    print(result.quality_report())
"""

import json
import time
import copy
from datetime import datetime
from dataclasses import dataclass, field
from typing import Callable, Any, Optional


@dataclass
class CheckGate:
    """A gate that validates phase output before proceeding."""
    name: str                           # Human-readable gate name
    check_fn: Callable[[dict], bool]    # Validation function: context -> bool
    fail_action: str = "retry"          # "retry" | "abort" | "skip_to_report"
    max_retries: int = 3                # Max retry attempts before abort
    fix_hint: str = ""                  # Hint for fixing failed checks


@dataclass
class PhaseResult:
    """Result of executing a single phase."""
    name: str
    description: str
    status: str                         # "completed" | "failed" | "aborted" | "skipped"
    start_time: float
    end_time: float
    checks_passed: list[str] = field(default_factory=list)
    checks_failed: list[dict] = field(default_factory=list)
    fixes_applied: list[str] = field(default_factory=list)
    needs_human_review: list[str] = field(default_factory=list)
    artifacts: dict = field(default_factory=dict)
    error_message: str = ""


@dataclass
class QualityReport:
    """Final quality report summarizing the entire loop."""
    task_name: str
    overall_status: str                 # "passed" | "failed" | "partial"
    total_phases: int
    completed_phases: int
    failed_phases: int
    skipped_phases: int
    total_fixes_applied: list[str] = field(default_factory=list)
    pending_human_review: list[str] = field(default_factory=list)
    phase_summaries: list[str] = field(default_factory=list)
    execution_time: float = 0.0
    
    def format(self) -> str:
        """Format the quality report as a markdown string."""
        lines = []
        lines.append(f"# 🔍 质量检查报告 — {self.task_name}")
        lines.append(f"\n**执行时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**总体状态**: {'✅ 通过' if self.overall_status == 'passed' else '⚠️ 部分通过' if self.overall_status == 'partial' else '❌ 失败'}")
        lines.append(f"**阶段统计**: {self.completed_phases}/{self.total_phases} 完成, {self.failed_phases} 失败, {self.skipped_phases} 跳过\n")
        
        if self.total_fixes_applied:
            lines.append("## ✅ 已修正的问题")
            for fix in self.total_fixes_applied:
                lines.append(f"- {fix}")
            lines.append("")
        
        if self.pending_human_review:
            lines.append("## ⚠️ 亟待人工确认的地方")
            for item in self.pending_human_review:
                lines.append(f"- [ ] {item}")
            lines.append("")
        
        if self.phase_summaries:
            lines.append("## 📋 各阶段详情")
            for summary in self.phase_summaries:
                lines.append(f"\n{summary}")
        
        lines.append(f"\n---\n*Loop Engineering Framework v1.0*")
        return "\n".join(lines)


class Phase:
    """A single phase in the loop."""
    
    def __init__(self, name: str, description: str, execute_fn: Callable[[dict], dict], check_gates: Optional[list[CheckGate]] = None):
        self.name = name
        self.description = description
        self.execute_fn = execute_fn
        self.check_gates = check_gates or []
    
    def execute(self, context: dict) -> dict:
        """Execute the phase's function."""
        return self.execute_fn(context)



class LoopEngine:
    """Main engine that orchestrates phased execution with self-check gates."""
    
    def __init__(self, task_name: str, max_phase_retries: int = 5):
        self.task_name = task_name
        self.max_phase_retries = max_phase_retries
        self.results: list[PhaseResult] = []
        self.start_time = time.time()
    
    def run(self, phases: list[Phase], initial_context: Optional[dict] = None) -> QualityReport:
        """Execute all phases with self-check gates."""
        context = initial_context or {}
        all_fixes = []
        all_pending = []
        phase_summaries = []
        
        for phase in phases:
            result = self._execute_phase(phase, context)
            self.results.append(result)
            
            # Collect fixes and pending items
            all_fixes.extend(result.fixes_applied)
            all_pending.extend(result.needs_human_review)
            
            # Build phase summary
            summary = self._build_phase_summary(result)
            phase_summaries.append(summary)
            
            # Update context with artifacts
            context.update(result.artifacts)
            
            # If aborted, stop execution
            if result.status == "aborted":
                break
        
        elapsed = time.time() - self.start_time
        
        # Determine overall status
        completed = sum(1 for r in self.results if r.status == "completed")
        failed = sum(1 for r in self.results if r.status == "failed")
        skipped = sum(1 for r in self.results if r.status == "skipped")
        
        if failed > 0:
            overall = "failed"
        elif skipped > 0:
            overall = "partial"
        elif completed == len(phases):
            overall = "passed"
        else:
            overall = "partial"
        
        return QualityReport(
            task_name=self.task_name,
            overall_status=overall,
            total_phases=len(phases),
            completed_phases=completed,
            failed_phases=failed,
            skipped_phases=skipped,
            total_fixes_applied=all_fixes,
            pending_human_review=all_pending,
            phase_summaries=phase_summaries,
            execution_time=elapsed,
        )
    
    def _execute_phase(self, phase: Phase, context: dict) -> PhaseResult:
        """Execute a single phase with retry and self-check."""
        result = PhaseResult(
            name=phase.name,
            description=phase.description,
            status="completed",
            start_time=time.time(),
            end_time=0,
        )
        
        retries = 0
        while retries <= self.max_phase_retries:
            # Execute phase function
            try:
                artifacts = phase.execute(context)
                result.artifacts = artifacts or {}
            except Exception as e:
                result.status = "failed"
                result.error_message = str(e)
                retries += 1
                continue
            
            # Run self-checks
            checks_passed = []
            checks_failed = []
            fixes_applied = []
            needs_review = []
            retry_needed = False
            
            for gate in phase.check_gates:
                try:
                    passed = gate.check_fn(result.artifacts)
                    if passed:
                        checks_passed.append(gate.name)
                    else:
                        checks_failed.append({
                            "gate": gate.name,
                            "hint": gate.fix_hint,
                            "action": gate.fail_action,
                        })
                        
                        if gate.fail_action == "retry" and retries < self.max_phase_retries:
                            fixes_applied.append(f"⚠️ [{gate.name}] 未通过，正在重试 ({retries + 1}/{self.max_phase_retries})")
                            retries += 1
                            retry_needed = True
                            break  # Re-execute phase
                        elif gate.fail_action == "abort":
                            result.status = "failed"
                            result.error_message = f"Check gate '{gate.name}' failed with abort action"
                            break
                        elif gate.fail_action == "skip_to_report":
                            needs_review.append(f"⚠️ [{gate.name}] 未通过，标记为待人工确认")
                            checks_passed.append(gate.name)  # Mark as handled
                            
                except Exception as e:
                    checks_failed.append({
                        "gate": gate.name,
                        "error": str(e),
                        "action": gate.fail_action,
                    })
                    retries += 1
                    retry_needed = True
                    break
            
            if result.status == "failed":
                break
            
            # Only exit retry loop if no retry was triggered
            if not retry_needed:
                result.checks_passed = checks_passed
                result.checks_failed = checks_failed
                result.fixes_applied = fixes_applied
                result.needs_human_review = needs_review
                result.end_time = time.time()
                break  # Exit retry loop if all checks passed
            else:
                # Store partial results for next retry attempt
                result.checks_failed = checks_failed
                result.fixes_applied = fixes_applied
        
        return result
    
    def _build_phase_summary(self, result: PhaseResult) -> str:
        """Build a markdown summary for a phase."""
        status_icon = {"completed": "✅", "failed": "❌", "aborted": "🛑", "skipped": "⏭️"}
        icon = status_icon.get(result.status, "?")
        
        lines = []
        lines.append(f"### {icon} 阶段: {result.name}")
        lines.append(f"**状态**: {result.status} | **耗时**: {result.end_time - result.start_time:.1f}s")
        
        if result.checks_passed:
            lines.append(f"**自检通过**: {', '.join(result.checks_passed)}")
        if result.checks_failed:
            for cf in result.checks_failed:
                lines.append(f"  - ❌ {cf['gate']}: {cf.get('hint', cf.get('error', ''))}")
        if result.fixes_applied:
            for fix in result.fixes_applied:
                lines.append(f"  - 🔧 {fix}")
        if result.needs_human_review:
            for item in result.needs_human_review:
                lines.append(f"  - 👤 {item}")
        if result.error_message:
            lines.append(f"**错误**: {result.error_message}")
        
        return "\n".join(lines)


# Convenience class for defining phases
# Export public API
__all__ = ["LoopEngine", "Phase", "CheckGate", "QualityReport", "PhaseResult"]
