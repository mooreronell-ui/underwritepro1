"""
Monitoring and Metrics Module for UnderwritePro SaaS
Tracks application performance, errors, and business metrics
"""
import os
import time
import logging
from datetime import datetime
from typing import Dict, Any
from collections import defaultdict
import threading

logger = logging.getLogger(__name__)

class MetricsCollector:
    """Collect and track application metrics"""
    
    def __init__(self):
        self.metrics = defaultdict(lambda: {
            "count": 0,
            "total_time": 0,
            "min_time": float('inf'),
            "max_time": 0,
            "errors": 0
        })
        self.lock = threading.Lock()
        
        # Business metrics
        self.business_metrics = {
            "total_users": 0,
            "total_organizations": 0,
            "total_deals": 0,
            "total_borrowers": 0,
            "deals_by_status": defaultdict(int),
            "deals_by_type": defaultdict(int)
        }
    
    def record_request(self, endpoint: str, duration: float, status_code: int):
        """Record API request metrics"""
        with self.lock:
            metric = self.metrics[endpoint]
            metric["count"] += 1
            metric["total_time"] += duration
            metric["min_time"] = min(metric["min_time"], duration)
            metric["max_time"] = max(metric["max_time"], duration)
            
            if status_code >= 400:
                metric["errors"] += 1
    
    def record_business_event(self, event_type: str, data: Dict[str, Any]):
        """Record business events"""
        with self.lock:
            if event_type == "user_registered":
                self.business_metrics["total_users"] += 1
                self.business_metrics["total_organizations"] += 1
            elif event_type == "deal_created":
                self.business_metrics["total_deals"] += 1
                self.business_metrics["deals_by_status"][data.get("status", "unknown")] += 1
                self.business_metrics["deals_by_type"][data.get("deal_type", "unknown")] += 1
            elif event_type == "borrower_created":
                self.business_metrics["total_borrowers"] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all metrics"""
        with self.lock:
            # Calculate averages
            endpoint_metrics = {}
            for endpoint, data in self.metrics.items():
                if data["count"] > 0:
                    endpoint_metrics[endpoint] = {
                        "count": data["count"],
                        "avg_time": data["total_time"] / data["count"],
                        "min_time": data["min_time"],
                        "max_time": data["max_time"],
                        "errors": data["errors"],
                        "error_rate": data["errors"] / data["count"] if data["count"] > 0 else 0
                    }
            
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "endpoints": endpoint_metrics,
                "business": dict(self.business_metrics)
            }
    
    def reset(self):
        """Reset all metrics"""
        with self.lock:
            self.metrics.clear()
            self.business_metrics = {
                "total_users": 0,
                "total_organizations": 0,
                "total_deals": 0,
                "total_borrowers": 0,
                "deals_by_status": defaultdict(int),
                "deals_by_type": defaultdict(int)
            }

# Global metrics collector
metrics_collector = MetricsCollector()

class RequestTimer:
    """Context manager for timing requests"""
    
    def __init__(self, endpoint: str):
        self.endpoint = endpoint
        self.start_time = None
        self.duration = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.duration = time.time() - self.start_time
        status_code = 500 if exc_type else 200
        metrics_collector.record_request(self.endpoint, self.duration, status_code)

def get_system_metrics() -> Dict[str, Any]:
    """Get system-level metrics"""
    import psutil
    
    return {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage('/').percent,
        "timestamp": datetime.utcnow().isoformat()
    }

def get_database_metrics(engine) -> Dict[str, Any]:
    """Get database connection pool metrics"""
    try:
        pool = engine.pool
        return {
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "total_connections": pool.size() + pool.overflow()
        }
    except Exception as e:
        logger.error(f"Failed to get database metrics: {e}")
        return {}

class HealthChecker:
    """Check health of various system components"""
    
    @staticmethod
    def check_database(engine) -> Dict[str, Any]:
        """Check database connectivity"""
        try:
            from sqlalchemy import text
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return {"status": "healthy", "latency_ms": 0}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
    
    @staticmethod
    def check_redis(redis_client) -> Dict[str, Any]:
        """Check Redis connectivity"""
        if not redis_client:
            return {"status": "disabled"}
        
        try:
            redis_client.ping()
            return {"status": "healthy"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
    
    @staticmethod
    def check_disk_space() -> Dict[str, Any]:
        """Check available disk space"""
        import psutil
        disk = psutil.disk_usage('/')
        
        status = "healthy"
        if disk.percent > 90:
            status = "critical"
        elif disk.percent > 80:
            status = "warning"
        
        return {
            "status": status,
            "percent_used": disk.percent,
            "free_gb": disk.free / (1024**3)
        }
    
    @staticmethod
    def check_memory() -> Dict[str, Any]:
        """Check available memory"""
        import psutil
        memory = psutil.virtual_memory()
        
        status = "healthy"
        if memory.percent > 90:
            status = "critical"
        elif memory.percent > 80:
            status = "warning"
        
        return {
            "status": status,
            "percent_used": memory.percent,
            "available_gb": memory.available / (1024**3)
        }
    
    @staticmethod
    def get_overall_health(engine, redis_client=None) -> Dict[str, Any]:
        """Get overall system health"""
        checks = {
            "database": HealthChecker.check_database(engine),
            "redis": HealthChecker.check_redis(redis_client),
            "disk": HealthChecker.check_disk_space(),
            "memory": HealthChecker.check_memory()
        }
        
        # Determine overall status
        statuses = [check["status"] for check in checks.values()]
        if "critical" in statuses or "unhealthy" in statuses:
            overall_status = "unhealthy"
        elif "warning" in statuses:
            overall_status = "degraded"
        else:
            overall_status = "healthy"
        
        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": checks
        }

class AlertManager:
    """Manage alerts for critical issues"""
    
    def __init__(self):
        self.alerts = []
        self.alert_thresholds = {
            "error_rate": 0.1,  # 10% error rate
            "response_time": 5.0,  # 5 seconds
            "cpu_percent": 90,
            "memory_percent": 90,
            "disk_percent": 90
        }
    
    def check_alerts(self, metrics: Dict[str, Any]):
        """Check if any metrics exceed thresholds"""
        alerts = []
        
        # Check endpoint error rates
        for endpoint, data in metrics.get("endpoints", {}).items():
            if data.get("error_rate", 0) > self.alert_thresholds["error_rate"]:
                alerts.append({
                    "type": "high_error_rate",
                    "endpoint": endpoint,
                    "error_rate": data["error_rate"],
                    "threshold": self.alert_thresholds["error_rate"]
                })
            
            if data.get("avg_time", 0) > self.alert_thresholds["response_time"]:
                alerts.append({
                    "type": "slow_response",
                    "endpoint": endpoint,
                    "avg_time": data["avg_time"],
                    "threshold": self.alert_thresholds["response_time"]
                })
        
        return alerts

# Global instances
alert_manager = AlertManager()
