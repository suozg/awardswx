import wx
import numpy as np

class GameOfLifePanel(wx.Panel):
    def __init__(self, parent, fut_place=None, rows=50, cols=50, cell_size=10):
        super().__init__(parent)

        self.fut_place = fut_place
        self.rows = rows
        self.cols = cols
        self.cell_size = cell_size
        self.grid = np.zeros((rows, cols), dtype=bool)
        self.running = False
        self.generations = 0

        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_timer, self.timer)
        self.Bind(wx.EVT_LEFT_DOWN, self.on_click)
        self.Bind(wx.EVT_CHAR_HOOK, self.on_key)  # Для пробела
        self.SetFocus()

        self.label = wx.StaticText(self, label="Conway's Game of Life", style=wx.ALIGN_CENTER)
        self.last_footer_message = ""
        self.gen_label = wx.StaticText(self, label="gen.# 0", style=wx.ALIGN_LEFT)

        self.canvas = wx.Panel(self)
        self.canvas.Bind(wx.EVT_PAINT, self.on_paint)
        self.canvas.Bind(wx.EVT_LEFT_DOWN, self.on_click)  # Событие клика левой кнопкой мыши


        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.label, 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 5)
        sizer.Add(self.gen_label, 0, wx.EXPAND | wx.BOTTOM, 5)
        sizer.Add(self.canvas, 1, wx.EXPAND)

        self.random_btn = wx.Button(self, label="🎲 Випадкове поле")
        self.random_btn.Bind(wx.EVT_BUTTON, self.on_random)

        sizer.Add(self.random_btn, 0, wx.EXPAND | wx.ALL, 5)

        self.SetSizer(sizer)

        self.update_footer_message(self.last_footer_message)

    def on_click(self, event):
        x, y = event.GetPosition()

        canvas_width, canvas_height = self.canvas.GetSize()
        grid_width = self.cols * self.cell_size
        grid_height = self.rows * self.cell_size

        offset_x = (canvas_width - grid_width) // 2
        offset_y = (canvas_height - grid_height) // 2

        # Переводим координаты мыши в координаты сетки
        x_cell = (x - offset_x) // self.cell_size
        y_cell = (y - offset_y) // self.cell_size

        # Проверяем попадание внутрь сетки
        if 0 <= x_cell < self.cols and 0 <= y_cell < self.rows:
            self.grid[y_cell, x_cell] = not self.grid[y_cell, x_cell]
            self.canvas.Refresh()

    def on_random(self, event):
        # 30% клеток — живые
        self.grid = np.random.rand(self.rows, self.cols) < 0.3
        self.generations = 0
        self.gen_label.SetLabel("gen.# 0")
        self.canvas.Refresh()

    def on_key(self, event):
        key = event.GetKeyCode()
        if key == wx.WXK_SPACE:
            self.running = not self.running
            if self.running:
                self.timer.Start(100)
            else:
                self.timer.Stop()
        else:
            event.Skip()

    def on_timer(self, event):
        new_grid = np.copy(self.grid)

        for row in range(self.rows):
            for col in range(self.cols):
                neighbors = self.count_neighbors(row, col)
                if self.grid[row, col]:
                    new_grid[row, col] = neighbors in (2, 3)
                else:
                    new_grid[row, col] = neighbors == 3

        if np.array_equal(self.grid, new_grid):
            self.running = False
            self.timer.Stop()
        else:
            self.grid = new_grid
            self.generations += 1
            self.gen_label.SetLabel(f"gen.# {self.generations}")
            self.canvas.Refresh()

    def count_neighbors(self, row, col):
        count = 0
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                r, c = row + dr, col + dc
                if 0 <= r < self.rows and 0 <= c < self.cols:
                    count += self.grid[r, c]
        return count

    def on_paint(self, event):
        dc = wx.PaintDC(self.canvas)
        dc.Clear()

        canvas_width, canvas_height = self.canvas.GetSize()
        grid_width = self.cols * self.cell_size
        grid_height = self.rows * self.cell_size

        offset_x = (canvas_width - grid_width) // 2
        offset_y = (canvas_height - grid_height) // 2

        # Рисуем клетки
        for row in range(self.rows):
            for col in range(self.cols):
                x = offset_x + col * self.cell_size
                y = offset_y + row * self.cell_size
                if self.grid[row, col]:
                    dc.SetBrush(wx.Brush(wx.Colour(0, 0, 0)))
                else:
                    dc.SetBrush(wx.Brush(wx.Colour(255, 255, 255)))
                dc.DrawRectangle(x, y, self.cell_size, self.cell_size)

        # Рисуем сетку
        dc.SetPen(wx.Pen(wx.Colour(200, 200, 200)))
        for row in range(self.rows + 1):
            y = offset_y + row * self.cell_size
            dc.DrawLine(offset_x, y, offset_x + grid_width, y)
        for col in range(self.cols + 1):
            x = offset_x + col * self.cell_size
            dc.DrawLine(x, offset_y, x, offset_y + grid_height)


    # Цей метод викликається тепер через InfoPanel.get_footer_message
    def get_footer_message(self):
         """Повертає останнє повідомлення для футера з панелі гри."""
         # Повертаємо власне останнє повідомлення панелі гри
         return self.last_footer_message


     # Метод для оновлення повідомлення футера зсередини GameOfLifePanel
    def update_footer_message(self, message):
         """Оновлює внутрішнє останнє повідомлення панелі гри та сам футер."""
         # Це для оновлень в реальному часі, поки вкладка гри активна
         self.last_footer_message = f"Гра Життя {message}"
         if self.fut_place:
              self.fut_place.SetLabel(self.last_footer_message)