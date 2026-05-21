import importlib.util
import sys
from pathlib import Path
from typing import Optional

from loguru import logger

class Pipe:
    def __init__(self):
        pass
        
    def pipe(self, body: dict, __user__: Optional[dict] = None) -> str:
        user_query = body["messages"][-1]["content"]

        try:
            root = Path(__file__).resolve().parents[3]
            wrapper_path = root / "src" / "openwebui-haystack-orchestrator" / "pipeline_wrappers.py"
            spec = importlib.util.spec_from_file_location("pipeline_wrappers_local", str(wrapper_path))
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)

            run_agentic_reply = getattr(module, "run_agentic_reply")
            return run_agentic_reply(user_query)
        except Exception as e:
            logger.error("Local agentic pipeline failed: {}", e)
            return f"Local agentic pipeline error: {e}"