#!/usr/bin/env python3
"""
NeuroDino - Model Watcher (Inference Mode)

Watch your trained brain play the game without training.
Press 'S' to toggle between 60 FPS and Unlimited FPS.
Press 'R' to restart the game.
Press 'Q' or ESC to quit.

Usage:
    python watch_model.py                    # Load best_brain.pkl
    python watch_model.py --brain path.pkl   # Load specific brain file
    python watch_model.py --fast             # Start in unlimited FPS mode
    python watch_model.py --silent           # No display, just run and print scores
"""

import os
import sys
import argparse
import pickle
import pygame

# Add pydino directory to sys.path
pydino_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pydino")
sys.path.append(pydino_path)

from dimensions import Dimensions
from pydino.runner import Runner, Config
from pydino.trex import Trex, Status as TrexStatus
from neurodino.neuro_trex import NeuroTrex
from neurodino.brain import Brain
from neurodino.sensors import get_inputs
import numpy as np
import math


class ModelWatcher(Runner):
    """
    Simplified runner for watching a single trained brain play.
    No training, no population - just inference.
    """
    
    def __init__(self, screen, dimensions, brain: Brain, target_fps=60, silent=False):
        super().__init__(screen, dimensions, use_audio=not silent)
        
        self.brain = brain
        self.target_fps = target_fps
        self.score = 0
        self.high_score = 0
        self.games_played = 0
        self.silent = silent
        self.last_10k = 0  # Track last 10K milestone for silent mode
        
        # Night mode variables (matching original Runner)
        self.inverted = False
        self.invert_timer = 0
        self.invert_trigger = False
        self.NIGHT_ALPHA_MAX = 180
        self.VISUAL_INVERT_MS = 1000
        self._night_overlay = pygame.Surface((dimensions.width, dimensions.height), pygame.SRCALPHA)
        
        # Visualization toggles
        self.viz_bezier = True      # B - Use Bezier curves
        self.viz_width = True       # W - Edge width proportional to weights
        self.viz_opacity = True     # O - Edge opacity proportional to weights
        self.viz_color = True       # C - Edge color by weight sign (blue/red vs gray)
        
        # Replace default trex with our NeuroTrex
        self._setup_neuro_trex()
    
    def _setup_neuro_trex(self):
        """Setup a single NeuroTrex with the loaded brain."""
        self.dino = NeuroTrex(self.screen, self.sprite_def["tRex"], self)
        self.dino.brain = self.brain
        self.dino.visible = True
        self.trex = self.dino  # For compatibility with base Runner
    
    def _get_inputs(self):
        """Get inputs for the brain (same as training); see neurodino/sensors.py."""
        return get_inputs(self, self.dino)
    
    def update(self):
        """Game loop with AI control."""
        now = pygame.time.get_ticks()
        delta = 1000.0 / 60  # Fixed 60 FPS physics
        self.time_ms = now
        
        # Clear screen (skip in silent mode)
        if not self.silent:
            self.screen.fill((247, 247, 247))
        
        # Update game state
        if self.playing:
            self.running_time += delta
        
        has_obstacles = self.running_time > self.config.clearTime
        
        # Night mode logic (from original Runner) - always update timer, even in turbo
        show_night_mode = self.inverted
        if self.playing:
            actual_score = int(self.distance_ran * 0.025)
            
            # Timer-based fade cycle
            if self.invert_timer > self.config.invertFadeDuration:
                self.invert_timer = 0
                self.invert_trigger = False
                self.inverted = not self.inverted
            elif self.invert_timer > 0:
                self.invert_timer += delta
            else:
                # Trigger at each invertDistance milestone
                if actual_score > 0 and (actual_score % self.config.invertDistance == 0) and not self.invert_trigger:
                    self.invert_timer += delta
                    self.inverted = not self.inverted
                    self.invert_trigger = True
                elif (actual_score % self.config.invertDistance) != 0:
                    self.invert_trigger = False
        
        # Draw horizon FIRST (includes moon, stars, clouds, ground) 
        self.horizon.update(delta, self.current_speed, has_obstacles, show_night_mode)
        
        # AI Decision and Dino update (draws dino ON TOP of horizon)
        if self.playing and not self.crashed and self.dino.status != TrexStatus.CRASHED:
            inputs = self._get_inputs()
            outputs = self.dino.brain.predict(inputs)
            action = np.argmax(outputs)
            self.dino.act(action)
            self.dino.update(delta)  # This draws dino
            
            if self.dino.jumping:
                self.dino.updateJump(delta)
        
        if self.playing and not self.silent:
            self.distance_meter.update(delta, math.ceil(self.distance_ran))
        
        # Collision detection
        if self.playing and not self.crashed:
            if has_obstacles and self.horizon.obstacles:
                for obstacle in self.horizon.obstacles:
                    if self._check_for_collision(obstacle, self.dino):
                        self.dino.update(100, TrexStatus.CRASHED)
                        self.crashed = True
                        self._on_game_over()
                        break
            
            if not self.crashed:
                self.distance_ran += self.current_speed * (delta / self.ms_per_frame)
                self.score = int(self.distance_ran * 0.025)
                
                # Silent mode: Print every 10K
                if self.silent:
                    current_10k = self.score // 10000
                    if current_10k > self.last_10k:
                        self.last_10k = current_10k
                        print(f"📈 Score: {self.score:,}")
                
                if self.current_speed < self.config.maxSpeed:
                    self.current_speed += self.config.acceleration
        
        # Draw game over panel if crashed (skip in silent mode)
        if not self.silent and self.crashed and self.game_over_panel:
            self.game_over_panel.draw(False, self.dino)
        
        # Apply night overlay (skip in silent mode)
        if not self.silent:
            fade_factor = self._get_invert_fade_factor()
            if fade_factor > 0:
                self._apply_night_overlay(fade_factor)
        
        # Draw stats overlay (skip in silent mode)
        # Blit game surface to main screen (centered)
        if not self.silent and hasattr(self, 'main_screen'):
            # Clear main screen
            self.main_screen.fill((247, 247, 247))
            # Blit game surface centered
            offset = getattr(self, 'game_offset', 0)
            self.main_screen.blit(self.screen, (offset, 0))
            # Draw stats and brain on main screen
            self._draw_stats(self.main_screen, offset)
            self._draw_brain(self.main_screen)
    
    def _get_invert_fade_factor(self):
        """Calculate fade factor for night mode transition (from original Runner)."""
        T = self.config.invertFadeDuration
        t = self.invert_timer
        vis = self.VISUAL_INVERT_MS
        
        if self.inverted:
            if t == 0:
                return 1.0
            elif t < vis:
                return self._ease_in_out_cubic(t / vis)
            elif t <= (T - vis):
                return 1.0
            else:
                return self._ease_in_out_cubic(1.0 - ((t - (T - vis)) / vis))
        else:
            if t > 0 and t > (T - vis):
                return self._ease_in_out_cubic(1.0 - ((t - (T - vis)) / vis))
        return 0.0
    
    def _ease_in_out_cubic(self, t):
        """CSS-like ease-in-out for smooth transitions."""
        if t <= 0.0:
            return 0.0
        if t >= 1.0:
            return 1.0
        if t < 0.5:
            return 4.0 * t * t * t
        return 1.0 - ((-2.0 * t + 2.0) ** 3) / 2.0
    
    def _apply_night_overlay(self, fade_factor):
        if fade_factor <= 0.0:
            return
        
        try:
            # Get pixels as array (only for game area, not brain viz)
            game_rect = pygame.Rect(0, 0, self.screen.get_width(), 150)
            game_surface = self.screen.subsurface(game_rect)
            
            # Convert to array, invert, then blend
            pixels = pygame.surfarray.pixels3d(game_surface)
            inverted = 255 - pixels
            
            # Blend between original and inverted based on fade_factor
            blended = pixels * (1.0 - fade_factor) + inverted * fade_factor
            np.copyto(pixels, blended.astype(np.uint8))
            del pixels  # Release surface lock
        except Exception:
            # Fallback to dark overlay if pixel manipulation fails
            alpha = int(self.NIGHT_ALPHA_MAX * fade_factor)
            if alpha > 0:
                self._night_overlay.fill((0, 0, 0, alpha))
                self.screen.blit(self._night_overlay, (0, 0))
    
    def _on_game_over(self):
        """Handle game over."""
        self.games_played += 1
        if self.score > self.high_score:
            self.high_score = self.score
        
        if self.silent:
            print(f"💀 ÖLDÜ! Score: {self.score:,} | High: {self.high_score:,} | Game #{self.games_played}")
        else:
            print(f"Game {self.games_played}: Score {self.score} | High Score: {self.high_score}")
    
    def restart_game(self):
        """Restart the game."""
        self.crashed = False
        self.playing = True
        self.distance_ran = 0
        self.score = 0
        self.last_10k = 0  # Reset 10K tracker
        self.current_speed = self.config.speed
        self.running_time = 0
        
        # Reset night mode
        self.inverted = False
        self.invert_timer = 0
        self.invert_trigger = False
        
        self.horizon.reset()
        if not self.silent:
            self.distance_meter.reset()
        
        # Reset dino
        self._setup_neuro_trex()
        self.dino.update(0, TrexStatus.RUNNING)
    
    def _draw_stats(self, target_screen, offset=0):
        """Draw stats overlay - only speed."""
        font = pygame.font.Font(None, 28)
        txt = font.render(f"Speed: {self.current_speed:.1f}", True, (80, 80, 80))
        target_screen.blit(txt, (offset + 10, 10))
    
    def _draw_brain(self, target_screen):
        """Draw brain visualization."""
        brain = self.brain
        if not hasattr(brain, "last_inputs"):
            return
        
        start_y = 150
        w = target_screen.get_width()
        h = target_screen.get_height() - start_y
        
        # Background - white
        surf = pygame.Surface((w, h))
        surf.fill((255, 255, 255))
        target_screen.blit(surf, (0, start_y))
        
        # Layout - use screen width for positioning
        layer_x = [80, w // 2, w - 80]
        input_y = np.linspace(start_y + 30, start_y + h - 30, brain.input_nodes)
        hidden_y = np.linspace(start_y + 20, start_y + h - 20, brain.hidden_nodes)
        
        # Center output nodes vertically (3 nodes with 60px spacing)
        center_y = start_y + h // 2
        output_spacing = 80
        output_y = [center_y - output_spacing, center_y, center_y + output_spacing]
        
        input_labels = ["O1 TTI", "O1 Act", "O1 W", "O2 TTI", "O2 Act", "O2 W", 
                       "Speed", "Gap", "DinoY", "DinoVel", "Air", "Duck"]
        output_labels = ["Jump", "Duck", "Run"]
        
        font = pygame.font.Font(None, 18)
        
        def get_color(val):
            v = max(0, min(1, abs(val)))
            return (int(v*255), int(v*255), int(v*255))
        
        def draw_bezier(start, end, color, width=1):
            """Draw a Bezier curve between two points."""
            x1, y1 = start
            x2, y2 = end
            # Control points for smooth curve
            mid_x = (x1 + x2) // 2
            ctrl1 = (mid_x, y1)
            ctrl2 = (mid_x, y2)
            
            # Generate curve points
            points = []
            for t in range(0, 21):
                t = t / 20.0
                # Cubic Bezier formula
                x = int((1-t)**3 * x1 + 3*(1-t)**2*t * ctrl1[0] + 3*(1-t)*t**2 * ctrl2[0] + t**3 * x2)
                y = int((1-t)**3 * y1 + 3*(1-t)**2*t * ctrl1[1] + 3*(1-t)*t**2 * ctrl2[1] + t**3 * y2)
                points.append((x, y))
            
            if len(points) > 1:
                if width > 1:
                    pygame.draw.lines(target_screen, color, False, points, width)
                else:
                    pygame.draw.aalines(target_screen, color, False, points)
        
        # Draw weights with curves or lines (only strong connections)
        def draw_edge(start, end, weight):
            # Base color based on viz_color toggle
            if self.viz_color:
                # Colored mode: blue = positive, red = negative
                if weight < 0:
                    base_color = (255, 0, 0)    # Red for negative
                else:
                    base_color = (0, 0, 255)    # Blue for positive
            else:
                # Gray mode
                base_color = (80, 80, 80)
            
            # Apply opacity if enabled - NN-SVG style (linear 0-1, weak weights invisible)
            if self.viz_opacity:
                # Linear scale like NN-SVG: domain([0, 1]).range([0, 1])
                w_norm = min(1.0, abs(weight))
                if w_norm < 0.05:
                    return  # Skip drawing very weak connections
                # Blend from white background (255,255,255) to base_color based on weight
                # weak = white (invisible on white bg), strong = base_color
                color = (int(255 - (255 - base_color[0]) * w_norm),
                        int(255 - (255 - base_color[1]) * w_norm),
                        int(255 - (255 - base_color[2]) * w_norm))
            else:
                color = base_color
            
            # Apply width if enabled - FCNN style (weak = thin/invisible)
            if self.viz_width:
                # Linear scale: weight 0 -> width 0, weight 1 -> width 3
                width = int(abs(weight) * 3)
                if width < 1:
                    return  # Skip drawing very thin connections
            else:
                width = 1
            
            # Draw Bezier or straight line
            if self.viz_bezier:
                draw_bezier(start, end, color, width)
            else:
                pygame.draw.line(target_screen, color, start, end, width)
        
        # Threshold: show all when opacity OFF, filter weak when ON
        threshold = 0.05 if self.viz_opacity else 0.001
        
        for i in range(brain.input_nodes):
            for j in range(brain.hidden_nodes):
                weight = brain.weights_ih[j][i]
                if abs(weight) > threshold:
                    draw_edge((layer_x[0], int(input_y[i])), 
                             (layer_x[1], int(hidden_y[j])), weight)
        
        for j in range(brain.hidden_nodes):
            for k in range(brain.output_nodes):
                weight = brain.weights_ho[k][j]
                if abs(weight) > threshold:
                    draw_edge((layer_x[1], int(hidden_y[j])),
                             (layer_x[2], int(output_y[k])), weight)
        
        # Draw input nodes
        for i, val in enumerate(brain.last_inputs):
            pos = (layer_x[0], int(input_y[i]))
            pygame.draw.circle(target_screen, (255, 255, 255), pos, 8)
            pygame.draw.circle(target_screen, (51, 51, 51), pos, 8, 1)
            lbl = font.render(f"{input_labels[i]}:{val:.2f}", True, (0, 0, 0))
            target_screen.blit(lbl, (pos[0]-40, pos[1]-12))
        
        # Draw hidden nodes
        for i, val in enumerate(brain.last_hidden):
            pos = (layer_x[1], int(hidden_y[i]))
            pygame.draw.circle(target_screen, (255, 255, 255), pos, 6)
            pygame.draw.circle(target_screen, (51, 51, 51), pos, 6, 1)
        
        # Draw output nodes
        max_idx = np.argmax(brain.last_outputs)
        for i, val in enumerate(brain.last_outputs):
            color = (0, 255, 0) if i == max_idx else (255, 255, 255)
            pos = (layer_x[2], int(output_y[i]))
            radius = 10 + int(val * 10)
            pygame.draw.circle(target_screen, color, pos, radius)
            pygame.draw.circle(target_screen, (51, 51, 51), pos, radius, 2)
            lbl = font.render(f"{output_labels[i]} ({val:.0%})", True, (0, 0, 0))
            target_screen.blit(lbl, (pos[0]+20, pos[1]-8))


def main():
    parser = argparse.ArgumentParser(description='Watch trained NeuroDino model')
    parser.add_argument('--brain', type=str, default='best_brain.pkl',
                        help='Path to brain file (default: best_brain.pkl)')
    parser.add_argument('--fast', action='store_true',
                        help='Start in unlimited FPS mode')
    parser.add_argument('--silent', action='store_true',
                        help='No display, just run simulation and print scores')
    args = parser.parse_args()
    
    # Load brain
    if not os.path.exists(args.brain):
        print(f"Error: Brain file not found: {args.brain}")
        print("Train a model first with: python main_train.py")
        sys.exit(1)
    
    try:
        with open(args.brain, "rb") as f:
            data = pickle.load(f)
            if isinstance(data, tuple):
                brain, score = data
                print(f"✅ Loaded brain from {args.brain}")
                print(f"   Training score: {score:,}")
            else:
                brain = data
                print(f"✅ Loaded brain from {args.brain} (legacy format)")
    except Exception as e:
        print(f"Error loading brain: {e}")
        sys.exit(1)
    
    # Silent mode setup
    if args.silent:
        os.environ['SDL_VIDEODRIVER'] = 'dummy'
        os.environ['SDL_AUDIODRIVER'] = 'dummy'
        print("🔇 SILENT MODE - No display, maximum speed")
        print("   Press Ctrl+C to stop\n")
    
    # Initialize pygame
    pygame.init()
    
    if not args.silent:
        pygame.display.set_caption("NeuroDino - Model Watcher")
    
    # Game area stays fixed at 600x150, neural network area expanded
    dims = Dimensions(width=600, height=150)
    screen = pygame.display.set_mode((900, 850))  # Wider and taller for NN
    
    # Create separate surface for game at original size
    game_surface = pygame.Surface((dims.width, dims.height))
    game_offset = (900 - 600) // 2  # Center horizontally
    
    clock = pygame.time.Clock()
    
    # Create watcher - pass game_surface as the drawing target for the game
    watcher = ModelWatcher(game_surface, dims, brain, silent=args.silent)
    watcher.main_screen = screen  # Store main screen for NN drawing
    watcher.game_offset = game_offset  # Store offset for centering
    watcher.start()
    
    # FPS modes: 0=60fps, 1=unlimited, 2=turbo
    speed_mode = 0
    if args.fast:
        speed_mode = 1
    if args.silent:
        speed_mode = 2
    
    turbo_mode = False  # Runtime turbo toggle (no drawing)
    
    if not args.silent:
        print("\n🎮 Controls:")
        print("   S - Toggle speed (60 FPS → Unlimited → Turbo)")
        print("   B - Toggle Bezier curves")
        print("   W - Toggle edge width proportional to weights")
        print("   O - Toggle edge opacity proportional to weights")
        print("   C - Toggle edge color (Blue/Red vs Gray)")
        print("   R - Restart game")
        print("   Q/ESC - Quit\n")
    
    
    running = True
    last_log_time = pygame.time.get_ticks()
    frame_count = 0
    
    try:
        while running:
            # FPS control based on mode
            if speed_mode == 0:
                clock.tick(60)
            else:
                clock.tick()  # Unlimited
            
            frame_count += 1
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and not args.silent:
                    if event.key == pygame.K_q or event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_s:
                        # Cycle through 3 modes
                        speed_mode = (speed_mode + 1) % 3
                        turbo_mode = (speed_mode == 2)
                        watcher.silent = turbo_mode
                        
                        mode_names = ["60 FPS", "UNLIMITED", "🚀 TURBO (no draw)"]
                        print(f"Speed: {mode_names[speed_mode]}")
                    elif event.key == pygame.K_r:
                        watcher.restart_game()
                        print("Game restarted!")
                    elif event.key == pygame.K_b:
                        watcher.viz_bezier = not watcher.viz_bezier
                        print(f"Bezier curves: {'ON' if watcher.viz_bezier else 'OFF'}")
                    elif event.key == pygame.K_w:
                        watcher.viz_width = not watcher.viz_width
                        print(f"Edge width: {'ON' if watcher.viz_width else 'OFF'}")
                    elif event.key == pygame.K_o:
                        watcher.viz_opacity = not watcher.viz_opacity
                        print(f"Edge opacity: {'ON' if watcher.viz_opacity else 'OFF'}")
                    elif event.key == pygame.K_c:
                        watcher.viz_color = not watcher.viz_color
                        print(f"Edge color: {'Blue/Red' if watcher.viz_color else 'Gray'}")
            
            watcher.update()
            
            if not args.silent and not turbo_mode:
                pygame.display.flip()
            
            # Auto-restart on crash
            if watcher.crashed:
                if not args.silent and not turbo_mode:
                    pygame.time.wait(500)
                watcher.restart_game()

            # Logging for Turbo/Silent/Headless Modes
            if args.silent or turbo_mode:
                current_time = pygame.time.get_ticks()
                if current_time - last_log_time > 1000: # 10 seconds
                    elapsed_seconds = (current_time - last_log_time) / 1000.0
                    real_sps = int(frame_count / elapsed_seconds)
                    print(f"  [Watch] Score: {watcher.score:,} | High: {watcher.high_score:,} | SPS: {real_sps} (Sim/Sec)")
                    
                    last_log_time = current_time
                    frame_count = 0
            
            # Update title (only in display mode)
            if not args.silent and not turbo_mode:
                mode_names = ["60", "MAX", "TURBO"]
                fps_val = clock.get_fps()
                if fps_val == float('inf') or fps_val > 99999:
                    fps_text = f"MAX ({mode_names[speed_mode]})"
                else:
                    fps_text = f"{int(fps_val)} ({mode_names[speed_mode]})"
                pygame.display.set_caption(
                    f"NeuroDino | Score: {watcher.score:,} | High: {watcher.high_score:,} | FPS: {fps_text}"
                )
    except KeyboardInterrupt:
        print("\n\n⏹️  Stopped by user")
    
    pygame.quit()
    print(f"\n📊 Session Stats:")
    print(f"   Games Played: {watcher.games_played}")
    print(f"   High Score: {watcher.high_score}")


if __name__ == "__main__":
    main()
