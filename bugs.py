import pyglet
import math
import random
import copy
from pyglet.gl import *
import pyglet.window

from datetime import datetime, timedelta
width = 1000	
height = 700
foodBoxLen=17
foodBoxScale = foodBoxLen**2/10.**2

numBirths = 0
turn=0

boxProp=[]

timer = 1/60.
defaultButtonCol = [175,0,0]
selected = []
selectTol = 5
sourceCenterRad = 7
sourceRateScale = 12
sourceStdevScale = 1.5
hist = []
foodHist = []
numBugsTotal = 0

didturn = datetime.now()
curButton = ""
sliderWidth = 16
sliderHeight = 5

with open('bugsOutput.txt', 'w') as f:
		f.write("Time, number bugs, Avg size, 0-5, 5-10, 10-15, 15-20, jaw 0-5, jaw 5-10, jaw 10-15, jaw 15-20, vMax 0-5, vMax 5-10, vMax 10-15, vMax 15-20, kM 0-5, kM 5-10, kM 10-15, kM 15-20, Avg food density, Mut const, % pred, avg size pred, num eaten, % herb, avg size herb, % scav, avg size scav, food growth const, num births " + '\n')

window = pyglet.window.Window(width,height)

class FoodBox:
	def __init__(self, food, regen, poo):
		self.food = food
		self.regen = regen
		self.poo = poo

class BugStor:
	def __init__(self, TOB, TOD, parent, firstChild, traits, x, y, killed): 
		self.TOB = TOB
		self.TOD = TOD
		self.parent = parent
		self.firstChild = firstChild
		self.traits = traits
		self.x = x
		self.y = y
		self.killed = killed


		
class FoodSource:
	def __init__(self, x, y, stdev, rate):
		self.x = x
		self.y = y
		self.stdev = stdev
		self.rate = rate
		
class Bug:
	def __init__(self, x, y, r, energy, jaw, gRate, speed, maxR, vMax, kM, mut,num, kMPoo, vMaxPoo, jawDead, points):
		self.x = x
		self.y = y
		self.r = r
		self.jaw = jaw
		self.energy = energy
		self.gRate = gRate
		self.speed = speed
		self.maxR = maxR
		self.vMax = vMax
		self.kM = kM
		self.mut = mut
		self.num = num
		self.kMPoo = kMPoo
		self.vMaxPoo = vMaxPoo
		self.jawDead = jawDead
		self.points = points

class BugDead:
	def __init__(self, x, y, r, energy, points):	
		self.x = x
		self.y = y
		self.r = r
		self.energy = energy
		self.points = points
		
class Maint:
	def __init__(self, r, jaw, speed, vMax, kM, vMaxPoo, kMPoo, jawDead):
		self.r = r
		self.jaw = jaw
		self.speed = speed
		self.vMax = vMax
		self.kM = kM
		self.vMaxPoo = vMaxPoo
		self.kMPoo = kMPoo
		self.jawDead = jawDead
class Slider:
	def __init__(self, x, y, height, percent, label, value, lines, colors):
		self.x = x
		self.y = y
		self.height = height
		self.percent = percent
		self.label = label
		self.value = value
		self.lines = lines
		self.colors = colors	
		
class Button:
	def __init__ (self, x, y, width, height, r, g, b, label):
		self.x = x
		self.y = y
		self.width = width
		self.height = height
		self.r = r
		self.g = g
		self.b = b
		self.label = label
		
class ModeRunning:
	def __init__(self):
		self.buttons = [Button(50, 10, 50, 18, defaultButtonCol[0], defaultButtonCol[1], defaultButtonCol[2], "Editor"), Button (110, 10, 50, 18, defaultButtonCol[0], defaultButtonCol[1], defaultButtonCol[2], "Tree")]
		self.foodGrowMax = 2.
		self.foodGrowMin = .1	
		self.skip=0	
		self.growthConstant = .01
		self.sliders = [Slider(10,8,60,.50,"Food grow rate", (self.foodGrowMax+self.foodGrowMin)/2, [],[])]
		self.kMconst=1.  #4 works
		self.overallDepletionConst = .5
		self.maxspeed=3
		self.eatingScalar=.2
		self.breedScalar = .15  #was .2
		self.spaceInLast = False
		self.depletion = Maint(.0017, .095, .0005, .025, .02, .02, .02, .03)#2nd and 3rd to last were .015
	def draw(self):	
		if self.skip == 0:
			drawFood()
			drawDead()
			drawBugs()
			drawSliders()	
			drawButtons()
	def update(self):
		global didturn
		global turn
		current = datetime.now()
		#if entered_update - left_update < timedelta(milliseconds=10):
		#	print("skip")
		#	return
		if current-didturn > timedelta(milliseconds = 16):
			self.updateEnergyMaint()
			self.grow()
			for i in range(10):
				didturn = datetime.now()
				self.updateBugPos()
				self.updateEat()
				self.breed()
				self.checkCollision()
				self.starve()	
				if turn%100==0:
					self.updateFood()
					self.decayDead()
				if turn%writeRate==0:
					write()
				turn+=1
	def click(self, x, y, button, modifiers):
		if button == pyglet.window.mouse.LEFT:
			change = True
			for i in self.sliders:
				if i.x <= x <= i.x + sliderWidth and i.y <= y <= i.y + i.height:
					change = False
			for i in self.buttons:
				if i.x <= x <= i.x + i.width and i.y <= y <= i.y + i.height:
					change = False
					if i.label == mode.buttons[0].label:
						changeMode(2)
						selectButton(2)
					if i.label == mode.buttons[1].label:
						global treeLines
						global treeLineCols

						changeMode(1)
						modeList[1].setupTree()

			if change:
				if self.skip ==0:
					self.skip=1
				else:
					self.skip=0
				pass
	def drag(self, x, y, dx, dy, button, modifiers):
		for i in self.sliders:
			if i.x <= x <= i.x + sliderWidth and i.y <= y <= i.y + i.height:
				i.percent = float((y-i.y))/i.height
			if i.label == "Food grow rate":
				value = self.foodGrowMin + (self.foodGrowMax-self.foodGrowMin)*i.percent
				i.value = value
	def scroll(self, x, y, scroll_x, scroll_y):
		pass
	def release(self, x, y, button, modifiers):
		pass		
	def updateBugPos(self):
		for bug in list:
			angle = random.random()*2*math.pi
			denom = bug.kM + bug.vMax + bug.vMaxPoo + bug.kMPoo + bug.jaw + bug.jawDead
			weightHerb = (bug.kM + bug.vMax)/(denom)
			weightPoo = (bug.vMaxPoo + bug.kMPoo)/(denom)
			boxX = int(bug.x//foodBoxLen)
			boxY = int(bug.y//foodBoxLen)
			food = boxProp[boxX][boxY].food
			poo = boxProp[boxX][boxY].poo 
			try:
				percentFood = boxProp[boxX][boxY].food/(boxProp[boxX][boxY].food+boxProp[boxX][boxY].poo)
			except:
				percentFood = 1.
			movementScalar = 1 - weightHerb*percentFood*food - (weightPoo)*(1-percentFood)*boxProp[boxX][boxY].poo 
			bug.x = bug.x + bug.speed*math.cos(angle)*self.maxspeed * movementScalar
			bug.y = bug.y + bug.speed*math.sin(angle)*self.maxspeed * movementScalar
			
			if bug.x+bug.r > width:
				bug.x = width-bug.r-1
			if bug.x-bug.r < 0:
				bug.x = bug.r+1
			if bug.y + bug.r > height:
				bug.y = height-bug.r-1
			if bug.y - bug.r < 0:
				bug.y = bug.r+1	


	def updateEat(self):
		for i in list:
			boxX = int(i.x//foodBoxLen)
			boxY = int(i.y//foodBoxLen)
			densityFood = boxProp[boxX][boxY].food
			densityPoo = boxProp[boxX][boxY].poo
			try:
				fracFood = densityFood/(densityFood+densityPoo)
			except:
				if densityPoo == 1.:
					fracFood = 0.
				elif densityFood == 1.:
					fracFood = 1.
			try:
				eatenFood = fracFood*.005*(i.vMax*.6 + .4)*densityFood/(.8*i.kM*self.kMconst+densityFood)
			except:
				eatenFood = 0.
			try:
				eatenPoo = .015*i.vMaxPoo*densityPoo/(i.kMPoo*self.kMconst+densityPoo)
			except:
				eatenPoo = 0.
			i.energy = i.energy + eatenFood/2.4 + eatenPoo/2.4   
				
			boxProp[boxX][boxY].food = max(0.,boxProp[boxX][boxY].food - eatenFood/foodBoxScale)
			boxProp[boxX][boxY].poo = max(0.,boxProp[boxX][boxY].poo - eatenPoo/foodBoxScale)
			i.energy = min(i.energy, 1.)
	def breed(self):
		global numBirths
		for i in list:
			if i.energy>.95 and i.r>i.maxR*maxR*.8:
				i.energy = i.energy*.6
				first=copy.deepcopy(i)
				second=copy.deepcopy(i)
				first.r = first.r*.714
				second.r = second.r*.714
				self.kill(i)

				list.append(first)
				list.append(second)
				self.inheritance()
				list[-1].points = getBugPoints(list[-1])
				list[-2].points = getBugPoints(list[-2])
				numBirths += 1
				self.dealWithHistBirth(i, first, second)
	def checkCollision(self):
		global gridEmpty
		grid = copy.deepcopy(gridEmpty)
		for i in list:
			gridX = int(i.x//(maxR*2))
			gridY = int(i.y//(maxR*2))
			grid[gridX][gridY].append(i)
			self.checkCollision2(grid, gridX, gridY)
		self.checkCollisionDead(grid)
	def checkCollision2(self, grid, gridX, gridY):
		for i in [-1,0,1]:	
			for j in [-1,0,1]:	
				
				try:	
					for q in grid[gridX+i][gridY+j]:
						r1 = grid[gridX][gridY][-1].r
						r2 = q.r 
						x1 = grid[gridX][gridY][-1].x
						x2 = q.x
						y1 = grid[gridX][gridY][-1].y
						y2 = q.y
						if (math.fabs(x2-x1)<(r1+r2) and math.fabs(y2-y1)<(r1+r2)):
							dist = (x2-x1)*(x2-x1)+(y2-y1)*(y2-y1)
							r = (r1+r2)*(r1+r2)
							if dist<r and dist != 0 and q.energy != 0 and grid[gridX][gridY][-1].energy != 0:
								self.theRing(grid[gridX][gridY][-1], q)
				except:
					pass
	def theRing(self, one, two):
		global eaten
		if hist[one.num].parent != hist[two.num].parent:
			if one.jaw*one.r*1.2 > two.r and not (two.jaw*two.r > one.r):	#Was multiplying eater's values by 1.2
				if self.spaceInLast:
					print("KILLING")
					self.spaceInLast = False
				else:
					print(" KILLING")
					self.spaceInLast = True
				two.energy = 0
				hist[two.num].killed = True
				eaten += 1
				pounce(one, two)
			elif two.jaw*two.r*1.2 > one.r and not (one.jaw*one.r > two.r):
				if self.spaceInLast:
					print("KILLING")
					self.spaceInLast = False
				else:
					print(" KILLING")
					self.spaceInLast = True
				one.energy = 0
				hist[one.num].killed = True
				eaten += 1
				self.pounce(two, one)
	def pounce(self, pouncer, pouncee):
		pouncer.x = (1-.25*pouncer.jawDead)*pouncer.x + .25*pouncer.jawDead*pouncee.x
		pouncer.y = (1-.25*pounder.jawDead)*pouncer.y + .25*pouncer.jawDead*pouncee.y
	def checkCollisionDead(self, grid):
		for i in listDead:
			gridX = int(i.x//(maxR*2))
			gridY = int(i.y//(maxR*2))
			self.checkCollisionDead2(grid, gridX, gridY, i)

	def checkCollisionDead2(self, grid, gridX, gridY, i):

		for x in [-1,0,1]:		#k corresponds to i
			for y in [-1,0,1]:	#n corresponds to j
				try:		
					for q in grid[gridX+x][gridY+y]:
						if (math.fabs(i.x - q.x)<(q.r + i.r) and math.fabs(i.y - q.y)<(i.r + q.r)):
							dist = (i.x - q.x)*(i.x - q.x) + (i.y - q.y)*(i.y - q.y)
							r = (i.r+q.r)*(i.r+q.r)
							
							if dist<r and q.energy != 0 and i.energy > 0:
								self.eatDead(i, q)						
				except: 
					pass
	def eatDead(self, meal, eater):
		
		food = min(eater.jawDead*eater.jawDead*eater.jawDead, meal.energy)
		eater.energy += food*self.eatingScalar*meal.r/maxR      #SCALE BY EATER RADIUS?
		meal.energy += -food
	def starve(self):
		global listDead
		for i in reversed(range(len(list))):
			if list[i].energy<=0:
				hist[list[i].num].TOD = turn
				hist[list[i].num].traits.r = list[i].r
				if hist[list[i].num].firstChild == -1:
					listDead.append(BugDead(list[i].x, list[i].y, list[i].r, 1., list[i].points))
				list.pop(i)
		for i in reversed(range(len(listDead))):
			if listDead[i].energy<=0:
				listDead.pop(i)

	def updateFood(self):
		for i in boxProp:
			for j in i:
				j.food = min(1, j.food + mode.sliders[0].value*j.regen)
	def decayDead(self):
		for i in listDead:
			reduce = .05*i.energy + .01 
			i.energy += -reduce
			boxProp[int(i.x//foodBoxLen)][int(i.y//foodBoxLen)].food += .3*reduce*i.r/maxR
	def updateEnergyMaint(self):
		for i in list:
			percentR = i.r/maxR
			loss = 10*self.overallDepletionConst*(self.depletion.r*percentR/2 + (self.depletion.speed*i.speed*percentR + self.depletion.jaw*i.jaw* percentR*percentR*percentR + self.depletion.jawDead*i.jawDead+ self.depletion.vMax*i.vMax + (1-i.kM)*self.depletion.kM + self.depletion.vMaxPoo*i.vMaxPoo + self.depletion.kMPoo*(1-i.kMPoo) + self.depletion.jawDead*i.jawDead)/90)
			i.energy = i.energy - loss  #currently only penalizing primary*secondary.  do secondary as well?
			self.poo(i, loss)
		
	def poo(self, bug, loss):
		boxX = int(bug.x//foodBoxLen)
		boxY = int(bug.y//foodBoxLen)
		boxProp[boxX][boxY].poo = min(1., boxProp[boxX][boxY].poo + (.5-(bug.vMaxPoo - bug.kMPoo)/2)*loss*bug.r/(maxR*foodBoxScale))    #maybe scale with R
	def grow(self):
		for i in range(len(list)):
			list[i].r = list[i].r + 10*self.growthConstant*(maxR*list[i].maxR-list[i].r)*list[i].gRate*list[i].energy
	def kill(self, victim):
		victim.energy = 0

	def dealWithHistBirth(self, i, first, second):
		global hist
		global turn
		global numBugsTotal
		first.num = numBugsTotal
		hist[i.num].firstChild = numBugsTotal
		numBugsTotal += 1
		second.num = numBugsTotal
		numBugsTotal += 1
		hist.append(BugStor(turn, -1, i.num, -1, list[-2], turn, -1, False))
		hist.append(BugStor(turn, -1, i.num, -1, list[-1], turn, -1, False))
		
	def inheritance(self): 
		list[-1].maxR = self.inheritanceScale(list[-1].maxR)
		list[-1].gRate = self.inheritanceScale(list[-1].gRate)
		list[-1].vMax = self.inheritanceScale(list[-1].vMax)
		list[-1].kM = self.inheritanceScale(list[-1].kM)
		list[-1].speed = self.inheritanceScale(list[-1].speed)
		list[-1].jaw = self.inheritanceScale(list[-1].jaw)
		#list[-1].mut = self.inheritanceScale(list[-1].mut)
		list[-1].maxR = self.inheritanceScale(list[-1].maxR)
		list[-1].kMPoo = self.inheritanceScale(list[-1].kMPoo)
		list[-1].vMaxPoo = self.inheritanceScale(list[-1].vMaxPoo)
		list[-1].jawDead = self.inheritanceScale(list[-1].jawDead)
		
		list[-2].maxR = self.inheritanceScale(list[-2].maxR)
		list[-2].gRate = self.inheritanceScale(list[-2].gRate)
		list[-2].vMax = self.inheritanceScale(list[-2].vMax)
		list[-2].kM = self.inheritanceScale(list[-2].kM)
		list[-2].speed = self.inheritanceScale(list[-2].speed)
		list[-2].jaw = self.inheritanceScale(list[-2].jaw)
		#list[i].mut = self.inheritanceScale(list[i].mut)
		list[-2].maxR = self.inheritanceScale(list[-2].maxR)
		list[-2].kMPoo = self.inheritanceScale(list[-2].kMPoo)
		list[-2].vMaxPoo = self.inheritanceScale(list[-2].vMaxPoo)
		list[-2].jawDead = self.inheritanceScale(list[-2].jawDead)
		
	def inheritanceScale(self, value):
		value = value + (random.random()-.5)*self.breedScalar
		value = min(1,value)
		value = max(.0001,value)
		return value

class ModeTree:	
	def __init__(self):
		self.buttons = []
		self.sliders = []	
		self.foodLines = []
		self.foodCols = []
		self.lines = []
		self.lineCols = []
		self.linesInArea = []
		self.lineColsInArea = []
		self.bugsInArea = []
		self.topLine = []
		self.xScaleMin = 1.
		self.yScaleMin = 1.
		self.xScale = 1.
		self.yScale = 1.
		self.xScaleMax = .5
		self.yScaleMax = 20.
		self.xScaleMin = .1
		self.yScaleMin = .1
		self.maxHeight = 0
		self.borderBoxes = []
		self.borderBoxCols = []
		self.distDragged = [0, 0]
		self.transX = 0
		self.transY = 0
		self.justBuilt = True
		self.window = []
		self.x = 0.
		self.y = 0.
		self.bottomStrip = 90
		self.topStrip = 10
	def update(self):
		pass
	def draw(self):	
		self.drawTreeLines()
		self.getTrans()
		if self.xScale*self.yScale > .1:
			self.drawTreeBugs()
			#pass
		self.drawKillXs()
		self.drawBorderBoxes()
		self.drawFoodLines()
	


	def click(self, x, y, button, modifiers):
		if button == pyglet.window.mouse.RIGHT:
			self.settingUp = True
			self.vertexListLines.delete()
			self.resetY()
			self.resetTOD()
			changeMode(0)
		elif button == pyglet.window.mouse.LEFT:
			self.startCoords = [self.x, self.y]
	def drag(self, x, y, dx, dy, button, modifiers):
		moveX = dx/self.xScale
		moveY = dy/self.yScale
		self.distDragged[0] += dx
		self.distDragged[1] += dy
		self.x = min(max(self.x-moveX,0),turn-self.window[0])
		self.y = min(max(self.y-moveY,0),self.maxHeight-self.window[1])
	def scroll(self, x, y, scroll_x, scroll_y):
		self.zoom(scroll_y, x, y)
	def release(self, x, y, button, modifiers):
		if not self.justBuilt:
			self.getLinesInArea()
			self.getBugsInArea()
			self.getBugDrawData()
		else:
			self.justBuilt = False
		self.distDragged = [0, 0]
		self.transX = 0
		self.transY = 0
		self.startCoords = [self.x, self.y]
	def zoom(self, scroll, x, y):	
		stepSizeY = max((self.yScaleMax - self.yScaleMin)/20,0)
		stepSizeX = max((self.xScaleMax - self.xScaleMin)/20,0)
		stepSizeScale = self.xScale
		oldXScale = self.xScale
		oldYScale = self.yScale
		self.xScale += scroll*stepSizeX*stepSizeScale**.2#*stepSizeScale
		self.yScale += scroll*stepSizeY*stepSizeScale**.2#*stepSizeScale
		self.xScale = max(min(self.xScaleMax, self.xScale),self.xScaleMin)
		self.yScale = max(min(self.yScaleMax, self.yScale),self.yScaleMin)
		oldWindow = self.window
		self.window = self.getWindow()
		self.adjustCorner(x, y, oldWindow, oldXScale, oldYScale)
		self.getBugsInArea()
		self.getBugDrawData()
		self.getLinesInArea()
		self.distDragged = [0, 0]
	def adjustCorner(self, x, y, oldWindow, oldXScale, oldYScale):
		xPos = self.getXPos(x, oldXScale)
		yPos = self.getYPos(y, oldYScale)
		self.x = int(min(max(self.x+(oldWindow[0] - self.window[0])*min(max((xPos-self.x)/oldWindow[0],0),1) , 0), turn - self.window[0]))
		self.y = int(min(max(self.y+(oldWindow[1] - self.window[1])*min(max((yPos-self.y)/oldWindow[1],0),1) , 0), self.maxHeight - self.window[1]))
	def getXPos(self, x, oldXScale):
		return x/oldXScale + self.x
	def getYPos(self, y, oldYScale):
		return (y - self.bottomStrip)/oldYScale + self.y
	def getTrans(self):
		if self.distDragged[0]/self.xScale < self.startCoords[0] < turn + self.distDragged[0]/self.xScale - self.window[0]:
			self.transX = self.distDragged[0]
		if self.distDragged[1]/self.yScale < self.startCoords[1] < self.maxHeight + self.distDragged[1]/self.yScale - self.window[1]:
			self.transY = self.distDragged[1]
	def getLinesInArea(self):
		self.linesInArea = []
		self.lineColsInArea = []
		for i in range(0, len(self.lines), 4):  
			if self.lines[i] <= self.x + 2*self.window[0] and self.lines[i+2] >= self.x - self.window[0] and self.lines[i+1] <= self.y + 2*self.window[1] and self.lines[i+3] >= self.y - self.window[1]:
				self.linesInArea+=self.lines[i:i+4]
				self.lineColsInArea += self.lineCols[int(i*1.5):int(i*1.5)+6]
		try:
			self.vertexListLines.delete()
		except:
			pass
		self.vertexListLines = pyglet.graphics.vertex_list(len(self.linesInArea)/2,
			('v2i', self.linesInArea),
			('c3B', self.lineColsInArea)	
		)
		self.getKillXLines()
	def getKillXLines(self):
		self.killXLines = []
		self.killXCols = [255, 0, 0]
		distMax = max(1, self.yScale*self.xScale)
		for i in self.bugsInArea:
			if i.killed:
				dist = min(distMax, i.traits.r)
				self.killXLines += [int((i.x-self.x)*self.xScale - dist), int((int(i.y)-self.y)*self.yScale - dist), int((i.x-self.x)*self.xScale + dist), int((int(i.y)-self.y)*self.yScale + dist), int((i.x-self.x)*self.xScale + dist), int((int(i.y)-self.y)*self.yScale - dist), int((i.x-self.x)*self.xScale - dist), int((int(i.y)-self.y)*self.yScale + dist)]
		self.killXCols = self.killXCols*int(len(self.killXLines)/2)
		try:
			self.vertexListKill.delete()
		except:
			pass
		if len(self.killXLines) > 0:
			self.vertexListKill = pyglet.graphics.vertex_list(len(self.killXLines)/2,
				('v2i', self.killXLines),
				('c3B', self.killXCols)
			)
	def getBugsInArea(self):
		self.bugsInArea = []
		for i in hist:
			if self.x - self.window[0] <= i.x <= self.x + 2*self.window[0] and self.y - self.window[1] <=i.y <= self.y + 2*self.window[1]:
				self.bugsInArea.append(i)
	def getBugDrawData(self):
		points = []
		cols = []
		for bug in self.bugsInArea:
			for i in range(5):
				points += self.addTri((bug.x-self.x)*self.xScale, self.yScale*(int(bug.y)-self.y), min(1,self.yScale*self.xScale)*bug.traits.r, bug.traits.points[i], bug.traits.points[i+1])
			points += self.addTri((bug.x-self.x)*self.xScale, self.yScale*(int(bug.y)-self.y), min(1,self.yScale*self.xScale)*bug.traits.r, bug.traits.points[5], bug.traits.points[0])
			cols += self.addHexCols(bug)
		self.bugDrawData = pyglet.graphics.vertex_list(len(points)/2,
		('v2i', points),
		('c3B', cols)
		)

	def drawTreeLines(self):
		glPushMatrix()
		glTranslated(-self.xScale*self.x,-self.yScale*self.y,0)
		glTranslated(0, self.bottomStrip, 0)
		glScaled(self.xScale,self.yScale,1)
		self.vertexListLines.draw(pyglet.gl.GL_LINES)
		glPopMatrix()		

	def drawFoodLines(self):
		vertex_list = pyglet.graphics.vertex_list((len(self.foodLines)/2),
		('v2i', self.foodLines),
		('c3B', self.foodCols)
		)		
		vertex_list.draw(pyglet.gl.GL_LINE_STRIP)
		vertex_list.delete()
		
	def drawTreeBugs(self):	
		glPushMatrix()
		glTranslated(0, self.bottomStrip, 0)
		glTranslated(self.transX,self.transY,0)
		self.bugDrawData.draw(pyglet.gl.GL_TRIANGLES)
		glPopMatrix()
	def drawKillXs(self):
		if len(self.killXLines) > 0:
			glPushMatrix()
			glTranslated(0, self.bottomStrip, 0)
			#if self.distDragged[0]/self.xScale < self.startCoords[0] < turn + self.distDragged[0]/self.xScale - self.window[0]:
			#	self.transX = copy.deepcopy(self.distDragged[0])
			#if self.distDragged[1]/self.yScale < self.startCoords[1] < self.maxHeight + self.distDragged[1]/self.yScale - self.window[1]:
			#	self.transY = copy.deepcopy(self.distDragged[1])
			glTranslated(self.transX,self.transY,0)
			self.vertexListKill.draw(pyglet.gl.GL_LINES)
			glPopMatrix()
	def addTri(self, x, y, r, UV1, UV2):
		triPts = []
		triPts.append(int(x))
		triPts.append(int(y))
		triPts.append(int(x + r*UV1[0]))
		triPts.append(int(y + r*UV1[1]))
		triPts.append(int(x + r*UV2[0]))
		triPts.append(int(y + r*UV2[1]))
		return triPts
	def addHexCols(self, bug):
		cols = []
		traitCol = [int(255*bug.traits.jaw), int(255*bug.traits.vMax), int(255*(1-bug.traits.kM))]
		for i in range(6):
			for j in range(3):
				cols += traitCol
		return cols
			
	def getWindow(self):
		return [turn*self.xScaleMin/self.xScale, self.maxHeight*self.yScaleMin/self.yScale]
	def resetY(self):
		for i in hist:
			i.y = -1
	def resetTOD(self):
		global turn
		for i in hist:
			if i.TOD == turn + 1:
				i.TOD = -1
				
	def doXScale(self, x):
		return self.xScale*x 
	def doYScale(self, y):
		return self.yScale*y + self.bottomStrip
	def setupTree(self):
		self.fixTOD()
		self.assignYs()
		self.foodLines = []
		self.foodCols = []
		self.topLine = []
		self.buildFoodLine()
		self.borderBoxes = []
		self.borderBoxCols = []
		self.yScaleMin = (height - (self.bottomStrip + self.topStrip))/self.getMaxY()
		self.xScaleMin = 1.0*width/turn
		self.xScale = self.xScaleMin
		self.yScale = self.yScaleMin
		self.x = 0
		self.y = 0
		self.assignLines()
		self.maxHeight = self.getMaxY()
		self.window = self.getWindow()
		self.getBugsInArea()
		self.getBugDrawData()
		self.getLinesInArea()
		#self.getLinesDraw()
		self.getBorderBoxes()
		self.justBuilt = True
		self.startCoords = [self.x, self.y]
	def fixTOD(self):
		global turn
		for i in hist:
			if i.TOD == -1:
				i.TOD = turn + 1
	def assignYs(self):
		global hist
		for i in range(numberBugs):
			self.assignMe(hist[i])
	def assignMe(self, curBug):
		curBug.y = self.getMaxHeight(curBug) + 1
		if curBug.y < hist[curBug.parent].y:
			curBug.y = (curBug.y*.75 + hist[curBug.parent].y*.25)
		self.topLine = self.adjustTopLine(curBug, self.topLine)
		self.topLine = self.addLast(curBug, self.topLine)
		if curBug.firstChild != -1:
			self.assignMe(hist[curBug.firstChild])
			self.assignMe(hist[curBug.firstChild+1])

	def getMaxHeight(self, curBug):
		maxHeight = 0
		for i in range(len(self.topLine)):
			if curBug.TOD + 100 >= self.topLine[i][0] and curBug.TOB < self.topLine[i][1]:
				maxHeight = max(self.topLine[i][2], maxHeight)
		return maxHeight

	def adjustTopLine(self, curBug, top):
		for i in range(len(top)):
			if top[i][0] < curBug.TOB and top[i][1] > curBug.TOD:
				top[i][0] = curBug.TOD
				top.insert(i,[top[i][0], curBug.TOB, top[i][2]])
				return self.adjustTopLine(curBug, top)
			elif top[i][0] >= curBug.TOB and top[i][1] <=curBug.TOD:
				top.pop(i)	
				return self.adjustTopLine(curBug, top)
			elif top[i][0] < curBug.TOB and top[i][1] > curBug.TOB:
				top[i][1] = curBug.TOB
			elif top[i][0] <= curBug.TOD and top[i][1] > curBug.TOD:
				top[i][0] = curBug.TOD
		return top	
		
	def addLast(self, curBug, top):
		insertIndex = 0
		for i in range(len(top)):
			if top[i][1] == curBug.TOB:
				insertIndex = i
		top.insert(insertIndex, [curBug.TOB, curBug.TOD, curBug.y])
		return top

	def buildFoodLine(self):
		foodXScale = writeRate*self.xScale
		for i in range(len(foodHist)):
			self.foodLines.append(int(i*foodXScale))
			self.foodLines.append(int(foodHist[i]*self.bottomStrip*.95))
			self.foodCols.append(0)
			self.foodCols.append(190)
			self.foodCols.append(0)

	def assignLines(self):
		global hist
		self.lines = []
		self.lineCols = []
		for i in hist:
			self.lines.append(int(i.x))
			self.lines.append(int(i.y))
			if i.TOD != -1:
				self.lines.append(int(i.x + i.TOD - i.TOB))
				self.lines.append(int(i.y))
				
				if i.firstChild != -1:
					self.addLineCol(i)
					self.addLineCol(i)	
				
					self.lines.append(int(i.x + i.TOD - i.TOB))
					self.lines.append(int(i.y))
					self.lines.append(int(hist[i.firstChild].x))
					self.lines.append(int(hist[i.firstChild].y))

					self.lines.append(int(i.x + i.TOD - i.TOB))
					self.lines.append(int(i.y))
					self.lines.append(int(hist[i.firstChild+1].x))
					self.lines.append(int(hist[i.firstChild+1].y))
			else:
				self.lines.append(int(turn))
				self.lines.append(int(i.y))
			self.addLineCol(i)

	def getMaxY(self):
		curMax = 0
		for i in hist:
			curMax = max(curMax,i.y)
		return curMax*1.
		
	def addLineCol(self, bug):
		global treeLineCols
		for i in range(2):
			self.lineCols.append(int(255*bug.traits.jaw))
			self.lineCols.append(int(255*bug.traits.vMax))
			self.lineCols.append(int(255*(1-bug.traits.kM)))
	def getBorderBoxes(self):
		self.addBox(0, 0, width, self.bottomStrip-10, 60)
		self.addBox(0, height - self.topStrip, width, height, 0)
	
	def addBox(self, xStart, yStart, width, height, lightness):
		self.addPt(xStart, yStart)
		self.addPt(xStart+width, yStart)
		self.addPt(xStart+width, yStart+height)
		self.addPt(xStart, yStart+height)
		self.addCols(lightness)
	def addPt(self, xPt, yPt):
		self.borderBoxes.append(xPt)
		self.borderBoxes.append(yPt)
	def addCols(self, lightness):
		for i in range(4):
			for j in range(3):
				self.borderBoxCols.append(lightness)
				
	def drawBorderBoxes(self):
		vertex_list = pyglet.graphics.vertex_list((len(self.borderBoxes)/2),
		('v2i', self.borderBoxes),
		('c3B', self.borderBoxCols)
		)
		vertex_list.draw(pyglet.gl.GL_QUADS)
		vertex_list.delete()
class ModeGod:
	def __init__(self):
		self.buttons = [Button(50, 10, 50, 18, defaultButtonCol[0], defaultButtonCol[1], defaultButtonCol[2], "Place"), Button(110, 10, 50, 18, defaultButtonCol[0], defaultButtonCol[1], defaultButtonCol[2], "Delete"), Button(170, 10, 50, 18, defaultButtonCol[0], defaultButtonCol[1], defaultButtonCol[2], "Edit")]
		self.sliders = []	
	def update(self):
		pass
	def draw(self):
		drawFood()
		self.drawFoodCircles()
		drawButtons()
	def click(self, x, y, button, modifiers):
		global foodSources
		if button == pyglet.window.mouse.LEFT:
			global selected

			clickedButton = False
			for i in mode.buttons:
				if i.x <= x <= i.x + i.width and i.y <= y <= i.y + i.height:
					if i.label == mode.buttons[0].label:
						selectButton(0)
					elif i.label == mode.buttons[1].label:
						selectButton(1)
					elif i.label == mode.buttons[2].label:
						selectButton(2)		
					clickedButton = True
			if not clickedButton:
				try:  
					selected = select(x, y)
					if curButton == "Delete" and selected[1] == "center":
						foodSources.pop(selected[0])
					elif curButton == "Place":
						foodSources.append(FoodSource(x, y, random.random()*(.5*stdev)+.5*stdev, foodReplenishScale*random.random()*.8 + foodReplenishScale*.2))
				except:
					pass

		if button == pyglet.window.mouse.RIGHT:
			
			for x in range(len(boxProp)):
				for y in range(len(boxProp[0])):
					boxProp[x][y].regen = getFoodRegen(x,y)
			changeMode(0)
	def drag(self, x, y, dx, dy, button, modifiers):
		if curButton == "Edit":
			try:
				if selected[1] == "center":
					foodSources[selected[0]].x += dx
					foodSources[selected[0]].y += dy
				elif selected[1] == "rate":
					unitVector = getUnitVector(foodSources[selected[0]].x, foodSources[selected[0]].y, x, y)
					dotProd = getDotProd(unitVector[0], unitVector[1], dx, dy)
					foodSources[selected[0]].rate += dotProd/sourceRateScale
				elif selected[1] == "stdev":
					unitVector = getUnitVector(foodSources[selected[0]].x, foodSources[selected[0]].y, x, y)
					dotProd = getDotProd(unitVector[0], unitVector[1], dx, dy)
					foodSources[selected[0]].stdev += dotProd/sourceStdevScale
			except:
				pass
	def scroll(self, x, y, scroll_x, scroll_y):
		pass
	def release(self, x, y, button, modifiers):
		pass
	def drawFoodCircles(self):
		for i in foodSources:
			points = getFoodCirclePoints(i)
			cols = getFoodCircleCols(points)
		

			
			vertex_list = pyglet.graphics.vertex_list((len(points[1])/2),
			('v2i', points[1]),
			('c3B', cols[0])
			)
			vertex_list.draw(pyglet.gl.GL_LINE_STRIP)
			vertex_list.delete()	
			
			vertex_list = pyglet.graphics.vertex_list((len(points[2])/2),
			('v2i', points[2]),
			('c3B', cols[1])
			)
			vertex_list.draw(pyglet.gl.GL_LINE_STRIP)
			vertex_list.delete()
			
			glBegin(GL_TRIANGLE_FAN)
			glColor3f(1.,1.,1.)
			for i in range(0, len(points[0]), 2):
				glVertex2f(points[0][i], points[0][i+1])
			glEnd()		
writeRate = 300



#Lists of classes are catagoryList
#List of objects listCatagory	


modeList = [ModeRunning(), ModeTree(), ModeGod()]


mode = modeList[0]

#Bug variables
numberBugs=25
numberSources=5
energyStart=.2
foodReplenishScale=4
maxR=20

#sortBinSize = 5
eaten = 0


#Food variables
stdev=175 #was 175

list = []
listDead = []



def getBugPoints(bug):
	points = []
	for i in range(6):
		if i%2 == 0:
			points.append([math.cos(2*math.pi*i/6 - math.pi/6), math.sin(2*math.pi*i/6 - math.pi/6)])
		else:
			r=1
			if i == 1:
				r = 1 - .8*bug.vMaxPoo
			elif i==3:
				r = .8*bug.kMPoo + .2
			elif i==5:
				r = 1 - .8*bug.jawDead
			points.append([r*math.cos(2*math.pi*i/6 - math.pi/6), r*math.sin(2*math.pi*i/6 - math.pi/6)])
	return points
def getFoodRegen(x, y):
	regen = 0.
	for source in range(len(foodSources)):
		dist = math.sqrt((x*foodBoxLen-foodSources[source].x)**2+(y*foodBoxLen-foodSources[source].y)**2)
		regen += foodSources[source].rate*2.718**(-dist*dist/(foodSources[source].stdev)**2)/foodSources[source].stdev
	return regen
	
def getFoodBoxCoords():
	coords=[]
	for i in range(len(boxProp)):
		for j in range(len(boxProp[0])):
		
			coords.append(i*foodBoxLen)
			coords.append(j*foodBoxLen)
			coords.append(i*foodBoxLen+foodBoxLen)
			coords.append(j*foodBoxLen)		
			coords.append(i*foodBoxLen+foodBoxLen)
			coords.append(j*foodBoxLen+foodBoxLen)
			coords.append(i*foodBoxLen)
			coords.append(j*foodBoxLen+foodBoxLen)
	return coords
	

def update(dt):
	mode.update()
	
def write():

	global eaten
	global numBirths
	global foodHist
	sizeData = getSizeData()
	pred = getPred()
	avgFoodDensity = getAvgFoodDensity()
	foodHist.append(avgFoodDensity)
	scav = getScav()
	herb = getHerb()
	mutConst = getMutConst()
	
	with open('bugsOutput.txt', 'a') as f:
		f.write(str(turn/100) + ", " + str(len(list)) + ", " + str(sizeData[0][0]) + ", " + str(sizeData[1][0]) + ", " + str(sizeData[1][1]) + ", " + str(sizeData[1][2]) + ", " + str(sizeData[1][3])  + ", " + str(sizeData[2][0]) + ", " + str(sizeData[2][1]) + ", " + str(sizeData[2][2]) + ", " + str(sizeData[2][3])  + ", " + str(sizeData[3][0]) + ", " + str(sizeData[3][1]) + ", " + str(sizeData[3][2]) + ", " + str(sizeData[3][3])  + ", " + str(sizeData[4][0]) + ", " + str(sizeData[4][1]) + ", " + str(sizeData[4][2]) + ", " + str(sizeData[4][3])  + ", " + str(avgFoodDensity) + ", " + str(mutConst) + ", " + str(pred[0]) + ", " + str(pred[1]) + "," + str(eaten) + ", " + str(herb[0]) + ", " + str(herb[1]) + ", " + str(scav[0]) + ", " + str(scav[1]) + ", " + str(mode.sliders[0].value) + ", " + str(numBirths) + '\n')
		
	eaten = 0
	numBirths = 0
def getSizeData():
	countBins = []
	jawBins = []
	kMBins = []
	vMaxBins = []
	for i in range(4):
		countBins.append(0)
		jawBins.append(0)
		kMBins.append(0)
		vMaxBins.append(0)
	sizeTotal=0.
	for q in list:
		myBin = int(q.r//5)
		jawBins[myBin] += q.jaw
		kMBins[myBin] += q.kM
		vMaxBins[myBin] += q.vMax
		countBins[myBin] += 1
		sizeTotal = sizeTotal + q.r
	for i in range(len(countBins)):
		try:
			jawBins[i] = jawBins[i]/countBins[i]
		except:
			jawBins[i] = 0
		try:
			kMBins[i] = kMBins[i]/countBins[i]
		except:
			kMBins[i] = 0
		try:
			vMaxBins[i] = vMaxBins[i]/countBins[i]
		except:
			vMaxBins[i] = 0
	tempSizeList = [sizeTotal/len(list)]
	return [tempSizeList, countBins, jawBins, vMaxBins, kMBins]

def getMutConst():
	mutConst = 0.
	for i in list:
		mutConst = mutConst + i.mut
	return mutConst/len(list)
def getScav():
	numScav = 0.
	scavSize = 0.
	for i in list:
	
		if (1-i.kM)*(1-i.jaw) > .7:
			scavSize = scavSize + i.r
			numScav += 1
	if numScav == 0:
		return (0,0)
	else:
		return (numScav/len(list),scavSize/numScav)

def getHerb():
	numHerb = 0.
	herbSize = 0.
	for i in list:
		if i.vMax*(1-i.jaw) > .7:
			numHerb += 1
			herbSize = herbSize + i.r
	if numHerb == 0:
		return (0,0)
	else:
		return (numHerb/len(list),herbSize/numHerb)
	
def getAvgFoodDensity():
	foodTotal = 0.
	for i in boxProp:
		for j in i:
			foodTotal = foodTotal + j.food
	return foodTotal/(len(boxProp)*len(boxProp[0]))

def getPred():
	numPred = 0.
	predSize = 0.
	for q in list:
		if q.jaw> .7:
			numPred += 1
			predSize = predSize + q.r
	if numPred == 0 :
		return (0,0)
	else:
		return (numPred/len(list),predSize/numPred)
	
		
	
	
		
def drawDead():
	for bug in listDead:
		glBegin(GL_TRIANGLE_FAN)
		glColor3f(bug.energy, bug.energy, bug.energy)
		glVertex2f(int(bug.x),int(bug.y))
		glColor3f(.4*bug.energy, .4*bug.energy, .4*bug.energy)
		for i in bug.points:
			glVertex2f(int(bug.x + bug.r*i[0]), int(bug.y + bug.r*i[1]))
		glVertex2f(int(bug.x + bug.r*bug.points[0][0]), int(bug.y + bug.r*bug.points[0][1]))
		glEnd()	
def drawBugs():
	
	for bug in list:
		glBegin(GL_TRIANGLE_FAN)
		glColor3f(bug.energy, bug.energy, bug.energy)
		glVertex2f(int(bug.x),int(bug.y))
		glColor3f(bug.jaw,bug.vMax,1-bug.kM)
		for i in bug.points:
			glVertex2f(int(bug.x + bug.r*i[0]), int(bug.y + bug.r*i[1]))
		glVertex2f(int(bug.x + bug.r*bug.points[0][0]), int(bug.y + bug.r*bug.points[0][1]))
		glEnd()
	#points = getListBugPoints()
	#vertex_list = pyglet.graphics.vertex_list((len(points[0])/2),
	#	('v2i', points[0]),
	#	('c3B', points[1])
	#)
	#vertex_list.draw(pyglet.gl.GL_TRIANGLES)
	#vertex_list.delete()	
######Stuff for making vertex list of bugs
def getListBugPoints():
	points = []
	cols = []
	for bug in list:
		for i in range(5):
			points +=addTri(bug.x, bug.y, bug.r, bug.points[i], bug.points[i+1])
		points += addTri(bug.x, bug.y, bug.r, bug.points[5], bug.points[0])
		cols += addHexCols(bug)
	return [points, cols]
def addTri(x, y, r, UV1, UV2):
	triPts = []
	triPts.append(int(x))
	triPts.append(int(y))
	triPts.append(int(x + r*UV1[0]))
	triPts.append(int(y + r*UV1[1]))
	triPts.append(int(x + r*UV2[0]))
	triPts.append(int(y + r*UV2[1]))
	return triPts
def addHexCols(bug):
	cols = []
	energy = [int(255*bug.energy), int(255*bug.energy), int(255*bug.energy)]
	traitCol = [int(255*bug.jaw), int(255*bug.vMax), int(255*(1-bug.kM))]
	for i in range(6):
		cols += energy
		cols += traitCol
		cols += traitCol
	return cols
#### End
def getFoodCirclePoints(source):
	centerPts = []
	rateLine = []
	stdevLine = []
	centerPts.append(int(source.x))
	centerPts.append(int(source.y))
	for i in range(20):
		centerPts.append(int(source.x + math.cos(math.pi*i/10)*sourceCenterRad))
		centerPts.append(int(source.y + math.sin(math.pi*i/10)*sourceCenterRad))
		rateLine.append(int(source.x + math.cos(math.pi*i/10)*source.rate*sourceRateScale))
		rateLine.append(int(source.y + math.sin(math.pi*i/10)*source.rate*sourceRateScale))
		for j in range(2):
			stdevLine.append(int(source.x + math.cos(math.pi*i/10 + j*math.pi/20)*source.stdev*sourceStdevScale))
			stdevLine.append(int(source.y + math.sin(math.pi*i/10 + j*math.pi/20)*source.stdev*sourceStdevScale))
	centerPts.append(int(source.x + sourceCenterRad))
	centerPts.append(int(source.y))
	rateLine.append(int(source.x + source.rate*sourceRateScale))
	rateLine.append(int(source.y))
	stdevLine.append(int(source.x + source.stdev*sourceStdevScale))
	stdevLine.append(int(source.y))
	return [centerPts, rateLine, stdevLine]
	
def getFoodCircleCols(lines):
	rateCols = []
	stdevCols = []
	for i in range(len(lines[1])/2):
		rateCols.append(225)
		rateCols.append(0)
		rateCols.append(0)
	for i in range(len(lines[2])/2):
		stdevCols.append(28)
		stdevCols.append(227)
		stdevCols.append(249)
	return [rateCols, stdevCols]
		
def drawFood():
	colors = []
	for i in boxProp:
		for j in i:
			for k in range(4):
				colors.append(int(255*(j.food*.184 + j.poo*.77)))
				colors.append(int(255*(j.food*.482 + j.poo*.184)))
				colors.append(int(255*(j.food*.082 + j.poo*.34)))

	vertex_list = pyglet.graphics.vertex_list((len(foodBoxCoords)/2),
    ('v2i', foodBoxCoords),
    ('c3B', colors)
	)
	vertex_list.draw(pyglet.gl.GL_QUADS)
	vertex_list.delete()

def assignSliderLines():
	for i in modeList:
		for j in i.sliders:
			global sliderWidth
			lines = []
			lines.append(j.x)
			lines.append(j.y)
			lines.append(j.x+sliderWidth)
			lines.append(j.y)
			
			lines.append(j.x+sliderWidth/2)
			lines.append(j.y)
			lines.append(j.x+sliderWidth/2)
			lines.append(j.y+j.height)
			
			lines.append(j.x)
			lines.append(j.y+j.height)
			lines.append(j.x+sliderWidth)
			lines.append(j.y+j.height)	
			j.lines = lines
	
def assignSliderColors():
	for i in modeList:
		for j in i.sliders:
			colors = []
			for k in range(len(j.lines)/2):
				colors.append(200)
				colors.append(200)
				colors.append(200)
			j.colors = colors
	

def drawSliders():
	global sliderWidth
	global sliderHeight
	for i in mode.sliders:
		pyglet.graphics.draw(len(i.lines)/2, pyglet.gl.GL_LINES,
		('v2i', i.lines),
		('c3B', i.colors)
		)
		#label = pyglet.text.Label(i.label ,
		#font_name='Times New Roman',
		#font_size=int(11),
		#x=int(i.x-25), y=int(i.y+i.height+10))
		#label.draw()

		#label = pyglet.text.Label("keke" ,
		#font_name='Times New Roman',
		#font_size=int(10),
		#x=int(i.x+sliderWidth/2+6), y=int(i.y+i.height/2))
		#label.draw()
		
		glColor3f(.784, .784, .784)
		glBegin(GL_QUADS)
		
		glVertex2f(i.x, i.y + i.height*i.percent-sliderHeight/2)
		glVertex2f(i.x+sliderWidth, i.y + i.height*i.percent-sliderHeight/2)
		glVertex2f(i.x+sliderWidth, i.y + i.height*i.percent+sliderHeight/2)
		glVertex2f(i.x, i.y + i.height*i.percent+sliderHeight/2)
		glEnd()
		
def drawButtons():
	for i in mode.buttons:
		glColor3f(i.r, i.g, i.b)
		glBegin(GL_QUADS)
		glVertex2f(i.x, i.y)
		glVertex2f(i.x+i.width, i.y)
		glVertex2f(i.x+i.width, i.y+i.height)
		glVertex2f(i.x, i.y+i.height)
		glEnd()
		
		label = pyglet.text.Label(i.label ,
		font_name='Times New Roman',
		font_size=int(i.height*.7),
		x=int(i.x+2), y=int(i.y+2))
		label.draw()	
def changeMode(newMode):
	global mode
	mode = modeList[newMode]

def select(x, y):
	sourceCenterRad
	sourceRateScale
	for i in foodSources:
		dist = math.sqrt((x-i.x)*(x-i.x) + (y-i.y)*(y-i.y))
		if dist <= sourceCenterRad:
			return [foodSources.index(i), "center"]
		elif i.rate*sourceRateScale-selectTol <= dist <= i.rate*sourceRateScale+selectTol:
			return [foodSources.index(i), "rate"]
		elif i.stdev*sourceStdevScale-selectTol <= dist <= i.stdev*sourceStdevScale+selectTol:
			return [foodSources.index(i), "stdev"]

def selectButton(clicked):
	global mode
	global curButton
	for i in mode.buttons:
		i.r = defaultButtonCol[0]
		i.g = defaultButtonCol[1]			
		i.b = defaultButtonCol[2]
	mode.buttons[clicked].r = 0
	mode.buttons[clicked].b = 100
	curButton = mode.buttons[clicked].label
@window.event	
def on_mouse_drag(x, y, dx, dy, button, modifiers):
	mode.drag(x,y,dx,dy,button,modifiers)
	
@window.event	
def on_mouse_press(x, y, button, modifiers):
	mode.click(x, y, button, modifiers)
		#list.append(Bug(x, y, startSize*maxR/2,random.random()*.5+.3,1.0,random.random(),random.random()*.5+.5,startSize,0.0,0.0, random.random()*.5))

@window.event
def on_mouse_release(x, y, button, modifiers):
	mode.release(x, y, button, modifiers)
		
		
@window.event		
def on_mouse_scroll(x, y, scroll_x, scroll_y):
	mode.scroll(x, y, scroll_x, scroll_y)
	
def getDotUnitVectors():
	vectors = []
	for i in range(6):
		vectors.append(math.cos(2*math.pi*i*60/360))
		vectors.append(math.sin(2*math.pi*i*60/360))
	return vectors	

def getUnitVector(x1, y1, x2, y2):
	mag = math.sqrt((x2-x1)*(x2-x1) + (y2-y1)*(y2-y1))
	return [(x2-x1)/mag, (y2-y1)/mag]
	
def getDotProd(x1, y1, x2, y2):
	return x1*x2 + y1*y2
@window.event
def on_draw():

	glClear(GL_COLOR_BUFFER_BIT)
	glLoadIdentity()
	
	#glBlendFunc(GL_ONE, GL_ONE)
	#glEnable(GL_BLEND);
	
	
	mode.draw()
		
for i in range(numberBugs):
	startSize = random.random()*.5+.5
	list.append(Bug(random.random()*width, random.random()*height, startSize*maxR/2,random.random()*.5+.3,random.random()*.5,random.random(),random.random(),startSize,random.random(),random.random(), random.random()*.5, numBugsTotal, 1., 0., 0., []))
	list[-1].points = getBugPoints(list[-1])
	hist.append(BugStor(0, -1, -1, -1, list[-1], 0, -1, False))
	numBugsTotal += 1
foodSources = []
for i in range(numberSources):
	foodSources.append(FoodSource(random.random()*width,random.random()*height, random.random()*(.5*stdev)+.5*stdev, foodReplenishScale*random.random()*.8 + foodReplenishScale*.2))

	
for i in range(int(width/foodBoxLen + 1)):
	holder=[]
	for j in range(int(height/foodBoxLen + 1)):
		holder.append(FoodBox(0.1, getFoodRegen(i, j), 0.))
	boxProp.append(holder)

foodBoxCoords=getFoodBoxCoords()
def getGridEmpty():
	grid = []
	for i in range (width//(maxR*2)+1):
		column = []
		for j in range (height//(maxR*2)+1):
			column.append( [] )
		grid.append(column)	
	return grid
gridEmpty = getGridEmpty()			
#	label.draw()
dotUnitVectors = getDotUnitVectors()
assignSliderLines()
assignSliderColors()


pyglet.clock.schedule_interval(update, timer)

pyglet.app.run()