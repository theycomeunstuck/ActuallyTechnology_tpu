#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Простой клон Flappy Bird для начинающих на Pygame.

Управление:
- ПРОБЕЛ или ↑ (стрелка вверх) — “взмах” (прыжок птицы)
- R или ПРОБЕЛ на экране Game Over — перезапуск
- ESC — выход

Идея механики:
- Птица падает вниз под действием "гравитации" (постоянно увеличиваем скорость вниз).
- По нажатию кнопки придаём птице отрицательную скорость (рывок вверх).
- Трубы движутся слева направо с постоянной скоростью.
- Если птица пересекается с трубой или выходит за границы экрана — Game Over.
- За каждую пройденную пару труб (когда птица пролетиТ “мимо”, а левая граница трубы уже позади птицы) +1 очко.
"""

import sys
import random
import pygame

# ---------------- Настройки игры (попробуйте менять и смотреть эффект) ----------------
WIDTH, HEIGHT = 1280, 720     # размер окна игры (ширина x высота)
FPS = 90                     # частота кадров (чем больше, тем плавнее)
GRAVITY = 0.35               # сила "гравитации" (ускорение вниз)
JUMP_STRENGTH = 7.5          # сила "взмаха" (рывок вверх)
PIPE_GAP = 160               # размер зазора между верхней и нижней трубой
PIPE_SPEED = 3.5               # скорость движения труб влево
PIPE_INTERVAL = 1400         # период появления новых труб (мс)

# Цвета в формате (R,G,B)
SKY = (135, 206, 235)
GREEN = (76, 175, 80)
GREEN_DARK = (56, 142, 60)
TEXT = (33, 33, 33)
WHITE = (255, 255, 255)
GROUND = (221, 216, 148)

# ---------------- Классы игровых объектов ----------------
class Bird:
    """
    Птица: хранит координаты, скорость, радиус, умеет обновляться и рисоваться.
    В Pygame координата Y растёт вниз, X — вправо. (0,0) — левый верхний угол.
    """
    def __init__(self):
        self.x = WIDTH // 4            # фиксированное положение по X (чуть левее центра)
        self.y = HEIGHT // 2           # старт по центру экрана по Y
        self.radius = 18               # радиус круга-птицы
        self.vel_y = 0                 # вертикальная скорость (положительная — вниз)

    def flap(self):
        """Резкий рывок вверх: просто задаём отрицательную скорость."""
        self.vel_y = -JUMP_STRENGTH

    def update(self):
        """Обновляем вертикальную скорость и положение птицы каждый кадр."""
        self.vel_y += GRAVITY
        self.y += self.vel_y

    @property
    def rect(self) -> pygame.Rect:
        """
        Прямоугольник, охватывающий круг птицы.
        Используем для удобной проверки столкновений с трубами.
        """
        return pygame.Rect(
            int(self.x - self.radius),
            int(self.y - self.radius),
            int(self.radius * 2),
            int(self.radius * 2),
        )

    def draw(self, surf: pygame.Surface):
        """Простая отрисовка: круг (тело), глаз и крыло для вида."""
        # Тело
        pygame.draw.circle(surf, (255, 231, 76), (int(self.x), int(self.y)), self.radius)
        # Крыло (полумесяц)
        wing_rect = pygame.Rect(0, 0, self.radius + 4, self.radius)
        wing_rect.center = (int(self.x - 4), int(self.y + 4))
        pygame.draw.ellipse(surf, (255, 208, 32), wing_rect)
        # Глаз
        pygame.draw.circle(surf, WHITE, (int(self.x + 6), int(self.y - 6)), 5)
        pygame.draw.circle(surf, (0, 0, 0), (int(self.x + 7), int(self.y - 6)), 2)


class PipePair:
    """
    Пара труб: верхняя и нижняя. Между ними — зазор (PIPE_GAP), через который надо пролететь.
    Трубы стоят в одном X, но у них разная высота.
    """
    def __init__(self, x: int):
        self.x = x
        self.width = 70

        # Случайная вертикальная позиция зазора.
        # Оставляем "поля" сверху/снизу, чтобы зазор не упирался в границы.
        margin = 120
        self.gap_y = random.randint(margin, HEIGHT - margin)
        self.gap = PIPE_GAP

        self.scored = False  # помета, чтобы очки за эту пару труб начислить один раз

    def update(self):
        """Сдвигаем трубы влево с постоянной скоростью."""
        self.x -= PIPE_SPEED

    def offscreen(self) -> bool:
        """Пара труб полностью ушла за левую границу окна — можно удалять."""
        return self.x + self.width < 0

    def collides(self, rect: pygame.Rect) -> bool:
        """
        Проверяем столкновение: если прямоугольник птицы пересекается с верхней или нижней трубой.
        Верхняя труба: от верха экрана до верхней границы зазора.
        Нижняя труба: от нижней границы зазора до низа экрана.
        """
        top_rect = pygame.Rect(self.x, 0, self.width, self.gap_y - self.gap // 2)
        bottom_rect = pygame.Rect(
            self.x,
            self.gap_y + self.gap // 2,
            self.width,
            HEIGHT - (self.gap_y + self.gap // 2),
        )
        return rect.colliderect(top_rect) or rect.colliderect(bottom_rect)

    def draw(self, surf: pygame.Surface):
        """Отрисовываем две трубы и “ободки” на срезах для красоты."""
        top_h = self.gap_y - self.gap // 2
        bottom_y = self.gap_y + self.gap // 2

        # Верхняя труба
        pygame.draw.rect(surf, GREEN, (self.x, 0, self.width, top_h))
        pygame.draw.rect(surf, GREEN_DARK, (self.x, top_h - 10, self.width, 10))

        # Нижняя труба
        pygame.draw.rect(surf, GREEN, (self.x, bottom_y, self.width, HEIGHT - bottom_y))
        pygame.draw.rect(surf, GREEN_DARK, (self.x, bottom_y, self.width, 10))


# ---------------- Вспомогательные функции ----------------
def reset_game():
    """
    Сбрасываем игру к начальному состоянию:
    - новая птица,
    - пустой список труб,
    - нулевой счёт,
    - время последнего появления трубы = текущему времени.
    """
    bird = Bird()
    pipes = []
    score = 0
    last_spawn = pygame.time.get_ticks()
    return bird, pipes, score, last_spawn


# ---------------- Главная программа ----------------
def main():
    pygame.init()
    pygame.display.set_caption("Flappy (учебная версия)")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()

    # Две гарнитуры шрифтов: обычный и крупный (для заголовков)
    font = pygame.font.SysFont(None, 32, bold=True)
    big_font = pygame.font.SysFont(None, 56, bold=True)

    # Состояние игры: "PLAYING" (идёт игра) или "GAME_OVER" (проигрыш, ждём перезапуска)
    state = "PLAYING"
    best_score = 0


    # Создаём объекты
    bird, pipes, score, last_spawn = reset_game()

    # Отдельно нарисуем "землю" внизу как полоску (для красоты)
    ground_h = 40

    while True:
        # --- 1) Обработка событий (клавиши, выход) ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()

                if state == "PLAYING":
                    # В полёте — по пробелу/стрелке вверх "взмахиваем"
                    if event.key in (pygame.K_SPACE, pygame.K_UP):
                        bird.flap()

                elif state == "GAME_OVER":
                    # На экране Game Over — по R/SPACE/UP перезапускаем
                    if score > best_score:
                        best_score = score


                    if event.key in (pygame.K_r, pygame.K_SPACE, pygame.K_UP):
                        bird, pipes, score, last_spawn = reset_game()
                        state = "PLAYING"

        # --- 2) Логика обновления мира (только когда игра не завершена) ---
        if state == "PLAYING":
            bird.update()

            # Появление новых труб с интервалом PIPE_INTERVAL миллисекунд
            now = pygame.time.get_ticks()
            if now - last_spawn >= PIPE_INTERVAL:
                pipes.append(PipePair(WIDTH + 10))  # создаём новую пару труб чуть за правым краем
                last_spawn = now

            # Обновляем все трубы (двигаем влево) и удаляем ушедшие
            for p in pipes:
                p.update()
            pipes = [p for p in pipes if not p.offscreen()]

            # Проверка столкновений: с трубами...
            for p in pipes:
                if p.collides(bird.rect):
                    state = "GAME_OVER"
                    break

            # ...и с верхом/низом экрана (считаем, что “земля” — нижняя граница окна)
            if bird.y - bird.radius <= 0 or bird.y + bird.radius >= HEIGHT - ground_h:
                state = "GAME_OVER"

            # Начисление очков: когда труба прошла левее птицы (правый край трубы позади X птицы)
            for p in pipes:
                if not p.scored and (p.x + p.width) < bird.x:
                    p.scored = True
                    score += 1

        # --- 3) Отрисовка кадра ---
        screen.fill(SKY)

        # Трубы
        for p in pipes:
            p.draw(screen)

        # "Земля" — просто широкая полоска снизу, чтобы визуально было понятнее границы
        pygame.draw.rect(screen, GROUND, (0, HEIGHT - ground_h, WIDTH, ground_h))

        # Птица
        bird.draw(screen)

        # Счёт (в левом верхнем углу)
        score_surf = font.render(f"Счёт: {score}", True, TEXT)
        best_surf = font.render(f"Рекорд: {best_score}", True, TEXT)
        screen.blit(score_surf, (10, 10))
        screen.blit(best_surf, (10, 40))

        # Экран Game Over (полупрозрачный оверлей и подсказки)
        if state == "GAME_OVER":
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 120))  # чёрный с прозрачностью
            screen.blit(overlay, (0, 0))


            title = big_font.render("ИГРА ОКОНЧЕНА", True, WHITE)
            result = font.render(f"Ваш счёт: {score}", True, WHITE)
            record = font.render(f"Рекорд: {best_score}", True, WHITE)
            hint = font.render("R или ПРОБЕЛ — начать заново", True, WHITE)
            esc = font.render("ESC — выйти", True, WHITE)

            title_rect = title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 40))
            hint_rect = hint.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 10))
            esc_rect = esc.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 45))

            screen.blit(title, title_rect)
            screen.blit(hint, hint_rect)
            screen.blit(esc, esc_rect)

        pygame.display.flip()
        clock.tick(FPS)


if __name__ == "__main__":
    main()
