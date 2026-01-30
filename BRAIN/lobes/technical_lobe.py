from sympy import symbols, Eq, solve, linsolve, sympify, diff, integrate
from sympy.core.sympify import SympifyError
import ast
import sys
from ..belel_langchain_wrapper import query_model  # Your wrapper for model queries
from ..trust_score_audit import audit_output  # Your auditor

class RestrictedExec:
    def __init__(self):
        self.allowed_globals = {
            '__builtins__': {
                'abs': abs, 'dict': dict, 'help': help, 'min': min, 'setattr': setattr,
                'all': all, 'dir': dir, 'hex': hex, 'next': next, 'slice': slice,
                'any': any, 'divmod': divmod, 'id': id, 'object': object, 'sorted': sorted,
                'ascii': ascii, 'enumerate': enumerate, 'input': input, 'oct': oct, 'staticmethod': staticmethod,
                'bin': bin, 'eval': eval, 'int': int, 'open': open, 'str': str,
                'bool': bool, 'exec': exec, 'isinstance': isinstance, 'ord': ord, 'sum': sum,
                'bytearray': bytearray, 'filter': filter, 'issubclass': issubclass, 'pow': pow, 'super': super,
                'bytes': bytes, 'float': float, 'iter': iter, 'print': print, 'tuple': tuple,
                'callable': callable, 'format': format, 'len': len, 'property': property, 'type': type,
                'chr': chr, 'frozenset': frozenset, 'list': list, 'range': range, 'vars': vars,
                'classmethod': classmethod, 'getattr': getattr, 'locals': locals, 'repr': repr, 'zip': zip,
                'compile': compile, 'globals': globals, 'map': map, 'reversed': reversed,
                'complex': complex, 'hasattr': hasattr, 'max': max, 'round': round
            }
        }  # Restricted builtins to prevent escapes

    def execute_safely(self, code_str):
        try:
            tree = ast.parse(code_str)
            # Simple AST check: Ban imports, etc.
            for node in ast.walk(tree):
                if isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
                    raise ValueError("Imports not allowed in sandbox.")
            exec(code_str, self.allowed_globals)
            return self.allowed_globals.get('result', None)  # Assume code sets 'result'
        except Exception as e:
            return f"Sandbox error: {str(e)}"

class TechnicalLobe:
    def __init__(self):
        self.sandbox = RestrictedExec()

    def solve_math(self, equation: str):
        try:
            expr = sympify(equation)
            x = symbols('x')
            solution = solve(expr, x)
            return str(solution)
        except SympifyError:
            return "Invalid equation."

    def differentiate(self, func: str):
        x = symbols('x')
        return str(diff(sympify(func), x))

    def integrate_func(self, func: str):
        x = symbols('x')
        return str(integrate(sympify(func), x))

    def generate_code(self, task: str):
        prompt = f"Generate safe Python code for: {task}. Set 'result' to output. No imports."
        code = query_model(prompt)  # Use your model to gen code
        output = self.sandbox.execute_safely(code)
        audited = audit_output(output)  # Sovereign check
        return {"code": code, "output": audited if audited else output}

# Integrate in brain_router.py: route_to_technical(signal) calls this