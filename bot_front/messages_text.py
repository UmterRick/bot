import json
from datetime import datetime

group_chat_greeting = 'Привіт,я бот яімояшкола, до якого чату ви мене додали?'

main_menu_text = '<b> 📜 Головне Меню 📜 </b>'
your_courses = "Ваші курси : "
start_text = 'Привіт! 👋\n' \
             'Я бот🤖, який допоможе тобі обрати собі курс у нашому освітньому центрі ЯІМОЯШКОЛА🎓\nОберіть хто ви?👇🏻'

admin_groups_start = "Вітаю, я Бот <i>ЯІМОЯШКОЛА</i>\n " \
                     "Ви додали мене до чату адміністраторів.\n" \
                     "Тут ви зможете отримувати нові заявки до груп" \

password_request = 'Введіть пароль :'
wrong_password = 'Пароль невірний, спробуйте ще раз :'

add_chat_text = 'Натисніть на кнопку, оберіть чат що відповідає цій групі та надішліть команду не редагуючи її'

trainer_manual = "<b>Перед</b> натискання кнопки нижче вам потрібно:\n" \
                 "\t- <b>Додати</b> бота до групи як нового учасника\n" \
                 "\t- <b>Зробити</b> його <b>адміністратором</b> групи\n" \
                 "<b>Після</b> цього натисніть на кнопку та оберіть потрібний чат\n" \
                 "<b>Надішліть</b> запропоноване повідомлення <b>не змінюючи</b> його\n"

warn_text = "<b>Така група вже існує</b>"


async def create_new_enroll(user, store):
    current_enroll = json.loads(user['temp_state_2'])
    to_admin_text = f"<strong>Получена новая заявка</strong>\n\nІм'я: <i>{user['name']}</i>;" \
                    f"\nНікнейм: @{user['nickname']};\nТелефон: {user['contact']}\n\nЗаписан(а) на курсы: \n"
    groups = await store.select('user_group', {'"user_id"': user['id'], 'type': 'student'}, ('"group_id"',))
    new_course = await store.select_one('courses', {'id': current_enroll[0]}, ('name',))
    user_courses = list()
    for group in groups:
        course_id = await store.select_one('groups', {'id': group['group_id']}, ('course',))
        course_id = course_id['course']
        user_courses.append(course_id)
    user_courses = list(set(user_courses))
    for course in user_courses:
        course = await store.select_one('courses', {'id': int(course)}, ('name',))
        course_msg = f"\t✅ Курс : {course['name']}\n"
        to_admin_text += course_msg
    to_admin_text += '\nЗаявка подана на:\n'
    new_course_msg = f"\t✅ Курс : {new_course['name']} \n" \
                     f"\t\t{current_enroll[1]} Потік\n"
    to_admin_text += new_course_msg
    return to_admin_text


def select_greet_time():
    now = datetime.now()
    morning = datetime.now().replace(hour=9, minute=00)
    day = datetime.now().replace(hour=12, minute=00)
    evening = datetime.now().replace(hour=18, minute=00)
    greet = "Привіт"
    if morning < now < day:
        greet = 'Доброго ранку, '
    elif day < now < evening:
        greet = 'Добрий день, '
    elif evening < now:
        greet = 'Добрий вечір, '

    return greet


def first_push(course_name):
    note_text = f"{select_greet_time()} освітній центр ЯІМОЯШКОЛА, нагадує вам, " \
                f"що завтра в цей час  ми чекаємо вас на заняття\n" \
                f"{course_name}"
    return note_text


def second_push(course_name):
    note_text = f"{select_greet_time()} освітній центр ЯІМОЯШКОЛА, нагадує вам, " \
                f"що сьогодні  ми чекаємо вас на заняття\n" \
                f"{course_name}"
    return note_text


def registered_greeting(type_, name):
    text = f"Привіт ми вже знайомі, ви {type_} <i>{name}</i>" \
           f" в нашому освітньому центрі"
    return text
