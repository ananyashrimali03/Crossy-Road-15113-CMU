from cmu_graphics import *
import random

# Game constants
GRID_SIZE = 40
ROWS = 15
COLS = 11
PLAYER_START_ROW = 13
LEVEL_ROWS = 13          # total obstacle rows the player must cross
FINISH_ROW = PLAYER_START_ROW - LEVEL_ROWS  # row 0 — reaching this wins

# Lane types
GRASS = 0
ROAD = 1
RIVER = 2

class Lane:
    def __init__(self, row, laneType, speed=0, direction=1):
        self.row = row
        self.type = laneType
        self.speed = speed
        self.direction = direction  # 1 for right, -1 for left
        self.obstacles = []
        
        if laneType == ROAD:
            self.generateCars()
        elif laneType == RIVER:
            self.generateLogs()
    
    def generateCars(self):
        # Randomly place 2-4 cars with gaps
        numCars = random.randint(2, 4)
        spacing = COLS * GRID_SIZE // numCars
        for i in range(numCars):
            x = i * spacing + random.randint(-20, 20)
            width = random.choice([60, 80, 100])
            color = random.choice(['red', 'blue', 'yellow', 'purple', 'orange'])
            self.obstacles.append({
                'x': x,
                'width': width,
                'color': color,
                'type': 'car'
            })
    
    def generateLogs(self):
        # Place 2-3 logs with gaps
        numLogs = random.randint(2, 3)
        spacing = COLS * GRID_SIZE // numLogs
        for i in range(numLogs):
            x = i * spacing + random.randint(-30, 30)
            width = random.randint(80, 140)
            self.obstacles.append({
                'x': x,
                'width': width,
                'type': 'log'
            })
    
    def update(self):
        for obstacle in self.obstacles:
            obstacle['x'] += self.speed * self.direction
            
            # Wrap around screen
            if self.direction > 0 and obstacle['x'] > COLS * GRID_SIZE + 50:
                obstacle['x'] = -obstacle['width'] - 50
            elif self.direction < 0 and obstacle['x'] < -obstacle['width'] - 50:
                obstacle['x'] = COLS * GRID_SIZE + 50

class Player:
    MOVE_SPEED = 12          # pixels moved per frame toward target

    def __init__(self):
        self.col = COLS // 2
        self.row = PLAYER_START_ROW
        self.x = self.col * GRID_SIZE + GRID_SIZE // 2
        self.y = self.row * GRID_SIZE + GRID_SIZE // 2
        self.targetX = self.x
        self.targetY = self.y
        self.moving = False
        self.onLog = None
        self.alive = True
        self.rotation = 0          # 0=up, 90=right, 180=down, 270=left
        self.inputQueue = []       # holds at most one pending (dx, dy)

    # ── public: called from onKeyPress ──
    def move(self, dx, dy):
        if not self.alive:
            return
        if not self.moving:
            self._startMove(dx, dy)   # instant — no queue needed
        else:
            self.inputQueue = [(dx, dy)]  # overwrite; only latest input matters

    # ── internal: validate + commit a move ──
    def _startMove(self, dx, dy):
        newCol = self.col + dx
        newRow = self.row + dy
        if not (0 <= newCol < COLS and newRow >= 0):
            return   # out of bounds — ignore

        # Rotation
        if dy < 0:   self.rotation = 0
        elif dx > 0: self.rotation = 90
        elif dy > 0: self.rotation = 180
        elif dx < 0: self.rotation = 270

        self.col = newCol
        self.row = newRow
        self.targetX = self.col * GRID_SIZE + GRID_SIZE // 2
        self.targetY = self.row * GRID_SIZE + GRID_SIZE // 2
        self.moving = True

    def update(self):
        if self.moving:
            dx = self.targetX - self.x
            dy = self.targetY - self.y
            dist = (dx * dx + dy * dy) ** 0.5

            if dist <= self.MOVE_SPEED:
                # Snap to target — we've arrived
                self.x = self.targetX
                self.y = self.targetY
                self.moving = False

                # Immediately start the queued move (if any)
                if self.inputQueue:
                    qdx, qdy = self.inputQueue.pop(0)
                    self._startMove(qdx, qdy)
            else:
                # Move a fixed number of pixels toward target
                self.x += dx / dist * self.MOVE_SPEED
                self.y += dy / dist * self.MOVE_SPEED

        # If on a log, drift with it
        if self.onLog and not self.moving:
            self.x += self.onLog['speed']
            self.targetX = self.x

            if self.x < 0 or self.x > COLS * GRID_SIZE:
                self.alive = False

def onAppStart(app):
    app.player = Player()
    app.lanes = []
    app.score = 0
    app.highScore = 0
    app.gameOver = False
    app.won = False
    app.winTimer = 0
    app.stepsCounter = 0
    app.cameraOffsetY = 0
    
    # Initialize first lanes
    for row in range(ROWS + 5):
        generateLane(app, row)

def generateLane(app, row):
    # Rows at or above the finish line, or at/below the start, are safe grass
    if row >= PLAYER_START_ROW or row <= FINISH_ROW:
        laneType = GRASS
    else:
        # Random terrain generation
        rand = random.random()
        if rand < 0.3:
            laneType = GRASS
        elif rand < 0.65:
            laneType = ROAD
        else:
            laneType = RIVER
    
    # Set speed and direction for obstacles
    speed = 0
    direction = 1
    if laneType == ROAD:
        speed = random.uniform(1.5, 3.5)
        direction = random.choice([1, -1])
    elif laneType == RIVER:
        speed = random.uniform(1.0, 2.5)
        direction = random.choice([1, -1])
    
    lane = Lane(row, laneType, speed, direction)
    # Insert at front so list stays sorted by row
    app.lanes.insert(0, lane)

def onStep(app):
    if app.gameOver or app.won:
        # Still tick the win timer so we can auto-advance after a pause
        if app.won:
            app.winTimer += 1
        return
    
    app.stepsCounter += 1
    
    # Update lanes
    for lane in app.lanes:
        lane.update()
    
    # Update player
    app.player.update()
    
    # ── camera: keep player anchored near the bottom of the screen ──
    SCREEN_ANCHOR_Y = ROWS * GRID_SIZE - 2 * GRID_SIZE
    targetCameraY = app.player.y - SCREEN_ANCHOR_Y
    app.cameraOffsetY = max(0, app.cameraOffsetY + (targetCameraY - app.cameraOffsetY) * 0.25)

    # ── generate new lanes ahead of the player (but not past FINISH_ROW) ──
    minRow = min(lane.row for lane in app.lanes)
    visibleTopRow = int(app.cameraOffsetY // GRID_SIZE) - 2
    while minRow > visibleTopRow and minRow > FINISH_ROW - 2:
        minRow -= 1
        generateLane(app, minRow)
    
    # ── win check ──
    if not app.player.moving and app.player.row <= FINISH_ROW:
        app.won = True
        app.winTimer = 0
        app.score = max(app.score, LEVEL_ROWS)
        app.highScore = max(app.highScore, app.score)
        return          # skip collision checks on the win frame
    
    # Update score (how far forward from start)
    if not app.player.moving:
        newScore = max(0, PLAYER_START_ROW - app.player.row)
        if newScore > app.score:
            app.score = newScore
            app.highScore = max(app.highScore, app.score)
    
    # Check collisions
    checkCollisions(app)

def checkCollisions(app):
    if not app.player.alive:
        app.gameOver = True
        return
    
    playerRow = app.player.row
    
    # Find the lane the player is actually on by matching row number
    lane = None
    for l in app.lanes:
        if l.row == playerRow:
            lane = l
            break
    
    if lane is None:
        return   # player is on a row we haven't generated yet — safe for now
    
    # Reset log status
    app.player.onLog = None
    
    if lane.type == RIVER:
        # Must be on a log
        onLog = False
        for obstacle in lane.obstacles:
            if (obstacle['x'] < app.player.x < obstacle['x'] + obstacle['width']):
                onLog = True
                app.player.onLog = {
                    'speed': lane.speed * lane.direction
                }
                break
        
        if not onLog and not app.player.moving:
            app.player.alive = False
            app.gameOver = True
    
    elif lane.type == ROAD:
        # Must NOT hit a car
        for obstacle in lane.obstacles:
            if (obstacle['x'] < app.player.x < obstacle['x'] + obstacle['width']):
                carY = lane.row * GRID_SIZE + GRID_SIZE // 2
                if abs(app.player.y - carY) < GRID_SIZE * 0.6:
                    app.player.alive = False
                    app.gameOver = True

def onKeyPress(app, key):
    if app.gameOver or app.won:
        if key == 'r':
            onAppStart(app)
        return
    
    if key == 'up':
        app.player.move(0, -1)
    elif key == 'down':
        app.player.move(0, 1)
    elif key == 'left':
        app.player.move(-1, 0)
    elif key == 'right':
        app.player.move(1, 0)

def redrawAll(app):
    # Draw sky
    drawRect(0, 0, COLS * GRID_SIZE, ROWS * GRID_SIZE, fill='skyBlue')
    
    # Draw lanes
    for lane in app.lanes:
        y = lane.row * GRID_SIZE - app.cameraOffsetY
        
        if -GRID_SIZE < y < ROWS * GRID_SIZE + GRID_SIZE:
            if lane.type == GRASS:
                drawRect(0, y, COLS * GRID_SIZE, GRID_SIZE, fill='lightGreen')
                # Draw grass texture
                for i in range(0, COLS * GRID_SIZE, 20):
                    drawLine(i, y + 5, i + 5, y + 8, fill='green', lineWidth=2)
                    drawLine(i + 10, y + 3, i + 12, y + 7, fill='green', lineWidth=2)
                
                # ── finish line decoration on FINISH_ROW ──
                if lane.row == FINISH_ROW:
                    # Checkered banner across the row
                    squareSize = 10
                    for col in range(COLS * GRID_SIZE // squareSize):
                        for rowIdx in range(GRID_SIZE // squareSize):
                            color = 'white' if (col + rowIdx) % 2 == 0 else 'black'
                            drawRect(col * squareSize, y + rowIdx * squareSize,
                                     squareSize, squareSize, fill=color)
                    # Flag poles at left and right
                    for flagX in [15, COLS * GRID_SIZE - 15]:
                        drawRect(flagX - 2, y - 30, 4, 30, fill='gray')
                        drawPolygon(flagX + 2, y - 30,
                                    flagX + 22, y - 24,
                                    flagX + 2, y - 18,
                                    fill='red', border='darkred', borderWidth=1)
            
            elif lane.type == ROAD:
                drawRect(0, y, COLS * GRID_SIZE, GRID_SIZE, fill='dimGray')
                # Draw road lines
                for i in range(0, COLS * GRID_SIZE, 40):
                    drawRect(i, y + GRID_SIZE // 2 - 2, 20, 4, fill='white')
                
                # Draw cars
                for car in lane.obstacles:
                    carX = car['x']
                    carY = y + GRID_SIZE // 2
                    drawRect(carX, carY - 15, car['width'], 30, 
                            fill=car['color'], border='black', borderWidth=2)
                    # Windows
                    drawRect(carX + 10, carY - 8, 20, 16, fill='lightBlue')
                    drawRect(carX + car['width'] - 30, carY - 8, 20, 16, fill='lightBlue')
            
            elif lane.type == RIVER:
                drawRect(0, y, COLS * GRID_SIZE, GRID_SIZE, fill='deepSkyBlue')
                # Draw water effect
                for i in range(0, COLS * GRID_SIZE, 30):
                    drawOval(i + (app.stepsCounter % 30), y + 10, 15, 8, 
                            fill='lightBlue', opacity=50)
                
                # Draw logs
                for log in lane.obstacles:
                    logX = log['x']
                    logY = y + GRID_SIZE // 2
                    drawRect(logX, logY - 12, log['width'], 24, 
                            fill='sienna', border='saddleBrown', borderWidth=2)
                    # Log rings
                    for i in range(3):
                        drawCircle(logX + 20 + i * 30, logY, 8, 
                                  fill='peru', border='saddleBrown')
    
    # Draw player (chicken)
    if app.player.alive:
        px = app.player.x
        py = app.player.y - app.cameraOffsetY
        
        # Body - main circle
        drawCircle(px, py, 15, fill='white', border='black', borderWidth=2)
        
        # Head based on rotation
        if app.player.rotation == 0:  # up
            headY = py - 15
            drawCircle(px, headY, 8, fill='white', border='black', borderWidth=2)
            drawCircle(px - 3, headY - 2, 2, fill='black')
            drawCircle(px + 3, headY - 2, 2, fill='black')
            drawPolygon(px, headY + 2, px - 3, headY + 5, px + 3, headY + 5, 
                       fill='orange')
            # Comb (red crest)
            drawPolygon(px - 2, headY - 6, px, headY - 10, px + 2, headY - 6, 
                       fill='red')
        elif app.player.rotation == 90:  # right
            headX = px + 15
            drawCircle(headX, py, 8, fill='white', border='black', borderWidth=2)
            drawCircle(headX + 2, py - 3, 2, fill='black')
            drawCircle(headX + 2, py + 3, 2, fill='black')
            drawPolygon(headX + 3, py, headX + 6, py - 3, headX + 6, py + 3, 
                       fill='orange')
            # Comb
            drawPolygon(headX + 6, py - 2, headX + 10, py, headX + 6, py + 2, 
                       fill='red')
        elif app.player.rotation == 180:  # down
            headY = py + 15
            drawCircle(px, headY, 8, fill='white', border='black', borderWidth=2)
            drawCircle(px - 3, headY + 2, 2, fill='black')
            drawCircle(px + 3, headY + 2, 2, fill='black')
            drawPolygon(px, headY - 2, px - 3, headY - 5, px + 3, headY - 5, 
                       fill='orange')
            # Comb
            drawPolygon(px - 2, headY + 6, px, headY + 10, px + 2, headY + 6, 
                       fill='red')
        else:  # left
            headX = px - 15
            drawCircle(headX, py, 8, fill='white', border='black', borderWidth=2)
            drawCircle(headX - 2, py - 3, 2, fill='black')
            drawCircle(headX - 2, py + 3, 2, fill='black')
            drawPolygon(headX - 3, py, headX - 6, py - 3, headX - 6, py + 3, 
                       fill='orange')
            # Comb
            drawPolygon(headX - 6, py - 2, headX - 10, py, headX - 6, py + 2, 
                       fill='red')
    
    # Draw UI
    drawRect(0, 0, COLS * GRID_SIZE, 50, fill='black', opacity=70)
    drawLabel(f'Score: {app.score}', 20, 15, size=20, fill='white', 
             align='left', bold=True)
    drawLabel(f'High Score: {app.highScore}', COLS * GRID_SIZE - 20, 15, 
             size=20, fill='white', align='right', bold=True)
    
    # ── WIN screen ──
    if app.won:
        # Semi-transparent dark backdrop
        drawRect(0, 0, COLS * GRID_SIZE, ROWS * GRID_SIZE,
                fill='black', opacity=60)
        
        # Confetti burst — seeded by winTimer so it animates each frame
        confettiColors = ['red','gold','cyan','magenta','lime','orange','white']
        random.seed(42)          # fixed seed so positions are stable per frame
        for i in range(60):
            # Each confetti piece gets a deterministic starting point at the top-center
            startX = COLS * GRID_SIZE // 2 + random.randint(-30, 30)
            startY = ROWS * GRID_SIZE // 2 - 60
            # Velocity spread
            vx = random.uniform(-3, 3)
            vy = random.uniform(0.5, 2.5)
            # Position at current winTimer
            cx = startX + vx * app.winTimer
            cy = startY + vy * app.winTimer
            # Only draw if still on screen
            if 0 < cx < COLS * GRID_SIZE and 0 < cy < ROWS * GRID_SIZE:
                color = confettiColors[i % len(confettiColors)]
                drawRect(cx, cy, 6, 6, fill=color, border='black', borderWidth=1)
        random.seed()            # restore random state
        
        # Banner box (oval behind rect fakes rounded corners)
        drawOval(bx + bannerW // 2, by + bannerH // 2, bannerW + 8, bannerH + 8,
                fill='darkGoldenRod')
        drawRect(bx, by, bannerW, bannerH, fill='gold', border='darkGoldenRod', borderWidth=4)
        
        drawLabel('Level Completed!', COLS * GRID_SIZE // 2, by + 40,
                 size=36, fill='darkRed', bold=True)
        # Score line
        drawLabel(f'Score: {app.score}', COLS * GRID_SIZE // 2, by + 80,
                 size=24, fill='black', bold=True)
        # Restart hint
        drawLabel('Press R to Play Again', COLS * GRID_SIZE // 2, by + 120,
                 size=18, fill='darkSlateGray')
    
    # ── GAME OVER screen ──
    elif app.gameOver:
        drawRect(0, 0, COLS * GRID_SIZE, ROWS * GRID_SIZE, 
                fill='black', opacity=80)
        drawLabel('GAME OVER', COLS * GRID_SIZE // 2, ROWS * GRID_SIZE // 2 - 40,
                 size=50, fill='white', bold=True)
        drawLabel(f'Score: {app.score}', COLS * GRID_SIZE // 2, 
                 ROWS * GRID_SIZE // 2 + 10, size=30, fill='white', bold=True)
        drawLabel('Press R to Restart', COLS * GRID_SIZE // 2, 
                 ROWS * GRID_SIZE // 2 + 50, size=25, fill='yellow')

def main():
    runApp(width=COLS*GRID_SIZE, height=ROWS*GRID_SIZE)

main()