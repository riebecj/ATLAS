import numpy as np

class Ellipse_Type(object):
	'''
	Ellipse Class object for storing, returning, and maintaining the fidelity of the elliptical 
	data as it is being convolved for posterity and fidelity. 
	'''
	def __init__(self, e):
		for i in e:
			self._x = e[0]
			self._y = e[1]
			self._sigma_major = e[2]
			self._sigma_minor = e[3]
			self._theta = e[4]
	@property
	def x(self):
		return self._x
		
	@property
	def y(self):
		return self._y
		
	@property
	def sigma_major(self):
		return self._sigma_major
		
	@property
	def sigma_minor(self):
		return self._sigma_minor
		
	@property
	def theta(self):
		return self._theta
		
	def data(self):
		return (self._x, self._y, self._sigma_major, self._sigma_minor, self._theta)

class Convolve(object):
	'''
	Convolve function taken from Dr. John E. Davis of the Harvard Smithsonian. 
	
	The original method was written in S-Lang, a language developed by Dr. Davis. 
	I have converted the S-Lang method into Python to execute in the same manner and deliver
	similar, if not, identical results. 
	'''
	def ellipse_to_correlation_matrix(self, e):
		sigy2 = np.square(e.sigma_major)
		sigx2 = np.square(e.sigma_minor)
		
		c = np.cos(e.theta)
		s = np.sin(e.theta)
		c2 = c*c
		s2 = s*s
		
		sx2 = sigx2*c2 + sigy2*s2
		sy2 = sigx2*s2 + sigy2*c2
		rho_sxsy = c*s*(sigy2-sigx2)
		
		a = [sx2, rho_sxsy, rho_sxsy, sy2]
		a = np.reshape(a, (2,2))
		return a

	def correlation_matrix_to_ellipse(self, matrix, x0, y0):
		sx2 = matrix.item((0,0))
		sy2 = matrix.item((1,1))
		rho2_sxsy = 2*matrix.item((0,1))
		sum = sy2+sx2
		diff = sy2-sx2
		
		e = []
		x = x0
		y = y0
		
		theta = 0.5*np.arctan2(rho2_sxsy, diff)
		diff = np.hypot(diff, rho2_sxsy)
		smajor = np.sqrt(0.5*(sum + diff))
		sminor = np.sqrt(0.5*(sum - diff))
		
		e.append(x)
		e.append(y)
		e.append(smajor)
		e.append(sminor)
		
		if theta > 0:
			e.append(theta)
		else:
			theta = theta + 360
			e.append(theta)
			
		e = Ellipse_Type(e)
		return e

	def inverse_2x2(self, a):
		det = a.item((0,0)) * a.item((1,1)) - a.item((0,1)) * a.item((1,0))
		a1 = np.matrix('0.00000000 0.00000000; 0.00000000 0.00000000')
		a1.itemset((0,0), a.item(1,1))
		a1.itemset((0,1), -a.item(0,1))
		a1.itemset((1,0), -a.item(1,0))
		a1.itemset((1,1), a.item(0,0))
		return a1/det

	def combine_ellipses(self, es):
		num = len(es)
		mu = 0
		Cinv = 0
		
		for i in es:
			e = Ellipse_Type(i)
			_point = np.matrix('0.000000; 0.0000000')
			_point.itemset((0,0), e.x)
			_point.itemset((1,0), e.y)
			C_m = self.ellipse_to_correlation_matrix(e)
			Cinv_m = self.inverse_2x2(C_m)
			mu += np.dot(Cinv_m, _point)
			Cinv += Cinv_m           
		
		C = self.inverse_2x2(Cinv)
		mu = np.dot(C, mu)
		new_e = self.correlation_matrix_to_ellipse(C, mu.item(0,0), mu.item(1,0))
		return new_e
		
	def convolve(self, ellipses):
		new_e = self.combine_ellipses(ellipses)
		return new_e.data()
	
	def info(self):
		print "Enter data as a list of tuples."
		print "I.E. Convolve.convolve([(list),(of),(tuples)])"
		print "Returns a single tuple of the combined elliptical data from list."
		print '''
		Tuple Structure
		----------------
		(Lat, Long, Sigma-Major, Sigma-Minor, Theta)
		
		Lat 		= Latitude of elliptical center in decimal degrees.
		Long 		= Longitude of elliptical center in decimal degrees.
		Sigma-Major	= The major leg of the ellipse. Unit agnostic. 
		Sigma-Minor	= The minor leg of the ellipse. Unit agnostic.
		Theta		= The Orientation angle of the ellipse in True degrees. 
		
		'''
	
	def test(self):
		d = [(30,71.6,50,24,18),(29.2,71.7,23,16,27),(30.3,72.3,47,5,-56)]
		print "data file = {}".format(d)
		e = self.convolve(d)
		print "Convolved output: {0}".format(e)