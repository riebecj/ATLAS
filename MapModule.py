import matplotlib.pyplot as plt
from PySide import QtWebKit
from PySide import QtCore
from PySide import QtGui
import numpy as np
import sys
import os

class Map(QtGui.QMainWindow):  	
	def __init__(self, parent):
		super(Map, self).__init__(parent)
		self.initUI()
		self.create_main_frame()
		self.state = True
	
	def initUI(self):
		QtGui.QToolTip.setFont(QtGui.QFont('SansSerif', 10))
		self.setGeometry(300, 300, 250, 150)
		self.showMaximized()
		self.setWindowTitle('ATLAS Map Widget')
		self.setWindowIcon(QtGui.QIcon('ATLAS LOGO.png'))
		
		self.exitAction = QtGui.QAction('Exit', self)
		self.exitAction.triggered.connect(self.closeEvent)
		self.exitAction.setShortcut("Esc")
		
	def create_main_frame(self):
		self.main_frame = QtWebKit.QWebView()
		self.main_frame.load(QtCore.QUrl('file:///C:\ATLAS\_map.html'))	
		self.setCentralWidget(self.main_frame)
	
	def reload(self):
		self.main_frame.load(QtCore.QUrl('file:///C:\ATLAS\_map.html'))
		
	def closeEvent(self, event):
		self.close()
		self.state = False
		event.accept()
	
	def get_state(self):
		return self.state

#app = QtGui.QApplication(sys.argv)
#M = Map(None)
#sys.exit(app.exec_())
