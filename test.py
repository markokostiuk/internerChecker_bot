from datetime import datetime
import pytz

# Часовой пояс для Украины
ukraine_tz = pytz.timezone('Europe/Kiev')

# Текущее время в часовом поясе Украины
ukraine_time = datetime.now(ukraine_tz)

# Форматирование времени в ДД.ММ.ГГ ЧЧ:ММ:СС
formatted_time = ukraine_time.strftime('%d.%m.%y %H:%M:%S')

print(f"Текущее время по украинскому времени: {formatted_time}")
