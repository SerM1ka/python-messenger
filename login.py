import socket

from server import HOST, PORT, NAME_MESSAGE, send_msg
from gui.gui_login import Ui_LoginWindow
from PyQt5 import QtWidgets
import sys


class Login:
    def __init__(self):
        self.connected = False
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.ui_login = Ui_LoginWindow(HOST, PORT)
        self.app = QtWidgets.QApplication(sys.argv)
        self.LoginWindow = QtWidgets.QMainWindow()

    def __try_socket_connect(self, host, name):
        try:
            ip, port = host.split(':')
            self.sock.connect((ip, int(port)))
            send_msg(self.sock, NAME_MESSAGE)
            send_msg(self.sock, name)
            self.name = name
            self.connected = True
        except:
            self.connected = False

    def __close_login(self):
        self.LoginWindow.close()

    def __try_login(self):
        host = self.ui_login.IPInput.text()
        name = self.ui_login.NameInput.text()

        if not host:
            self.ui_login.label.setText('Please provide host (IP:PORT)')
        elif not name:
            self.ui_login.label_2.setText('Please provide your nickname')
        else:
            self.__try_socket_connect(host, name)
            if self.connected:
                self.__close_login()
            else:
                self.ui_login.label.setText('Unable to connect')

    def start_login(self):
        self.ui_login.setupUi(self.LoginWindow)
        self.ui_login.CancelButton.clicked.connect(self.__close_login)
        self.ui_login.OKButton.clicked.connect(self.__try_login)
        self.LoginWindow.show()
        self.app.exec()
