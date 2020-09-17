from PyQt5 import QtWidgets, uic
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import QCursor, QPalette, QFont
from functools import partial

class Labels(QtWidgets.QWidget):

    def __init__(self, LABELS, ui):
        QtWidgets.QWidget.__init__(self)

        self.VertLayout = QtWidgets.QVBoxLayout()
        self.setLayout(self.VertLayout)

        self.ui = ui
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum,
            QtWidgets.QSizePolicy.Minimum
        )
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet('background-color: rgb(44, 44, 46); border-radius: 8px;')

        self.labels = []
        self.frames_collected = []
        self.label_raw_text = LABELS
        self.selected_color = "color: rgb(255, 69, 58)"
        self.default_color = "color: white"
        self.palette = QPalette()
        self.font = QFont()

        self.title = QtWidgets.QLabel('Labeled Data')
        self.title.setStyleSheet(self.default_color)
        self.VertLayout.addWidget(self.title)

        for i in range(0, len(self.label_raw_text)):

            # initialize each label
            curr_label = QtWidgets.QLabel()
            curr_label.setText(str(i))

            # set first label to blue
            if i == 0:
                curr_label.setStyleSheet(self.selected_color)
            else:
                curr_label.setStyleSheet(self.default_color)

            # contextmenu
            curr_label.setContextMenuPolicy(Qt.CustomContextMenu)
            curr_label.customContextMenuRequested.connect(partial(self.rightMenuShow, curr_label))

            # add label to layout
            self.VertLayout.addWidget(curr_label)

            self.labels.append(curr_label)
            self.frames_collected.append(0)

        self.set_label_text()

    def get_current_label_raw_text(self):
        """Returns selected label."""
        for i in range(0, len(self.labels)):
            if self.labels[i].styleSheet() == self.selected_color:
                return self.label_raw_text[i]

    def get_current_label_index(self):
        """Returns index of selected label."""
        for i in range(0, len(self.labels)):
            if self.labels[i].styleSheet() == self.selected_color:
                return i

    def get_current_frames(self):
        """Returns number of frames collected for selected label."""
        for i in range(0, len(self.labels)):
            if self.labels[i].styleSheet() == self.selected_color:
                return self.frames_collected[i]

    def add_frames_current_label(self, num_frames):
        """Adds num_frames to label's frame count."""
        current_index = self.get_current_label_index()

        self.frames_collected[current_index] += num_frames

        # minimum frames collected is 0
        if self.frames_collected[current_index] < 0:
            self.frames_collected[current_index] = 0

        # update label text
        self.set_label_text()

    def set_label_text(self):
        """Set label text to label and frame count."""
        for label, frame_count, label_raw_text in zip(self.labels,
                                                      self.frames_collected,
                                                      self.label_raw_text):

            label_text = "{} ({} frames)".format(label_raw_text, frame_count)
            label.setText(label_text)

    def move_down(self):
        """Moves selected label to one below."""
        curr_ind = self.get_current_label_index()
        if curr_ind < len(self.labels)-1 and curr_ind+1 < len(self.labels):
            # changes colors of labels to highlight the currently selected one
            self.labels[curr_ind].setStyleSheet(self.default_color)
            self.labels[curr_ind+1].setStyleSheet(self.selected_color)

    def move_up(self):
        """Moves selected label to one below."""
        curr_ind = self.get_current_label_index()
        if curr_ind > 0 and curr_ind-1 >= 0:
            # changes colors of labels to highlight the currently selected one
            self.labels[curr_ind].setStyleSheet(self.default_color)
            self.labels[curr_ind-1].setStyleSheet(self.selected_color)

    def rightMenuShow(self, thislabel): 
        menu = QtWidgets.QMenu()
        act_sel = menu.addAction('Select Label')
        act_edit = menu.addAction('Edit Label')
        act_add = menu.addAction('Add Label')
        act_del = menu.addAction('Delete Label')
        index = -1
        action = menu.exec_(QCursor.pos())
        for i in range(len(self.labels)):
            if self.labels[i] == thislabel:
                index = i
                break

        if action == act_sel:
            curr_ind = self.get_current_label_index()
            if curr_ind != index and index >= 0 and index < len(self.labels):
                self.labels[curr_ind].setStyleSheet(self.default_color)
                self.labels[index].setStyleSheet(self.selected_color)
        elif action == act_edit:
            inputDialog = QInputDialog(None)
            inputDialog.setInputMode(QInputDialog.TextInput)
            inputDialog.setWindowTitle('Edit')
            inputDialog.setLabelText('New label name:')
            inputDialog.setPalette(self.palette)
            inputDialog.setFont(self.font)
            okPressed = inputDialog.exec_()
            text = inputDialog.textValue()
            if okPressed and text != '':
                self.label_raw_text[index] = text
                self.set_label_text()
        elif action == act_add:
            curr_label = QtWidgets.QLabel()
            curr_label.setStyleSheet(self.default_color)
            curr_label.setFont(self.font)
            curr_label.setContextMenuPolicy(Qt.CustomContextMenu)
            curr_label.customContextMenuRequested.connect(partial(self.rightMenuShow, curr_label))
            self.VertLayout.addWidget(curr_label)
            self.labels.append(curr_label)
            self.frames_collected.append(0)
            self.label_raw_text.append('default')
            self.set_label_text()
            self.ui.stepsbar.update_label_num(len(self.labels))
            self.ui.stepsbar.update_label_state(self)
        elif action == act_del:
            curr_ind = self.get_current_label_index()
            if curr_ind == index:
                self.ui.footer.setText("Cannot delete selected label!")
            else:
                label_del = self.labels.pop(index)
                self.VertLayout.removeWidget(label_del)
                label_del.setParent(None)
                self.frames_collected.pop(index)
                self.label_raw_text.pop(index)
                self.set_label_text()
                self.ui.stepsbar.update_label_num(len(self.labels))
                self.ui.stepsbar.update_label_state(self)

    def switch_theme(self, palette):
        self.palette = palette
        curr_index = self.get_current_label_index()
        self.title.setStyleSheet(self.default_color)
        for i in range(len(self.labels)):
            if i == curr_index:
                self.labels[i].setStyleSheet(self.selected_color)
            else:
                self.labels[i].setStyleSheet(self.default_color)

    def setFont(self, font):
        self.font = font
        for i in range(len(self.labels)):
            self.labels[i].setFont(font)
        font_bold = QFont(font)
        font_bold.setWeight(99)
        self.title.setFont(font_bold)

    def resizeEvent(self, event):
        self.ui.stepsbar.setFixedWidth(self.ui.width() - 55 - event.size().width())
