from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Update
from datetime import datetime, timedelta
from utils import create_callback_data
from user_utils import get_trainers
from aiogram import types
from database import *
import calendar
import json

def ChatTypeKB():
    keyboard = InlineKeyboardMarkup()
    admin_chat = InlineKeyboardButton('Чат адміністраторів', callback_data='admin_chat')
    log_chat = InlineKeyboardButton('Чат звітів', callback_data='log_chat')
    keyboard.row(admin_chat)
    keyboard.row(log_chat)

    return keyboard


def UserTypeKB():
    keyboard = types.InlineKeyboardMarkup()
    already_user = InlineKeyboardButton('Учень🤓', callback_data='3')
    trainer_user = InlineKeyboardButton('Тренер📝', callback_data='2')
    admin_user = InlineKeyboardButton('Адміністратор📒', callback_data='1')
    keyboard.row(already_user)
    keyboard.row(trainer_user, admin_user)

    return keyboard


def MenuKB(user_type):
    keyboard = InlineKeyboardMarkup(row_width=1)
    my_crs_callback = 'my_course' if user_type == 3 else 'trainer_course'

    my_courses_btn = InlineKeyboardButton('Мої курси', callback_data=my_crs_callback)
    all_courses_btn = InlineKeyboardButton('Всі курси', callback_data='all_courses')
    contacts_btn = InlineKeyboardButton('Наші контакти', callback_data='contacts')
    guests_btn = InlineKeyboardButton('Користувачі', callback_data='guests')
    groups_btn = InlineKeyboardButton('Перелік усіх груп', callback_data='all_groups')
    back_btn = InlineKeyboardButton('⬅️ Назад', callback_data='turn_back')

    if user_type == 2:
        keyboard.row(my_courses_btn)

    elif user_type == 1:
        keyboard.row(all_courses_btn)
        # keyboard.row(guests_btn)
        # keyboard.row(groups_btn)
    else:
        keyboard.row(my_courses_btn)
        keyboard.row(all_courses_btn)

    keyboard.row(contacts_btn)
    keyboard.row(back_btn)
    return keyboard


async def TrainersKB(store):
    keyboard = InlineKeyboardMarkup()
    trainers = await get_trainers(store)
    for trainer in trainers:
        callback = list()
        button = str()
        # for course in trainers[trainer]:
        #     temp = callback + trainers[trainer][course]['groups']
        #     callback = temp
        #     if len(callback) == 0:
        #         button = '[]'
        #     else:
        #         button = str(temp)[1:-1]
        trainer_btn = InlineKeyboardButton(trainer, callback_data=trainer)
        keyboard.row(trainer_btn)
    back_btn = InlineKeyboardButton('⬅️ Назад', callback_data='turn_back')
    keyboard.row(back_btn)

    return keyboard


def ContactKB():
    keyboard = InlineKeyboardMarkup(row_width=1)
    instagram = InlineKeyboardButton('🖼 Instagram',
                                     url='https://www.instagram.com/meandmyschoolcenter/')
    insta_kids = InlineKeyboardButton('👶 Instagram Діти',
                                      url='https://www.instagram.com/meandmyschoolkids/')
    facebook = InlineKeyboardButton('💙 Facebook',
                                    url='https://www.facebook.com/meandmyschoolcenter/?hc_ref=ARR'
                                        '-D44Bb8Kj9bWSV4DhW3XVZEjkWkIylAy1-aGhlCQ5AkDIx5sUht8hxsN-9MAgXSI&ref'
                                        '=nf_target&__tn__=kC-R')
    viber = InlineKeyboardButton('💜 Viber',
                                 url='https://invite.viber.com/?g2=AQAeAWoOG4gBCEyzb32Jt0WVJ6QTVFi5U8nL%2B'
                                     '%2FWQyjZnLpqtMlWibHHyFvTQ9kce')
    telegram = InlineKeyboardButton('✉️ Telegram',
                                    url='https://t.me/meandmyschoolcenter')
    website = InlineKeyboardButton('🌐 Наш сайт',
                                   url='https://meandmyschool.org.ua/')
    phone_1 = InlineKeyboardButton('📞 Телефон Kyivstar: +38(097)-270-50-72', callback_data='phone1')
    phone_2 = InlineKeyboardButton('📞 Телефон Vodafone: +38(050)-270-50-72', callback_data='phone2')
    address = InlineKeyboardButton('🏫 Наша адреса : Костомарівська 2', url='https://g.page/meandmyschoolcenter?share')

    back_btn = InlineKeyboardButton('⬅️ Назад', callback_data='turn_back')

    keyboard.row(instagram, insta_kids)
    keyboard.row(telegram, viber)
    keyboard.row(facebook, website)
    keyboard.row(phone_1, phone_2)
    keyboard.row(address)
    keyboard.row(back_btn)

    return keyboard


async def TopicKB(store):
    # global TOPICS
    topics = await store.select('categories', None, ('*',))
    # topics = DataBase.getTopics(DataBase())

    keyboard = types.InlineKeyboardMarkup(row_width=2)
    for topic in topics:
        category_btn = InlineKeyboardButton(topic['name'], callback_data=topic['id'])
        keyboard.row(category_btn)
    back_btn = InlineKeyboardButton('⬅️ Назад', callback_data='turn_back')
    keyboard.row(back_btn)
    return keyboard


def MyCoursesKB(telegram_id):
    keyboard = InlineKeyboardMarkup()
    user = User.read(User(), telegram_id)
    courses = DataBase.getCourses(DataBase())

    if user['type'] == 'trainer':
        groups = user['trainer_group']
        for key in courses:
            names = courses[key]['trainer'].split(',')
            trainers = list()
            for name in names:
                name = name.strip()
                trainers.append(name)

            if user['name'] in trainers:
                my_course_btn = InlineKeyboardButton('✅ Курс : ' + courses[key]['name'], url=courses[key]['link'],
                                                     callback_data='ignore')
                keyboard.row(my_course_btn)
                for group in groups:
                    user_groups = Group.read(Group(), group)
                    if user_groups[group]['course_hash'] == key:
                        my_group_btn = InlineKeyboardButton('▶️ Група : ' + user_groups[group]['daytime'],
                                                            callback_data=create_callback_data(group, 'my_group'))
                        add_chat_btn = InlineKeyboardButton('Додати посилання на чат групи',
                                                            callback_data=create_callback_data(group,
                                                                                               'add_chat_to_group'))
                        keyboard.row(my_group_btn)
                        keyboard.row(add_chat_btn)
                    else:
                        my_group_btn = InlineKeyboardButton('_____________',
                                                            callback_data='ignore')
                        keyboard.row(my_group_btn)
                        break
    else:
        groups = user['groups']
        for group_id in groups:
            group_info = Group.read(Group(), group_id)
            for key in courses:
                if key == group_info[group_id]['course_hash']:
                    my_course_btn = InlineKeyboardButton('✅ Курс : ' + courses[key]['name'], url=courses[key]['link'],
                                                         callback_data='ignore')
                    keyboard.row(my_course_btn)
                    break
                else:
                    continue
            my_group_btn = InlineKeyboardButton('▶️ Група : ' + group_info[group_id]['daytime'],
                                                callback_data=create_callback_data(group_id, 'my_group'))
            keyboard.row(my_group_btn)
            if group_info[group_id]['chat'] is not None:
                my_group_chat = InlineKeyboardButton('Посилання до чату групи', url=group_info[group_id]['chat'])
                keyboard.row(my_group_chat)

    back_btn = InlineKeyboardButton('⬅️ Назад', callback_data='turn_back')
    keyboard.row(back_btn)

    return keyboard


async def CoursesKB(bot, call, category):
    list_of_courses = list()
    temp = None
    try:
        courses = DataBase.getCourses(DataBase(), category=category)
        await call.message.delete()
        for course in courses:
            try:
                keyboard = InlineKeyboardMarkup(row_width=1)
                cur_course = courses[course]
                course_body = f"✅✅✅" \
                              f"\n🔹<b>Назва курсу:</b>\n🔹{cur_course['name']}" \
                              f"\n🔸<b>Тренер:</b>\n🔸{cur_course['trainer']}"
                inline_btn = InlineKeyboardButton(f"⚪️Перелік груп️⚪️", callback_data=course)
                url_btn = InlineKeyboardButton(text='📄Повний опис курсу📄', url=cur_course['link'])

                keyboard.add(inline_btn, url_btn)

                sending_course = await bot.send_message(call.from_user.id, course_body, parse_mode='HTML',
                                                        reply_markup=keyboard)
                list_of_courses.append(sending_course.message_id)
                temp = course
            except:
                PrintException()
                print(f"ERROR while sending courses at course_hash: {courses[course]['name']}")
                DataBase.saveLog(DataBase(), call.message.chat.id, call.from_user.full_name, 'ERR',
                                 f"Ошибка присылания курсов  произошла на курсе :{courses[course]['name']}")
        keyboard = InlineKeyboardMarkup()
        back_btn = InlineKeyboardButton('⬅️ Назад', callback_data='turn_back')
        keyboard.add(back_btn)
        back_btn = await bot.send_message(call.from_user.id, 'Повернутись до категорій', reply_markup=keyboard)
        list_of_courses.append(back_btn.message_id)

        User.tempVar(User(), call.message.chat.id, 'temp', str(list_of_courses))
        DataBase.saveLog(DataBase(), call.message.chat.id, call.from_user.full_name, 'INFO',
                         f"Были присланы курсы по категории :{courses[temp]['category']}")

    except:
        PrintException()
        print('ERROR in courses KB')


async def GroupsKB(curse_groups, telegram_id, course, state):
    user = User.read(User(), telegram_id)
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    if len(curse_groups) == 0:
        empty_group_btn = InlineKeyboardButton(text='Очікуйте, запис на курс незабаром почнеться',
                                               callback_data='ignore_callback')
        keyboard.row(empty_group_btn)
    for key in curse_groups:
        group_type = "Не определено"
        if curse_groups[key]['offline'] == 1:
            group_type = 'Офлайн'
        elif curse_groups[key]['offline'] == 0:
            group_type = 'Онлайн'
        group_body = ('📅(🕒) ' + curse_groups[key]['daytime'] + ' 🌐(' + group_type + ')')

        inline_btn = InlineKeyboardButton(f"{group_body}", callback_data=create_callback_data(key, 'clicked'))

        keyboard.row(inline_btn)
        if user['type'] == 'admin':
            delete_btn = InlineKeyboardButton("❌", callback_data=create_callback_data(key, 'del'))
            edit_btn = InlineKeyboardButton("✏️", callback_data=create_callback_data(key, course, 'edit'))
            students_btn = InlineKeyboardButton("👨‍ 👩‍", callback_data=create_callback_data(key, 'students'))

            keyboard.row(delete_btn, edit_btn)
            keyboard.row(students_btn)
        else:
            enroll_btn = InlineKeyboardButton("Подати заявку у групу️",
                                              callback_data=create_callback_data(key, 'enroll'))
            keyboard.row(enroll_btn)
    if user['type'] == 'admin':
        add_btn = InlineKeyboardButton('Додати нову групу', callback_data=create_callback_data(course, 'add_group'))
        keyboard.row(add_btn)
        await state.update_data(group_to=course, editing=False)
    back_btn = InlineKeyboardButton('⬅️ Назад', callback_data='turn_back')
    keyboard.row(back_btn)
    return keyboard


def GroupsTypeKB():
    flag_keyboard = InlineKeyboardMarkup()
    online_btn = InlineKeyboardButton(text='Онлайн', callback_data='0')
    offline_btn = InlineKeyboardButton(text='Офлайн', callback_data='1')
    flag_keyboard.add(online_btn)
    flag_keyboard.add(offline_btn)
    back_btn = InlineKeyboardButton('⬅️ Назад', callback_data='group_back')
    flag_keyboard.row(back_btn)
    return flag_keyboard


def DaysKB():
    days_keyboard = InlineKeyboardMarkup()
    d = datetime(year=2021, month=2, day=1, hour=0)
    for i in range(7):
        if str(calendar.day_name[d.weekday()]) == 'Monday':
            res = 'ПН'
        elif str(calendar.day_name[d.weekday()]) == 'Tuesday':
            res = 'ВТ'
        elif str(calendar.day_name[d.weekday()]) == 'Wednesday':
            res = 'СР'
        elif str(calendar.day_name[d.weekday()]) == 'Thursday':
            res = 'ЧТ'
        elif str(calendar.day_name[d.weekday()]) == 'Friday':
            res = 'ПТ'
        elif str(calendar.day_name[d.weekday()]) == 'Saturday':
            res = 'СБ'
        elif str(calendar.day_name[d.weekday()]) == 'Sunday':
            res = 'ВС'
        else:
            res = str(calendar.day_name[d.weekday()])
        day_btn = InlineKeyboardButton(res, callback_data=res)
        d += timedelta(days=1)
        days_keyboard.row(day_btn)
    back_btn = InlineKeyboardButton('⬅️ Назад', callback_data='group_back')
    days_keyboard.row(back_btn)
    return days_keyboard


def EngDaysKB():
    days_keyboard = InlineKeyboardMarkup()
    d = datetime(year=2021, month=2, day=1, hour=0)
    for i in range(7):
        res = str(calendar.day_name[d.weekday()])
        day_btn = InlineKeyboardButton(text=res, callback_data=res)
        d += timedelta(days=1)
        days_keyboard.row(day_btn)
    return days_keyboard


def TimeKB():
    global daytimes
    keyboard = InlineKeyboardMarkup()
    d = datetime(year=2021, month=2, day=5, hour=9, minute=0)
    for i in range(21):
        hour = d.strftime('%H:%M')
        d += timedelta(minutes=30)
        daytimes.append(hour)
        gt_btn = InlineKeyboardButton(hour, callback_data=hour)
        keyboard.add(gt_btn)
    back_btn = InlineKeyboardButton('⬅️ Назад', callback_data='group_back')
    keyboard.row(back_btn)
    return keyboard


def NotesKB(group_id):
    keyboard = InlineKeyboardMarkup()
    notes = Notification.read(Notification())
    for key in notes:
        if int(notes[key]['group']) == int(group_id):
            note_btn = InlineKeyboardButton(text=notes[key]['datetime'], callback_data=key)
            del_note_btn = InlineKeyboardButton('❌', callback_data=create_callback_data(key, 'remove', group_id))

            keyboard.row(note_btn)
            keyboard.row(del_note_btn)
    add_note_btn = InlineKeyboardButton('Додати нагадування', callback_data=create_callback_data(group_id, 'add_note'))
    back_btn = InlineKeyboardButton('⬅️ Назад', callback_data=create_callback_data(group_id, 'turn_back'))
    keyboard.row(add_note_btn)
    keyboard.row(back_btn)
    return keyboard


def StudentsKB(group_id):
    keyboard = InlineKeyboardMarkup()
    students = Group.getStudents(Group(), group_id)
    for key in students:
        user_btn = InlineKeyboardButton(students[key], callback_data=create_callback_data(group_id, students[key]))
        delete_user_btn = InlineKeyboardButton('❌',
                                               callback_data=create_callback_data(group_id, key, 'delete'))
        keyboard.row(user_btn, delete_user_btn)
    back_btn = InlineKeyboardButton('⬅️ Назад', callback_data=create_callback_data(group_id, 'stud_back'))
    keyboard.row(back_btn)
    return keyboard


def AddChatKB():
    keyboard = InlineKeyboardMarkup()
    button = InlineKeyboardButton('Перейти в чат', switch_inline_query='Додати цей чат')
    back_btn = InlineKeyboardButton('⬅️ Назад', callback_data=create_callback_data('turn_back'))

    keyboard.row(button)
    keyboard.row(back_btn)

    return keyboard


def AllUsersKB(call):
    try:
        users = User.read(User())
        keyboard = InlineKeyboardMarkup()
        type_ = "Не визначено"
        for u_id in users:
            if users[u_id]['type'] == 'admin':
                type_ = 'Адміністратор'
            elif users[u_id]['type'] == 'client':
                type_ = 'Учень'
            elif users[u_id]['type'] == 'admin_group':
                type_ = 'Група Адміністраторів'
            elif users[u_id]['type'] == 'trainer':
                type_ = 'Тренер'
            elif u_id.startswith('-'):
                type_ = 'група'
            elif users[u_id]['type'] == 'non_type':
                type_ = 'Гість'

            print(f"{u_id} VS {call.message.chat.id}")

            if int(u_id) != int(call.message.chat.id):
                button = InlineKeyboardButton(f"{users[u_id]['name']} ({type_})", callback_data=u_id)
                delete_btn = InlineKeyboardButton('❌', callback_data=create_callback_data(u_id, 'fulldelete'))
                keyboard.row(button, delete_btn)

        back_btn = InlineKeyboardButton('⬅️ Назад', callback_data=create_callback_data('turn_back'))
        keyboard.row(back_btn)

        return keyboard
    except Exception as ex:
        PrintException()


def AllGroupsKB():
    try:
        groups = Group.read(Group())
        keyboard = InlineKeyboardMarkup()
        for g_id in groups:
            button = InlineKeyboardButton(f'{g_id} Група',
                                          callback_data=create_callback_data(g_id, groups[g_id]['course_hash'],
                                                                             'group_num'))
            keyboard.row(button)
        back_btn = InlineKeyboardButton('⬅️ Назад', callback_data=create_callback_data('turn_back'))
        keyboard.row(back_btn)

        return keyboard
    except:
        PrintException()


from storage.db_utils import DataStore
import asyncio

loop = asyncio.get_event_loop()
loop.run_until_complete(TrainersKB(DataStore()))
