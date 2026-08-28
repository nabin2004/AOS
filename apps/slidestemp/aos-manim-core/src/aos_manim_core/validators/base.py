from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional


class ValidationSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


@dataclass
class ValidationIssue:
    code: str
    message: str
    severity: ValidationSeverity = ValidationSeverity.ERROR
    target: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        loc = f" on [{self.target}]" if self.target else ""
        return f"[{self.severity.value}] {self.code}{loc}: {self.message}"


@dataclass
class ValidationResult:
    is_valid: bool = True
    issues: List[ValidationIssue] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_issue(
        self,
        code: str,
        message: str,
        severity: ValidationSeverity = ValidationSeverity.ERROR,
        target: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        if severity == ValidationSeverity.ERROR:
            self.is_valid = False
        self.issues.append(
            ValidationIssue(
                code=code,
                message=message,
                severity=severity,
                target=target,
                details=details or {},
            )
        )

    def merge(self, other: ValidationResult) -> ValidationResult:
        merged = ValidationResult(
            is_valid=self.is_valid and other.is_valid,
            issues=self.issues + other.issues,
            metadata={**self.metadata, **other.metadata},
        )
        return merged

    def summary(self) -> str:
        if self.is_valid and not self.issues:
            return "Validation PASSED: All invariants and constraints satisfied."
        status = "PASSED with warnings" if self.is_valid else "FAILED"
        lines = [f"Validation {status} ({len(self.issues)} issues):"]
        for issue in self.issues:
            lines.append(f"  - {issue}")
        return "\n".join(lines)


class BaseValidator(ABC):
    """Abstract base validator for all plugin checks."""

    @abstractmethod
    def validate(self, target: Any, **kwargs: Any) -> ValidationResult:
        """Validate target object or result and return a ValidationResult."""
        pass
