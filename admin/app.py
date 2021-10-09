import json
import flask_login as login
from flask_admin.contrib.sqla import ModelView
from flask_admin.contrib.fileadmin import FileAdmin
from flask import url_for, redirect, render_template, request, Flask
from sqlalchemy import Integer, ForeignKey, String, Time
from flask_admin import Admin, AdminIndexView, helpers, expose, BaseView
from werkzeug.security import generate_password_hash, check_password_hash
from flask_babelex import Babel
from flask_sqlalchemy import SQLAlchemy
from wtforms import form, fields, validators
from utils import week_days_translate, ROOT_DIR, read_config, set_logger

app = Flask(__name__)
db_config = read_config('database.json')
app.config['FLASK_ADMIN_SWATCH'] = 'cerulean'
app.config['SQLALCHEMY_DATABASE_URI'] = db_config.get('url')
app.config['SECRET'] = '\x08/\x8a\x15(~\xe6\xe85-\xc7\x93\xdd\xb7\x88\xd0\xd9\xb1\xa5&\x98\xf8P'
db = SQLAlchemy(app)
babel = Babel(app)
admin_logger = set_logger('admin_panel')


class LoginView(ModelView):
    can_create = False
    can_edit = False
    can_delete = False
    can_set_page_size = False
    can_view_details = False

    def is_accessible(self):
        return False


class LogsView(ModelView):

    def is_accessible(self):
        return login.current_user.is_authenticated


class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(Integer, primary_key=True)
    name = db.Column(String(255))
    courses = db.relationship('Course', backref='Category',
                              lazy='dynamic')

    def __repr__(self):
        return self.name


class CategoryView(ModelView):
    column_list = ('id', 'name')

    def is_accessible(self):
        return login.current_user.is_authenticated


class Course(db.Model):
    __tablename__ = 'courses'

    id = db.Column(Integer, primary_key=True)
    name = db.Column(String(255))
    trainer = db.Column(String(255))
    description = db.Column(String(255))
    link = db.Column(String(255))
    price = db.Column(db.Integer)
    category = db.Column(Integer, ForeignKey('categories.id', ondelete='CASCADE', onupdate='CASCADE'))
    groups = db.relationship('Group', backref='Course', lazy='dynamic')

    def __repr__(self):
        return self.name


class CourseView(ModelView):
    column_list = ('id', 'name', 'trainer', 'link', 'price', 'description', 'category',)
    column_sortable_list = ('id', 'price', 'category')
    column_searchable_list = ('id', 'trainer', 'category', 'name')

    def on_model_change(self, form, model, is_created):
        try:
            trainer = json.loads(form.trainer._value())
            super().on_model_change(form, model, is_created)
        except Exception as ex:
            admin_logger.warning(f"Incorrect trainers pattern {model}")
            raise validators.ValidationError('Check trainer filed pattern {"trainer": ["name1", "name2"]}')

    def is_accessible(self):
        return login.current_user.is_authenticated


class CourseViewEmpty(ModelView):
    column_list = ()


class Group(db.Model):
    __tablename__ = 'groups'

    id = db.Column(Integer, primary_key=True)
    stream = db.Column(Integer)
    day = db.Column(String(255))
    program_day = db.Column(String(40))
    time = db.Column(Time)
    type = db.Column(Integer)
    chat = db.Column(String(255))
    course = db.Column(Integer, ForeignKey('courses.id', ondelete='CASCADE', onupdate='CASCADE'))

    query = db.session.query_property(SQLAlchemy.Query)

    def __init__(self, stream, day, program_day, time, type_: bool, chat, course):
        self.stream = stream
        self.day = day
        self.time = time
        self.type = type_
        self.program_day = program_day
        self.chat = chat
        self.course = course

    def __repr__(self):
        return f"Stream: {self.stream} | Day: {self.day} | Time: {self.time}"


class GroupView(ModelView):
    column_list = ('id', 'stream', 'day', 'time', 'type', 'course')
    form_excluded_columns = ('program_day', 'chat')
    column_searchable_list = ('id', 'course', 'day')
    column_sortable_list = ('id', 'stream', 'day', 'time', 'type', 'course')
    form_choices = {
        'day': [
            ('Понеділок', 'Понеділок'), ('Вівторок', 'Вівторок'),
            ('Середа', 'Середа'), ('Четвер', 'Четвер'),
            ("П'ятниця", "П'ятниця"), ('Субота', 'Субота'), ('Неділя', 'Неділя')],

        'type': [('Yes', 'Yes'), ('No', 'No')]

    }
    column_labels = dict(type='Offline?')

    def on_model_change(self, form_, model, is_created):
        model.type = True if model.type == "Yes" else False
        model.program_day = week_days_translate[model.day]
        return model

    def on_model_delete(self, model):
        Group.query.filter(Group.stream == model.stream, Group.course == model.course).delete(
            synchronize_session='evaluate')

    def is_accessible(self):
        return login.current_user.is_authenticated


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(Integer, primary_key=True)
    name = db.Column(String(255))
    nickname = db.Column(String(255))

    telegram = db.Column(Integer)
    contact = db.Column(String(40))
    type = db.Column(Integer)
    state = db.Column(String(255))
    at_category = db.Column(String(255))
    temp_state_1 = db.Column(String(255))
    temp_state_2 = db.Column(String(255))

    def __repr__(self):
        return self.name, self.type


class UserView(ModelView):
    column_list = ('id', 'name', 'nickname', 'contact', 'type',)
    column_editable_list = ('name', 'nickname', 'contact', 'type')
    form_columns = ('name', 'nickname', 'contact', 'type',)
    column_sortable_list = ('name', 'nickname', 'contact', 'type',)
    column_searchable_list = ('name', 'nickname', 'contact', 'type')
    can_create = False
    form_choices = {
        'type': [
            ('admin', 'admin'), ('trainer', 'trainer'), ('student', 'student')
        ]}

    def on_model_change(self, form, model, is_created):
        if model.type == 'admin':
            model.type = 1
        elif model.type == 'trainer':
            model.type = 2
        elif model.type == 'student':
            model.type = 3
        return model

    def is_accessible(self):
        return login.current_user.is_authenticated


class UserGroupModel(db.Model):
    __tablename__ = 'user_group'
    id = db.Column(Integer, autoincrement=True, primary_key=True)
    user_id = db.Column(Integer, ForeignKey('users.id', ondelete='CASCADE', onupdate='CASCADE'))
    group_id = db.Column(Integer, ForeignKey('users.id', ondelete='CASCADE', onupdate='CASCADE'))
    type = db.Column(String(255))

    def __repr__(self):
        return self.id


class UserGroupView(ModelView):
    column_list = ('id', 'user_id', 'group_id', 'type')
    column_editable_list = ('user_id', 'group_id', 'type')
    column_sortable_list = ('user_id', 'group_id', 'type')
    column_searchable_list = ('user_id', 'group_id', 'type')
    form_columns = ('user_id', 'group_id', 'type')
    form_choices = {
        'type': [
            ('enroll', 'enroll'), ('trainer', 'trainer'), ('student', 'student')
        ]}

    def is_accessible(self):
        return login.current_user.is_authenticated


# Create user model.
class UserLogin(db.Model):
    __tablename__ = 'user_login'
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(80), unique=True)
    password = db.Column(db.String(255))

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id

    def __unicode__(self):
        return self.username


class LoginForm(form.Form):
    login = fields.StringField(validators=[validators.data_required()])
    password = fields.PasswordField(validators=[validators.data_required()])

    def validate_login(self, field):
        user = self.get_user()

        if user is None:
            raise validators.ValidationError('Invalid user')

        if not check_password_hash(user.password, self.password.data):
            raise validators.ValidationError('Invalid password')

    def get_user(self):
        return db.session.query(UserLogin).filter_by(login=self.login.data).first()


class Configs(FileAdmin):
    can_delete = False
    can_rename = False
    can_mkdir = False
    can_delete_dirs = False
    can_upload = False
    editable_extensions = ('json', 'txt')

    def is_accessible(self):
        return login.current_user.is_authenticated


class MyAdminIndexView(AdminIndexView):

    @expose('/')
    def index(self):
        if not login.current_user.is_authenticated:
            return redirect(url_for('.login_view'))
        return super(MyAdminIndexView, self).index()

    @expose('/login/', methods=('GET', 'POST'))
    def login_view(self):
        # handle user login
        form = LoginForm(request.form)
        if helpers.validate_form_on_submit(form):
            user = form.get_user()
            login.login_user(user)

        if login.current_user.is_authenticated:
            return redirect(url_for('.index'))
        self._template_args['form'] = form
        return super(MyAdminIndexView, self).index()

    @expose('/logout/')
    def logout_view(self):
        login.logout_user()
        return redirect(url_for('.index'))


@app.route('/')
def index():
    return render_template('index.html')


def init_login():
    login_manager = login.LoginManager()
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.query(UserLogin).get(user_id)


class MainLogView(BaseView):
    @expose('/')
    def index(self):
        with open(ROOT_DIR + '/log/main.log', 'r') as m_logs:
            content = m_logs.read()

        return self.render('log_template.html', content=content)

    def is_accessible(self):
        return login.current_user.is_authenticated


class DBLogView(BaseView):
    @expose('/')
    def index(self):
        with open(ROOT_DIR + '/log/database.log', 'r') as m_logs:
            content = m_logs.read()

        return self.render('log_template.html', content=content)

    def is_accessible(self):
        return login.current_user.is_authenticated


class UtilsLogView(BaseView):
    @expose('/')
    def index(self):
        with open(ROOT_DIR + '/log/utils.log', 'r') as m_logs:
            content = m_logs.read()

        return self.render('log_template.html', content=content)

    def is_accessible(self):
        return login.current_user.is_authenticated


init_login()
admin = Admin(app, name='Bot', index_view=MyAdminIndexView(), base_template='my_master.html',
              template_mode='bootstrap4')

try:
    admin.add_view(LoginView(UserLogin, db.session))
    admin.add_view(CategoryView(Category, db.session))
    admin.add_view(CourseView(Course, db.session))
    admin.add_view(UserView(User, db.session))
    admin.add_view(GroupView(Group, db.session))
    admin.add_view(UserGroupView(UserGroupModel, db.session))
    admin.add_view(MainLogView(name='Main Logs', endpoint='/main_logs', category='Logs'))
    admin.add_view(DBLogView(name='Database Logs', endpoint='/database_logs', category='Logs'))
    admin.add_view(UtilsLogView(name='Utils Logs', endpoint='/utils_logs', category='Logs'))
    admin.add_view(Configs(ROOT_DIR + "/configs/", '/configs', name="Configs"))

except ValueError:
    pass
try:
    admin_user = UserLogin(login='Admin', password=generate_password_hash('123456'))
    db.session.add(admin_user)
except:
    pass
app.secret_key = app.config['SECRET']

