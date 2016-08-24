from multiprocessing import *
from PySide.QtCore import *
from PySide.QtGui import *
from PySide import QtCore
from PySide import QtGui
import sysCalls, sqlite3, pyodbc, time, json, sys, logging, ctypes, os

import numpy as np


class Open_Mission(QThread):
	init_Q_Ready = Signal()
	Q_Ready = Signal()
	DF_Ready = Signal()
	postDelete = Signal()
	AnalyseReady = Signal()
	
	def __init__(self, filename, input, output):
		super(Open_Mission, self).__init__()
		drivers = sysCalls.odbcDrivers()
		self.drivers = drivers.get()
		
		if self.drivers == []:
			ctypes.windll.user32.MessageBoxW(0, u"The appropriate ODBC drivers are not installed. Please install the correct drivers and restart the program.", u"ODBC Driver Error", 0x0 | 0x30)
			self.quit()
			return
 
		self.datafields = ['utc_time_stamp_usec', 'freq_mhz', 'pri_1', 'pw_usec', 'emitter_name1']
		self.filename = filename
		self.inQ = input
		self.outQ = output
		self.loop = True
		
	def reconnect(self, filename):
			self.filename = filename
			self.conn.close()
			self.connect_db(self.filename)
			self.init_query(self.outQ)
			self.init_Q_Ready.emit()
	
	def run(self):
		try:
			self.connect_db(self.filename)
			self.init_query(self.outQ)
			self.init_Q_Ready.emit()
			while self.loop == True:
				try:
					self.fltr = self.inQ.get()	
					if self.fltr != None:
					
						if type(self.fltr) is list:
							ID = self.inQ.get()
							self.get(self.fltr, self.outQ, ID)
							
						elif self.fltr == "SAVE":
							self.save()
							
						elif self.fltr == "DELETE":
							points = self.inQ.get()
							self.delete(points)
							
						elif self.fltr == "RECONNECT":
							file = self.inQ.get()
							self.reconnect(file)
							
						else:
							self._query(self.fltr, self.outQ)
							
				except Exception:
					pass
					
				time.sleep(2)
	
		except Exception:
			logging.exception("Connection Exception")
			raise

	def quit(self):
		self.loop = False
		self.terminate()
	
	def connect_db(self, filename):
		self.filename = filename
		type = self.filename.split(".")[1]
		
		for drvr in self.drivers:
			if type in drvr:
				self.Driver = drvr
		
		self.connMsnFile = pyodbc.connect("Driver=%s;DBQ=%s" % (self.Driver, self.filename))
		self.c1 = self.connMsnFile.cursor()
		self.c1.execute("SELECT * FROM aea_aef_report_data WHERE pri_type IN (0,1,3) AND ff_code IN ('FF3B', 'FF38', 'FF8A')")
		self.data = self.c1.fetchall()

		self.c1.execute("SELECT * FROM aea_aef_report_data WHERE pri_type=2 AND ff_code IN ('FF3B', 'FF38', 'FF8A')")
		self.stagger_data = self.c1.fetchall()
		
		self.fields = [column[0] for column in self.c1.description]

		self.inject = ""
		for column in self.c1.description:
			self.inject += "?,"
				
		self.inject = self.inject[:-1]

		self.d_types = []
		for row in self.c1.columns(table='aea_aef_report_data'):
			self.d_types.append(row.type_name)

		self.result = [None]*(len(self.fields)+len(self.d_types))
		self.result[::2] = self.fields
		self.result[1::2] = self.d_types
		self.result = str(self.result)
		self.result = self.result.replace(" u'", '')
		self.result = self.result.replace("'", '')
		self.result = self.result.split(',')
		self.result = map(' '.join, zip(self.result[::2], self.result[1::2]))
		self.result = str(self.result)
		self.result = self.result.replace("'", '')
		self.result = self.result.replace("[", '')
		self.result = self.result.replace("]", '')

		self.conn = sqlite3.connect(':memory:')
		self.c = self.conn.cursor()
		
		self.c.execute('CREATE TABLE aea_aef_report_data(%s)' % self.result)
		self.conn.commit
		
		for place, i in enumerate(self.data):
			pri = i[72] / 1000.000
			dev = i[56] / 1000.000
			i[72] = pri
			i[56] = dev
			self.data[place] = i
		
		self.c.executemany("INSERT INTO aea_aef_report_data VALUES (%s)" % self.inject, self.data)
		self.conn.commit
		
		self.data1 = self.Normalize_Staggers(self.stagger_data, self.c1)
		
		if self.data1 != None:
			for place, i in enumerate(self.data1):
				pri = i[72] / 1000.000
				dev = i[56] / 1000.000
				i[72] = pri
				i[56] = dev
				self.data1[place] = i
				
			self.c.executemany("INSERT INTO aea_aef_report_data VALUES (%s)" % self.inject, self.data1)
			self.conn.commit
		else:
			
			self.c1.execute("SELECT * FROM aea_aef_report_data WHERE pri_type=2")
			self.data1 = self.c1.fetchall()

			for place, i in enumerate(self.data1):
				pri = i[72] / 1000.000
				dev = i[56] / 1000.000
				i[72] = pri
				i[56] = dev
				self.data1[place] = i
				
			self.c.executemany("INSERT INTO aea_aef_report_data VALUES (%s)" % self.inject, self.data1)
			self.conn.commit
		
		self.current_file = self.filename	
		
		self.connMsnFile.close()

	def get(self, data, output, ID):
	
		if ID == "Analyse":
			def chunks(l, n):
				for i in xrange(0, len(l), n):
					yield l[i:i+n]
					
			dataframe = []
			
			try:
				for i in list(chunks(data, 100)):
					sql = ""
					for t in i:
						sql += ("utc_time_stamp_usec={0} OR ".format(str(t)))
			
					sql = sql[:-4]
					
					self.c.execute("SELECT report_no, frequency_type, freq_modulation_type, freq_min_mhz, freq_max_mhz, \
					pri_1, pri_type, pw_usec, pw_type, lat_deg, lon_deg, \
					ellipse_smajor_nm, ellipse_sminor_nm, ellipse_orientation_deg, emitter_name1, \
					emitter_name2, emitter_name3, emitter_name4, emitter_name5, emitter_name6, emitter_name7, emitter_name8, emitter_name9, emitter_name10 FROM aea_aef_report_data WHERE {0}".format(sql))
						
					d = self.c.fetchall()

					for p in d:
						dataframe.append(p)
					
					
					
				self.output.put(dataframe)
				self.AnalyseReady.emit()
			except:
				logging.exception("Connection Exception")
				raise
			
		else:	
			def chunks(l, n):
				for i in xrange(0, len(l), n):
					yield l[i:i+n]
					
			dataframe = []
			try:
				for i in list(chunks(data, 100)):
					sql = ""
					for t in i:
						sql += ("utc_time_stamp_usec={0} OR ".format(str(t)))
			
					sql = sql[:-4]
					
					self.c.execute("SELECT report_no, frequency_type, freq_modulation_type, freq_min_mhz, freq_max_mhz, \
					pri_1, pri_type, pw_usec, pw_type, azimuth_true_bearing_deg, elevation_angle, lat_deg, lon_deg, \
					ellipse_smajor_nm, ellipse_sminor_nm, ellipse_orientation_deg, range_emitter_nm, ba_altitude_above_mean_sea_Level, \
					ba_latitude, ba_longitude, ba_trueHeading_angle, ba_true_airspeed, emitter_name1, \
					emitter_name2, emitter_name3 FROM aea_aef_report_data WHERE {0}".format(sql))
						
					d = self.c.fetchall()

					for p in d:
						dataframe.append(p)
					
				self.output.put(dataframe)
				self.DF_Ready.emit()
			except:
				logging.exception("Connection Exception")
				raise
					
	def init_query(self, output):
		self.output = output
		self.freq=[]
		self.utime=[]
		self.pri = []
		self.pw = []
		self.name1 = []
		self.unique_name = []
		self.aef = []
		self.unique_aef = []
		self.geo = []
		
		self.dict = {'utc_time_stamp_usec': self.utime, 'freq_mhz': self.freq, 'pri_1': self.pri, 'pw_usec': self.pw, 'emitter_name1': self.name1}
		
		self.range_list = range(1, 17)
		
		self.c.execute("SELECT emitter_name1, lat_deg, lon_deg, ellipse_smajor_nm, ellipse_sminor_nm, ellipse_orientation_deg FROM aea_aef_report_data")
		self.geo = self.c.fetchall()
		
		for field in self.datafields:	
			self.c.execute("SELECT %s FROM aea_aef_report_data" % field)
			self.dict[field] = self.c.fetchall()
		
		self.c.execute("SELECT DISTINCT report_no FROM aea_aef_report_data")
		self.aef = self.c.fetchall()
		
		self.NameQuery = ""
		for num in self.range_list:
			self.NameQuery = self.NameQuery+"emitter_name"+str(num)+", "
		
		self.NameQuery = self.NameQuery[:-2]
		
		self.c.execute("SELECT DISTINCT %s FROM aea_aef_report_data" % self.NameQuery)
		self.name1 = self.c.fetchall()

		self.utime = self.dict['utc_time_stamp_usec']
		self.utime = [i[0] for i in self.utime]
		self.output.put(self.utime)
		self.freq = self.dict['freq_mhz']
		self.freq = [i[0] for i in self.freq]
		self.output.put(self.freq)
		self.pri = self.dict['pri_1']
		self.pri = [i[0] for i in self.pri]
		self.output.put(self.pri)
		self.pw = self.dict['pw_usec']
		self.pw = [i[0] for i in self.pw]
		self.output.put(self.pw)
		self.name1 = self.dict['emitter_name1']
		self.name1 = [i[0] for i in self.name1]
		self.output.put(self.name1)
		self.aef = [i[0] for i in self.aef]
		self.output.put(self.aef)

		for name in self.name1:
			if name not in self.unique_name:
				self.unique_name.append(name)
				
		self.unique_name.sort()
		self.output.put(self.unique_name)
		
		for num in self.aef:
			num = str(num)
			self.unique_aef.append(num)	

		self.output.put(self.unique_aef)	
		self.data_to_geojson(self.geo)
		
		self.c.execute("SELECT ba_latitude, ba_longitude FROM aea_aef_report_data")
		d = self.c.fetchall()
		acftPath = []
		
		for i in d:
			l = []
			l.append(i[0])
			l.append(i[1])
			acftPath.append(l)
			
		with open('ACFT.json', 'w') as outfile:
			outfile.seek(0)
			outfile.truncate()
			outfile.write("ACFT = ")
			json.dump(acftPath, outfile)
		
	def _query(self, filter, output):
		self.output = output
		
		if filter == 'None':
			self.freq=[]
			self.utime=[]
			self.pri = []
			self.pw = []
			self.name1 = []
			self.unique_name = []
			self.aef = []
			self.unique_aef = []
			self.geo = []
			
			self.dict = {'utc_time_stamp_usec': self.utime, 'freq_mhz': self.freq, 'pri_1': self.pri, 'pw_usec': self.pw, 'emitter_name1': self.name1}
			
			self.range_list = range(1, 17)
			
			self.c.execute("SELECT emitter_name1, lat_deg, lon_deg, ellipse_smajor_nm, ellipse_sminor_nm, ellipse_orientation_deg FROM aea_aef_report_data")
			self.geo = self.c.fetchall()
			
			for field in self.datafields:	
				self.c.execute("SELECT %s FROM aea_aef_report_data" % field)
				self.dict[field] = self.c.fetchall()
			
			self.c.execute("SELECT DISTINCT report_no FROM aea_aef_report_data")
			self.aef = self.c.fetchall()
			
			self.NameQuery = ""
			for num in self.range_list:
				self.NameQuery = self.NameQuery+"emitter_name"+str(num)+", "
			
			self.NameQuery = self.NameQuery[:-2]
			
			self.c.execute("SELECT DISTINCT %s FROM aea_aef_report_data" % self.NameQuery)
			self.name1 = self.c.fetchall()

			self.utime = self.dict['utc_time_stamp_usec']
			self.utime = [i[0] for i in self.utime]
			self.output.put(self.utime)
			self.freq = self.dict['freq_mhz']
			self.freq = [i[0] for i in self.freq]
			self.output.put(self.freq)
			self.pri = self.dict['pri_1']
			self.pri = [i[0] for i in self.pri]
			self.output.put(self.pri)
			self.pw = self.dict['pw_usec']
			self.pw = [i[0] for i in self.pw]
			self.output.put(self.pw)
			self.name1 = self.dict['emitter_name1']
			self.name1 = [i[0] for i in self.name1]
			self.aef = [int(i[0]) for i in self.aef]

			for name in self.name1:
				if name not in self.unique_name:
					self.unique_name.append(name)
					
			self.unique_name.sort()
			self.output.put(self.unique_name)
			
			for num in self.aef:
				num = str(num)
				self.unique_aef.append(num)	

			self.output.put(self.unique_aef)
			self.Q_Ready.emit()
			self.data_to_geojson(self.geo)			
		else:
			try:
				self.freq=[]
				self.utime=[]
				self.pri = []
				self.pw = []
				self.name1 = []
				self.unique_name = []
				self.aef = []
				self.unique_aef = []
				self.geo = []
				
				self.dict = {'utc_time_stamp_usec': self.utime, 'freq_mhz': self.freq, 'pri_1': self.pri, 'pw_usec': self.pw}
				
				self.range_list = range(1, 17)

				self.c.execute("SELECT emitter_name1, lat_deg, lon_deg, ellipse_smajor_nm, ellipse_sminor_nm, ellipse_orientation_deg FROM aea_aef_report_data" + filter)
				self.geo = self.c.fetchall()

				for field in self.datafields:	
					query = "SELECT %s FROM aea_aef_report_data" + filter
					self.c.execute(query % field)
					self.dict[field] = self.c.fetchall()
				
				self.c.execute("SELECT DISTINCT report_no FROM aea_aef_report_data" + filter)
				self.aef = self.c.fetchall()
				
				self.NameQuery = ""
				for num in self.range_list:
					self.NameQuery = self.NameQuery+"emitter_name"+str(num)+", "
				
				self.NameQuery = self.NameQuery[:-2]
				query = "SELECT DISTINCT %s FROM aea_aef_report_data" + filter
				self.c.execute(query % self.NameQuery)
				self.name1 = self.c.fetchall()
				
				self.utime = self.dict['utc_time_stamp_usec']
				self.utime = [i[0] for i in self.utime]
				self.output.put(self.utime)
				self.freq = self.dict['freq_mhz']
				self.freq = [i[0] for i in self.freq]
				self.output.put(self.freq)
				self.pri = self.dict['pri_1']
				self.pri = [i[0] for i in self.pri]
				self.output.put(self.pri)
				self.pw = self.dict['pw_usec']
				self.pw = [i[0] for i in self.pw]
				self.output.put(self.pw)
				self.name1 = [i for i in self.name1]
				self.aef = [int(i[0]) for i in self.aef]
				
				for _Tuple in self.name1:
					for name in _Tuple:
						if name not in self.unique_name:
							self.unique_name.append(name)
				
				self.unique_name.sort()
				self.output.put(self.unique_name)
				
				for num in self.aef:
					num = str(num)
					self.unique_aef.append(num)	

				self.output.put(self.unique_aef)
				self.Q_Ready.emit()
				self.data_to_geojson(self.geo)
				
				self.c.execute("SELECT azimuth_true_bearing_deg, ba_longitude, ba_latitude FROM aea_aef_report_data" + filter + " AND lat_deg=-90")
				d = self.c.fetchall()
				
				lobData = []
				for i in d:
					LOB = self.calculateLOB(i)
					lobData.append(LOB)
				
				lobData = lobData[:25]
				
				self.data_to_geojson(lobData, ID="LOB")
				
			except:
				(type, value, traceback) = sys.exc_info()
				sys.excepthook(type, value, traceback)
	
	def Normalize_Staggers(self, data, c1): # Converts staggered AEFs for visualization on main plots
		def stag_leg_calc(data):
			for _row in data:
				_index = 72
				_prinum = 0
				for num in range(0,16):
					if _row[_index] > 0:
						_prinum += 1
						_index += 1
					else:
						_index += 1
			return _prinum

		def time_delta(data):
			_entries = -1
			for row in data:
				_entries += 1
			
			first = data[0]
			last = data[_entries]
			_delta = last[8] - first[8]
			return _delta	
			
		def time_analysis(span,rows,legs,data):
			step = span / (rows * legs)
			
			_f = data[0]
			init_time = _f[8]
				
			return init_time, int(step)
			
		def Select_AEFs(data):
			AEFs = []
			for row in data:
				if row[3] not in AEFs:
					AEFs.append(int(row[3]))
			return AEFs

		AEFs = Select_AEFs(data)
		stagger_list = []
		for AEF in AEFs:
			AEF = float(AEF)
			self.c1.execute("SELECT * FROM aea_aef_report_data WHERE pri_type=2 AND report_no=?", AEF)
			data = self.c1.fetchall()
			
			if data == []:
				return
				
			self.col = [column[0] for column in self.c1.description]
			self.numcol = len(self.col)

			index = 0
			legs = stag_leg_calc(data)
			time_span = time_delta(data)
			entries = len(data)
			s_time, step = time_analysis(time_span,entries,legs,data)
			t_stamp = s_time	
				
			for row in data:
				_index = 72
				for i in range(0,legs):
					item = []
					for num in range(0,8):
						item.append(row[num])
					
					item.append(t_stamp)
					t_stamp += step
					
					for num in range(9,72):
						item.append(row[num])
					
					item.append(row[_index])
					_index += 1
					
					for num in range(0,15):
						item.append(0)
					
					for num in range(88,self.numcol):
						item.append(row[num])
					
					stagger_list.append(item)

		return stagger_list

	def data_to_geojson(self, data, ID="Default"): # Writes data out as geojson for plotting on map
		# Convert NM to meters and Orientation angle from True North degrees 
		# to Unit Circle degrees for proper map plotting
		if ID == "Default":
			for place, i in enumerate(data):
				i = list(i)
				i[3] = (i[3] * 1852)
				i[4] = (i[4] * 1852)
				i[5] = (float(i[5]) + 90)
				if i[0] == None:
					i[0] = "UNKNOWN"
				i = tuple(i)
				data[place] = i
			
			# create json-like list of dicts	
			markers = []
			for i in data:
				if i[1] == -90 and i[2] == -180:
					continue
				if i[1] == 0 and i[2] == 0:
					continue
				else:
					d = {"Primary_ID": str(i[0]), "lat": i[1], "lng": i[2], "Semi_Major": i[3], "Semi_Minor": i[4], "Orientation": i[5]}
					markers.append(d)
			markers = {"markers": markers}	
			# write json file to working directory
			with open('markers.json', 'w') as outfile:
				outfile.seek(0)
				outfile.truncate()
				outfile.write("var atlas = ")
				json.dump(markers, outfile)	
				
		else:
		
			with open('LOBs.json', 'w') as outfile:
				outfile.seek(0)
				outfile.truncate()
				outfile.write("LinesOfBearing = ")
				json.dump(data, outfile)

	def save(self): # Saves current working mission file in working directory
		t = os.path.isfile("save.ats")
		if t == True:
			reply = ctypes.windll.user32.MessageBoxW(0, u"There is a previously saved mission file. Are you sure you want to overwrite?", u"Save File", 0x04 | 0x30)
			if reply == 7:
				return
			else:		
				data = '\n'.join(self.conn.iterdump())
				f = open("save.ats", 'w')
				with f:
					f.write(data)
				
				ctypes.windll.user32.MessageBoxW(0, u"Mission Data has been saved!", u"Save File", 0x0 | 0x40)
		else:		
			data = '\n'.join(self.conn.iterdump())
			
			f = open("save.ats", 'w')
			
			with f:
				f.write(data)
		
			ctypes.windll.user32.MessageBoxW(0, u"Mission Data has been saved!", u"Save File", 0x0 | 0x40)
	
	def delete(self, points): # Deletes selected points on main plots
		def chunks(l, n):
			for i in xrange(0, len(l), n):
				yield l[i:i+n]
		
		try:
			for i in list(chunks(points, 100)):
				sql = ""
				for t in i:
					sql += ("utc_time_stamp_usec={0} OR ".format(str(t)))
		
				sql = sql[:-4]
				self.c.execute("DELETE FROM aea_aef_report_data WHERE {0}".format(sql))
				
			self.postDelete.emit()
		except:
			logging.exception("Connection Exception")
			raise
			
	def calculateLOB(self, data): # Returns LOB as [ [x,y] , [x1,y1] ]
		theta = data[0]
		_lat = data[2]
		_long = data[1]
		
		if theta < 0:
			theta = theta + 360
		
		thetaPrime = 90 - theta
		r = 2		
		
		x1 = np.sin(theta * 0.0174533)
		if theta >= 0 and theta <= 180:
			if x1 < 0:
				x1 = x1 * -1
		else:
			if x1 > 0:
				x1 = x1 * -1
		x1 = (x1 * r) + _long
		
		y1 = np.sin(thetaPrime * 0.0174533)
		if theta >= 180 or theta <= 90:
			if y1 < 0:
				y1 = y1 * -1
		else:
			if y1 > 0:
				y1 = y1 * -1
			
		y1 = (y1 * r) + _lat
		
		acft = []
		acft.append(_lat)
		acft.append(_long)
		
		endpoint = []
		endpoint.append(y1)
		endpoint.append(x1)
		
		LOB = []
		LOB.append(acft)
		LOB.append(endpoint)
		
		return LOB
