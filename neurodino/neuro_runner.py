
# neurodino/neuro_runner.py
from __future__ import annotations
import pygame
import numpy as np
import math
import pickle
import os
import csv
import time
from typing import List, Optional
from tensorboardX import SummaryWriter # Visualization

from pydino.runner import Runner, Config, _get
from pydino.trex import Status as TrexStatus
from .neuro_trex import NeuroTrex
from .genetics import Genetics
from .brain import Brain
from .sensors import get_inputs

class NeuroRunner(Runner):
    """
    Subclass of Runner that manages a population of NeuroTrex agents.
    Overrides the main game loop to simulate multiple agents simultaneously.

    The runner the first model (v1) was trained with, kept to reproduce it.
    Its agents decide before the obstacles move each frame, unlike
    watch_model.py, the website and main_train.py (neurodino/episode.py).
    """
    def __init__(self, screen, dimensions, pop_size=50, target_fps=60):
        # Disable audio cues for training to avoid noise/overhead
        super().__init__(screen, dimensions, use_audio=False)
        
        self.pop_size = pop_size
        self.target_fps = target_fps
        self.genetics = Genetics(pop_size)
        self.generation = 1
        self.best_distance = 0
        self.best_global_score = 0 # Track all-time best for safe saving
        self.brain_file = "best_brain.pkl"
        self.rendering = True  # Default to rendering enabled
        
        # Initialize CSV Log
        self.log_file = "training_log.csv"
        if not os.path.exists(self.log_file):
            with open(self.log_file, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["Generation", "Max_Score", "Avg_Score", "Global_Best"])
        else:
            # Resume generation count from CSV
            try:
                with open(self.log_file, "r") as f:
                    lines = list(csv.reader(f))
                    if len(lines) > 1: # Header + at least 1 row
                        last_row = lines[-1]
                        if last_row:
                            self.generation = int(last_row[0]) + 1
                            print(f"Resuming from Generation {self.generation}")
            except Exception as e:
                print(f"Could not read generation from CSV: {e}")
        
        # We need to re-initialize population properly
        self.watching_dino = None
        self._init_population()

    def set_rendering(self, enabled: bool):
        """Toggle rendering to save resources."""
        self.rendering = enabled


    def _init_components(self) -> None:
        """Override to prevent creating a default single Trex."""
        # We call super()._init_components() to setup Horizon, DistanceMeter etc.
        # But we will overwrite self.trex later.
        super()._init_components()
        # Create a dummy list if needed, but _init_population handles the real deal
        self.population: List[NeuroTrex] = []

    def _init_population(self):
        """Create trexes for current genomes."""
        # Try to load saved brain
        self.best_brain = None # Initialize to avoid AttributeError
        loaded_score = 0
        
        # Load best brain if exists
        if os.path.exists(self.brain_file):
            try:
                with open(self.brain_file, "rb") as f:
                    data = pickle.load(f)
                    
                    if isinstance(data, tuple):
                        self.best_brain, saved_score = data
                        self.best_global_score = saved_score
                        self.best_distance = saved_score # Sync UI
                        print(f"Loaded best_brain.pkl! High Score: {self.best_global_score}")
                    else:
                        print("Loaded legacy brain file (no score). Resetting score.")
                        self.best_brain = data
                        self.best_global_score = 0
            except (EOFError, pickle.UnpicklingError):
                 print("Error loading brain file. Starting fresh.")
        
        # Initialize TensorBoard Writers
        
        # 1. Full History (Static Name -> Single Color, Continuous)
        self.writer_full = SummaryWriter(log_dir="runs/dino-full-train")
        
        # 2. Session Log (Dynamic Name -> Multi Color, Segmented)
        timestamp = int(time.time())
        log_dir_session = f"runs/dino-train-{timestamp}"
        self.writer_session = SummaryWriter(log_dir=log_dir_session)
        
        print(f"TensorBoard logging to:\n  - {log_dir_session}\n  - runs/dino-full-train")

        # If we have a saved brain, populate with mutations of it
        if self.best_brain:
            self.genetics.genomes = []
            # Keep one exact copy (Elitism) check
            self.genetics.genomes.append(self.best_brain.copy())
            # Fill the rest with mutated versions
            for _ in range(self.pop_size - 1):
                child = self.best_brain.copy()
                child.mutate(0.20) # Apply mutation to diversify
                self.genetics.genomes.append(child)

        # Check if we have genomes (first run vs next gen)
        if not self.genetics.genomes:
            # First gen: Create random brains
            # Inputs: 12 (Enhanced for Immortal Play)
            #   Obs1[TTI, Action, Width], Obs2[TTI, Action, Width]
            #   Speed, Gap, DinoY, DinoVelocity, Airborne, Ducking
            # Outputs: 3 (Jump, Duck, Run)
            # Hidden: 48 (Increased capacity for complex timing)
            self.genetics.create_random_population(input_size=12, hidden_size=48, output_size=3)
        
        self.population = []
        for i in range(self.genetics.pop_size):
            # Create our NeuroTrex 
            t = NeuroTrex(self.screen, self.sprite_def["tRex"], self)
            t.brain = self.genetics.genomes[i]
            t.index = i
            self.population.append(t)
        
        # Point self.trex to the first one for compatibility with some Runner methods
        if self.population:
            self.trex = self.population[0]

    def _get_inputs(self, dino):
        """The network's 12 inputs for one dino; see neurodino/sensors.py."""
        return get_inputs(self, dino)

    def update(self) -> None:
        """
        Overridden game loop.
        Adapted from Runner.update but for multiple agents.
        """
        now = pygame.time.get_ticks()
        # We ignore actual wall-clock delta to enforce deterministic fixed time step.
        # This ensures Cloud (frame-based) and Dino (time-based) remain in sync
        # regardless of training speed (FPS).
        
        # Calculate delta based on target FPS
        delta = 1000.0 / self.target_fps 
        
        # Speed scale for frame-based objects (Clouds)
        # If FPS is 120, scale should be 0.5 (move half distance per frame)
        speed_scale = 60.0 / self.target_fps
        
        self.time_ms = now
        
        # 1. AI Updates (Think & Act)
        if self.playing and not self.crashed:
            active_dinos = [d for d in self.population if d.status != TrexStatus.CRASHED]
            for dino in active_dinos:
                dino.fitness = self.distance_ran
                inputs = self._get_inputs(dino)
                outputs = dino.brain.predict(inputs)
                action = np.argmax(outputs)
                dino.act(action)
                dino.update(delta) # Apply animation state
                
                # Apply jump physics if jumping
                if dino.jumping:
                    dino.updateJump(delta)
            
            # Debug Probe: Print Brain state if Leader is in danger
            if self.watching_dino and self.watching_dino.status != TrexStatus.CRASHED:
                # Re-calculate partial input to check checks
                # Note: This is expensive if done every frame, but fine for debugging 1 agent
                if self.watching_dino in active_dinos:
                     # Check direct inputs
                     dummy_inputs = self._get_inputs(self.watching_dino)


        # 2. Physics & Logic
        if self.rendering:
            self.screen.fill((247, 247, 247))

        if self.playing:
            self.running_time += delta

        has_obstacles = self.running_time > self.config.clearTime
        # Apply speed_scale to horizon update (affects Clouds/Ground scroll per frame)
        # Note: Horizon.update might draw internally depending on implementation, 
        # but we can't easily stop it without modifying pydino.
        self.horizon.update(delta, self.current_speed * speed_scale, has_obstacles, False)

        if self.rendering:
            if self.playing:
                self.distance_meter.update(delta, math.ceil(self.distance_ran))
            else:
                 self.distance_meter.update(0, math.ceil(self.distance_ran))
        else:
            # Still need to update distance state even if not drawing? 
            # actually distance_meter.update does logic like score calc?
            # Usually only drawing. Distance ran is tracked in self.distance_ran
            pass

        # Draw Logic: Sticky Camera (Prevents flickering)
        if not hasattr(self, "watching_dino"):
            self.watching_dino = None
            
        if self.watching_dino is None or self.watching_dino.status == TrexStatus.CRASHED:
             active_dinos = [d for d in self.population if d.status != TrexStatus.CRASHED]
             if active_dinos:
                 # Watch the best performing dino (highest fitness = longest survival)
                 self.watching_dino = max(active_dinos, key=lambda d: d.fitness)
             else:
                 self.watching_dino = None

        # Note: dino.update() already called in AI loop (line 245)
        # Only handle crashed dino position updates here
        for dino in self.population:
            if dino.status == TrexStatus.CRASHED:
                dino.xPos -= self.current_speed * (delta / self.ms_per_frame)

        # Draw Logic: Manual Smart Draw
        # We manually fetch the correct animation frame and draw ONCE.
        if self.rendering and self.watching_dino and self.watching_dino.status != TrexStatus.CRASHED:
            try:
                # 1. Temporarily enable drawing
                self.watching_dino.visible = True
                
                # 2. Calculate correct frame x-coordinate
                # Trex.update calculates this internally, but doesn't expose 'sprite_x_to_draw' publicly
                # So we re-calculate it from the state variables.
                frames = self.watching_dino.currentAnimFrames
                if frames:
                    idx = self.watching_dino.currentFrameIndex % len(frames)
                    x_pos = frames[idx]
                    self.watching_dino.draw(x_pos, 0)
                
                # 3. Disable drawing again
                self.watching_dino.visible = False
            except Exception as e:
                # Log for debugging instead of silent fail
                print(f"Warning: Drawing error for watching_dino: {e}")

        # 4. Collision Detection - Check ALL visible obstacles
        if self.playing and not self.crashed:
            if has_obstacles and self.horizon.obstacles:
                for dino in self.population:
                    if dino.status == TrexStatus.CRASHED:
                        continue
                    
                    # Check collision with ALL visible obstacles, not just the first
                    for obstacle in self.horizon.obstacles:
                        if self._check_for_collision(obstacle, dino):
                            dino.update(100, TrexStatus.CRASHED)
                            dino.fitness = self.distance_ran
                            break  # No need to check more obstacles for this dino

            # Check if anyone is alive
            alive_count = sum(1 for d in self.population if d.status != TrexStatus.CRASHED)
            if alive_count == 0:
                self.crashed = True
                self.start_next_generation()
            else:
                self.distance_ran += self.current_speed * (delta / self.ms_per_frame)
                if self.current_speed < self.config.maxSpeed:
                    self.current_speed += self.config.acceleration

        # 5. Draw Stats
        if self.rendering:
            self._draw_overlay(alive_count if 'alive_count' in locals() else 0)
        
        # 6. Draw Brain Visualization
        if self.rendering and self.watching_dino and self.watching_dino.status != TrexStatus.CRASHED:
             self._draw_brain(self.watching_dino.brain)

    def _draw_overlay(self, alive_count):
        try:
            font = pygame.font.Font(None, 24)
            # Use max of recorded best or current generation's best if we are tracking it differently
            display_best = max(self.best_global_score, int(self.best_distance))
            stats = [
                f"Gen: {self.generation}",
                f"Alive: {alive_count}/{self.pop_size}",
                f"Best: {display_best}",
                f"Speed: {self.current_speed:.1f}"
            ]
            for i, line in enumerate(stats):
                txt = font.render(line, True, (80, 80, 80))
                self.screen.blit(txt, (10, 10 + i * 20))
        except:
            pass

    def start_next_generation(self):
        """Evolve and restart."""
        # 1. Collect fitness data
        pop_data = []
        gen_max = 0
        for dino in self.population:
            gen_max = max(gen_max, dino.fitness)
            pop_data.append((dino.brain, dino.fitness))
        
        # Sync high score to GUI if possible
        if hasattr(self.distance_meter, "highScore"):
             self.distance_meter.highScore = self.best_distance
             
        # Report Score (matched to game UI: pixels * 0.025)
        current_score = int(gen_max * 0.025)
        print(f"Gen {self.generation} Done. Max Score: {current_score}")

        # Save Best Brain (ONLY IF REKOR KIRILDI)
        if pop_data:
            pop_data.sort(key=lambda x: x[1], reverse=True)
            best_brain = pop_data[0][0]
            
            # Update global best score if beaten
            if current_score > self.best_global_score:
                previous_best = self.best_global_score # Keep track for logging
                self.best_global_score = current_score
                self.best_distance = current_score # Sync for UI
                print(f"🏆 NEW RECORD! (Was: {previous_best} -> Now: {current_score})")
                
                # 1. Main Save (Overwrite)
                with open("best_brain.pkl", "wb") as f:
                    pickle.dump((best_brain, current_score), f)
                
                # 2. Backup Save (History)
                if not os.path.exists("backups"):
                    os.makedirs("backups")
                    
                backup_filename = f"backups/brain_score_{current_score}.pkl"
                with open(backup_filename, "wb") as f:
                    pickle.dump((best_brain, current_score), f)
                print(f"   Saved backup: {backup_filename}")
                
            else:
                 # Optional: print current best to show we are safe
                 pass

        # 1.5 Log to CSV
        avg_score = sum(d.fitness for d in self.population) / len(self.population)
        avg_score = int(avg_score * 0.025) # Convert to game score units
        
        with open(self.log_file, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                self.generation,
                current_score,
                avg_score,
                self.best_global_score
            ])

        # 1.6 TensorBoard Logging (Dual Write)
        # Log to Session (Color Segment)
        if self.writer_session:
            # SCALARS
            self.writer_session.add_scalar("Score/Max", current_score, self.generation)
            self.writer_session.add_scalar("Score/Average", avg_score, self.generation)
            self.writer_session.add_scalar("Score/Global_Best", self.best_global_score, self.generation)
            self.writer_session.add_scalar("Performance/Game_Speed", self.current_speed, self.generation)
            
            # HISTOGRAMS
            self.writer_session.add_histogram("Weights/Input_Hidden", best_brain.weights_ih, self.generation)
            self.writer_session.add_histogram("Weights/Hidden_Output", best_brain.weights_ho, self.generation)
            self.writer_session.add_histogram("Biases/Hidden", best_brain.bias_h, self.generation)
            self.writer_session.add_histogram("Biases/Output", best_brain.bias_o, self.generation)

        # Log to Full History (Continuous Segment)
        if self.writer_full:
            # SCALARS
            self.writer_full.add_scalar("Score/Max", current_score, self.generation)
            self.writer_full.add_scalar("Score/Average", avg_score, self.generation)
            self.writer_full.add_scalar("Score/Global_Best", self.best_global_score, self.generation)
            self.writer_full.add_scalar("Performance/Game_Speed", self.current_speed, self.generation)
            
            # HISTOGRAMS
            self.writer_full.add_histogram("Weights/Input_Hidden", best_brain.weights_ih, self.generation)
            self.writer_full.add_histogram("Weights/Hidden_Output", best_brain.weights_ho, self.generation)
            self.writer_full.add_histogram("Biases/Hidden", best_brain.bias_h, self.generation)
            self.writer_full.add_histogram("Biases/Output", best_brain.bias_o, self.generation)

        # Calculate current adaptive mutation rate for logging
        # (Same formula as in Genetics.evolve_population)
        base_rate = 0.20
        generation_decay = 0.995 ** self.generation
        score_factor = 1.0 / (1.0 + self.best_global_score / 2000.0)
        current_mutation_rate = max(0.02, min(0.25, base_rate * generation_decay * score_factor))
        
        # Log mutation rate to TensorBoard
        if self.writer_session:
            self.writer_session.add_scalar("Evolution/Mutation_Rate", current_mutation_rate, self.generation)
        if self.writer_full:
            self.writer_full.add_scalar("Evolution/Mutation_Rate", current_mutation_rate, self.generation)

        # 2. Evolve with ADAPTIVE mutation rate
        new_genomes = self.genetics.evolve_population(
            pop_data, 
            generation=self.generation,
            best_score=self.best_global_score
        )
        
        # 3. Reset Game State
        self.generation += 1
        self.crashed = False
        self.playing = True
        self.distance_ran = 0
        self.current_speed = self.config.speed
        
        self.horizon.reset()
        self.distance_meter.reset()
        
        # 4. Re-create population
        self.population = []
        for i in range(self.genetics.pop_size):
            t = NeuroTrex(self.screen, self.sprite_def["tRex"], self)
            t.brain = new_genomes[i]
            t.index = i
            self.population.append(t)
        
        self.trex = self.population[0]
        self.watching_dino = self.population[0] # Start watching the first one
        self.activated = True # Skip intro

    def _draw_brain(self, brain: Brain):
        """Draws the neural network visualization."""
        if not hasattr(brain, "last_inputs") or not hasattr(brain, "last_hidden"):
            return

        start_y = 160
        w = self.screen.get_width()
        h = self.screen.get_height() - start_y
        
        # Background for dashboard
        surf = pygame.Surface((w, h))
        surf.fill((30, 30, 30)) # Dark Grey
        self.screen.blit(surf, (0, start_y))
        
        # Layout positions
        layer_x = [50, 300, 550] # Input, Hidden, Output X coords
        
        # Node positions
        input_y = np.linspace(start_y + 40, start_y + h - 40, brain.input_nodes)
        hidden_y = np.linspace(start_y + 20, start_y + h - 20, brain.hidden_nodes)
        output_y = np.linspace(start_y + 60, start_y + h - 60, brain.output_nodes)
        
        # Labels
        input_labels = ["O1 TTI", "O1 Act", "O1 W", "O2 TTI", "O2 Act", "O2 W", "Speed", "Gap", "DinoY", "DinoVel", "Air", "Duck"]
        output_labels = ["Jump", "Duck", "Run"]
        
        font = pygame.font.Font(None, 20)
        
        def get_color(val):
            """Green for high activation, Fade for low."""
            v = max(0, min(1, val))
            return (int(v*255), int(v*255), int(v*255))

        # 1. Draw Weights
        # IH Weights
        for i in range(brain.input_nodes):
            for j in range(brain.hidden_nodes):
                weight = brain.weights_ih[j][i]
                color = (255, 50, 50) if weight < 0 else (50, 255, 50)
                width = max(1, int(abs(weight) * 3))
                if abs(weight) > 0.1: # Optimize drawing
                    pygame.draw.line(self.screen, color, (layer_x[0], int(input_y[i])), (layer_x[1], int(hidden_y[j])), width)
        
        # HO Weights 
        for j in range(brain.hidden_nodes):
            for k in range(brain.output_nodes):
                weight = brain.weights_ho[k][j]
                color = (255, 50, 50) if weight < 0 else (50, 255, 50)
                width = max(1, int(abs(weight) * 3))
                if abs(weight) > 0.1:
                    pygame.draw.line(self.screen, color, (layer_x[1], int(hidden_y[j])), (layer_x[2], int(output_y[k])), width)

        # 2. Draw Nodes
        # Input Nodes
        for i, val in enumerate(brain.last_inputs):
            color = get_color(val)
            pos = (layer_x[0], int(input_y[i]))
            pygame.draw.circle(self.screen, color, pos, 10)
            pygame.draw.circle(self.screen, (200,200,200), pos, 10, 1)
            
            # Label
            lbl = font.render(f"{input_labels[i]}:{val:.2f}", True, (200,200,200))
            self.screen.blit(lbl, (pos[0]-40, pos[1]-20))

        # Hidden Nodes
        for i, val in enumerate(brain.last_hidden):
            # Tanh outputs [-1, 1], normalize to [0, 1] for visualization
            normalized = (val + 1.0) / 2.0  # Maps -1→0, 0→0.5, 1→1
            color = get_color(normalized)
            pos = (layer_x[1], int(hidden_y[i]))
            pygame.draw.circle(self.screen, color, pos, 8)
            pygame.draw.circle(self.screen, (200,200,200), pos, 8, 1)

        # Output Nodes
        max_idx = np.argmax(brain.last_outputs)
        for i, val in enumerate(brain.last_outputs):
            color = (0, 255, 0) if i == max_idx else (100, 100, 100) # Highlight decision
            pos = (layer_x[2], int(output_y[i]))
            
            # Radius reflects confidence
            radius = 10 + int(val * 10)
            pygame.draw.circle(self.screen, color, pos, radius)
            pygame.draw.circle(self.screen, (255,255,255), pos, radius, 2)
            
            # Label
            lbl_txt = f"{output_labels[i]} ({val:.1%})"
            lbl = font.render(lbl_txt, True, (255,255,255))
            self.screen.blit(lbl, (pos[0]+25, pos[1]-5))
