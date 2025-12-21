"""
Model configuration management for OpenRouter integration.
Handles favorites, defaults, and model metadata persistence.
"""

import json
import os
import requests
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path

# NO DEFAULT CONFIGURATION - Fail-fast approach
# Configuration must be explicitly provided in models_config.json

class ModelsConfig:
    """Manages model configuration and OpenRouter integration."""
    
    def __init__(self, config_path: str = None):
        if config_path is None:
            # Look at repository root (3 levels up: core/ -> src/ -> development/ -> root)
            repo_root = Path(__file__).parent.parent.parent.parent
            config_path = repo_root / "models_config.json"
        self.config_path = Path(config_path)
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        
        if not self.openrouter_api_key:
            raise ValueError(
                "❌ OPENROUTER_API_KEY environment variable not set\n"
                "🔧 Set OPENROUTER_API_KEY in your .env file"
            )
    
    def _read_json(self, path: Path) -> Optional[Dict]:
        """Read JSON file with fail-fast error handling."""
        if not path.exists():
            return None  # Let caller handle missing file
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"❌ Invalid JSON in {path}: {e}")
        except Exception as e:
            raise RuntimeError(f"❌ Failed to read {path}: {e}")
    
    def _write_json(self, path: Path, data: Dict) -> Tuple[bool, Optional[str]]:
        """Write JSON file safely."""
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True, None
        except Exception as e:
            return False, str(e)
    
    def load_config(self) -> Tuple[List[str], str, Dict, str]:
        """Load model configuration with FAIL-FAST - no defaults!
        
        Returns:
            (favorites, default_model, meta, last_session_name)
        
        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config is invalid or missing required fields
        """
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"❌ Models configuration file not found: {self.config_path}\n"
                f"🔧 Create {self.config_path} with required fields:\n"
                f"   {{\n"
                f"     \"favorites\": [\"model-id-1\", \"model-id-2\"],\n"
                f"     \"default\": \"model-id-1\",\n"
                f"     \"meta\": {{}},\n"
                f"     \"last_session_name\": \"\"\n"
                f"   }}"
            )
        
        cfg = self._read_json(self.config_path)
        if cfg is None:
            raise ValueError(f"❌ Failed to read models configuration: {self.config_path}")
        
        # Require explicit values - NO FALLBACKS
        if "favorites" not in cfg:
            raise ValueError(
                f"❌ 'favorites' field missing in {self.config_path}\n"
                f"🔧 Add \"favorites\": [\"model-id-1\", \"model-id-2\"]"
            )
        
        if not cfg["favorites"]:
            raise ValueError(
                f"❌ 'favorites' list is empty in {self.config_path}\n"
                f"🔧 Add at least one model to favorites list"
            )
        
        if "default" not in cfg:
            raise ValueError(
                f"❌ 'default' field missing in {self.config_path}\n"
                f"🔧 Add \"default\": \"model-id\""
            )
        
        if not cfg["default"]:
            raise ValueError(
                f"❌ 'default' model is empty in {self.config_path}\n"
                f"🔧 Set \"default\" to a valid model ID"
            )
        
        favorites = cfg["favorites"]
        default_model = cfg["default"]
        
        # Validate default is in favorites
        if default_model not in favorites:
            raise ValueError(
                f"❌ Default model '{default_model}' not in favorites list\n"
                f"🔧 Add '{default_model}' to favorites or choose a different default\n"
                f"   Current favorites: {favorites}"
            )
        
        meta = cfg.get("meta", {})
        last_session_name = cfg.get("last_session_name", "")
        
        return favorites, default_model, meta, last_session_name
    
    def save_config(self, favorites: List[str], default_model: str, 
                   meta: Dict, last_session_name: str = None) -> Tuple[bool, Optional[str]]:
        """Save model configuration with validation - NO FALLBACKS.
        
        Raises:
            ValueError: If favorites is empty or default_model is not in favorites
        """
        # Validate before saving - NO FALLBACKS
        if not favorites:
            raise ValueError("❌ Cannot save config: favorites list is empty")
        
        if not default_model:
            raise ValueError("❌ Cannot save config: default_model is empty")
        
        if default_model not in favorites:
            raise ValueError(
                f"❌ Cannot save config: default_model '{default_model}' not in favorites\n"
                f"   Current favorites: {favorites}"
            )
        
        data = {
            "favorites": list(favorites),
            "default": default_model,
            "meta": meta or {},
            "last_used": default_model,  # Track last used model
        }
        if last_session_name is not None:
            data["last_session_name"] = last_session_name
        return self._write_json(self.config_path, data)
    
    def _price_per_million(self, v) -> Optional[float]:
        """Convert price to per-million tokens."""
        try:
            x = float(v)
            return x * 1_000_000.0
        except Exception:
            return None
    
    def _fmt_usd_per_m(self, v) -> str:
        """Format USD per million tokens."""
        if v is None:
            return "n/a"
        try:
            return f"${v:.2f}/M"
        except Exception:
            return "n/a"
    
    def fetch_openrouter_models(self) -> Tuple[List[Dict], Optional[str]]:
        """Fetch models from OpenRouter API.
        
        Returns:
            (models_list, error). Each model: {id, prompt_per_m, completion_per_m, ctx}
        """
        if not self.openrouter_api_key:
            return [], "OPENROUTER_API_KEY not set"
        
        url = "https://openrouter.ai/api/v1/models"
        headers = {
            "Authorization": f"Bearer {self.openrouter_api_key}",
            "HTTP-Referer": "http://localhost",
            "X-Title": "ScrumSimV3",
        }
        
        try:
            r = requests.get(url, headers=headers, timeout=(10, 60))
            if r.status_code != 200:
                return [], f"HTTP {r.status_code}"
            
            data = r.json() or {}
            items = data.get("data") or []
            out = []
            
            for m in items:
                mid = (m.get("id") or "").strip()
                pr = None
                co = None
                ctx = None
                
                try:
                    pricing = m.get("pricing") or {}
                    pr = self._price_per_million(pricing.get("prompt")) if pricing.get("prompt") is not None else None
                    co = self._price_per_million(pricing.get("completion")) if pricing.get("completion") is not None else None
                except Exception:
                    pass
                
                try:
                    tp = m.get("top_provider") or {}
                    ctx = tp.get("context_length")
                except Exception:
                    pass
                
                out.append({
                    "id": mid,
                    "prompt_per_m": pr,
                    "completion_per_m": co,
                    "ctx": ctx,
                })
            
            return out, None
        except Exception as e:
            return [], str(e)
    
    def describe_model_row(self, m: Dict) -> str:
        """Create a descriptive string for a model."""
        pid = m.get("id") or ""
        pin = self._fmt_usd_per_m(m.get("prompt_per_m"))
        pout = self._fmt_usd_per_m(m.get("completion_per_m"))
        ctx = m.get("ctx")
        ctxs = f" · {ctx} ctx" if ctx else ""
        return f"{pid} — {pin} in · {pout} out{ctxs}"
    
    def fetch_openrouter_credits(self) -> Tuple[Optional[Dict], Optional[str]]:
        """Fetch OpenRouter credits information."""
        if not self.openrouter_api_key:
            return None, "OPENROUTER_API_KEY not set"
        
        url = "https://openrouter.ai/api/v1/credits"
        headers = {
            "Authorization": f"Bearer {self.openrouter_api_key}",
            "HTTP-Referer": "http://localhost",
            "X-Title": "ScrumSimV3",
        }
        
        try:
            r = requests.get(url, headers=headers, timeout=(10, 30))
            if r.status_code != 200:
                return None, f"HTTP {r.status_code}"
            js = r.json() or {}
            return js.get("data") or {}, None
        except Exception as e:
            return None, str(e)
    
    def sort_models(self, models: List[Dict], mode: str) -> List[Dict]:
        """Sort models by specified criteria."""
        if mode == "Price (input)":
            return sorted(models, key=lambda m: (m.get("prompt_per_m") is None, m.get("prompt_per_m") or 0.0, m.get("id")))
        elif mode == "Price (output)":
            return sorted(models, key=lambda m: (m.get("completion_per_m") is None, m.get("completion_per_m") or 0.0, m.get("id")))
        else:  # Alphabetical
            return sorted(models, key=lambda m: m.get("id", ""))
    
    def filter_models(self, models: List[Dict], filter_text: str = "", 
                     show_free_only: bool = False) -> List[Dict]:
        """Filter models by text and free-only option."""
        if show_free_only:
            models = [m for m in models if m.get("id", "").endswith(":free")]
        
        if filter_text:
            ftxt = filter_text.strip().lower()
            models = [m for m in models if ftxt in (m.get("id") or "").lower()]
        
        return models
