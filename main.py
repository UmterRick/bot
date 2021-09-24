import asyncio
import logging
from sys import _getframe
from collections.abc import Iterable

import aiogram.utils.exceptions
from aiogram import Dispatcher, Bot
from aiogram.dispatcher import FSMContext
from aiogram.utils.executor import start_webhook
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.middlewares.logging import LoggingMiddleware

from mams_site import get_content
from bot_front.new_keyboards import *
from bot_front.messages_text import *
from storage.db_utils import DataStore
from user_utils import USER_TYPE, update_state
from utils import read_config, set_logger, get_admin_group, week_days_tuple  # ,update_user_group

bot_config = read_config('bot.json')
webhook_config = read_config('webhook.json')
memory_storage = MemoryStorage()

temp_course_text = {}

WEBHOOK_HOST = webhook_config.get("host", "")
WEBHOOK_PATH = webhook_config.get("path", "")
WEBHOOK_URL = webhook_config.get("url", "")

WEBAPP_HOST = webhook_config.get("apphost", "")  # or ip
WEBAPP_PORT = webhook_config.get("appport", -1)

logging.basicConfig(level=logging.INFO)

bot = Bot(token=bot_config.get("TOKEN", ""))
dp = Dispatcher(bot, storage=memory_storage)
dp.middleware.setup(LoggingMiddleware())

store = DataStore()
logger = set_logger('main')


class MainStates(StatesGroup):
    check_state = State()
    show_contact = State()
    show_my_courses = State()
    choose_trainer = State()
    wait_menu_click = State()
    wait_for_category = State()
    wait_for_course = State()
    wait_for_group = State()
    wait_for_client_answer = State()
    students_list = State()
    check = State()


class EnterStates(StatesGroup):
    login_state = State()
    password_state = State()


class AdminStates(StatesGroup):
    answer_enroll = State()
    add_group_time = State()
    add_group_days = State()
    add_group_flag = State()
    add_note = State()


@dp.message_handler(commands='start', state='*')
async def auth_user_type(message: types.Message):
    chat = message.chat.id
    curr_user = await store.select_one('users', {'telegram': chat}, ('name', 'type'))

    logger.info(f"{_getframe().f_code.co_name} | Start on user: {curr_user} ([] = new user)")
    if not curr_user or curr_user['type'] <= 0:
        if not curr_user:
            user = {
                'name': message.from_user.full_name,
                'nickname': message.from_user.username,
                'telegram': message.chat.id,
                'contact': None,
                'type': 0,
                'state': str(EnterStates.login_state.state)
            }
            await store.insert('users', user)
            logger.info(f"{_getframe().f_code.co_name} | New user added | {user}")
        await bot.send_message(chat, start_text, reply_markup=UserTypeKB())
        await EnterStates.login_state.set()
        await update_state(message.chat.id, EnterStates.login_state, store)

    else:
        await bot.send_message(chat, registered_greeting(USER_TYPE.get(curr_user['type'], 0), curr_user['name']),
                               'HTML', reply_markup=await MenuKB(curr_user['type']))
        logger.info(f"{_getframe().f_code.co_name} | Registered user {message.chat.id} start Bot")
        await MainStates.wait_menu_click.set()
        await update_state(message.chat.id, MainStates.wait_menu_click, store)


@dp.callback_query_handler(state=EnterStates.login_state)
async def auth_step_two(call: types.CallbackQuery):
    print('auth_step_two data = ', call.data)
    if call.data == 'turn_back':
        pass
    try:
        user_type = int(call.data)
    except ValueError as err:
        logger.error(f"{_getframe().f_code.co_name} | Incorrect User Type got : "
                     f"{call.data}, 1,2,3 was expected ({err})")
        user_type = 3

    if user_type in (1, 2):
        pass_msg = await call.message.edit_text(password_request, reply_markup=await BackBtn())

        await store.update('users', {'telegram': call.message.chat.id}, {'temp_state_2': pass_msg.message_id})
        await EnterStates.password_state.set()
        await update_state(call.message.chat.id, EnterStates.password_state, store)
        await store.update('users', {'telegram': call.message.chat.id}, {'temp_state_1': user_type})
    elif user_type == 3:
        await call.message.edit_text(f"Ви увійшли як Учень🤓", reply_markup=await MenuKB(3))
        await store.update('users', {'telegram': call.message.chat.id}, {'type': user_type})
        await MainStates.wait_menu_click.set()
        await update_state(call.message.chat.id, MainStates.wait_menu_click, store)


@dp.callback_query_handler(state=EnterStates.password_state)
async def from_password(call: types.CallbackQuery):
    if call.data == 'turn_back':
        await EnterStates.login_state.set()
        await update_state(call.message.chat.id, EnterStates.login_state, store)
        await call.message.edit_text(start_text, reply_markup=UserTypeKB())


@dp.message_handler(state=EnterStates.password_state)
async def check_password(message: types.Message):
    print('check_password data = ', message.text)
    passwords = read_config('users_access.json')
    passwords = passwords.get('passwords', {})
    chat_id = message.chat.id
    user = await store.select_one('users', {'telegram': message.chat.id}, ('temp_state_1', 'type'))

    to_delete = await store.select_one('users', {'telegram': message.chat.id}, ('temp_state_2',))
    if int(user['temp_state_1']) == 1 and message.text == passwords.get('admin', None) and int(chat_id) < 0:
        await bot.send_message(message.chat.id, 'Ви увійшли як <b> Чат Адміністраторів</b>', parse_mode='HTML')
        await bot.delete_message(message.chat.id, to_delete['temp_state_2'])
        await store.update('users', {'telegram': message.chat.id}, {'type': -1, 'name': 'AdminChat'})
        await AdminStates.answer_enroll.set()
        await update_state(chat_id, AdminStates.answer_enroll, store)
    elif int(user['temp_state_1']) == 1 and message.text == passwords.get('admin', None) and int(chat_id) > 0:

        await bot.send_message(message.chat.id, 'Ви увійшли як <b>Адміністратор</b>', parse_mode='HTML',
                               reply_markup=await MenuKB(user['type']))
        await bot.delete_message(message.chat.id, to_delete['temp_state_2'])

        await store.update('users', {'telegram': message.chat.id}, {'type': 1})
        await MainStates.wait_menu_click.set()
        await update_state(message.chat.id, MainStates.wait_menu_click, store)
    elif int(user['temp_state_1']) == 2 and message.text == passwords.get('trainer', None):
        await bot.send_message(message.chat.id, 'Оберіть себе у списку', parse_mode='HTML',
                               reply_markup=await TrainersKB(store))
        await bot.delete_message(message.chat.id, to_delete['temp_state_2'])

        await store.update('users', {'telegram': message.chat.id}, {'type': 2})
        await MainStates.choose_trainer.set()
        await update_state(message.chat.id, MainStates.choose_trainer, store)
    else:
        to_delete = await store.select_one('users', {'telegram': message.chat.id}, ('temp_state_2',))
        try:
            await bot.delete_message(message.chat.id, to_delete['temp_state_2'])
        except Exception as ex:
            logger.error(f'Cannot delete password request message | {ex}')
        pass_msg = await bot.send_message(message.chat.id, 'Невірний пароль, спробуйте ще раз!',
                                          reply_markup=await BackBtn())
        await store.update('users', {'telegram': message.chat.id}, {'temp_state_2': pass_msg.message_id})


@dp.callback_query_handler(state=MainStates.choose_trainer)
async def trainer_name_clicked(call: types.CallbackQuery):
    print('trainer_name_clicked data = ', call.data)
    if call.data == 'turn_back':
        await call.message.edit_text(start_text, 'HTML', reply_markup=UserTypeKB())
        await EnterStates.login_state.set()
        await update_state(call.message.chat.id, EnterStates.login_state, store)
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
                        '"user"': user['id'],
                        '"group"': group['id'],
                        '"type"': 'trainer'
                    }
                    await store.insert('user_group', relations)

        await call.message.edit_text('<b> 📜 Головне Меню 📜 </b> ', parse_mode='HTML', reply_markup=await MenuKB(2))
        await MainStates.wait_menu_click.set()
        await update_state(call.message.chat.id, MainStates.wait_menu_click, store)


@dp.callback_query_handler(state=MainStates.wait_menu_click)
async def menu_btn_clicked(call: types.CallbackQuery):
    print('menu_btn_clicked data = ', call.data)

    chat_id = call.message.chat.id

    if call.data == 'all_courses':
        await call.message.edit_text('Оберіть категорію курсів:', reply_markup=await TopicKB(store))
        await MainStates.wait_for_category.set()
        await update_state(chat_id, MainStates.wait_for_category, store)

    if call.data == 'my_course' or call.data == 'trainer_course':
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
        msg = await bot.send_message(chat_id, 'Повернутись', reply_markup=await BackBtn())
        temp_msgs.append(msg.message_id)
        await store.update('users', {'telegram': chat_id}, {'temp_state_1': json.dumps(temp_msgs)})

        await MainStates.show_my_courses.set()
        await update_state(chat_id, MainStates.show_my_courses, store)

    if call.data == 'contacts':
        await call.message.edit_text('Наші контакти :', reply_markup=contact_kb())

        await MainStates.show_contact.set()
        await update_state(chat_id, MainStates.show_contact, store)

    if call.data == 'turn_back':
        await EnterStates.login_state.set()
        await update_state(chat_id, EnterStates.login_state, store)
        await call.message.edit_text(start_text, reply_markup=UserTypeKB())

    if call.data == 'enroll_ok':
        await call.message.delete()


@dp.callback_query_handler(state=[MainStates.show_contact, MainStates.show_my_courses])
async def from_main_menu(call: types.CallbackQuery, state: FSMContext):
    print(f'from main menu data = {call.data}')
    chat_id = call.message.chat.id
    call_user = await store.select_one('users', {'telegram': chat_id}, ('type', 'id', 'name'))
    if call.data == 'turn_back':
        to_delete = await store.select_one('users', {'telegram': chat_id}, ('temp_state_1',))
        to_delete = json.loads(to_delete['temp_state_1'])
        await call.message.edit_text('<b> 📜 Головне Меню 📜 </b> ', parse_mode='HTML',
                                     reply_markup=await MenuKB(call_user['type']))
        if await state.get_state() == MainStates.show_my_courses.state:
            for msg in to_delete:
                if msg != call.message.message_id:
                    await bot.delete_message(chat_id, msg)
        await MainStates.wait_menu_click.set()
        await update_state(chat_id, MainStates.wait_menu_click, store)
        return
    if await state.get_state() == MainStates.show_my_courses.state:
        try:
            await store.update('users', {'telegram': chat_id}, {'temp_state_2': call.data})
            data = json.loads(call.data)

            stream = data.get('students', ())
            print(f"to show students {data}")
        except json.JSONDecodeError:
            stream = ()
        stream_users = list()
        for group in stream:
            users = await store.select('user_group', {'"group"': group, 'type': 'student'}, ('"user"',))
            stream_users += users
        keyboard = InlineKeyboardMarkup()
        print(f"find THEM  {stream_users}")
        for student in stream_users:
            stream_student = await store.select_one('users', {'id': student["user"]}, ('name',))
            btn = InlineKeyboardButton(stream_student['name'], callback_data=str(student['user']))
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

    # if data[0] == 'phone1':
    #     await bot.answer_callback_query(call.id, '+38(097)-270-50-72', True)
    # elif data[0] == 'phone2':
    #     await bot.answer_callback_query(call.id, '+38(050)-270-50-72', True)

    # user_info = db_get_user_info(DB_NAME, call.message.chat.id)

    # if 'my_group' in data and user_info[0][2] == 'trainer':
    #     group_id = data[0]
    #     print('my_groups', group_id)
    #     keyboard = InlineKeyboardMarkup()
    #     students = db_get_group_students(DB_NAME, int(group_id))
    #     for student in students:
    #         user_btn = InlineKeyboardButton(student[1], callback_data=create_callback_data(group_id, student[0]))
    #         keyboard.row(user_btn)
    #     back_btn = InlineKeyboardButton('⬅️ Назад', callback_data=group_id + ';stud_back')
    #     keyboard.row(back_btn)
    #     await call.message.edit_text('Список студентів до групи :', reply_markup=keyboard)

    # await MainStates.students_list.set()
    # user_state = await StateName(state)
    # db_upd_user_state(DB_NAME, CHAT_ID, user_state)


@dp.callback_query_handler(state=MainStates.wait_for_category)
async def courses_list_request(call: types.CallbackQuery):
    print('courses_list_request ', call.data)
    chat_id = call.message.chat.id
    if call.data == 'turn_back':

        await MainStates.wait_menu_click.set()
        await update_state(chat_id, MainStates.wait_menu_click, store)
        user = await store.select_one('users', {'telegram': chat_id}, ('type',))
        await call.message.edit_text('<b> 📜 Головне Меню 📜 </b> ', parse_mode='HTML',
                                     reply_markup=await MenuKB(user['type']))
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
                                             parse_mode='HTML', reply_markup=await Courses(course))
            courses_msgs.append(new_msg.message_id)
        new_msg = await bot.send_message(chat_id, 'Повернутись до меню', reply_markup=await BackBtn())
        courses_msgs.append(new_msg.message_id)
        await store.update('users', {'telegram': chat_id},
                           {'temp_state_1': json.dumps({"courses": courses_msgs})})
        await MainStates.wait_for_course.set()
        await update_state(chat_id, MainStates.wait_for_course, store)


@dp.callback_query_handler(state=MainStates.wait_for_course)
async def group_list_request(call: types.CallbackQuery):
    print('group_list_request ', call.data)
    chat_id = call.message.chat.id

    to_delete = await store.select_one('users', {'telegram': chat_id}, ('temp_state_1',))
    to_delete = json.loads(to_delete['temp_state_1'])
    to_delete = list(to_delete.get('courses'))
    to_delete.pop(to_delete.index(call.message.message_id))
    for msg in to_delete:
        await bot.delete_message(chat_id, msg)

    if call.data == 'turn_back':
        await MainStates.wait_for_category.set()
        await update_state(chat_id, MainStates.wait_for_category, store)
        await call.message.edit_text('Оберіть категорію курсів:', reply_markup=await TopicKB(store))
        return
    course_id = int(call.data)
    text_msg = await bot.send_message(chat_id, call.message.text)
    await bot.delete_message(chat_id, call.message.message_id)
    to_send = await GroupStreamsKB(course_id, store)
    delete_after = [text_msg.message_id, ]

    for msg, keyboard in to_send:
        stream_msg = await bot.send_message(chat_id, msg, reply_markup=keyboard)
        delete_after.append(stream_msg.message_id)
    back_msg = await bot.send_message(chat_id, "Повернутись", reply_markup=await BackBtn())
    delete_after.append(back_msg.message_id)
    await MainStates.wait_for_group.set()
    await store.update('users', {'telegram': chat_id}, {'temp_state_2': json.dumps(delete_after)})
    await update_state(chat_id, MainStates.wait_for_group, store)


@dp.callback_query_handler(lambda c: 'accept' not in c.data, state=MainStates.wait_for_group)
async def group_request(call: types.CallbackQuery, state: FSMContext):
    chat_id = call.message.chat.id
    if call.data == 'turn_back':
        user = await store.select_one('users', {'telegram': chat_id}, ('temp_state_2', 'at_category'))
        to_delete = json.loads(user['temp_state_2'])
        for msg in to_delete:
            try:
                await bot.delete_message(chat_id, msg)
            except Exception as ex:
                logger.warning(f"Skip deleting msg because : {ex}")
        call.data = int(user['at_category'])
        print(call.data, type(call.data))

        await courses_list_request(call, state)
        return

    data = json.loads(call.data)
    print(f"wait_for_group {await state.get_state()} || {data}")
    if isinstance(data, Iterable):
        course_id, stream_id, request_type = data
    else:
        logger.error(f"Got wrong callback from user {chat_id}, wait iterable, got {call.data} instead")
        return
    print(f'group data {course_id=} | {stream_id=} | {request_type=}')

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
        return


@dp.callback_query_handler(state=MainStates.students_list)
async def student_clicked(call: types.CallbackQuery):

    print('student_clicked  data :', call.data)
    chat_id = call.message.chat.id
    if 'turn_back' in call.data:
        call.data = 'trainer_course'
        await MainStates.wait_menu_click.set()
        await update_state(chat_id, MainStates.wait_menu_click, store)
        await menu_btn_clicked(call)
        return
    else:
        user = await store.select_one('users', {'id': int(call.data)}, ('nickname', 'name' ))
        user_text = f"Ім'я: {user['name']}\nНікнейм : @{user['nickname']}"
        await bot.answer_callback_query(call.id, user_text, True, cache_time=10)


@dp.callback_query_handler(state=MainStates.wait_for_client_answer)
@dp.message_handler(content_types=['text', 'contact'], state=MainStates.wait_for_client_answer)
async def client_answer_enroll_message(input_obj: [types.Message, types.CallbackQuery]):
    print('client_answer_enroll message = ', 'm: ', input_obj)
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
                               reply_markup=await MenuKB(chat_id))
        await MainStates.wait_menu_click.set()
        await update_state(chat_id, MainStates.wait_menu_click, store)

    elif contact is not None or data == 'Так' or data is True:
        phone = user['contact']
        if phone is None or not phone:
            await store.update('users', {'telegram': chat_id}, {'contact': contact})
            user = await store.select_one('users', {'telegram': chat_id},
                                          ('id', 'type', 'temp_state_1', 'temp_state_2', 'contact',
                                           'name', 'nickname'))

        enroll_msg = await create_new_enroll(user, store)
        course_id, stream_id = json.loads(user['temp_state_2'])
        enroll_to_groups = await store.select('groups', {'stream': stream_id, 'course': course_id}, ('id',))
        enroll_to_groups = [group['id'] for group in enroll_to_groups]
        for group in enroll_to_groups:
            await store.insert('user_group', {'"user"': user['id'], '"group"': group, 'type': 'enroll'})
        keyboard = await admin_enroll_kb(user, enroll_to_groups)
        try:
            profile_photos = await input_obj.from_user.get_profile_photos(None, 1)
            avatar = profile_photos.photos[0][0].file_id
            await bot.send_photo(admin_chat, avatar, enroll_msg, 'HTML', reply_markup=keyboard)
        except Exception as ex:
            print("**" * 30, type(ex), ex)
            await bot.send_message(admin_chat, enroll_msg, 'HTML', reply_markup=keyboard)

        await bot.delete_message(chat_id, int(user['temp_state_1']))
        await bot.send_message(chat_id, '<b> Вашу заявку було відіслано до адміністраторів,'
                                        ' вам передзвонять щодо записі до курсу </b> ', parse_mode='HTML',
                               reply_markup=await MenuKB(user['type']))

        await MainStates.wait_menu_click.set()
        await update_state(chat_id, MainStates.wait_menu_click, store)
    else:
        logger.error(f"Miss input : {type(input_obj)} --> {data}")


@dp.callback_query_handler(state=AdminStates.answer_enroll)
async def check_client_enroll(call: types.CallbackQuery):
    print('check_client_enroll data = ', call.data)
    data = json.loads(call.data)
    from_user_id = data['u']
    to_groups = data['g']
    status = data['s']

    enroll_text = call.message.text
    user = await store.select_one('users', {'telegram': from_user_id}, ('*',))

    keyboard = InlineKeyboardMarkup().row(InlineKeyboardButton('OK', callback_data='enroll_ok'))
    pattern = 'Заявка подана на:'
    start_from = enroll_text.find(pattern)
    course_name = enroll_text[start_from + len(pattern):]
    if status:
        for group in to_groups:
            await store.update('user_group', {'"user"': user['id'], '"group"': group}, {'type': 'student'})
        client_enroll_answer = f'Ваш запит на зарахування: \n {course_name}\n ' \
                               f'\n <b>✅ПРИЙНЯТО✅</b>'
        admin_service_msg = f" ✅\n{call.from_user.full_name} <b>ПІДТВЕРДИЛА</b> заявку від\n" \
                            f"🎓 {user['username']}\n🔵 <b>{course_name}</b>"

    else:
        for group in to_groups:
            await store.delete('user_group', {'"user"': user['id'], '"group"': group})
        client_enroll_answer = f'Ваш запит на зарахування: \n {course_name}\n ' \
                               f"\n<b>❎ВІДХИЛЕНО❎</b>" \
                               f"\nЯкщо, у вас є запитання обреіть зручний вам спосіб зв'язку із нами у 'Контактах'"

        admin_service_msg = f"❌\n{call.from_user.full_name} <b>ВІДХИЛИЛА</b> заявку від\n" \
                            f"🎓 {user['username']}\n🔵 <b>{course_name}</b>"
    await call.message.delete()
    await bot.send_message(user['telegram'], client_enroll_answer, 'HTML', reply_markup=keyboard)
    await bot.send_message(call.message.chat.id, admin_service_msg, 'HTML')


# @dp.callback_query_handler(lambda c: c.data in ['0', '1', 'again', 'done'], state='*')
# async def admin_add_flag(call: types.CallbackQuery, state: FSMContext):
#     global CHAT_ID
#     print('admin_add_flag data = ', call.data)
#
#     chat = call.message.chat.id
#     if call.data in ['0', '1']:
#         await state.update_data(group_flag=call.data)
#         days_keyboard = DaysKB()
#         await call.message.edit_text(text='Отметьте день', reply_markup=days_keyboard)
#
#         await AdminStates.add_group_days.set()
#
#         user_state = await StateName(state)
#         db_upd_user_state(DB_NAME, CHAT_ID, user_state)
#
#     elif call.data == 'again':
#         days_keyboard = DaysKB()
#         await call.message.edit_text(text='Отметьте день', reply_markup=days_keyboard)
#
#         await AdminStates.add_group_days.set()
#
#         user_state = await StateName(state)
#         db_upd_user_state(DB_NAME, CHAT_ID, user_state)
#
#     elif call.data == 'done':
#         state_data = await state.get_data()
#
#         print('state dict = ', state_data)
#         info_to_db = state_data['group_datetime']
#         group_type = state_data['group_flag']
#         to_course = state_data['group_to']
#         group_id = state_data['group_id']
#
#         final_info = ' '
#         for info in info_to_db:
#             final_info += (str(info) + '; ')
#         if state_data['editing'] is True:
#             db_edit_group(DB_NAME, group_id, final_info, group_type)
#             await state.update_data(editing=False)
#         elif state_data['editing'] is False:
#             db_add_group(DB_NAME, final_info, group_type, to_course)
#
#         group_type = 'Оффлайн' if group_type == '1' else 'Онлайн'
#
#         cur_groups = db_read_groups(DB_NAME, to_course)
#         keyboard = await GroupsKB(cur_groups, call.message.chat.id, to_course, state)
#         courses_body = get_content(HTML)
#
#         temp_text = call.message.text
#         await call.message.edit_text(temp_text, reply_markup=keyboard)
#
#         await MainStates.wait_for_group.set()
#
#         user_state = await StateName(state)
#         db_upd_user_state(DB_NAME, CHAT_ID, user_state)
#
#
# @dp.callback_query_handler(lambda c: c.data in weekdays, state=AdminStates.add_group_days)
# async def admin_add_days(call: types.CallbackQuery, state: FSMContext):
#     CHAT_ID = call.message.chat.id
#
#     temp_days = call.data
#     await state.update_data(group_day=temp_days)
#     keyboard = TimeKB()
#     await call.message.edit_text(text='Отметьте время', reply_markup=keyboard)
#
#     await AdminStates.add_group_time.set()
#
#     user_state = await StateName(state)
#     db_upd_user_state(DB_NAME, CHAT_ID, user_state)
#
#
# @dp.callback_query_handler(lambda c: c.data in daytimes, state=AdminStates.add_group_time)
# async def add_time(call: types.CallbackQuery, state: FSMContext):
#     global CHAT_ID
#     CHAT_ID = call.message.chat.id
#
#     keyboard = InlineKeyboardMarkup()
#     temp_time = call.data
#     await state.update_data(group_time=temp_time)
#     state_data = await state.get_data()
#     group_datetime = ' (' + str(state_data['group_day']) + ')' + str(state_data['group_time'])
#     datetimeList = state_data['group_datetime']
#     datetimeList.append(group_datetime)
#     await state.update_data(group_datetime=datetimeList)
#     again_btn = InlineKeyboardButton('Додати час', callback_data='again')
#     done_btn = InlineKeyboardButton('Завершити', callback_data='done')
#     keyboard.row(again_btn)
#     keyboard.row(done_btn)
#     await call.message.edit_text(text='Процес додавання групи', reply_markup=keyboard)
#
#     await AdminStates.add_group_flag.set()
#
#     user_state = await StateName(state)
#     db_upd_user_state(DB_NAME, CHAT_ID, user_state)
#
#
# GROUP_ID = None

#
# @dp.callback_query_handler(state=AdminStates.add_note)
# async def new_notification(call: types.CallbackQuery, state: FSMContext):
#     global GROUP_ID
#     data = separate_callback_data(call.data)
#     print('new_notification data = ', data)
#     if 'add_note' in data:
#         group_id = data[0]
#         await state.update_data(group_id=group_id)
#         GROUP_ID = group_id
#         keyboard = EngDaysKB()
#
#         await call.message.edit_text('Оберіть день нагадування', reply_markup=keyboard)
#
#     if call.data in eng_weekdays:
#         note_day = call.data
#         await state.update_data(note_day=note_day)
#
#         keyboard = TimeKB()
#
#         await call.message.edit_text('Оберіть час нагадування', reply_markup=keyboard)
#     if call.data in daytimes:
#         note_time = call.data
#
#         await state.update_data(note_time=note_time)
#
#         state_data = await state.get_data()
#         note_daytime = f"({state_data['note_day']})[{state_data['note_time']}];"
#         db_add_notification(DB_NAME, state_data['group_id'], note_daytime)
#         print('GROUP_ID', GROUP_ID)
#         await call.message.edit_text('Нагадування до ціеї групи', reply_markup=NotesKB(GROUP_ID))
#
#     if 'remove' in data:
#         group_id = data[2]
#         note_id = data[0]
#         print('remove note id = ', note_id)
#         db_delete_notification(DB_NAME, note_id)
#         await call.message.edit_text('Нагадування до ціеї групи :', reply_markup=NotesKB(group_id))
#
#     if 'turn_back' in data:
#         group_id = data[0]
#
#         group_info, course_info, to_course_id = db_get_group_info(DB_NAME, group_id)
#         print(group_id, '___', group_info, course_info, to_course_id)
#         cur_groups = db_read_groups(DB_NAME, to_course_id)
#         keyboard = await GroupsKB(cur_groups, call.message.chat.id, to_course_id, state)
#
#         await call.message.edit_text(course_info, reply_markup=keyboard)
#         await MainStates.wait_for_group.set()
#         user_state = await StateName(state)
#         db_upd_user_state(DB_NAME, CHAT_ID, user_state)


@dp.callback_query_handler(lambda c: c.data == 'read_push')
async def note_was_read(call: types.CallbackQuery):
    await call.message.delete()


async def schedule_push():
    await update_user_group(store)
    now = datetime.now()

    today = now.strftime("%A")
    users_groups = await store.select('user_group', {'type': 'student'}, ('"user"', '"group"', 'push'))
    groups = list(set([item['group'] for item in users_groups]))
    for group in groups:

        group_data = await store.select_one('groups', {'id': group}, ('program_day', 'time', 'course'))
        course = await store.select_one('courses', {'id': group_data['course']}, ('name', ))
        course_name = course['name']
        lesson_day = group_data['program_day']
        day_before_lesson = "NeverDay"
        for order, day in enumerate(week_days_tuple):
            if day == lesson_day:
                day_before_lesson = week_days_tuple[order - 1]

        if today in (lesson_day, day_before_lesson):  # TODO: remove True
            group_datetime = datetime.now().replace(hour=group_data['time'].hour, minute=group_data['time'].minute)
            if today == day_before_lesson:
                tomorrow = datetime.now() + timedelta(days=1)
                delta = group_datetime - tomorrow if group_datetime < tomorrow else tomorrow - group_datetime
                if delta.seconds < 10 * 60:

                    group_users = await store.select("user_group", {'"group"': group}, ('"user"',))
                    group_users = [row['user'] for row in group_users]
                    for user in group_users:
                        row = await store.select_one("user_group",
                                               {'"user"': user, '"group"': group, 'type': 'student'},
                                               ('push', ))
                        push = row['push']
                        if push < 0:
                            user_data = await store.select_one('users', {'id': user}, ('telegram', ))
                            user_chat = user_data['telegram']
                            await bot.send_message(user_chat, first_push(course_name), reply_markup=push_keyboard())
                    await store.update('user_group', {'"group"': group}, {'push': 1})

                elif 40 * 60 > delta.seconds > 15 * 60:
                    await store.update('user_group', {'"group"': group}, {'push': -1})
            elif today == lesson_day:
                delta = group_datetime - now if group_datetime < now else now - group_datetime
                print(f"TODAY {delta.seconds=}")

                if delta.seconds < 2.5 * 60 * 60:
                    group_users = await store.select("user_group", {'"group"': group}, ('"user"',))
                    group_users = [row['user'] for row in group_users]
                    print(f"CHECK TO SEND TODAY PUSH {group_users}")
                    for user in group_users:
                        row = await store.select_one("user_group",
                                                     {'"user"': user, '"group"': group, 'type': 'student'},
                                                     ('push',))
                        push = row['push']
                        if push < 0:
                            user_data = await store.select_one('users', {'id': user}, ('telegram',))
                            user_chat = user_data['telegram']
                            await bot.send_message(user_chat, second_push(course_name), reply_markup=push_keyboard())
                            print(f"SEND SECOND NOTIFICATION  TO {user_chat}")
                    await store.update('user_group', {'"group"': group}, {'push': 1})
                    print("TODAY SET AS SENT")
                    print()
                elif 3.5 * 60 * 60 > delta.seconds > 3 * 60 * 60:
                    await store.update('user_group', {'"group"': group}, {'push': -1})
                    print("SET TODAY NOTIFICATION IN WAIT ")


@dp.message_handler(lambda m: '/start' not in m.text, state=None)
async def check_state_for_user_message(message: types.Message, state: FSMContext):
    user = await store.select_one('users', {'telegram': message.chat.id}, ('state',))
    await state.set_state(user['state'])
    now_state = await state.get_state()
    logger.info(f"Got msg: {message.text} in state {now_state} changed to {user['state']}")


@dp.callback_query_handler(state=None)
async def check_state_for_user_callback(call: types.CallbackQuery, state: FSMContext):
    user = await store.select_one('users', {'telegram': call.message.chat.id}, ('state',))
    await state.set_state(user['state'])
    now_state = await state.get_state()
    logger.info(f"Got callback: {call.data} in state {now_state} changed to {user['state']}")


def repeat(coroutine, curr_loop):
    asyncio.ensure_future(coroutine(), loop=curr_loop)
    curr_loop.call_later(20, repeat, coroutine, curr_loop)


async def on_startup(dp):
    await bot.set_webhook(WEBHOOK_URL)
    # insert code here to run it after start


async def on_shutdown(dp):
    logging.warning('Shutting down..')

    await bot.delete_webhook()
    await dp.storage.close()
    await dp.storage.wait_closed()
    logging.warning('Bye!')


if __name__ == "__main__":
    database_config = read_config('database.json')
    logger.info(f"===== STARTUP BOT =====")
    existing_tables = store.check_existence()
    if not existing_tables[0]:
        logger.error(
            f"{_getframe().f_code.co_name}: Expected tables doesnt match: {existing_tables[1]} from {database_config.get('expected_tables')} ")
        exit()

    commands = [types.BotCommand(command="/start", description="Начало работы с ботом"), ]
    loop = asyncio.get_event_loop()
    loop.run_until_complete(bot.set_my_commands(commands))
    loop.run_until_complete(get_content(store))
    loop.run_until_complete(job())
    # loop.call_later(10, repeat, job, loop)
    start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        skip_updates=True,
        host=WEBAPP_HOST,
        port=WEBAPP_PORT,
    )
