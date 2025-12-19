import wx
import numpy as np

class GameOfLifePanel(wx.Panel):
    def __init__(self, parent, fut_place=None, rows=48, cols=64, cell_size=10):
        super().__init__(parent)

        self.fut_place = fut_place
        self.rows = rows
        self.cols = cols
        self.cell_size = cell_size
        self.grid = np.zeros((rows, cols), dtype=bool)
        self.running = False
        self.generations = 0
        
        self.history = []
        self.max_history = 200

        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_timer, self.timer)

        # UI елементи
        self.label = wx.StaticText(self, label="Гра «Життя»", style=wx.ALIGN_CENTER)
        self.gen_label = wx.StaticText(self, label="Покоління: 0", style=wx.ALIGN_LEFT)

        self.canvas = wx.Panel(self)
        self.canvas.SetBackgroundStyle(wx.BG_STYLE_PAINT) # Оптимізація для малювання
        self.canvas.Bind(wx.EVT_PAINT, self.on_paint)
        self.canvas.Bind(wx.EVT_LEFT_DOWN, self.on_click)
        self.Bind(wx.EVT_CHAR_HOOK, self.on_key) 

        # Панель кнопок (аналог Pygame кнопок)
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.play_btn = wx.Button(self, label="▶️ Старт/Пауза")
        self.next_btn = wx.Button(self, label="⏭️ Крок")
        self.back_btn = wx.Button(self, label="⬅️ Назад")
        self.random_btn = wx.Button(self, label="🎲 Випадково")
        self.clear_btn = wx.Button(self, label="🗑️ Очистити")

        btn_sizer.Add(self.play_btn, 1, wx.ALL, 2)
        btn_sizer.Add(self.next_btn, 1, wx.ALL, 2)
        btn_sizer.Add(self.back_btn, 1, wx.ALL, 2)
        btn_sizer.Add(self.random_btn, 1, wx.ALL, 2)
        btn_sizer.Add(self.clear_btn, 1, wx.ALL, 2)

        # Зв'язування подій
        self.play_btn.Bind(wx.EVT_BUTTON, self.toggle_running)
        self.next_btn.Bind(wx.EVT_BUTTON, self.on_next_step)
        self.back_btn.Bind(wx.EVT_BUTTON, self.on_undo)
        self.random_btn.Bind(wx.EVT_BUTTON, self.on_random)
        self.clear_btn.Bind(wx.EVT_BUTTON, self.on_clear)

        # Головний сайзер
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(self.label, 0, wx.EXPAND | wx.TOP, 5)
        main_sizer.Add(self.gen_label, 0, wx.LEFT | wx.BOTTOM, 5)
        main_sizer.Add(self.canvas, 1, wx.EXPAND)
        main_sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 5)

        self.SetSizer(main_sizer)
        self.update_footer_message("Готово до запуску")

    # --- Логіка історії
    def push_history(self):
        """Зберігає поточний стан перед зміною."""
        self.history.append(np.copy(self.grid))
        if len(self.history) > self.max_history:
            self.history.pop(0)

    def on_undo(self, event=None):
        """Повертає стан на один крок назад."""
        if self.history:
            self.grid = self.history.pop()
            if self.generations > 0:
                self.generations -= 1
            self.update_ui()

    # --- Обробка кроків ---
    def on_next_step(self, event=None):
        self.push_history()
        self.calculate_next_generation()
        self.update_ui()

    def calculate_next_generation(self):
        new_grid = np.zeros((self.rows, self.cols), dtype=bool)
        for r in range(self.rows):
            for c in range(self.cols):
                n = self.count_neighbors(r, c)
                alive = self.grid[r, c]
                if alive and n in (2, 3):
                    new_grid[r, c] = True
                elif not alive and n == 3:
                    new_grid[r, c] = True
        self.grid = new_grid
        self.generations += 1

    def count_neighbors(self, row, col):
        # Торіонна логіка
        total = 0
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0: continue
                # Зациклюємо поле (світ-тор)
                r = (row + dr) % self.rows
                c = (col + dc) % self.cols
                total += int(self.grid[r, c])
        return total

    # --- Керування станом ---
    def toggle_running(self, event=None):
        self.running = not self.running
        if self.running:
            self.timer.Start(100) # Швидкість оновлення
            self.update_footer_message("Запущено")
        else:
            self.timer.Stop()
            self.update_footer_message("Пауза")

    def on_clear(self, event=None):
        self.push_history()
        self.grid.fill(False)
        self.generations = 0
        self.update_ui()

    def on_random(self, event=None):
        self.push_history()
        self.grid = np.random.rand(self.rows, self.cols) < 0.2
        self.generations = 0
        self.update_ui()

    def on_timer(self, event):
        if self.running:
            self.push_history()
            self.calculate_next_generation()
            self.update_ui()

    def on_click(self, event):
        x, y = event.GetPosition()
        w, h = self.canvas.GetSize()
        grid_w, grid_h = self.cols * self.cell_size, self.rows * self.cell_size
        
        offset_x = (w - grid_w) // 2
        offset_y = (h - grid_h) // 2

        col = (x - offset_x) // self.cell_size
        row = (y - offset_y) // self.cell_size

        if 0 <= col < self.cols and 0 <= row < self.rows:
            self.push_history() # Зберігаємо перед ручним редагуванням
            self.grid[row, col] = not self.grid[row, col]
            self.canvas.Refresh()

    def on_key(self, event):
        key = event.GetKeyCode()
        if key == wx.WXK_SPACE:
            self.toggle_running()
        elif key in (ord('5'), wx.WXK_BACK):
            self.on_undo()
        else:
            event.Skip()

    def update_ui(self):
        self.gen_label.SetLabel(f"Покоління: {self.generations}")
        self.canvas.Refresh()

    def on_paint(self, event):
        dc = wx.AutoBufferedPaintDC(self.canvas)
        dc.Clear()
        
        w, h = self.canvas.GetSize()
        grid_w, grid_h = self.cols * self.cell_size, self.rows * self.cell_size
        ox, oy = (w - grid_w) // 2, (h - grid_h) // 2

        # Клітини
        dc.SetPen(wx.Pen(wx.Colour(200, 200, 200), 1))
        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r, c]:
                    dc.SetBrush(wx.Brush(wx.Colour(0, 255, 0))) 
                else:
                    dc.SetBrush(wx.Brush(wx.Colour(255, 255, 255)))
                
                dc.DrawRectangle(ox + c * self.cell_size, oy + r * self.cell_size, 
                                 self.cell_size, self.cell_size)

    def update_footer_message(self, message):
        self.last_footer_message = f"Гра Життя: {message}"
        if self.fut_place:
            self.fut_place.SetLabel(self.last_footer_message)
