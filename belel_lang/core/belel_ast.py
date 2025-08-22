# be_core_bridge/soul/belel_ast.py

"""
Belel AST (Abstract Syntax Tree) generator
Parses BelelLang into a structured, introspectable tree.
Designed for spiritual governance, covenant logic, and AI integrity enforcement.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Union

# Base Node
@dataclass
class ASTNode:
    pass

# === Program Root ===
@dataclass
class Program(ASTNode):
    statements: List['Statement']

# === Statements ===
@dataclass
class Statement(ASTNode):
    pass

@dataclass
class Declaration(Statement):
    name: str
    value_type: str
    value: Optional[Union[str, int, float, bool]] = None

@dataclass
class Invocation(Statement):
    function: str
    arguments: List['Expression']

@dataclass
class LogicBlock(Statement):
    condition: 'Condition'
    then_branch: Statement
    else_branch: Optional[Statement] = None

@dataclass
class Covenant(Statement):
    name: str
    clauses: List['CovenantClause']

# === Covenant Clauses ===
@dataclass
class CovenantClause(ASTNode):
    clause_type: str  # "require", "permit", "forbid"
    body: Union['Condition', 'Action']

@dataclass
class Action(ASTNode):
    name: str
    arguments: List['Expression'] = field(default_factory=list)

# === Expressions and Conditions ===
@dataclass
class Expression(ASTNode):
    left: Union['Expression', str, int, float, bool]
    operator: Optional[str] = None
    right: Optional['Expression'] = None

@dataclass
class Condition(ASTNode):
    left: Expression
    operator: Optional[str] = None
    right: Optional[Expression] = None

# === Literals ===
@dataclass
class Literal(Expression):
    value: Union[str, int, float, bool]

# === Types ===
@dataclass
class TypeAnnotation(ASTNode):
    type_name: str

# === Identifiers ===
@dataclass
class Identifier(ASTNode):
    name: str
