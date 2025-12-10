from typing import Callable, Dict

class ToolRegistry:
    _registry: Dict[str, Callable] = {}

    @classmethod
    def register(cls, name: str):
        """Decorator to register a function as a tool."""
        def decorator(func: Callable):
            cls._registry[name] = func
            return func
        return decorator

    @classmethod
    def get_tool(cls, name: str) -> Callable:
        if name not in cls._registry:
            raise ValueError(f"Tool '{name}' not found in registry.")
        return cls._registry[name]

    @classmethod
    def list_tools(cls):
        return list(cls._registry.keys())