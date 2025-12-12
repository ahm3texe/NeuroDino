
# neurodino/genetics.py
import random
import numpy as np
from typing import List, Tuple, Any
from .brain import Brain

class Genetics:
    """
    Manages population evolution: Selection, Crossover, Mutation.
    """
    def __init__(self, population_size: int):
        self.pop_size = population_size
        self.genomes: List[Brain] = []
        self.generation = 1

    def create_random_population(self, input_size: int, hidden_size: int, output_size: int) -> None:
        """Initializes the population with random brains."""
        self.genomes = []
        for _ in range(self.pop_size):
            brain = Brain(input_size, hidden_size, output_size)
            self.genomes.append(brain)

    @staticmethod
    def crossover(brain_a: Brain, brain_b: Brain) -> Brain:
        """
        UNIFORM CROSSOVER: Each gene (weight) is randomly copied from Parent A or B.
        
        Why NOT Arithmetic Crossover?
        - Averaging weights can destroy learned patterns ("neural lobotomy")
        - Parent A: +0.8 (jump), Parent B: -0.8 (don't jump) → Child: 0.0 (useless)
        - Over generations, population regresses to mean ("gray population")
        
        Uniform Crossover preserves exact gene values, just recombines them.
        """
        input_n = brain_a.input_nodes
        hidden_n = brain_a.hidden_nodes
        output_n = brain_a.output_nodes
        
        offspring = Brain(input_n, hidden_n, output_n)

        # UNIFORM CROSSOVER: Each weight randomly from A or B (no blending!)
        # Create random masks (True = from A, False = from B)
        mask_ih = np.random.random(brain_a.weights_ih.shape) < 0.5
        mask_ho = np.random.random(brain_a.weights_ho.shape) < 0.5
        mask_bh = np.random.random(brain_a.bias_h.shape) < 0.5
        mask_bo = np.random.random(brain_a.bias_o.shape) < 0.5
        
        # Apply masks: where True take from A, else from B
        offspring.weights_ih = np.where(mask_ih, brain_a.weights_ih, brain_b.weights_ih)
        offspring.weights_ho = np.where(mask_ho, brain_a.weights_ho, brain_b.weights_ho)
        offspring.bias_h = np.where(mask_bh, brain_a.bias_h, brain_b.bias_h)
        offspring.bias_o = np.where(mask_bo, brain_a.bias_o, brain_b.bias_o)

        return offspring

    @staticmethod
    def select_parent(population_data: List[Tuple[Brain, float]]) -> Brain:
        """Tournament Selection: Pick random few, return the best."""
        tournament_size = 3
        candidates = random.sample(population_data, min(len(population_data), tournament_size))
        # Sort by fitness (descending)
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]

    def evolve_population(self, old_population_data: List[Tuple[Brain, float]], 
                          generation: int = 1, best_score: int = 0) -> List[Brain]:
        """
        Creates the next generation with ADAPTIVE mutation rates.
        
        old_population_data: List of (Brain, fitness_score)
        generation: Current generation number (for decay calculation)
        best_score: Best score achieved so far (for adaptive rate)
        """
        # Sort entire population by fitness
        old_population_data.sort(key=lambda x: x[1], reverse=True)
        
        new_population = []

        # 1. Elitism: Save the champion(s)
        # Keep the absolute best unchanged to prevent regression.
        best_brain = old_population_data[0][0]
        new_population.append(best_brain.copy())
        
        if len(old_population_data) > 1:
             new_population.append(old_population_data[1][0].copy())

        # 2. Calculate ADAPTIVE Mutation Rate
        # Formula: Start high (exploration), decay over time (exploitation)
        # 
        # Base Rate: 0.20 (20% of weights mutate)
        # Decay: Exponential decay based on generation
        # Score Bonus: Lower mutation when score is high (protect good solutions)
        #
        # Rate = base * generation_decay * score_factor
        # Minimum: 0.02 (always keep some exploration)
        # Maximum: 0.25 (never go too crazy)
        
        base_rate = 0.20
        
        # Generation Decay: 0.995^gen → Gen50: 0.78, Gen100: 0.60, Gen200: 0.37
        generation_decay = 0.995 ** generation
        
        # Score Factor: High score = lower mutation (protect the genius)
        # At score 0: factor = 1.0
        # At score 1000: factor = 0.67
        # At score 5000: factor = 0.33
        score_factor = 1.0 / (1.0 + best_score / 2000.0)
        
        # Final adaptive rate with bounds
        adaptive_rate = base_rate * generation_decay * score_factor
        adaptive_rate = max(0.05, min(0.25, adaptive_rate))  # Clamp to [0.05, 0.25]
        
        # 3. Crossover & Mutation with adaptive rate
        while len(new_population) < self.pop_size:
            parent_a = self.select_parent(old_population_data)
            parent_b = self.select_parent(old_population_data)
            
            child = self.crossover(parent_a, parent_b)
            child.mutate(adaptive_rate)
            new_population.append(child)

        self.genomes = new_population
        # Note: Generation counter managed by NeuroRunner, not here
        return new_population
