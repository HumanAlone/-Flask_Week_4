from os import path
from json import load, dump
from random import sample, shuffle

from flask import Flask, render_template, request as req
from flask_migrate import Migrate
from flask_wtf import FlaskForm, CSRFProtect
from wtforms import StringField, RadioField, SelectField
from wtforms.validators import InputRequired, Length
from flask_sqlalchemy import SQLAlchemy

from json_service import make_a_database

app = Flask(__name__)
csrf = CSRFProtect(app)
csrf.init_app(app)
SECRET_KEY = r'0\'\xc7^\x00\x9dD\x1d\x96\xfc\xc4"\xe6\x1a\x11\x920\x11\xa2ks\x80\xf8\xa7f(' \
             r'\x17\x9f\xda\xe8g.\r<ie\xd5\x13\x98\xa4\xe1o '

app.config.update(
    DEBUG=True,  # Заменить
    SECRET_KEY=SECRET_KEY,
    SQLALCHEMY_DATABASE_URI='sqlite:///tutor.db',
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
)
db = SQLAlchemy(app)
migrate = Migrate(app, db)
make_a_database()  # Make a json file teachers.json
days_of_week = {"mon": "Понедельник", "tue": "Вторник", "wed": "Среда", "thu": "Четверг",
                "fri": "Пятница", "sat": "Суббота", "sun": "Воскресенье"}
goals = {"travel": "⛱ Для путешествий", "study": "🏫 Для школы", "work": "🏢 Для работы",
         "relocate": "🚜 Для переезда", "programming": "💻 Для программирования"}
goal_tags = ["travel", "study", "work", "relocate", "programming"]
try:
    with open("teachers.json", "r") as f_inp:
        teachers = load(f_inp)
except FileNotFoundError:
    teachers = None

teachers_goals_association = db.Table('teachers_goals',
                                      db.Column('teacher_id', db.Integer, db.ForeignKey('teachers.id')),
                                      db.Column('goal_id', db.Integer, db.ForeignKey('goals.id'))
                                      )


class Goal(db.Model):
    __tablename__ = "goals"
    id = db.Column(db.Integer, primary_key=True)
    goal = db.Column(db.String(25), nullable=False)
    teachers = db.relationship("Teacher", secondary=teachers_goals_association, back_populates="goals")


class Booking(db.Model):
    __tablename__ = "bookings"
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey("teachers.id"))
    time = db.Column(db.String, nullable=False)
    weekday = db.Column(db.String(3), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    teacher = db.relationship("Teacher", back_populates="bookings")


class Teacher(db.Model):
    __tablename__ = "teachers"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    about = db.Column(db.String(250), nullable=False, unique=True)
    rating = db.Column(db.Float, nullable=False)
    picture = db.Column(db.String, nullable=False)
    price = db.Column(db.Float, nullable=False)
    free = db.Column(db.JSON, nullable=False)
    goals = db.relationship("Goal", secondary=teachers_goals_association, back_populates="teachers")
    bookings = db.relationship("Booking", back_populates="teacher")


for teacher in teachers:
    goals = []
    for goal in teacher['goals']:
        goals.append(Goal(goal=goal))

    temp_teacher = Teacher(name=teacher['name'], about=teacher['about'], rating=teacher['rating'],
                           picture=teacher['picture'], price=teacher['price'], free=teacher['free'],
                           goals=goals)
    db.session.add(temp_teacher)
db.session.commit()


class Request(db.Model):
    __tablename__ = "requests"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    time = db.Column(db.String(10), nullable=False)
    goal = db.Column(db.String(15), nullable=False)


class BookingForm(FlaskForm):
    client_weekday = StringField("День недели")
    client_time = StringField("Время")
    client_teacher = StringField("Идентификатор преподавателя")
    client_name = StringField("Имя клиента", validators=[InputRequired(message="Введите своё имя")])
    client_phone = StringField("Номер телефона клиента", validators=[InputRequired(), Length(min=11, max=12)])


class RequestForm(FlaskForm):
    client_goal = RadioField('Цели', default="Для путешествий",
                             choices=[("Для путешествий", "Для путешествий"), ("Для школы", "Для школы"),
                                      ("Для работы", "Для работы"),
                                      ("Для переезда", "Для переезда")])
    client_time = RadioField('Время', default="1-2 часа в неделю",
                             choices=[("1-2 часа в неделю", "1-2 часа в неделю"),
                                      ("3-5 часов в неделю", "3-5 часов в неделю"),
                                      ("5-7 часов в неделю", "5-7 часов в неделю"),
                                      ("7-10 часов в неделю",
                                       "7-10 часов в неделю")])
    client_name = StringField("Имя клиента", validators=[InputRequired(message="Введите своё имя")])
    client_phone = StringField("Номер телефона клиента", validators=[InputRequired(), Length(min=11, max=12)])


class SelectSorting(FlaskForm):
    sorting = SelectField('Сортировка', choices=[('1', 'В случайном порядке'), ('2', 'Сначала лучшие по рейтингу'),
                                                 ('3', 'Сначала дорогие'), ('4', 'Сначала недорогие')])


def find_teacher_by_id(teachers, teachers_id):
    """ Returns a teacher by id """
    for teacher in teachers:
        if teachers_id == teacher["id"]:
            teacher_temp = teacher
            return teacher_temp


def sort_teachers(unsorted_teachers, option):
    """ Returns a sorted teacher array """
    sorted_teachers = []
    if option == '1':
        sorted_teachers = unsorted_teachers[:]
        shuffle(sorted_teachers)
    elif option == '2':
        sorted_teachers = unsorted_teachers.order_by(Teacher.rating.desc()).all()
    elif option == '3':
        sorted_teachers = unsorted_teachers.order_by(Teacher.price.desc()).all()
    elif option == '4':
        sorted_teachers = unsorted_teachers.order_by(Teacher.price).all()
    return sorted_teachers


@app.route("/")
@app.route('/index')
def index():
    teachers = db.session.query(Teacher).all()
    if teachers is None:
        return server_error(500)
    return render_template("index.html", teachers=sample(teachers, 6), goals=goals)


@app.route("/all", methods=["POST", "GET"])
def all_():
    form = SelectSorting()
    teachers = db.session.query(Teacher)
    if req.method == "GET":
        return render_template("all.html", teachers=teachers, form=form)
    sorting_option = form.sorting.data
    temp = sort_teachers(teachers, sorting_option)
    return render_template("all.html", form=form, teachers=temp)


@app.route("/goals/<int:goal>/")
def goals_view(goal):
    if goal not in range(1, 6):
        return render_not_found(404)
    teachers_temp = []
    goal_temp = goals[goal_tags[goal - 1]]
    for teacher in teachers:
        if goal_tags[goal - 1] in teacher["goals"]:
            teachers_temp.append(teacher)
    return render_template("goal.html", teachers=sorted(teachers_temp, key=lambda x: x["rating"], reverse=True),
                           goal=goal_temp)


@app.route("/profiles/<int:teachers_id>/")
def profiles(teachers_id):
    teacher = db.session.query(Teacher).filter(Teacher.id == teachers_id).all()
    if not teacher:
        return render_not_found(404)
    return render_template("profile.html", teacher=teacher[0], days_of_week=days_of_week)


@app.route("/request/")
def request():
    form = RequestForm()
    return render_template("request.html", form=form)


@app.route("/request_done/", methods=['POST'])
def request_done():
    name = req.form.get("client_name")
    phone = req.form.get("client_phone")
    time = req.form["client_time"]
    goal = req.form.get("client_goal")
    request_temp = Request(name=name, phone=phone, time=time, goal=goal)
    db.session.add(request_temp)
    db.session.commit()
    return render_template("request_done.html", name=name, phone=phone, time=time, goal=goal)


@app.route("/booking/<int:teachers_id>/<day_of_week>/<time>/")
def booking(teachers_id, day_of_week, time):
    form = BookingForm()
    teacher = find_teacher_by_id(teachers, teachers_id)
    day = days_of_week.get(day_of_week, 0)
    if not teacher or not day:
        return render_not_found(404)
    return render_template("booking.html", id=teachers_id, day_of_week=day, time=time,
                           teacher=teacher, form=form)


@app.route("/booking_done/", methods=["POST"])
def booking_done():
    form = BookingForm()
    weekday = form.client_weekday.data
    time = form.client_time.data
    teacher = form.client_teacher.data
    name = form.client_name.data
    phone = form.client_phone.data
    book = Booking(teacher_id=teacher, time=time, weekday=weekday, name=name, phone=phone)
    db.session.add(book)
    db.session.commit()
    return render_template("booking_done.html", form=form, name=name, phone=phone, weekday=weekday, time=time,
                           teacher=teacher)


@app.template_filter()
def any_filter(list_):
    """ A custom filter returns true if there is at least one element in a collection """
    return any(list_)


@app.errorhandler(404)
def render_not_found(error):
    return f'<center><h1>Ничего не нашлось!</h1><img src="/static/Ошибка 404.png" alt="Фото потерялось..."></center>'


@app.errorhandler(500)
def server_error(error):
    return f'<center><h1>Вы сломали сервер! Ошибка {error}</h1></center>'


if __name__ == "__main__":
    app.run()
