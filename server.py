import socket
import threading

HTML_CHAT_MARKUP = \
    "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n" \
    "<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n" \
    "p, li { white-space: pre-wrap; }\n" \
    "</style></head>" \
    "<body style=\" font-family:\'MS Shell Dlg 2\'; font-size:14pt; font-weight:400; font-style:normal;\">"

# HOST = '127.0.0.1'
HOST = socket.gethostbyname(socket.gethostname())
PORT = 9090
HEADER = 64
FORMAT = 'utf-8'
DISCONNECT_MESSAGE = '!!DISCONNECT!!'
NAME_MESSAGE = '!!NAME!!'
GET_USERS_LIST_MESSAGE = '!!GET_USERS_LIST!!'
NEW_USER_MESSAGE = '!!NEW_USER!!'
CHAT_MSG_MESSAGE = '!!CHAT_MSG!!'
CHAT_MSG_RECEIVED_MESSAGE = '!!CHAT_MSG_RECEIVED!!'
CHAT_CHANGED_MESSAGE = '!!CHAT_CHANGED_MESSAGE!!'
CHAT_HISTORY_MESSAGE = '!!CHAT_HISTORY!!'

ADMIN_NAME = '---ADMIN---'


def receive_msg(conn):
    msg_length = conn.recv(HEADER).decode(FORMAT)
    msg = ''

    if msg_length:
        msg_length = int(msg_length)
        msg = conn.recv(msg_length).decode(FORMAT)

    return msg


def send_msg(conn, msg):
    message = msg.encode(FORMAT)
    msg_length = str(len(message)).encode(FORMAT)
    msg_length += b' ' * (HEADER - len(msg_length))
    conn.send(msg_length)
    conn.send(message)


def get_own_html_message(msg):
    return "<p align=\"right\" style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; " \
           "-qt-block-indent:0; text-indent:0px;\">" \
           f"<span>{msg}</span></p>\n"


def get_user_html_message(user, msg):
    return "<p align=\"left\" style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; " \
           "-qt-block-indent:0; text-indent:0px;\">" \
           f"<span style=\"font-weight:600;\">{user}: </span>" \
           f"<span>{msg}</span></p>\n"


users_names = {}
connections = {}
chats_histories = {}


def get_chat_history_key(addr, current_chat):
    if (addr, current_chat) in chats_histories:
        return addr, current_chat
    elif (current_chat, addr) in chats_histories:
        return current_chat, addr
    else:
        return None


def admin_broadcast(admin_conn, msg):
    for _, conn in admin_conn:
        send_msg(conn[0], msg)


class Server:
    def __init__(self, conn, addr):

        self.admin = None
        self.current_chat = None
        self.conn = conn
        self.addr = str(addr)

    def get_user_name(self):
        name = receive_msg(self.conn)

        if name and name == ADMIN_NAME:
            self.admin = True
            connections[self.addr] = (self.conn, True)
        elif name:
            users_names[self.addr] = name

    def send_users_list(self):
        if self.admin:
            users = [(str((user_1, user_2)), users_names[user_1] + '<--->' + users_names[user_2]) for user_1, user_2 in chats_histories.keys()
                     if len(chats_histories[(user_1, user_2)]) > 0]
        else:
            users = [(user_addr, user_name) for user_addr, user_name in users_names.items()
                     if user_addr in connections and user_addr != self.addr]

        send_msg(self.conn, str(users))

    def broadcast_msg(self, msg):
        users_list = [(user_addr, user_conn) for user_addr, user_conn in connections.items() if
                      user_addr != self.addr and user_addr in users_names]

        for _, user_conn in users_list:
            send_msg(user_conn, msg)

    def delete_user(self):
        connections.pop(self.addr)

    def handle_new_message(self):
        msg = receive_msg(self.conn)
        admin_conn = [(addr, conn) for addr, conn in connections.items() if type(conn) == tuple]
        if msg:
            chat_history_key = get_chat_history_key(self.addr, self.current_chat)
            chat_prev_len = len(chats_histories[chat_history_key])
            chats_histories[chat_history_key].append((self.addr, msg))

            msg = get_user_html_message(users_names[self.addr], msg)

            if chat_prev_len == 0 and len(chats_histories[chat_history_key]) > 0:
                admin_broadcast(admin_conn, NEW_USER_MESSAGE)
                admin_broadcast(admin_conn, str((chat_history_key, users_names[self.addr] + '<--->' + users_names[self.current_chat])))

            if self.current_chat in connections:
                send_msg(connections[self.current_chat], CHAT_MSG_RECEIVED_MESSAGE)
                send_msg(connections[self.current_chat], str((self.addr, msg)))

            admin_broadcast(admin_conn, CHAT_MSG_RECEIVED_MESSAGE)
            admin_broadcast(admin_conn, str((chat_history_key, msg)))



    def get__html_chat_history(self, chat_history):
        result = HTML_CHAT_MARKUP

        for user, message in chat_history:
            if self.admin or str(user) != self.addr:
                message = get_user_html_message(users_names[user], message)
            else:
                message = get_own_html_message(message)

            result += message

        result += '</body></html>'

        return result

    def handle_chat_change(self):
        new_chat_addr = receive_msg(self.conn)
        self.current_chat = new_chat_addr

        if self.admin:
            chat_history = chats_histories[eval(new_chat_addr)]
        else:
            chat_history_key = get_chat_history_key(self.addr, new_chat_addr)
            if chat_history_key:
                chat_history = chats_histories[chat_history_key]
            else:
                chat_history = []
                chats_histories[(self.addr, new_chat_addr)] = chat_history

        chat_history = self.get__html_chat_history(chat_history)
        send_msg(self.conn, CHAT_HISTORY_MESSAGE)
        send_msg(self.conn, chat_history)

    def handle_client(self):
        print(f"[NEW CONNECTION] {self.addr} connected.")
        new_user = False

        if self.addr not in connections:
            new_user = True

        connections[self.addr] = self.conn
        connected = True

        while connected:
            msg = receive_msg(self.conn)

            if msg:
                if msg == DISCONNECT_MESSAGE:
                    if not self.admin:
                        print(f'[{users_names[self.addr]}] {msg}')
                    self.delete_user()
                    connected = False
                elif msg == NAME_MESSAGE:
                    self.get_user_name()

                    if new_user and not self.admin:
                        self.broadcast_msg(NEW_USER_MESSAGE)
                        self.broadcast_msg(str((self.addr, users_names[self.addr])))
                elif msg == GET_USERS_LIST_MESSAGE:
                    self.send_users_list()
                elif msg == CHAT_CHANGED_MESSAGE:
                    self.handle_chat_change()
                elif msg == CHAT_MSG_MESSAGE:
                    self.handle_new_message()

                if self.addr in users_names:
                    print(f'[{users_names[self.addr]}] {msg}')

        self.conn.close()


def start():
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.bind((HOST, PORT))
    server_sock.listen()
    print(f'[LISTENING] Server is listening on {HOST}')

    while True:
        conn, addr = server_sock.accept()
        server = Server(conn, addr)

        thread = threading.Thread(target=server.handle_client)
        thread.daemon = True
        thread.start()
        print(f"[ACTIVE CONNECTIONS] {threading.active_count() - 1} connected.")


if __name__ == '__main__':
    print("[STARTING] server is starting...")
    start()
