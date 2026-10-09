from __future__ import annotations

from dataclasses import dataclass


@dataclass
class StopPolicy:
    max_steps: int = 16

    def should_stop(self, step: int, has_final_text: bool) -> bool:
        if has_final_text:
            return True
        return step >= self.max_steps
