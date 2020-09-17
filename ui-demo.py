#!/usr/bin/env python3
# ============================================================================
"""
Detailed but concise file description here
"""
# ============================================================================

# System
import os
import sys
import time
import signal
import subprocess
import configparser
from functools import partial
import psutil

# Data processing
import numpy as np
from shutil import copy

# Qt stuff
from PyQt5         import QtWidgets, uic
from PyQt5         import QtCore, QtGui
from PyQt5.QtCore  import *
from PyQt5.QtGui   import *
from pyqtgraph     import PlotWidget, plot
import pyqtgraph as pg
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QPalette, QColor
from PIL import Image
from ui_assets.ui_labels import Labels
from ui_assets.ui_steps import StepsBar

# Self-define functions
import utils
from functools import partial

#================================================================
# read in configuration
config=configparser.ConfigParser()
config.read('config.ini')

LABELS         =      config['GLOBAL']['LABELS'         ][1:-1].split(', ')
INSTANCES      =  int(config['GLOBAL']['INSTANCES'      ])
CHANNELS       =  int(config['GLOBAL']['CHANNELS'       ])
ALGOS          =      config['GLOBAL']['ALGOS'          ][1:-1].split(', ')
CURR_ALGO_INDEX=  int(config['GLOBAL']['CURR_ALGO_INDEX'])
FRAME_LENGTH   =  int(config['GLOBAL']['FRAME_LENGTH'   ])

DS_HANDLERS    =      config['DS'    ]['DS_HANDLERS'    ][1:-1].split(', ')
DS_FILENAMES   =      config['DS'    ]['DS_FILENAMES'   ][1:-1].split(', ')
DS_FILE_NUM    =  int(config['DS'    ]['DS_FILE_NUM'    ])

SAMPLE_RATE = int(config['DS']['SAMPLE_RATE'])
NUM_BINS = int(config['ML']['NUM_BINS'])

# Get data collection .py filename
ds_filename = DS_FILENAMES[DS_FILE_NUM]
ds_handler = DS_HANDLERS[DS_FILE_NUM]
#================================================================

# Check if OS supports signals
does_support_signals=utils.does_support_signals()

# For Qt
SETUP_TIME = 7 # time for subprocesses to write their pid numbers to file
window = None # hold onto window for interrupts
FPS_COUNTER_RATE = 3  # sec

# For UI style
font_family = 'Verdana'
fontsize_normal = 11
fontsize_maximized = 14

def receive_signal(signum, stack):
	"""Kill ML and data handler if UI is interrupted from its terminal."""
	print('Received UI signal')
	window.closeEvent(event=None)
	sys.exit()

class T4Train(QtWidgets.QMainWindow):
	def __init__(self, ds_filename):
		super(T4Train, self).__init__()
		self.ds_filename = ds_filename
		uic.loadUi("ui_assets/ui_qtview.ui", self)
		self.show()
		
		# delete any existing files from a previous session
		utils.delete_files_ending_in([".npy", ".txt", ".png", ".wav"])


		# start data collection subprocess
		self.ds_subprocess=subprocess.Popen("python "+ds_filename+".py",
											shell=True)

		# start machine learning subprocess
		self.ml_subprocess=subprocess.Popen("python ml.py",
											shell=True)

		# allow wait time for subprocesses to write their pid numbers to file
		time.sleep(SETUP_TIME)

		while True:
			try:
				self.ml_pid = utils.read_pid_num("ml_pidnum.txt")
				break
			except:
				continue

		while True:
			try:
				self.ds_pid = utils.read_pid_num("ds_pidnum.txt")
				break
			except:
				continue

		# set up labels from configurations
		self.labels = Labels(LABELS, self)

		# set up stepsbar
		self.stepsbar = StepsBar(len(self.labels.labels), QFont(font_family, fontsize_normal))

		# Set up FPS counter (frames per second)
		self.num_frames = 0
		self.fps_label = QtWidgets.QLabel()
		self.fps_label.setText("FPS: {}".format(self.num_frames))
		self.setWindowTitle("T for Train - Demo")
		
		# graphs
		self.graphs = []

		# flags
		self.is_predicting = False
		self.model_exists = False

		# feature
		self.feature = utils.Featurization.Raw
		if "Microphone" in ds_handler:
			self.feature = utils.Featurization.FFT
		self.write_featurization()

		# set up message board in bottom right
		self.footer = QtWidgets.QLabel("T4T")
		self.footer.setWordWrap(True)
		self.footer.setFixedWidth(self.width())
		self.footer.setAlignment(Qt.AlignHCenter)

		print("Processes:", self.ml_pid, self.ds_pid, os.getpid())

		self.key = None

		self.build()

	def build(self):
		"""Called after class constructor."""
		self.centralwidget.setContentsMargins(20, 0, 20, 0)
		self.footer.setContentsMargins(0,10,0,0)
		self.fontsize_labels = fontsize_normal
		self.fontsize_footer = fontsize_normal + 8
		self.MainVL.setSpacing(0)
		self.FootGL.setContentsMargins(0, 10, 0, 0)
		if self.ds_filename == "ds_camera":
			self.FootGL.setContentsMargins(0, 0, 0, 0)
			self.footwidget.setContentsMargins(0, 0, 0, 0)

		# featurize plots
		self.feat_plots = []

		# graph titles
		self.signal_titles = []
		self.feature_titles = []

		# contextmenu
		self.topwidget.setContextMenuPolicy(Qt.CustomContextMenu)
		self.topwidget.customContextMenuRequested.connect(self.contextmenu_commands)
		self.footwidget.setContextMenuPolicy(Qt.CustomContextMenu)
		self.footwidget.customContextMenuRequested.connect(self.contextmenu_commands)

		# applicationmenu
		self.add_appmenu()

		# add widgets
		self.TopGL.addWidget(self.stepsbar, 1, 1, alignment=QtCore.Qt.AlignRight)
		self.TopGL.addWidget(self.labels, 1, 1, alignment=QtCore.Qt.AlignLeft)
		self.FootGL.addWidget(self.footer,1, 1, alignment=QtCore.Qt.AlignHCenter)
		self.FootGL.addWidget(self.fps_label, 1, 1, alignment=QtCore.Qt.AlignRight)

		# set graph layouts
		self.Graphs = QtWidgets.QWidget()
		self.FeatGraphs = QtWidgets.QWidget()
		self.CameraFrame = QtWidgets.QWidget()
		self.GraphVL = QtWidgets.QVBoxLayout()
		self.FeatGraphHL = QtWidgets.QHBoxLayout()
		self.CameraFrameVL = QtWidgets.QVBoxLayout()
		self.Graphs.setLayout(self.GraphVL)
		self.FeatGraphs.setLayout(self.FeatGraphHL)
		self.CameraFrame.setLayout(self.CameraFrameVL)

		# update margins
		self.TopGL.setContentsMargins(0, 15, 0, 15)
		self.GraphL.setSpacing(15)
		self.Graphs.setContentsMargins(0, 4, 8, 4)
		self.FeatGraphs.setContentsMargins(0, 4, 8, 4)
		self.GraphVL.setContentsMargins(0, 4, 8, 4)

		# keep track of smallest and largest values encountered on y axis to keep 
		# a y range that doesnt automatically shrink, but also fits all new data
		self.graph_mins = []
		self.graph_maxes = []
		self.feat_mins = []
		self.feat_maxes = []

		# change line thickness
		self.graph_width = []
		self.feat_width = []

		# setup graphs
		pg.setConfigOption('background', (44, 44, 46))
		for i in range(0, CHANNELS):
			graphWidget = pg.PlotWidget()
			graphWidget.setMinimumHeight(0)
			title = QtWidgets.QLabel(self)
			title.setContentsMargins(20,0,0,0)
			title.setFont(QFont(font_family, fontsize_normal))
			title.setText('Channel %d Signal' % (i+1))
			self.signal_titles.append(title)
			graphWidget.disableAutoRange(True)
			graphWidget.setDragMode(0)
			self.graphs.append(graphWidget)
			self.graph_mins.append(0)
			self.graph_maxes.append(0)
			self.graph_width.append(8)

			feat = pg.PlotWidget()
			feat.setMinimumHeight(0)
			title = QtWidgets.QLabel(self)
			title.setContentsMargins(20,0,0,0)
			title.setFont(QFont(font_family, fontsize_normal))
			title.setText('Channel %d Featurization (%s)' % (i+1, self.feature.name))
			self.feature_titles.append(title)
			self.feat_plots.append(feat)
			self.feat_mins.append(0)
			self.feat_maxes.append(0)
			self.feat_width.append(8)

		self.add_line_thickness_menu()

		# add widgets into layouts
		def splitter_horizontal(widget, isGraph):
			splitter = QtWidgets.QSplitter(Qt.Horizontal)
			splitter.setHandleWidth(0)
			splitter.addWidget(QtWidgets.QLabel())
			splitter.addWidget(widget)
			splitter.addWidget(QtWidgets.QLabel())
			splitter.setSizes([1,1,1])
			return splitter

		for i in range(0, CHANNELS):
			self.GraphVL.addWidget(self.signal_titles[i], alignment=QtCore.Qt.AlignLeft)
			self.GraphVL.addWidget(self.graphs[i])

		if self.ds_filename == "ds_camera":
			self.piclabel = QtWidgets.QLabel()
			self.piclabel.setScaledContents(True)
			self.pixmap = QtGui.QPixmap()
			self.splitter = splitter_horizontal(self.piclabel, False)
			self.CameraFrameVL.addWidget(self.splitter)

		for i in range(0, CHANNELS):
			layout = QtWidgets.QVBoxLayout()
			layout.addWidget(self.feature_titles[i], alignment=QtCore.Qt.AlignLeft)
			layout.addWidget(self.feat_plots[i])
			self.FeatGraphHL.addLayout(layout)

		# self.GraphL.addWidget(self.Graphs, CHANNELS)
		self.GraphL.addWidget(self.FeatGraphs, 1)

		if self.ds_filename == "ds_camera":
			self.GraphL.addWidget(self.CameraFrame, 2)

		# setup timer
		self.plot_timer = QtCore.QTimer()
		self.plot_timer.timeout.connect(self.update_points)
		self.plot_timer.start(100)

		self.prediction_timer = QtCore.QTimer()
		self.prediction_timer.timeout.connect(self.update_prediction)
		self.prediction_timer.start(300)

		self.fps_timer = QtCore.QTimer()
		self.fps_timer.timeout.connect(self.update_fps)
		self.fps_timer.start(FPS_COUNTER_RATE * 1000)

		self.pid_timer = QtCore.QTimer()
		self.pid_timer.timeout.connect(self.check_pid_exist)
		self.pid_timer.start(1000)

		# adjust theme colors after all UI is built out
		self.set_theme()

		# warnings for binning
		if 'Microphone' in ds_handler and self.feature == utils.Featurization.FFT:
			if NUM_BINS > (FRAME_LENGTH/2):
				self.error_message('Number of bins is more than half of frame length. '
								   'Change NUM_BINS in config.ini.', 'Warning')
		if 'Camera' not in ds_handler and not (FRAME_LENGTH / NUM_BINS).is_integer():
			self.error_message('Number of bins does not divide evenly into frame length. '
								'Data will be lost. Change NUM_BINS in config.ini.', 'Warning')

	def closeEvent(self, event):
		"""Called on exit."""
		# delete files from current session
		utils.delete_files_ending_in([".npy", ".txt", ".png", ".wav"])

		# Close data collection .py
		try:
			utils.write_cmd_message("ds_cmd.txt", "BYE")

			if does_support_signals:
				os.kill(self.ds_pid, signal.SIGINT)
		except Exception as e:
			print(e)

		# Close machine learning .py
		try:
			utils.write_cmd_message("ml_cmd.txt", "BYE")

			if does_support_signals:
				os.kill(self.ml_pid, signal.SIGINT)
		except Exception as e:
			print(e)

		# Close Qt window
		if event is not None:
			# allow window to close
			event.accept()

	def keyPressEvent(self, event):
		"""Listen and handle keyboard input."""
		should_stop_predicting = True

		# SpaceBar
		if event.key()==QtCore.Qt.Key_Space:
			self.on_spacebar()
			self.stepsbar.update_label_state(self.labels)
		# L
		elif event.key()==QtCore.Qt.Key_L:
			self.stepsbar.set_state(0, 1)
			self.on_load()
		# S
		elif event.key()==QtCore.Qt.Key_S:
			self.stepsbar.set_state(2, 1)
			self.on_save()
		# T
		elif event.key()==QtCore.Qt.Key_T:
			self.stepsbar.set_state(1, 1)
			if not self.is_predicting:
				print("initial train")
				self.on_initial_train()
			else:
				print("retrain with {} featurization".format(self.feature))
				self.on_retrain()
		# I
		elif event.key()==QtCore.Qt.Key_I:
			self.on_feature_importance()
		# M
		elif event.key()==QtCore.Qt.Key_M:
			self.on_ml_algo_toggle()
		# C
		elif event.key()==QtCore.Qt.Key_C:
			self.on_confusion_matrix()
		# BackSpace
		elif event.key()==QtCore.Qt.Key_Backspace:
			self.on_delete_frame()
			self.stepsbar.update_label_state(self.labels)
		# Key Up
		elif event.key()==QtCore.Qt.Key_Up:
			self.on_up()
		# Key Down
		elif event.key()==QtCore.Qt.Key_Down:
			self.on_down()
		# Key Left
		elif event.key()==QtCore.Qt.Key_Left:
			self.on_up()
		# Key Right
		elif event.key()==QtCore.Qt.Key_Right:
			self.on_down()
		#
		else:
			should_stop_predicting = False
			self.footer.setText("Invalid Keyboard Input.")
		
		if should_stop_predicting and event.key() != QtCore.Qt.Key_T:
			# for all other keycodes, stop predicting
			self.stop_predicting()

	def stop_predicting(self):
		"""Stop predicting."""
		self.is_predicting=False
		utils.write_cmd_message("ml_cmd.txt", "STOP PREDICTING")
		if does_support_signals:
			os.kill(self.ml_pid, signal.SIGINT)

	def update_prediction(self, *args):
		"""Write prediction."""
		if self.is_predicting:
			try:
				text_str="Current Prediction: {}".format(np.load('prediction.npy')[0])
				self.footer.setText(text_str)
			except Exception as e:
				return

	def prepare_ml_input_files(self):
		"""Create training_data.npy and training_labels.npy for training."""
		try:
			os.remove("training_labels.npy")
		except OSError:
			pass

		try:
			os.remove("training_data.npy")
		except OSError:
			pass

		training_data_files, labels = utils.get_training_data_files_and_labels(self.labels.label_raw_text)

		utils.write_training_labels(training_data_files,
									labels,
									"training_labels.npy")

		utils.compile_all_training_data(training_data_files, "training_data")

	def update_points(self):
		"""Read current frame and plot points."""
		if self.ds_filename == "ds_camera":
			try:
				imageTest = Image.open('camera.png')
				imageTest.verify()
				self.pixmap = QtGui.QPixmap('camera.png')
				if not self.pixmap.isNull():
					picwidth, picheight = self.piclabel.width(), self.piclabel.height()
					if self.piclabel.height() < 100:
						picwidth ,picheight = 300, 200
					self.piclabel.setPixmap(self.pixmap.scaled(picwidth, picheight, Qt.KeepAspectRatio))
			except Exception as e:
				pass

		try:
			self.curr_frame = np.load('tmpframe.npy').astype(np.float)
			npy_data = self.curr_frame[:, :-2]
		except Exception as e:
			return

		x_linspace=np.linspace(start=0, stop=100, num=len(npy_data[0]))
		xs, ys=[], []
		for i in range(0, CHANNELS):
			for x_element, y_element in zip(x_linspace, npy_data[i]):
				xs.append(float(x_element))
				ys.append(float(y_element))

			y_max = max(ys)
			y_min = min(ys)

			if y_max > self.graph_maxes[i]:
				self.graph_maxes[i] = y_max
			if y_min < self.graph_mins[i]: 
				self.graph_mins[i] = y_min

			self.graphs[i].clear()
			self.graphs[i].setYRange(self.graph_mins[i], self.graph_maxes[i], padding=0.1)
			self.graphs[i].plot(xs, ys, pen = pg.mkPen('w', width = self.graph_width[i]))

			xs, ys = [], []

			# featurize plots
			reframe = utils.featurize(npy_data[i], featurization_type=self.feature, numbins=NUM_BINS, sample_rate=SAMPLE_RATE)

			self.feat_plots[i].clear()

			# special x scale for FFT
			if self.feature == utils.Featurization.FFT:
				newfreqs = np.fft.rfftfreq(npy_data[i].shape[0] // NUM_BINS * NUM_BINS, d=1./SAMPLE_RATE)

				# calculating how data can be binned + dropped index
				binnable_length = (len(newfreqs[1:]) // NUM_BINS * NUM_BINS) + 1

				# drop first entry in `newfreqs` to ignore 0 hz frequency
				newfreqs = np.mean(np.reshape(newfreqs[1:binnable_length], (NUM_BINS, -1)), axis=1)
				self.feat_plots[i].plot(newfreqs, reframe[:, 0], pen = pg.mkPen('y', width=self.feat_width[i]))
			else:
				self.feat_plots[i].plot(range(len(reframe)), reframe[:,0], pen=pg.mkPen('y', width=self.feat_width[i]))

		self.num_frames += 1

	def on_spacebar(self):
		"""Collect frames."""
		global INSTANCES
		self.footer.setText("Writing label to file.")
		utils.write_label(self.labels.get_current_label_raw_text(),
						  "current_label.txt")

		self.footer.setText("Sending message to data source.")

		# send signal to ds.py to collect #instances frames
		utils.write_cmd_message("ds_cmd.txt", "SPACEBAR")

		if does_support_signals:
			os.kill(self.ds_pid, signal.SIGINT)

		self.footer.setText("Collecting "+str(INSTANCES)+" frames.")

		# Frame Checking: Continue only when the npy file saves the
		# collected frames. Prevents app from crashing when user
		# holds down spacebar.
		current_label = self.labels.get_current_label_raw_text()
		current_label = current_label.lower().strip().replace(" ", "_")
		current_training_data_file_name = 'training_data_{}.npy'.format(current_label)

		num_collected = 0
		if os.path.exists(current_training_data_file_name):
			num_collected = np.load(current_training_data_file_name).shape[0]

		# DVS: this is locking ui up, fix?
		# Tried semaphore, link keypress to another routine function at init, still locked
		while True:
			if os.path.exists(current_training_data_file_name):
				try:
					# DVS: What is this? if a==b+1?
					if np.load(current_training_data_file_name). \
							shape[0] == num_collected + 1:
						break
				except Exception as e:
					continue
		self.labels.add_frames_current_label(INSTANCES)

		self.footer.setText("Done Collecting Frames.")

	def on_load(self):
		"""L for Load."""
		global INSTANCES
		if not os.path.exists("saved_files/import/"):
			self.footer.text = "Failed to Load Data. No such path " \
							   "'saved_files/import/'"
		else:
			# copy files into current directory
			for item in os.listdir("saved_files/import/"):
				copy("saved_files/import/%s" % item, os.getcwd())
			self.footer.setText("Copied saved_files/import/ to current dir")

			# get all training data files
			training_data_files, labels = utils.get_training_data_files_and_labels(self.labels.label_raw_text)

			# update frame counts based on loaded files
			for i in range(len(training_data_files)):
				num_frames=np.load(training_data_files[i]).shape[0]
				self.labels.frames_collected[i]=num_frames*INSTANCES

			self.labels.set_label_text()

	def on_save(self):
		"""S for save."""
		self.is_predicting=False

		curr_time=time.strftime("%Y_%m_%d-%H_%M")

		# move training_data_label files to saved_files folder
		if not os.path.exists("saved_files/"):
			os.makedirs("saved_files")

		if not os.path.exists(os.path.join(os.getcwd(), curr_time)):
			os.makedirs(os.path.join("saved_files", curr_time))

		# send signal to ml to save model
		utils.write_cmd_message("ml_cmd.txt", "SAVE, {}".format(curr_time))

		if does_support_signals:
			os.kill(self.ml_pid, signal.SIGINT)

		for item in os.listdir(os.getcwd()):
			if item.startswith('training_data_') and item.endswith('.npy'):
				copy(item, "saved_files/{}/".format(curr_time))

		self.footer.setText("Saved files to saved_files/{}/".format(curr_time))

	def on_initial_train(self):
		"""T for Train."""
		self.footer.setText("Training...")

		# prepare compiled file of training data and training labels
		self.prepare_ml_input_files()

		# send signal to ML to begin training
		utils.write_cmd_message("ml_cmd.txt", "TRAIN")

		if does_support_signals:
			os.kill(self.ml_pid, signal.SIGINT)

		self.is_predicting=True
		self.model_exists =True

	def on_retrain(self):
		"""T for Retrain."""
		self.is_predicting=False
		self.model_exists =False

		self.footer.setText("Retraining...")

		# kill current ml process
		utils.write_cmd_message("ml_cmd.txt", "BYE")

		if does_support_signals:
			os.kill(self.ml_pid, signal.SIGINT)

		# restart ml process
		self.ml_subprocess=subprocess.Popen("python ml.py", shell=True)
		while True:
			try:
				self.ml_pid = utils.read_pid_num("ml_pidnum.txt")
				break
			except:
				continue

		# prepare compiled file of training data and training labels
		self.prepare_ml_input_files()

		utils.write_cmd_message("ml_cmd.txt", "TRAIN")

		if does_support_signals:
			os.kill(self.ml_pid, signal.SIGINT)

		self.is_predicting=True
		self.model_exists =True

	def on_feature_importance(self):
		"""I for feature importance."""
		self.prepare_ml_input_files()
		utils.write_cmd_message("ml_cmd.txt", "FEATURE_IMPORTANCE")
		if does_support_signals:
			os.kill(self.ml_pid, signal.SIGINT)
		self.footer.setText("Feature Importances written to feature_"
							"importances.csv")

	def on_ml_algo_toggle(self):
		"""M for ML algorithm toggle."""
		global ALGOS, CURR_ALGO_INDEX
		CURR_ALGO_INDEX = utils.increment_algo_ind(CURR_ALGO_INDEX, ALGOS)
		utils.write_cmd_message("ml_cmd.txt", "TOGGLE_ALGO_" + str(CURR_ALGO_INDEX))
		if does_support_signals:
			os.kill(self.ml_pid, signal.SIGINT)
		self.footer.setText("Machine Learning Algorithm Switched to %s" %
							ALGOS[CURR_ALGO_INDEX])

	def on_confusion_matrix(self):
		"""C for confusion matrix."""
		# prepare compiled file of training data and training labels
		self.prepare_ml_input_files()
		utils.write_cmd_message("ml_cmd.txt", "CONFUSION")
		if does_support_signals:
			os.kill(self.ml_pid, signal.SIGINT)
		self.footer.setText("Confusion matrix written to file.")

	def on_delete_frame(self):
		"""Backspace for delete frame."""
		# get current training data file name
		current_label=self.labels.get_current_label_raw_text().lower(). \
			strip().replace(" ", "_")
		current_training_data_file_name='training_data_{}.npy'. \
			format(current_label)

		# delete frame from selected label
		if os.path.exists(current_training_data_file_name):
			current_frames=np.load(current_training_data_file_name)
			current_frames=current_frames[:-1]
			np.save(current_training_data_file_name, current_frames)

		# decrement frame count on UI
		self.labels.add_frames_current_label(-INSTANCES)

		# update UI frame count
		self.labels.set_label_text()

	def on_down(self):
		self.labels.move_down()

	def on_up(self):
		self.labels.move_up()

	def update_fps(self, *args):
		"""Update FPS label."""
		fps=int(self.num_frames/FPS_COUNTER_RATE)
		self.fps_label.setText("FPS: {}".format(fps))
		self.num_frames = 0

	def contextmenu_commands(self):
		"""set up context menu"""
		menu = QtWidgets.QMenu()
		menu_commands = QtWidgets.QMenu('Commands')
		menu.addMenu(menu_commands)
		act_L = menu_commands.addAction('Load [L]')
		act_Space = menu_commands.addAction('Collect [Space]')
		act_Backspace = menu_commands.addAction('Delete [Backspace]')
		act_T = menu_commands.addAction('Train [T]')
		act_S = menu_commands.addAction('Save [S]')
		act_I = menu_commands.addAction('Feature Importance [I]')
		act_C = menu_commands.addAction('Confusion Matrix [C]')
		action = menu.exec_(QCursor.pos())
		key = None
		if action == act_L:
			key = QtCore.Qt.Key_L
		elif action == act_Space:
			key = QtCore.Qt.Key_Space
		elif action == act_Backspace:
			key = QtCore.Qt.Key_Backspace
		elif action == act_T:
			key = QtCore.Qt.Key_T
		elif action == act_S:
			key = QtCore.Qt.Key_S
		elif action == act_I:
			key = QtCore.Qt.Key_I
		elif action == act_C:
			key = QtCore.Qt.Key_C
		if key != None:
			event = QKeyEvent(QtCore.QEvent.KeyPress, key, QtCore.Qt.ControlModifier)
			self.keyPressEvent(event)

	def add_line_thickness_menu(self):
		"""add line thickness into context menu"""
		def line_thickness_change(width_list, index, value):
			width_list[index] = value

		def new_slider_thickness():
			slider = QtWidgets.QSlider(Qt.Horizontal)
			slider.setFixedSize(150,32)
			slider.setMinimum(1)
			slider.setMaximum(10)
			slider.setSingleStep(1)
			return slider

		for i in range(CHANNELS):
			menu_line_thickness = self.graphs[i].getPlotItem().ctrlMenu.addMenu('Line Thickness')
			act = QtGui.QWidgetAction(menu_line_thickness)
			slider_graph = new_slider_thickness()
			slider_graph.setValue(self.graph_width[i])
			slider_graph.valueChanged.connect(partial(line_thickness_change, self.graph_width, i))
			act.setDefaultWidget(slider_graph)
			menu_line_thickness.addAction(act)

			menu_line_thickness = self.feat_plots[i].getPlotItem().ctrlMenu.addMenu('Line Thickness')
			act = QtGui.QWidgetAction(menu_line_thickness)
			slider_graph = new_slider_thickness()
			slider_graph.setValue(self.feat_width[i])
			slider_graph.valueChanged.connect(partial(line_thickness_change, self.feat_width, i))
			act.setDefaultWidget(slider_graph)
			menu_line_thickness.addAction(act)

	def add_appmenu(self):
		"""set up application menu"""
		# File
		act_quit = self.menuFile.addAction('Quit')
		def fake_quit():
			self.error_message('Are you sure you want to quit?', 'Warning')
		act_quit.triggered.connect(fake_quit)

		# Algorithm
		def switch_algo(act_algo):
			global CURR_ALGO_INDEX, ALGOS
			index = ALGOS.index(str(act_algo.text()))
			# only change algorithm if different
			if index != CURR_ALGO_INDEX:
				CURR_ALGO_INDEX = index

				# send algo change message to ml
				utils.write_cmd_message("ml_cmd.txt", "TOGGLE_ALGO_" + str(CURR_ALGO_INDEX))
				if does_support_signals:
					os.kill(self.ml_pid, signal.SIGINT)

			self.footer.setText("Machine Learning Algorithm Switched to %s" % \
					ALGOS[CURR_ALGO_INDEX])

		group = QtWidgets.QActionGroup(self.menuAlgo)
		global CURR_ALGO_INDEX, ALGOS
		for index in range(len(ALGOS)):
			act = QtWidgets.QAction(ALGOS[index], self, checkable=True, checked=(index==CURR_ALGO_INDEX))
			self.menuAlgo.addAction(act)
			group.addAction(act)
		group.setExclusive(True)
		group.triggered.connect(switch_algo)

		# User Interface
		# set fontsize
		def labels_change(value):
			self.fontsize_labels = value
			font = QFont(font_family, value)
			self.labels.setFont(font)
			self.fps_label.setFont(font)
			self.stepsbar.setFont(font)
			for i in range(CHANNELS):
				self.signal_titles[i].setFont(font)
				self.feature_titles[i].setFont(font)
		def footer_change(value):
			self.fontsize_footer = value
			self.footer.setFont(QFont(font_family, value))

		def get_slider(value=fontsize_normal, maximum=20, minimum=5):
			slider = QtWidgets.QSlider(Qt.Horizontal)
			slider.setStyleSheet('background-color: rgb(30, 30, 30); padding: 5px')
			slider.setFixedSize(150,32)
			slider.setMinimum(minimum)
			slider.setMaximum(maximum)
			slider.setSingleStep(1)
			slider.setValue(value)
			return slider

		self.menu_fontsize = self.menuUser.addMenu('Font Size')

		self.font_labels = self.menu_fontsize.addMenu('Labels')
		slider = get_slider(self.fontsize_labels)
		slider.valueChanged.connect(labels_change)
		act = QtGui.QWidgetAction(self.menu_fontsize)
		act.setDefaultWidget(slider)
		self.font_labels.addAction(act)

		self.font_footer = self.menu_fontsize.addMenu('Footer')
		slider = get_slider(self.fontsize_footer, maximum=85)
		slider.valueChanged.connect(footer_change)
		act = QtGui.QWidgetAction(self.menu_fontsize)
		act.setDefaultWidget(slider)
		self.font_footer.addAction(act)

		# set line thickness
		def thickness_change(value):
			for i in range(CHANNELS):
				self.graph_width[i] = value
				self.feat_width[i] = value

		self.menu_line_thickness = self.menuUser.addMenu('Line Thickness')
		slider = get_slider(value=5, minimum=1, maximum=10)
		slider.valueChanged.connect(thickness_change)
		act = QtGui.QWidgetAction(self.menu_line_thickness)
		act.setDefaultWidget(slider)
		self.menu_line_thickness.addAction(act)


		# hide stepsbar
		act = QtWidgets.QAction('Show Status Bar', self, checkable=True)
		act.setChecked(True)
		act.toggled.connect(self.show_stepsbar)
		self.menuUser.addAction(act)

		# Featurization
		group = QtWidgets.QActionGroup(self.menuFeat)
		feat_list = [feat.value for feat in utils.Featurization]

		if "Microphone" in ds_handler:
			feat_list = [utils.Featurization.Raw.value, utils.Featurization.FFT.value]
		elif "Camera" in ds_handler:
			feat_list = [utils.Featurization.Raw.value, utils.Featurization.Delta.value]

		default_index = 0
		if "Microphone" in ds_handler:
			default_index = 1

		for feat in feat_list:
			act = QtWidgets.QAction(feat, self, checkable=True, checked=(feat==feat_list[default_index]))
			self.menuFeat.addAction(act)
			group.addAction(act)
		group.setExclusive(True)
		group.triggered.connect(self.toggle_feat)

	def write_featurization(self):
		try: 
			with open("feat.txt", "w") as f:
				f.write(self.feature.value)
		except Exception as e:
			print("unable to write featurization file")

	def toggle_feat(self, act_feat):
		self.feature = utils.Featurization(str(act_feat.text()))
		# write to featurization command file
		self.write_featurization()
		if self.feature == utils.Featurization.FFT:
			if NUM_BINS > (FRAME_LENGTH/2):
				self.error_message('Number of bins is more than half of frame length. '
									    'Change NUM_BINS in config.ini.', 'Warning')
			if not ((FRAME_LENGTH/2)/NUM_BINS).is_integer():
				self.error_message('Number of bins does not divide evenly into frame length/2 for FFT. '
										'Data will be lost. Change NUM_BINS in config.ini.', 'Warning')

		self.footer.setText("Featurization switched to %s" % act_feat.text())
		for i in range(CHANNELS):
			self.feature_titles[i].setText('Channel %d Featurization (%s)' % (i+1, self.feature.name))

	def show_stepsbar(self, show):
		self.TopGL.removeWidget(self.labels)
		self.labels.setParent(None)
		self.TopGL.removeWidget(self.stepsbar)
		self.stepsbar.setParent(None)
		if show:
			self.TopGL.addWidget(self.stepsbar, 1, 1, alignment=QtCore.Qt.AlignRight)
			self.TopGL.addWidget(self.labels, 1, 1, alignment=QtCore.Qt.AlignLeft)
		else:
			self.TopGL.addWidget(self.labels, 1, 1, alignment=QtCore.Qt.AlignHCenter)

	def set_theme(self):
		palette = QPalette()
		palette.setColor(QPalette.Window, QColor(10, 10, 10))
		palette.setColor(QPalette.WindowText, Qt.white)
		palette.setColor(QPalette.Base, Qt.black)
		palette.setColor(QPalette.AlternateBase, Qt.gray)
		palette.setColor(QPalette.ToolTipBase, Qt.white)
		palette.setColor(QPalette.ToolTipText, Qt.white)
		palette.setColor(QPalette.Text, Qt.white)
		palette.setColor(QPalette.Button, Qt.black)
		palette.setColor(QPalette.Background, QColor(28, 28, 30))
		palette.setColor(QPalette.ButtonText, Qt.white)
		palette.setColor(QPalette.BrightText, Qt.red)
		palette.setColor(QPalette.Link, QColor(42, 130, 218))
		palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
		palette.setColor(QPalette.HighlightedText, Qt.black)
		self.setPalette(palette)
		palette.setColor(QPalette.Base, QColor(28, 28, 30))
		self.menubar.setPalette(palette)
		self.menuFile.setPalette(palette)
		self.menuAlgo.setPalette(palette)
		self.menuUser.setPalette(palette)
		self.menuFeat.setPalette(palette)
		self.menu_fontsize.setPalette(palette)
		self.labels.switch_theme(palette)

		board_stylesheet = 'background-color: rgb(44, 44, 46); border-radius: 8px'
		self.Graphs.setAttribute(QtCore.Qt.WA_StyledBackground, True)
		self.Graphs.setStyleSheet(board_stylesheet)
		self.FeatGraphs.setAttribute(QtCore.Qt.WA_StyledBackground, True)
		self.FeatGraphs.setStyleSheet(board_stylesheet)
		for graphWidget in self.graphs:
			graphWidget.setBackground((44, 44, 46))
		for feat in self.feat_plots:
			feat.setBackground((44, 44, 46))
		for i in range(CHANNELS):
			self.signal_titles[i].setStyleSheet("color: white; font: bold")
			self.feature_titles[i].setStyleSheet("color: white; font: bold")
	
	def set_all_fonts(self, fontsize):
		self.fontsize_labels = fontsize
		self.fontsize_footer = 85
		self.labels.setFont(QFont(font_family, self.fontsize_labels))
		self.fps_label.setFont(QFont(font_family, self.fontsize_labels))
		self.stepsbar.setFont(QFont(font_family, self.fontsize_labels))
		self.footer.setFont(QFont(font_family, self.fontsize_footer))
		for i in range(CHANNELS):
			self.signal_titles[i].setFont(QFont(font_family, self.fontsize_labels))
			self.feature_titles[i].setFont(QFont(font_family, self.fontsize_labels))

	def changeEvent(self, event):
		if event.type() == QEvent.WindowStateChange:
			if self.isMaximized() or self.isFullScreen():
				self.set_all_fonts(fontsize_maximized)
			else:
				self.set_all_fonts(fontsize_normal)
			if self.ds_filename == "ds_camera":
				self.piclabel.setPixmap(self.pixmap.scaled(300, 200, Qt.KeepAspectRatio))
			self.footer.setFixedWidth(self.width())

	def resizeEvent(self, event):
		if 'stepsbar' in self.__dict__:
			self.stepsbar.setFixedWidth(self.width() - 55 - self.labels.width())
		if 'footer' in self.__dict__:
			self.footer.setFixedWidth(self.width())
		if self.ds_filename == "ds_camera" and 'piclabel' in self.__dict__:
			self.piclabel.setPixmap(self.pixmap.scaled(300, 200, Qt.KeepAspectRatio))

	def error_message(self, message, title='Error'):
		reply = QMessageBox.warning(self, title, message, QMessageBox.Ok|QMessageBox.Ignore, QMessageBox.Ok)
		if reply == QMessageBox.Ok:
			self.closeEvent(QCloseEvent())
			quit()

	def check_pid_exist(self):
		"""check if process ml and ds still alive"""
		if not psutil.pid_exists(self.ml_pid) or not psutil.pid_exists(self.ds_pid):
			self.error_message('Process ml.py or ds.py is dead. Please restart.')

if __name__ == "__main__":
	# Check if OS supports signals
	if does_support_signals:
		signal.signal(signal.SIGINT, receive_signal)

	app = QtWidgets.QApplication(sys.argv)    
	window = T4Train(ds_filename)

	# Force the style to be the same on all OSs:
	app.setStyle("Fusion")
	app.setFont(QFont(font_family, fontsize_normal))
	window.set_all_fonts(fontsize_maximized)

app.exec_()
print("Closing from UI")
quit()
