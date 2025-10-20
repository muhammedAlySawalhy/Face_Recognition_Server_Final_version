from fastapi import Request

from ..registry import MetricRegistry


def get_registry(request: Request) -> MetricRegistry:
    return request.app.state.registry
