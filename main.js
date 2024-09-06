var socket = io();
var currentUsername = "{{ session.get('username') }}";
var replyToMessage = null;

socket.on('connect', function() {
    console.log('Connected to chat');
});

socket.on('message', function(msg) {
    displayMessage(msg);
});

socket.on('message_deleted', function(data) {
    var messageElement = document.getElementById(`message-${data.id}`);
    if (messageElement) {
        messageElement.remove();
    }
});

socket.on('message_edited', function(data) {
    document.getElementById(`message-text-${data.id}`).textContent = data.newMessage;
});

function sendMessage() {
    var input = document.getElementById('message_input');
    var message = input.value;

    var messageData = {
        'username': currentUsername,
        'message': message,
        'replyTo': replyToMessage
    };

    socket.send(messageData);
    input.value = '';
    replyToMessage = null;
}

function displayMessage(data) {
    var messagesDiv = document.getElementById('messages');
    var newMessageDiv = document.createElement('div');
    newMessageDiv.classList.add('message');
    newMessageDiv.id = `message-${data.id}`;

    if (data.username === currentUsername) {
        newMessageDiv.classList.add('self');
    } else {
        newMessageDiv.classList.add('other');
    }

    var time = new Date(data.timestamp).toLocaleTimeString();

    if (data.replyTo) {
        var replyDiv = document.createElement('div');
        replyDiv.classList.add('reply');
        replyDiv.innerText = `Ответ на: ${data.replyTo.message}`;
        newMessageDiv.appendChild(replyDiv);
    }

    newMessageDiv.innerHTML += `
        <p id="message-text-${data.id}" class="${data.username === '{{ chat.user_1 }}' ? 'user_1' : 'user_2'}">${data.message}</p>
        <div class="meta">От: ${data.username} | Время: ${time}</div>
    `;

    if (data.username === currentUsername) {
        newMessageDiv.innerHTML += `
            <div class="controls">
                <span onclick="editMessage(${data.id})">Edit</span> |
                <span onclick="deleteMessage(${data.id})">Delete</span>
            </div>
        `;
    } else {
        newMessageDiv.innerHTML += `
            <div class="controls">
                <span onclick="replyMessage(${data.id})">Reply</span>
            </div>
        `;
    }

    messagesDiv.appendChild(newMessageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function replyMessage(messageId) {
    replyToMessage = messageId;
}

function editMessage(messageId) {
    var newMessage = prompt("Введите новое сообщение:");
    if (newMessage) {
        socket.emit('edit', { id: messageId, newMessage: newMessage });
    }
}

function deleteMessage(messageId) {
    socket.emit('delete', { id: messageId });
}
