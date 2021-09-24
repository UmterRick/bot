import datetime
import json

from flask import Flask
from flask_admin.form import fields, rules
from flask_admin.contrib.sqla import ModelView
from flask_admin.model import typefmt
from flask_admin.model.template import macro
from sqlalchemy import Integer, ForeignKey, String, Time
from flask_admin import Admin
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


class UserGroupModel(db.Model):
    __tablename__ = 'user_group'
    id = db.Column(Integer, autoincrement=True, primary_key=True)
    user = db.Column(Integer, ForeignKey('users.id', ondelete='CASCADE', onupdate='CASCADE'))
    group = db.Column(Integer, ForeignKey('users.id', ondelete='CASCADE', onupdate='CASCADE'))
    type = db.Column(String(255))

    def __repr__(self):
        return self.id


admin = Admin(app, name='Bot', template_mode='bootstrap3')
admin.add_view(ModelView(Category, db.session))
admin.add_view(CourseView(Course, db.session))
admin.add_view(UserView(User, db.session))
admin.add_view(GroupView(Group, db.session))

app.secret_key = app.config['SECRET']

if __name__ == "__main__":
    db.create_all()
    app.run()
