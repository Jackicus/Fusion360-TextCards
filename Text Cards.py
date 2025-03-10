import json
import adsk.core, adsk.fusion, traceback
from dataclasses import dataclass

'''     ⚙️ Application locations                ''' 
app         = adsk.core.Application.get()       # Main: 
ui          = app.userInterface                 # 🖥️ Interface
design      = app.activeProduct                 # 🛠️ Design
'''     📂 Project References                   '''
rootComp    = design.rootComponent              # Root:
sketches    = rootComp.sketches                 # 🖼️ Sketch       .add(profile)                   
extrudes    = rootComp.features.extrudeFeatures # 📦 Extrudes     .addSimple(prof, dist, op_type) 
'''     🍞 Features                             '''
Point       = adsk.core.Point3D                 # 📍 Point        .create(x, y, z)        
ValueInput  = adsk.core.ValueInput              # 📏 ValueInput   .createByReal(distance) 
xyPlane     = rootComp.xYConstructionPlane      # 📐 (XYPlane)    Construction
'''     🍞 Operations                           '''
NewBody     = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
JoinBody    = adsk.fusion.FeatureOperations.JoinFeatureOperation

class Card:         # (0,0,0), (5,5,0), 0.8, profile
    ''' 📍 Two point rectangle:    
        📦 Extrude distance:       '''    
    def __init__(self, startpoint, endpoint, distance, borderOffset = 0.1, borderdistance = 0.08, profile=xyPlane):
        '''SKETCH: '''
        self.sketch = sketches.add(profile)          # NEW SKETCH
        '''RECTANGLE: '''
        self.startPoint = Point.create(*startpoint)  # START
        self.endPoint = Point.create(*endpoint)      # END 
        self.draw_rectangle()
        rectprofile = self.sketch.profiles.item(0)  # Get profile from sketch
        ''' EXTRUDE: '''
        self.distance = ValueInput.createByReal(distance) 
        
        self.cardBody = extrudes.addSimple(rectprofile, self.distance, NewBody)    
        '''BORDER'''
        self.borderDistance = ValueInput.createByReal(distance+borderdistance)
        self.borderOffset = borderOffset
        borderprofile = self.add_border()
        
        ''' FEATURES: '''
        self.profile    = self.cardBody.endFaces.item(0) # END FACE
        self.sketch     = sketches.add(self.profile)
        
    def draw_rectangle(self):
        '''Draws a Two Point Rectangle'''
        lines = self.sketch.sketchCurves.sketchLines
        lines.addTwoPointRectangle(self.startPoint, self.endPoint)

    def add_border(self, ):
        '''Creates a inside border on the card'''
        sketch = self.sketch
        # Expand dimensions by border thickness
        borderStart = Point.create(self.startPoint.x    + self.borderOffset,    self.startPoint.y   + self.borderOffset, 0)
        borderEnd   = Point.create(self.endPoint.x      - self.borderOffset,    self.endPoint.y     - self.borderOffset, 0)
        # Draw border rectangle
        sketch.sketchCurves.sketchLines.addTwoPointRectangle(borderStart, borderEnd)

        # Get the new profile and extrude as a thin frame
        borderProfile = sketch.profiles.item(0)
        extrudes.addSimple(borderProfile, self.borderDistance, JoinBody)


class Textline:
    '''Holds a list of textboxes arranged as a line'''
    def __init__(self, entry, card, distance=0.08, 
                 textSize = 0.6, firstLineTextSize = 1.4, secondLineTextSize = 0.45
                 ):
        # Text line to be placed
        self.card = card
        # Content for the text line
        self.entry = entry.fields
        # Measurements
        self.distance = adsk.core.ValueInput.createByReal(distance)
        self.textSize = textSize
        self.firstLineTextSize = firstLineTextSize
        self.secondLineTextSize = secondLineTextSize
        # Make textboxes
        self.lines = self.make_entry_line()
        # Adjust Sizes
        self.set_line_equal_spacing()
        self.set_text_sizes()
        # Add to Sketch / Extrude
        self.textprofiles = self.draw_lines()
        self.textextrudes = self.create_textline()
 
    def set_text_sizes(self):
        for i, line in enumerate(self.lines):
            textsize = self.textSize
            if i == 0:
                textsize = self.firstLineTextSize
            if i == 1: 
                textsize = self.secondLineTextSize
            for tb in line:
                tb.input.size = textsize

            
    def set_line_equal_spacing(self):
        # Left / Right for textboxes in a line
        for line in self.lines:
            if len(line) > 1:  # Only adjust if more than one textbox
                space = 1 / len(line)
                left = 0
                right = 1
                for i, tb in enumerate(line):
                    right -= space
                    tb.padding.left  = left
                    tb.padding.right = right
                    left += space
    
    def draw_lines(self):
        '''Draw text on the sketch and collect profiles'''
        lineProfiles = adsk.core.ObjectCollection.create()
        for line in self.lines:
            for tb in line:
                lineProfiles.add(tb.draw_text(self.card.profile, self.card.sketch))
        return lineProfiles

    def create_textline(self):
        '''Draw text and extrude it'''
        self.textprofiles = self.draw_lines()
        self.extrude = extrudes.addSimple(self.textprofiles, self.distance, JoinBody)

    def make_entry_line(self, size=0.6, spacing=(0.6,0.18,0.18), lrpadding=(0.02, 0.02)):
        '''Makes a line from an entry with spacings'''
        listit = []
        paddings = self.calculate_padding_from_spacings(spacing, lrpadding)
        for i, field in enumerate(self.entry):
            padding = paddings[i]
            if isinstance(field, str):
                listit.append([Textline.Textbox((field, size), padding)])
            elif isinstance(field, list):
                sublist = [Textline.Textbox((sub, size), padding) for sub in field]
                listit.append(sublist)
        return listit

    def calculate_padding_from_spacings(self, spacing, lrpad):
        '''Calculate paddings from spacings'''
        listsizes = []
        total_spacing = sum(spacing)
        if total_spacing > 1:
            raise ValueError("Total spacing exceeds 1")
        startsize = (1 - total_spacing) / 2  # Center vertically
        left, right = lrpad
        for item in spacing:
            top = startsize
            bot = 1 - (startsize + item)
            listsizes.append((top, bot, left, right))
            startsize += item
        return listsizes

    class Textbox:      
        def __init__(self, input=("Text!", 0.6), padding=(0.05, 0.05, 0.05, 0.05)):
            '''TEXT INPUT DETAILS'''
            self.input = Textline.Textbox.Input(*input)
            self.padding = Textline.Textbox.Padding(*padding)

        def draw_text(self, profile, sketch):
            # Text, Size, Fonts
            text = sketch.sketchTexts.createInput2(self.input.text, self.input.size)  # String passed here
            text.fontName = self.input.font
            # Position & Alignments
            start, end = self.padding.convert_to_start_end_points(profile)
            text.setAsMultiLine(start, end, self.input.vAlign, self.input.hAlign, 0.8)  # Multiline text
            return sketch.sketchTexts.add(text)
        
        class Input:
            '''Textbox item input'''
            @staticmethod
            def align_select(alignmentString):
                va = adsk.core.VerticalAlignments
                ha = adsk.core.HorizontalAlignments       
                aligns = {  
                    'center': ha.CenterHorizontalAlignment,
                    'left': ha.LeftHorizontalAlignment,
                    'right': ha.RightHorizontalAlignment, 
                    'top': va.TopVerticalAlignment,
                    'middle': va.MiddleVerticalAlignment,
                    'bottom': va.BottomVerticalAlignment }
                return aligns[alignmentString]

            def __init__(self, text, size=0.6, font='Arial', hAlign='center', vAlign='middle'):
                self.text = str(text)  # Always a string
                self.size = size
                self.font = font
                self.hAlign = self.align_select(hAlign)
                self.vAlign = self.align_select(vAlign)

        class Padding:
            ''' Space between the profile edges
                Multiplier of the profiles lengths  '''
            def __init__(self, top=0.1, bottom=0.1, left=0.1, right=0.1):
                # Spaces
                self.top    = top
                self.bottom = bottom
                self.left   = left
                self.right  = right

            def profile_start_end(self, profile):
                # Get Start End Points
                start = profile.boundingBox.minPoint  # 3D Point
                end = profile.boundingBox.maxPoint    # 3D Point
                return start, end

            def profile_lengths(self, profile): 
                # Get XY Lengths
                start, end = self.profile_start_end(profile)
                xlen = end.x - start.x     # - Longest X distance
                ylen = end.y - start.y     # - Longest Y distance 
                return xlen, ylen
            
            def convert_to_start_end_points(self, profile):                 
                # Start and end adjusted by padding of lengths
                start, end = self.profile_start_end(profile)
                xlen, ylen = self.profile_lengths(profile)
                z = 0   # Z stays zero
                # Start point
                x = start.x + (self.left * xlen)
                y = start.y + (self.bottom * ylen)
                startpoint = Point.create(x, y, z)
                # End point
                x = end.x - (self.right * xlen)
                y = end.y - (self.top * ylen)
                endpoint = Point.create(x, y, z)
                return startpoint, endpoint 

class Table:
    class Entry:
        '''Single entry from a table.'''
        def __init__(self, line, file):
            '''Line of a file'''
            self.file = file
            self.line = line
            self.rawfields = self.get_entry()
            self.fields = self.get_field()

        def get_field(self):
            # Fields as lists [[][][]]
            listOfFields = []
            for field in self.rawfields:
                if isinstance(field, list):
                    listOfFields.append(field)
                if isinstance(field, str):
                    listOfFields.append([field])
            return listOfFields

        def get_entry(self):
            # Open file and get entry
            with open(self.file, 'r', encoding='utf-8') as file:
                file = json.load(file)
                entry = file[self.line]
                attributes = [value for key, value in entry.items()]
                return attributes

def run(context):
    ui = adsk.core.Application.get().userInterface
    try:
        # CARD DETAILS INPUT
        # ui.messageBox("FIRST: Setup Cards!")
        # x = ui.inputBox("Enter Card X position", "CARD Settings")
        # x = ui.messageBox(x)
        # y = ui.inputBox("Enter Card Y position", "CARD Settings")
        # distance = ui.inputBox("Enter Card Thickness:", "TEXT Settings")
        
        # TEXT DETAILS INPUT
        #ui.messageBox("SECOND: Setup the text!")
        #firstline = ui.inputBox("Enter TEXT SIZE for the FIRST line:", "TEXT Settings")
        #otherlines = ui.inputBox("Enter TEXT SIZE for the all other lines:", "TEXT Settings")
        #faturedistance = ui.inputBox("Enter Text Thickness:", "TEXT Settings")

        # BORDER DETAILS INPUT
        #ui.messageBox("THIRD: Setup the Border!")
        #borderOffset = ui.inputBox("Enter OFFSET for the BORDER:", "BORDER Settings")

        # ENTRY SETTINGS
        #ui.messageBox("FINALLY: Select the range of entries")
        #start = ui.inputBox("START LINE:", "ENTRY Settings")
        #end = ui.inputBox("END LINE:", "ENTRY Settings")
        

        # PATH
        path = 'C:/Users/jackt/OneDrive/Fusion 360 Scripts/Text Cards/setText.json'

        featureThick = 0.06
        borderOffset = 0.1
        linesize = 0.6
        firstLineSize = 1.5
        build = 20

        class xyz:
            def __init__(self, x, y, z):
                self.x = x
                self.y = y
                self.z = z
            
            def to_tuple(self):
                return (self.x, self.y, self.z)
            
            def increase(self, xyz):
                # size increases
                xx, yy, zz = xyz.to_tuple()
                self.x = self.x + xx
                self.y = self.y + yy
                self.z = self.z + zz
            
            def moveHorizontal(self, size, gap=(0, 0, 0)):
                if not isinstance(gap, xyz):
                    gap = xyz(*gap)
                # Move across
                self.x = self.x + size.x + gap.x
            
            def moveVertical(self, size, gap=(0, 0, 0)):
                if not isinstance(gap, xyz):
                    gap = xyz(*gap)
                # Move up
                self.y = self.y + size.y + gap.y
            
            def moveUp(self, size, gap=(0, 0, 0)):
                if not isinstance(gap, xyz):
                    gap = xyz(*gap)
                # Incase ye feelin’ freaky
                self.z = self.z + size.z + gap.z
        
        # PATH
        path = 'C:/Users/jackt/OneDrive/Fusion 360 Scripts/Text Cards/setText.json'

        featureThick = 0.06
        borderOffset = 0.1
        linesize = 0.54
        firstLineSize = 1.5
        secondLineSize = 0.42

        cardsize = xyz(4.3, 4.3, 0.06)
        cardThick = cardsize.z
        
        bounds = xyz(22, 22, 20) #  build plater essentially
        gaps = xyz(0.1, 0.1, 0.6) # space given between cards
        start = xyz(0, 0, 0)
        end = xyz(0, 0, 0)

        end.moveHorizontal(cardsize)  # Start with end shifted right instead o’ up
        for linenum in range(0, 100):
            
            if end.y + cardsize.y >= bounds.y:  # Check y-bound instead o’ x
                # Increase X on bounds (swap from Y)
                start.moveHorizontal(cardsize, gaps)  # Shift right, not up
                end.moveHorizontal(cardsize, gaps)    # Shift right, not up
                start.y = 0                           # Reset y, not x

            # Move end to size
            end.y = start.y                         # Align y, not x
            end.moveVertical(cardsize)              # Move up, not across
            card = Card(start.to_tuple(), end.to_tuple(), cardThick, borderOffset, featureThick)
            textline = Textline(
                Table.Entry(linenum, path), 
                card, featureThick, linesize, firstLineSize, secondLineSize)
            # Move start up size with a gap (swap from across)
            start.moveVertical(cardsize, gaps)




   
    except:
        ui.messageBox(f"Failed:\n{traceback.format_exc()}")