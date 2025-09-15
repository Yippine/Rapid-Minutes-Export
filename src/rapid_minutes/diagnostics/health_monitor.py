"""
Health Monitor - Advanced system health monitoring and alerting
Part of the automated diagnosis and repair system for Phase 3 excellence
"""

import asyncio
import time
import psutil
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta

class HealthStatus(Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"

@dataclass
class HealthMetric:
    """Represents a single health metric measurement"""
    name: str
    value: float
    unit: str
    status: HealthStatus
    threshold_warning: float
    threshold_critical: float
    timestamp: datetime
    description: str = ""

@dataclass
class SystemHealthReport:
    """Comprehensive system health report"""
    timestamp: datetime
    overall_status: HealthStatus
    metrics: List[HealthMetric]
    recommendations: List[str]
    alerts: List[str]
    uptime_seconds: float

class HealthMonitor:
    """
    Advanced system health monitoring with proactive issue detection

    Features:
    - Real-time system metrics monitoring
    - Predictive health analysis
    - Automated alerting
    - Performance trend analysis
    - Resource usage optimization recommendations
    """

    def __init__(self, check_interval: int = 30):
        self.check_interval = check_interval
        self.logger = logging.getLogger(__name__)
        self.start_time = time.time()
        self.metrics_history: List[SystemHealthReport] = []
        self.max_history_size = 1000

        # Health thresholds (configurable)
        self.thresholds = {
            'cpu_percent': {'warning': 70.0, 'critical': 90.0},
            'memory_percent': {'warning': 80.0, 'critical': 95.0},
            'disk_percent': {'warning': 85.0, 'critical': 95.0},
            'response_time_ms': {'warning': 2000.0, 'critical': 5000.0},
            'error_rate_percent': {'warning': 5.0, 'critical': 15.0},
            'active_connections': {'warning': 100, 'critical': 200}
        }

    async def start_monitoring(self):
        """Start continuous health monitoring"""
        self.logger.info("Starting health monitoring system...")

        while True:
            try:
                report = await self.generate_health_report()
                await self.process_health_report(report)
                self._store_health_report(report)

                # Log critical issues immediately
                if report.overall_status == HealthStatus.CRITICAL:
                    self.logger.critical(f"CRITICAL SYSTEM HEALTH: {report.alerts}")
                elif report.overall_status == HealthStatus.WARNING:
                    self.logger.warning(f"System health warnings: {len(report.alerts)} issues detected")

                await asyncio.sleep(self.check_interval)

            except Exception as e:
                self.logger.error(f"Health monitoring error: {e}")
                await asyncio.sleep(self.check_interval)

    async def generate_health_report(self) -> SystemHealthReport:
        """Generate comprehensive health report"""
        timestamp = datetime.now()
        metrics = []
        alerts = []
        recommendations = []

        # System resource metrics
        cpu_metric = await self._check_cpu_usage()
        memory_metric = await self._check_memory_usage()
        disk_metric = await self._check_disk_usage()

        metrics.extend([cpu_metric, memory_metric, disk_metric])

        # Application-specific metrics
        response_metric = await self._check_response_time()
        error_metric = await self._check_error_rate()
        connection_metric = await self._check_active_connections()

        metrics.extend([response_metric, error_metric, connection_metric])

        # Analyze metrics for alerts and recommendations
        overall_status = HealthStatus.HEALTHY

        for metric in metrics:
            if metric.status == HealthStatus.CRITICAL:
                overall_status = HealthStatus.CRITICAL
                alerts.append(f"CRITICAL: {metric.name} is {metric.value}{metric.unit} (threshold: {metric.threshold_critical})")
                recommendations.extend(self._get_metric_recommendations(metric))
            elif metric.status == HealthStatus.WARNING and overall_status != HealthStatus.CRITICAL:
                overall_status = HealthStatus.WARNING
                alerts.append(f"WARNING: {metric.name} is {metric.value}{metric.unit} (threshold: {metric.threshold_warning})")
                recommendations.extend(self._get_metric_recommendations(metric))

        # Check for trending issues
        trend_alerts, trend_recommendations = await self._analyze_trends()
        alerts.extend(trend_alerts)
        recommendations.extend(trend_recommendations)

        uptime_seconds = time.time() - self.start_time

        return SystemHealthReport(
            timestamp=timestamp,
            overall_status=overall_status,
            metrics=metrics,
            recommendations=list(set(recommendations)),  # Remove duplicates
            alerts=alerts,
            uptime_seconds=uptime_seconds
        )

    async def _check_cpu_usage(self) -> HealthMetric:
        """Check CPU usage percentage"""
        cpu_percent = psutil.cpu_percent(interval=1)

        if cpu_percent >= self.thresholds['cpu_percent']['critical']:
            status = HealthStatus.CRITICAL
        elif cpu_percent >= self.thresholds['cpu_percent']['warning']:
            status = HealthStatus.WARNING
        else:
            status = HealthStatus.HEALTHY

        return HealthMetric(
            name="CPU Usage",
            value=cpu_percent,
            unit="%",
            status=status,
            threshold_warning=self.thresholds['cpu_percent']['warning'],
            threshold_critical=self.thresholds['cpu_percent']['critical'],
            timestamp=datetime.now(),
            description="System CPU utilization percentage"
        )

    async def _check_memory_usage(self) -> HealthMetric:
        """Check memory usage percentage"""
        memory = psutil.virtual_memory()
        memory_percent = memory.percent

        if memory_percent >= self.thresholds['memory_percent']['critical']:
            status = HealthStatus.CRITICAL
        elif memory_percent >= self.thresholds['memory_percent']['warning']:
            status = HealthStatus.WARNING
        else:
            status = HealthStatus.HEALTHY

        return HealthMetric(
            name="Memory Usage",
            value=memory_percent,
            unit="%",
            status=status,
            threshold_warning=self.thresholds['memory_percent']['warning'],
            threshold_critical=self.thresholds['memory_percent']['critical'],
            timestamp=datetime.now(),
            description="System memory utilization percentage"
        )

    async def _check_disk_usage(self) -> HealthMetric:
        """Check disk usage percentage"""
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100

        if disk_percent >= self.thresholds['disk_percent']['critical']:
            status = HealthStatus.CRITICAL
        elif disk_percent >= self.thresholds['disk_percent']['warning']:
            status = HealthStatus.WARNING
        else:
            status = HealthStatus.HEALTHY

        return HealthMetric(
            name="Disk Usage",
            value=disk_percent,
            unit="%",
            status=status,
            threshold_warning=self.thresholds['disk_percent']['warning'],
            threshold_critical=self.thresholds['disk_percent']['critical'],
            timestamp=datetime.now(),
            description="System disk space utilization percentage"
        )

    async def _check_response_time(self) -> HealthMetric:
        """Check application response time"""
        # Simulate response time check (replace with actual implementation)
        response_time = 150.0  # Placeholder value in ms

        if response_time >= self.thresholds['response_time_ms']['critical']:
            status = HealthStatus.CRITICAL
        elif response_time >= self.thresholds['response_time_ms']['warning']:
            status = HealthStatus.WARNING
        else:
            status = HealthStatus.HEALTHY

        return HealthMetric(
            name="Response Time",
            value=response_time,
            unit="ms",
            status=status,
            threshold_warning=self.thresholds['response_time_ms']['warning'],
            threshold_critical=self.thresholds['response_time_ms']['critical'],
            timestamp=datetime.now(),
            description="Average API response time"
        )

    async def _check_error_rate(self) -> HealthMetric:
        """Check application error rate"""
        # Simulate error rate check (replace with actual implementation)
        error_rate = 1.5  # Placeholder value in percentage

        if error_rate >= self.thresholds['error_rate_percent']['critical']:
            status = HealthStatus.CRITICAL
        elif error_rate >= self.thresholds['error_rate_percent']['warning']:
            status = HealthStatus.WARNING
        else:
            status = HealthStatus.HEALTHY

        return HealthMetric(
            name="Error Rate",
            value=error_rate,
            unit="%",
            status=status,
            threshold_warning=self.thresholds['error_rate_percent']['warning'],
            threshold_critical=self.thresholds['error_rate_percent']['critical'],
            timestamp=datetime.now(),
            description="Application error rate percentage"
        )

    async def _check_active_connections(self) -> HealthMetric:
        """Check number of active connections"""
        # Simulate active connections check (replace with actual implementation)
        active_connections = 25  # Placeholder value

        if active_connections >= self.thresholds['active_connections']['critical']:
            status = HealthStatus.CRITICAL
        elif active_connections >= self.thresholds['active_connections']['warning']:
            status = HealthStatus.WARNING
        else:
            status = HealthStatus.HEALTHY

        return HealthMetric(
            name="Active Connections",
            value=active_connections,
            unit="connections",
            status=status,
            threshold_warning=self.thresholds['active_connections']['warning'],
            threshold_critical=self.thresholds['active_connections']['critical'],
            timestamp=datetime.now(),
            description="Number of active client connections"
        )

    def _get_metric_recommendations(self, metric: HealthMetric) -> List[str]:
        """Get recommendations based on metric status"""
        recommendations = []

        if metric.name == "CPU Usage" and metric.status != HealthStatus.HEALTHY:
            recommendations.extend([
                "Consider scaling horizontally with additional instances",
                "Review CPU-intensive operations and optimize algorithms",
                "Check for infinite loops or inefficient background processes"
            ])

        elif metric.name == "Memory Usage" and metric.status != HealthStatus.HEALTHY:
            recommendations.extend([
                "Implement memory caching strategies",
                "Review memory leaks in long-running processes",
                "Consider increasing available memory or optimizing memory usage"
            ])

        elif metric.name == "Disk Usage" and metric.status != HealthStatus.HEALTHY:
            recommendations.extend([
                "Implement log rotation and cleanup policies",
                "Archive or delete old upload files",
                "Monitor temporary file cleanup processes"
            ])

        elif metric.name == "Response Time" and metric.status != HealthStatus.HEALTHY:
            recommendations.extend([
                "Optimize database queries and add appropriate indexes",
                "Implement response caching for frequently accessed data",
                "Review API endpoint efficiency and reduce processing time"
            ])

        elif metric.name == "Error Rate" and metric.status != HealthStatus.HEALTHY:
            recommendations.extend([
                "Review recent error logs and fix underlying issues",
                "Implement better input validation and error handling",
                "Check external service dependencies and add circuit breakers"
            ])

        return recommendations

    async def _analyze_trends(self) -> Tuple[List[str], List[str]]:
        """Analyze trends in health metrics"""
        alerts = []
        recommendations = []

        if len(self.metrics_history) < 3:
            return alerts, recommendations

        # Simple trend analysis (can be enhanced with more sophisticated algorithms)
        recent_reports = self.metrics_history[-3:]

        # Check for degrading trends
        for metric_name in ['CPU Usage', 'Memory Usage', 'Response Time']:
            values = [
                next((m.value for m in report.metrics if m.name == metric_name), 0)
                for report in recent_reports
            ]

            if len(values) == 3 and values[0] < values[1] < values[2]:
                alerts.append(f"TREND: {metric_name} is consistently increasing")
                recommendations.append(f"Monitor {metric_name} closely and prepare scaling strategies")

        return alerts, recommendations

    def _store_health_report(self, report: SystemHealthReport):
        """Store health report in history"""
        self.metrics_history.append(report)

        # Maintain history size limit
        if len(self.metrics_history) > self.max_history_size:
            self.metrics_history = self.metrics_history[-self.max_history_size:]

    async def process_health_report(self, report: SystemHealthReport):
        """Process health report and trigger actions if needed"""
        # This method can be extended to integrate with alerting systems,
        # auto-repair mechanisms, or external monitoring tools

        if report.overall_status == HealthStatus.CRITICAL:
            await self._trigger_critical_alert(report)
        elif report.overall_status == HealthStatus.WARNING:
            await self._trigger_warning_alert(report)

    async def _trigger_critical_alert(self, report: SystemHealthReport):
        """Trigger critical system alert"""
        self.logger.critical("CRITICAL SYSTEM ALERT")
        self.logger.critical(f"Alerts: {report.alerts}")
        self.logger.critical(f"Recommendations: {report.recommendations}")

        # Here you could integrate with:
        # - Email/SMS alerting systems
        # - Slack/Discord notifications
        # - PagerDuty or similar incident management
        # - Auto-scaling triggers

    async def _trigger_warning_alert(self, report: SystemHealthReport):
        """Trigger system warning alert"""
        self.logger.warning("SYSTEM WARNING")
        self.logger.warning(f"Alerts: {report.alerts}")
        self.logger.warning(f"Recommendations: {report.recommendations}")

    def get_current_health_status(self) -> Optional[SystemHealthReport]:
        """Get the most recent health report"""
        if self.metrics_history:
            return self.metrics_history[-1]
        return None

    def get_health_history(self, hours: int = 24) -> List[SystemHealthReport]:
        """Get health history for the specified number of hours"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [
            report for report in self.metrics_history
            if report.timestamp >= cutoff_time
        ]

    def export_health_data(self) -> Dict:
        """Export health data for external analysis"""
        current_status = self.get_current_health_status()
        if not current_status:
            return {}

        return {
            'current_status': asdict(current_status),
            'history_count': len(self.metrics_history),
            'uptime_hours': current_status.uptime_seconds / 3600,
            'monitoring_active': True
        }