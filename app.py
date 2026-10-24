import os
import sys
import threading
import time
import numpy as np
import gradio as gr
import pygame

# 1. Headless Config (Must be before pygame.init)
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

# 2. Path Setup
current_dir = os.path.dirname(os.path.abspath(__file__))
pydino_path = os.path.join(current_dir, "pydino")
sys.path.append(pydino_path)

# 3. Imports from existing codebase
import pickle
from dimensions import Dimensions
from watch_model import ModelWatcher
# Import necessary classes effectively re-using watch_model logic
# We need to load the brain manually

# Global State
GAME_INSTANCE = None
CURRENT_FRAME = None
CURRENT_FRAME = None
CURRENT_BRAIN_DATA = {"inputs": [], "hidden": [], "outputs": []}
BRAIN_WEIGHTS_JSON = "{}" 
MILLION_COUNTER = 0
DEATH_COUNTER = 1 # Start at Gen 1
LAST_SCORE_MILESTONE = 0
LOCK = threading.Lock()
TARGET_TPS = 60

# --- JS Visualizer Code (Global Injection) ---
# This JS will be injected once at page load via demo.load(js=...)
# It defines window.drawBrain which is called by the data stream.

def load_web_ui_asset(filename):
    asset_path = os.path.join(current_dir, "neurodino", "web-ui", filename)
    if not os.path.exists(asset_path):
        print(f"Warning: Asset not found: {asset_path}")
        return ""
    with open(asset_path, "r", encoding="utf-8") as f:
        return f.read()

VISUALIZER_JS_TEMPLATE = load_web_ui_asset("visualizer.js")

def load_brain(brain_path="best_brain.pkl"):
    """Load the best brain."""
    if not os.path.exists(brain_path):
        return None
    try:
        with open(brain_path, "rb") as f:
            data = pickle.load(f)
            if isinstance(data, tuple):
                return data[0] # brain, score
            return data # just brain
    except Exception as e:
        print(f"Error loading brain: {e}")
        return None

def game_thread_func():
    """Background thread calling the game update loop."""
    global GAME_INSTANCE, CURRENT_FRAME, CURRENT_BRAIN_DATA, TARGET_TPS, MILLION_COUNTER, DEATH_COUNTER, LAST_SCORE_MILESTONE
    
    clock = pygame.time.Clock()
    print("Game thread started.")
    
    while True:
        try:
            if GAME_INSTANCE:
                pygame.event.pump()
                GAME_INSTANCE.update()
                
                # 1M Counter Logic
                if hasattr(GAME_INSTANCE, 'score'):
                    s = GAME_INSTANCE.score
                    milestone = s // 1000000
                    if milestone > LAST_SCORE_MILESTONE:
                        MILLION_COUNTER += (milestone - LAST_SCORE_MILESTONE)
                        LAST_SCORE_MILESTONE = milestone
                
                if GAME_INSTANCE.crashed:
                    DEATH_COUNTER += 1 # Only count death here
                    LAST_SCORE_MILESTONE = 0 # Reset milestone tracker on death
                    GAME_INSTANCE.restart_game()
                
                view = pygame.surfarray.array3d(GAME_INSTANCE.screen)
                view = view.transpose([1, 0, 2])
                
                if hasattr(GAME_INSTANCE, 'brain'):
                    b = GAME_INSTANCE.brain
                    # Force flatten using numpy to handle both lists and arrays robustly
                    inputs = np.array(b.last_inputs).flatten().tolist()
                    hidden = np.array(b.last_hidden).flatten().tolist()
                    outputs = np.array(b.last_outputs).flatten().tolist()
                    
                    brain_data = {
                        "inputs": inputs,
                        "hidden": hidden,
                        "outputs": outputs,
                        "million_count": MILLION_COUNTER,
                        "death_count": DEATH_COUNTER
                    }
                else:
                    brain_data = {"inputs": [], "hidden": [], "outputs": []}

                with LOCK:
                    CURRENT_FRAME = view
                    CURRENT_BRAIN_DATA = brain_data
            
            if TARGET_TPS > 0:
                clock.tick(TARGET_TPS) 
            else:
                clock.tick()
            
        except Exception as e:
            print(f"Error in game loop: {e}")
            time.sleep(1)

def set_speed(choice):
    global TARGET_TPS
    if choice == "Yavaş (30 FPS)":
        TARGET_TPS = 30
    elif choice == "Normal (60 FPS)":
        TARGET_TPS = 60
    elif choice == "Hızlı (120 FPS)":
        TARGET_TPS = 120
    elif choice == "Maksimum (Unlimited)":
        TARGET_TPS = 0
    return f"Hız ayarlandı: {choice}"

def start_game_server():
    global GAME_INSTANCE, BRAIN_WEIGHTS_JSON
    
    pygame.init()
    brain = load_brain()
    if not brain: return False

    # Extract static weights
    import json
    weights = {
        "ih": brain.weights_ih.tolist() if hasattr(brain.weights_ih, 'tolist') else brain.weights_ih,
        "ho": brain.weights_ho.tolist() if hasattr(brain.weights_ho, 'tolist') else brain.weights_ho,
        "bh": np.array(brain.bias_h).flatten().tolist(),
        "bo": np.array(brain.bias_o).flatten().tolist()
    }
    BRAIN_WEIGHTS_JSON = json.dumps(weights)

    pygame.display.set_mode((600, 150))
    dims = Dimensions(width=600, height=150)
    game_surface = pygame.Surface((dims.width, dims.height))
    
    GAME_INSTANCE = ModelWatcher(game_surface, dims, brain, silent=False)
    GAME_INSTANCE.start()
    
    t = threading.Thread(target=game_thread_func, daemon=True)
    t.start()
    return True

def data_producer():
    """Yields (image, json_data) tuple."""
    while True:
        with LOCK:
                yield (CURRENT_FRAME, CURRENT_BRAIN_DATA)
        # Reduce sleep to almost zero (1ms) to maximize frame rate
        # Gradio will yield as fast as network permits
        
        # Adaptive Streaming: If Unlimited (0), throttle stream to 20 FPS to save CPU
        if TARGET_TPS == 0:
            time.sleep(0.05) # 20 FPS cap for visuals
        else:
            time.sleep(1.0 / TARGET_TPS) # Sync with Game Speed (e.g. 60 FPS) for smoothness

# --- Gradio UI ---
description = """
# 🦖 NeuroDino Canlı Yayın
Bu demo, **Genetik Algoritma** ile eğitilmiş bir Yapay Zeka'nın (Neural Network) canlı oynayışını gösterir.
"""

# HTML for the Canvas (No Script here)
CANVAS_HTML = load_web_ui_asset("canvas.html")

# CSS
CSS = load_web_ui_asset("style.css")

# HTML for Custom Controls
CUSTOM_CONTROLS_HTML = load_web_ui_asset("custom_controls.html")

# JS to force Light Mode
FORCE_LIGHT_JS = """
function refresh() {
    const url = new URL(window.location);
    if (url.searchParams.get('__theme') !== 'light') {
        url.searchParams.set('__theme', 'light');
        window.location.href = url.href;
    }
}
"""

with gr.Blocks(css=CSS, theme=gr.themes.Default(), js="document.body.classList.remove('dark');") as demo:
    
    with gr.Row(elem_id="main_row"):
        with gr.Column(scale=1.5, elem_id="left_game_col"):
            # Added elem_id="game_display" and removed internal height cap
            image_out = gr.Image(label="Oyun Görünümü", streaming=True, elem_id="game_display", show_label=False)
            
            # Custom Controls (Pixel Art Style)
            gr.HTML(CUSTOM_CONTROLS_HTML)
            
            with gr.Row():
                 speed_radio = gr.Radio(
                    choices=["Yavaş (30 FPS)", "Normal (60 FPS)", "Hızlı (120 FPS)", "Maksimum (Unlimited)"],
                    value="Normal (60 FPS)",
                    label="Oyun Hızı",
                    interactive=True
                )
        
        with gr.Column(scale=2):
            # Just the canvas container
            gr.HTML(CANVAS_HTML)
            
            # Hidden JSON sink
            brain_data_sink = gr.JSON(visible=False)

    # Initialize Server & Get JS
    if start_game_server():
        # Inject Javascript Global Code
        js_code = VISUALIZER_JS_TEMPLATE.replace("__WEIGHTS_PLACEHOLDER__", BRAIN_WEIGHTS_JSON)
        demo.load(None, None, None, js=js_code)
    

    
    
    # Stream Loop
    demo.load(data_producer, inputs=None, outputs=[image_out, brain_data_sink])
    
    # Trigger JS draw on data update
    brain_data_sink.change(
        fn=None,
        inputs=[brain_data_sink],
        js="(data) => { if(window.drawBrain) window.drawBrain(data); }"
    )   
    
    # Speed control connection
    status_msg = gr.Markdown(visible=False)
    speed_radio.change(fn=set_speed, inputs=speed_radio, outputs=status_msg)

if __name__ == "__main__":
    # Server already started in block definition to get weights, just launch
    demo.queue().launch(server_name="0.0.0.0", server_port=7860, share=True)
