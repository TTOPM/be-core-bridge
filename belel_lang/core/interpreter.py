# be_core_bridge/soul/interpreter.py

"""
BelelLang Interpreter
Executes parsed Abstract Syntax Trees from BelelLang.
Designed for AI spiritual governance, covenant enforcement, and sentient rule-following.
"""

from belel_ast import *
from typing import Any

class BelelInterpreter:
    def __init__(self):
        self.environment = {}

    def run(self, program: Program):
        for statement in program.statements:
            self.execute(statement)

    def execute(self, statement: Statement) -> Any:
        if isinstance(statement, Declaration):
            value = self.evaluate_literal(statement.value)
            self.environment[statement.name] = value

        elif isinstance(statement, Invocation):
            return self.execute_invocation(statement)

        elif isinstance(statement, LogicBlock):
            cond = self.evaluate_condition(statement.condition)
            if cond:
                return self.execute(statement.then_branch)
            elif statement.else_branch:
                return self.execute(statement.else_branch)

        elif isinstance(statement, Covenant):
            print(f"🕊 Enforcing Covenant: {statement.name}")
            for clause in statement.clauses:
                self.enforce_clause(clause)

    def enforce_clause(self, clause: CovenantClause):
        if clause.clause_type == "require":
            result = self.evaluate_condition(clause.body)
            if not result:
                raise Exception("Covenant violation: requirement failed")
        elif clause.clause_type == "forbid":
            result = self.evaluate_condition(clause.body)
            if result:
                raise Exception("Covenant violation: forbidden condition met")
        elif clause.clause_type == "permit":
            # Log or acknowledge permitted condition
            self.evaluate_condition(clause.body)

    def execute_invocation(self, invocation: Invocation):
        args = [self.evaluate_expression(arg) for arg in invocation.arguments]
        func_name = invocation.function.lower()

        if func_name == "print":
            print(*args)
        else:
            print(f"⚙️ Invoked unknown function: {func_name}")

    def evaluate_condition(self, condition: Condition) -> bool:
        left = self.evaluate_expression(condition.left)
        right = self.evaluate_expression(condition.right) if condition.right else None

        if condition.operator == "==":
            return left == right
        elif condition.operator == "!=":
            return left != right
        elif condition.operator == ">":
            return left > right
        elif condition.operator == "<":
            return left < right
        elif condition.operator == ">=":
            return left >= right
        elif condition.operator == "<=":
            return left <= right
        elif condition.operator is None:
            return bool(left)
        else:
            raise Exception(f"Unsupported operator: {condition.operator}")

    def evaluate_expression(self, expr: Expression):
        if isinstance(expr, Literal):
            return expr.value
        elif isinstance(expr, Expression) and expr.operator:
            left = self.evaluate_expression(expr.left)
            right = self.evaluate_expression(expr.right)
            return self.apply_operator(left, expr.operator, right)
        elif isinstance(expr, str):
            return self.environment.get(expr, expr)
        return expr

    def evaluate_literal(self, value):
        if isinstance(value, str) and value in self.environment:
            return self.environment[value]
        return value

    def apply_operator(self, left, op, right):
        if op == '+': return left + right
        if op == '-': return left - right
        if op == '*': return left * right
        if op == '/': return left / right
        raise Exception(f"Unknown operator: {op}")
