import sys
import numpy
if __name__ == "__main__":
	sys.path[0] = '/'.join(sys.path[0].split('/')[0:-2]) #go up 2 level
from src.geometry.Geometry2D import *
from src.dynamics.dynamics2D import *


class SuperLattice2D(SuperGeometry):
	def __init__(self,SuperGeometry):
		self.DnQn = 'D2Q9'
		self.distribution = numpy.array([4/9, 1/9,1/9,1/9,1/9, 1/36,1/36,1/36,1/36])
		self.cx = 			numpy.array([  0,   1,  0, -1,  0,    1,  -1,  -1,   1])
		self.cy = 			numpy.array([  0,   0,  1,  0, -1,    1,   1,  -1,  -1])
		self.opposite = 	numpy.array([  0,   3,  4,  1,  2,    7,   8,   5,   6]) #should be moved to boundary condition part
		self.dynamics = numpy.zeros([SuperGeometry.materialMap.shape[0],SuperGeometry.materialMap.shape[1]])
		self.omega = numpy.zeros([SuperGeometry.materialMap.shape[0],SuperGeometry.materialMap.shape[1]])
		self.initDF = 0
		self.rhoMap = numpy.zeros([SuperGeometry.materialMap.shape[0],SuperGeometry.materialMap.shape[1]])
		self.UMap = numpy.zeros([SuperGeometry.materialMap.shape[0],SuperGeometry.materialMap.shape[1],2])
	def defineDynamics(self, SuperGeometry, materialNum, dynamics):
		for coord in self.getMaterialCoords(materialNum,SuperGeometry):
			self.dynamics[coord[0],coord[1]] = dynamics.index
			if hasattr(dynamics, 'omega'):
				self.omega[coord[0],coord[1]] = dynamics.omega
			else:
				self.omega[coord[0],coord[1]] = 0

			# index = 0: noDynamics
			# index = 1: bulkDynamics
			# index = 2: bounceBack
			# index = 3: velocity boundary
			# index = 4: pressure boundary

	def initDistributionFunction(self):
		self.f = numpy.zeros([self.rhoMap.shape[0],self.rhoMap.shape[1],9])
		self.feq = self.f
		for i in numpy.arange(self.f.shape[2]):
			self.f[:,:,i] = numpy.multiply(self.rhoMap,self.distribution[i])
		return self.f

	def defineRhoU(self,SuperGeometry,materialNum,rho,u):
		for coord in self.getMaterialCoords(materialNum,SuperGeometry):
			self.rhoMap[coord[0],coord[1]] = rho
			self.UMap[coord[0],coord[1],0] = u[0]
			self.UMap[coord[0],coord[1],1] = u[1]


	def collideAndStream(self):
		pass

	def collide(self):
		#initialize distribution function
		if self.initDF == 0:
			self.f = self.initDistributionFunction()
			self.surrundingDynamics = numpy.zeros(self.f.shape)
			for i in numpy.arange(9):
				self.surrundingDynamics[:,:,i] = numpy.roll(numpy.roll(self.dynamics,-self.cx[i],0),-self.cy[i],1)


			self.initDF = 1
		#collision
		for i in numpy.arange(self.rhoMap.shape[0]):
			for j in numpy.arange(self.rhoMap.shape[1]):
				if self.dynamics[i,j] == 0: #no dynamics
					pass
				elif self.dynamics[i,j] == 1: #BGK dynamics
					self.BGKcollide(i,j,self.f,self.UMap[:,:,0],self.UMap[:,:,1]) #i,j,f,ux,uy
				elif self.dynamics[i,j] == 2: #bounce back (half-way bounce back. ref: LBM:the principles and methods p177)
					pass

	def BGKcollide(self,i,j,f,ux,uy):
		self.t1 = numpy.power(ux,2)+numpy.power(uy,2) # u^2
		self.t2 = numpy.zeros([ux.shape[0],ux.shape[1],9])
		for i in numpy.arange(ux.shape[0]):
			for j in numpy.arange(ux.shape[1]):
				for k in numpy.arange(9):
					self.t2[i,j,k] = ux[i,j]*self.cx[k]+uy[i,j]*self.cy[k] #c_xy * u
					self.feq[i,j,k] = self.rhoMap[i,j]*self.distribution[k]*(1+3*self.t2[i,j,k]+4.5*self.t2[i,j,k]**2-1.5*self.t1[i,j])
					self.f[i,j,k] = self.omega[i,j]*self.feq[i,j,k] + (1-self.omega[i,j])*f[i,j,k]



	def stream(self):
		for i in numpy.arange(self.dynamics.shape[0]):
			for j in numpy.arange(self.dynamics.shape[1]):
				if self.dynamics[i,j] == 1:	
					for k in numpy.arange(1,9):
						if self.surrundingDynamics[i,j,k] == 2: #half way bounceback: modify f on wall
							self.f[(i+self.cx[k])%self.f.shape[0],(j+self.cy[k])%self.f.shape[1],self.opposite[k]] = self.f[i,j,k]

		for k in numpy.arange(1,9):
			self.f[:,:,k] = numpy.roll(numpy.roll(self.f[:,:,k],self.cx[k],0),self.cy[k],1)
		self.getRhoUMap() #calculate rhoMap given f after stream

	def getRhoUMap(self):
		self.rhoMap = self.f.sum(2)
		self.tmp_sum_ux = numpy.zeros(self.f.shape)
		self.tmp_sum_uy = numpy.zeros(self.f.shape)
		for i in numpy.arange(9):
			self.tmp_sum_ux[:,:,i] = self.f[:,:,i]*self.cx[i]
			self.tmp_sum_uy[:,:,i] = self.f[:,:,i]*self.cy[i]
		self.UMap[:,:,0] = self.tmp_sum_ux.sum(2)/self.rhoMap
		self.UMap[:,:,1] = self.tmp_sum_uy.sum(2)/self.rhoMap

	def getAverageRho(self):
		self.averageRho = 0
		for i in numpy.arange(self.dynamics.shape[0]):
			for j in numpy.arange(self.dynamics.shape[1]):
				if self.dynamics[i,j] == 1:
					self.averageRho = self.averageRho + self.rhoMap[i,j]
		return self.averageRho

	def communicate(self):
		pass

	def executeCoupling(self):
		pass

	def getRhoMap(self):
		return(self.rhoMap)

	def getUxMap(self):
		return(self.UMap[:,:,0])

	def getUyMap(self):
		return(self.UMap[:,:,1])

	def getSpeedMap(self):
		return(numpy.power(numpy.power(self.UMap[:,:,0],2)+numpy.power(self.UMap[:,:,1],2),1/2))



	@staticmethod #return N x 2 matrix 
	def getMaterialCoords(materialNum,SuperGeometry):
		materialCoords = numpy.zeros([0,2])
		for x in numpy.arange(SuperGeometry.materialMap.shape[0]):
			for y in numpy.arange(SuperGeometry.materialMap.shape[1]):
				if SuperGeometry.materialMap[x][y] == materialNum:
					materialCoords = numpy.append(materialCoords,[[x,y]],0)
		return numpy.int_(materialCoords)



if __name__ == "__main__":
	#parameters
	numpy.set_printoptions(3)
	nx = 10
	ny = 5
	center_x = 3
	center_y = 3
	radius = 2
	omega = 1
	#define geometry
	topPlate = Indicator.cuboid(0,ny,nx,ny) #x1,y1,x2,y2
	circle = Indicator.circle(center_x,center_y,radius)

	cGeometry = CuboidGeometry2D(0,0,nx,ny)
	cGeometry.setPeriodicity()
	superG = SuperGeometry(cGeometry)
	superG.rename(0,5,topPlate)
	superG.rename(0,1,circle)
	superG.rename(0,2)
	#print(superG.materialMap)
	superG.print()
	print('================================================')
	#lattice
	rho = 1
	u = [0.1,0.]
	sLattice = SuperLattice2D(superG)
	sLattice.defineRhoU(superG,1,1.1,u)
	#print(sLattice.getRhoMap())
	sLattice.defineRhoU(superG,5,1.0,u)

	sLattice.defineRhoU(superG,2,rho,u)
	print(sLattice.getRhoMap())
	#print(sLattice.getRhoMap().sum())

	#print(sLattice.getUxMap())
	#print(sLattice.getUyMap())
	#print(sLattice.getSpeedMap())
	bulk1 = BGKdynamics(omega)
	bounceb = bounceBack()
	sLattice.defineDynamics(superG,1,bulk1)# SuperGeometry, materialNum, dynamics
	sLattice.defineDynamics(superG,2,bulk1)
	sLattice.defineDynamics(superG,5,bounceb)
	#print(sLattice.dynamics)
	#print(sLattice.omega)
	#print(sLattice.dynamics)
	#print(sLattice.getUxMap())
	#print(sLattice.getUyMap())
	print(sLattice.rhoMap.sum(0).sum(0))
	print(sLattice.rhoMap.sum(0)[-1]  )
	print(sLattice.getAverageRho())
	for i in numpy.arange(1):
		sLattice.collide()
		sLattice.stream()



	#print(sLattice.dynamics)

	#print(sLattice.surrundingDynamics[:,:,1])

	#print(sLattice.f[:,:,1])
	#print(sLattice.rhoMap)
	#print(sLattice.getUxMap())
	#print(sLattice.getUyMap())
	print(sLattice.getRhoMap())
	#print(sLattice.getRhoMap().sum())

	print(sLattice.getAverageRho())



