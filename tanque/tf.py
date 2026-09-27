import math
import random
import sys
import pygame

# --- PARÂMETROS DA FÓRMULA ---
NUM_MAX_PARTICULAS = 800
TAXA_EMISSAO = 2
ORDEM = 0.75  # Coesão ao fundir
CAOS = 0.15  # Turbulência / Força de afastamento
TEMPO_STEP = 0.15

# Dimensões da Caixa 3D
TAM_CAIXA = 100
FUNDO_CAIXA = -100
TOPO_CAIXA = 100

# --- CONTROLO DA CÂMARA (ÓRBITA) ---
cam_rot_y = 45.0  # Rotação horizontal (graus)
cam_rot_x = 30.0  # Rotação vertical (graus)
cam_distancia = 450.0  # Zoom inicial

WIDTH, HEIGHT = 800, 600
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption(
    "Fluido 3D Interativo (Arrasta com o Rato para Rodar | Scroll para Zoom)"
)
clock = pygame.time.Clock()


class Particula3D:

    def __init__(self, x=None, y=None, z=None, raio=3.0):
        self.x = x if x is not None else random.uniform(-10, 10)
        self.y = y if y is not None else TOPO_CAIXA
        self.z = z if z is not None else random.uniform(-10, 10)

        self.vx = random.uniform(-1, 1) * CAOS * 3
        self.vy = random.uniform(-3, -1)
        self.vz = random.uniform(-1, 1) * CAOS * 3

        self.raio = raio
        self.viva = True

    def atualizar(self, outras_particulas):
        if not self.viva:
            return

        # Gravidade + Caos
        self.vy -= 0.6
        self.vx += random.uniform(-1, 1) * CAOS
        self.vz += random.uniform(-1, 1) * CAOS

        nx = self.x + self.vx * TEMPO_STEP * 10
        ny = self.y + self.vy * TEMPO_STEP * 10
        nz = self.z + self.vz * TEMPO_STEP * 10

        # --- FUSÃO OU AFASTAMENTO COM OUTRAS PARTÍCULAS ---
        for p in outras_particulas:
            if p is self or not p.viva:
                continue

            dx = nx - p.x
            dy = ny - p.y
            dz = nz - p.z
            dist_sq = dx * dx + dy * dy + dz * dz
            dist_min = self.raio + p.raio

            if 0 < dist_sq < dist_min * dist_min:
                dist = math.sqrt(dist_sq)

                dvx = self.vx - p.vx
                dvy = self.vy - p.vy
                dvz = self.vz - p.vz
                vel_relativa = math.sqrt(dvx * dvx + dvy * dvy + dvz * dvz)

                # Condição de FUSÃO: impacto lento
                if vel_relativa < 2.5 and self.raio < 12.0:
                    m1 = self.raio**3
                    m2 = p.raio**3
                    m_total = m1 + m2

                    self.vx = (self.vx * m1 + p.vx * m2) / m_total
                    self.vy = (self.vy * m1 + p.vy * m2) / m_total
                    self.vz = (self.vz * m1 + p.vz * m2) / m_total

                    self.raio = (m_total) ** (1 / 3)
                    p.viva = False
                else:
                    # Condição de AFASTAMENTO / REPULSÃO
                    overlap = dist_min - dist
                    nx += (dx / dist) * overlap * 0.6
                    ny += (dy / dist) * overlap * 0.6
                    nz += (dz / dist) * overlap * 0.6

                    self.vx = (self.vx + (dx / dist) * CAOS * 10) * ORDEM
                    self.vy = (self.vy + (dy / dist) * CAOS * 10) * ORDEM
                    self.vz = (self.vz + (dz / dist) * CAOS * 10) * ORDEM

        # --- Limites das Paredes ---
        if ny - self.raio < FUNDO_CAIXA:
            ny = FUNDO_CAIXA + self.raio
            self.vy *= -ORDEM * 0.2
            self.vx *= ORDEM
            self.vz *= ORDEM

        if abs(nx) + self.raio > TAM_CAIXA:
            nx = TAM_CAIXA - self.raio if nx > 0 else -TAM_CAIXA + self.raio
            self.vx *= -ORDEM

        if abs(nz) + self.raio > TAM_CAIXA:
            nz = TAM_CAIXA - self.raio if nz > 0 else -TAM_CAIXA + self.raio
            self.vz *= -ORDEM

        self.x, self.y, self.z = nx, ny, nz

    def projetar(self, rot_x, rot_y, distancia):
        # Matriz de rotação 3D Completa (Y e X)
        rad_y = math.radians(rot_y)
        rad_x = math.radians(rot_x)

        # Rotação Eixo Y
        x1 = self.x * math.cos(rad_y) - self.z * math.sin(rad_y)
        z1 = self.x * math.sin(rad_y) + self.z * math.cos(rad_y)
        y1 = self.y

        # Rotação Eixo X
        y2 = y1 * math.cos(rad_x) - z1 * math.sin(rad_x)
        z2 = y1 * math.sin(rad_x) + z1 * math.cos(rad_x) + distancia

        focal = 350
        escala = focal / max(1, z2)
        px = int(WIDTH / 2 + x1 * escala)
        py = int(HEIGHT / 2 - y2 * escala)
        tam = max(2, int(self.raio * 1.5 * escala))
        return px, py, tam, z2


def desenhar_caixa_3d(screen, rot_x, rot_y, distancia):
    vertices = []
    for x in [-TAM_CAIXA, TAM_CAIXA]:
        for y in [FUNDO_CAIXA, TOPO_CAIXA]:
            for z in [-TAM_CAIXA, TAM_CAIXA]:
                rad_y = math.radians(rot_y)
                rad_x = math.radians(rot_x)

                x1 = x * math.cos(rad_y) - z * math.sin(rad_y)
                z1 = x * math.sin(rad_y) + z * math.cos(rad_y)
                y1 = y

                y2 = y1 * math.cos(rad_x) - z1 * math.sin(rad_x)
                z2 = y1 * math.sin(rad_x) + z1 * math.cos(rad_x) + distancia

                escala = 350 / max(1, z2)
                px = int(WIDTH / 2 + x1 * escala)
                py = int(HEIGHT / 2 - y2 * escala)
                vertices.append((px, py))

    arestas = [
        (0, 1),
        (0, 2),
        (0, 4),
        (1, 3),
        (1, 5),
        (2, 3),
        (2, 6),
        (3, 7),
        (4, 5),
        (4, 6),
        (5, 7),
        (6, 7),
    ]

    for p1, p2 in arestas:
        pygame.draw.line(screen, (60, 70, 80), vertices[p1], vertices[p2], 1)


particulas = []
arrastando = False
pos_anterior = (0, 0)

# Loop Principal
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        # Rotação da Câmara com o Rato
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Botão Esquerdo
                arrastando = True
                pos_anterior = event.pos
            elif event.button == 4:  # Scroll Up (Zoom In)
                cam_distancia = max(200.0, cam_distancia - 20.0)
            elif event.button == 5:  # Scroll Down (Zoom Out)
                cam_distancia = min(800.0, cam_distancia + 20.0)

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                arrastando = False

        elif event.type == pygame.MOUSEMOTION:
            if arrastando:
                dx = event.pos[0] - pos_anterior[0]
                dy = event.pos[1] - pos_anterior[1]

                cam_rot_y += dx * 0.5
                cam_rot_x = max(-80.0, min(80.0, cam_rot_x + dy * 0.5))
                pos_anterior = event.pos

    # Emitir novas partículas
    if len(particulas) < NUM_MAX_PARTICULAS:
        for _ in range(TAXA_EMISSAO):
            particulas.append(Particula3D())

    screen.fill((15, 18, 22))

    desenhar_caixa_3d(screen, cam_rot_x, cam_rot_y, cam_distancia)

    # Remover partículas fundidas
    particulas = [p for p in particulas if p.viva]

    desenhar_lista = []
    for p in particulas:
        p.atualizar(particulas)
        px, py, tam, z_depth = p.projetar(cam_rot_x, cam_rot_y, cam_distancia)
        desenhar_lista.append((z_depth, px, py, tam))

    # Ordenar por profundidade (Z-buffer)
    desenhar_lista.sort(key=lambda item: item[0], reverse=True)

    # Desenhar Esferas Cinzentas com Reflexo
    for _, px, py, tam in desenhar_lista:
        # Esfera
        pygame.draw.circle(screen, (120, 125, 135), (px, py), tam)
        pygame.draw.circle(screen, (50, 55, 65), (px, py), tam, 1)

        # Highlight 3D (Reflexo)
        if tam >= 3:
            off_x = int(px - tam * 0.3)
            off_y = int(py - tam * 0.3)
            raio_reflexo = max(1, int(tam * 0.35))
            pygame.draw.circle(
                screen, (245, 250, 255), (off_x, off_y), raio_reflexo
            )

    pygame.display.flip()
    clock.tick(60)