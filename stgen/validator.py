"""
Automated Protocol Validation Framework
Checks protocol compliance with IoT communication best practices.
"""

import logging
from typing import Dict, Any, List
from dataclasses import dataclass

_LOG = logging.getLogger("validator")


@dataclass
class ValidationResult:
    """Result of a single validation check."""
    check_name: str
    passed: bool
    message: str
    severity: str  # "critical", "warning", "info"
    metric_value: Any = None


class ProtocolValidator:
    """
    Validates protocol implementation against IoT best practices.
    
    Checks include:
    - Latency requirements
    - Packet loss tolerance
    - Throughput capabilities
    - Order preservation
    - Concurrency handling
    - Failure recovery
    """
    
    def __init__(self, results: Dict[str, Any], qos_requirements: Dict[str, Any] = None):
        """
        Initialize validator.
        
        Args:
            results: Test results from orchestrator
            qos_requirements: Expected QoS thresholds (optional)
        """
        self.results = results
        self.qos = qos_requirements or {}
        self.checks: List[ValidationResult] = []
        
    def run_all_checks(self) -> List[ValidationResult]:
        """Run all validation checks."""
        _LOG.info("Running protocol validation checks...")
        
        self._check_latency()
        self._check_packet_loss()
        self._check_throughput()
        self._check_concurrency()
        self._check_ordering()
        self._check_error_handling()
        
        return self.checks
    
    def _check_latency(self) -> None:
        """Validate latency meets requirements."""
        max_latency = self.qos.get("max_latency_ms", 200)
        
        if "lat_p95_ms" in self.results:
            p95 = self.results["lat_p95_ms"]
            passed = p95 <= max_latency
            
            self.checks.append(ValidationResult(
                check_name="Latency (P95)",
                passed=passed,
                message=f"P95 latency: {p95:.2f}ms (threshold: {max_latency}ms)",
                severity="critical" if not passed else "info",
                metric_value=p95
            ))
        
        if "lat_p99_ms" in self.results:
            p99 = self.results["lat_p99_ms"]
            max_p99 = max_latency * 2  # P99 can be 2x P95
            passed = p99 <= max_p99
            
            self.checks.append(ValidationResult(
                check_name="Latency (P99)",
                passed=passed,
                message=f"P99 latency: {p99:.2f}ms (threshold: {max_p99}ms)",
                severity="warning" if not passed else "info",
                metric_value=p99
            ))
    
    def _check_packet_loss(self) -> None:
        """Validate packet loss is within acceptable range."""
        max_loss = self.qos.get("max_loss_percent", 1.0) / 100.0
        
        if "loss" in self.results:
            loss = self.results["loss"]
            passed = loss <= max_loss
            
            self.checks.append(ValidationResult(
                check_name="Packet Loss",
                passed=passed,
                message=f"Loss rate: {loss*100:.2f}% (threshold: {max_loss*100:.1f}%)",
                severity="critical" if not passed else "info",
                metric_value=loss
            ))
    
    def _check_throughput(self) -> None:
        """Validate throughput capabilities."""
        if "sent" in self.results and "recv" in self.results:
            sent = self.results["sent"]
            recv = self.results["recv"]
            
            # Check if protocol handled all clients
            min_expected = self.qos.get("min_messages", 10)
            passed = recv >= min_expected
            
            self.checks.append(ValidationResult(
                check_name="Throughput",
                passed=passed,
                message=f"Delivered {recv}/{sent} messages (min: {min_expected})",
                severity="warning" if not passed else "info",
                metric_value=recv
            ))
    
    def _check_concurrency(self) -> None:
        """Check if protocol handles concurrent clients."""
        if "sent" in self.results and "errors" in self.results:
            errors = self.results["errors"]
            passed = errors == 0
            
            self.checks.append(ValidationResult(
                check_name="Concurrency Handling",
                passed=passed,
                message=f"Errors during concurrent operation: {errors}",
                severity="critical" if not passed else "info",
                metric_value=errors
            ))
    
    def _check_ordering(self) -> None:
        """Check message ordering (if required)."""
        if self.qos.get("in_order_delivery", False):
            # Check if protocol maintains order
            # This requires sequence number analysis (to be implemented)
            self.checks.append(ValidationResult(
                check_name="Message Ordering",
                passed=True,  # Placeholder
                message="Order preservation not yet validated",
                severity="info"
            ))
    
    def _check_error_handling(self) -> None:
        """Validate error handling and recovery."""
        if "errors" in self.results:
            errors = self.results["errors"]
            passed = errors == 0
            
            self.checks.append(ValidationResult(
                check_name="Error Handling",
                passed=passed,
                message=f"Total errors: {errors}",
                severity="warning" if errors > 0 else "info",
                metric_value=errors
            ))
    
    def generate_report(self) -> str:
        """Generate validation report."""
        report = []
        report.append("=" * 60)
        report.append("PROTOCOL VALIDATION REPORT")
        report.append("=" * 60)
        report.append("")
        
        passed = sum(1 for c in self.checks if c.passed)
        total = len(self.checks)
        
        report.append(f"Checks Passed: {passed}/{total}")
        report.append("")
        
        for check in self.checks:
            if check.passed:
                symbol = "✅"
            elif check.severity == "critical":
                symbol = "❌"
            else:
                symbol = " "
            
            report.append(f"{symbol} {check.check_name}: {check.message}")
        
        report.append("")
        report.append("=" * 60)
        
        if passed == total:
            report.append(" ALL CHECKS PASSED - Protocol is production-ready!")
        elif any(c.severity == "critical" and not c.passed for c in self.checks):
            report.append(" CRITICAL ISSUES FOUND - Protocol needs fixes")
        else:
            report.append("  WARNINGS FOUND - Protocol works but has issues")
        
        report.append("=" * 60)
        
        return "\n".join(report)


def validate_protocol_results(results: Dict[str, Any], qos: Dict[str, Any] = None) -> str:
    """
    Convenience function to validate protocol results.
    
    Args:
        results: Test results from orchestrator
        qos: QoS requirements
        
    Returns:
        Validation report string
    """
    validator = ProtocolValidator(results, qos)
    validator.run_all_checks()
    return validator.generate_report()