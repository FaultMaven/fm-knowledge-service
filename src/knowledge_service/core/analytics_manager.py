"""Analytics tracking for search and knowledge base usage."""

import logging
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class AnalyticsManager:
    """Manager for tracking analytics and usage metrics."""

    def __init__(self):
        self.search_history: List[Dict[str, Any]] = []
        self.query_counts: Dict[str, int] = defaultdict(int)
        self.search_results_count: List[int] = []

    def track_search(self, query: str, result_count: int, execution_time_ms: float,
                     user_id: str, search_mode: str = "semantic"):
        """Track a search query."""
        search_record = {
            "query": query,
            "result_count": result_count,
            "execution_time_ms": execution_time_ms,
            "user_id": user_id,
            "search_mode": search_mode,
            "timestamp": datetime.utcnow().isoformat()
        }

        self.search_history.append(search_record)
        self.query_counts[query.lower()] += 1
        self.search_results_count.append(result_count)

        # Keep only last 1000 searches to prevent memory issues
        if len(self.search_history) > 1000:
            self.search_history = self.search_history[-1000:]

        logger.debug(f"Tracked search: query='{query}', results={result_count}")

    def get_analytics(self) -> Dict[str, Any]:
        """Get search analytics summary."""
        if not self.search_history:
            return {
                "total_searches": 0,
                "top_queries": [],
                "avg_results_per_query": 0.0,
                "search_trends": {}
            }

        # Calculate top queries
        top_queries = sorted(
            [{"query": q, "count": c} for q, c in self.query_counts.items()],
            key=lambda x: x["count"],
            reverse=True
        )[:10]

        # Calculate average results per query
        avg_results = (
            sum(self.search_results_count) / len(self.search_results_count)
            if self.search_results_count else 0.0
        )

        # Calculate search trends (by day)
        trends = defaultdict(int)
        for search in self.search_history:
            try:
                timestamp = datetime.fromisoformat(search["timestamp"])
                date_key = timestamp.strftime("%Y-%m-%d")
                trends[date_key] += 1
            except Exception as e:
                logger.warning(f"Error processing timestamp: {e}")

        return {
            "total_searches": len(self.search_history),
            "top_queries": top_queries,
            "avg_results_per_query": round(avg_results, 2),
            "search_trends": dict(trends)
        }

    def reset_analytics(self):
        """Reset all analytics data."""
        self.search_history = []
        self.query_counts = defaultdict(int)
        self.search_results_count = []
        logger.info("Analytics data reset")
