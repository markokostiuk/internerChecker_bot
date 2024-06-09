import ast
import base64
import os
from datetime import datetime

import cv2
import numpy as np
import pytz
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from telebot import TeleBot, types

load_dotenv()
login = os.environ.get('LOGIN')
password = os.environ.get('PASSWORD')
TOKEN = os.environ.get('TOKEN')
owner_id = os.environ.get('OWNER_USER_ID')

minutes = 5

up_pixel = 50
bottom_pixel = 399
right_pixel = 783
one_minute_pixel = 2

bot = TeleBot(TOKEN)

auth_state = False


def get_image():
    global login, password
    url_login = 'https://my.bilink.ua/ua/login'
    url_redirect = 'https://my.bilink.ua/ua'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
    }

    # Создаем сессию
    session = requests.Session()
    session.headers.update(headers)

    # Получаем страницу логина для получения CSRF токена
    try:
        r = session.get(url_login)
    except:
        return "Ошибка получения страницы логина."

    # Используем BeautifulSoup для парсинга страницы и извлечения CSRF токена
    try:
        soup = BeautifulSoup(r.content, 'html.parser')
        csrf_token = soup.find('input', {'name': '_csrf'})['value']
    except:
        return "Ошибка парсинга csrf токена."

    # Заполняем данные формы логина
    form_data = {
        '_csrf': csrf_token,
        'LoginForm[username]': login,
        'LoginForm[password]': password
    }


    # Отправляем POST запрос для авторизации
    try:
        r = session.post(url_login, data=form_data)
    except:
        return "Ошибка авторизации."

    # Проверяем перенаправление и повторный GET запрос, если необходимо
    if r.status_code == 302 and 'location' in r.headers:
        redirect_url = r.headers['location']
        if not redirect_url.startswith('http'):
            redirect_url = url_redirect + redirect_url
        r = session.get(redirect_url)

    try:
        # Получаем cookies из сессии
        cookies = session.cookies.get_dict()
        phpsessid = cookies.get('PHPSESSID')
    except:
        return "Ошибка получения PHPSESSID."

    headers = {
        "Cookie": f"PHPSESSID={phpsessid}; _csrf={csrf_token}"
    }

    url_graph = 'https://my.bilink.ua/ua/service/get-port-graph?time=6h'

    try:
        response = session.get(url_graph, headers=headers)

        imgstring = response.content
        imgdata = base64.b64decode(imgstring)
        filename = 'image.png'
    except:
        return "Ошибка получения графика."

    with open(filename, 'wb') as f:
        f.write(imgdata)

    return True


def analyze():
    global bottom_pixel, up_pixel, minutes, right_pixel, one_minute_pixel
    allowed_bgr_colors = [(31, 27, 24), (51, 47, 43)]

    image = cv2.imread('image.png')

    right_part = image[up_pixel: bottom_pixel, right_pixel - minutes * one_minute_pixel: right_pixel]

    # Создаем маску для разрешенных цветов
    mask = np.zeros(right_part.shape[:2], dtype=np.uint8)
    for color in allowed_bgr_colors:
        color_mask = cv2.inRange(right_part, np.array(color), np.array(color))
        mask = cv2.bitwise_or(mask, color_mask)

    # Проверяем, есть ли пиксели, которые не попадают в маску разрешенных цветов
    non_allowed_color_present = np.any(mask == 0)

    return non_allowed_color_present


def check():
    global minutes

    result_get_image = get_image()

    ukraine_tz = pytz.timezone('Europe/Kiev')
    ukraine_time = datetime.now(ukraine_tz)
    formatted_time = ukraine_time.strftime('%d.%m.%y %H:%M:%S')

    if result_get_image == True:
        if analyze():
            text = f'<strong>Результат:</strong>\n\n<strong><u>✅ ИНТЕРНЕТ ЕСТЬ!</u></strong>'
        else:
            text = f'<strong>Результат:</strong>\n\n<strong><u>❌ ИНТЕРНЕТА НЕТ!</u></strong>'
    else:
        text = f'<strong>ОШИБКА!:</strong>\n\n<strong><u>{result_get_image}</u></strong>'

    return text+f"\n\nЗапрос был выполнен: {formatted_time}"


def auth(user_id: str):
    with open('users.txt', 'r') as f:
        for line in f:
            line = line.strip()
            if line == user_id:
                return True
    return False


def get_data(user_id):
    if os.path.exists('config.txt'):
        with open('config.txt', 'r') as file:
            lines = file.readlines()

        for i, line in enumerate(lines):
            try:
                data = ast.literal_eval(line.strip())
                if data.get('userID') == user_id:
                    return data.get('userID'), data.get('mainChatID'), data.get('mainMessageID')
            except (SyntaxError, ValueError):
                continue


def update_config_file(file_path, target_user_id, new_line):
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            lines = file.readlines()

        # Проверить, есть ли строка с заданным userID
        user_found = False
        for i, line in enumerate(lines):
            try:
                data = ast.literal_eval(line.strip())
                if data.get('userID') == target_user_id:
                    lines[i] = new_line + '\n'
                    user_found = True
                    break
            except (SyntaxError, ValueError):
                continue

        # Если такой строки нет, добавить новую строку в конец файла
        if not user_found:
            lines.append(new_line + '\n')

        # Сохранить изменения в файл
        with open(file_path, 'w') as file:
            file.writelines(lines)
    else:
        with open(file_path, 'w') as file:
            file.write(new_line+'\n')

@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    message_id = bot.send_message(chat_id, text='Загрузка...').message_id
    user_id = message.from_user.id

    if not auth(str(user_id)):
        bot.edit_message_text(message_id=message_id, chat_id=chat_id, text='Доступ запрещен.')
        return

    config = str({'userID': user_id, 'mainChatID': chat_id, 'mainMessageID': message_id})

    update_config_file(file_path='config.txt', target_user_id=user_id, new_line=config)

    bot.delete_message(chat_id=chat_id, message_id=message.message_id)
    main(user_id)



@bot.message_handler()
def delete_any(message):
    if message.text not in ['/start', '/image']:
        bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)

def main(user_id):
    _, mainChatID, mainMessageID = get_data(user_id)

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('Обновить', callback_data='update'))

    answer = check()
    bot.edit_message_text(message_id=mainMessageID,
                          chat_id=mainChatID,
                          text=answer,
                          parse_mode='html',
                          reply_markup=markup)


@bot.message_handler(commands=['image'])
def image(message):
    user_id = message.from_user.id
    if not auth(str(user_id)):
        bot.edit_message_text(message_id=message_id, chat_id=chat_id, text='Доступ запрещен.')
        return

    _, mainChatID, _ = get_data(user_id)

    if os.path.exists('image.png'):
        img = open('image.png', 'rb')
        bot.send_photo(chat_id=mainChatID, photo=img)

    bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)

@bot.callback_query_handler(func=lambda callback: True)
def callback_message(callback):
    if callback.data == 'update':
        _, mainChatID, _ = get_data(callback.from_user.id)

        bot.edit_message_text(message_id=callback.message.message_id,
                              chat_id=mainChatID,
                              text='Загрузка...')

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton('Обновить', callback_data='update'))

        answer = check()

        bot.edit_message_text(message_id=callback.message.message_id,
                              chat_id=mainChatID,
                              text=answer,
                              parse_mode='html',
                              reply_markup=markup)


if __name__ == "__main__":
    bot.polling(none_stop=True)
