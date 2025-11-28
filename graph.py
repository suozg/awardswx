# graph.py

import wx
import wx.lib.plot as plot
from database_logic import AwardDataLoader  

class AwardGraphPanel(wx.Panel):
    def __init__(self, parent, cursor, start_year, element_controls): 
        super().__init__(parent, wx.ID_ANY) 
        self.cursor = cursor 
        self.START_YEAR = start_year 
        self.element_controls = element_controls
        self.data_loader = AwardDataLoader(self.START_YEAR) 

        try:
            self.data_loader.load_data(self.cursor) 

        except RuntimeError as e:
            wx.MessageBox(str(e), "Помилка завантаження даних графіка", wx.OK | wx.ICON_ERROR)

        self.init_ui()

    def init_ui(self):
        sizer = wx.BoxSizer(wx.VERTICAL)

        # Создание canvas для графика
        self.plot_canvas = plot.PlotCanvas(self, wx.ID_ANY) 
        sizer.Add(self.plot_canvas, 1, wx.EXPAND | wx.ALL, 10)

        # Получаем данные для графика ЧЕРЕЗ self.data_loader
        x_data, y_state, y_all, y_present = self.data_loader.get_graph_data() 

        # Проверяем, есть ли данные для построения графика
        if not x_data or not y_all:
            # Добавьте сообщение об ошибке или пустой график
            empty_plot_label = wx.StaticText(self.plot_canvas, wx.ID_ANY, "Немає даних для побудови графіка.")
            # Возможно, нужно скрыть plot_canvas и показать этот label
            sizer.Replace(self.plot_canvas, empty_plot_label) # Пример замены
            self.plot_canvas.Hide()
            sizer.Add(empty_plot_label, 1, wx.ALIGN_CENTER | wx.ALL, 10)
            self.plot_canvas = None 

        else:
            # Создание линий графика с использованием полученных данных
            line1 = plot.PolyLine(list(zip(x_data, y_state)), colour='blue', width=1, legend='Від держави')
            line2 = plot.PolyLine(list(zip(x_data, y_all)), colour='red', width=1, legend='Усі нагороди')
            line3 = plot.PolyLine(list(zip(x_data, y_present)), colour='green', width=1, legend='Подання')

            # Отрисовка графика
            self.plot_canvas.Draw(plot.PlotGraphics([line1, line2, line3], "Динаміка нагороджень", "Рік", "Кількість")) # Добавлены метки осей
            self.plot_canvas.xSpec = ('minmax',) # Устанавливаем спецификации осей
            self.plot_canvas.ySpec = ('minmax',)


        # Легенда (используем данные через self.data_loader)
        legend_panel = wx.Panel(self, wx.ID_ANY) # Создаем на AwardGraphPanel, не на detail_panel
        legend_sizer = wx.BoxSizer(wx.HORIZONTAL)
        # Получаем суммарные данные через self.data_loader
        total_all = sum(y_all) if y_all else 0 # Используем данные из get_graph_data
        total_state = sum(y_state) if y_state else 0 # Используем данные из get_graph_data
        total_present = sum(y_present) if y_present else 0 # Используем данные из get_graph_data

        legend_sizer.Add(wx.StaticText(legend_panel, wx.ID_ANY, label=f"🟥 Усі нагороди ({total_all})"), 0, wx.RIGHT, 10)
        legend_sizer.Add(wx.StaticText(legend_panel, wx.ID_ANY, label=f"🟦 Від держави ({total_state})"), 0, wx.RIGHT, 10)
        legend_sizer.Add(wx.StaticText(legend_panel, wx.ID_ANY, label=f"🟩 Подання ({total_present})"), 0)
        legend_panel.SetSizer(legend_sizer)
        sizer.Add(legend_panel, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.BOTTOM, 10) # Выравнивание по центру горизонтали

        # Слайдер (используем данные через self.data_loader)
        self.slider_panel = wx.Panel(self, wx.ID_ANY) # Создаем на AwardGraphPanel
        slider_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.slider_label = wx.StaticText(self.slider_panel, wx.ID_ANY, label="")
        # Используем x_data для определения диапазона слайдера
        slider_max_value = len(x_data) - 1 if x_data else 0
        self.slider = wx.Slider(self.slider_panel, wx.ID_ANY, value=slider_max_value, minValue=0, maxValue=slider_max_value)
        slider_sizer.Add(self.slider_label, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        slider_sizer.Add(self.slider, 1, wx.EXPAND) # Слайдер должен расширяться
        self.slider_panel.SetSizer(slider_sizer)
        sizer.Add(self.slider_panel, 0, wx.EXPAND | wx.ALL, 10) # Панель слайдера расширяется горизонтально

        # Привязка события слайдера и установка начального значения
        if x_data: # Привязываем слайдер только если есть данные
            self.slider.Bind(wx.EVT_SLIDER, self.on_slider_scroll)
            self.slider.SetFocus() # Устанавливаем фокус на слайдер
            self.on_slider_scroll(None) # Имитируем первое событие для установки начального текста
        else:
            # Если данных нет, отключаем слайдер
            self.slider.Disable()
            self.slider_label.SetLabel("Нет данных за годы для слайдера") # Устанавливаем текст по умолчанию

        self.SetSizer(sizer)
        self.Layout() # Выполняем компоновку
        self.SetMinSize((600, 400)) # Устанавливаем минимальные размеры (SetSizeHints устарел)


    def on_slider_scroll(self, event):
        # Используем данные x_data, y_state, y_all ЧЕРЕЗ self.data_loader
        x_data, y_state, y_all, y_present = self.data_loader.get_graph_data() # Получаем данные

        val = self.slider.GetValue()
        # Проверяем границы, чтобы избежать ошибки индекса
        if not x_data or val < 0 or val >= len(x_data):
             text = "** Нет данных для слайдера **"
             self.slider_label.SetLabel(text)
             self.slider_panel.Layout()
             return

        selected_year = x_data[val]
        # Проверяем индекс снова для безопасности
        if selected_year in x_data:
             index = x_data.index(selected_year) # Находим индекс по году
             y_val_state = y_state[index]
             y_val_all = y_all[index]
             # Избегаем деления на ноль
             percentage = round(y_val_state / y_val_all * 100) if y_val_all else 0
             text = f' ** за {selected_year} рік: {y_val_all} ({y_val_state}, або {percentage}%)'
        else:
             text = f' ** за {selected_year} рік: 0' # Или другое сообщение

        self.slider_label.SetLabel(text)
        self.slider_panel.Layout()


    def get_status_text(self):
        """Возвращает текст статуса, получая данные через AwardDataLoader."""
        return self.data_loader.get_status_text() # <-- Получаем текст статуса через data_loader


# --- Конец класса AwardGraphPanel ---
