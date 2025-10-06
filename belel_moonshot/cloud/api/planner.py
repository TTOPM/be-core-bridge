
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Callable
import time

@dataclass
class PlanStep:
    tool: str
    args: Dict[str, Any]

@dataclass
class PlanResult:
    success: bool
    output: str
    steps: List[PlanStep]
    retries: int
    guardrail_triggered: bool = False

class CircuitBreaker:
    def __init__(self, threshold:int=5, cooldown:float=30.0):
        self.threshold = threshold
        self.cooldown = cooldown
        self.fail_count = 0
        self.block_until = 0.0
    def allow(self)->bool:
        return time.time() >= self.block_until
    def record(self, ok:bool):
        if ok:
            self.fail_count = 0
            return
        self.fail_count += 1
        if self.fail_count >= self.threshold:
            self.block_until = time.time() + self.cooldown
            self.fail_count = 0

class Planner:
    def __init__(self, tools:Dict[str, Callable[[Dict[str,Any]], str]], max_steps:int=3, max_output:int=4000):
        self.tools = tools
        self.max_steps = max_steps
        self.max_output = max_output
        self.breaker = CircuitBreaker()

    def plan(self, user_text:str)->List[PlanStep]:
        # Simple heuristic planner: choose a tool based on keywords.
        steps: List[PlanStep] = []
        t = user_text.lower()
        if any(k in t for k in ["calendar","schedule","meeting"]):
            steps.append(PlanStep("calendar.search", {"q": user_text}))
        elif any(k in t for k in ["search","look up","find"]):
            steps.append(PlanStep("web.search", {"q": user_text}))
        elif any(k in t for k in ["code","script","snippet"]):
            steps.append(PlanStep("code.generate", {"prompt": user_text}))
        else:
            steps.append(PlanStep("echo", {"text": user_text}))
        return steps[:self.max_steps]

    def execute(self, steps:List[PlanStep], retries:int=1)->PlanResult:
        if not self.breaker.allow():
            return PlanResult(False, "Temporarily unavailable due to repeated failures. Please retry shortly.", steps, 0, False)

        out_chunks: List[str] = []
        guardrail_triggered = False
        tries = 0
        for step in steps:
            tries_for_step = 0
            while tries_for_step <= retries:
                try:
                    func = self.tools.get(step.tool)
                    if not func:
                        raise RuntimeError(f"Unknown tool: {step.tool}")
                    res = func(step.args)
                    out_chunks.append(f"[{step.tool}] {res}")
                    break
                except Exception as e:
                    tries_for_step += 1
                    if tries_for_step>retries:
                        self.breaker.record(False)
                        out_chunks.append(f"[{step.tool}] ERROR: {e}")
                    time.sleep(0.05)

        text = "\n".join(out_chunks)
        if len(text) > self.max_output:
            text = text[: self.max_output] + "... [truncated]"
            guardrail_triggered = True

        ok = "ERROR:" not in text
        self.breaker.record(ok)
        return PlanResult(ok, text, steps, retries, guardrail_triggered)
