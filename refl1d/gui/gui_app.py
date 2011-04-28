# Copyright (C) 2006-2011, University of Maryland
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/ or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
# Author: James Krycka

"""
This module creates the GUI for the Refl1D Reflectometry Modeler application.
It builds the initial wxPython frame, presents a splash screen to the user,
and then constructs the rest of the GUI.

From the command line, the application is run from a startup script that calls
the main function of this module.  From the root directory of the package, you
can run this application in GUI mode as follows:

$ python bin/refl1d_gui [<optional parameters>]

The following is a list of command line parameters for development and
debugging purposes.  None are documented and they may change at any time.

Options for showing diagnostic info:
    --platform      Display platform specific info, especially about fonts
    --syspath       Display the contents of sys.path
    --time          Display diagnostic timing information

Options for overriding the default font and point size attributes where
parameters within each set are mutually exclusive (last one takes precedence):
    --arial, --tahoma, --verdana
    --6pt, --7pt, --8pt, --9pt, --10pt, --11pt, --12pt

Options for controlling the development and testing environment:
    --inspect       Run the wxPython Widget Inspection Tool in a debug window
"""

#==============================================================================

import os
import sys
import time

import wx

from .about import APP_TITLE
from .utilities import (get_appdir, get_datadir, get_rootdir,
                        get_rootdir_parent, log_time)

# Defer import of AppFrame until after the splash screen has been displayed.
# When running for the first time (where imported modules are not in cache),
# importing AppFrame can take several seconds because it results in importing
# matplotlib, numpy, and most application modules.
### from .app_frame import AppFrame

# Desired initial application frame size (if physical screen size permits).
FRAME_WIDTH = 1200
FRAME_HEIGHT = 900

# Desired plash screen size and other information.
# Note that it is best to start with an image having the desired dimensions or
# larger.  If image is smaller the image conversion time may be noticeable.
SPLASH_FILE = "refl1d_splash.jpg"
SPLASH_TIMEOUT = 3000  # in miliseconds
SPLASH_WIDTH = 720
SPLASH_HEIGHT = 540

# Diagnostic timing information.
LOGTIM = True if (len(sys.argv) > 1 and '--time' in sys.argv[1:]) else False

#==============================================================================

class Refl1dGUIApp(wx.App):
    """
    This class builds the wxPython GUI for the Refl1D Reflectometry Modeler
    application.

    First a splash screen is displayed, then the application frame is created
    but not shown until the splash screen exits.  The splash screen remains
    active while the application frame is busy initializing itself (which may
    be time consuming if many imports are performed and the data is not in the
    system cache, e.g., on running the application for the first time).  Only
    when initialization of the application is complete and control drops into
    the wx event loop, can the splash screen terminate (via timeout or a mouse
    click on the splash screen) which causes the frame to be made visible.
    """

    def OnInit(self):
        # Determine the position and size of the splash screen based on the
        # desired size and screen real estate that we have to work with.
        pos, size = self.window_placement(SPLASH_WIDTH, SPLASH_HEIGHT)
        #print "splash pos and size =", pos, size

        # Display the splash screen.  It will remain visible until the caller
        # executes app.MainLoop() AND either the splash screen timeout expires
        # or the user left clicks over the splash screen.
        if LOGTIM: log_time("Starting to display the splash screen")
        pic = os.path.join(get_datadir(), SPLASH_FILE)
        self.display_splash_screen(img_name=pic, pos=pos, size=size)

        # Determine the position and size of the application frame based on the
        # desired size and screen real estate that we have to work with.
        pos, size = self.window_placement(FRAME_WIDTH, FRAME_HEIGHT)
        #print "frame pos and size =", pos, size

        # Create the application frame, but it will not be shown until the
        # splash screen terminates.  Note that import of AppFrame is done here
        # while the user is viewing the splash screen.
        if LOGTIM: log_time("Starting to build the GUI application")

        from .app_frame import AppFrame

        self.frame = AppFrame(parent=None, title=APP_TITLE, pos=pos, size=size)

        # Declare the application frame to be the top window.
        self.SetTopWindow(self.frame)

        # To have the frame visible behind the spash screen, comment out the
        # line below.
        #self.frame.Show(True)

        # To test that the splash screen will not go away until the frame
        # initialization is complete, simulate an increase in startup time
        # by taking a nap.
        #time.sleep(6)

        return True

    def window_placement(self, desired_width, desired_height):
        """
        Determines the position and size of a window such that it fits on the
        user's screen without obstructing (or being obstructed by) the task bar.
        The returned size is bounded by the desired width and height passed in,
        but it may be smaller if the screen is too small.  Usually the returned
        position (upper left coordinates) will result in centering the window
        on the screen excluding the task bar area.  However, for very large
        monitors it will be placed on the left side of the screen.
        """

        # WORKAROUND: When running Linux and using an Xming (X11) server on a
        # PC with a dual monitor configuration, the reported display count may
        # be 1 (instead of 2) with a display size of both monitors combined.
        # (For example, on a target PC with an extended desktop consisting of
        # two 1280x1024 monitors, the reported monitor size was 2560x1045.)
        # To avoid displaying the window across both monitors, we check for
        # screen 'too big'.  If so, we assume a smaller width which means the
        # application will be placed towards the left hand side of the screen.

        x, y, w, h = wx.Display().GetClientArea() # size excludes task bar
        #print "*** x, y, w, h", x, y, w, h
        xpos, ypos = x, y
        h -= 20  # to make room for Mac window decorations
        if len(sys.argv) > 1 and '--platform' in sys.argv[1:]:
            j, k = wx.DisplaySize()  # size includes task bar area
            print "*** Reported screen size including taskbar is %d x %d"%(j, k)
            print "*** Reported screen size excluding taskbar is %d x %d"%(w, h)

        if w > 1920: w = 1280  # display on left side, not centered on screen
        if w > desired_width:  xpos = x + (w - desired_width)/2
        if h > desired_height: ypos = y + (h - desired_height)/2

        # Return the suggested position and size for the application frame.
        return (xpos, ypos), (min(w, desired_width), min(h, desired_height))

    def display_splash_screen(self, img_name=None, pos=None, size=(320, 240)):
        """Displays a splash screen and the specified position and size."""

        # Prepare the picture.
        w, h = size
        image = wx.Image(img_name, wx.BITMAP_TYPE_JPEG)
        image.Rescale(w, h, wx.IMAGE_QUALITY_HIGH)
        bm = image.ConvertToBitmap()

        # Create and show the splash screen.  It will disappear only when the
        # program has entered the event loop AND either the timeout has expired
        # or the user has left clicked on the screen.  Thus any processing
        # performed by the calling routine (including doing imports) will
        # prevent the splash screen from disappearing.
        splash = wx.SplashScreen(bitmap=bm,
                                 splashStyle=(wx.SPLASH_TIMEOUT|
                                              wx.SPLASH_CENTRE_ON_SCREEN),
                                 style=(wx.SIMPLE_BORDER|
                                        wx.FRAME_NO_TASKBAR|
                                        wx.STAY_ON_TOP),
                                 milliseconds=SPLASH_TIMEOUT,
                                 parent=None, id=wx.ID_ANY)
        splash.Bind(wx.EVT_CLOSE, self.OnCloseSplashScreen)

        # Repositon if center of screen placement is overridden by caller.
        if pos is not None:
            splash.SetPosition(pos)
        splash.Show()

    def OnCloseSplashScreen(self, event):
        """
        Make the application frame visible when the splash screen is closed.
        """

        # To show the frame earlier, uncomment Show() code in OnInit.
        if LOGTIM: log_time("Terminating the splash screen and showing the GUI")
        self.frame.Show(True)
        event.Skip()

#==============================================================================

def inspect():
    import wx.lib.inspection
    wx.lib.inspection.InspectionTool().Show()
    
def main():
    if LOGTIM: log_time("Starting Refl1D")

    # Instantiate the application class and give control to wxPython.
    app = Refl1dGUIApp(redirect=False, filename=None)

    from .. import cli
    cli.FitOpts.FLAGS |= set(('inspect','syspath'))
    opts = cli.getopts()
    
    # For wx debugging, load the wxPython Widget Inspection Tool if requested.
    # It will cause a separate interactive debugger window to be displayed.
    if opts.inspect:
        import wx.lib.inspection
        wx.lib.inspection.InspectionTool().Show()

    if opts.syspath:
        print "*** Application directory is:   ", get_appdir()
        print "*** Data directory is:          ", get_datadir()
        print "*** Package root directory is:  ", get_rootdir()
        print "*** Parent of root directory is:", get_rootdir_parent()
        print "*** Python path is:"
        for i, p in enumerate(sys.path):
            print "%5d  %s" %(i, p)

    # Argument processing
    model = cli.initial_model(opts)
    if model:
        app.frame.panel.set_model(model=model)

    # Enter event loop which allows the user to interact with the application.
    if LOGTIM: log_time("Entering the event loop")
    app.MainLoop()
