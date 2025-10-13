# Performance Optimization

### Database Optimization
```sql
-- Performance optimization queries
-- /opt/cognito-ai/backend/database/optimizations.sql

-- Optimize category results queries
CREATE INDEX CONCURRENTLY idx_category_results_composite
ON category_results(request_id, status, completed_at DESC)
WHERE status = 'completed';

-- Optimize source reference lookups
CREATE INDEX CONCURRENTLY idx_source_references_composite
ON source_references(category_result_id, verification_status, credibility_score DESC)
WHERE verification_status IN ('verified', 'pending');

-- Optimize audit queries with partial index
CREATE INDEX CONCURRENTLY idx_audit_events_recent
ON audit_events(timestamp DESC, event_type)
WHERE timestamp >= CURRENT_DATE - INTERVAL '90 days';

-- Materialized view for dashboard analytics
CREATE MATERIALIZED VIEW mv_request_analytics AS
SELECT
    DATE_TRUNC('day', created_at) as date,
    status,
    COUNT(*) as request_count,
    AVG(EXTRACT(EPOCH FROM (completed_at - created_at))/60) as avg_processing_minutes,
    COUNT(DISTINCT drug_name) as unique_drugs
FROM drug_requests
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE_TRUNC('day', created_at), status;

-- Refresh materialized view hourly
CREATE OR REPLACE FUNCTION refresh_analytics()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_request_analytics;
END;
$$ LANGUAGE plpgsql;
```

### Caching Strategy
```python
# apps/backend/src/core/caching.py
import redis
import json
from typing import Optional, Any
from datetime import timedelta

class PharmaceuticalCache:
    """
    Specialized caching for pharmaceutical data with appropriate TTLs
    """

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.default_ttl = 3600  # 1 hour

        # Different TTLs for different data types
        self.ttl_config = {
            "category_config": 86400,     # 24 hours - relatively stable
            "drug_request": 1800,         # 30 minutes - frequently updated
            "source_analysis": 3600,      # 1 hour - processed data
            "conflict_resolution": 7200,  # 2 hours - complex computations
            "api_response": 300,          # 5 minutes - fresh data needed
        }

    async def get_cached_result(self, key: str, data_type: str = "default") -> Optional[Any]:
        """Get cached pharmaceutical processing result"""
        try:
            cached_data = await self.redis.get(f"pharma:{data_type}:{key}")
            if cached_data:
                return json.loads(cached_data)
            return None
        except Exception as e:
            # Log error but don't fail the operation
            logger.error(f"Cache retrieval error: {str(e)}")
            return None

    async def cache_result(self, key: str, data: Any, data_type: str = "default") -> bool:
        """Cache pharmaceutical processing result with appropriate TTL"""
        try:
            ttl = self.ttl_config.get(data_type, self.default_ttl)
            await self.redis.setex(
                f"pharma:{data_type}:{key}",
                ttl,
                json.dumps(data, default=str)
            )
            return True
        except Exception as e:
            logger.error(f"Cache storage error: {str(e)}")
            return False

    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate cache entries matching pattern"""
        try:
            keys = await self.redis.keys(f"pharma:{pattern}*")
            if keys:
                return await self.redis.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache invalidation error: {str(e)}")
            return 0
```
