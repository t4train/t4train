from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt
import numpy as np

class Steps(QtWidgets.QWidget):

    def __init__(self, label_num, font=QtGui.QFont(), *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_num = label_num
        self.font = font
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Preferred
        )

        self.state = [0] * (3+self.label_num)
        self.pen_width = 4
        self.line_pen = QtGui.QPen(Qt.white, self.pen_width, Qt.SolidLine)
        self.dotline_pen = QtGui.QPen(Qt.white, self.pen_width, Qt.DotLine)
        self.inactive_brush = QtGui.QBrush(QtGui.QColor(10, 10, 10), Qt.SolidPattern)
        self.active_brush = QtGui.QBrush(QtGui.QColor('red'), Qt.SolidPattern)
        self.brushes = [self.inactive_brush, self.active_brush]
        self.pens = [self.dotline_pen, self.line_pen]
        self.circle_diam = 30
        self.line_long = 60
        self.line_short = 10
        self.horizontal_padding = 16
    
    def update_label_num(self, label_num):
        self.label_num = label_num
        self.state = [self.state[0]]
        self.state.extend([0] * (2+self.label_num))
        self.update()

    def paintEvent(self, event):
        # reset sizes
        # line long = width - (channels - 1) * (line_short) - (2 * horizontal_padding)
        # div by 3 since there are 3 long lines
        width = (self.circle_diam+self.pen_width*2)*(3+self.label_num) + self.line_short*(self.label_num-1)
        self.line_long = (self.width() - width - (self.horizontal_padding * 2)) / 3
#        self.line_long = (self.width() - self.padding * 10 - (self.circle_diam + self.line_short) * (self.label_num + 3)) / 4


        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)

        self.base_pos_x = self.horizontal_padding
        self.base_pos_y = self.height() * 0.1
        painter.setPen(self.line_pen)

        def draw_line(len, pen=1):
            painter.setPen(self.pens[pen])
            painter.drawLine(self.base_pos_x, self.base_pos_y + self.circle_diam / 2 + self.pen_width, 
                             self.base_pos_x + len, self.base_pos_y + self.circle_diam / 2 + self.pen_width)
            self.base_pos_x += len

        def draw_circle(state, pen=1):
            painter.setPen(self.pens[pen])
            painter.setBrush(self.brushes[state]) #
            painter.drawEllipse(self.base_pos_x + self.pen_width, self.base_pos_y + self.pen_width, 
                                self.circle_diam, self.circle_diam)
            self.base_pos_x += self.circle_diam + self.pen_width * 2

        def draw_text(text1, text2, isLabel=False, isOptional=False):
            font_metrics = QtGui.QFontMetricsF(self.font)
            painter.setFont(self.font)
            text1_width = font_metrics.width(text1)
            text2_width = font_metrics.width(text2)
            text_height = font_metrics.height()
            mid_x = self.base_pos_x + self.pen_width + self.circle_diam / 2
            if isOptional and text1_width/2+font_metrics.width(' (Optional)') < (self.circle_diam+self.pen_width*2+self.line_long):
                text1 += ' (Optional)'
            if isLabel:
                mid_x = self.base_pos_x + ((self.pen_width*2+self.circle_diam)*self.label_num+self.line_short*(self.label_num-1))/2
            painter.drawText(mid_x - text1_width/2, self.base_pos_y + self.circle_diam + self.pen_width * 2 + self.height() * 0.2, text1)
            painter.drawText(mid_x - text2_width/2, self.base_pos_y + self.circle_diam + self.pen_width * 2 + self.height() * 0.2 + text_height, text2)

        # Load
        draw_text('Load', '(L)', isOptional=True)
        draw_circle(self.state[0], self.state[0])

        draw_line(self.line_long, self.state[0])

        # collect/delete
        draw_text('Collect/Delete', '(Space/BackSpace)', isLabel=True)
        for i in range(self.label_num-1):
            draw_circle(self.state[3+i])
            draw_line(self.line_short)
        draw_circle(self.state[2+self.label_num])

        draw_line(self.line_long)

        # Train
        draw_text('Train','(T)')
        draw_circle(self.state[1])

        draw_line(self.line_long)

        # Save
        draw_text('Save','(S)')
        draw_circle(self.state[2])

        painter.end()


class StepsBar(QtWidgets.QWidget):

    def __init__(self, label_num=1, font=QtGui.QFont(), *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_num = label_num

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Preferred
        )
        self.setMinimumHeight(125)

        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet('background-color: rgb(44, 44, 46); border-radius: 8px;')

        layout = QtWidgets.QVBoxLayout()
        self.steps = Steps(label_num, font)
        layout.addWidget(self.steps)
        self.setLayout(layout)

    def set_state(self, index, state):
        self.steps.state[index] = state
        self.steps.update()

    def update_label_num(self, label_num):
        self.steps.update_label_num(label_num)

    def update_label_state(self, labels):
        self.steps.state[1] = 0
        self.steps.state[2] = 0
        cnt_active = 0
        for i in range(len(labels.labels)):
            if labels.frames_collected[i] > 0:
                cnt_active += 1
        for i in range(cnt_active):
            self.steps.state[3+i] = 1
        for i in range(cnt_active, len(labels.labels)):
            self.steps.state[3+i] = 0
        self.steps.update()
    
    def setFont(self, font):
        self.steps.font = font
        self.steps.update()
