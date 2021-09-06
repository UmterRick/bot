from flask import Flask
from flask_admin.form import fields
from flask_admin.contrib.sqla import ModelView
from sqlalchemy import Integer, ForeignKey, String
from flask_admin import Admin
from flask_sqlalchemy import  SQLAlchemy
from wtforms import form, fields

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

    def __repr__(self):
        return self.name




class GroupModel(db.Model):
    __tablename__ = 'groups'

    id = db.Column(Integer, primary_key=True)
    daytime = db.Column(String(255))
    type = db.Column(Integer)
    chat = db.Column(String(255))
    course = db.Column(Integer, ForeignKey('courses.id', ondelete='CASCADE', onupdate='CASCADE'))

    def __repr__(self):
        return self.course, self.daytime


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
admin.add_view(ModelView(Course, db.session))
admin.add_view(UserView(User, db.session))

db.create_all()
app.secret_key = app.config['SECRET']

if __name__ == "__main__":
    app.run()