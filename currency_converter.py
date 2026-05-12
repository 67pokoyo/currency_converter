import json
import os
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from typing import Dict, List, Optional
import requests
from threading import Thread

DATA_FILE = "conversion_history.json"
API_KEY = "YOUR_API_KEY"  # Замените на свой ключ (бесплатный: https://app.exchangerate-api.com/sign-up)
API_URL = f"https://v6.exchangerate-api.com/v6/{API_KEY}/latest/"


class CurrencyModel:
    """Модель для работы с данными и API"""

    def __init__(self):
        self.history: List[Dict] = []
        self.rates: Dict = {}
        self.supported_currencies: List[str] = []
        self.load_history()

    def load_history(self):
        """Загрузка истории из JSON"""
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    self.history = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Ошибка загрузки истории: {e}")
                self.history = []

    def save_history(self):
        """Сохранение истории в JSON"""
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
            return True
        except IOError as e:
            print(f"Ошибка сохранения: {e}")
            return False

    def fetch_rates(self, base_currency: str) -> bool:
        """Получение курсов валют из API"""
        try:
            response = requests.get(f"{API_URL}{base_currency}", timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("result") == "success":
                    self.rates = data.get("conversion_rates", {})
                    # Обновляем список поддерживаемых валют
                    self.supported_currencies = sorted(list(self.rates.keys()))
                    return True
            return False
        except requests.exceptions.RequestException as e:
            print(f"Ошибка API: {e}")
            return False

    def convert(self, amount: float, from_currency: str, to_currency: str) -> Optional[float]:
        """Конвертация валюты"""
        if from_currency == to_currency:
            return amount

        # Получаем курс
        if from_currency != "USD":  # API обычно базируется на USD
            # Сначала конвертируем в USD, затем в целевую валюту
            if from_currency in self.rates and to_currency in self.rates:
                usd_amount = amount / self.rates[from_currency]
                result = usd_amount * self.rates[to_currency]
                return round(result, 2)
        else:
            if to_currency in self.rates:
                return round(amount * self.rates[to_currency], 2)
        return None

    def add_to_history(self, from_curr: str, to_curr: str, amount: float, result: float, rate: float):
        """Добавление операции в историю"""
        record = {
            "id": len(self.history) + 1,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "from_currency": from_curr,
            "to_currency": to_curr,
            "amount": amount,
            "result": result,
            "rate": rate
        }
        self.history.insert(0, record)  # Новые записи в начало
        self.save_history()

    def clear_history(self):
        """Очистка истории"""
        self.history = []
        self.save_history()

    def delete_history_item(self, item_id: int):
        """Удаление конкретной записи из истории"""
        self.history = [h for h in self.history if h.get("id") != item_id]
        self.save_history()


class CurrencyConverter:
    """Контроллер и UI приложения"""

    def __init__(self, root):
        self.root = root
        self.root.title("Currency Converter")
        self.root.geometry("900x650")
        self.root.resizable(True, True)

        self.model = CurrencyModel()
        self.current_rates_loaded = False

        self.setup_ui()
        self.load_currencies()

    def setup_ui(self):
        """Настройка интерфейса"""
        # Основной контейнер
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Статусная строка
        self.status_var = tk.StringVar()
        self.status_var.set("Готов к работе. Загрузка курсов валют...")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # Верхняя панель: конвертация
        conv_frame = ttk.LabelFrame(main_frame, text="🔄 Конвертация валют", padding=15)
        conv_frame.pack(fill=tk.X, pady=(0, 10))

        # Сумма
        ttk.Label(conv_frame, text="Сумма:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky=tk.W, padx=5,
                                                                              pady=5)
        self.amount_entry = ttk.Entry(conv_frame, width=20, font=("Arial", 12))
        self.amount_entry.grid(row=0, column=1, padx=5, pady=5)
        self.amount_entry.insert(0, "1")

        # Из валюты
        ttk.Label(conv_frame, text="Из валюты:", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky=tk.W, padx=5,
                                                                                  pady=5)
        self.from_currency_var = tk.StringVar()
        self.from_currency_combo = ttk.Combobox(conv_frame, textvariable=self.from_currency_var,
                                                width=15, state="readonly")
        self.from_currency_combo.grid(row=1, column=1, padx=5, pady=5)
        self.from_currency_combo.bind("<<ComboboxSelected>>", self.on_currency_change)

        # В валюту
        ttk.Label(conv_frame, text="В валюту:", font=("Arial", 10, "bold")).grid(row=2, column=0, sticky=tk.W, padx=5,
                                                                                 pady=5)
        self.to_currency_var = tk.StringVar()
        self.to_currency_combo = ttk.Combobox(conv_frame, textvariable=self.to_currency_var,
                                              width=15, state="readonly")
        self.to_currency_combo.grid(row=2, column=1, padx=5, pady=5)

        # Кнопка конвертации
        self.convert_btn = ttk.Button(conv_frame, text="💱 Конвертировать", command=self.convert, width=20)
        self.convert_btn.grid(row=3, column=0, columnspan=2, pady=10)

        # Результат
        self.result_var = tk.StringVar()
        self.result_var.set("Результат: --")
        result_label = ttk.Label(conv_frame, textvariable=self.result_var, font=("Arial", 14, "bold"),
                                 foreground="green")
        result_label.grid(row=4, column=0, columnspan=2, pady=5)

        # Средняя панель: информация о курсе
        info_frame = ttk.LabelFrame(main_frame, text="ℹ️ Информация о курсе", padding=10)
        info_frame.pack(fill=tk.X, pady=(0, 10))

        self.rate_var = tk.StringVar()
        self.rate_var.set("Курс: --")
        ttk.Label(info_frame, textvariable=self.rate_var, font=("Arial", 10)).pack()

        self.last_update_var = tk.StringVar()
        self.last_update_var.set("Последнее обновление: --")
        ttk.Label(info_frame, textvariable=self.last_update_var, font=("Arial", 9)).pack()

        # Кнопка обновления курсов
        self.refresh_btn = ttk.Button(info_frame, text="🔄 Обновить курсы", command=self.refresh_rates)
        self.refresh_btn.pack(pady=5)

        # Нижняя панель: история
        history_frame = ttk.LabelFrame(main_frame, text="📜 История конвертаций", padding=10)
        history_frame.pack(fill=tk.BOTH, expand=True)

        # Таблица истории (Treeview)
        columns = ("Дата", "Откуда", "Куда", "Сумма", "Результат", "Курс")
        self.history_tree = ttk.Treeview(history_frame, columns=columns, show="headings", height=12)

        # Настройка колонок
        self.history_tree.heading("Дата", text="Дата и время")
        self.history_tree.heading("Откуда", text="Из валюты")
        self.history_tree.heading("Куда", text="В валюту")
        self.history_tree.heading("Сумма", text="Сумма")
        self.history_tree.heading("Результат", text="Результат")
        self.history_tree.heading("Курс", text="Курс")

        self.history_tree.column("Дата", width=150)
        self.history_tree.column("Откуда", width=80)
        self.history_tree.column("Куда", width=80)
        self.history_tree.column("Сумма", width=100)
        self.history_tree.column("Результат", width=100)
        self.history_tree.column("Курс", width=100)

        # Скроллбар
        scrollbar = ttk.Scrollbar(history_frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar.set)

        self.history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Кнопки управления историей
        btn_frame = ttk.Frame(history_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        self.clear_history_btn = ttk.Button(btn_frame, text="🗑 Очистить историю", command=self.clear_history)
        self.clear_history_btn.pack(side=tk.LEFT, padx=5)

        self.export_btn = ttk.Button(btn_frame, text="💾 Экспорт истории", command=self.export_history)
        self.export_btn.pack(side=tk.LEFT, padx=5)

        self.delete_btn = ttk.Button(btn_frame, text="❌ Удалить выбранное", command=self.delete_selected)
        self.delete_btn.pack(side=tk.LEFT, padx=5)

    def load_currencies(self):
        """Загрузка списка валют"""
        # Показываем статус загрузки
        self.status_var.set("Загрузка курсов валют...")
        self.convert_btn.config(state=tk.DISABLED)

        # Загружаем в отдельном потоке
        thread = Thread(target=self._load_currencies_thread, daemon=True)
        thread.start()

    def _load_currencies_thread(self):
        """Фоновый поток для загрузки валют"""
        # Для начала используем USD как базовую валюту
        if self.model.fetch_rates("USD"):
            self.current_rates_loaded = True

            # Обновляем UI в основном потоке
            self.root.after(0, self._update_currency_lists)
            self.root.after(0, lambda: self.status_var.set("Курсы валют загружены"))
            self.root.after(0, lambda: self.convert_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.last_update_var.set(
                f"Последнее обновление: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"))
        else:
            self.root.after(0, lambda: self.status_var.set("Ошибка загрузки курсов. Проверьте API ключ"))
            self.root.after(0, lambda: messagebox.showerror("Ошибка",
                                                            "Не удалось загрузить курсы валют. Проверьте подключение к интернету и API ключ."))

    def _update_currency_lists(self):
        """Обновление выпадающих списков валют"""
        currencies = self.model.supported_currencies

        if currencies:
            self.from_currency_combo["values"] = currencies
            self.to_currency_combo["values"] = currencies

            # Устанавливаем значения по умолчанию
            if "USD" in currencies:
                self.from_currency_var.set("USD")
            if "EUR" in currencies:
                self.to_currency_var.set("EUR")
            elif len(currencies) > 1:
                self.from_currency_var.set(currencies[0])
                self.to_currency_var.set(currencies[1])

            self.update_history_display()

    def on_currency_change(self, event=None):
        """При изменении валюты обновляем информацию о курсе"""
        self.update_rate_info()

    def update_rate_info(self):
        """Обновление информации о курсе"""
        if not self.current_rates_loaded:
            return

        from_curr = self.from_currency_var.get()
        to_curr = self.to_currency_var.get()

        if from_curr and to_curr and from_curr in self.model.rates and to_curr in self.model.rates:
            if from_curr == "USD":
                rate = self.model.rates[to_curr]
            else:
                rate = round(self.model.rates[to_curr] / self.model.rates[from_curr], 4)

            self.rate_var.set(f"Курс: 1 {from_curr} = {rate} {to_curr}")

    def refresh_rates(self):
        """Обновление курсов валют"""
        self.status_var.set("Обновление курсов...")
        self.convert_btn.config(state=tk.DISABLED)

        thread = Thread(target=self._refresh_rates_thread, daemon=True)
        thread.start()

    def _refresh_rates_thread(self):
        """Фоновый поток для обновления курсов"""
        if self.model.fetch_rates("USD"):
            self.current_rates_loaded = True
            self.root.after(0, lambda: self.status_var.set("Курсы обновлены"))
            self.root.after(0, lambda: self.convert_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.last_update_var.set(
                f"Последнее обновление: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"))
            self.root.after(0, self.update_rate_info)
        else:
            self.root.after(0, lambda: self.status_var.set("Ошибка обновления курсов"))
            self.root.after(0, lambda: messagebox.showerror("Ошибка", "Не удалось обновить курсы валют"))

    def convert(self):
        """Конвертация валюты"""
        # Валидация ввода
        try:
            amount = float(self.amount_entry.get())
            if amount <= 0:
                messagebox.showwarning("Ошибка ввода", "Сумма должна быть положительным числом!")
                return
        except ValueError:
            messagebox.showwarning("Ошибка ввода", "Пожалуйста, введите корректное число!")
            return

        from_curr = self.from_currency_var.get()
        to_curr = self.to_currency_var.get()

        if not from_curr or not to_curr:
            messagebox.showwarning("Ошибка", "Выберите валюты для конвертации!")
            return

        if not self.current_rates_loaded:
            messagebox.showwarning("Ошибка", "Курсы валют ещё не загружены. Попробуйте позже.")
            return

        # Конвертируем
        result = self.model.convert(amount, from_curr, to_curr)

        if result is not None:
            self.result_var.set(f"Результат: {result} {to_curr}")

            # Рассчитываем курс
            if from_curr == "USD":
                rate = self.model.rates[to_curr]
            else:
                rate = round(self.model.rates[to_curr] / self.model.rates[from_curr], 4)

            # Добавляем в историю
            self.model.add_to_history(from_curr, to_curr, amount, result, rate)
            self.update_history_display()

            messagebox.showinfo("Успех", f"Конвертация выполнена!\n{amount} {from_curr} = {result} {to_curr}")
        else:
            messagebox.showerror("Ошибка", "Не удалось выполнить конвертацию")

    def update_history_display(self):
        """Обновление отображения истории"""
        # Очищаем таблицу
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)

        # Добавляем записи
        for record in self.model.history:
            self.history_tree.insert("", tk.END, values=(
                record["date"],
                record["from_currency"],
                record["to_currency"],
                f"{record['amount']:.2f}",
                f"{record['result']:.2f}",
                f"{record['rate']:.4f}"
            ), tags=(record["id"],))

    def clear_history(self):
        """Очистка истории"""
        if messagebox.askyesno("Подтверждение", "Вы уверены, что хотите очистить всю историю?"):
            self.model.clear_history()
            self.update_history_display()
            messagebox.showinfo("История", "История очищена")

    def delete_selected(self):
        """Удаление выбранной записи из истории"""
        selected = self.history_tree.selection()
        if not selected:
            messagebox.showwarning("Удаление", "Выберите запись для удаления")
            return

        if messagebox.askyesno("Подтверждение", "Удалить выбранную запись?"):
            # Получаем ID записи (хранится в tags)
            for item in selected:
                item_id = self.history_tree.item(item)["tags"][0] if self.history_tree.item(item)["tags"] else None
                if item_id:
                    self.model.delete_history_item(int(item_id))

            self.update_history_display()
            messagebox.showinfo("Успех", "Запись удалена")

    def export_history(self):
        """Экспорт истории в файл"""
        if not self.model.history:
            messagebox.showwarning("Экспорт", "Нет истории для экспорта")
            return

        export_file = f"history_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        try:
            with open(export_file, "w", encoding="utf-8") as f:
                json.dump(self.model.history, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("Экспорт", f"История экспортирована в файл:\n{export_file}")
        except IOError as e:
            messagebox.showerror("Ошибка", f"Не удалось экспортировать: {e}")


# ---------- ТЕСТЫ ----------
import unittest
import tempfile


class TestCurrencyModel(unittest.TestCase):
    def setUp(self):
        """Подготовка к тестам"""
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        self.temp_file.close()

        global DATA_FILE
        self.original_data_file = DATA_FILE
        globals()['DATA_FILE'] = self.temp_file.name

        self.model = CurrencyModel()

    def tearDown(self):
        """Очистка после тестов"""
        globals()['DATA_FILE'] = self.original_data_file
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)

    # Позитивные тесты
    def test_add_to_history(self):
        """Тест добавления в историю"""
        before_count = len(self.model.history)
        self.model.add_to_history("USD", "EUR", 100, 85.50, 0.855)
        self.assertEqual(len(self.model.history), before_count + 1)

    def test_clear_history(self):
        """Тест очистки истории"""
        self.model.add_to_history("USD", "EUR", 100, 85.50, 0.855)
        self.model.clear_history()
        self.assertEqual(len(self.model.history), 0)

    def test_validate_positive_amount(self):
        """Тест валидации положительной суммы"""
        amount = 100
        self.assertGreater(amount, 0)

    # Негативные тесты
    def test_validate_zero_amount(self):
        """Тест нулевой суммы (должна быть ошибка)"""
        amount = 0
        self.assertNotGreater(amount, 0)

    def test_validate_negative_amount(self):
        """Тест отрицательной суммы (должна быть ошибка)"""
        amount = -50
        self.assertNotGreater(amount, 0)

    def test_validate_invalid_string(self):
        """Тест строки вместо числа (должна быть ошибка)"""
        amount_str = "abc"
        with self.assertRaises(ValueError):
            float(amount_str)

    # Граничные тесты
    def test_save_and_load_history(self):
        """Тест сохранения и загрузки истории"""
        test_data = [{"id": 1, "date": "2024-01-01", "from_currency": "USD",
                      "to_currency": "EUR", "amount": 100, "result": 85.50, "rate": 0.855}]
        self.model.history = test_data
        self.model.save_history()

        self.model.history = []
        self.model.load_history()
        self.assertEqual(len(self.model.history), 1)
        self.assertEqual(self.model.history[0]["amount"], 100)

    def test_same_currency_conversion(self):
        """Тест конвертации в ту же валюту"""
        result = self.model.convert(100, "USD", "USD")
        self.assertEqual(result, 100)

    def test_delete_history_item(self):
        """Тест удаления конкретной записи"""
        self.model.add_to_history("USD", "EUR", 100, 85.50, 0.855)
        item_id = self.model.history[0]["id"]
        self.model.delete_history_item(item_id)
        self.assertEqual(len(self.model.history), 0)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        sys.argv.pop(1)
        unittest.main()
    else:
        root = tk.Tk()
        app = CurrencyConverter(root)
        root.mainloop()
