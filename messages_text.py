from database import Group, DataBase, User
from configs import PrintException, datetime
group_chat_greeting = 'Привіт,я бот яімояшкола, до якого чату ви мене додали?'

main_menu_text = '<b> 📜 Головне Меню 📜 </b>'
your_courses = "Ваші курси : "
start_text = 'Привіт! 👋\n' \
             'Я бот🤖, який допоможе тобі обрати собі курс у нашому освітньому центрі ЯІМОЯШКОЛА🎓\nОберіть хто ви?👇🏻'

admin_groups_start = "Вітаю, я Бот <i>ЯІМОЯШКОЛА</i>\n " \
                     "Ви додали мене до чату адміністраторів.\n" \
                     "Тут ви зможете отримувати нові заявки до груп" \

log_chat_start = "Вітаю, я Бот <i>ЯІМОЯШКОЛА</i>\n " \
                     "Ви додали мене до чату звітів.\n" \
                     "Тут ви зможете отримувати інформацию щодо моєї роботи " \


password_request = 'Введіть пароль :'
wrong_password = 'Пароль невірний, спробуйте ще раз :'

add_chat_text = 'Натисніть на кнопку, оберіть чат що відповідає цій групі та надішліть команду не редагуючи її'
#fjdkslcsmd
trainer_manual = "<b>Перед</b> натискання кнопки нижче вам потрібно:\n" \
                 "\t- <b>Додати</b> бота до групи як нового учасника\n" \
                 "\t- <b>Зробити</b> його <b>адміністратором</b> групи\n" \
                 "<b>Після</b> цього натисніть на кнопку та оберіть потрібний чат\n" \
                 "<b>Надішліть</b> запропоноване повідомлення <b>не змінюючи</b> його\n"

warn_text = "<b>Така група вже існує</b>"


def Enroll_text(user):
    courses = DataBase.getCourses(DataBase())

    to_admin_text = f"<strong>Получена новая заявка</strong>\n\nИмя: <i>{user['name']}</i>;" \
                    f"\nНикнейм: @{user['nickname']};\nТелефон: {user['contact']}\n\nТекущие курсы: \n"
    for group in user['groups']:
        g_info = Group.read(Group(), group)
        group_type = 'Офлайн' if g_info[group]['offline'] == 1 else 'Онлайн'

        for key in courses:
            if key == g_info[group]['course_hash']:
                to_admin_text += f"✅ Курс : {courses[key]['name']} \n\t " \
                                 f"▶️ Група 📅(🕒){g_info[group]['daytime']} 🌐{group_type}\n"
    to_admin_text += '\nЗаявка подана на:\n'
    enroll = user['enrolls'][-1]
    e_info = Group.read(Group(), enroll)
    group_type = 'Офлайн' if e_info[enroll]['offline'] == 1 else 'Онлайн'

    for key in courses:
        if key == e_info[enroll]['course_hash']:
            to_admin_text += f"❓ Курс : {courses[key]['name']}'; \n\t" \
                             f"▶️ Група 📅(🕒){e_info[enroll]['daytime']} 🌐{group_type}\n"
    return to_admin_text


def AnswerEnroll(user_id, enroll_id, answer, call):
    result = 'Ошибка ответа на заявку'
    answer_text = str()
    admin_answer = str()
    admin_log_text = str()
    try:
        courses = DataBase.getCourses(DataBase())
        e_info = Group.read(Group(), enroll_id)
        client = User.read(User(), user_id)
        print(client)
        for key in courses:
            if key == e_info[enroll_id]['course_hash']:
                group_type = 'Офлайн' if e_info[enroll_id]['offline'] == 1 else 'Онлайн'
                text = f"Ваш запит на зачислення до курсу: \n▶️ {courses[key]['name']}\n" \
                       f"▶️ Група 📅(🕒){e_info[enroll_id]['daytime']} 🌐{group_type}"
                if answer == 'accept':
                    answer_text = f"\n\n <b>✅ПРИЙНЯТО✅</b>"
                    admin_answer = '<b>ПІДТВЕРДИЛА</b>'
                elif answer == 'cancel':
                    answer_text = f"\n\n<b>❎ВІДХИЛЕНО❎</b>"
                    admin_answer = '<b>ВІДХИЛИЛА</b>'
                admin_log_text = f" ✅\n{call.from_user.full_name} {admin_answer} заявку від\n" \
                                 f"🎓 {client['name']} (@{client['nickname']})( {client['contact']} )\n" \
                                 f"До групи :\n  📅(🕒){e_info[enroll_id]['daytime']} 🌐{group_type}\n"\
                                 f"У курсі :\n🔵 <b>{courses[key]['name']}</b>"
                result = text + answer_text
                break
    except:
        PrintException()
    print(result, '\n', admin_log_text)
    return result, admin_log_text


def NotificationText(group_id, user_id):
    now = datetime.now()
    courses = DataBase.getCourses(DataBase())
    g_info = Group.read(Group(), group_id)
    users = User.read(User())
    morning = datetime.now().replace(hour=9, minute=00)
    day = datetime.now().replace(hour=12, minute=00)
    evening = datetime.now().replace(hour=18, minute=00)
    greet = "Привіт"
    course_name = 'у нашому закладі'
    if morning < now < day:
        greet = 'Доброго ранку, '
    elif day < now < evening:
        greet = 'Добрий день, '
    elif evening < now:
        greet = 'Добрий вечір, '
    group_type = 'Офлайн' if g_info[group_id]['offline'] == 1 else 'Онлайн'
    for key in courses:
        if key == g_info[group_id]['course_hash']:
            course_name = courses[key]['name']
            break

    note_text = f"{greet}{users[user_id]['name']}, освітній центр ЯІМОЯШКОЛА, нагадує вам, " \
                f"що ближчим чаосом ми чекаємо вас на заняття у групі \n" \
                f"Група: \n📅(🕒){g_info[group_id]['daytime']} 🌐{group_type} \n" \
                f"до курсу: \n{course_name}"
    return note_text

def Registered_greeting(type_, name):
    text = f"Привіт ми вже знайомі, ви {type_} <i>{name}</i>" \
           f" в нашому освітньому центрі"
    return text

def LogText(log):
    if log['type'] == 'ERR':
            point = '🔴'
    elif log['type'] == 'INFO':
        point = '🔵'
    elif log['type'] == 'WARN':
        point = '⚪️'
    else:
        point = '✔️'
    text = f"{point} #{log['type']}\n" \
           f"От : {log['user_name']} ({log['user_id']}) \n" \
           f"Время : {log['time']}\n" \
           f"Log : \n" \
           f"{log['content']}"
    return text

