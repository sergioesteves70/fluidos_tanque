import math
import os
import random
import sys
import psutil
import pygame

# --- PARÂMETROS DA SIMULAÇÃO ---
NUM_MAX_PARTICULAS = 800
TAXA_EMISSAO = 2
CAOS = 0.05
TEMPO_STEP = 0.1

# --- ELASTICIDADE / RIGIDEZ ---
RIGIDEZ = 12.0
AMORTECIMENTO = 4.5
VEL_MAX = 25.0

# Dimensões da Caixa 3D
TAM_CAIXA = 100
FUNDO_CAIXA = -100
TOPO_CAIXA = 100

# --- CONTROLO DA CÂMARA ---
cam_rot_y = 45.0
cam_rot_x = 30.0
cam_distancia = 450.0

WIDTH, HEIGHT = 800, 600
pygame.init()
pygame.font.init()

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Fluido 3D - Gravidade 3D Corrigida")
clock = pygame.time.Clock()

FONTE = pygame.font.SysFont("Consolas", 14)


def obter_uso_memoria_mb():
    """Retorna o uso de memória RAM (RSS) do processo atual em MB."""
    processo = psutil.Process(os.getpid())
    return processo.memory_info().rss / (1024 * 1024)


def calcular_vetor_gravidade_local(rot_x, rot_y, g_mag=9.8):
    """
    Transforma a gravidade global do ecrã (0, -g_mag, 0) para o referencial
    local interno (X, Y, Z) da caixa usando a matriz de rotação inversa exata.
    """
    rad_x = math.radians(rot_x)
    rad_y = math.radians(rot_y)

    # Decomposição exata nos eixos locais da caixa
    gx = -g_mag * math.sin(rad_x) * math.sin(rad_y)
    gy = -g_mag * math.cos(rad_x)
    gz = g_mag * math.sin(rad_x) * math.cos(rad_y)

    return gx, gy, gz


class Particula3D:

    def __init__(self, x=None, y=None, z=None, raio=3.5):
        self.x = x if x is not None else random.uniform(-10, 10)
        self.y = y if y is not None else (TOPO_CAIXA - 10)
        self.z = z if z is not None else random.uniform(-10, 10)

        self.vx = random.uniform(-0.5, 0.5)
        self.vy = random.uniform(-1.0, 0.0)
        self.vz = random.uniform(-0.5, 0.5)

        self.raio = raio
        self.viva = True

    def atualizar(self, outras_particulas, gx, gy, gz):
        if not self.viva:
            return

        # 1. Forças Principais: Gravidade Local + Caos
        fx = gx + random.uniform(-1, 1) * CAOS
        fy = gy + random.uniform(-1, 1) * CAOS
        fz = gz + random.uniform(-1, 1) * CAOS

        # 2. Interação entre Partículas
        for p in outras_particulas:
            if p is self or not p.viva:
                continue

            dx = self.x - p.x
            dy = self.y - p.y
            dz = self.z - p.z
            dist_sq = dx * dx + dy * dy + dz * dz
            dist_min = self.raio + p.raio

            if 0 < dist_sq < dist_min * dist_min:
                dist = math.sqrt(dist_sq)
                nx_dir, ny_dir, nz_dir = dx / dist, dy / dist, dz / dist

                compressao = dist_min - dist

                dvx = self.vx - p.vx
                dvy = self.vy - p.vy
                dvz = self.vz - p.vz

                # Fusão
                vel_relativa = math.sqrt(dvx * dvx + dvy * dvy + dvz * dvz)
                if vel_relativa < 0.8 and compressao > dist_min * 0.6 and self.raio < 10.0:
                    m1 = self.raio**3
                    m2 = p.raio**3
                    m_total = m1 + m2
                    self.vx = (self.vx * m1 + p.vx * m2) / m_total
                    self.vy = (self.vy * m1 + p.vy * m2) / m_total
                    self.vz = (self.vz * m1 + p.vz * m2) / m_total
                    self.raio = (m_total) ** (1 / 3)
                    p.viva = False
                    continue

                # Mola e Amortecimento
                f_mola = RIGIDEZ * compressao
                vel_normal = dvx * nx_dir + dvy * ny_dir + dvz * nz_dir
                f_damp = AMORTECIMENTO * vel_normal

                f_total = f_mola - f_damp
                fx += nx_dir * f_total
                fy += ny_dir * f_total
                fz += nz_dir * f_total

        # 3. Integração de Velocidades
        self.vx += fx * TEMPO_STEP
        self.vy += fy * TEMPO_STEP
        self.vz += fz * TEMPO_STEP

        # Limite de Velocidade
        vel_mag = math.sqrt(self.vx**2 + self.vy**2 + self.vz**2)
        if vel_mag > VEL_MAX:
            escala = VEL_MAX / vel_mag
            self.vx *= escala
            self.vy *= escala
            self.vz *= escala

        # 4. Atualização Homogénea das Posições
        nx = self.x + self.vx * TEMPO_STEP
        ny = self.y + self.vy * TEMPO_STEP
        nz = self.z + self.vz * TEMPO_STEP

        # 5. Colisões Uniformes com as 6 Paredes
        ATRITO = 0.82
        RESTITUICAO = -0.2

        # Eixo Y (Topo / Fundo)
        if ny - self.raio < FUNDO_CAIXA:
            ny = FUNDO_CAIXA + self.raio
            self.vy *= RESTITUICAO
            self.vx *= ATRITO
            self.vz *= ATRITO
        elif ny + self.raio > TOPO_CAIXA:
            ny = TOPO_CAIXA - self.raio
            self.vy *= RESTITUICAO
            self.vx *= ATRITO
            self.vz *= ATRITO

        # Eixo X (Esquerda / Direita)
        if nx - self.raio < -TAM_CAIXA:
            nx = -TAM_CAIXA + self.raio
            self.vx *= RESTITUICAO
            self.vy *= ATRITO
            self.vz *= ATRITO
        elif nx + self.raio > TAM_CAIXA:
            nx = TAM_CAIXA - self.raio
            self.vx *= RESTITUICAO
            self.vy *= ATRITO
            self.vz *= ATRITO

        # Eixo Z (Frente / Fundo)
        if nz - self.raio < -TAM_CAIXA:
            nz = -TAM_CAIXA + self.raio
            self.vz *= RESTITUICAO
            self.vx *= ATRITO
            self.vy *= ATRITO
        elif nz + self.raio > TAM_CAIXA:
            nz = TAM_CAIXA - self.raio
            self.vz *= RESTITUICAO
            self.vx *= ATRITO
            self.vy *= ATRITO

        self.x, self.y, self.z = nx, ny, nz

    def projetar(self, rot_x, rot_y, distancia):
        rad_y = math.radians(rot_y)
        rad_x = math.radians(rot_x)

        x1 = self.x * math.cos(rad_y) - self.z * math.sin(rad_y)
        z1 = self.x * math.sin(rad_y) + self.z * math.cos(rad_y)
        y1 = self.y

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
        (0, 1), (0, 2), (0, 4), (1, 3), (1, 5), (2, 3),
        (2, 6), (3, 7), (4, 5), (4, 6), (5, 7), (6, 7)
    ]

    for p1, p2 in arestas:
        pygame.draw.line(screen, (60, 70, 80), vertices[p1], vertices[p2], 1)


def desenhar_painel_info(screen, fps, num_partic, memoria_mb, gx, gy, gz):
    linhas = [
        f"FPS: {fps:.1f}",
        f"Particulas: {num_partic} / {NUM_MAX_PARTICULAS}",
        f"Memoria RAM: {memoria_mb:.1f} MB",
        f"Gravidade (X,Y,Z): ({gx:.2f}, {gy:.2f}, {gz:.2f})",
    ]

    largura_max = max(FONTE.size(linha)[0] for linha in linhas) + 20
    altura = len(linhas) * 20 + 10

    hud_surface = pygame.Surface((largura_max, altura), pygame.SRCALPHA)
    hud_surface.fill((10, 15, 20, 200))
    pygame.draw.rect(hud_surface, (0, 200, 255, 150), hud_surface.get_rect(), 1)

    for i, linha in enumerate(linhas):
        texto = FONTE.render(linha, True, (220, 230, 240))
        hud_surface.blit(texto, (10, 5 + i * 20))

    screen.blit(hud_surface, (10, 10))


particulas = []
arrastando = False
pos_anterior = (0, 0)

# Loop Principal
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                arrastando = True
                pos_anterior = event.pos
            elif event.button == 4:
                cam_distancia = max(200.0, cam_distancia - 20.0)
            elif event.button == 5:
                cam_distancia = min(800.0, cam_distancia + 20.0)

        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                arrastando = False

        elif event.type == pygame.MOUSEMOTION:
            if arrastando:
                dx = event.pos[0] - pos_anterior[0]
                dy = event.pos[1] - pos_anterior[1]

                cam_rot_y += dx * 0.5
                cam_rot_x = max(-85.0, min(85.0, cam_rot_x + dy * 0.5))
                pos_anterior = event.pos

    # Emissão
    if len(particulas) < NUM_MAX_PARTICULAS:
        for _ in range(TAXA_EMISSAO):
            particulas.append(Particula3D())

    # Decomposição uniforme da força de gravidade
    gx, gy, gz = calcular_vetor_gravidade_local(cam_rot_x, cam_rot_y, g_mag=9.8)

    screen.fill((15, 18, 22))

    desenhar_caixa_3d(screen, cam_rot_x, cam_rot_y, cam_distancia)

    particulas = [p for p in particulas if p.viva]

    desenhar_lista = []
    for p in particulas:
        p.atualizar(particulas, gx, gy, gz)
        px, py, tam, z_depth = p.projetar(cam_rot_x, cam_rot_y, cam_distancia)
        desenhar_lista.append((z_depth, px, py, tam))

    # Ordenar por profundidade (Z-buffer)
    desenhar_lista.sort(key=lambda item: item[0], reverse=True)

    for _, px, py, tam in desenhar_lista:
        pygame.draw.circle(screen, (120, 125, 135), (px, py), tam)
        pygame.draw.circle(screen, (50, 55, 65), (px, py), tam, 1)

        if tam >= 3:
            off_x = int(px - tam * 0.3)
            off_y = int(py - tam * 0.3)
            raio_reflexo = max(1, int(tam * 0.35))
            pygame.draw.circle(screen, (245, 250, 255), (off_x, off_y), raio_reflexo)

    fps_atual = clock.get_fps()
    memoria_mb = obter_uso_memoria_mb()

    desenhar_painel_info(screen, fps_atual, len(particulas), memoria_mb, gx, gy, gz)

    pygame.display.flip()
    clock.tick(60)