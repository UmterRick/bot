from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from user_utils import get_trainers
from aiogram import types
from utils import update_user_group, read_config
import json


async def back_btn_kb():
    keyboard = InlineKeyboardMarkup()
    back_btn = InlineKeyboardButton('⬅️ Назад', callback_data='turn_back')
    keyboard.row(back_btn)
    return keyboard


def user_type_kb():
    keyboard = types.InlineKeyboardMarkup()
    already_user = InlineKeyboardButton('Учень🤓', callback_data='3')
    trainer_user = InlineKeyboardButton('Тренер📝', callback_data='2')
    admin_user = InlineKeyboardButton('Адміністратор📒', callback_data='1')
    keyboard.row(already_user)
    keyboard.row(trainer_user, admin_user)

    return keyboard


async def menu_kb(user_type):
    keyboard = InlineKeyboardMarkup(row_width=1)
    my_crs_callback = 'my_course' if user_type == 3 else 'trainer_course'

    my_courses_btn = InlineKeyboardButton('Мої курси', callback_data=my_crs_callback)
    all_courses_btn = InlineKeyboardButton('Всі курси', callback_data='all_courses')
    contacts_btn = InlineKeyboardButton('Наші контакти', callback_data='contacts')
    back_btn = InlineKeyboardButton('⬅️ Назад', callback_data='turn_back')

    if user_type == 2:
        keyboard.row(my_courses_btn)

    elif user_type == 1:
        pass
    else:
        keyboard.row(my_courses_btn)
        keyboard.row(all_courses_btn)

    keyboard.row(contacts_btn)
    keyboard.row(back_btn)
    return keyboard


async def trainers_kb(store):
    keyboard = InlineKeyboardMarkup()
    trainers = await get_trainers(store)
    for trainer in trainers:
        if trainer not in ('', ' ', ','):
            trainer_btn = InlineKeyboardButton(trainer, callback_data=trainer)
            keyboard.row(trainer_btn)
    back_btn = InlineKeyboardButton('⬅️ Назад', callback_data='turn_back')
    keyboard.row(back_btn)

    return keyboard


def contact_kb():
    config = read_config("contacts.json")
    keyboard = InlineKeyboardMarkup(row_width=1)
    instagram = InlineKeyboardButton('🖼 Instagram',
                                     url=config.get("instagram", 'https://www.instagram.com'))
    insta_kids = InlineKeyboardButton('👶 Instagram Діти',
                                      url=config.get("instagram_kids", 'https://www.instagram.com'))
    facebook = InlineKeyboardButton('💙 Facebook',
                                    url=config.get("facebook", 'https://www.facebook.com'))
    viber = InlineKeyboardButton('💜 Viber',
                                 url=config.get("viber", 'https://invite.viber.com'))
    telegram = InlineKeyboardButton('✉️ Telegram',
                                    url=config.get("telegram", 'https://t.me'))
    website = InlineKeyboardButton('🌐 Наш сайт',
                                   url=config.get("site", "google.com"))
    phone_1 = InlineKeyboardButton(f'📞 Телефон 1: {config.get("phone1", "000")}',
                                   callback_data="phone1")
    phone_2 = InlineKeyboardButton(f'📞 Телефон 2: {config.get("phone2", "000")}',
                                   callback_data="phone2")
    address = InlineKeyboardButton(f'🏫 Наша адреса : {config.get("address", "Костомарівська 2")}',
                                   url=config.get('google_maps', 'https://www.google.com/maps'))

    back_btn = InlineKeyboardButton('⬅️ Назад', callback_data='turn_back')

    keyboard.row(instagram, insta_kids)
    keyboard.row(telegram, viber)
    keyboard.row(facebook, website)
    keyboard.row(phone_1, phone_2)
    keyboard.row(address)
    keyboard.row(back_btn)

    return keyboard


async def topic_kb(store):
    topics = await store.select('categories', None, ('*',))
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    for topic in topics:
        category_btn = InlineKeyboardButton(topic['name'], callback_data=topic['id'])
        keyboard.row(category_btn)
    back_btn = InlineKeyboardButton('⬅️ Назад', callback_data='turn_back')
    keyboard.row(back_btn)
    return keyboard


async def my_courses(store, user):
    send = {}
    await update_user_group(store)
    if user['type'] == 2:
        groups = await store.select('"user_group"', {'"user"': user['id'], 'type': 'trainer'}, ('"group"',))
        data = {}
        for group in groups:
            group_info = await store.select_one('groups', {'id': group['group']},
                                                ('id', 'stream', 'day', 'time', 'type', 'course', 'chat'))
            course = await store.select_one('courses', {'id': group_info['course']}, ('name', 'id', 'trainer'))
            trainers = json.loads(course['trainer'])
            trainers = trainers['trainer']
            if user['name'] in trainers:
                if data.get(course['id'], None) is None:
                    data[course['id']] = {'name': course['name'], 'groups': [group_info, ]}
                data[course['id']]['groups'].append(group_info)
        for key, value in data.items():
            msg = value.get('name')
            stream = {}
            send[key] = {'course': msg,
                         'groups': []}
            for group in value['groups']:
                group_data = (group['day'], group['time'], group['type'], group['id'])
                if stream.get(group['stream'], None) is None:
                    stream[group['stream']] = [group_data, ]
                if group_data not in stream[group['stream']]:
                    stream[group['stream']].append(group_data)

            for st, gr in stream.items():
                g_msg = ""
                keyboard = InlineKeyboardMarkup()
                callback = list()
                for info in gr:
                    gr_type = '🌐 Online' if info[2] else '🏠 Offline'
                    print(f"{info=}")
                    g_msg += f"📅{info[0]}  🕒{info[1].strftime('%H:%M')} {gr_type}\n"
                    callback.append(info[3])
                btn1 = InlineKeyboardButton("Студенти", callback_data=json.dumps({'students': callback}))
                btn2 = InlineKeyboardButton("Додати чат", callback_data=json.dumps({"add_chat_to": callback}))
                keyboard.add(btn1)
                keyboard.add(btn2)
                send[key]['groups'].append((g_msg, keyboard))

        return send
    if user['type'] == 3:
        groups = await store.select('"user_group"', {'"user"': user['id'], 'type': 'student'}, ('"group"',))
        data = {}

        for group in groups:
            group_info = await store.select_one('groups', {'id': group['group']},
                                                ('id', 'stream', 'day', 'time', 'type', 'course', 'chat'))
            course = await store.select_one('courses', {'id': group_info['course']}, ('name', 'id', 'trainer'))
            print(f"------- {group_info}, {course} ----------")
            if data.get(course['id'], None) is None:
                data[course['id']] = {'name': course['name'], 'groups': [group_info, ]}
            data[course['id']]['groups'].append(group_info)
        for key, value in data.items():
            msg = value['name']
            stream = {}
            send[key] = {'course': msg,
                         'groups': []}
            for group in value.get('groups'):
                group_data = (group['day'], group['time'], group['type'], group['id'], group['chat'], )
                if stream.get(group['stream'], None) is None:
                    stream[group['stream']] = [group_data, ]
                if group_data not in stream[group['stream']]:
                    stream[group['stream']].append(group_data)

            for st, gr in stream.items():
                g_msg = ""
                keyboard = InlineKeyboardMarkup()
                btn1 = InlineKeyboardButton(text="", url="")
                for info in gr:
                    print(f"*********** {info}")
                    gr_type = '🌐 Online' if info[2] else '🏠 Offline'
                    g_msg += f"📅{info[0]}  🕒{info[1].strftime('%H:%M')} {gr_type}\n"
                    btn1 = InlineKeyboardButton("Чат групи", url=info[4])
                keyboard.add(btn1)
                send[key]['groups'].append((g_msg, keyboard))

        return send


async def course_kb(course):
    keyboard = InlineKeyboardMarkup(row_width=1)

    inline_btn = InlineKeyboardButton(f"⚪️Перелік груп️⚪️", callback_data=course['id'])
    url_btn = InlineKeyboardButton(text='📄Повний опис курсу📄', url=course['link'], callback_data='None')
    keyboard.add(inline_btn, url_btn)
    return keyboard


async def groups_stream_kb(course_id, store):
    to_send = list()
    groups = await store.select('groups', {'course': course_id}, ('*',))
    streams = dict()
    for group in groups:
        if group['stream'] not in streams:
            streams[group['stream']] = [group, ]
        else:
            streams[group['stream']].append(group)

    for stream_id, stream in streams.items():
        keyboard = InlineKeyboardMarkup()
        msg = str()
        for group in stream:
            gr_type = '🌐 Online' if group['type'] else '🏠 Offline'
            msg += f"📅{group['day']}  🕒{group['time'].strftime('%H:%m')} {gr_type}\n"
        btn = InlineKeyboardButton("Подати заявку у групу", callback_data=json.dumps([course_id, stream_id, 'enroll']))
        keyboard.add(btn)
        to_send.append([msg, keyboard])

    for i in to_send:
        print(i)
    return to_send


async def admin_enroll_kb(user: dict, groups: list):
    keyboard = InlineKeyboardMarkup()
    accept = InlineKeyboardButton('Підтвердити✅',
                                  callback_data=json.dumps(
                                      {
                                          's': True,
                                          'u': user['id'],
                                          'g': groups
                                      }))
    decline = InlineKeyboardButton('Відхилити❌',
                                   callback_data=json.dumps(
                                       {
                                           's': False,
                                           'u': user['id'],
                                           'g': groups
                                       }))
    keyboard.add(accept, decline)
    return keyboard


def push_keyboard():
    return InlineKeyboardMarkup().row(InlineKeyboardButton("Прочитано", callback_data='read_push'))


def add_chat_kb():
    keyboard = InlineKeyboardMarkup()
    button = InlineKeyboardButton('Перейти в чат', switch_inline_query='Додати цей чат')
    back_btn = InlineKeyboardButton('⬅️ Назад', callback_data='turn_back')
    keyboard.row(button)
    keyboard.row(back_btn)
    return keyboard
