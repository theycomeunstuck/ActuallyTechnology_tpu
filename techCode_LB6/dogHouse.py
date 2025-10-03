#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Doghouse — 5×3 слот-автомат с «собачьей» тематикой
===================================================

Особенности:
- 5 барабанов, 3 ряда, 10 фиксированных линий выплат.
- Символы: четыре «собаки» (старшие), иконки (младшие), WILD («Домик») и SCATTER («Лапа»).
- WILD заменяет любые символы (кроме SCATTER) и умножает линейный выигрыш ×2 за каждый WILD в комбинации.
- SCATTER платит в любом месте; 3+/5 активируют фриспины (8/12/15). Во время фриспинов выпавшие WILD становятся «липкими» (sticky) до конца бонуса.
- Два интерфейса: CLI (консоль) и GUI (Pygame). Запуск:
    GUI по умолчанию:        python doghouse_slot.py
    CLI-режим:               python doghouse_slot.py --cli

Зависимости:
    - Для GUI: pygame (pip install pygame)
    - CLI не требует дополнительных библиотек.

Примечание о выплатах: все множители в таблице выплат применяются к ставке «на линию».
"""
from __future__ import annotations

import argparse
import random
import sys
import time
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Sequence, Set

# ------------------------------
# Константы игрового поля
# ------------------------------
REELS = 5
ROWS = 3
LINES = 10  # фиксированные линии

# Коды символов — краткие для ASCII-вывода
DOG1 = "D1"  # Старший
DOG2 = "D2"
DOG3 = "D3"
DOG4 = "D4"
COLLAR = "CL"  # Ошейник
BOWL = "BW"    # Миска
BONE = "BN"    # Кость
PAW = "S"      # SCATTER (Лапа)
HOUSE = "W"    # WILD (Домик)

REGULAR_SYMBOLS: Tuple[str, ...] = (DOG1, DOG2, DOG3, DOG4, COLLAR, BOWL, BONE)
ALL_SYMBOLS: Tuple[str, ...] = REGULAR_SYMBOLS + (PAW, HOUSE)

# Читабельные названия для GUI/CLI
SYMBOL_NAME: Dict[str, str] = {
    DOG1: "Ротвейлер",
    DOG2: "Мопс",
    DOG3: "Бигль",
    DOG4: "Шиба",
    COLLAR: "Ошейник",
    BOWL: "Миска",
    BONE: "Кость",
    PAW: "Скаттер (Лапа)",
    HOUSE: "Домик (WILD)",
}

# ------------------------------
# Таблица выплат (множители к ставке на линию)
# Ключ: символ -> {кол-во_в_ряду: множитель}
# ------------------------------
PAYTABLE: Dict[str, Dict[int, int]] = {
    DOG1: {3: 8, 4: 30, 5: 100},
    DOG2: {3: 6, 4: 24, 5: 80},
    DOG3: {3: 5, 4: 18, 5: 60},
    DOG4: {3: 4, 4: 12, 5: 40},
    COLLAR: {3: 3, 4: 8, 5: 20},
    BOWL: {3: 2, 4: 6, 5: 15},
    BONE: {3: 2, 4: 5, 5: 12},
    # SCATTER платит «вразброс», не по линиям — отдельно ниже
}

# SCATTER-выплаты: множители к СТАВКЕ ОБЩЕЙ (total bet)
SCATTER_PAYS: Dict[int, int] = {3: 2, 4: 10, 5: 50}

# Фриспины по кол-ву скаттеров
SCATTER_FREE_SPINS: Dict[int, int] = {3: 8, 4: 12, 5: 15}

# Вес символов при генерации (чем больше — тем чаще появляется)
SYMBOL_WEIGHTS: Dict[str, int] = {
    DOG1: 3,
    DOG2: 4,
    DOG3: 5,
    DOG4: 6,
    COLLAR: 8,
    BOWL: 9,
    BONE: 9,
    PAW: 2,     # редкий скаттер
    HOUSE: 2,   # редкий вайлд
}

# 10 стандартных линий (индексы рядов для каждого из 5 барабанов)
PAYLINES: List[List[int]] = [
    [1, 1, 1, 1, 1],  # по центру
    [0, 0, 0, 0, 0],  # верхний ряд
    [2, 2, 2, 2, 2],  # нижний ряд
    [0, 1, 2, 1, 0],  # V
    [2, 1, 0, 1, 2],  # ^
    [0, 0, 1, 0, 0],
    [2, 2, 1, 2, 2],
    [1, 0, 0, 0, 1],
    [1, 2, 2, 2, 1],
    [0, 1, 2, 2, 2],  # диагональная вариация
]

# ------------------------------
# Утилиты
# ------------------------------
def weighted_choice(symbols: Sequence[str], weights: Sequence[int]) -> str:
    """Выбор одного символа по весам.
    Используем random.choices для читаемости и стабильности.
    """
    return random.choices(symbols, weights=weights, k=1)[0]


@dataclass
class SpinResult:
    grid: List[List[str]]  # [reel][row]
    line_wins: List[Tuple[int, str, int, int, int]] = field(default_factory=list)
    # каждый элемент: (№ линии (0-индекс), базовый_символ, длина, множитель, выплата_в_монетах)
    scatter_count: int = 0
    scatter_win: int = 0
    total_win: int = 0


class DoghouseEngine:
    """Игровой движок, не зависящий от интерфейса.

    Содержит баланс, ставку, логику спинов, подсчёт выигрышей, фриспины и sticky-wild.
    """

    def __init__(self, starting_balance: int = 1000, bet_per_line: int = 1):
        self.balance: int = starting_balance
        self.bet_per_line: int = bet_per_line
        self.lines: int = LINES
        self.free_spins_left: int = 0
        self.sticky_wilds: Set[Tuple[int, int]] = set()  # {(reel, row)}
        self.last_result: Optional[SpinResult] = None

        self._symbols = list(SYMBOL_WEIGHTS.keys())
        self._weights = [SYMBOL_WEIGHTS[s] for s in self._symbols]

    # --------------------------
    # Публичные методы
    # --------------------------
    @property
    def total_bet(self) -> int:
        return self.bet_per_line * self.lines

    def can_spin(self) -> bool:
        """Есть ли деньги на спин в базовой игре (во фриспинах ставка не списывается)."""
        return self.free_spins_left > 0 or self.balance >= self.total_bet

    def change_bet(self, delta: int) -> None:
        """Изменить ставку на линию в разумных пределах."""
        new_bet = max(1, min(100, self.bet_per_line + delta))
        self.bet_per_line = new_bet

    def spin(self) -> SpinResult:
        """Совершить один спин. Возвращает результат и обновляет баланс/фриспины.

        - Если активны фриспины, ставка не списывается; sticky-wild остаются.
        - В базовой игре перед спином списывается total_bet.
        - SCATTER может начислить фриспины (и во время бонуса тоже — разрешим «ретригер»).
        """
        if not self.can_spin():
            raise RuntimeError("Недостаточно средств для спина.")

        base_game = self.free_spins_left == 0
        if base_game:
            # списываем ставку
            self.balance -= self.total_bet

        # генерируем сетку символов (с учётом sticky-wild во фриспинах)
        grid = self._generate_grid_with_sticky()

        # считаем выигрыши
        result = self._evaluate_grid(grid)

        # обновляем баланс и состояние фриспинов
        self.balance += result.total_win

        # если есть скаттеры на 3+ — даём фриспины (и ретригерим)
        new_frees = self._free_spins_from_scatters(result.scatter_count)
        if new_frees > 0:
            self.free_spins_left += new_frees

        # уменьшить счётчик фриспинов (если активны)
        if self.free_spins_left > 0:
            self.free_spins_left -= 1

        self.last_result = result
        return result

    # --------------------------
    # Внутренняя логика
    # --------------------------
    def _generate_grid_with_sticky(self) -> List[List[str]]:
        """Создать 5×3 сетку символов. Во фриспинах сохраняем липкие WILD-ы."""
        grid: List[List[str]] = [["" for _ in range(ROWS)] for _ in range(REELS)]
        for r in range(REELS):
            for c in range(ROWS):
                if (r, c) in self.sticky_wilds:
                    grid[r][c] = HOUSE  # sticky wild как обычный WILD при подсчёте
                else:
                    grid[r][c] = weighted_choice(self._symbols, self._weights)

        # Во время фриспинов: любые новые WILD становятся sticky на последующие спины
        if self.free_spins_left > 0:
            for r in range(REELS):
                for c in range(ROWS):
                    if grid[r][c] == HOUSE:
                        self.sticky_wilds.add((r, c))
        else:
            # в базовой игре sticky очищаем (они только для бонуса)
            self.sticky_wilds.clear()
        return grid

    def _evaluate_grid(self, grid: List[List[str]]) -> SpinResult:
        # Посчитаем скаттеры (платит от 3)
        flat = [grid[r][c] for r in range(REELS) for c in range(ROWS)]
        sc_count = sum(1 for s in flat if s == PAW)
        scatter_win = 0
        if sc_count >= 3:
            multiplier = SCATTER_PAYS.get(sc_count, SCATTER_PAYS[max(SCATTER_PAYS.keys())])
            scatter_win = multiplier * self.total_bet

        line_wins: List[Tuple[int, str, int, int, int]] = []
        total_win = scatter_win

        for li, line in enumerate(PAYLINES):
            # Получаем символы по линии слева направо: (reel i, row = line[i])
            symbols = [grid[i][line[i]] for i in range(REELS)]

            # Скаттеры не участвуют в линейных выплатах
            # Вайлды заменяют
            best_payout = 0
            best_tuple: Optional[Tuple[int, str, int, int, int]] = None

            # Если все вайлды — считаем как лучшую старшую собаку
            if all(s == HOUSE for s in symbols):
                base = DOG1
                length = REELS
                mult = PAYTABLE[base][5] if 5 in PAYTABLE[base] else 0
                wilds = REELS
                # множитель ×2^кол-ву вайлдов
                payout = mult * self.bet_per_line * (2 ** wilds)
                if payout > best_payout:
                    best_payout = payout
                    best_tuple = (li, base, length, mult * (2 ** wilds), payout)
            else:
                # Рассмотрим всех кандидатов «базового» символа (любые, кроме скаттера и вайлда),
                # которые встречаются слева направо с учётом замены вайлдами.
                for base in REGULAR_SYMBOLS:
                    length, wild_count = self._match_length_left(symbols, base)
                    if length >= 3 and base in PAYTABLE and length in PAYTABLE[base]:
                        mult = PAYTABLE[base][length]
                        payout = mult * self.bet_per_line * (2 ** wild_count)
                        if payout > best_payout:
                            best_payout = payout
                            best_tuple = (li, base, length, mult * (2 ** wild_count), payout)

            if best_tuple is not None and best_payout > 0:
                total_win += best_payout
                line_wins.append(best_tuple)

        return SpinResult(grid=grid, line_wins=line_wins, scatter_count=sc_count,
                          scatter_win=scatter_win, total_win=total_win)

    @staticmethod
    def _match_length_left(symbols: List[str], base: str) -> Tuple[int, int]:
        """Возвращает (длина подряд слева, кол-во вайлдов в этой последовательности)
        для заданного базового символа.
        """
        length = 0
        wilds = 0
        for s in symbols:
            if s == base or s == HOUSE:
                length += 1
                if s == HOUSE:
                    wilds += 1
            else:
                break
        return length, wilds

    @staticmethod
    def _free_spins_from_scatters(sc_count: int) -> int:
        for n in sorted(SCATTER_FREE_SPINS.keys(), reverse=True):
            if sc_count >= n:
                return SCATTER_FREE_SPINS[n]
        return 0


# ============================================================
# CLI-интерфейс (консоль)
# ============================================================

def render_grid_ascii(grid: List[List[str]]) -> str:
    """Красивый ASCII-рендер сетки 5×3.
    grid — список столбцов, внутри — строки (reel-major). Для вывода удобнее строки-major.
    """
    # Преобразуем в rows×cols для печати по строкам сверху вниз
    rows: List[List[str]] = [[grid[c][r] for c in range(REELS)] for r in range(ROWS)]
    # Заголовок
    lines = ["+-----+-----+-----+-----+-----+"]
    for r in range(ROWS):
        row = "|".join(f" {rows[r][c]:^3} " for c in range(REELS))
        lines.append("|" + row + "|")
        lines.append("+-----+-----+-----+-----+-----+")
    return "\n".join(lines)


def cli_loop():
    print("Добро пожаловать в слот 'Doghouse' (CLI)!\n")
    engine = DoghouseEngine(starting_balance=1000, bet_per_line=1)

    help_text = (
        "Команды: enter — спин, + — увеличить ставку, - — уменьшить ставку, h — помощь, q — выход\n"
    )
    print(help_text)

    while True:
        print(f"Баланс: {engine.balance} | Ставка/линия: {engine.bet_per_line} | Линий: {engine.lines} | Total bet: {engine.total_bet}")
        if engine.free_spins_left > 0:
            print(f"Бонус! Бесплатные спины: осталось {engine.free_spins_left}")

        cmd = input("[Enter=СПИН / +=ставка / -=ставка / h / q]: ").strip().lower()
        if cmd == "q":
            print("Выход. Спасибо за игру!")
            return
        if cmd == "+":
            engine.change_bet(+1)
            continue
        if cmd == "-":
            engine.change_bet(-1)
            continue
        if cmd == "h":
            print(help_text)
            continue

        if not engine.can_spin():
            print("Недостаточно средств. Игра окончена.")
            return

        result = engine.spin()
        print(render_grid_ascii(result.grid))

        # Вывод выигрышей
        if result.scatter_win > 0:
            print(f"SCATTER x{result.scatter_count} платит {result.scatter_win}")
        if result.line_wins:
            print("Линейные выигрыши:")
            for (li, base, length, mult_eff, coins) in result.line_wins:
                print(f"  Линия {li+1:02d}: {SYMBOL_NAME.get(base, base)} ×{length} -> множитель {mult_eff}, выплата {coins}")
        if result.total_win == 0:
            print("Увы, без выигрыша.")
        else:
            print(f"Итого выигрыш за спин: {result.total_win}. Баланс: {engine.balance}")

        print("-" * 60)


# ============================================================
# GUI на Pygame
# ============================================================

def run_gui():
    try:
        import pygame
    except Exception as e:
        print("Для GUI требуется pygame. Установите: pip install pygame")
        print("Ошибка импорта:", e)
        sys.exit(1)

    pygame.init()
    W, H = 1260, 680
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("Doghouse — слот 5×3")
    clock = pygame.time.Clock()

    # Шрифты
    font_big = pygame.font.SysFont(None, 48)
    font_mid = pygame.font.SysFont(None, 32)
    font_small = pygame.font.SysFont(None, 24)

    # Цвета (приятные пастельные)
    BG = (32, 35, 48)
    PANEL = (45, 50, 66)
    WHITE = (240, 240, 240)
    YELLOW = (255, 226, 120)
    GREEN = (140, 220, 160)
    RED = (255, 120, 120)
    BLUE = (150, 195, 255)
    GOLD = (255, 210, 100)

    # Цвета «плиток» символов
    TILE_COLORS: Dict[str, Tuple[int, int, int]] = {
        DOG1: (235, 111, 146),  # розовый
        DOG2: (64, 160, 255),   # голубой
        DOG3: (160, 138, 255),  # сиреневый
        DOG4: (255, 158, 100),  # апельсин
        COLLAR: (87, 190, 160),
        BOWL: (255, 214, 165),
        BONE: (198, 160, 246),
        PAW: (255, 255, 140),
        HOUSE: (255, 200, 120),
    }

    # Геометрия барабанов
    REEL_W, REEL_H = 170, 150
    GAP_X, GAP_Y = 14, 14
    START_X = 60
    START_Y = 90

    # Правый край области барабанов и x панели результатов
    REELS_AREA_RIGHT = START_X + REEL_W * REELS + GAP_X * (REELS - 1)
    PANEL_X = REELS_AREA_RIGHT + 20  # панель справа от барабанов
    PANEL_W = 240  # фиксированная ширина панели (окно достаточно широкое)

    spin_button = pygame.Rect(PANEL_X + 20, 560, 200, 80)
    bet_minus = pygame.Rect(60, 560, 60, 60)
    bet_plus = pygame.Rect(240, 560, 60, 60)
    max_bet = pygame.Rect(320, 560, 120, 60)

    engine = DoghouseEngine(starting_balance=1000, bet_per_line=1)

    spinning = False
    spin_start_time = 0.0
    # Для анимации — время «остановки» для каждого барабана
    reel_stop_times: List[float] = [0.0] * REELS
    anim_grid: List[List[str]] = [[random.choice(list(SYMBOL_WEIGHTS.keys())) for _ in range(ROWS)] for _ in range(REELS)]
    last_win = 0
    last_info: List[str] = []

    def draw_panel():
        pygame.draw.rect(screen, PANEL, pygame.Rect(0, 0, W, 70))
        title = font_big.render("Doghouse — 5×3", True, WHITE)
        screen.blit(title, (20, 16))

        bal = font_mid.render(f"Баланс: {engine.balance}", True, YELLOW)
        bet = font_mid.render(f"Ставка/линия: {engine.bet_per_line}  |  Линий: {engine.lines}  |  Total: {engine.total_bet}", True, WHITE)
        screen.blit(bal, (520, 14))
        screen.blit(bet, (520, 40))

    def draw_reels(grid: List[List[str]], highlight_lines: Optional[List[int]] = None):
        for r in range(REELS):
            for c in range(ROWS):
                x = START_X + r * (REEL_W + GAP_X)
                y = START_Y + c * (REEL_H + GAP_Y)
                rect = pygame.Rect(x, y, REEL_W, REEL_H)
                sym = grid[r][c]
                color = TILE_COLORS.get(sym, (200, 200, 200))
                pygame.draw.rect(screen, color, rect, border_radius=18)
                pygame.draw.rect(screen, (20, 20, 20), rect, 3, border_radius=18)

                label = font_mid.render(sym, True, (30, 30, 30))
                screen.blit(label, (x + 12, y + 10))
                name = font_small.render(SYMBOL_NAME.get(sym, sym), True, (30, 30, 30))
                screen.blit(name, (x + 12, y + REEL_H - 26))

        # Лёгкие маркеры линий, если есть выигрышные
        if highlight_lines:
            for li in highlight_lines:
                line = PAYLINES[li]
                pts = []
                for i in range(REELS):
                    x = START_X + i * (REEL_W + GAP_X) + REEL_W // 2
                    y = START_Y + line[i] * (REEL_H + GAP_Y) + REEL_H // 2
                    pts.append((x, y))
                if len(pts) >= 2:
                    pygame.draw.lines(screen, GOLD, False, pts, 4)

    def draw_buttons():
        # Spin
        pygame.draw.rect(screen, GREEN if not spinning else (100, 180, 120), spin_button, border_radius=14)
        txt = font_mid.render("SPIN", True, (15, 35, 15))
        screen.blit(txt, (spin_button.x + 44, spin_button.y + 26))
        # Bet -/+
        pygame.draw.rect(screen, BLUE, bet_minus, border_radius=10)
        screen.blit(font_mid.render("-", True, (20, 20, 40)), (bet_minus.x + 22, bet_minus.y + 16))
        pygame.draw.rect(screen, BLUE, bet_plus, border_radius=10)
        screen.blit(font_mid.render("+", True, (20, 20, 40)), (bet_plus.x + 20, bet_plus.y + 16))
        pygame.draw.rect(screen, BLUE, max_bet, border_radius=10)
        screen.blit(font_small.render("MAX BET", True, (20, 20, 40)), (max_bet.x + 20, max_bet.y + 20))

        # Подсказки
        help1 = font_small.render("SPACE — SPIN, +/- — ставка, ESC — выход", True, WHITE)
        screen.blit(help1, (60, 630))

        if engine.free_spins_left > 0:
            bonus_lbl = font_mid.render(f"БОНУС! Бесплатные спины: {engine.free_spins_left}", True, YELLOW)
            screen.blit(bonus_lbl, (60, 520))

        if last_win > 0:
            lw = font_mid.render(f"Выигрыш: {last_win}", True, GOLD)
            screen.blit(lw, (520, 520))

    def start_spin():
        nonlocal spinning, spin_start_time, reel_stop_times, last_info
        if spinning:
            return
        if not engine.can_spin():
            last_info = ["Недостаточно средств для спина"]
            return
        spinning = True
        spin_start_time = time.time()
        # Каждому барабану зададим момент остановки (последовательно)
        base = 0.8
        step = 0.35
        reel_stop_times = [spin_start_time + base + i * step for i in range(REELS)]

    def update_animation():
        nonlocal spinning, anim_grid, last_win, last_info
        now = time.time()
        if not spinning:
            return

        # вращаем барабаны, пока не пришло их время остановиться — подменяем случайными символами
        for r in range(REELS):
            if now < reel_stop_times[r]:
                # крутим — сдвигаем вниз и добавляем случайный символ сверху
                col = anim_grid[r]
                col.pop()  # убрать нижний
                col.insert(0, random.choice(list(SYMBOL_WEIGHTS.keys())))
            else:
                # барабан должен «зафиксироваться» на итоговой сетке
                pass

        # когда все барабаны прошли своё время — фиксируем результат и считаем выигрыш
        if now >= reel_stop_times[-1]:
            # Выполним спин в движке (списывает ставку, считает sticky и т.п.)
            result = engine.spin()
            anim_grid = [col[:] for col in result.grid]  # перерисуем на итоговую сетку
            spinning = False
            last_win = result.total_win

            # Соберём краткий отчёт строками (для правой панели)
            info = []
            if result.scatter_win > 0:
                info.append(f"SCATTER x{result.scatter_count} -> {result.scatter_win}")
            for (li, base, length, mult_eff, coins) in result.line_wins:
                info.append(f"Л{li+1}: {base}×{length} -> {coins}")
            if not info:
                info = ["Без выигрыша"]
            last_info = info

    # Основной цикл GUI
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    start_spin()
                elif event.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                    engine.change_bet(+1)
                elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    engine.change_bet(-1)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                if spin_button.collidepoint(mx, my):
                    start_spin()
                elif bet_minus.collidepoint(mx, my):
                    engine.change_bet(-1)
                elif bet_plus.collidepoint(mx, my):
                    engine.change_bet(+1)
                elif max_bet.collidepoint(mx, my):
                    engine.bet_per_line = 10

        # Анимация вращения/остановки
        update_animation()

        # Рендеринг
        screen.fill(BG)
        draw_panel()

        # Подсветка выигрышных линий (после остановки)
        hl = [li for (li, *_rest) in (engine.last_result.line_wins if engine.last_result else [])]
        draw_reels(anim_grid, highlight_lines=hl if hl else None)

        # Боковая панель с инфо
        pygame.draw.rect(screen, PANEL, pygame.Rect(PANEL_X, 90, PANEL_W, 450), border_radius=12)
        screen.blit(font_mid.render("Результат", True, WHITE), (PANEL_X + 20, 100))
        y = 130
        for s in last_info[:12]:
            screen.blit(font_small.render(s, True, WHITE), (PANEL_X + 20, y))
            y += 26

        draw_buttons()

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


# ============================================================
# Точка входа
# ============================================================


def main():
    parser = argparse.ArgumentParser(description="Doghouse 5×3 — слот-автомат (CLI/GUI)")
    parser.add_argument("--cli", action="store_true", help="Запустить консольный интерфейс вместо GUI")
    args = parser.parse_args()

    if args.cli:
        cli_loop()
    else:
        run_gui()


if __name__ == "__main__":
    main()
