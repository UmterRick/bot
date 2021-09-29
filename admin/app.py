import datetime
import json
from flask import url_for, redirect, render_template, request
from flask_admin.contrib import sqla
from flask import Flask
from flask_admin.form import fields, rules
from flask_admin.contrib.sqla import ModelView
from flask_admin.model import typefmt
from flask_admin.model.template import macro
from sqlalchemy import Integer, ForeignKey, String, Time
from flask_admin import Admin, AdminIndexView, helpers, expose
import flask_login as login
from werkzeug.security import generate_password_hash, check_password_hash

from flask_sqlalchemy import SQLAlchemy
from wtforms import form, fields, validators
from utils import week_days_translate

app = Flask(__name__)
app.config['FLASK_ADMIN_SWATCH'] = 'cerulean'
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://postgres:postgres@localhost:5432/botdb"
app.config['SECRET'] = '\x08/\x8a\x15(~\xe6\xe85-\xc7\x93\xdd\xb7\x88\xd0\xd9\xb1\xa5&\x98\xf8P'
db = SQLAlchemy(app)


# Add administrative views here


class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(Integer, primary_key=True)
    name = db.Column(String(255))
    courses = db.relationship('Course', backref='Category',
                              lazy='dynamic')

    def __repr__(self):
        return self.name


class CategoryView(ModelView):
    def is_accessible(self):
        return login.current_user.is_authenticated


class Course(db.Model):
    __tablename__ = 'courses'

    id = db.Column(Integer, primary_key=True)
    name = db.Column(String(255))
    trainer = db.Column(String(255))
    description = db.Column(String(255))
    price = db.Column(db.Integer)
    category = db.Column(Integer, ForeignKey('categories.id', ondelete='CASCADE', onupdate='CASCADE'))
    groups = db.relationship('Group', backref='Course', lazy='dynamic')

    def __repr__(self):
        return self.name


class CourseView(ModelView):
    column_list = ('id', 'name', 'trainer', 'price', 'description', 'category',)
    column_sortable_list = ('price', 'category')
    column_searchable_list = ('trainer', 'category', 'name')

    def on_model_change(self, form, model, is_created):
        try:
            trainer = json.loads(form.trainer._value())
            a = trainer['trainer']
            super().on_model_change(form, model, is_created)
        except Exception as ex:
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

    def __init__(self, stream, day, program_day, time, type: bool, chat, course):
        self.stream = stream
        self.day = day
        self.time = time
        self.type = type
        self.program_day = program_day
        self.chat = chat
        self.course = course

    def __repr__(self):
        return f"Stream: {self.stream} | Day: {self.day} | Time: {self.time}"


class GroupView(ModelView):
    column_list = ('stream', 'day', 'time', 'type', 'course')
    form_excluded_columns = ('program_day', 'chat')
    column_searchable_list = ('course', 'day')
    column_sortable_list = ('stream', 'day', 'time', 'type', 'course')
    form_choices = {
        'day': [
            ('Понеділок', 'Понеділок'), ('Вівторок', 'Вівторок'),
            ('Середа', 'Середа'), ('Четвер', 'Четвер'),
            ("П'ятниця", "П'ятниця"), ('Субота', 'Субота'), ('Неділя', 'Неділя')],

        'type': [('Yes', 'Yes'), ('No', 'No')]

    }
    column_labels = dict(type='Offline?')

    def on_model_change(self, form, model, is_created):
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
    form_columns = ('name', 'nickname', 'telegram', 'type', 'contact')
    form_excluded_columns = ('state', 'at_category')

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
    column_list = ('name', 'nickname', 'contact', 'type',)
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
    user = db.Column(Integer, ForeignKey('users.id', ondelete='CASCADE', onupdate='CASCADE'))
    group = db.Column(Integer, ForeignKey('users.id', ondelete='CASCADE', onupdate='CASCADE'))
    type = db.Column(String(255))

    def __repr__(self):
        return self.id


# Create user model.
class UserLogin(db.Model):
    __tablename__ = 'user_login'
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(80), unique=True)
    password = db.Column(db.String(255))

    # Flask-Login integration
    # NOTE: is_authenticated, is_active, and is_anonymous
    # are methods in Flask-Login < 0.3.0
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

    # Required for administrative interface
    def __unicode__(self):
        return self.username


# Define login and registration forms (for flask-login)
class LoginForm(form.Form):
    login = fields.StringField(validators=[validators.data_required()])
    password = fields.PasswordField(validators=[validators.data_required()])

    def validate_login(self, field):
        user = self.get_user()

        if user is None:
            raise validators.ValidationError('Invalid user')

        # we're comparing the plaintext pw with the the hash from the db
        if not check_password_hash(user.password, self.password.data):
            # to compare plain text passwords use
            # if user.password != self.password.data:
            raise validators.ValidationError('Invalid password')

    def get_user(self):
        return db.session.query(UserLogin).filter_by(login=self.login.data).first()


class RegistrationForm(form.Form):
    login = fields.StringField(validators=[validators.data_required()])
    email = fields.StringField()
    password = fields.PasswordField(validators=[validators.data_required()])

    def validate_login(self, field):
        if db.session.query(UserLogin).filter_by(login=self.login.data).count() > 0:
            raise validators.ValidationError('Duplicate username')


# Initialize flask-login
def init_login():
    login_manager = login.LoginManager()
    login_manager.init_app(app)

    # Create user loader function
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.query(UserLogin).get(user_id)


# Create customized model view class
class MyModelView(sqla.ModelView):

    def is_accessible(self):
        return login.current_user.is_authenticated


# Create customized index view class that handles login & registration
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
            from flask_admin.model import BaseModelView
            print("====" * 50)
            cv = CourseView(Course, db.session)
            cv.is_visible()

            return redirect(url_for('.index'))
        # link = '<p>Don\'t have an account? <a href="' + url_for('.register_view') + '">Click here to
        # register.</a></p>'
        self._template_args['form'] = form
        # self._template_args['link'] = link
        return super(MyAdminIndexView, self).index()

    @expose('/register/', methods=('GET', 'POST'))
    def register_view(self):
        form = RegistrationForm(request.form)
        if helpers.validate_form_on_submit(form):
            user = UserLogin()

            form.populate_obj(user)
            # we hash the users password to avoid saving it as plaintext in the db,
            # remove to use plain text:
            user.password = generate_password_hash(form.password.data)

            db.session.add(user)
            db.session.commit()

            login.login_user(user)
            return redirect(url_for('.index'))
        link = '<p>Already have an account? <a href="' + url_for('.login_view') + '">Click here to log in.</a></p>'
        self._template_args['form'] = form
        self._template_args['link'] = link
        return super(MyAdminIndexView, self).index()

    @expose('/logout/')
    def logout_view(self):
        global admin
        login.logout_user()
        admin._views = []
        return redirect(url_for('.index'))


# Flask views
@app.route('/')
def index():
    return render_template('index.html')


# Initialize flask-login
init_login()

admin = Admin(app, name='Bot', index_view=MyAdminIndexView(), base_template='my_master.html',
              template_mode='bootstrap4')

# Add view
# admin.add_view(MyModelView(UserLogin, db.session))
try:
    admin.add_view(CategoryView(Category, db.session))
    admin.add_view(CourseView(Course, db.session))
    admin.add_view(UserView(User, db.session))
    admin.add_view(GroupView(Group, db.session))
except ValueError:
    pass
app.secret_key = app.config['SECRET']

if __name__ == "__main__":
    db.create_all()
    admin_user = UserLogin(login='Admin', password=generate_password_hash('123456'))
    db.session.commit()
    app.run(port=8000)
