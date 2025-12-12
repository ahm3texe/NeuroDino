
# neurodino/neuro_trex.py
from __future__ import annotations
import sys
import os

# Ensure pydino is importable
# Assuming this script is run from project root, 'pydino' is a top-level package.
# If run locally, we might need path hack.
from pydino.trex import Trex, Status
from typing import Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from .brain import Brain

class NeuroTrex(Trex):
    """
    AI-controlled T-Rex.
    Overrides input handling to listen to the neural network instead of keyboard.
    """
    def __init__(self, screen, sprite_def, runner):
        self.visible = False # Initialize before super() because super calls update->draw
        super().__init__(screen, sprite_def, runner)
        self.runner = runner 
        self.brain: Optional[Brain] = None
        self.fitness: float = 0.0
        self.is_alive: bool = True
        
        # Force running state immediately for AI (properly init frames)
        self.update(0, Status.RUNNING)
        
    def draw(self, x, y):
        """Only draw if visible."""
        if self.visible:
            super().draw(x, y)
        
    def handle_event(self, event):
        """Disable manual input."""
        pass

    def act(self, action: int):
        """
        Execute action decided by the Brain.
        0: JUMP
        1: DUCK
        2: RUN (Do nothing)
        """
        if self.status == Status.CRASHED:
            return

        # 0: JUMP
        if action == 0:
            if not self.jumping and not self.ducking:
                self.startJump(self.runner.current_speed)
        
        # 1: DUCK
        elif action == 1:
            if self.jumping:
                # Fast drop
                self.setSpeedDrop()
            elif not self.ducking:
                self.setDuck(True)
        
        # 2: RUN
        else:
            if self.ducking:
                self.setDuck(False)
