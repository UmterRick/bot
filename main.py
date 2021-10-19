import asyncio
import logging
import os
from collections.abc import Iterable
import pytz

import aiogram.utils.exceptions
from aiogram import Dispatcher, Bot
from aiogram.dispatcher import FSMContext
from aiogram.utils.executor import start_webhook
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.middlewares.logging import LoggingMiddleware

from parser.mams_site import get_content
from bot_front.new_keyboards import *
from bot_front.messages_text import *
from storage.db_utils import DataStore
from user_utils import USER_TYPE, update_state
from utils import read_config, set_logger, get_admin_group, week_days_tuple  # ,update_user_group
from datetime import datetime, timedelta

bot_config = read_config('bot.json')
webhook_config = read_config('webhook.json')
memory_storage = MemoryStorage()

logging.basicConfig(level=logging.INFO)

bot = Bot(token=bot_config.get("TOKEN", ""))
dp = Dispatcher(bot, storage=memory_storage)
dp.middleware.setup(LoggingMiddleware())

store = DataStore()
logger = set_logger('main')

WEBHOOK_HOST = webhook_config.get("host", "")
WEBHOOK_PATH = webhook_config.get("path", "") + bot_config['TOKEN']
WEBHOOK_URL = webhook_config.get("url", "") + bot_config["TOKEN"]

WEBAPP_HOST = webhook_config.get("app_host", "")  # or ip
WEBAPP_PORT = int(os.getenv('PORT', 5000))


class MainStates(StatesGroup):
    show_contact = State()
    show_my_courses = State()
    choose_trainer = State()
    wait_menu_click = State()
    wait_for_category = State()
    wait_for_course = State()
    wait_for_group = State()
    wait_for_client_answer = State()
    students_list = State()

    login_state = State()
    password_state = State()

    answer_enroll = State()
    add_group_time = State()


@dp.message_handler(lambda m: 'Додати цей чат' in m.text, state='*')
async def add_chat_to_stream(message: types.Message):
    invite_link = await message.chat.create_invite_link()

    select_chat_to = await store.select_one('users', {'telegram': message.from_user.id}, ('temp_state_1',))
    chat_to = json.loads(select_chat_to['temp_state_1'])
    for chat in chat_to.get('add_chat_to', []):
        await store.update('groups', {'id': chat}, {'chat': invite_link.invite_link})
        logger.info(f"New chat for {chat}: {invite_link.invite_link} ")


@dp.message_handler(commands='start', state='*')
async def auth_user_type(message: types.Message):
    chat = message.chat.id
    curr_user = await store.select_one('users', {'telegram': chat}, ('name', 'type'))
    print(curr_user)
    logger.info(f"| Start on user: {curr_user} ([] = new user)")
    if not curr_user or curr_user['type'] <= 0:
        if not curr_user:
            user = {
                'name': message.from_user.full_name,
                'nickname': message.from_user.username,
                'telegram': message.chat.id,
                'contact': None,
                'type': 0,
                'state': str(MainStates.login_state.state)
            }
            await store.insert('users', user)
            logger.info(f" | New user added | {user}")
        await bot.send_message(chat, start_text, reply_markup=user_type_kb())
        await MainStates.login_state.set()
        await update_state(message.chat.id, MainStates.login_state, store)
        return
    elif int(chat) > 0:
        await bot.send_message(chat, registered_greeting(USER_TYPE.get(curr_user['type'], 0), curr_user['name']),
                               'HTML', reply_markup=await menu_kb(curr_user['type']))
        logger.info(f" | Registered user {message.chat.id} start Bot")
        await MainStates.wait_menu_click.set()
        await update_state(message.chat.id, MainStates.wait_menu_click, store)
    elif int(chat) < 0:
        if curr_user['type'] == -1:
            pass


@dp.callback_query_handler(lambda c: 'read_push' not in c.data, state=MainStates.login_state)
async def auth_step_two(call: types.CallbackQuery):
    if call.data == 'turn_back':
        pass
    try:
        user_type = int(call.data)
    except ValueError as err:
        logger.error(f" | Incorrect User Type got : "
                     f"{call.data}, 1,2,3 was expected ({err})")
        user_type = 3

    if user_type in (1, 2):
        pass_msg = await call.message.edit_text(password_request, reply_markup=await back_btn_kb())

        await store.update('users', {'telegram': call.message.chat.id}, {'temp_state_2': pass_msg.message_id})
        await MainStates.password_state.set()
        await update_state(call.message.chat.id, MainStates.password_state, store)
        await store.update('users', {'telegram': call.message.chat.id}, {'temp_state_1': user_type})
        logger.info(f"User {call.from_user.full_name} try to enter as {'Admin' if user_type == 1 else 'Trainer'}")

    elif user_type == 3:
        if call.message.chat.id < 0:
            return
        await call.message.edit_text(f"Ви увійшли як Учень🤓", reply_markup=await menu_kb(3))
        await store.update('users', {'telegram': call.message.chat.id}, {'type': user_type})
        await MainStates.wait_menu_click.set()
        await update_state(call.message.chat.id, MainStates.wait_menu_click, store)
        logger.info(f"User {call.from_user.full_name} enter as Учень")


@dp.callback_query_handler(lambda c: 'read_push' not in c.data, state=MainStates.password_state)
async def from_password(call: types.CallbackQuery):
    if call.data == 'turn_back':
        await MainStates.login_state.set()
        await update_state(call.message.chat.id, MainStates.login_state, store)
        await call.message.edit_text(start_text, reply_markup=user_type_kb())


@dp.message_handler(state=MainStates.password_state)
async def check_password(message: types.Message):
    passwords = read_config('users_access.json')
    passwords = passwords.get('passwords', {})
    chat_id = message.chat.id
    user = await store.select_one('users', {'telegram': message.chat.id}, ('temp_state_1', 'type'))
    to_delete = await store.select_one('users', {'telegram': message.chat.id}, ('temp_state_2',))
    if int(user['temp_state_1']) == 1 and message.text == passwords.get('admin', None) and int(chat_id) < 0:
        await bot.send_message(message.chat.id, 'Ви увійшли як <b> Чат Адміністраторів</b>', parse_mode='HTML')
        await bot.delete_message(message.chat.id, to_delete['temp_state_2'])
        await store.update('users', {'telegram': message.chat.id}, {'type': -1, 'name': 'AdminChat'})
        await MainStates.answer_enroll.set()
        await update_state(chat_id, MainStates.answer_enroll, store)
        logger.info(f"User {message.from_user.full_name} auth in AdminChat")
    elif int(user['temp_state_1']) == 1 and message.text == passwords.get('admin', None) and int(chat_id) > 0:

        await bot.send_message(message.chat.id, 'Ви увійшли як <b>Адміністратор</b>', parse_mode='HTML')
        await bot.delete_message(message.chat.id, to_delete['temp_state_2'])

        await store.update('users', {'telegram': message.chat.id}, {'type': 1})
        await MainStates.wait_menu_click.set()
        await update_state(message.chat.id, MainStates.wait_menu_click, store)
        logger.info(f"User {message.from_user.full_name} auth as Admin")

    elif int(user['temp_state_1']) == 2 and message.text == passwords.get('trainer', None) and int(chat_id) > 0:
        await bot.send_message(message.chat.id, 'Оберіть себе у списку', parse_mode='HTML',
                               reply_markup=await trainers_kb(store))
        await bot.delete_message(message.chat.id, to_delete['temp_state_2'])

        await store.update('users', {'telegram': message.chat.id}, {'type': 2})
        await MainStates.choose_trainer.set()
        await update_state(message.chat.id, MainStates.choose_trainer, store)
        logger.info(f"User {message.from_user.full_name} choose trainer name")

    else:
        to_delete = await store.select_one('users', {'telegram': message.chat.id}, ('temp_state_2',))
        try:
            await bot.delete_message(message.chat.id, to_delete['temp_state_2'])
        except Exception as ex:
            logger.error(f'Cannot delete password request message | {ex}')
        pass_msg = await bot.send_message(message.chat.id, 'Невірний пароль, спробуйте ще раз!',
                                          reply_markup=await back_btn_kb())
        await store.update('users', {'telegram': message.chat.id}, {'temp_state_2': pass_msg.message_id})
        logger.info(f"User {message.from_user.full_name} input wrong password")


@dp.callback_query_handler(lambda c: 'read_push' not in c.data, state=MainStates.choose_trainer)
async def trainer_name_clicked(call: types.CallbackQuery):
    if call.data == 'turn_back':
        await call.message.edit_text(start_text, 'HTML', reply_markup=user_type_kb())
        await MainStates.login_state.set()
        await update_state(call.message.chat.id, MainStates.login_state, store)
    else:
        await store.update('users', {'telegram': call.message.chat.id}, {'name': call.data})
        user = await store.select_one('users', {'telegram': int(call.message.chat.id)}, ('id',))
        courses = await store.select('courses', None, ('trainer', 'id'))
        for course in courses:
            names = json.loads(course['trainer'])
            names = names.get('trainer', [])
            if call.data in names:
                groups = await store.select('groups', {'course': course['id']}, ('id',))
                for group in groups:
                    relations = {
                        '"user_id"': user['id'],
                        '"group_id"': group['id'],
                        '"type"': 'trainer'
                    }
                    await store.insert('user_group', relations)

        await call.message.edit_text('<b> 📜 Головне Меню 📜 </b> ', parse_mode='HTML', reply_markup=await menu_kb(2))
        await MainStates.wait_menu_click.set()
        await update_state(call.message.chat.id, MainStates.wait_menu_click, store)
        logger.info(f"User {call.from_user.full_name} auth as Trainer: {call.data}")


@dp.callback_query_handler(lambda c: 'read_push' not in c.data, state=MainStates.wait_menu_click)
async def menu_btn_clicked(call: types.CallbackQuery):
    chat_id = call.message.chat.id

    if call.data == 'all_courses':
        logger.info(f"User {call.from_user.full_name} viewing categories")
        await call.message.edit_text('Оберіть категорію курсів:', reply_markup=await topic_kb(store))
        await MainStates.wait_for_category.set()
        await update_state(chat_id, MainStates.wait_for_category, store)

    if call.data == 'my_course' or call.data == 'trainer_course':
        logger.info(f"User {call.from_user.full_name} viewing users courses")

        user = await store.select_one('users', {'telegram': chat_id}, ('type', 'id', 'name'))
        to_send = await my_courses(store, user)
        temp_msgs = list()
        msg = await call.message.edit_text('Ваші курси :')
        temp_msgs.append(msg.message_id)
        for course_id, content in to_send.items():
            msg = await bot.send_message(chat_id, content['course'])
            temp_msgs.append(msg.message_id)
            for daytime, keyboard in content['groups']:
                msg = await bot.send_message(chat_id, daytime, reply_markup=keyboard)
                temp_msgs.append(msg.message_id)
        msg = await bot.send_message(chat_id, 'Повернутись', reply_markup=await back_btn_kb())
        temp_msgs.append(msg.message_id)
        await store.update('users', {'telegram': chat_id}, {'temp_state_1': json.dumps(temp_msgs)})

        await MainStates.show_my_courses.set()
        await update_state(chat_id, MainStates.show_my_courses, store)

    if call.data == 'contacts':
        logger.info(f"User {call.from_user.full_name} viewing contacts")

        await call.message.edit_text('Наші контакти :', reply_markup=contact_kb())

        await MainStates.show_contact.set()
        await update_state(chat_id, MainStates.show_contact, store)

    if call.data == 'turn_back':
        await MainStates.login_state.set()
        await update_state(chat_id, MainStates.login_state, store)
        await call.message.edit_text(start_text, reply_markup=user_type_kb())


@dp.callback_query_handler(lambda c: 'read_push' not in c.data,
                           state=[MainStates.show_contact, MainStates.show_my_courses])
async def from_main_menu(call: types.CallbackQuery, state: FSMContext):
    chat_id = call.message.chat.id
    call_user = await store.select_one('users', {'telegram': chat_id}, ('type', 'id', 'name'))
    if call.data == 'turn_back':
        to_delete = await store.select_one('users', {'telegram': chat_id}, ('temp_state_1',))
        to_delete = json.loads(to_delete['temp_state_1'])
        try:
            await call.message.edit_text('<b> 📜 Головне Меню 📜 </b> ', parse_mode='HTML',
                                         reply_markup=await menu_kb(call_user['type']))
        except aiogram.utils.exceptions.MessageNotModified:
            await MainStates.show_contact.set()

        if await state.get_state() == MainStates.show_my_courses.state:
            for msg in to_delete:
                if msg != call.message.message_id:
                    try:
                        await bot.delete_message(chat_id, msg)
                    except aiogram.utils.exceptions.MessageToDeleteNotFound as ex:
                        logger.warning(f"Skip message while deleteL: {ex}")
        await MainStates.wait_menu_click.set()
        await update_state(chat_id, MainStates.wait_menu_click, store)
        return
    if await state.get_state() == MainStates.show_my_courses.state:
        logger.info(f"User {call.from_user.full_name} viewing groups students")

        try:
            await store.update('users', {'telegram': chat_id}, {'temp_state_2': call.data})
            data = json.loads(call.data)

            stream = data.get('students', ())
            chat_to = data.get('add_chat_to', ())
        except json.JSONDecodeError:
            stream = ()
            chat_to = ()

        if stream:
            to_kb = list()
            stream_users = list()
            for group in stream:
                users = await store.select('user_group', {'"group_id"': group, 'type': 'student'}, ('"user_id"',))
                stream_users += users
            keyboard = InlineKeyboardMarkup()
            for student in stream_users:
                stream_student = await store.select_one('users', {'id': student["user_id"]}, ('name',))
                to_kb.append((stream_student['name'], student['user_id']))
            to_kb = list(set(to_kb))
            for btn_text, btn_call in to_kb:
                btn = InlineKeyboardButton(btn_text, callback_data=str(btn_call))
                keyboard.add(btn)

            back_btn = InlineKeyboardButton('⬅️ Назад', callback_data='turn_back')
            keyboard.add(back_btn)
            to_delete = await store.select_one('users', {'telegram': chat_id}, ('temp_state_1',))
            to_delete = json.loads(to_delete['temp_state_1'])
            for msg in to_delete:
                if msg != call.message.message_id:
                    await bot.delete_message(chat_id, msg)

            await call.message.edit_text('Студенти групи', reply_markup=keyboard)
            await MainStates.students_list.set()
            await update_state(chat_id, MainStates.students_list, store)

        elif chat_to:
            logger.info(f"User {call.from_user.full_name} want add chat to group")

            to_delete = await store.select_one('users', {'telegram': chat_id}, ('temp_state_1',))
            to_delete = json.loads(to_delete['temp_state_1'])
            for msg in to_delete:
                if msg != call.message.message_id:
                    try:
                        await bot.delete_message(chat_id, msg)
                    except aiogram.utils.exceptions.MessageToDeleteNotFound as ex:
                        logger.warning(f"Skip message when delete: {ex}")
            await store.update('users', {'telegram': chat_id}, {'temp_state_1': call.data})
            await call.message.edit_text(trainer_manual, parse_mode='HTML', reply_markup=add_chat_kb())

    if await state.get_state() == MainStates.show_contact.state:
        logger.info(f"User {call.from_user.full_name} viewing phone numbers")
        config = read_config("contacts.json")
        if call.data == 'phone1':
            await bot.answer_callback_query(call.id, config["phone1"], True)
        elif call.data == 'phone2':
            await bot.answer_callback_query(call.id, config["phone2"], True)


@dp.callback_query_handler(lambda c: 'read_push' not in c.data, state=MainStates.wait_for_category)
async def courses_list_request(call: types.CallbackQuery):
    logger.info(f"User {call.from_user.full_name} viewing courses on category {call.data}")
    chat_id = call.message.chat.id
    if call.data == 'turn_back':

        await MainStates.wait_menu_click.set()
        await update_state(chat_id, MainStates.wait_menu_click, store)
        user = await store.select_one('users', {'telegram': chat_id}, ('type',))
        await call.message.edit_text('<b> 📜 Головне Меню 📜 </b> ', parse_mode='HTML',
                                     reply_markup=await menu_kb(user['type']))
    else:
        if call.data.isdigit():
            category = int(call.data)
        else:
            logger.error(f"Call data must be digit str, got {call.data} instead")
            return
        await store.update('users', {'telegram': call.message.chat.id}, {'at_category': category})
        courses = await store.select('courses', {'category': category}, ('*',))
        courses_msgs = list()
        try:
            await call.message.delete()
        except aiogram.utils.exceptions.MessageToDeleteNotFound:
            logger.warning("Skip deleting call message")
        for course in courses:
            trainers = json.loads(course['trainer'])
            trainers = trainers.get('trainer')
            course_body = f"✅✅✅" \
                          f"\n🔹<b>Назва курсу:</b>\n🔹{course['name']}" \
                          f"\n🔸<b>Тренер:</b>\n🔸{', '.join(trainers)}"
            new_msg = await bot.send_message(chat_id, course_body,
                                             parse_mode='HTML', reply_markup=await course_kb(course))
            courses_msgs.append(new_msg.message_id)
        new_msg = await bot.send_message(chat_id, 'Повернутись до меню', reply_markup=await back_btn_kb())
        courses_msgs.append(new_msg.message_id)
        await store.update('users', {'telegram': chat_id},
                           {'temp_state_1': json.dumps({"courses": courses_msgs})})
        await MainStates.wait_for_course.set()
        await update_state(chat_id, MainStates.wait_for_course, store)


@dp.callback_query_handler(lambda c: 'read_push' not in c.data, state=MainStates.wait_for_course)
async def group_list_request(call: types.CallbackQuery):
    logger.info(f"User {call.from_user.full_name} viewing groups on course id = {call.data}")

    chat_id = call.message.chat.id
    if call.data == 'None':
        await bot.answer_callback_query(call.id, 'Опису цього курсу ще не існує')
        return
    to_delete = await store.select_one('users', {'telegram': chat_id}, ('temp_state_1', 'id'))
    user_id = to_delete['id']
    to_delete = json.loads(to_delete['temp_state_1'])
    to_delete = list(to_delete.get('courses'))
    to_delete.pop(to_delete.index(call.message.message_id))
    for msg in to_delete:
        try:
            await bot.delete_message(chat_id, msg)
        except aiogram.exceptions.MessageToDeleteNotFound:
            logger.warning("Skip deleting message")
        except Exception as ex:
            logger.error(f"Cannot delete message from user #{user_id} chat cause {ex} ")

    if call.data == 'turn_back':
        await MainStates.wait_for_category.set()
        await update_state(chat_id, MainStates.wait_for_category, store)
        await call.message.edit_text('Оберіть категорію курсів:', reply_markup=await topic_kb(store))
        return

    course_id = int(call.data)
    text_msg = await bot.send_message(chat_id, call.message.text)
    await bot.delete_message(chat_id, call.message.message_id)
    to_send = await groups_stream_kb(course_id, store)
    delete_after = [text_msg.message_id, ]

    for msg, keyboard in to_send:
        stream_msg = await bot.send_message(chat_id, msg, reply_markup=keyboard)
        delete_after.append(stream_msg.message_id)
    back_msg = await bot.send_message(chat_id, "Повернутись", reply_markup=await back_btn_kb())
    delete_after.append(back_msg.message_id)
    await MainStates.wait_for_group.set()
    await store.update('users', {'telegram': chat_id}, {'temp_state_2': json.dumps(delete_after)})
    await update_state(chat_id, MainStates.wait_for_group, store)


@dp.callback_query_handler(lambda c: 'read_push' not in c.data, state=MainStates.wait_for_group)
async def group_request(call: types.CallbackQuery):
    logger.info(f"User {call.from_user.full_name} viewing group info ")

    chat_id = call.message.chat.id
    if call.data == 'turn_back':
        user = await store.select_one('users', {'telegram': chat_id}, ('temp_state_2', 'at_category'))
        to_delete = json.loads(user['temp_state_2'])
        for msg in to_delete:
            try:
                await bot.delete_message(chat_id, msg)
            except Exception as ex:
                logger.warning(f"Skip deleting msg because : {ex}")
        call.data = str(user['at_category'])
        await courses_list_request(call)
        return

    data = json.loads(call.data)
    if isinstance(data, Iterable):
        course_id, stream_id, request_type = data
    else:
        logger.error(f"Got wrong callback from user {chat_id}, wait iterable, got {call.data} instead")
        return

    if request_type == 'enroll':
        stream_info = call.message.text

        to_delete = await store.select_one('users', {'telegram': chat_id}, ('temp_state_2',))
        to_delete = json.loads(to_delete['temp_state_2'])
        for msg in to_delete:
            await bot.delete_message(chat_id, msg)
        user = await store.select_one('users', {'telegram': chat_id}, ('contact',))
        course = await store.select_one('courses', {'id': course_id}, ('name',))
        phone = user['contact']
        if phone is None or not phone:
            keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
            ok_btn = types.KeyboardButton('Так', request_contact=True)
            no_btn = types.KeyboardButton('Ні')
            keyboard.add(ok_btn, no_btn)
        else:
            keyboard = InlineKeyboardMarkup()
            ok_btn = InlineKeyboardButton('Так', callback_data=json.dumps(True))
            no_btn = InlineKeyboardButton('Ні', callback_data=json.dumps(False))
            keyboard.row(ok_btn, no_btn)
        accept_enroll = await bot.send_message(chat_id=chat_id,
                                               text=f"Подати завку до групи:\n<b>{stream_info}</b>\n"
                                                    f"До курсу:\n<i>{course['name']}</i>",
                                               reply_markup=keyboard, parse_mode='HTML')
        await store.update('users', {'telegram': chat_id}, {'temp_state_1': accept_enroll.message_id})
        await store.update('users', {'telegram': chat_id}, {'temp_state_2': json.dumps([course_id, stream_id])})
        await MainStates.wait_for_client_answer.set()
        await update_state(chat_id, MainStates.wait_for_client_answer, store)


@dp.callback_query_handler(lambda c: 'read_push' not in c.data, state=MainStates.students_list)
async def student_clicked(call: types.CallbackQuery):
    logger.info(f"User {call.from_user.full_name} viewing student info student id = {call.data}")

    chat_id = call.message.chat.id
    if 'turn_back' in call.data:
        call.data = 'trainer_course'
        await MainStates.wait_menu_click.set()
        await update_state(chat_id, MainStates.wait_menu_click, store)
        await menu_btn_clicked(call)
        return
    else:
        user = await store.select_one('users', {'id': int(call.data)}, ('nickname', 'name'))
        user_text = f"Ім'я: {user['name']}\nНікнейм : @{user['nickname']}"
        await bot.answer_callback_query(call.id, user_text, True, cache_time=10)


@dp.callback_query_handler(lambda c: 'read_push' not in c.data, state=MainStates.wait_for_client_answer)
@dp.message_handler(content_types=['text', 'contact'], state=MainStates.wait_for_client_answer)
async def client_answer_enroll_message(input_obj: [types.Message, types.CallbackQuery]):
    logger.info(f"User {input_obj.from_user.full_name} accept or decline enroll sending")

    if isinstance(input_obj, types.CallbackQuery):
        chat_id = input_obj.message.chat.id
        data = json.loads(input_obj.data)
        contact = None
    elif isinstance(input_obj, types.Message):
        chat_id = input_obj.chat.id
        data = input_obj.text
        if input_obj.content_type == 'contact':
            contact = input_obj.contact.phone_number
        else:
            contact = None
    else:
        logger.error(f"Input must be message or callback")
        return

    admin_chat = await get_admin_group(store)

    user = await store.select_one('users', {'telegram': chat_id},
                                  ('id', 'type', 'temp_state_1', 'temp_state_2', 'contact',
                                   'name', 'nickname'))

    if data is False or data == 'Ні':
        await bot.delete_message(chat_id, user['temp_state_1'])
        await bot.send_message(chat_id, '<b> Ви відмінили відправку заявки </b> ', parse_mode='HTML',
                               reply_markup=await menu_kb(chat_id))
        await MainStates.wait_menu_click.set()
        await update_state(chat_id, MainStates.wait_menu_click, store)

    elif contact is not None or data == 'Так' or data is True:
        course_id, stream_id = json.loads(user['temp_state_2'])
        enroll_to_groups = await store.select('groups', {'stream': stream_id, 'course': course_id}, ('id',))
        enroll_to_groups = [group['id'] for group in enroll_to_groups]
        enroll_existing = await store.select_one('user_group', {'user_id': user['id'], 'group_id': enroll_to_groups[0]},
                                                 ('id',))
        if enroll_existing:
            logger.warning(f"User {user['nickname']} tey send duplicate enroll to {enroll_to_groups}")

            msg_id = input_obj.message.message_id if isinstance(input_obj,
                                                                types.CallbackQuery) else input_obj.message_id
            await bot.delete_message(chat_id, msg_id)
            await bot.send_message(chat_id, '<b> Ви вже подавали заявку, або навчаетесь у цій групі </b> ',
                                   parse_mode='HTML',
                                   reply_markup=await menu_kb(user['type']))
            await MainStates.wait_menu_click.set()
            await update_state(chat_id, MainStates.wait_menu_click, store)
            return
        phone = user['contact']
        if phone is None or not phone:
            await store.update('users', {'telegram': chat_id}, {'contact': contact})
            user = await store.select_one('users', {'telegram': chat_id},
                                          ('id', 'type', 'temp_state_1', 'temp_state_2', 'contact',
                                           'name', 'nickname'))

        enroll_msg = await create_new_enroll(user, store)

        for group in enroll_to_groups:
            await store.insert('user_group', {'"user_id"': user['id'], '"group_id"': group, 'type': 'enroll'})
        keyboard = await admin_enroll_kb(user, enroll_to_groups)
        try:
            profile_photos = await input_obj.from_user.get_profile_photos(None, 1)
            avatar = profile_photos.photos[0][0].file_id
            await bot.send_photo(admin_chat, avatar, enroll_msg, 'HTML', reply_markup=keyboard)
        except aiogram.exceptions.MigrateToChat as migration:
            await bot.send_message(migration.migrate_to_chat_id, enroll_msg, 'HTML', reply_markup=keyboard)

        except Exception as ex:
            logger.warning(f"Cannot get user profile photo for enroll creating... Sending without photo {ex}")
            await bot.send_message(admin_chat, enroll_msg, 'HTML', reply_markup=keyboard)

        await bot.delete_message(chat_id, int(user['temp_state_1']))
        await bot.send_message(chat_id, '<b> Вашу заявку було відіслано до адміністраторів,'
                                        ' вам передзвонять щодо записі до курсу </b> ', parse_mode='HTML',
                               reply_markup=await menu_kb(user['type']))

        await MainStates.wait_menu_click.set()
        await update_state(chat_id, MainStates.wait_menu_click, store)
    else:
        logger.error(f"Miss input : {type(input_obj)} --> {data}")


@dp.callback_query_handler(lambda c: 'read_push' not in c.data, state=MainStates.answer_enroll)
async def check_client_enroll(call: types.CallbackQuery):
    logger.info(f"Admin {call.from_user.full_name} answer to user enroll")

    data = json.loads(call.data)
    from_user_id = data['u']
    to_groups = data['g']
    status = data['s']

    enroll_text = call.message.caption
    user = await store.select_one('users', {'id': from_user_id}, ('id', 'nickname', 'telegram'))
    keyboard = InlineKeyboardMarkup().row(InlineKeyboardButton('OK', callback_data='read_push'))
    pattern = 'Заявка подана на:'
    start_from = enroll_text.find(pattern)
    course_name = enroll_text[start_from + len(pattern):]
    if status:
        for group in to_groups:
            await store.update('user_group', {'"user_id"': user['id'], '"group_id"': group}, {'type': 'student'})
        client_enroll_answer = f'Ваш запит на зарахування: \n {course_name}\n ' \
                               f'\n <b>✅ПРИЙНЯТО✅</b>'
        admin_service_msg = f" ✅\n{call.from_user.full_name} <b>ПІДТВЕРДИВ(ЛА)</b> заявку від\n" \
                            f"🎓 @{user['nickname']}\n🔵 <b>{course_name}</b>"
        logger.info(f"User {call.from_user.full_name} ACCEPT {user['nickname']} enroll")

    else:
        for group in to_groups:
            await store.delete('user_group', {'"user_id"': user['id'], '"group_id"': group})
        client_enroll_answer = f'Ваш запит на зарахування: \n {course_name}\n ' \
                               f"\n<b>❎ВІДХИЛЕНО❎</b>" \
                               f"\nЯкщо, у вас є запитання обреіть зручний вам спосіб зв'язку із нами у 'Контактах'"

        admin_service_msg = f"❌\n{call.from_user.full_name} <b>ВІДХИЛИВ(ЛА)</b> заявку від\n" \
                            f"🎓 @{user['nickname']}\n🔵 <b>{course_name}</b>"
        logger.info(f"User {call.from_user.full_name} DECLINE {user['nickname']} enroll")

    await call.message.delete()
    await bot.send_message(user['telegram'], client_enroll_answer, 'HTML', reply_markup=keyboard)
    await bot.send_message(call.message.chat.id, admin_service_msg, 'HTML')


@dp.callback_query_handler(lambda c: 'read_push' == c.data, state=[None, '*'])
async def note_was_read(call: types.CallbackQuery):
    try:
        await call.message.delete()
    except aiogram.exceptions.MessageToDeleteNotFound as ex:
        logger.warning(f"Skip deleting msg because : {ex}")


async def schedule_push():
    await update_user_group(store)
    timezone = pytz.timezone('Europe/Kiev')
    now = datetime.now(timezone)
    today = now.strftime("%A")
    users_groups = await store.select('user_group', {'type': 'student'}, ('"user_id"', '"group_id"', 'push'))
    groups = list(set([item['group_id'] for item in users_groups]))
    for group in groups:

        group_data = await store.select_one('groups', {'id': group}, ('program_day', 'time', 'course'))
        course = await store.select_one('courses', {'id': group_data['course']}, ('name',))
        course_name = course['name']
        lesson_day = group_data['program_day']
        day_before_lesson = "NeverDay"
        for order, day in enumerate(week_days_tuple):
            if day == lesson_day:
                day_before_lesson = week_days_tuple[order - 1]
        if today in (lesson_day, day_before_lesson):
            if today == day_before_lesson:
                tomorrow = datetime.now(timezone) + timedelta(days=1)
                group_datetime = tomorrow.replace(hour=group_data['time'].hour, minute=group_data['time'].minute)

                logger.info(f"*** Tomorrow is lesson in {group} group")
                delta = group_datetime - tomorrow if group_datetime > tomorrow else tomorrow - group_datetime

                print(f"tomorrow = {tomorrow.strftime('%Y/%m/%d  %H:%M')}")
                print(f"group = {group_datetime.strftime('%Y/%m/%d  %H:%M')}")
                print(f"delta = {delta.seconds} s")
                if delta.seconds < 10 * 60:
                    logger.info(f"*** Now - LessonTime < 10 min")
                    logger.info(f"*** START sending notifications")
                    group_users = await store.select("user_group", {'"group_id"': group}, ('"user_id"',))
                    group_users = [row['user_id'] for row in group_users]
                    for user in group_users:
                        row = await store.select_one("user_group",
                                                     {'"user_id"': user, '"group_id"': group, 'type': 'student'},
                                                     ('push',))
                        push = row['push'] if row['push'] is not None else 1
                        if push < 0:
                            user_data = await store.select_one('users', {'id': user}, ('telegram',))
                            user_chat = user_data['telegram']
                            logger.info(f"*** Sending push to user id = {user}")
                            await bot.send_message(user_chat, first_push(course_name), reply_markup=push_keyboard())
                    await store.update('user_group', {'"group_id"': group}, {'push': 1})
                    logger.info(f"*** SET push as SEND")
                    logger.info(f"*** FINISH sending notifications")

                elif 40 * 60 > delta.seconds > 15 * 60:
                    await store.update('user_group', {'"group_id"': group}, {'push': -1})
                    logger.info(f"*** SET push as WAITING")

            elif today == lesson_day:
                group_datetime = datetime.now(timezone).replace(hour=group_data['time'].hour, minute=group_data['time'].minute)

                logger.info(f"*** Today is Lesson in group id = {group}")

                delta = group_datetime - now if group_datetime > now else now - group_datetime
                print(f"today = {now.strftime('%Y/%m/%d  %H:%M')}")
                print(f"group = {group_datetime.strftime('%Y/%m/%d  %H:%M')}")
                print(f"delta = {delta.seconds} s")
                if delta.seconds < 2.5 * 60 * 60:
                    logger.info(f"*** Now - LessonTime < 10 min")
                    logger.info(f"*** START sending notifications")
                    group_users = await store.select("user_group", {'"group_id"': group}, ('"user_id"',))
                    group_users = [row['user_id'] for row in group_users]
                    for user in group_users:
                        row = await store.select_one("user_group",
                                                     {'"user_id"': user, '"group_id"': group, 'type': 'student'},
                                                     ('push',))
                        push = row['push']
                        if push < 0:
                            user_data = await store.select_one('users', {'id': user}, ('telegram',))
                            user_chat = user_data['telegram']
                            logger.info(f"*** Sending push to user id = {user}")

                            await bot.send_message(user_chat, second_push(course_name), reply_markup=push_keyboard())
                    await store.update('user_group', {'"group_id"': group}, {'push': 1})
                    logger.info(f"*** SET push as SEND")
                    logger.info(f"*** FINISH sending notifications")

                elif 3.5 * 60 * 60 > delta.seconds > 3 * 60 * 60:
                    await store.update('user_group', {'"group_id"': group}, {'push': -1})
                    logger.info(f"*** SET push as WAITING")


@dp.callback_query_handler(state=None)
@dp.message_handler(lambda m: '/start' not in m.text, state=None)
async def check_state_for_user_message(input_obj: types.Message, state: FSMContext):
    if isinstance(input_obj, types.Message):
        chat_id = input_obj.chat.id
        data = input_obj.text
        if "Додати цей чат" in data:
            await add_chat_to_stream(input_obj)
    elif isinstance(input_obj, types.CallbackQuery):
        chat_id = input_obj.message.chat.id
        data = input_obj.data
    else:
        logger.error("Wrong type in state fixer RETURN")
        return

    user = await store.select_one('users', {'telegram': chat_id}, ('state',))
    await state.set_state(user.get('state', MainStates.login_state.state))
    now_state = await state.get_state()
    logger.info(f"Got msg: {data} in state {now_state} changed to {user.get('state', MainStates.login_state.state)}")


def repeat(coroutine, curr_loop):
    asyncio.ensure_future(coroutine(), loop=curr_loop)
    curr_loop.call_later(5, repeat, coroutine, curr_loop)


async def on_startup(dispatcher):  # there was dispatcher in args
    logger.info(f"on start dispatcher: {dispatcher}")
    await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True)
    # insert code here to run it after start


async def on_shutdown(dispatcher):
    logger.info("===== SHUTDOWN BOT ====")
    await bot.delete_webhook()
    await dispatcher.storage.close()
    await dispatcher.storage.wait_closed()
    logging.warning('Bye!')


def start_bot():
    database_config = read_config('database.json')
    logger.info(f"===== STARTUP BOT =====")
    existing_tables = store.check_existence()
    if not existing_tables[0]:
        logger.error(
            f" | Expected tables doesnt match: {existing_tables[1]} "
            f"from {database_config.get('expected_tables')} ")

        store.create_tables()
        existing_tables = store.check_existence()
        if not existing_tables[0]:
            logger.error(
                f" | Expected tables doesnt match: {existing_tables[1]} "
                f"from {database_config.get('expected_tables')} ")
            exit()

    commands = [types.BotCommand(command="/start", description="Початок спілкування с ботом"), ]
    loop = asyncio.get_event_loop()
    loop.run_until_complete(bot.set_my_commands(commands))
    loop.run_until_complete(get_content(store))
    loop.call_later(3, repeat, schedule_push, loop)
    # dp.bot.set_webhook(webhook_config['url']+bot_config['TOKEN'],)

    start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        skip_updates=True,
        on_startup=on_startup,
        host=WEBAPP_HOST,
        port=WEBAPP_PORT,
    )
