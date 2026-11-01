import pygame
import random
import math

# Configurações iniciais
WIDTH, HEIGHT = 1000, 700
FPS = 60

# Cores e Constantes
BLACK = (20, 20, 20)
GREEN = (50, 200, 50)   # Comida

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Simulador de Vida - Evolução e Ecossistema")
clock = pygame.time.Clock()

# Definição das 6 Espécies
# ID: {nome, cor, dieta (lista de IDs que come, ou 'food'), velocidade_base, raio_base, visão_base}
SPECIES_DEFS = {
    0: {"name": "Herbívoro Veloz", "color": (0, 255, 255),   "diet": ["food"], "base_speed": 3.5, "base_radius": 4, "base_vision": 100},
    1: {"name": "Herbívoro Tanque", "color": (255, 255, 0),  "diet": ["food"], "base_speed": 1.5, "base_radius": 8, "base_vision": 80},
    2: {"name": "Herbívoro Comum", "color": (255, 105, 180), "diet": ["food"], "base_speed": 2.2, "base_radius": 6, "base_vision": 120},
    3: {"name": "Carnívoro Caçador", "color": (255, 165, 0), "diet": [0, 1, 2], "base_speed": 2.8, "base_radius": 7, "base_vision": 150},
    4: {"name": "Predador Apex", "color": (255, 50, 50),     "diet": [0, 1, 2, 3, 5], "base_speed": 2.5, "base_radius": 10, "base_vision": 200},
    5: {"name": "Onívoro Oportunista", "color": (255, 255, 255), "diet": ["food", 0], "base_speed": 2.0, "base_radius": 5, "base_vision": 110}
}

class Food:
    def __init__(self):
        self.x = random.randint(10, WIDTH - 10)
        self.y = random.randint(10, HEIGHT - 10)
        self.radius = 3

    def draw(self, surface):
        pygame.draw.circle(surface, GREEN, (self.x, self.y), self.radius)


class Agent:
    def __init__(self, x, y, species_id, inherited_traits=None):
        self.x = x
        self.y = y
        self.species_id = species_id
        
        # Carrega propriedades da espécie
        defs = SPECIES_DEFS[species_id]
        self.color = defs["color"]
        self.diet = defs["diet"]
        
        # Evolução e Genética
        if inherited_traits:
            # Sofre mutação (Até 10% para mais ou para menos)
            mutation_rate = 0.1
            self.speed = max(0.5, inherited_traits['speed'] * random.uniform(1 - mutation_rate, 1 + mutation_rate))
            self.radius = max(3.0, inherited_traits['radius'] * random.uniform(1 - mutation_rate, 1 + mutation_rate))
            self.vision = max(50.0, inherited_traits['vision'] * random.uniform(1 - mutation_rate, 1 + mutation_rate))
        else:
            # Status base se for gerado "do nada"
            self.speed = defs["base_speed"]
            self.radius = defs["base_radius"]
            self.vision = defs["base_vision"]
        
        # O custo de energia depende do corpo! Mais rápido/maior/visão longa = gasta mais energia
        # Balanço matemático para evitar que morram em 1 segundo
        self.energy_drain = (self.speed * self.radius * self.vision) / 5000.0
        
        self.energy = 100
        self.max_energy = 200
        self.reproduce_threshold = 160
        self.dead = False

    def distance_to(self, other):
        return math.hypot(self.x - other.x, self.y - other.y)

    def move_towards(self, target_x, target_y):
        dx = target_x - self.x
        dy = target_y - self.y
        dist = math.hypot(dx, dy)
        if dist > 0:
            self.x += (dx / dist) * self.speed
            self.y += (dy / dist) * self.speed

    def wander(self):
        self.x += random.uniform(-self.speed, self.speed)
        self.y += random.uniform(-self.speed, self.speed)
        self.x = max(self.radius, min(WIDTH - self.radius, self.x))
        self.y = max(self.radius, min(HEIGHT - self.radius, self.y))

    def update(self, foods, agents):
        self.energy -= self.energy_drain
        if self.energy <= 0:
            self.dead = True
            return

        target = None
        min_dist = self.vision

        # Procurar Comida (se for parte da dieta)
        if "food" in self.diet:
            for food in foods:
                dist = self.distance_to(food)
                if dist < min_dist:
                    min_dist = dist
                    target = food

        # Procurar Presas (outros agentes que estejam na dieta)
        for agent in agents:
            if not agent.dead and agent.species_id in self.diet and agent != self:
                dist = self.distance_to(agent)
                if dist < min_dist:
                    min_dist = dist
                    target = agent

        # Tentar comer o alvo
        if target:
            if min_dist < self.radius + target.radius:
                if isinstance(target, Food):
                    foods.remove(target)
                    self.energy = min(self.max_energy, self.energy + 30)
                else:
                    target.dead = True
                    # Carnívoros ganham mais energia comendo outros agentes
                    self.energy = min(self.max_energy, self.energy + 80)
                target = None
            else:
                self.move_towards(target.x, target.y)
        else:
            self.wander()

    def draw(self, surface):
        # Corpo
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), int(self.radius))
        
        # Linha de visão (opcional, desenhada bem fraca só para ver o alcance evolutivo de 1 agente aleatório)
        # Pode pesar no processamento se ativar para todos, deixamos desligado por padrão.
        # pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), int(self.vision), 1)

def main():
    # Inicializa alimentos e agentes
    foods = [Food() for _ in range(80)]
    agents = []
    
    # Colocar 5 indivíduos de cada uma das 6 espécies inicialmente
    for species_id in SPECIES_DEFS.keys():
        for _ in range(5):
            agents.append(Agent(random.randint(50, WIDTH-50), random.randint(50, HEIGHT-50), species_id))

    font = pygame.font.SysFont(None, 22)
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # Gerar comida constante (ecossistema base)
        if random.random() < 0.25: # 25% de chance de nascer comida por frame
            foods.append(Food())

        new_agents = []
        species_count = {s_id: 0 for s_id in SPECIES_DEFS.keys()}

        # Atualizar todos os agentes
        for agent in agents:
            agent.update(foods, agents)
            
            if not agent.dead:
                species_count[agent.species_id] += 1
                
                # Reprodução (Passando a Genética)
                if agent.energy > agent.reproduce_threshold:
                    agent.energy /= 2
                    traits = {
                        'speed': agent.speed,
                        'radius': agent.radius,
                        'vision': agent.vision
                    }
                    new_agents.append(Agent(agent.x + random.randint(-15, 15), 
                                            agent.y + random.randint(-15, 15), 
                                            agent.species_id, traits))

        # Atualiza a lista de agentes (remove mortos, adiciona nascidos)
        agents.extend(new_agents)
        agents = [a for a in agents if not a.dead]

        # REGRAS DO DEUS DO ECOSSISTEMA: NUNCA DEIXE UMA ESPÉCIE SUMIR
        for species_id, count in species_count.items():
            if count == 0:
                # Nasce um indivíduo base novo no meio do mapa para reviver a espécie
                agents.append(Agent(WIDTH//2 + random.randint(-100, 100), 
                                    HEIGHT//2 + random.randint(-100, 100), 
                                    species_id))

        # Desenho
        screen.fill(BLACK)
        
        for food in foods:
            food.draw(screen)
            
        for agent in agents:
            agent.draw(screen)

        # UI e Informações
        y_offset = 10
        for species_id, count in species_count.items():
            name = SPECIES_DEFS[species_id]["name"]
            color = SPECIES_DEFS[species_id]["color"]
            text = font.render(f"{name}: {count}", True, color)
            screen.blit(text, (10, y_offset))
            y_offset += 25
            
        # Comida total
        text_food = font.render(f"Plantas: {len(foods)}", True, GREEN)
        screen.blit(text_food, (10, y_offset))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()

if __name__ == "__main__":
    main()
