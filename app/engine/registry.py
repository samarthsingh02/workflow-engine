from typing import Callable, Dict, Optional


class ToolRegistry:
    _tools: Dict[str, Callable] = {}
    _conditions: Dict[str, Callable] = {}

    # --- Tool Management ---
    @classmethod
    def register(cls, name: str):
        """Decorator to register a function as a tool."""

        def decorator(func: Callable):
            cls._tools[name] = func
            return func

        return decorator

    @classmethod
    def get_tool(cls, name: str) -> Callable:
        if name not in cls._tools:
            raise ValueError(f"Tool '{name}' not found in registry.")
        return cls._tools[name]

    @classmethod
    def list_tools(cls):
        return list(cls._tools.keys())

    # --- Condition Management ---
    @classmethod
    def register_condition(cls, name: str):
        """Decorator to register a function as a condition for edges."""

        def decorator(func: Callable):
            cls._conditions[name] = func
            return func

        return decorator

    @classmethod
    def get_condition(cls, name: str) -> Callable:
        if name not in cls._conditions:
            raise ValueError(f"Condition '{name}' not found in registry.")
        return cls._conditions[name]

    @classmethod
    def get_condition_name(cls, func: Callable) -> Optional[str]:
        """Reverse lookup: find the registered name for a given function object."""
        for name, registered_func in cls._conditions.items():
            if registered_func == func:
                return name
        return None