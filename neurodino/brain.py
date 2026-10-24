
# neurodino/brain.py
import numpy as np

class Brain:
    """
    A simple Feed-Forward Neural Network (MLP).
    Input -> Hidden (Tanh) -> Output (Softmax)
    """
    def __init__(self, input_nodes: int, hidden_nodes: int, output_nodes: int):
        self.input_nodes = input_nodes
        self.hidden_nodes = hidden_nodes
        self.output_nodes = output_nodes

        # Xavier/Glorot Initialization (Optimal for Tanh)
        # Limit = sqrt(6 / (fan_in + fan_out))
        
        # Input -> Hidden
        limit_ih = np.sqrt(6 / (self.input_nodes + self.hidden_nodes))
        self.weights_ih = np.random.uniform(-limit_ih, limit_ih, (self.hidden_nodes, self.input_nodes))
        
        # Hidden -> Output
        limit_ho = np.sqrt(6 / (self.hidden_nodes + self.output_nodes))
        self.weights_ho = np.random.uniform(-limit_ho, limit_ho, (self.output_nodes, self.hidden_nodes))

        # Biases: Initialize symmetrically for Tanh (-0.5 to 0.5)
        self.bias_h = np.random.uniform(-0.5, 0.5, (self.hidden_nodes, 1))
        self.bias_o = np.random.uniform(-0.5, 0.5, (self.output_nodes, 1))
        
        # Initialize visualization attributes to prevent AttributeError on first frame
        self.last_inputs = np.zeros(input_nodes)
        self.last_hidden = np.zeros(hidden_nodes)
        self.last_outputs = np.zeros(output_nodes)

    def predict(self, input_array: list) -> np.ndarray:
        """
        Forward propagation.
        Returns probability distribution for actions.
        """
        # Store for visualization
        self.last_inputs = np.array(input_array)
        
        # Convert list to numpy array (column vector)
        inputs = np.array(input_array).reshape(-1, 1)

        # Input -> Hidden
        hidden = np.dot(self.weights_ih, inputs) # W_ih * x
        hidden = hidden + self.bias_h # b_h
        hidden = np.tanh(hidden) # tanh(...)
        self.last_hidden = hidden.flatten() # Store for viz

        # Hidden -> Output
        output = np.dot(self.weights_ho, hidden) # W_ho * h
        output = output + self.bias_o # b_o
        output = self.softmax(output) # softmax(...)
        self.last_outputs = output.flatten() # Store for viz

        return output.flatten()

    def copy(self) -> 'Brain':
        """Deep copy for genetics."""
        new_brain = Brain(self.input_nodes, self.hidden_nodes, self.output_nodes)
        new_brain.weights_ih = self.weights_ih.copy()
        new_brain.weights_ho = self.weights_ho.copy()
        new_brain.bias_h = self.bias_h.copy()
        new_brain.bias_o = self.bias_o.copy()
        return new_brain

    def mutate(self, rate: float):
        """
        Adaptive mutation with intelligent parameter tweaking.
        
        Features:
        - Reduced shock mutation (3% instead of 10%)
        - Gaussian nudge scales with mutation rate (gentler when rate is low)
        - Preserves learned patterns while allowing exploration
        """
        # Adaptive sigma: When mutation rate is low, nudges are gentler
        # rate=0.20 → sigma=0.15 (standard)
        # rate=0.05 → sigma=0.08 (gentle)
        # rate=0.02 → sigma=0.05 (very gentle)
        sigma = 0.05 + (rate * 0.5)  # Range: 0.05 to 0.175
        
        # Increased shock rate: 8% to allow more exploration
        # This helps escape local optima while still preserving most good solutions
        shock_rate = 0.08
        
        def mutate_val(val):
            if np.random.random() < rate:
                # Rare "Shock" mutation for escaping local optima
                if np.random.random() < shock_rate:
                    return np.random.uniform(-1, 1)
                
                # Adaptive Gaussian nudge (gentler over time)
                return val + np.random.normal(0, sigma)
            return val
        
        v_mutate = np.vectorize(mutate_val)

        self.weights_ih = v_mutate(self.weights_ih)
        self.weights_ho = v_mutate(self.weights_ho)
        self.bias_h = v_mutate(self.bias_h)
        self.bias_o = v_mutate(self.bias_o)

    # Activation functions


    def softmax(self, x):
        e_x = np.exp(x - np.max(x))
        return e_x / e_x.sum(axis=0)
