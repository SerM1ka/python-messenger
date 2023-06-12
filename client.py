from PyQt5.QtWidgets import QMainWindow

from admin import AdminWindow
from gui.gui_client import Ui_ClientWindow
from login import Login
from server import DISCONNECT_MESSAGE, GET_USERS_LIST_MESSAGE, NEW_USER_MESSAGE, \
    receive_msg, send_msg, CHAT_CHANGED_MESSAGE, CHAT_HISTORY_MESSAGE, CHAT_MSG_MESSAGE, get_own_html_message, \
    CHAT_MSG_RECEIVED_MESSAGE, ADMIN_NAME

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import QThread, QObject, pyqtSignal as Signal, pyqtSlot as Slot, Qt
import sys


class SocketWorker(QObject):
    users_list_changed = Signal(list)
    clear_input = Signal()
    new_user_in_list = Signal(tuple)
    chat_history_received = Signal(str)
    update_chat_history = Signal(str)
    msg_received = Signal(str)

    def __init__(self, sock):
        super().__init__()
        self.sock = sock

    @Slot()
    def listen_msg(self):
        while True:
            msg = receive_msg(self.sock)

            if msg:
                if msg == NEW_USER_MESSAGE:
                    self.get_new_user()
                elif msg == CHAT_HISTORY_MESSAGE:
                    self.chat_history_received.emit(receive_msg(self.sock))
                elif msg == CHAT_MSG_RECEIVED_MESSAGE:
                    self.msg_received.emit(receive_msg(self.sock))

    def get_new_user(self):
        new_user = eval(receive_msg(self.sock))
        self.new_user_in_list.emit(new_user)

    def get_users_list(self):
        send_msg(self.sock, GET_USERS_LIST_MESSAGE)
        users_list = eval(receive_msg(self.sock))
        self.users_list_changed.emit(users_list)

    # @Slot(str)
    def send_msg_from_input(self, msg, chat):
        if msg and chat:
            send_msg(self.sock, CHAT_MSG_MESSAGE)
            send_msg(self.sock, msg)
            self.clear_input.emit()
            msg = get_own_html_message(msg)
            self.update_chat_history.emit(msg)

    def send_chat_changed(self, addr):
        send_msg(self.sock, CHAT_CHANGED_MESSAGE)
        send_msg(self.sock, addr)


class ClientWindow(QMainWindow):
    listen_server = Signal()
    send_msg_from_input = Signal(str)
    get_users_list = Signal()

    def __init__(self, sock, name):
        super().__init__()
        self.connected = True
        self.sock = sock
        self.name = name
        self.ui_chat = Ui_ClientWindow()
        self.__setup()

    def __setup(self):
        self.ui_chat.setupUi(self)
        self.ui_chat.LoggedAsLabel.setText(f'You logged as {self.name}')
        self.__setup_worker()
        self.worker.get_users_list()
        self.worker_thread.start()
        self.ui_chat.SendButton.clicked.connect(
            lambda: self.worker.send_msg_from_input(self.ui_chat.MessageInput.toPlainText(),
                                                    self.ui_chat.UsersList.currentItem())
        )
        self.ui_chat.UsersList.currentItemChanged.connect(
            lambda: self.worker.send_chat_changed(str(self.ui_chat.UsersList.currentItem().data(QtCore.Qt.UserRole)))
        )

    def __setup_worker(self):
        self.worker = SocketWorker(self.sock)
        self.worker_thread = QThread()
        self.worker.users_list_changed.connect(self.__update_users_list)
        self.worker.new_user_in_list.connect(self.__add_user_to_list)
        self.worker.clear_input.connect(self.__clear_input)
        self.worker.chat_history_received.connect(self.__set_new_chat_history)
        self.worker.update_chat_history.connect(self.__update_chat_history)
        self.worker.msg_received.connect(self.__handle_new_user_msg)

        self.worker_thread.started.connect(self.worker.listen_msg)

        self.worker.moveToThread(self.worker_thread)

    def disconnect_sock(self):
        send_msg(self.sock, DISCONNECT_MESSAGE)

    def __handle_new_user_msg(self, payload):
        user_addr, msg = eval(payload)
        current_user_chat = self.ui_chat.UsersList.currentItem()

        if current_user_chat:
            current_user_chat = current_user_chat.data(QtCore.Qt.UserRole)

            if str(user_addr) == str(current_user_chat):
                self.__update_chat_history(msg)

    def __update_chat_history(self, new_msg):
        chat_area = self.ui_chat.ChatTextarea
        current_chat = chat_area.toHtml()
        end = '</body></html>'
        updated_chat = current_chat[:-len(end)] + new_msg + end
        chat_area.setHtml(updated_chat)
        chat_area.verticalScrollBar().setValue(chat_area.verticalScrollBar().maximum())

    def __set_new_chat_history(self, chat_history):
        chat_area = self.ui_chat.ChatTextarea
        chat_area.setHtml(chat_history)
        chat_area.verticalScrollBar().setValue(chat_area.verticalScrollBar().maximum())

    def __clear_input(self):
        self.ui_chat.MessageInput.clear()

    def __add_user_to_list(self, user):
        user_addr, user_name = user
        ui_users_list = self.ui_chat.UsersList
        item = QtWidgets.QListWidgetItem()
        item.setText(user_name)
        item.setData(QtCore.Qt.UserRole, str(user_addr))
        item.setTextAlignment(Qt.AlignHCenter)
        ui_users_list.addItem(item)

    def __update_users_list(self, users_list):
        ui_users_list = self.ui_chat.UsersList

        for user_addr, user_name in users_list:
            item = QtWidgets.QListWidgetItem()
            item.setText(user_name)
            item.setData(QtCore.Qt.UserRole, str(user_addr))
            item.setTextAlignment(Qt.AlignHCenter)
            ui_users_list.addItem(item)


if __name__ == '__main__':
    login = Login()
    login.start_login()

    if login.connected:
        app = QtWidgets.QApplication(sys.argv)

        if login.name == ADMIN_NAME:
            user = AdminWindow(login.sock, login.name)
        else:
            user = ClientWindow(login.sock, login.name)

        user.show()
        app.aboutToQuit.connect(user.disconnect_sock)
        app.exec()
