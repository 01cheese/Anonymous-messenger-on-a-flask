from flask import Flask, render_template, redirect, url_for, request, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate  # Импортируем Flask-Migrate
from uuid import uuid4

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite'
app.config['SECRET_KEY'] = 'your_secret_key'  # Замените на случайное значение для безопасности
db = SQLAlchemy(app)


# Инициализируем Flask-Migrate
migrate = Migrate(app, db)



# Модель чата
class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chat_link = db.Column(db.String(100), unique=True)
    user_1 = db.Column(db.String(100), nullable=True)
    user_2 = db.Column(db.String(100), nullable=True)



# Главная страница
@app.route('/')
def index():
    return render_template('index.html')


# Создание нового чата
@app.route('/create_chat', methods=['POST'])
def create_chat():
    chat_link = str(uuid4())
    chat = Chat(chat_link=chat_link)
    db.session.add(chat)
    db.session.commit()
    return f'Ссылка на чат: {request.host_url}join_chat/{chat_link}'


# Присоединение к чату
@app.route('/join_chat/<chat_link>', methods=['GET', 'POST'])
def join_chat(chat_link):
    chat = Chat.query.filter_by(chat_link=chat_link).first()
    if not chat:
        return "Чат не найден", 404

    if request.method == 'POST':
        username = request.form['username']

        # Проверяем, чтобы пользователь не пытался занять оба места
        if session.get('username') in [chat.user_1, chat.user_2]:
            return redirect(url_for('chat_room', chat_link=chat_link))

        if chat.user_1 is None:
            chat.user_1 = username
        elif chat.user_2 is None:
            chat.user_2 = username
        else:
            return "Чат уже полон!", 400

        db.session.commit()
        session['username'] = username
        return redirect(url_for('chat_room', chat_link=chat_link))

    return render_template('join_chat.html', chat=chat)


# Комната чата
@app.route('/chat_room/<chat_link>')
def chat_room(chat_link):
    chat = Chat.query.filter_by(chat_link=chat_link).first()
    if not chat:
        return "Чат не найден", 404
    if session.get('username') not in [chat.user_1, chat.user_2]:
        return "Вы не участник этого чата", 403

    return render_template('chat.html', chat=chat)


# Запуск приложения
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Создаем таблицы при запуске
    app.run(debug=True)
