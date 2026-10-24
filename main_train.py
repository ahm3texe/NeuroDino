import os
import sys
import argparse
import math
import numpy as np
import pygame

# Add pydino directory to sys.path so that internal imports (e.g. 'from constants import FPS') work
pydino_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pydino")
sys.path.append(pydino_path)

from dimensions import Dimensions
from neurodino.neuro_runner import NeuroRunner
from pydino.trex import Status

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='NeuroDino Training')
    parser.add_argument('--headless', action='store_true', 
                        help='Run in headless mode (no display, maximum speed)')
    args = parser.parse_args()
    
    # Headless mode setup
    if args.headless:
        os.environ['SDL_VIDEODRIVER'] = 'dummy'
        os.environ['SDL_AUDIODRIVER'] = 'dummy'
        print("🚀 HEADLESS MODE - No display, maximum training speed")
    
    pygame.init()
    
    if not args.headless:
        pygame.display.set_caption("NeuroDino — Training (Generation 1)")
    
    # Standard Dino dimensions
    dims = Dimensions(width=600, height=150)
    
    # Window size: Game (150) + Dashboard (500) = 650 (Expanded for 32 Neurons)
    screen = pygame.display.set_mode((dims.width, 650))
    clock = pygame.time.Clock()
    
    # Headless mode: unlimited FPS, no display updates
    if args.headless:
        target_fps = 0  # Unlimited
    else:
        target_fps = 60  # Default to 60 FPS (Standard)
    
    fps_modes = [60, 480, 0, -1]  # Visual, Fast, Unlimited, Headless Train
    current_fps_index = 0
    
    # Note: NeuroRunner(target_fps=60) means physics runs at 16ms steps.
    # If we tick at 60, it's 1x speed. If we tick at 480, it's 8x speed (Training).
    # If we tick at 0, it's unlimited (Maximum hardware speed).
    runner = NeuroRunner(screen, dims, pop_size=50, target_fps=60)
    runner.start()  # Start playing state
    if args.headless:
        # Nothing is shown, so skip drawing the game and the brain every step;
        # the simulation is unaffected. Drawing to the dummy display kept
        # --headless at a few hundred steps per second.
        runner.set_rendering(False)
    
    running = True
    last_gen = 0
    last_log_time = pygame.time.get_ticks()
    frame_count = 0 
    
    while running:
        # Unlimited mode: don't sleep
        if target_fps == 0 or target_fps == -1:
            clock.tick()
        else:
            clock.tick(target_fps)
        
        frame_count += 1
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_s:
                # Cycle through FPS modes
                current_fps_index = (current_fps_index + 1) % len(fps_modes)
                target_fps = fps_modes[current_fps_index]
                
                if target_fps == 60:
                    print("Speed: Normal (60 FPS)")
                elif target_fps == 480:
                    print("Speed: Fast (480 FPS)")
                elif target_fps == 0:
                    print("Speed: UNLIMITED (Max Hardware)")
                else:
                    print("Speed: HEADLESS SIMULATION (No Rendering)")

                # Apply rendering state
                if target_fps == -1:
                    runner.set_rendering(False)
                    # For logic, we behave like unlimited
                else:
                    runner.set_rendering(True)
        
        runner.update()
        
        # Headless mode (CLI arg or Runtime Toggle): skip display updates
        if args.headless or target_fps == -1:
            # Progress indicator every 10 seconds (Runtime Feedback)
            current_time = pygame.time.get_ticks()
            if current_time - last_log_time > 1000  : # 10 seconds
                elapsed_seconds = (current_time - last_log_time) / 1000.0
                real_fps = int(frame_count / elapsed_seconds)
                
                print(f"  [Progress] Gen {runner.generation} | Best: {runner.best_global_score} | SPS: {real_fps} (Sim/Sec)")
                
                last_log_time = current_time
                frame_count = 0
        else:
            pygame.display.flip()
            
            # Display FPS mode in title
            try:
                raw_fps = clock.get_fps()
                safe_fps = int(raw_fps) if not math.isinf(raw_fps) else 99999
            except OverflowError:
                safe_fps = 99999

            if target_fps == 0:
                fps_text = f"UNLIMITED ({safe_fps})"
            elif target_fps == -1:
                fps_text = f"HEADLESS ({safe_fps})"
            else:
                fps_text = str(target_fps)
            
            # Count alive using Status.CRASHED
            alive_count = sum(1 for d in runner.population if d.status != Status.CRASHED)
            
            pygame.display.set_caption(f"NeuroDino — Gen {runner.generation} | Alive: {alive_count} | FPS: {fps_text}")

    pygame.quit()

if __name__ == "__main__":
    main()
