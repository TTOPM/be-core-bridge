from __future__ import annotations

class CoreAdapter:
    def models_ok(self) -> bool:
        return True

    def pin_safe_profile(self) -> None:
        # pin to conservative routing/model
        pass

    def router_reset(self) -> None:
        pass
