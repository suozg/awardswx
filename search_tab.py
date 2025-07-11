# search_tab.py
# Імпортуємо необхідні бібліотеки та модулі
import wx # Бібліотека для створення графічного інтерфейсу (GUI)
import wx.richtext # Модуль для роботи з розширеним текстовим полем (RichTextCtrl)

# Імпортуємо конфігураційні дані та логіку бази даних
from config import START_YEAR, DEF_FUT_LABEL, SHOW_MORE_IMAGES
from database_logic import (
    search_q, get_service_settings_data,
    get_award_image_blobs_for_search
)
from graph import AwardGraphPanel # Панель для відображення графіка нагород
from ui_utils import (
    load_image_from_blob,
    on_highlight
)
from settings_manager import ServiceSettingsManager

class Tab1Panel(wx.Panel):
    """
    Панель для вкладки пошуку героїв та нагород.
    """
    def __init__(self, parent, conn, cursor, settings_manager, fut_place=None):
        super().__init__(parent, wx.ID_ANY) # Используйте wx.ID_ANY
        # Сохраняем переданные объекты соединения и курсора
        self.conn = conn
        self.cursor = cursor
        self.settings_manager = settings_manager
        self.latest_search_results = [] # Атрибути для зберігання результатів пошуку personality
        self.source_data_award_and_presentation = {} #  дані за пошуком з meed и  presentation
        self.skip_next_population = False # переменная управления очисткой
        self.fut_place = fut_place # Зберігаємо посилання на елемент футера
        self.last_message = "" # Змінна для зберігання останнього повідомлення футера
        self.element_controls = [] # Список для зберігання елементів керування, які потрібно очищати
        self.image_sizer_undo_result1 = None # Змінна для зберігання сайзера зображень для можливості його видалення

        # Головний сайзер для всієї панелі
        self.main_panel_sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.main_panel_sizer)

        # Створюємо ScrolledWindow, в якому буде розміщено весь вміст, що прокручується
        self.scroll_win = wx.ScrolledWindow(self, wx.ID_ANY)
        self.scroll_win.SetScrollRate(20, 20) # Встановлюємо швидкість прокрутки (px/крок)
        self.main_panel_sizer.Add(self.scroll_win, 1, wx.EXPAND | wx.ALL, 0) # Додаємо ScrolledWindow до головного сайзера

        # Створюємо сайзер для вмісту всередині ScrolledWindow
        self.content_sizer = wx.BoxSizer(wx.VERTICAL)
        self.scroll_win.SetSizer(self.content_sizer)

        self.init_ui() # Ініціалізуємо користувацький інтерфейс
        self.Bind(wx.EVT_WINDOW_DESTROY, self.OnDestroy)

    # --- Метод для закриття з'єднання з БД ---
    def OnDestroy(self, event):
        # Важливо викликати event.Skip(), щоб подія оброблялася далі по ланцюжку
        event.Skip()

    # --- Методи построения интерфейса вкладки ---
    def init_ui(self):
        """Ініціалізує елементи користувацького інтерфейсу панелі."""
        # Усі елементи, які раніше додавалися до self.sizer1, тепер будуть додаватися до self.content_sizer
        # Поле для введення пошукового запиту
        self.entry1 = wx.TextCtrl(self.scroll_win, style=wx.TE_PROCESS_ENTER) # Змінено батьківський елемент
        self.entry1.SetValue("")
        # Прив'язуємо обробник події натискання Enter у полі введення до методу on_search_button
        self.entry1.Bind(wx.EVT_TEXT_ENTER, self.on_search_button)

        # Статичний текст заголовка панелі
        title1 = wx.StaticText(self.scroll_win, label="ГЕРОЯМ - СЛАВА!") # Змінено батьківський елемент
        # Прив'язуємо обробник події кліка по заголовку до методу on_t_sizer_click
        title1.Bind(wx.EVT_LEFT_DOWN, self.on_t_sizer_click)

        # Кнопка для виконання пошуку
        button1 = wx.Button(self.scroll_win, label="Пошук") # Змінено батьківський елемент
        # Прив'язуємо обробник події натискання кнопки до методу on_search_button
        button1.Bind(wx.EVT_BUTTON, self.on_search_button)

        # Кнопка для очищення результатів
        button2 = wx.Button(self.scroll_win, label="Очистити") # Змінено батьківський елемент
        # Прив'язуємо обробник події натискання кнопки до методу clear_tab1
        button2.Bind(wx.EVT_BUTTON, self.clear_tab1)

        # Горизонтальний сайзер для поля вводу та кнопок
        h_sizer = wx.BoxSizer(wx.HORIZONTAL)
        # Додаємо поле вводу до горизонтального сайзера (розтягується по горизонталі)
        h_sizer.Add(self.entry1, 1, wx.ALL, 5)
        # Додаємо кнопку "Пошук"
        h_sizer.Add(button1, 0, wx.ALL, 5)
        # Додаємо кнопку "Очистити"
        h_sizer.Add(button2, 0, wx.ALL, 5)
        # Додаємо горизонтальний сайзер до головного сайзера (розширюється по горизонталі)
        self.content_sizer.Add(h_sizer, 0, wx.EXPAND | wx.ALL, 10) # Додаємо до content_sizer

        # Додаємо заголовок до content_sizer
        self.content_sizer.Add(title1, 0, wx.CENTER | wx.ALL, 5)


        # Додати зображення лого
        logo_bitmap = None
        # Проверяем, что настройки загружены
        if self.settings_manager and self.settings_manager.is_loaded:
            # Получаем СЫРОЙ BLOB логотипа из менеджера
            logo_blob = self.settings_manager.get_logo_blob()

            search_tab_logo_max_dim = 300 # НУЖНЫЙ РАЗМЕР ЗДЕСЬ!

            if logo_blob:
                # Вызываем load_image_from_blob, добавляя параметры grayscale и brightness_factor
                logo_bitmap = load_image_from_blob(
                    logo_blob,
                    max_dim=search_tab_logo_max_dim,
                    grayscale=True,          # <-- Сделать серым
                    brightness_factor=0.6    # <-- Сделать немного темнее (60% от оригинальной яркости)
                )

        # Создаем контрол wx.StaticBitmap для отображения логотипа
        if logo_bitmap and logo_bitmap.IsOk():
            self.logo_display = wx.StaticBitmap(self.scroll_win, wx.ID_ANY, logo_bitmap) # Змінено батьківський елемент
        else:
            # Placeholder, если логотип не загружен или невалиден
            self.logo_display = wx.StaticBitmap(self.scroll_win, size=(300, 300)) # Змінено батьківський елемент

        # Добавляем контрол логотипа в content_sizer панели
        self.logo_display.Bind(wx.EVT_LEFT_DOWN, self.on_t_sizer_click)
        self.content_sizer.Add(self.logo_display, 0, wx.ALIGN_CENTER | wx.ALL, 5)

        # Поле RichTextCtrl для відображення результатів пошуку
        self.result1 = wx.richtext.RichTextCtrl(self.scroll_win, style=wx.TE_MULTILINE | wx.TE_RICH2 | wx.TE_READONLY) # Змінено батьківський елемент
        # Приховуємо поле результатів за замовчуванням
        self.result1.Hide()
        # Додаємо поле результатів до content_sizer (розтягується)
        self.content_sizer.Add(self.result1, 1, wx.ALL | wx.EXPAND, 10)

        # Встановлюємо сайзер для ScrolledWindow
        self.scroll_win.SetSizerAndFit(self.content_sizer)


    def refresh_logo(self):
        """Перезагружает логотип из базы данных и обновляет отображение."""
        try:
            with self.conn:  # Используем активное подключение к БД
                cursor = self.conn.cursor()
                # ПЕРЕзагружаем настройки (включая логотип)
                self.settings_manager.load_settings(cursor)

            logo_blob = self.settings_manager.get_logo_blob()

            if logo_blob:
                bmp = load_image_from_blob(
                    logo_blob,
                    max_dim=300,
                    grayscale=True,
                    brightness_factor=0.6
                )
                if bmp.IsOk():
                    self.logo_display.SetBitmap(bmp)
                    self.logo_display.Refresh()
        except Exception as e:
            print(f"Ошибка обновления логотипа: {e}")

    def on_search_button(self, event, search_id=None):
        """Обробник події натискання кнопки "Пошук" або Enter у полі вводу."""
        # Отримуємо текст з поля вводу
        search_query = self.entry1.GetValue()
        self.search_id = search_id
        self.clear_tab1()

        message = DEF_FUT_LABEL # Початкове повідомлення
        self.latest_search_results = [] # Очищаємо попередні результати
        self.source_data_award_and_presentation = {} # очищаємо список СИРИХ даних

        try:
            # Виконуємо пошук у базі даних
            self.latest_search_results, stringTab1, imgList, counts_gid01, self.source_data_award_and_presentation = search_q(search_query, self.cursor, self.search_id)
            self.logo_display.Show(False)
            self.result1.SetValue(stringTab1)  # Встановлюємо отриманий текст у поле результатів

            # Виділяємо пошуковий запит у результатах (без урахування регістру)
            if search_query:
                if f"{search_query}".lower() in stringTab1.lower():
                    on_highlight(self.result1, f"{search_query}".lower(), stringTab1.lower(), wx.Colour(255, 255, 0)) # Жовтий колір

            # Виділяємо статуси "ВІДМОВЛЕНО" та "НА РОЗГЛЯДІ" різними кольорами
            if "(ВІДМОВЛЕНО)" in stringTab1:
                on_highlight(self.result1, "(ВІДМОВЛЕНО)", stringTab1, wx.Colour(255, 0, 0)) # Червоний колір
            if "(НА РОЗГЛЯДІ)" in stringTab1:
                on_highlight(self.result1, "(НА РОЗГЛЯДІ)", stringTab1, wx.Colour(0, 255, 0)) # Зелений колір
            if "(невірний)" in stringTab1:
                on_highlight(self.result1, "(невірний)", stringTab1, wx.Colour(255, 0, 0)) # Червоний колір
            # Формуємо повідомлення для футера на основі результатів
            if len(self.latest_search_results) != int(counts_gid01):
                message = f"Знайдено ще {len(self.latest_search_results) - counts_gid01} інші особи без подань чи нагород." # Повідомлення про кількість знайдених

            try:
                image_blobs = get_award_image_blobs_for_search(imgList, counts_gid01, self.cursor)

                # 1. Якщо сайзер зображень існує, видаліть його з батьківського сайзера
                #    та знищіть. Це знищить і всі StaticBitmap всередині нього.
                if hasattr(self, 'image_sizer_undo_result1') and self.image_sizer_undo_result1:
                    try:
                        if self.content_sizer.GetItem(self.image_sizer_undo_result1): # Змінено на content_sizer
                            self.content_sizer.Remove(self.image_sizer_undo_result1)
                        self.image_sizer_undo_result1.Clear(True)
                    except RuntimeError:
                        pass  # або логування

                    self.image_sizer_undo_result1 = None

                # 2. Створюємо місце для майбутніх зображень
                self.image_sizer_undo_result1 = wx.BoxSizer(wx.HORIZONTAL)
                # Додаємо його до content_sizer
                self.content_sizer.Add(self.image_sizer_undo_result1, 0, wx.ALIGN_CENTER | wx.ALL, 10)

                # Если есть бинарные данные изображений (список BLOBов не пуст)
                if image_blobs:
                    blobs_to_show = [image_blobs[0]] if SHOW_MORE_IMAGES is None else image_blobs
                    desired_max_dimension = 100

                    for i, blob in enumerate(blobs_to_show):
                        # Створюємо вертикальний сайзер для кожної пари (номер + зображення)
                        column_sizer = wx.BoxSizer(wx.VERTICAL)

                        # Додаємо порядковий номер до вертикального сайзера
                        num_label = wx.StaticText(self.scroll_win, label=f"{i + 1}.")
                        column_sizer.Add(num_label, 0, wx.ALIGN_CENTER | wx.ALL, 2)

                        # Додаємо зображення до вертикального сайзера
                        bitmap = load_image_from_blob(blob, max_dim=desired_max_dimension)
                        img_ctrl = wx.StaticBitmap(self.scroll_win, bitmap=bitmap)
                        column_sizer.Add(img_ctrl, 0, wx.ALIGN_CENTER | wx.ALL, 5)

                        # Додаємо вертикальний сайзер (стовпець) до основного горизонтального сайзера
                        self.image_sizer_undo_result1.Add(column_sizer, 0, wx.ALIGN_CENTER | wx.ALL, 5)

                self.scroll_win.Layout() # Оновлюємо розташування в ScrolledWindow

            except RuntimeError as err:
                wx.MessageBox(f"Помилка при отриманні або обробці зображень: {err}", "Помилка", wx.OK | wx.ICON_ERROR)
                if self.content_sizer: # Перевірка на всякий випадок
                     self.scroll_win.Layout()

        except Exception as e:
            wx.MessageBox(f"Помилка пошуку: {e}", "Помилка", wx.OK | wx.ICON_ERROR)
            return

        # Оновлюємо змінну last_message
        self.last_message = message
        # Встановлюємо повідомлення у футер
        if self.fut_place:
            self.fut_place.SetLabel(self.last_message)

        # Показуємо поле результатів
        self.result1.Show()
        # Оновлюємо розташування елементів на панелі
        self.scroll_win.Layout() # Оновлюємо розташування в ScrolledWindow
        self.scroll_win.FitInside() # Важливо для коректної роботи прокрутки

        self.skip_next_population = False  # для метод очистки КАРТКА (false - не чистить)


    def on_t_sizer_click(self, event):
        """Обробник події кліка по заголовку. Відображає графік нагород."""
        # Очищаємо панель перед відображенням графіка
        self.clear_tab1()
        self.logo_display.Show(False)
        # Створюємо панель з графіком нагород
        self.graph_panel = AwardGraphPanel(self.scroll_win, self.cursor, START_YEAR, self.element_controls) # Змінено батьківський елемент
        # Додаємо панель графіка до content_sizer (розтягується)
        self.content_sizer.Add(self.graph_panel, 1, wx.ALL | wx.EXPAND, 10)
        # Додаємо панель графіка до списку для подальшого очищення
        self.element_controls.append(self.graph_panel)

        message = DEF_FUT_LABEL # Початкове повідомлення

        # Отримуємо текст статусу з панелі графіка
        self.last_message = self.graph_panel.get_status_text()
        # Якщо є елемент футера, встановлюємо текст статусу в нього
        if self.fut_place:
            self.fut_place.SetLabel(self.last_message)

        # Оновлюємо розташування елементів на панелі
        self.scroll_win.Layout() # Оновлюємо розташування в ScrolledWindow
        self.scroll_win.FitInside() # Важливо для коректної роботи прокрутки


    def clear_tab1(self, event=None):
        """Очищає вміст панелі пошуку."""
        # Очищаємо поле вводу
        self.entry1.Clear()

        # Видаляємо всі елементи керування зі списку element_controls
        for ctrl in self.element_controls:
            if ctrl and ctrl.IsShown(): # Перевіряємо, чи елемент існує і видимий
                ctrl.Destroy() # Видаляємо елемент
        self.element_controls.clear() # Очищаємо список

        # Якщо існує сайзер зображень, видаляємо його
        if self.image_sizer_undo_result1 is not None:
            # Від'єднуємо сайзер від content_sizer
            self.content_sizer.Detach(self.image_sizer_undo_result1)
            # Очищаємо сам сайзер (видаляємо з нього елементи)
            self.image_sizer_undo_result1.Clear(True)
            # Обнуляємо посилання на сайзер зображень
            self.image_sizer_undo_result1 = None
            # Оновлюємо розташування елементів
            self.scroll_win.Layout() # Оновлюємо розташування в ScrolledWindow


        # Приховуємо поле результатів
        self.result1.Hide()
        # Очищаємо текст у полі результатів
        self.result1.Clear()
        self.logo_display.Show(True)

        # Встановлюємо текст за замовчуванням у футері
        # візуально
        if self.fut_place:
            self.fut_place.SetLabel(DEF_FUT_LABEL)
        # і оновлюємо внутрішню змінну last_message
        self.last_message = DEF_FUT_LABEL

        # Оновлюємо розташування елементів на панелі
        self.scroll_win.Layout() # Оновлюємо розташування в ScrolledWindow
        self.scroll_win.FitInside() # Важливо для коректної роботи прокрутки

        self.skip_next_population = True  #  для очистки КАРТКА


    def get_footer_message(self):
        """ для відновлення повідомлення у футері після перемикання вкладки."""
        return self.last_message # Повертаємо значення змінної last_message


    # ---  МЕТОД ДЛЯ ПЕРЕДАЧИ РЕЗУЛЬТАТІВ ПОИСКА ---
    def get_latest_search_results(self):
        if self.skip_next_population:
            return None, None
        else:
            """Повертає список останніх результатів пошуку."""
            # Повертаємо збережені списки id та вибраним даним
            return self.latest_search_results, self.source_data_award_and_presentation