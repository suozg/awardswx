# -*- mode: python ; coding: utf-8 -*-
import copy
import sys
import json
import os
from pathlib import Path

# Налаштування гри
# Path.home() автоматично знайде шлях до домашньої папки
SAVE_FILE = str(Path.home() / ".config/checkers_save.json")

BOARD_SIZE = 8
WHITE = 'w'  # Гравець
BLACK = 'b'  # ШІ
WHITE_KING = 'W'
BLACK_KING = 'B'
EMPTY = " "

# Кольори для терміналу
RESET = "\033[0m"
BG_BLACK = "\033[40m"    # Чорний фон
BG_WHITE = "\033[107m"    # Світлий фон
# Кольори для фігур
TEXT_WHITE = "\033[1;37m" # Яскраво-білий текст
TEXT_BLACK = "\033[1;34m" # Темний текст для ШІ

def save_game(board, turn):
    """Зберігає стан дошки та чергу ходу у файл JSON."""
    data = {
        "board": board,
        "turn": turn
    }
    with open(SAVE_FILE, "w") as f:
        json.dump(data, f)
    print("\n[СИСТЕМА] Гру збережено!")

def load_game():
    """Завантажує стан гри з файлу. Повертає (board, turn) або (None, None)."""
    if not os.path.exists(SAVE_FILE):
        return None, None
    try:
        with open(SAVE_FILE, "r") as f:
            data = json.load(f)
        print("\n[СИСТЕМА] Попередню гру завантажено!")
        return data["board"], data["turn"]
    except Exception:
        return None, None

def to_chess_coords(row, col):
    """Перетворює індекси матриці (row, col) у шахову нотацію (напр. A3)."""
    letters = "ABCDEFGH"
    return f"{letters[col]}{8 - row}"

def show_rules():
    """Виводить правила англійських шашок."""
    print("\n" + "="*45)
    print("      ПРАВИЛА АНГЛІЙСЬКИХ ШАШОК (CHECKERS)      ")
    print("="*45)
    print("1. ХОДИ: Звичайна шашка ходить ТІЛЬКИ ВПЕРЕД")
    print("   на одну клітинку по діагоналі.")
    print("2. БИТТЯ: Звичайна шашка б'є ТІЛЬКИ ВПЕРЕД.")
    print("3. ОБОВ'ЯЗКОВЕ ВЗЯТТЯ: Якщо ви можете збити")
    print("   фігуру суперника, ви ЗОБОВ'ЯЗАНІ це зробити.")
    print("4. ДАМКА (KING): Стає дамкою, дійшовши до краю.")
    print("   Ходить і б'є на ОДНУ клітинку, але в УСІ боки.")
    print("5. ПЕРЕМОГА: Збити всі фігури ворога або")
    print("   заблокувати його (позбавити можливості ходу).")
    print("Спробуйте запуск з параметром --classic.")
    print("="*45)
    input("Натисніть Enter, щоб повернутися до гри...")

def create_board():
    board = [[EMPTY for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            if (r + c) % 2 != 0:
                if r < 3: board[r][c] = BLACK
                elif r > 4: board[r][c] = WHITE
    return board

def print_board_classic(board):
    # Вирівнювання: 4 пробіли зліва, потім кожна літера через 3 пробіли
    print("\n     A   B   C   D   E   F   G   H")
    print("   +---+---+---+---+---+---+---+---+")
    for r in range(BOARD_SIZE):
        # Номер рядка (одна цифра + пробіл)
        row_str = f" {8 - r} |"
        for c in range(BOARD_SIZE):
            # Вміст клітинки (один символ і пробіли навколо)
            row_str += f" {board[r][c]} |"
        print(f"{row_str} {8 - r}")
        print("   +---+---+---+---+---+---+---+---+")
    print("     A   B   C   D   E   F   G   H")

def print_board_modern(board):
    # Кожна літера має стояти над центром своєї клітинки (3 символи завширшки)
    print("\n     A  B  C  D  E  F  G  H")
    for r in range(BOARD_SIZE):
        # Відступ зліва для цифри
        print(f"  {8 - r} ", end="") 
        for c in range(BOARD_SIZE):
            bg_color = BG_WHITE if (r + c) % 2 == 0 else BG_BLACK
            piece = board[r][c]
            
            # Визначаємо колір фігури
            if piece.lower() == 'w':
                char_color = TEXT_WHITE
            elif piece.lower() == 'b':
                char_color = TEXT_BLACK
            else:
                char_color = ""
            
            # Клітинка: 1 пробіл + фігура + 1 пробіл (всього 3 символи)
            print(f"{bg_color}{char_color} {piece} {RESET}", end="")
        
        # Номер рядка справа
        print(f" {8 - r}") 
    print("     A  B  C  D  E  F  G  H\n")

def get_all_moves(board, player):
    moves = []
    jumps = []
    is_white = player.lower() == 'w'
    enemies = [BLACK, BLACK_KING] if is_white else [WHITE, WHITE_KING]
    directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]

    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            if board[r][c].lower() == player[0].lower():
                piece = board[r][c]
                is_king = piece in [WHITE_KING, BLACK_KING]
                
                for dr, dc in directions:
                    if not is_king:
                        if is_white and dr > 0: continue
                        if not is_white and dr < 0: continue
                    
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < BOARD_SIZE and 0 <= nc < BOARD_SIZE:
                        if board[nr][nc] == EMPTY:
                            moves.append(((r, c), (nr, nc)))
                    
                    jr, jc = r + 2*dr, c + 2*dc
                    if 0 <= jr < BOARD_SIZE and 0 <= jc < BOARD_SIZE:
                        if board[nr][nc] in enemies and board[jr][jc] == EMPTY:
                            jumps.append(((r, c), (jr, jc), (nr, nc)))
    
    return jumps if jumps else moves

def make_move(board, move):
    new_board = copy.deepcopy(board)
    start, end = move[0], move[1]
    piece = new_board[start[0]][start[1]]
    new_board[end[0]][end[1]] = piece
    new_board[start[0]][start[1]] = EMPTY
    if len(move) == 3:
        new_board[move[2][0]][move[2][1]] = EMPTY
    if piece == WHITE and end[0] == 0: new_board[end[0]][end[1]] = WHITE_KING
    if piece == BLACK and end[0] == 7: new_board[end[0]][end[1]] = BLACK_KING
    return new_board

def evaluate(board):
    score = 0
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            if board[r][c] == BLACK: score += 10
            elif board[r][c] == BLACK_KING: score += 20
            elif board[r][c] == WHITE: score -= 10
            elif board[r][c] == WHITE_KING: score -= 20
    return score

def minimax(board, depth, alpha, beta, maximizing_player):
    if depth == 0: return evaluate(board), None
    player = BLACK if maximizing_player else WHITE
    moves = get_all_moves(board, player)
    if not moves: return evaluate(board), None
    
    best_move = None
    if maximizing_player:
        v = float('-inf')
        for m in moves:
            ev = minimax(make_move(board, m), depth-1, alpha, beta, False)[0]
            if ev > v: v, best_move = ev, m
            alpha = max(alpha, v)
            if beta <= alpha: break
        return v, best_move
    else:
        v = float('inf')
        for m in moves:
            ev = minimax(make_move(board, m), depth-1, alpha, beta, True)[0]
            if ev < v: v, best_move = ev, m
            beta = min(beta, v)
            if beta <= alpha: break
        return v, best_move

def main(draw_function):
    # Спробуємо завантажити збережену гру
    loaded_board, loaded_turn = load_game()
    
    if loaded_board:
        choice = input("Знайдено збережену гру. Продовжити? (y/n): ").lower()
        if choice == 'y':
            board = loaded_board
            turn = loaded_turn
        else:
            board = create_board()
            turn = WHITE
    else:
        board = create_board()
        turn = WHITE
    
    while True:
        draw_function(board)
        moves = get_all_moves(board, turn)
        
        if not moves:
            print(f"\nКІНЕЦЬ ГРИ! Перемогли {'Чорні' if turn == WHITE else 'Білі'}")
            # Видаляємо файл збереження після кінця гри
            if os.path.exists(SAVE_FILE): os.remove(SAVE_FILE)
            break
            
        if turn == WHITE:
            print("'?' - правила, 's' - зберегти, 'q' - вихід.") # Додали 's'
            print("\n--- ВАШ ХІД (Білі) ---")
            for i, m in enumerate(moves):
                start = to_chess_coords(m[0][0], m[0][1])
                end = to_chess_coords(m[1][0], m[1][1])
                is_jump = '(БИТТЯ!)' if len(m) == 3 else ''
                print(f"{i}: {start} -> {end} {is_jump}")
            
            cmd = input("\nВаш вибір: ").strip().lower()
            if cmd == '?':
                show_rules()
                continue
            if cmd == 's': # Обробка збереження
                save_game(board, turn)
                continue
            if cmd == 'q':
                sys.exit()
            
            try:
                idx = int(cmd)
                board = make_move(board, moves[idx])
                turn = BLACK
            except (ValueError, IndexError):
                print("!!! Помилка: введіть номер ходу від 0 до", len(moves)-1)
        else:
            # Код ШІ залишається без змін...
            print("\nШІ думає...")
            score, move = minimax(board, 4, float('-inf'), float('inf'), True)
            # очищення екрану
            os.system('cls' if os.name == 'nt' else 'clear')
            if move is not None:
               board = make_move(board, move)
               print(f"ШІ зробив хід: {to_chess_coords(move[0][0], move[0][1])} -> {to_chess_coords(move[1][0], move[1][1])}")
               turn = WHITE
            else:
               print("\nШІ не знайшов варіантів і здається!")
               break

if __name__ == "__main__":
    selected_draw = print_board_modern 

    if len(sys.argv) > 1:
        if sys.argv[1] == "--classic":
            selected_draw = print_board_classic
        elif sys.argv[1] == "--color":
            selected_draw = print_board_modern

    main(selected_draw)
