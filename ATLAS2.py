from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.widgets import LassoSelector
from matplotlib.figure import Figure
from multiprocessing import Queue
from matplotlib.path import Path
import matplotlib.pyplot as plt

from pylab import *

from ATLASTileHandler import MainHandler, MbtilesHandler
import InitializeMission, ellipseConvolver, MapModule, sysCalls

from PySide.QtCore import *
from PySide.QtGui import *
from PySide import QtCore, QtGui

import tornado.ioloop, tornado.web

import getpass, pandas, ctypes, sys, os, FileDialog, logging

try:
	from PySide.QtCore import QString
except ImportError:	
	QtCore.QString = str

'''
def errorLogConfig():
	if os.path.isfile("log.log"):
		with open('log.log', 'w') as outfile:
				outfile.seek(0)
				outfile.truncate()

	logger = logging.getLogger()
	logging.basicConfig(filename="C:\\ATLAS\\log.log", level=logging.DEBUG)
	def my_handler(type, value, tb):
		logger.exception("Uncaught exception: {0}".format(str(value)))
		
	ch = logging.StreamHandler(sys.stdout)
	ch.setLevel(logging.DEBUG)
	formatter = logging.Formatter("%(asctime)s - %(name)s - %(level)s - %(message)s")
	ch.setFormatter(formatter)
	logger.addHandler(ch)
	
	sys.excepthook = my_handler
'''

class _TileServer(QThread):
	def __init__(self):
		super(_TileServer, self).__init__()
		self.urls = self.setup()
	
	def setup(self):
		urls = [(r"/", MainHandler),]
		thisdir = "C:/ATLAS/"
		tilesets = [
			('map', os.path.join(thisdir, 'tiles.mbtiles'), ['png','json'],),
		]

		for t in tilesets:
			for ext in t[2]:
				urls.append(
					(r'/%s/([0-9]+)/([0-9]+)/([0-9]+).%s' % (t[0],ext), 
						MbtilesHandler, 
						{"ext": ext, "mbtiles": t[1]}
					)
				)
		return urls
		
	def run(self):
		self.startServer(self.urls)
		
	def startServer(self, urls):
		application = tornado.web.Application(urls, debug=True)
		application.listen(8988)
		tornado.ioloop.IOLoop.instance().start()

	def stopServer(self):
		io_loop = tornado.ioloop.IOLoop.instance()
		io_loop.add_callback(lambda x: x.stop(), io_loop)

		
class FileDialog(QtGui.QWidget):
	def __init__(self, parent=None):
		super(FileDialog, self).__init__(parent)
		self.username = getpass.getuser()
		self.path = "C:\\Users\\"+self.username+"\\Desktop"
	
	def open(self):
		self.filename = self.filepick()
		
	def filepick(self):	
		self.options = QtGui.QFileDialog.Options()
		
		self.filename, self.filtr = QtGui.QFileDialog.getOpenFileNames(self,
				"Open ATLAS Mission Data File", self.path,
				"Mission File (*.mdb;*.accdb);;All Files (*.*)", "", self.options)
		
		if self.filename != []:
			self.filename = str(self.filename)
			dirpath = os.path.dirname(self.filename)
			self.filename = self.filename[3:-2]
			self.path = dirpath[3:]
			return self.filename
		else:
			return	
			
	def get_name(self):
		return self.filename

		
class FilterWidget(QtGui.QFrame):
    def sizeHint(self):
        return QtCore.QSize(275, 462)	

		
class AuxWindow(QtGui.QMainWindow):
	def __init__(self, parent):
		super(AuxWindow, self).__init__(parent)

		self.mdiArea = QtGui.QMdiArea()
		self.mdiArea.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
		self.mdiArea.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
		self.setCentralWidget(self.mdiArea)
		
		self.windowMapper = QtCore.QSignalMapper(self)
		self.windowMapper.mapped.connect(self.setActiveSubWindow)
		self.state = True
		self.createActions()
		self.createMenus()
		self.createToolBars()
		self.createStatusBar()

		self.setWindowTitle("Auxiliary Plotting Widget")
		self.setUnifiedTitleAndToolBarOnMac(True)
		self.setWindowIcon(QtGui.QIcon('ATLAS LOGO.png'))
		
		self.exitAction = QtGui.QAction('Exit', self)
		self.exitAction.triggered.connect(self.closeEvent)
		self.exitAction.setShortcut("Esc")
		
	def get_state(self):
		return self.state
			
	def redraw_sub(self):
		for window in self.mdiArea.subWindowList():
			window.widget().update_params()
			window.widget().update_bins()	

	def closeEvent(self, event):
		self.close()
		self.state = False
		event.accept()
		
	def hfreq(self):
		child = self.createMdiChild("hfreq")
		child.show()

	def hpri(self):
		child = self.createMdiChild("hpri")
		child.show()
		
	def hpw(self):
		child = self.createMdiChild("hpw")
		child.show()
		
	def fvpri(self):
		child = self.createMdiChild("fvpri")
		child.show()
		
	def fvpw(self):
		child = self.createMdiChild("fvpw")
		child.show()
		
	def privpw(self):
		child = self.createMdiChild("privpw")
		child.show()

	def updateWindowMenu(self):
		self.windowMenu.clear()
		self.windowMenu.addAction(self.closeAllAct)
		self.windowMenu.addSeparator()
		self.windowMenu.addAction(self.tileAct)
		self.windowMenu.addAction(self.cascadeAct)
		self.windowMenu.addSeparator()
		self.windowMenu.addAction(self.nextAct)
		self.windowMenu.addAction(self.previousAct)

		windows = self.mdiArea.subWindowList()
		self.separatorAct.setVisible(len(windows) != 0)

	def createMdiChild(self, name):
		child = MdiChild(name)
		self.mdiArea.addSubWindow(child)
		return child

	def createActions(self):
		self.hfreqAct = QtGui.QAction(QtGui.QIcon('FH.png'), 'Freguency Histogram', self)
		self.hfreqAct.triggered.connect(self.hfreq)
		
		self.hpriAct = QtGui.QAction(QtGui.QIcon('PRH.png'), 'PRI Histogram', self)
		self.hpriAct.triggered.connect(self.hpri)
		
		self.hpwAct = QtGui.QAction(QtGui.QIcon('PWH.png'), 'PW Histogram', self)
		self.hpwAct.triggered.connect(self.hpw)
		
		self.fvpriAct = QtGui.QAction("FREQ v PRI", self, statusTip="Frequency v PRI Scattergram")
		self.fvpriAct.triggered.connect(self.fvpri)
		
		self.fvpwAct = QtGui.QAction("FREQ v PW", self, statusTip="Frequency v PW Scattergram")
		self.fvpwAct.triggered.connect(self.fvpw)
		
		self.privpwAct = QtGui.QAction("PRI v PW", self, statusTip="PRI v PW Scattergram")
		self.privpwAct.triggered.connect(self.privpw)

		self.exitAct = QtGui.QAction("E&xit", self, shortcut="Ctrl+Q",
				statusTip="Exit the application",
				triggered=self.close)

		self.closeAllAct = QtGui.QAction("Close &All", self,
				statusTip="Close all the windows",
				triggered=self.mdiArea.closeAllSubWindows)

		self.tileAct = QtGui.QAction("&Tile", self,
				statusTip="Tile the windows",
				triggered=self.mdiArea.tileSubWindows)

		self.cascadeAct = QtGui.QAction("&Cascade", self,
				statusTip="Cascade the windows",
				triggered=self.mdiArea.cascadeSubWindows)

		self.nextAct = QtGui.QAction("Ne&xt", self,
				shortcut=QtGui.QKeySequence.NextChild,
				statusTip="Move the focus to the next window",
				triggered=self.mdiArea.activateNextSubWindow)

		self.previousAct = QtGui.QAction("Pre&vious", self,
				shortcut=QtGui.QKeySequence.PreviousChild,
				statusTip="Move the focus to the previous window",
				triggered=self.mdiArea.activatePreviousSubWindow)

		self.separatorAct = QtGui.QAction(self)
		self.separatorAct.setSeparator(True)
		
	def createMenus(self):
		self.fileMenu = self.menuBar().addMenu("&File")
		action = self.fileMenu.addAction("Switch layout direction")
		action.triggered.connect(self.switchLayoutDirection)
		self.fileMenu.addSeparator()
		self.fileMenu.addAction(self.exitAct)

		self.editMenu = self.menuBar().addMenu("&Plots")
		self.editMenu.addAction(self.hfreqAct)		
		self.editMenu.addAction(self.hpriAct)	
		self.editMenu.addAction(self.hpwAct)	
		self.editMenu.addSeparator()
		self.editMenu.addAction(self.fvpriAct)
		self.editMenu.addAction(self.fvpwAct)
		self.editMenu.addAction(self.privpwAct)

		self.windowMenu = self.menuBar().addMenu("&Windows")
		self.updateWindowMenu()
		self.windowMenu.aboutToShow.connect(self.updateWindowMenu)

	def createToolBars(self):
		self.fileToolBar = self.addToolBar("Plots")
		self.fileToolBar.addAction(self.hfreqAct)	
		self.fileToolBar.addAction(self.hpriAct)
		self.fileToolBar.addAction(self.hpwAct)
		self.fileToolBar.addSeparator()
		self.fileToolBar.addAction(self.fvpriAct)
		self.fileToolBar.addSeparator()
		self.fileToolBar.addAction(self.fvpwAct)
		self.fileToolBar.addSeparator()
		self.fileToolBar.addAction(self.privpwAct)

	def createStatusBar(self):
		self.statusBar().showMessage("Ready")

	def activeMdiChild(self):
		activeSubWindow = self.mdiArea.activeSubWindow()
		if activeSubWindow:
			return activeSubWindow.widget()
		return None

	def findMdiChild(self, fileName):
		canonicalFilePath = QtCore.QFileInfo(fileName).canonicalFilePath()

		for window in self.mdiArea.subWindowList():
			if window.widget().currentFile() == canonicalFilePath:
				return window
		return None

	def switchLayoutDirection(self):
		if self.layoutDirection() == QtCore.Qt.LeftToRight:
			self.setLayoutDirection(QtCore.Qt.RightToLeft)
		else:
			self.setLayoutDirection(QtCore.Qt.LeftToRight)

	def setActiveSubWindow(self, window):
		if window:
			self.mdiArea.setActiveSubWindow(window)

			
class MdiChild(QtGui.QMainWindow):

	def __init__(self, type):
		super(MdiChild, self).__init__()
		
		self.type = type
		self.bins = 100
		self.freq, self.pri, self.pw = root.return_child_values()
		self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
		self.create_main_frame()
		self.on_draw()
		self.show()
	
	def update_params(self):
		self.freq, self.pri, self.pw = root.return_child_values()
	
	def setWindowName(self):
		if self.type == 'hfreq':
			self.setWindowTitle('Frequency Histogram')
				
		elif self.type == 'hpri':
			self.setWindowTitle('Pulse Repetition Interval (PRI) Histogram')
				
		elif self.type == 'hpw':
			self.setWindowTitle('Pulse Width (PW) Histogram')
				
		elif self.type == 'fvpri':
			self.setWindowTitle('Frequency VS Pulse Repetition Interval (PRI)')
				
		elif self.type == 'fvpw':
			self.setWindowTitle('Frequency VS Pulse Width (PW)')
				
		elif self.type == 'privpw':
			self.setWindowTitle('Pulse Repetition Interval (PRI) VS Pulse Width (PW)')

	def create_main_frame(self):
		self.main_frame = QWidget()
		
		self.setWindowName()
		
		self.fig = Figure((5.0, 4.0), dpi=100)
		self.canvas = FigureCanvas(self.fig)
		self.canvas.setParent(self.main_frame)
		self.canvas.setFocus()
		
		self.mpl_toolbar = NavigationToolbar(self.canvas, self.main_frame)

		self.canvas.mpl_connect('key_press_event', self.on_key_press)
		
		self.binSlider = QSlider(Qt.Vertical)
		self.binSlider.setMinimum(100)
		self.binSlider.setMaximum(2000)
		self.binSlider.setValue(100)
		self.binSlider.setTickPosition(QSlider.TicksBothSides)
		self.binSlider.setTickInterval(100)
		self.binSlider.valueChanged.connect(self.updateEntry)
		self.binSlider.sliderReleased.connect(self.update_bins)
		
		self.Entry = QLineEdit('100')
		self.Entry.setFixedWidth(35)
		self.Entry.returnPressed.connect(self.moveSlider)
		
		slider = QVBoxLayout()
		slider.addWidget(self.binSlider)
		slider.addWidget(self.Entry)
		
		vbox = QVBoxLayout()
		hbox = QHBoxLayout()
		
		hbox.addLayout(slider)
		hbox.addWidget(self.canvas)

		vbox.addLayout(hbox)
		vbox.addWidget(self.mpl_toolbar)
		self.main_frame.setLayout(vbox)
		self.setCentralWidget(self.main_frame)
	
	def moveSlider(self):
		val = int(self.Entry.text())
		self.binSlider.setValue(val)
		self.update_bins()
	
	def updateEntry(self):
		val = str(self.binSlider.value())
		self.Entry.setText(val)
		
	def on_draw(self):
		if self.type == 'hfreq':
			def plot(self):
				#self.ymin, self.ymax = self.getAxisLim(self.freq)
				#self.ymin = self.ymin - 5
				#self.ymax = self.ymax + 5
				self.axes.hist(self.freq, bins=self.bins)
				self.axes.set_xlabel("FREQ (MHz)")
				
		elif self.type == 'hpri':
			def plot(self):
				#self.ymin, self.ymax = self.getAxisLim(self.pri)
				#self.ymin = self.ymin - 5
				#self.ymax = self.ymax + 5
				self.axes.hist(self.pri, bins=self.bins)
				self.axes.set_xlabel("PRI (usec)")
				
		elif self.type == 'hpw':
			def plot(self):
				#self.ymin, self.ymax = self.getAxisLim(self.pw)
				#self.ymin = self.ymin - 2
				#self.ymax = self.ymax + 2
				self.axes.hist(self.pw, bins=self.bins)
				self.axes.set_xlabel("PW (usec)")
				
		elif self.type == 'fvpri':
			def plot(self):
				self.axes.scatter(self.pri, self.freq)
				
		elif self.type == 'fvpw':
			def plot(self):
				self.axes.scatter(self.pw, self.freq)
				
		elif self.type == 'privpw':
			def plot(self):
				self.axes.scatter(self.pri, self.pw)
		
		self.fig.clear()
		self.axes = self.fig.add_subplot(111)
		plot(self)
		self.canvas.draw()

	def update_bins(self):
		self.bins = int(self.Entry.text())
		self.on_draw()
		
	def on_key_press(self, event):
		key_press_handler(event, self.canvas, self.mpl_toolbar)


class SelectFromCollection(object):
    """Select indices from a matplotlib collection using `LassoSelector`.

    Selected indices are saved in the `ind` attribute. This tool highlights
    selected points by fading them out (i.e., reducing their alpha values).
    If your collection has alpha < 1, this tool will permanently alter them.

    Note that this tool selects collection objects based on their *origins*
    (i.e., `offsets`).

    Parameters
    ----------
    ax : :class:`~matplotlib.axes.Axes`
        Axes to interact with.

    collection : :class:`matplotlib.collections.Collection` subclass
        Collection you want to select from.

    alpha_other : 0 <= float <= 1
        To highlight a selection, this tool sets all selected points to an
        alpha value of 1 and non-selected points to `alpha_other`.
    """
    def __init__(self, ax, collection, alpha_other=0.3):
        self.canvas = ax.figure.canvas
        self.collection = collection
        self.alpha_other = alpha_other

        self.xys = collection.get_offsets()
        self.Npts = len(self.xys)

        # Ensure that we have separate colors for each object
        self.fc = collection.get_facecolors()
        if len(self.fc) == 0:
            raise ValueError('Collection must have a facecolor')
        elif len(self.fc) == 1:
            self.fc = np.tile(self.fc, self.Npts).reshape(self.Npts, -1)

        self.lasso = LassoSelector(ax, onselect=self.onselect)
        self.ind = []

    def onselect(self, verts):
        path = Path(verts)
        self.ind = np.nonzero([path.contains_point(xy) for xy in self.xys])[0]
        self.fc[:, -1] = self.alpha_other
        self.fc[self.ind, -1] = 1
        self.collection.set_facecolors(self.fc)
        self.canvas.draw_idle()

    def disconnect(self):
        self.lasso.disconnect_events()
        self.fc[:, -1] = 1
        self.collection.set_facecolors(self.fc)
        self.canvas.draw_idle()


class QCustomTableWidgetItem(QtGui.QTableWidgetItem):
	def __init__(self, value):
		super(QCustomTableWidgetItem, self).__init__(QtCore.QString('%s' % value))
		
	def __lt__(self, other):
		if (isinstance(other, QCustomTableWidgetItem)):
			selfDataValue = float(self.data(Qt.EditRole))
			otherDataValue = float(other.data(Qt.EditRole))
			return selfDataValue < otherDataValue
		else:
			return QtGui.QTableWidgetItem.__lt__(self, other)
	
		
class MainWindow(QtGui.QMainWindow):  
	def __init__(self):
		super(MainWindow, self).__init__()
		self.initUI()
		self.create_main_frame()
		self.createDockWindow()
		self.mtoolbar = NavigationToolbar(self.canvas, self)
		self.TS = _TileServer()
		self.TS.start()
		self._F = FileDialog()
		self.InputQ = Queue()
		self.OutputQ = Queue()
		self.ContextCheck = False
		self.show()
		
	def initUI(self):
		QtGui.QToolTip.setFont(QtGui.QFont('SansSerif', 10))
		self.setGeometry(300, 300, 250, 150)
		self.showMaximized()
		self.setWindowTitle('Airborne Tactical Analysis System (ATLAS)')
		self.setWindowIcon(QtGui.QIcon('ATLAS LOGO.png'))
		self.splashfile = "C:\Users\mpadm1n\Working Prototypes\ATLAS\images\loading.png"
		self.pixmap = QPixmap(self.splashfile)
		self.splash = QSplashScreen(self.pixmap)

		self.exitAction = QtGui.QAction(QtGui.QIcon('exit.png'), 'Exit', self)
		self.exitAction.triggered.connect(self.close)
		self.exitAction.setShortcut("Esc")
		self.openAction = QtGui.QAction(QtGui.QIcon('open.png'), 'Open', self)
		self.openAction.triggered.connect(self.open)
		self.openAction.setShortcut("CTRL+o")
		self.lassoAction = QtGui.QAction(QtGui.QIcon('lasso.png'), 'Lasso Data', self)
		self.lassoAction.triggered.connect(self.select)
		self.lassoAction.setShortcut("CTRL+l")
		self.cancelAction = QtGui.QAction(QtGui.QIcon('cancel.png'), 'Cancel Lasso', self)
		self.cancelAction.triggered.connect(self.selection_cancel)
		self.cancelAction.setShortcut("ALT+l")
		self.getdataAction = QtGui.QAction(QtGui.QIcon('get.png'), 'Get Data Result', self)
		self.getdataAction.triggered.connect(self.get_info_select)
		self.getdataAction.setShortcut("CTRL+g")
		self.homeAction = QtGui.QAction(QtGui.QIcon('lasso2.png'), 'Reset Plots', self)
		self.homeAction.triggered.connect(self.home)
		self.homeAction.setShortcut("CTRL+r")
		
		self.panAction = QtGui.QAction(QtGui.QIcon('pan.png'), 'Pan', self)
		self.panAction.setCheckable(True)
		self.panAction.triggered.connect(self.pan)
		self.panAction.setShortcut("CTRL+p")
		self.zoomAction = QtGui.QAction(QtGui.QIcon('zoom.png'), 'Zoom', self)
		self.zoomAction.triggered.connect(self.zoom)
		self.zoomAction.setCheckable(True)
		self.zoomAction.setShortcut("CTRL+b")

		self.actionGroup = QActionGroup(self)
		self.actionGroup.setExclusive(True)
		self.actionGroup.addAction(self.zoomAction)
		self.actionGroup.addAction(self.panAction)

		self.cpzAction = QtGui.QAction('Clear Pan/Zoom', self, statusTip="Clear Pan/Zoom")
		self.cpzAction.triggered.connect(self.cpz)
		self.cpzAction.setShortcut("CTRL+f")
		self.backAction = QtGui.QAction(QtGui.QIcon('lasso3.png'), 'Undo', self)
		self.backAction.triggered.connect(self.back)
		self.backAction.setShortcut("CTRL+z")
		self.forwardAction = QtGui.QAction(QtGui.QIcon('lasso4.png'), 'Redo', self)
		self.forwardAction.triggered.connect(self.forward)
		self.forwardAction.setShortcut("CTRL+y")
		self.saveAction = QtGui.QAction(QtGui.QIcon('lasso7.png'), 'Save Plot as Image', self)
		self.saveAction.triggered.connect(self.save)
		self.saveAction.setShortcut("CTRL+i")
		self.auxAction = QtGui.QAction(QtGui.QIcon('lasso5.png'), 'Generate Auxilary Plot Area', self)
		self.auxAction.triggered.connect(self.Aux_window)
		self.auxAction.setShortcut("CTRL+A")
		self.geoAction = QtGui.QAction(QtGui.QIcon('lasso6.png'), 'Generate Map', self)
		self.geoAction.triggered.connect(self._map_window)
		self.geoAction.setShortcut("CTRL+M")
		self.save_Action = QtGui.QAction(QtGui.QIcon('save.png'), 'Save/Backup Mission Data', self)
		self.save_Action.triggered.connect(self.saveMissionData)
		self.save_Action.setShortcut("CTRL+s")
		self.deletesave_Action = QtGui.QAction("Delete Save", self, statusTip="Delete Data Backup")
		self.deletesave_Action.triggered.connect(self.deleteSave)
		self.deleteAction = QtGui.QAction("Delete Emitter", self, statusTip="Delete currently displayed AEFs from Database")
		self.deleteAction.triggered.connect(self.deletePoints)
		self.deleteAction.setShortcut("CTRL+d")
		
		self.autosave_Action = QtGui.QAction("AutoSave", self, statusTip="Enable/Disable Autosave Feature")
		#self.autosave_Action.triggered.connect(AutoSave)
		#self.autosave_Action.triggered.connect(self.getAnalyse)
		
		#self.deleteproc_Action = QtGui.QAction("Delete Processed Emitters", self, statusTip="Delete All Emitters Processed from Mission")
		#self.deleteproc_Action.triggered.connect(delete_proc)
		#self.process_Action = QtGui.QAction("Process Emitter", self, statusTip="Process currently displayed AEFs as single Emitter")
		#self.process_Action.triggered.connect(run_ANALYZE)
		#self.process_Action.setShortcut("CTRL+q")
		
		#self.finalize_Action = QtGui.QAction("Finalize Mission", self, statusTip="Finalize and Exports Mission report")
		#self.finalize_Action.triggered.connect(finalize_mission)
		
		self.status = self.statusBar()
		
		self.menubar = self.menuBar()
		self.fileMenu = self.menubar.addMenu('&File')
		self.fileMenu.addAction(self.openAction) 	
		self.fileMenu.addAction(self.save_Action)
		self.fileMenu.addAction(self.deletesave_Action)
		#self.fileMenu.addAction(self.deleteproc_Action)
		#self.fileMenu.addAction(self.finalize_Action)
		self.fileMenu.addSeparator()
		self.fileMenu.addAction(self.exitAction)
		self.optionsMenu = self.menubar.addMenu('&Options')
		self.optionsMenu.addAction(self.autosave_Action)
		self.optionsMenu.addAction(self.cpzAction)
		self.viewMenu = self.menubar.addMenu("&View")
		self.dataMenu = self.menubar.addMenu('&Data Plots')
		self.dataMenu.addAction(self.auxAction)
		self.geoMenu = self.menubar.addMenu('&Map')
		self.geoMenu.addAction(self.geoAction)
		
		self.toolbar = self.addToolBar('ToolBar')
		self.toolbar.addAction(self.openAction)
		self.toolbar.addAction(self.save_Action) 
		self.toolbar.addAction(self.exitAction)
		self.toolbar.addSeparator()
		self.toolbar.addAction(self.auxAction)
		self.toolbar.addAction(self.geoAction)
		self.toolbar.addSeparator()
		self.toolbar.addAction(self.lassoAction)
		self.toolbar.addAction(self.getdataAction)
		self.toolbar.addAction(self.cancelAction)
		self.toolbar.addSeparator()
		self.toolbar.addAction(self.backAction)
		self.toolbar.addAction(self.homeAction)
		self.toolbar.addAction(self.forwardAction)
		self.toolbar.addSeparator()
		self.toolbar.addAction(self.panAction)
		self.toolbar.addAction(self.zoomAction)
		self.toolbar.addSeparator()
		self.toolbar.addAction(self.saveAction)
	
	def Analyse(self):
		data = self.OutputQ.get()
		
		aefs = []
		freqType = []
		freqModType = []
		freqMin = []
		freqMax = []
		pri = []
		priType = []
		pw = []
		pwType = []
		lat = []
		long = []
		smaj = []
		smin = []
		orient = []
		names = []
		
		
		for i in data:
			aefs.append(i[0])
			freqType.append(i[1])
			freqModType.append(i[2])
			freqMin.append(i[3])
			freqMax.append(i[4])
			pri.append(i[5])
			priType.append(i[6])
			pw.append(i[7])
			pwType.append(i[8])
			lat.append(i[9])
			long.append(i[10])
			smaj.append(i[11])
			smin.append(i[12])
			orient.append(i[13])
			names.append(i[14:])
		
		d = []
		for i in aefs: 
			if i not in d:
				d.append(i)
				
		aefs = d
		
		d = []
		for i in freqType: 
			if i not in d:
				d.append(i)
				
		freqType = d
		stable, contd, discd = 0,0,0
		for i in freqType:
			if i == 0:
				stable += 1
			elif i == 1:
				contd += 1
			elif i == 2:
				discd += 1
			else:
				ctypes.windll.user32.MessageBoxW(0, u"Unknown Frequency Type Detected", u"Data Type Error", 0x0 | 0x30)
		
		if stable > contd:
			if stable > discd:
				freqType = "Constant Single RF"
			else:
				freqType = "Discrete Agile"
		else:
			if contd > discd:
				freqType = "Continuous Agile"
			else:
				freqType = "Discrete Agile"
				
		d = []
		for i in freqModType: 
			if i not in d:
				d.append(i)
				
		freqModType = d
		pulsed, cw = 0,0
		for i in freqModType:
			if i == 0:
				pulsed += 1
			elif i == 1:
				cw += 1
			else:
				ctypes.windll.user32.MessageBoxW(0, u"Unknown Frequency Modulation Type Detected", u"Data Type Error", 0x0 | 0x30)
		
		if pulsed > cw:
			freqModType = "Pulsed"
		else:
			freqModType = "Continuous Wave"
		
		freqExcur = []
		for i in range(len(freqMin)):
			freqExcur.append(float(freqMax[i]) - float(freqMin[i]))
		
		freqMin = min(float(s) for s in freqMin)
		print freqMin
		freqMax = max(float(s) for s in freqMax)
		print freqMax
		freqExcur = (float(s) for s in freqExcur)
		
		
		print aefs
		print freqType
		print freqModType
		print freqMin
		print freqMax
			
	def AuxState(self):
		try:
			self.state = self.Aux.get_state()
			return self.state
		except:
			self.state = False
			return self.state

	def Aux_window(self):
		self.Aux = AuxWindow(root)
		self.Aux.show()
		
	def back(self):
		 self.mtoolbar.back()
	
	def clear_all(self):
		self.entry_1.clear()
		self.entry_2.clear()
		self.entry_3.clear()
		self.entry_4.clear()
		self.entry_5.clear()
		self.entry_6.clear()
		self.radar_list.clearSelection()
		self.aef_list.clearSelection()
		self.ptype_list.clearSelection()	
		if self.cb_1.checkState() == QtCore.Qt.CheckState.Checked:
			self.cb_1.toggle()
	
	def clear_list(self, listwidget):
		listwidget.clearSelection()
	
	def clear_p(self):
		self.entry_1.clear()
		self.entry_2.clear()
		self.entry_3.clear()
		self.entry_4.clear()
		self.entry_5.clear()
		self.entry_6.clear()
		
	def clear_que(self):
		while not self.OutputQ.empty():
			self.OutputQ.get()
			
	def closeEvent(self, event):
		self.TS.stopServer()
		try:
			self.IM.quit()	
		except:
			pass
		event.accept()
		
	def contextMenuEvent(self, event):
		if self.ContextCheck == True:
			menu = QtGui.QMenu(self)
			menu.addAction(self.cpzAction)
			menu.addSeparator()
			menu.addAction(self.homeAction)
			menu.addAction(self.backAction)
			menu.addAction(self.forwardAction)
			menu.addSeparator()
			menu.addAction(self.lassoAction)
			menu.addAction(self.cancelAction)
			menu.addAction(self.getdataAction)
			menu.addAction(self.deleteAction)
			menu.exec_(event.globalPos())
		else:
			return
		
	def cpz(self): # Clear Pan and Zoom
		if self.panAction.isChecked():
			self.panAction.trigger()
			
		if self.zoomAction.isChecked():
			self.zoomAction.trigger()
	
		self.actionGroup.setExclusive(False)
		self.panAction.setChecked(False)
		self.zoomAction.setChecked(False)
		self.zoomAction.setDisabled(False)
		self.panAction.setDisabled(False)
		self.actionGroup.setExclusive(True)
		
	def createDockWindow(self):
		self.dock = QtGui.QDockWidget("Filter", self)
		self.dock.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea)
		self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.dock)
		self.viewMenu.addAction(self.dock.toggleViewAction())
		
		label_1 = QtGui.QLabel("MIN:")
		label_1.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
		label_2 = QtGui.QLabel("MAX:")
		label_2.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
		label_3 = QtGui.QLabel("RF:")
		label_3.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
		label_4 = QtGui.QLabel("PRI:")
		label_4.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
		label_5 = QtGui.QLabel("PW:")
		label_5.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
		self.entry_1 = QtGui.QLineEdit() #RF MIN
		self.entry_2 = QtGui.QLineEdit() #RF MAX
		self.entry_3 = QtGui.QLineEdit() #PRI MIN
		self.entry_4 = QtGui.QLineEdit() #PRI MAX
		self.entry_5 = QtGui.QLineEdit() #PW MIN
		self.entry_6 = QtGui.QLineEdit() #PW MAX
		clear_1 = QPushButton("Clear")
		clear_1.clicked.connect(self.clear_p)
		splitter1 = QtGui.QFrame()
		splitter1.setFrameStyle(QFrame.HLine)
		splitter1.setSizePolicy(QSizePolicy.Minimum,QSizePolicy.Expanding)
		
		label_6 = QtGui.QLabel("Radar Names:")
		label_7 = QtGui.QLabel("AEF Numbers:")
		self.radar_list = QtGui.QListWidget()
		self.radar_list.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
		self.radar_list.setStyleSheet( """
                                QListWidget:item:selected {
                                     background-color:red;
                                }
                                """
                                )
		self.aef_list = QtGui.QListWidget()
		self.aef_list.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
		self.aef_list.setStyleSheet( """
                                QListWidget:item:selected {
                                     background-color:red;
                                }
                                """
                                )
		clear_2 = QPushButton("Clear")
		clear_2.clicked.connect(lambda: self.clear_list(self.radar_list))
		clear_3 = QPushButton("Clear")
		clear_3.clicked.connect(lambda: self.clear_list(self.aef_list))
		splitter2 = QtGui.QFrame()
		splitter2.setFrameStyle(QFrame.HLine)
		splitter2.setSizePolicy(QSizePolicy.Minimum,QSizePolicy.Expanding)
		
		self.cb_1 = QtGui.QCheckBox('CW Only', self)
		label_8 = QtGui.QLabel("PRI Type:")
		label_8.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
		self.ptype_list = QtGui.QListWidget()
		self.ptype_list.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
		self.ptype_list.setStyleSheet( """
                                QListWidget:item:selected {
                                     background-color:red;
                                }
                                """
                                )
		self.ptype_list.addItems(['Unknown', 'Pulse Constant', 'Stagger', 'Jitter'])
		self.ptype_list.setFixedSize(self.ptype_list.sizeHintForColumn(0) + 2 * self.ptype_list.frameWidth(), 
		self.ptype_list.sizeHintForRow(0) * self.ptype_list.count() + 2 * self.ptype_list.frameWidth())
		clear_4 = QPushButton("Clear")
		clear_4.clicked.connect(lambda: self.clear_list(self.ptype_list))
		splitter3 = QtGui.QFrame()
		splitter3.setFrameStyle(QFrame.HLine)
		splitter3.setSizePolicy(QSizePolicy.Minimum,QSizePolicy.Expanding)		
		
		label_9 = QtGui.QLabel("Ambiguities:")
		label_10 = QtGui.QLabel("Associated AEFs:")
		self.ambiguities_list = QtGui.QListWidget()
		self.assoc_aef_list = QtGui.QListWidget()
		q_unique = QPushButton("Filter on Unique ID")
		#q_unique.clicked.connect(_Unique_ID)
		q_aef = QPushButton("Filter on Assoc. AEFs")
		#q_aef.clicked.connect(quick_aef)
		splitter4 = QtGui.QFrame()
		splitter4.setFrameStyle(QFrame.HLine)
		splitter4.setSizePolicy(QSizePolicy.Minimum,QSizePolicy.Expanding)
		
		clear_5 = QPushButton("Clear All")
		clear_5.clicked.connect(self.clear_all)
		clear_5.setShortcut("Ctrl+C")
		submit = QPushButton("Submit")
		submit.clicked.connect(self.Submit)
		submit.setShortcut("Return")
		
		dockgrid = QtGui.QGridLayout()
		dockgrid.setSpacing(10)
		dockgrid.setRowStretch( 30, 1 )
		dockgrid.addWidget(label_1, 0, 1)
		dockgrid.addWidget(label_2, 0, 2)
		dockgrid.addWidget(label_3, 1, 0)
		dockgrid.addWidget(self.entry_1, 1, 1)
		dockgrid.addWidget(self.entry_2, 1, 2)
		dockgrid.addWidget(label_4, 2, 0)
		dockgrid.addWidget(self.entry_3, 2, 1)
		dockgrid.addWidget(self.entry_4, 2, 2)
		dockgrid.addWidget(label_5, 3, 0)
		dockgrid.addWidget(self.entry_5, 3, 1)
		dockgrid.addWidget(self.entry_6, 3, 2)
		dockgrid.addWidget(clear_1, 4, 1, 1, 2)
		dockgrid.addWidget(splitter1, 5, 0, 1, 3)
		dockgrid.addWidget(label_6, 6, 1)
		dockgrid.addWidget(self.radar_list, 7, 1, 5, 1)
		dockgrid.addWidget(clear_2, 12, 1)
		dockgrid.addWidget(label_7, 6, 2)
		dockgrid.addWidget(self.aef_list, 7, 2, 5, 1)
		dockgrid.addWidget(clear_3, 12, 2)
		dockgrid.addWidget(splitter2, 13, 0, 1, 3)
		dockgrid.addWidget(self.cb_1, 14, 1)
		dockgrid.addWidget(label_8, 15, 1)
		dockgrid.addWidget(self.ptype_list, 15, 2)
		dockgrid.addWidget(clear_4, 16, 2)
		dockgrid.addWidget(splitter3, 17, 0, 1, 3)
		dockgrid.addWidget(label_9, 18, 1)
		dockgrid.addWidget(label_10, 18, 2)
		dockgrid.addWidget(self.ambiguities_list, 19, 1, 5, 1)
		dockgrid.addWidget(self.assoc_aef_list, 19, 2, 5, 1) 
		#dockgrid.addWidget(q_unique, 24, 1)
		#dockgrid.addWidget(q_aef, 24, 2)
		dockgrid.addWidget(splitter4, 25, 0, 1, 3)
		dockgrid.addWidget(clear_5, 26, 0, 1, 3)
		dockgrid.addWidget(submit, 30, 0, 1, 3)
		
		self.filter_frame = FilterWidget()
		self.filter_frame.setLayout(dockgrid)
		self.dock.setWidget(self.filter_frame)
		
	def create_main_frame(self):
		self.main_frame = QWidget()
		
		self.fig = Figure((5.0, 4.0), dpi=100)
		self.canvas = FigureCanvas(self.fig)
		self.canvas.setParent(self.main_frame)
		self.canvas.setFocusPolicy(Qt.StrongFocus)
		self.canvas.setFocus()
	
		vbox = QVBoxLayout()
		vbox.addWidget(self.canvas)
		self.main_frame.setLayout(vbox)
		self.setCentralWidget(self.main_frame)
	
	def deletePoints(self):
		if hasattr(self, "selection"):
			verts = self.selection.xys[self.selection.ind]
			time_id = []
			
			for vert in verts:
				x = int(vert[0])
				time_id.append(x)
				
			self.InputQ.put("DELETE")
			self.InputQ.put(time_id)
			
			self.selection.disconnect()
			self.lassoAction.setEnabled(True)
		else:
			ctypes.windll.user32.MessageBoxW(0, u"No Data Selected.", u"Attribute Error", 0x01 | 0x30)
		
	def deleteSave(self):
		t = os.path.isfile("save.ats")
		if t == True:
			reply = ctypes.windll.user32.MessageBoxW(0, u"Are you sure you want to delete the backup file?", u"Delete File", 0x04 | 0x30)
			if reply == 7:
				return
			else:
				os.remove("save.ats")
				
		else:
			ctypes.windll.user32.MessageBoxW(0, u"No backup mission file exists", u"Delete File", 0x0 | 0x40)
	
	def filter_builder(self):
		_query_ = ""
		for i in range(3):	
			_a = ""
			if i == 0:
				x = self.entry_1 
				y = self.entry_2
				min = "freq_min_mhz>="
				max = "freq_max_mhz<="
			elif i == 1:
				x = self.entry_3
				y = self.entry_4
				min = "pri_1>="
				max = "pri_1<="
			else:
				x = self.entry_5
				y = self.entry_6
				min = "pw_usec>="
				max = "pw_usec<="
			
			if x.text() != "" and y.text() == "":
				_a += ( "(" + min + x.text() + ")" )
			elif x.text() == "" and y.text() != "":
				_a += ( "(" + max + y.text() + ")" )
			elif x.text() != "" and y.text() != "":
				_a += ( "(" + min + x.text() + " AND " + max + y.text() + ")" )
			else:
				_a += ""
			
			_query_ += _a
			
			if _a == "":
				continue
			else:
				_query_ += " AND "
		
		for i in range(3):
			index = []
			if i == 0:
				list = self.radar_list
				arg = "emitter_name1"
			elif i == 1:
				list = self.aef_list
				arg = "report_no"
			else:
				list = self.ptype_list
				arg = "pri_type"
			
			if i == 0 or i == 1:
				for item in list.selectedItems():
					item = list.item(list.row(item)).text()
					item = str(item)
					index.append(item)

			else:
				for item in list.selectedItems():
					item = list.indexFromItem(item).row()
					index.append(item)
			
			if index != []:
				item = str(index)
				item = item[1:-1]
				_query_ += (arg + ' IN (' + item + ') AND ')
				
		if self.cb_1.isChecked() == True:
			_query_ += "(freq_modulation_type=1) AND "
		
		_query_ = _query_[:-5]
		if _query_ == "":
			_query_ = "None"
		else:
			_query_ = " WHERE " + _query_

		return _query_
		
	def forward(self):
		 self.mtoolbar.forward()
	
	def get_data(self):
		self.utime = self.OutputQ.get()
		self.freq = self.OutputQ.get()
		self.pri = self.OutputQ.get()
		self.pw = self.OutputQ.get()
		self.unique_name = self.OutputQ.get()
		self.unique_aef = self.OutputQ.get()
		self.clear_que()
		self.update_lists(update_all=False)
		self.plot()
	
	def getFrame(self):	
		def update_table(table, data):
			table = table
			df = data
			table.setColumnCount(len(df.columns))
			table.setRowCount(len(df.index))
			table.setHorizontalHeaderLabels(("AEF Number", "RF Type", "RF Mod Type", "RF Min", "RF Max", "PRI", \
			"PRI Type", "PW", "PW Type", "Bearing", "Elevation Angle", "Latitude", "Longitude", "Semi-Major", \
			"Semi-Minor", "Orientation", "Range", "Altitude", "ACFT Latitude", "ACFT Longitude", "Heading (True)", \
			"Airspeed", "Primary ID", "Secondary ID", "Tertiary ID"))
			for i in range(len(df.index)):
				for j in range(len(df.columns)):
					if isinstance(df.iat[i,j], basestring):
						table.setItem(i,j,QTableWidgetItem(df.iat[i,j]))
					else:
						table.setItem(i,j,QCustomTableWidgetItem(df.iat[i,j]))

				
		data = self.OutputQ.get()
		df = pandas.DataFrame(data)
		self.result = QtGui.QTableWidget()
		self.result.setSortingEnabled(True)
		self.result.setWindowTitle('ATLAS Data Table')
		self.result.setWindowIcon(QtGui.QIcon('ATLAS LOGO.png'))
		update_table(self.result, df)
		self.result.show()
	
	def get_info_select(self):
		if hasattr(self, "selection"):
			verts = self.selection.xys[self.selection.ind]
			time_id = []
			
			for vert in verts:
				x = int(vert[0])
				time_id.append(x)
			
			self.InputQ.put(time_id)
			self.InputQ.put("DataFrame")
			
			self.selection.disconnect()
			self.lassoAction.setEnabled(True)

		elif hasattr(self, 'result'):
			self.result.show()
		else:
			ctypes.windll.user32.MessageBoxW(0, u"No Data Selected.", u"Attribute Error", 0x01 | 0x30)
		
	def getAnalyse(self):
		if hasattr(self, "selection"):
			verts = self.selection.xys[self.selection.ind]
			time_id = []
			
			for vert in verts:
				x = int(vert[0])
				time_id.append(x)
			
			self.InputQ.put(time_id)
			self.InputQ.put("Analyse")
			
			self.selection.disconnect()
			self.lassoAction.setEnabled(True)
		else:
			ctypes.windll.user32.MessageBoxW(0, u"No Data Selected.", u"Attribute Error", 0x01 | 0x30)
		
	def get_init_data(self):
		self.utime = self.OutputQ.get()
		self.freq = self.OutputQ.get()
		self.pri = self.OutputQ.get()
		self.pw = self.OutputQ.get()
		self.name1 = self.OutputQ.get()
		self.aef = self.OutputQ.get()
		self.unique_name = self.OutputQ.get()
		self.unique_aef = self.OutputQ.get()
		self.clear_que()
		self.update_lists()
		self.plot()
		
	def home(self):
		 self.mtoolbar.home()

	def _MapState(self):
		try:
			self.mapstate = self._map.get_state()
			return self.mapstate
		except:
			self.mapstate = False
			return self.mapstate
	
	def _map_window(self):
		self._map = MapModule.Map(root)
		self._map.show()
	
	def open(self):
		self._F.open()
		self.filename = self._F.get_name()
		if self.filename == None:
			return
		
		if not self.filename.endswith(".mdb"):
			if not self.filename.endswith(".accdb"):
				ctypes.windll.user32.MessageBoxW(0, u"The file you have selected is not a proper mission file.", u"File Type Error", 0x0 | 0x30)
				self.open()
		
		if not hasattr(self, "IM"):
			self.IM = InitializeMission.Open_Mission(self.filename, self.InputQ, self.OutputQ)
			self.IM.start()
			self.IM.init_Q_Ready.connect(self.get_init_data)
			self.IM.Q_Ready.connect(self.get_data)
			self.IM.DF_Ready.connect(self.getFrame)
			self.IM.postDelete.connect(self.Submit)
			#self.IM.AnalyseReady.connect(self.Analyse)
		else:
			self.InputQ.put("RECONNECT")
			self.InputQ.put(self.filename)
			 
		self.setStatus(self.filename)
							
	def pan(self):
		self.mtoolbar.pan()
		self.panAction.setDisabled(True)
		self.zoomAction.setDisabled(False)
	
	def plot(self):	
		self.fig.clf()
		self.fig.subplots_adjust(bottom=0.05,top=0.98,left=0.08,right=0.98,hspace=0.1)
		self.sb1 = self.fig.add_subplot(3,1,1)
		self.sb1.clear()
		self.pts1 = self.sb1.scatter(self.utime,self.freq)
		setp(self.sb1.axes.set_ylim(ymin=0))
		setp(self.sb1.get_xticklabels(), visible=False)
		self.sb1.set_ylabel("FREQ (MHz)")
		
		self.sb2 = self.fig.add_subplot(3,1,2, sharex=self.sb1)	
		self.sb2.clear()
		self.pts2 = self.sb2.scatter(self.utime,self.pri)	
		setp(self.sb2.axes.set_ylim(ymin=0))
		setp(self.sb2.get_xticklabels(), visible=False)
		self.sb2.set_ylabel("PRI (usec)")
		
		self.sb3 = self.fig.add_subplot(3,1,3, sharex=self.sb1)	
		self.sb3.clear()
		self.pts3 = self.sb3.scatter(self.utime,self.pw)
		setp(self.sb3.axes.set_ylim(ymin=0))
		setp(self.sb3.get_xticklabels(), visible=False)
		self.sb3.set_xlabel("TIME")
		self.sb3.set_ylabel("PW (usec)")
		
		def onclick(event):
			self.ContextCheck = True
			self.rightClickCheck = (event.button, event.x, event.y)
			
		def onrelease(event):
			if event.button == 3:
				if self.rightClickCheck == (event.button, event.x, event.y):
					pass
				else:
					self.ContextCheck = False
			
		cid = self.fig.canvas.mpl_connect("button_press_event", onclick)
		cid2 = self.fig.canvas.mpl_connect("button_release_event", onrelease)
		
		if self._MapState() == True:
			self._map.reload()
				
		if self.AuxState() == True:	
			self.Aux.redraw_sub()
		
		self.canvas.draw()
	
	def return_child_values(self):
		return self.freq, self.pri, self.pw

	def save(self):
		 self.mtoolbar.save_figure()

	def saveMissionData(self):
		self.InputQ.put("SAVE")
		 
	def select(self):
		self.cpz()
		self.lassoAction.setEnabled(False)
		self.bb1=self.sb1.get_position()
		self.bb2=self.sb2.get_position()
		self.bb3=self.sb3.get_position()
		
		def on_move(event):
			# get the x and y pixel coords
			x, y = event.x, event.y
			
			# translates pixel coordinates to canvas coordinates
			self.fx, self.fy = self.fig.transFigure.inverted().transform((x,y))
		
		def on_click(event):			
			self.fig.canvas.mpl_disconnect(self.binding_id)
			
			# checks which axes is being selected and uses those verts
			if self.bb1.contains(self.fx, self.fy):
				self.selection = SelectFromCollection(self.sb1, self.pts1)
			elif self.bb2.contains(self.fx, self.fy):
				self.selection = SelectFromCollection(self.sb2, self.pts2)
			elif self.bb3.contains(self.fx, self.fy):
				self.selection = SelectFromCollection(self.sb3, self.pts3)
			else:	
				box = None
				pts = None
			
			self.fig.canvas.mpl_disconnect(self.click_id)
		
		self.binding_id = self.fig.canvas.mpl_connect("motion_notify_event",on_move)
		self.click_id = self.fig.canvas.mpl_connect("button_press_event",on_click)
		
	def selection_cancel(self):
		try:
			self.lassoAction.setEnabled(True)
			self.fig.canvas.mpl_disconnect(self.click_id)
			self.fig.canvas.mpl_disconnect(self.binding_id)	
			self.selection.disconnect()
		except:
			pass

	def setStatus(self, filename):
		try:
			
			filename = filename.replace("\\", ".")
			filename = filename.replace("..", "\\")
			self.mission.setText(filename)
		except:
			mission = filename.replace("\\", "\\")
			self.mission = QLabel(mission)
			self.status.addPermanentWidget(self.mission)
								
	def Submit(self):
		self.str_query = self.filter_builder()
		self.InputQ.put(self.str_query)

	def update_lists(self, update_all=True):
		if update_all == True:
			self.ambiguities_list.clear()
			self.assoc_aef_list.clear()
			self.radar_list.clear()
			self.aef_list.clear()
			self.aef_list.addItems(self.unique_aef)
			self.radar_list.addItems(self.unique_name)
		else:
			self.ambiguities_list.clear()
			self.assoc_aef_list.clear()
			
		self.ambiguities_list.addItems(self.unique_name)
		self.assoc_aef_list.addItems(self.unique_aef)
	
	def zoom(self):
		self.mtoolbar.zoom()
		self.panAction.setDisabled(False)
		self.zoomAction.setDisabled(True)
		
	
if __name__ == '__main__':	
	#errorLogConfig()
	
	sysCalls.Compatability()
	
	app = QtGui.QApplication(sys.argv)
	root = MainWindow()
	sys.exit(app.exec_())