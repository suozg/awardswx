# ui_utils.py
import wx
from wx import MessageBox, OK, ICON_INFORMATION
import threading
import wx.grid
from database_logic import connect_to_database, RankingValues

#-- для ОБРОБКИ ЗОБРАЖЕНЬ------
import io
import os
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
from openpyxl.utils import get_column_letter
from PIL import Image
from PIL import ImageEnhance
from config import ALL_COLUMN_LABELS


#  поиск и отображение списка наград с автоподстановкой
class AwardSearchHelper:
    def __init__(self, combo_ctrl, debounce_delay=600, kartka_panel_instance=None):
        self.combo_ctrl = combo_ctrl
        self.DEBOUNCE_DELAY_MS = debounce_delay
        self._loaded_award_names = []
        self._is_user_typing = False
        self.search_timer = None
        self.kartka_panel = kartka_panel_instance # <-- Додано для доступу до прапорця

        self.combo_ctrl.Bind(wx.EVT_TEXT, self.on_text_changed)
        self.combo_ctrl.Bind(wx.EVT_COMBOBOX, self.on_combo_selected)

    def set_award_names(self, names):
        self._loaded_award_names = names

    def on_text_changed(self, event):
        # Якщо зміна програмна, ігноруємо подію
        if self.kartka_panel and self.kartka_panel._is_programmatic_award_change:
            event.Skip()
            return

        self._is_user_typing = True
        if self.search_timer and self.search_timer.IsRunning():
            self.search_timer.Stop()
        self.search_timer = wx.CallLater(self.DEBOUNCE_DELAY_MS, self._perform_search_and_update)
        event.Skip()

    def on_combo_selected(self, event):
        if self.search_timer and self.search_timer.IsRunning():
            self.search_timer.Stop()
        self._is_user_typing = False
        selected_value = self.combo_ctrl.GetValue() # Отримуємо вибране значення
        event.Skip()

    def _perform_search_and_update(self):
        current_text = self.combo_ctrl.GetValue()
        if not current_text:
            filtered = self._loaded_award_names
        else:
            filtered = [a for a in self._loaded_award_names if current_text.lower() in a.lower()]

        self.combo_ctrl.Unbind(wx.EVT_TEXT, handler=self.on_text_changed)

        insertion_point = self.combo_ctrl.GetInsertionPoint()

        self.combo_ctrl.SetItems(filtered)
        self.combo_ctrl.SetValue(current_text)
        self.combo_ctrl.SetInsertionPoint(insertion_point)

        # Додаємо більш надійну перевірку, чи користувач вже зробив вибір.
        # Якщо поточний текст є одним із елементів у відфільтрованому списку
        # І не було активного введення (ми вже завершили друк)
        is_exact_match_selected = current_text in filtered and len(filtered) == 1

        # Викликаємо Popup(), лише якщо:
        # 1. Ми в режимі введення (користувач активно друкує)
        # 2. Є текст для пошуку
        # 3. Є відфільтровані результати
        # 4. Поточний текст НЕ є точним збігом, який вже обрано (тобто, користувач все ще шукає, а не вибрав)
        if self._is_user_typing and current_text and filtered and not is_exact_match_selected:
            try:
                self.combo_ctrl.Popup()
            except Exception:
                pass
        else:
            # Якщо це точний збіг і вибір зроблено, або якщо режим введення вже завершено,
            # переконайтеся, що випадаючий список закритий.
            try:
                self.combo_ctrl.Dismiss() # <-- Явно закриваємо список
            except Exception:
                pass

        self.combo_ctrl.Bind(wx.EVT_TEXT, self.on_text_changed)
        self._is_user_typing = False # Залишаємо тут для скидання після Debounce

    def reset_search(self):
        # Цей метод викликається ззовні для програмного скидання.
        # Його мета - очистити текстове поле та відобразити повний список.
        # Не використовуємо SetValue(""), щоб не генерувати EVT_TEXT.
        # Натомість, оновлюємо items напряму, якщо потрібно.

        # Забезпечуємо, що _is_user_typing вимкнено
        self._is_user_typing = False
        if self.search_timer and self.search_timer.IsRunning():
            self.search_timer.Stop()

        # Тимчасово відв'язуємо обробник тексту, щоб SetItems не викликав його
        self.combo_ctrl.Unbind(wx.EVT_TEXT, handler=self.on_text_changed)

        # Очищаємо текстове поле
        self.combo_ctrl.ChangeValue("") # Використовуємо ChangeValue, щоб не генерувати EVT_TEXT

        # Встановлюємо повний список елементів
        self.combo_ctrl.SetItems(self._loaded_award_names)

        # Встановлюємо вибір на порожній елемент (індекс 0)
        self.combo_ctrl.SetSelection(0)

        # Повторно прив'язуємо обробник
        self.combo_ctrl.Bind(wx.EVT_TEXT, self.on_text_changed)

# ----------------- ЛОГІКА ЗАПИТІВ ДЛЯ ЗВІТІВ


MIN_ROW_HEIGHT = 25
MAX_WIDTH = 300 # максимальна ширина розширених стовбців

class ReportGeneratorWx(wx.Frame):
    def __init__(self, parent, db_path, key, zvit_fields, zvit_dir, filters, exel_bmp=None):
        super().__init__(parent, title="Звіт", size=(800, 640))

        self.ALL_COLUMN_LABELS = ALL_COLUMN_LABELS

        self.filters = filters
        self.db_path = db_path
        self.key = key
        self._exel_bmp = exel_bmp

        # Перетворюємо zvit_fields на список int
        if isinstance(zvit_fields, str):
            zvit_fields = list(map(int, zvit_fields.split(',')))
        self.zvit_fields = zvit_fields
        self.zvit_dir = zvit_dir
        self.data = None

        self.panel = wx.Panel(self)
        self.rows_expanded = False 
        self.active_columns = []

        # --- Создаем рендерер переноса текста ОДИН РАЗ при инициализации ---
        self.wrap_renderer = wx.grid.GridCellAutoWrapStringRenderer()

        n_flags = len(self.zvit_fields)
        num_standard_flags = 14

        # Обробляємо перші num_standard_flags (14) прапорів (індекси 0 до 13 у zvit_fields)
        for i in range(num_standard_flags): # i буде від 0 до 13
            # original_data_index для цих прапорів дорівнює індексу прапора i
            original_data_index = i
            if self.zvit_fields[i] == 1: # Стандартне правило 0/1
                self.active_columns.append(original_data_index)
            # Припускаємо, що прапори 0, 2, 3 на цих позиціях означають "сховати"

        # Обробляємо ОСТАННІЙ прапор (індекс 14 у zvit_fields) за спеціальним правилом
        last_flag_index_in_zvit = 14 # Фіксований індекс для спеціального прапора
        # Ми вже перевірили, що n_flags >= 15, тому доступ self.zvit_fields[14] є безпечним.
        last_flag = self.zvit_fields[last_flag_index_in_zvit]

        original_index_rno = 15 # Очікуваний індекс РНОКПП у даних (18 у 20-колонковому кортежі)
        original_index_dob = 16 # Очікуваний індекс Дата нар. у даних (19 у 20-колонковому кортежі)

        if last_flag == 1: # Показувати тільки РНОКПП (оригінальний індекс 18)
            # Перевірка, що цільовий індекс 18 є дійсним для ALL_COLUMN_LABELS (довжина 20)
            if original_index_rno < len(self.ALL_COLUMN_LABELS):
                 self.active_columns.append(original_index_rno)

        elif last_flag == 2: # Показувати тільки Дату нар. (оригінальний індекс 19)
             if original_index_dob < len(self.ALL_COLUMN_LABELS):
                  self.active_columns.append(original_index_dob)

        elif last_flag == 3: # Показувати і РНОКПП (18), і Дату нар. (19)
             if original_index_rno < len(self.ALL_COLUMN_LABELS):
                  self.active_columns.append(original_index_rno)
             if original_index_dob < len(self.ALL_COLUMN_LABELS):
                  self.active_columns.append(original_index_dob)
        # Якщо last_flag == 0, нічого не додається для цих колонок

        # --- Визначаємо ЛЕЙБЛИ для активних колонок ---
        try:
             self.column_labels = [self.ALL_COLUMN_LABELS[i] for i in self.active_columns]
        except IndexError as e:
             # Fallback labels and active_columns to prevent grid creation crash
             self.column_labels = ["Помилка в конфігурації колонок"]
             self.active_columns = [0] # Спробуємо показати хоча б одну колонку (першу)

        # --- Створюємо сітку (кількість колонок сітки = len(self.active_columns)) ---
        self.grid = wx.grid.Grid(self.panel)
        # Переконайтеся, що сітка має хоча б одну колонку
        grid_col_count = len(self.active_columns) if self.active_columns else 1
        self.grid.CreateGrid(0, grid_col_count)

        # Встановлюємо заголовки колонок для видимих колонок сітки
        for idx, label in enumerate(self.column_labels):
            self.grid.SetColLabelValue(idx, label)

        # --- Відключаємо редагування для всієї сітки ---
        self.grid.EnableEditing(False) # <-- Додайте цей рядок

        for idx, label in enumerate(self.column_labels):
            self.grid.SetColLabelValue(idx, label)

        # --- Прив'язка події правої кнопки миші до ЯЧЕЙКИ сітки ---
        self.grid.Bind(wx.grid.EVT_GRID_CELL_RIGHT_CLICK, self.on_grid_right_click)

        # --- Додаємо прив'язку події подвійного лівого кліку на ячейці ---
        self.grid.Bind(wx.grid.EVT_GRID_CELL_LEFT_DCLICK, self.on_grid_cell_dclick)

        self.record_count_label = wx.StaticText(self.panel)

        self.excel_button = wx.BitmapButton(self.panel, bitmap=self._exel_bmp, size=(40, 35))
        if self._exel_bmp and self._exel_bmp.IsOk():
            self.excel_button.SetBitmap(self._exel_bmp, wx.LEFT)
            self.excel_button.SetLabel("")
        self.excel_button.Bind(wx.EVT_BUTTON, self.on_export_excel)

        self.close_button = wx.Button(self.panel, label="Закрити")
        self.close_button.Bind(wx.EVT_BUTTON, self.on_close)

        # --- Ініціалізуємо атрибути для зберігання останнього виділення ---
        self._last_selected_blocks = None
        self._last_selected_cells = None
        self._last_selected_rows = None
        self._last_right_clicked_cell = None

        # --- Налаштовуємо Sizers ---
        panel_sizer = wx.BoxSizer(wx.VERTICAL)
        panel_sizer.Add(self.grid, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)
        bottom_sizer = wx.BoxSizer(wx.HORIZONTAL)
        bottom_sizer.Add(self.record_count_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT | wx.RIGHT, 5)
        bottom_sizer.AddStretchSpacer(1)
        bottom_sizer.Add(self.excel_button, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        bottom_sizer.AddStretchSpacer(1)       
        bottom_sizer.Add(self.close_button, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 5)
        panel_sizer.Add(bottom_sizer, 0, wx.EXPAND | wx.ALL, 5)

        self.panel.SetSizer(panel_sizer)
        self.Layout()

        self._load_data()


    def on_close(self, event):
        self.Close()


    # --- Обробник подвійного лівого кліку на ячейці ---
    def on_grid_cell_dclick(self, event):
        # Зупиняємо стандартну обробку події, щоб редактор не запускався
        event.Skip(False)

        # Якщо ви хочете, щоб замість запуску редактора подвійний клік
        # викликав ваше контекстне меню, розкоментуйте наступний рядок:
        # self.on_grid_right_click(event)
        # Однак, стандартний UX для подвійного кліка - це активація/редагування,
        # а для контекстного меню - правий клік. Краще просто зупинити редактор.


    # --- Обробник ПРАВОЇ КНОПКИ МИШІ (зберігає виділення) ---
    def on_grid_right_click(self, event):

        # --- Отримуємо та зберігаємо поточне виділення ЯКІ ТІЛЬКИ ВІДБУВСЯ КЛІК ---
        try:
            self._last_selected_blocks = list(self.grid.GetSelectedBlocks())
        except TypeError:
            self._last_selected_blocks = [] # Встановлюємо порожній список у випадку помилки

        self._last_selected_cells = self.grid.GetSelectedCells() # Це вже список
        self._last_selected_rows = self.grid.GetSelectedRows()   # Це список
        self._last_right_clicked_cell = (event.GetRow(), event.GetCol()) # Зберігаємо клікнуту ячейку

        # --- Створюємо та налаштовуємо контекстне меню ---
        menu = wx.Menu()

        copy_cells_id = wx.NewIdRef()
        copy_rows_id = wx.NewIdRef()

        # Додаємо пункти меню та ВМИКАЄМО/ВИМИКАЄМО їх залежно від ЗБЕРЕЖЕНОГО виділення
        # Пункт "Копіювати виділені ячейки"
        copy_cells_item = menu.Append(copy_cells_id, "Копіювати виділені ячейки")
        # Вмикаємо його, якщо є виділені блоки АБО окремі ячейки
        if len(self._last_selected_blocks) > 0 or len(self._last_selected_cells) > 0:
             self.Bind(wx.EVT_MENU, self.on_copy_cells, id=copy_cells_id)
        else:
             copy_cells_item.Enable(False)


        # Пункт "Копіювати виділені рядки"
        copy_rows_item = menu.Append(copy_rows_id, "Копіювати виділені рядки")
        # Вмикаємо його, якщо є виділені рядки
        if len(self._last_selected_rows) > 0:
             self.Bind(wx.EVT_MENU, self.on_copy_rows, id=copy_rows_id)
        else:
             copy_rows_item.Enable(False)


        # Додаємо розділювач, якщо є хоча б один активний пункт копіювання
        if copy_cells_item.IsEnabled() or copy_rows_item.IsEnabled() or (self._last_right_clicked_cell[0] >= 0 and self._last_right_clicked_cell[1] >= 0):
             if menu.GetMenuItemCount() > 0: # Додаємо розділювач тільки якщо вже щось є
                 menu.AppendSeparator()


        # --- Додаємо пункт ПЕРЕМИКАННЯ ВИСОТИ РЯДКІВ ---
        toggle_rows_id = wx.NewIdRef()
        # Текст пункту залежить від поточного стану
        toggle_label = "Згорнути рядки" if self.rows_expanded else "Розгорнути рядки"
        menu.Append(toggle_rows_id, toggle_label)
        # Прив'язуємо його до існуючого обробника on_toggle_row_height
        self.Bind(wx.EVT_MENU, self.on_toggle_row_height, id=toggle_rows_id)

        # Можна додати інші стандартні пункти меню тут

        # Відображаємо меню
        self.grid.PopupMenu(menu, event.GetPosition())

        # Меню знищується автоматично після закриття/вибору пункту


    # --- Обробник пункту "Копіювати виділені ячейки" (використовує збережене виділення) ---
    def on_copy_cells(self, event):

        # !!! Використовуємо ЗБЕРЕЖЕНЕ виділення !!!
        selected_blocks = self._last_selected_blocks if self._last_selected_blocks is not None else []
        selected_cells = self._last_selected_cells if self._last_selected_cells is not None else []

        # Ця перевірка, по ідеї, не має спрацьовувати, бо пункт меню має бути вимкнений, якщо виділення немає
        if len(selected_blocks) == 0 and len(selected_cells) == 0:
            wx.MessageBox("Немає виділених ячеек для копіювання.", "Інформація", wx.OK | wx.ICON_INFORMATION)
            return

        text_to_copy = ""
        temp_data = {}

        # Збираємо дані з виділених блоків (збережений список)
        if len(selected_blocks) > 0:
             for block in selected_blocks:
                 r_start = block.GetTopLeft().GetRow()
                 c_start = block.GetTopLeft().GetCol()
                 r_end = block.GetBottomRight().GetRow()
                 c_end = block.GetBottomRight().GetCol()
                 for r in range(r_start, r_end + 1):
                     for c in range(c_start, c_end + 1):
                         temp_data[(r, c)] = self.grid.GetCellValue(r, c)

        # Збираємо дані з окремо виділених ячеек (збережений список)
        if selected_cells:
            for r, c in selected_cells:
                temp_data[(r, c)] = self.grid.GetCellValue(r, c)

        # Форматуємо зібрані дані в текст для буфера обміну
        if temp_data:
            all_coords = list(temp_data.keys())
            min_row = min(r for r, c in all_coords)
            max_row = max(r for r, c in all_coords)
            min_col = min(c for r, c in all_coords)
            max_col = max(c for r, c in all_coords)
            lines = []
            for r in range(min_row, max_row + 1):
                row_values = []
                for c in range(min_col, max_col + 1):
                    value = temp_data.get((r, c), "")
                    row_values.append(value)
                lines.append('\t'.join(row_values))
            text_to_copy = '\n'.join(lines)

        else:
            text_to_copy = "" # Якщо виділення було (пункт меню активний), але ячейки порожні

        # --- Логіка копіювання в буфер обміну ---
        if text_to_copy:

           if wx.TheClipboard.Open():
               clipboard_data = wx.TextDataObject(text_to_copy)
               success = wx.TheClipboard.SetData(clipboard_data)
               wx.TheClipboard.Close()
           else:
               wx.MessageBox("Не вдалося отримати доступ до буфера обміну.", "Помилка", wx.OK | wx.ICON_ERROR)


    # --- Обробник пункту "Копіювати виділені рядки" (використовує збережене виділення) ---
    def on_copy_rows(self, event):

        # !!! Використовуємо ЗБЕРЕЖЕНЕ виділення !!!
        selected_rows = self._last_selected_rows if self._last_selected_rows is not None else []

        # Ця перевірка, по ідеї, не має спрацьовувати, бо пункт меню має бути вимкнений
        if not selected_rows:
            wx.MessageBox("Немає виділених рядків для копіювання.", "Інформація", wx.OK | wx.ICON_INFORMATION)
            return

        text_to_copy = ""
        lines = []

        # Проходимо по виділених рядках (сортуємо їх)
        for row_idx in sorted(selected_rows):
             # Перевірка на всяк випадок, хоча індекси з GetSelectedRows мають бути дійсними
             if row_idx < 0 or row_idx >= self.grid.GetNumberRows():
                 continue

             row_values = []
             # Проходимо по всіх видимих колонках у цьому рядку
             for col_idx in range(self.grid.GetNumberCols()):
                  value = self.grid.GetCellValue(row_idx, col_idx)
                  row_values.append(str(value) if value is not None else "")

             lines.append('\t'.join(row_values))

        text_to_copy = '\n'.join(lines)

        # --- Логіка копіювання в буфер обміну ---
        if text_to_copy:

           if wx.TheClipboard.Open():
               clipboard_data = wx.TextDataObject(text_to_copy)
               success = wx.TheClipboard.SetData(clipboard_data)
               wx.TheClipboard.Close()
           else:
               wx.MessageBox("Не вдалося отримати доступ до буфера обміну.", "Помилка", wx.OK | wx.ICON_ERROR)


    # --- Обробник пункту "Копіювати цю ячейку" (використовує збережену клікнуту ячейку) ---
    def on_copy_clicked_cell(self, event):
        # !!! Використовуємо ЗБЕРЕЖЕНУ клікнуту ячейку !!!
        if self._last_right_clicked_cell and self._last_right_clicked_cell[0] >= 0 and self._last_right_clicked_cell[1] >= 0:
            r, c = self._last_right_clicked_cell
            try:
                text_to_copy = self.grid.GetCellValue(r, c)

                if text_to_copy or text_to_copy == "": # Копіюємо навіть порожній рядок
                    # --- Логіка копіювання в буфер обміну ---
                    if wx.TheClipboard.Open():
                        clipboard_data = wx.TextDataObject(text_to_copy)
                        success = wx.TheClipboard.SetData(clipboard_data)
                        wx.TheClipboard.Close()
                    else:
                        wx.MessageBox("Не вдалося отримати доступ до буфера обміну.", "Помилка", wx.OK | wx.ICON_ERROR)

            except Exception as e:
                wx.MessageBox(f"Помилка при копіюванні ячейки: {e}", "Помилка", wx.OK | wx.ICON_ERROR)

        else:
            wx.MessageBox("Не вдалося визначити ячейку для копіювання.", "Помилка", wx.OK | wx.ICON_ERROR)


    # --- Метод для перемикання висоти рядків (тепер також обробник меню) ---
    def on_toggle_row_height(self, event):
        if self.grid is None or self.grid.GetNumberRows() == 0:
            return

        if self.rows_expanded:
            # Якщо зараз розгорнуто, згортаємо
            self.rows_expanded = False
            # self.toggle_rows_button.SetLabel("Розгорнути рядки") # !!! ВИДАЛИТИ !!!
            min_height = self.grid.GetDefaultRowSize() if self.grid.GetDefaultRowSize() > 0 else MIN_ROW_HEIGHT
            for row_idx in range(self.grid.GetNumberRows()):
                self.grid.SetRowSize(row_idx, min_height)
        else:
            # Якщо зараз згорнуто, розгортаємо
            self.rows_expanded = True
            # self.toggle_rows_button.SetLabel("Згорнути рядки") # !!! ВИДАЛИТИ !!!
            self.grid.AutoSizeRows() # Автоматичний підбір висоти

        # Оновлюємо вигляд сітки та панелі
        self.grid.ForceRefresh()
        self.panel.Layout() # Можливо, Layout потрібен для панелі після зміни розмірів Grid
        # self.Layout() # Можливо, потрібен Layout для вікна Frame


    # --- Метод для наповнення сітки даними ---
    def _update_grid_with_data(self):
        # Цей метод має бути максимально стійким до стану self.data
        # Якщо даних немає або помилка завантаження, очищаємо сітку
        if self.data is None or not self.data:
            self.grid.ClearGrid()
            # Видаляємо всі існуючі рядки
            if self.grid.GetNumberRows() > 0:
                self.grid.DeleteRows(0, self.grid.GetNumberRows())
            self.record_count_label.SetLabel("Немає даних для відображення")
            self.SetTitle("Звіт – Немає даних") # Оновлюємо заголовок вікна
            self.grid.ForceRefresh()
            self.panel.Layout()
            return # Виходимо з методу

        # Дані є, продовжуємо оновлення сітки
        self.SetTitle(f"Звіт – {self.pre_titlestr}")

        num_rows_needed = len(self.data)
        num_cols_needed = len(self.active_columns)

        # Очищаємо та змінюємо розмір сітки
        self.grid.ClearGrid()
        current_rows = self.grid.GetNumberRows()
        if current_rows < num_rows_needed:
             self.grid.AppendRows(num_rows_needed - current_rows)
        elif current_rows > num_rows_needed:
             # Видаляємо зайві рядки з кінця
             self.grid.DeleteRows(num_rows_needed, current_rows - num_rows_needed)


        current_cols = self.grid.GetNumberCols()
        if current_cols < num_cols_needed:
             self.grid.AppendCols(num_cols_needed - current_cols)
        elif current_cols > num_cols_needed:
             # Видаляємо зайві колонки з кінця
             self.grid.DeleteCols(num_cols_needed, current_cols - num_cols_needed)

        # Перевстановлюємо заголовки колонок на випадок, якщо кількість колонок змінилася
        # self.column_labels вже містить коректні лейбли для self.active_columns
        if self.grid.GetNumberCols() == len(self.column_labels):
             for idx, label in enumerate(self.column_labels):
                 self.grid.SetColLabelValue(idx, label)

        # Заповнюємо ячейки даними
        for row_idx, row in enumerate(self.data):
            # Перевіряємо, чи кількість елементів у рядку даних достатня для активних колонок
            max_needed_data_index = max(self.active_columns) if self.active_columns else -1

            if len(row) > max_needed_data_index:
                 for col_idx, data_index in enumerate(self.active_columns):
                    try:
                        # Обробка значень None - перетворюємо на порожній рядок для відображення
                        value = row[data_index]
                        self.grid.SetCellValue(row_idx, col_idx, str(value if value is not None else ''))
                    except IndexError:
                         # Ця помилка вказує на невідповідність між active_columns та фактичною довжиною row
                         self.grid.SetCellValue(row_idx, col_idx, "ПОМИЛКА ДАНИХ (IndexError)") # Відображаємо помилку в ячейці
                    except Exception as e:
                         self.grid.SetCellValue(row_idx, col_idx, "ПОМИЛКА ДАНИХ") # Відображаємо загальну помилку
            else:
                # Якщо рядок даних занадто короткий
                # Заповнюємо ячейки для цього рядка, які відповідають активним колонкам,
                # доки не закінчаться дані в row або активні колонки.
                # Ті колонки, для яких data_index > len(row)-1, залишаться порожніми (ClearGrid вже очистив їх)
                for col_idx, data_index in enumerate(self.active_columns):
                    if data_index < len(row):
                        try:
                            value = row[data_index]
                            self.grid.SetCellValue(row_idx, col_idx, str(value if value is not None else ''))
                        except Exception as e:
                            self.grid.SetCellValue(row_idx, col_idx, "ПОМИЛКА ДАНИХ")
                    else:
                        # Data index is out of bounds for this specific row, leave cell empty
                        # ClearGrid ensures it's empty, no need to call SetCellValue("")
                        pass

        # --- Налаштовуємо рендерери переносу та розмір колонок ---       
       
        visible_cols = [i for i, flag in enumerate(self.zvit_fields) if flag]
      
        original_data_index_to_wrap = 5 # Индекс для "Текст подання"

        # Находим видимый индекс этой колонки в текущем гриде
        # Убеждаемся, что колонка вообще активна (видима)
        if original_data_index_to_wrap in self.active_columns:
            col_idx_visible = self.active_columns.index(original_data_index_to_wrap)

            # Створюємо НОВИЙ атрибут для колонки
            wrap_attr = wx.grid.GridCellAttr()
            wrap_attr.SetRenderer(self.wrap_renderer)
            wrap_attr.SetAlignment(wx.ALIGN_LEFT, wx.ALIGN_TOP) # Вирівнювання

            # Встановлюємо максимальну ширину колонки
            self.grid.SetColSize(col_idx_visible, MAX_WIDTH)

            # Застосовуємо атрибут з рендерером для переносу рядків до КОЛОНКИ
            self.grid.SetColAttr(col_idx_visible, wrap_attr)
               
        # Автопідбір висоти рядків або встановлення мінімальної висоти
        if self.rows_expanded: # Якщо стан "розгорнуто" (але початковий стан rows_expanded=False)
             self.grid.AutoSizeRows()
        else: # Якщо стан "згорнуто" (це початковий стан)
             min_height = self.grid.GetDefaultRowSize() if self.grid.GetDefaultRowSize() > 0 else MIN_ROW_HEIGHT
             for row_idx in range(self.grid.GetNumberRows()):
                self.grid.SetRowSize(row_idx, min_height)

        self.record_count_label.SetLabel(f"Кількість записів: {len(self.data)}")
        # self.grid.AutoSizeColumns() # Розгляньте, чи потрібен цей виклик. Він може скасувати SetColSize.
        self.grid.ForceRefresh() # Оновлюємо вигляд сітки
        self.panel.Layout() # Оновлюємо компоновку панелі


    # --- Метод _load_data (без змін) ---
    def _load_data(self):
        thread = threading.Thread(target=self._load_data_background)
        thread.start()
        self.record_count_label.SetLabel("Чекайте, йде обробка запиту...")
        # Використовуємо CallAfter для оновлення UI з потоку
        wx.CallAfter(self.record_count_label.SetLabel, "Чекайте, йде обробка запиту...")
        wx.Yield() # Щоб надпис одразу з'явився


    # --- Метод _load_data_background (з покращеною обробкою помилок та CallAfter) ---
    def _load_data_background(self):
        """ запускаємо окремий поток для отримання даних """
        conn = None
        cursor = None
        try:
            conn, cursor = connect_to_database(self.key, self.db_path)
            if conn is None or cursor is None:
                wx.CallAfter(self._show_message, "Не вдалося підключитися до бази даних.")
                wx.CallAfter(self.record_count_label.SetLabel, "Помилка підключення до БД")
                # Очищаємо сітку, оскільки немає даних
                wx.CallAfter(self._update_grid_with_data) # Викликаємо оновлення для порожніх даних
                return

            query, params, pre_titlestr = build_query(self.filters, self.zvit_fields)
            self.pre_titlestr = pre_titlestr

            if not query:
                 wx.CallAfter(self._show_message, "Не вдалося сформувати запит до бази даних.")
                 wx.CallAfter(self.record_count_label.SetLabel, "Помилка формування запиту")
                 # Очищаємо сітку
                 wx.CallAfter(self._update_grid_with_data)
                 return

            # fetch_data тепер прокидає виняток при помилці
            data = fetch_data(cursor, query, params)
            self.data = data # Зберігаємо дані

            # Оновлюємо UI в головному потоці
            wx.CallAfter(self._update_grid_with_data)

            if not data:
                wx.CallAfter(self._show_message, "Немає даних, що відповідають критеріям фільтрації.")
                # Мітка кількості записів оновиться у _update_grid_with_data

        except Exception as e:
            error_message = f"Помилка під час виконання запиту або обробки даних: {e}"
            wx.CallAfter(self._show_message, error_message)
            wx.CallAfter(self.record_count_label.SetLabel, "Помилка під час обробки даних")
            # У випадку помилки завантаження даних, також очищаємо сітку
            wx.CallAfter(self._update_grid_with_data)

        finally:
            if cursor:
                try: cursor.close()
                except Exception as e: print(f"Error closing cursor: {e}")
            if conn:
                try: conn.close()
                except Exception as e: print(f"Error closing connection: {e}")


    # --- Метод _show_message (без змін) ---
    def _show_message(self, message):
        # Перевіряємо, чи вікно ще існує перед показом повідомлення
        # IsBeingDeleted є в newer wxPython versions. if self is None або try/except
        # може знадобитися для старіших версій або інших сценаріїв закриття.
        if hasattr(self, 'IsBeingDeleted') and self.IsBeingDeleted():
            return
        if self and not self.IsBeingDeleted():
            wx.MessageBox(message, "Інформація", wx.OK | wx.ICON_INFORMATION)


    # --- Метод для експорту в Excel (базовий приклад, можна додати) ---
    def on_export_excel(self, event):
        if self.data is None or not self.data:
            wx.MessageBox("Немає даних для експорту.", "Інформація", wx.OK | wx.ICON_INFORMATION)
            return

        if self.zvit_dir:
            defaultDir = self.zvit_dir
        else:
            defaultDir = os.getcwd()
        with wx.FileDialog(self, "Зберегти звіт у Excel",
                           wildcard="Excel files (*.xlsx)|*.xlsx",
                           style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
                           defaultDir=defaultDir,
                           defaultFile="звіт.xlsx") as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return # Користувач скасував

            pathname = fileDialog.GetPath()
            try:
                wb = Workbook()
                ws = wb.active
                ws.title = "Звіт"

                # Додаємо заголовок звіту
                if hasattr(self, 'pre_titlestr') and self.pre_titlestr:
                    ws.append([self.pre_titlestr])
                    ws['A1'].font = Font(bold=True)
                    # Об'єднуємо комірки для заголовка
                    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(self.column_labels))
                    # Вирівнюємо заголовок по центру
                    ws['A1'].alignment = Alignment(horizontal='center', vertical='center')
                    header_row_index = 2 # Заголовки колонок будуть у другому рядку
                else:
                    header_row_index = 1 # Заголовки колонок будуть у першому рядку

                # Додаємо заголовки колонок
                ws.append(self.column_labels)
                header_font = Font(bold=True)
                header_alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
                for col_idx, cell in enumerate(ws[header_row_index]):
                    cell.font = header_font
                    cell.alignment = header_alignment
                    # Приблизний підбір ширини колонок (можна вдосконалити)
                    col_letter = get_column_letter(col_idx + 1)
                    ws.column_dimensions[col_letter].width = 20

                # Додаємо дані
                data_alignment = Alignment(vertical='top', wrap_text=True)
                # Використовуємо self.active_columns, щоб брати дані з row у правильному порядку
                for row in self.data:
                    excel_row_data = []
                    for data_index in self.active_columns:
                        try:
                            # Перевірка, щоб data_index не виходив за межі row на всяк випадок
                            value = row[data_index] if data_index < len(row) else ""
                            excel_row_data.append(str(value if value is not None else ''))
                        except Exception as e:
                            excel_row_data.append("Error") # Індикатор помилки

                    ws.append(excel_row_data)

                # Налаштування ширини колонок для експорту (можна синхронізувати з шириною в гриді)
                # Приблизний перерахунок пікселів у одиниці Excel (може відрізнятися)
                PIXELS_TO_EXCEL_UNITS = 7 # Наприклад
                MAX_EXCEL_WIDTH = MAX_WIDTH / PIXELS_TO_EXCEL_UNITS
                # ---  індекси, що потребують переносу
                self.long_text_source_indices = [5] 

                for i, original_col_index in enumerate(self.active_columns):
                    col_letter = get_column_letter(i + 1)
                    if original_col_index in self.long_text_source_indices:
                        ws.column_dimensions[col_letter].width = MAX_EXCEL_WIDTH
                    # Можна додати автопідбір ширини для інших колонок, якщо потрібно


                # Застосування стилів до даних
                for row_idx in range(header_row_index + 1, ws.max_row + 1): # Починаємо після заголовків
                     for col_idx in range(1, ws.max_column + 1):
                        ws.cell(row=row_idx, column=col_idx).alignment = data_alignment

                # Зберігаємо файл
                wb.save(pathname)

                wx.CallAfter(wx.MessageBox, f"Звіт успішно збережено в {pathname}", "Успіх", wx.OK | wx.ICON_INFORMATION)

            except Exception as e:
                error_msg = f"Помилка при збереженні звіту: {e}"
                wx.CallAfter(wx.MessageBox, error_msg, "Помилка", wx.OK | wx.ICON_ERROR)



# --------------- конец класса ReportGeneratorWx ------------


def build_query(filters, zvit_fields):

    # Инициализируем словарь параметров ОДИН РАЗ в начале
    params = {}

    not_protokol = ""

    # Добавляем параметры даты в словарь params
    start_date = filters.get("start_date")
    end_date = filters.get("end_date")
    params.update({"date_0": start_date, "date_1": end_date})

    # сортуємо за прізвищем згідно українського алфавіта
    id_order_name_alph = "ORDER BY \
                 CASE \
                   WHEN p.name GLOB '[А-Д]*' THEN 1 \
                   WHEN p.name GLOB 'Є*' THEN 2 \
                   WHEN p.name GLOB '[Е-З]*' THEN 3 \
                   WHEN p.name GLOB 'І*' THEN 4 \
                   WHEN p.name GLOB '[И-Я]*' THEN 5 \
                   ELSE 6 \
                 END, p.name"

    # параметр виборки за ПІДРОЗДІЛОМ
    unit_sel = filters.get("unit", "")
    unit_condition = ""
    if unit_sel:
        unit_condition = "AND p.unit = :unit"
        params["unit"] = unit_sel # Добавляем параметр для связывания

    # ---------- параметр виборки за ЗВАННЯМ / ЦИВІЛЬНІ / УСІ
    id_rank_condition = ""
    rank_sel = ""
    RankRegularStr = []
    rank_params = {}

    person_category = filters.get("person_category")
    civilian = filters.get("civilian")

    if person_category == 1:
        RankRegularStr = ['%полковник', 'майор', 'капітан%', '%лейтенант']
        rank_sel = "офіцери"

    elif person_category == 2:
        RankRegularStr = ['%сержант']
        rank_sel = "сержанти"

    elif person_category == 3:
        RankRegularStr = ['%солдат', '%матрос']
        rank_sel = "солдати"

    elif person_category == 4:
        id_rank_condition = "AND LENGTH(IFNULL(p.rank , '')) <> 0"
        rank_sel = "усі військові"

    elif civilian:
        id_rank_condition = "AND (p.rank IS NULL OR TRIM(p.rank) = '')"
        rank_sel = "цивільні"
        unit_sel = "" 
        unit_condition = "" 

    else:
        rank_sel = "усі особи"
        unit_sel = "" 
        unit_condition = "" 

    if RankRegularStr:
        conditions = []
        for i, pattern in enumerate(RankRegularStr):
            key = f"rank{i}"
            conditions.append(f"LOWER(p.rank) LIKE :{key}")
            rank_params[key] = pattern.lower()
        id_rank_condition = "AND (" + " OR ".join(conditions) + ")"

    params.update(rank_params)

    # ------ параметр виборки по НАЗВІ нагороди
    # ВИБІРКА ЗА НАЗВОЮ НАГОРОДИ
    award_id = filters.get("award_id")
    id_award_condition = "AND m.id_award = :id_award"


    # ------ параметри виборки по РАНГУ нагороди з урахуванням фільтру протоколи видачі
    id_rank_award_condition = "" # Инициализация строки условия для ранга награды
    award_ranking_value = None # Переменная для хранения числового значения ранга награды
    award_rank_filter_value = filters.get("award_rank") # Получаем строковое значение ранга из фильтров

    is_issue_protocols_filter = filters.get("issue_protocols", False) # Стан чекбокса "Протоколи видачі"

    # Визначаємо числові індекси для цільових рангів, якщо чекбокс активний
    target_ranks_for_protocol_indices = []
    if is_issue_protocols_filter:
        try:
            target_ranks_for_protocol_indices.append(RankingValues.index("Найвища"))
            target_ranks_for_protocol_indices.append(RankingValues.index("Президент"))
            target_ranks_for_protocol_indices.append(RankingValues.index("МОУ/ГК/ГШ"))
        except ValueError:
            target_ranks_for_protocol_indices = [] # Очистити список, щоб не застосовувати фільтр

    # --- Основна логіка фільтрації нагород по РАНГУ та протоколам ---
    if is_issue_protocols_filter and target_ranks_for_protocol_indices:
        # Якщо чекбокс "Протоколи видачі" активний, формуємо складну умову
        # Ця умова буде містити і IN(), і handover, розділені " AND ".
        # Вона не починається з "AND ", як і інші умови, що додаються до awarding_where_conditions.
        id_rank_award_condition = (
            f"a.ranking IN ({','.join([':' + f'ranking_p{i}' for i in range(len(target_ranks_for_protocol_indices))] )})"
            f" AND (m.handover IS NULL OR m.handover NOT LIKE '%$%')"
        )
        for i, rank_idx in enumerate(target_ranks_for_protocol_indices):
            params[f"ranking_p{i}"] = rank_idx
        not_protokol = "(відсутні протоколи видачі)"

    else:
        # Якщо чекбокс "Протоколи видачі" НЕ активний, тоді застосовуємо фільтр по рангу з комбобокса
        if award_rank_filter_value and award_rank_filter_value.strip():
            try:
                award_ranking_value = RankingValues.index(award_rank_filter_value)
                id_rank_award_condition = "a.ranking = :ranking" # Умова без "AND "
                params["ranking"] = award_ranking_value
            except ValueError:
                pass # Ранг не знайдено або порожній, фільтр не застосовується
    # --- Кінець  логіки фільтрації нагород по РАНГУ  ---
 

   # ------- параметр виборки ЗА ВИКОНАВЦЕМ
    id_worker_condition = "" # Инициализация строки условия
    id_worker_map = {"Усі": "_", "ВП": "0", "МПЗ": "1", "Інші": "2"}
    worker_filter_value = filters.get("worker", "")
    id_worker_value = id_worker_map.get(worker_filter_value, "") # Получаем значение для параметра

    if worker_filter_value and id_worker_value != "_":
        # Используем именованный параметр для значения worker
        id_worker_condition = "AND pr.worker = :worker_id"
        params["worker_id"] = int(id_worker_value) # Добавляем значение в params для binding

    worker_filter_active = worker_filter_value and id_worker_value != "_"

    # --- Определяем режим запроса ---
    mode = filters.get('mode')
    handover_status = filters.get('handover_status') # Получаем статус вручения
    specific_submission = filters.get('specific_submission')

    query = ""
    pre_titlestr = "" # Дефолтное значение заголовка

    # -- ЗАПИТИ ---

    # ОДНЕ!!! подання ЗА НОМЕРОМ
    if specific_submission:

        # В этом блоке отдельный запрос, который не использует большинство других фильтров
        params = {} # Переинициализируем params для этого специфического запроса

        submission_number_full = filters.get('submission_number', '')
        number_pres = submission_number_full.split(' від')[0] if ' від' in submission_number_full else submission_number_full

        params["number_pres"] = number_pres

        pre_titlestr = f"ПОДАННЯ №{filters.get('submission_number', '')}"

        query = """
            SELECT p.name, p.rank, p.unit, pr.registration,
                 pr.date_registration, pr.text_presentation, pr.report,
                 m.decree, m.date_decree,
                 a.denotation, -- Назва нагороди (індекс 11)
                 m.date_handover, -- Дата вручення (індекс 12)
                 p2.name, -- вибираємо ім'я отримувача (індекс 13)
                 m.consignment_note, m.number_meed, m.dead, p.inn, p.date_birth -- Індекси 15-19
            FROM presentation pr
            JOIN personality p ON pr.id_personality = p.id -- Основне з'єднання з personality
            LEFT JOIN meed m ON pr.id_meed = m.id -- З'єднання з meed
            LEFT JOIN award a ON m.id_award = a.id -- З'єднання з award
            LEFT JOIN personality p2 ON p2.id = m.handover -- З'єднання з personality 
            WHERE pr.registration = :number_pres
            {order_name_alph}
            """.format(order_name_alph=id_order_name_alph)

        return query, params, pre_titlestr


    # --- ОБЪЕДИНЕННЫЙ БЛОК РЕЖИМА "AWARDING" ---

    elif mode == "awarding":

        # Список для сбора строковых условий WHERE для этого блока
        awarding_where_conditions = []
        # Словарь для параметров, специфичных для этого блока (добавится к глобальным params)
        award_params_awarding = {}

        # ---------- ПОСМЕРТНІ

        # Определяем условие "Посмертно" если фильтр активен в UI
        awarding_dead_status_condition = ""
        if filters.get('posthumous'): 
            awarding_dead_status_condition = "m.dead = '1'" 

        # presentation_subquery_where определяется здесь локально на основе worker_filter_active
        presentation_subquery_where = "" 
        if worker_filter_active:
            presentation_subquery_where = "WHERE worker = :worker_id"

        if not filters.get("all_time") and handover_status != 1:
            awarding_where_conditions.append("m.date_decree BETWEEN :date_0 AND :date_1")

        # --- Определяем основную часть WHERE в зависимости от handover_status ---
        if handover_status == 3:
            # Логика для "ПРИЗНАЧЕНІ НАГОРОДИ"
            pre_titlestr = f'ПРИЗНАЧЕНІ нагороди {unit_sel}'

        else: # handover_status != 3 
            # Логика для "ЗАЛИШОК / ВРУЧЕНІ НАГОРОДИ"

            # Основное условие WHERE (наличие номера накладной)
            awarding_where_conditions.append("m.consignment_note IS NOT NULL AND m.consignment_note <> ''")

            # Условие по статусу вручения (1 или 2)
            consignment_note_filter = filters.get("consignment_note") # Получаем фильтр по накладной

            if handover_status == 1: # ЗАЛИШОК
                awarding_where_conditions.append("(m.handover IS NULL OR m.handover = '')")
                pre_titlestr = f"ЗАЛИШОК нагород В НАТУРІ {unit_sel}" # unit_sel определен выше

                # Если фильтр по накладной активен для ЗАЛИШКУ
                if consignment_note_filter:
                     awarding_where_conditions.append("m.consignment_note = :consignment_note")
                     award_params_awarding["consignment_note"] = consignment_note_filter

            elif handover_status == 2: # ВРУЧЕНІ
                 awarding_where_conditions.append("m.handover IS NOT NULL AND m.handover <> ''")
                 pre_titlestr = f'ВРУЧЕНІ нагороди {unit_sel} {not_protokol}' # unit_sel определен выше

                 # Если фильтр по накладной активен для ВРУЧЕНИХ
                 if consignment_note_filter:
                      awarding_where_conditions.append("m.consignment_note = :consignment_note")
                      award_params_awarding["consignment_note"] = consignment_note_filter

        # --- Добавляем другие общие фильтры, которые могут применяться в режиме awarding ---
 
        # Фильтр по подразделению (определен выше)
        if unit_condition:
            awarding_where_conditions.append(unit_condition)

        # Фильтр по званию/категории (определен выше)
        if id_rank_condition:
            awarding_where_conditions.append(id_rank_condition)

        # Фильтр по рангу награды (определен выше)
        if id_rank_award_condition:
            awarding_where_conditions.append(id_rank_award_condition)        

        if awarding_dead_status_condition:
            awarding_where_conditions.append(awarding_dead_status_condition) # id_dead_status уже содержит "AND ..."

        # Фильтр по ID награды (получен в _update_award_image)
        award_id_filter_value = filters.get("award_id")
        if award_id_filter_value is not None: # Проверяем, что значение не None
            awarding_where_conditions.append("AND m.id_award = :award_id") # Добавляем условие
            award_params_awarding["award_id"] = award_id_filter_value # Добавляем параметр

        # Объединяем собранные условия в одну строку WHERE
        # Начинаем с "WHERE", если есть хоть одно условие.
        awarding_where_string = ""
        if awarding_where_conditions:
            # Удаляем "AND " из начала каждого условия перед объединением, кроме первого.
            # Или просто объединяем все с " AND ", а "WHERE" добавим перед первым.
            # Проще: объединить все после WHERE, а само WHERE добавить, если список не пуст.
            # Условия в списке уже содержат "AND ". Удалим "AND " из начала каждого и объединим их " AND ".
            cleaned_conditions = [cond.replace("AND ", "", 1) if cond.startswith("AND ") else cond for cond in awarding_where_conditions]
            awarding_where_string = "WHERE " + " AND ".join(cleaned_conditions)

        # Добавляем параметры, специфичные для этого блока, в основной словарь params
        params.update(award_params_awarding)

        # --- Конструируем строку запроса для объединенного режима awarding ---

        query = f"""
            SELECT
                p.name, p.rank, p.unit,
                pr.registration, pr.date_registration, pr.text_presentation, pr.report,
                m.decree, m.date_decree,
                a.denotation, -- Назва нагороди (індекс 11)
                m.date_handover, -- Дата вручення (індекс 12)
                p2.name, -- вибираємо ім'я отримувача  (індекс 13)
                m.consignment_note, m.number_meed, m.dead, p.inn, p.date_birth -- Індекси 15-19
            FROM meed m
            JOIN personality p ON m.id_personality = p.id -- Основне з'єднання з personality
            JOIN award a ON m.id_award = a.id -- З'єднання з award
            LEFT JOIN (
                SELECT id, id_personality, id_meed, worker,
                  registration, date_registration, text_presentation, report, id_meed
                FROM presentation
                {presentation_subquery_where}
            ) pr ON m.id = pr.id_meed
            LEFT JOIN personality p2 ON p2.id = m.handover -- з'єднання з personality 
            {awarding_where_string}
            {id_order_name_alph}
            """

    # ---  вибираємо ПОДАННЯ ЗА УМОВАМИ!!!

    elif mode == 'submission':

        id_meed_status = ""
        label_selected_presvarR2 = "УСІ подання"

        submission_status_filter = filters.get('submission_status')

        if submission_status_filter == 1:
            id_meed_status = "AND pr.id_meed > 0"
            label_selected_presvarR2 = "ПОГОДЖЕНІ подання"

        elif submission_status_filter == 2:
            id_meed_status = "AND pr.id_meed = '0'" # Или == 0 если число
            label_selected_presvarR2 = "НЕ ПОГОДЖЕНІ подання"

        elif submission_status_filter == 3:
            id_meed_status = "AND (pr.id_meed IS NULL OR TRIM(pr.id_meed) = '')"
            label_selected_presvarR2 = "подання У ЗАЛИШКУ"

        pre_titlestr = f'{label_selected_presvarR2} -вик.{filters.get("worker", "")}'

        if filters.get('posthumous'):
            id_dead_status = "AND pr.report == 'посмертно'"  
            pre_titlestr += " -посмертно"
        else:
           id_dead_status = ""

        pre_titlestr += f" -{filters.get('start_date')}_{filters.get('end_date')}"

        if filters.get('person_category'):
            pre_titlestr += f" -{filters.get('person_category')}"

        if filters.get('unit'):
            pre_titlestr += f" -{filters.get('unit')}"        

        submission_conditions_list = [] # Список для збору умов БЕЗ початкових "AND "

        # Умова за діапазоном дат (якщо не "Увесь час") - ця умова завжди є в submission, якщо не all_time
        if not filters.get("all_time"):
            submission_conditions_list.append("pr.date_registration BETWEEN :date_0 AND :date_1")

        # Умови за статусом погодження (submission_status)
        # id_meed_status вже визначено вище і має формат "AND умова" або ""
        # Прибираємо "AND " перед додаванням до списку
        if id_meed_status:
            cleaned_meed_status = id_meed_status.lstrip().replace("AND ", "", 1).strip()
            if cleaned_meed_status:
                submission_conditions_list.append(cleaned_meed_status)

        # Умова посмертно - id_dead_status вже визначено вище і має формат "AND умова" або ""
        if id_dead_status:
            cleaned_dead_status = id_dead_status.lstrip().replace("AND ", "", 1).strip()
            if cleaned_dead_status:
                submission_conditions_list.append(cleaned_dead_status)

        # Додаємо умови, визначені раніше (unit_condition, id_rank_condition, id_worker_condition)
        # Ці змінні вже містять "AND умова" або "".
        # Потрібно прибрати "AND " перед додаванням до списку submission_conditions_list
        if unit_condition:
             cleaned_unit_condition = unit_condition.lstrip().replace("AND ", "", 1).strip()
             if cleaned_unit_condition:
                 submission_conditions_list.append(cleaned_unit_condition)

        if id_rank_condition:
             cleaned_rank_condition = id_rank_condition.lstrip().replace("AND ", "", 1).strip()
             if cleaned_rank_condition:
                 submission_conditions_list.append(cleaned_rank_condition)

        if id_worker_condition:
             # id_worker_condition визначається як "AND pr.worker = :worker_id" або "".
             cleaned_worker_condition = id_worker_condition.lstrip().replace("AND ", "", 1).strip()
             if cleaned_worker_condition:
                 submission_conditions_list.append(cleaned_worker_condition)


        # !!! Фінальне формування рядка WHERE !!!
        submission_where_string = ""
        if submission_conditions_list: # Якщо є хоча б одна умова
            # Об'єднуємо всі умови в списку за допомогою " AND "
            # Додаємо "WHERE " попереду, якщо список умов не порожній
            submission_where_string = "WHERE " + " AND ".join(submission_conditions_list)
        # Якщо список умов порожній, submission_where_string залишається "".


        # Этот запрос использует {submission_where_string}
        query = f"""
             SELECT p.name, p.rank, p.unit, pr.registration,
                  pr.date_registration, pr.text_presentation, pr.report,
                  m.decree, m.date_decree,
                  a.denotation, -- Назва нагороди (індекс 11)
                  m.date_handover, -- Дата вручення (індекс 12)
                  CASE WHEN p2.name IS NOT NULL THEN p2.name ELSE m.handover END, -- Ім'я вручанта або оригінальне значення (13)
                  m.consignment_note, m.number_meed, m.dead, p.inn, p.date_birth -- Індекси 15-19
             FROM presentation pr
             JOIN personality p ON pr.id_personality = p.id
             LEFT JOIN meed m ON m.id = pr.id_meed
             LEFT JOIN award a ON m.id_award = a.id
             LEFT JOIN personality p2 ON p2.id = m.handover -- друге з'єднання з personality 
             {submission_where_string} -- Вставляємо сформовану WHERE клаузу
             {id_order_name_alph} -- Вставляємо ORDER BY клаузу
             """
    # --- КОНЕЦ БЛОКОВ РЕЖИМОВ ---
    # Если ни один из режимов не был выбран (mode не 'specific_submission', 'awarding', 'submission')
    else:
        query = ""
        params = {} # или params = {} в начале функции и не изменять его, если нет фильтров
        pre_titlestr = "Не выбран режим выборки"

    # Возвращаем сформированный запрос, параметры и заголовок
    # Это должно быть в конце функции build_query
    return query, params, pre_titlestr

def fetch_data(cursor, query, params=None):
    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        result = cursor.fetchall()
        return result

    except Exception as e:
        return None # Або обробіть помилку іншим чином








# ---------------------------------------------------
# ---------------------------------------------------
# ----------------- ОБРОБКА ЗОБРАЖЕНЬ----------------
# ---------------------------------------------------
# ---------------------------------------------------


def load_image_from_blob(image_blob, max_dim=80, grayscale=False, brightness_factor=1.0):
    """
    Завантажує зображення з BLOB, масштабує його зі збереженням пропорцій
    під максимальний розмір, забезпечує прозорий фон, опціонально робить сірим
    та регулює яскравість, потім повертає wx.Bitmap.
    """
    if image_blob is None:
        return wx.Bitmap(max_dim, max_dim)

    try:
        img_stream = io.BytesIO(image_blob)
        image = Image.open(img_stream)
        width, height = image.size

        if max(width, height) > max_dim:
            scale = max_dim / max(width, height)
            new_width = int(width * scale)
            new_height = int(height * scale)
            try:
                image = image.resize((new_width, new_height), resample=Image.Resampling.LANCZOS)
            except AttributeError:
                image = image.resize((new_width, new_height), resample=Image.LANCZOS)
        elif max(width, height) == 0:
            return wx.Bitmap(max_dim, max_dim)

        image = image.convert("RGBA")

        if grayscale:
            image = image.convert("LA")

        if brightness_factor != 1.0:
            if image.mode == "LA":
                image = image.convert("RGBA")
            enhancer = ImageEnhance.Brightness(image)
            image = enhancer.enhance(brightness_factor)

        if image.mode == "RGBA":
            rgb_data = image.convert("RGB").tobytes()
            alpha_data = image.getchannel("A").tobytes()
            wx_image = wx.Image(image.width, image.height)
            wx_image.SetData(rgb_data)
            wx_image.SetAlpha(alpha_data)
        elif image.mode == "LA":
            image = image.convert("RGBA")
            rgb_data = image.convert("RGB").tobytes()
            alpha_data = image.getchannel("A").tobytes()
            wx_image = wx.Image(image.width, image.height)
            wx_image.SetData(rgb_data)
            wx_image.SetAlpha(alpha_data)
        elif image.mode == "L":
            rgb_data = image.convert("RGB").tobytes()
            wx_image = wx.Image(image.width, image.height)
            wx_image.SetData(rgb_data)
        else:
            rgb_data = image.convert("RGB").tobytes()
            wx_image = wx.Image(image.width, image.height)
            wx_image.SetData(rgb_data)

        bitmap = wx.Bitmap(wx_image)
        return bitmap

    except Exception as e:
        error_bitmap = wx.Bitmap(max_dim, max_dim)
        dc = wx.MemoryDC(error_bitmap)
        dc.SetBackground(wx.Brush(wx.RED))
        dc.Clear()
        dc.SetTextForeground(wx.WHITE)
        dc.DrawText("Помилка", 5, 5)
        dc.SelectObject(wx.NullBitmap)
        return error_bitmap


# --------------- ОБРОБКА ТЕКСТУ

def on_highlight(richtext_ctrl, word_to_find, text_to_highlight, highlight_color):
    """Виділяє всі входження word_to_find в тексті text_to_highlight кольором highlight_color."""
    start_index = 0 # Початковий індекс для пошуку

    # Створюємо об'єкт стилю тексту
    text_attr = wx.TextAttr()
    # Встановлюємо колір тексту для виділення
    text_attr.SetTextColour(highlight_color)

    # Пошук та виділення всіх входжень слова
    while True:
        # Знаходимо наступне входження слова, починаючи з start_index
        start_index = text_to_highlight.find(word_to_find, start_index)
        # Якщо слово не знайдено, виходимо з циклу
        if start_index == wx.NOT_FOUND:
            break

        # Визначаємо кінцевий індекс знайденого слова
        end_index = start_index + len(word_to_find)
        # Застосовуємо стиль виділення до знайденого фрагмента тексту
        richtext_ctrl.SetStyle(start_index, end_index, text_attr)
        # Оновлюємо start_index для пошуку наступного входження після поточного
        start_index = end_index

        