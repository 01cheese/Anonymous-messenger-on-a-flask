from flask import Flask, render_template, redirect, url_for, request, abort
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, join_room, leave_room, send
import uuid
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///chat.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
socketio = SocketIO(app)

# Модель комнаты
class Room(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)  # Поле для времени последней активности

# Модель сообщения
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.String(36), db.ForeignKey('room.id'), nullable=False)
    username = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.String(5), nullable=False)

# Инициализация базы данных
with app.app_context():
    db.create_all()

# Главная страница
@app.route('/')
def index():
    return render_template('index.html')

# Маршрут для создания комнаты
@app.route('/create_room')
def create_room():
    room_id = str(uuid.uuid4())  # Генерация уникального идентификатора комнаты
    new_room = Room(id=room_id)
    db.session.add(new_room)
    db.session.commit()
    room_link = request.host_url + 'room/' + room_id  # Создание полной ссылки на комнату
    return render_template('room_link.html', room_link=room_link)

# Маршрут для комнаты чата
@app.route('/room/<room_id>')
def chat_room(room_id):
    room = Room.query.get(room_id)
    if not room:  # Если комната была удалена
        abort(404)  # Возвращаем ошибку 404
    return render_template('chat_room.html', room_id=room_id)

# Обработчик для подключения пользователя к комнате
@socketio.on('join')
def on_join(data):
    room_id = data['room']
    username = data['username']
    join_room(room_id)

    # Отправка предыдущих сообщений пользователю
    messages = Message.query.filter_by(room_id=room_id).all()
    for msg in messages:
        send({'username': msg.username, 'message': msg.content, 'time': msg.timestamp}, to=request.sid)

    # Системное сообщение о присоединении
    system_message = {
        'username': 'System',
        'message': f"{username} has joined the room",
        'time': datetime.now().strftime('%H:%M'),
        'type': 'system'
    }

    send(system_message, to=room_id)

# Обработчик для отправки сообщений
@socketio.on('message')
def handle_message(data):
    room_id = data['room']
    message = data['message']
    username = data['username']

    room = Room.query.get(room_id)

    if not room:  # Если комната не найдена (удалена)
        send({'username': 'System', 'message': 'This chat room no longer exists.',
              'time': datetime.now().strftime('%H:%M'), 'type': 'system'}, to=request.sid)
        return  # Останавливаем выполнение, так как комната не существует

    # Обновляем время последней активности комнаты
    room.last_activity = datetime.utcnow()
    db.session.commit()

    # Форматируем время отправки сообщения
    timestamp = datetime.now().strftime('%H:%M')

    # Сохранение сообщения в базе данных
    new_message = Message(room_id=room_id, username=username, content=message, timestamp=timestamp)
    db.session.add(new_message)
    db.session.commit()

    # Отправка сообщения в комнату
    send({'username': username, 'message': message, 'time': timestamp}, to=room_id)


# Обработчик для выхода из комнаты
@socketio.on('leave')
def on_leave(data):
    room_id = data['room']
    username = data['username']
    leave_room(room_id)

    # Системное сообщение о выходе
    system_message = {
        'username': 'System',
        'message': f"{username} has left the room",
        'time': datetime.now().strftime('%H:%M'),
        'type': 'system'
    }

    send(system_message, to=room_id)

# Фоновая задача для удаления неактивных комнат
def delete_inactive_rooms():
    with app.app_context():  # Входим в контекст приложения
        now = datetime.utcnow()
        threshold = now - timedelta(seconds=10)  # Порог активности: 1 минута
        inactive_rooms = Room.query.filter(Room.last_activity < threshold).all()

        for room in inactive_rooms:
            # Удаление сообщений, связанных с комнатой
            Message.query.filter_by(room_id=room.id).delete()
            # Удаление самой комнаты
            db.session.delete(room)

        db.session.commit()

# Инициализация планировщика задач
scheduler = BackgroundScheduler()
scheduler.add_job(func=delete_inactive_rooms, trigger="interval", seconds=1)  # Проверка каждые 30 секунд
scheduler.start()

# Остановка планировщика при завершении работы приложения
atexit.register(lambda: scheduler.shutdown())

# Обработчик для кастомной страницы ошибки 404
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

if __name__ == '__main__':
    socketio.run(app, debug=True)
