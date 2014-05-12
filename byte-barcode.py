#!/usr/bin/env python

import Tkinter as tk
import ttk
from PIL import Image, ImageTk
from time import sleep, strftime
import signal

yesno = lambda t: t and "y" or "n"

class App(ttk.Frame):
    W,H = 30,60  #ui displays barcode images at this rescale factor
    dbg_ui = False
    dbg_key = False
    helptext = "\n"+(('='*13)+"\nByte-Barcode\n"+('='*13)+"\n\n"
    "Generate barcode images and a printable .pdf from byte values\n\n"
    "  <arrows>\tScroll through barcode images\n"
    "  1-9\t\tCheck/uncheck options\n"
    "  e\t\tExport images/[0-255].bmp, barcodes.pdf\n"
    "  o\t\tOpen barcodes.pdf\n"
    "  q\t\tExit\n")

    def __init__(self, root):
        ttk.Frame.__init__(self, root)   

        self.root = root
        self.byteCombo = None

        # variables bound to widgets
        self.byteComboStr = tk.StringVar()
        self.pdfBorderOn =  tk.BooleanVar()
        self.pdfLabelOn =   tk.BooleanVar()
        self.imgLeadBitOn = tk.BooleanVar()
        self.pdfBorderOn.set(True)
        self.pdfLabelOn.set(True)
        self.imgLeadBitOn.set(True)
        self.pdfBorderOn.trace('w', self.pdf_change)
        self.pdfLabelOn.trace('w', self.pdf_change)
        self.imgLeadBitOn.trace('w', self.img_change)
        self.byteComboStr.trace('w', self.byte_change)
        
        # initial values
        self.imWidth = 8
        self.imgArr = [None]*256
        self.byteStrings = [""]
        self.strings_generate()
        self.activeByte = ord('A')
        self.byteComboStr.set(self.byteStrings[self.activeByte])
        self.pdfReady = False
        self.imgReady = False

        # ui
        self.ui()

        # keyboard/mouse bindings
        root.bind_all('<Key>', self.key_handler)
        self.prevBtn.bind("<Button-1>", self.prev_byte)
        self.nextBtn.bind("<Button-1>", self.next_byte)
        self.byteCombo.bind('<<ListboxSelect>>', self.byte_change)

        # start
        self.img_change()
        self.export(openPdf=False)
        print App.helptext
        root.grab_set() # grab focus back from terminal
        
    def ui(self):
        self.style = ttk.Style()
        self.style.theme_use("default")
        
        # formatting
        mainFrame = ttk.Frame(self, relief=tk.RAISED, borderwidth=1)
        frame1=ttk.Frame(mainFrame,height=100,width=400)

        self.imageLbl = ttk.Label(mainFrame)
        self.imageLbl.image = Image.new('L',(self.imWidth*App.W,App.H))
        self.imageLbl.image = ImageTk.PhotoImage(self.imageLbl.image)
        self.imageLbl.configure(image=self.imageLbl.image)

        sep = ttk.Separator(mainFrame, orient=tk.HORIZONTAL)
        frame2=ttk.Frame(mainFrame)

        # pack
        frame1.pack(fill=tk.NONE, anchor=tk.CENTER, expand=1, pady=5)
        self.imageLbl.pack(anchor=tk.CENTER, pady=5)
        sep.pack(fill=tk.X, padx=5, pady=5)
        frame2.pack(fill=tk.BOTH, expand=1)
        mainFrame.pack(fill=tk.BOTH, expand=1)
        self.pack(fill=tk.BOTH, expand=1)

        # widgets
        self.prevBtn = ttk.Label(frame1, text=" << ")
        self.byteCombo = ttk.Combobox(frame1, textvariable=self.byteComboStr,
            state='readonly', justify=tk.CENTER, font="TkFixedFont")
        self.byteCombo['values'] = self.byteStrings
        self.nextBtn = ttk.Label(frame1, text=" >> ")
        self.bitCbx = ttk.Checkbutton(frame2, text="Barcode: Add Leading '10'", 
            variable=self.imgLeadBitOn)
        self.borderCbx = ttk.Checkbutton(frame2, text="PDF borders", 
            variable=self.pdfBorderOn)
        self.labelCbx = ttk.Checkbutton(frame2, text="PDF labels", 
            variable=self.pdfLabelOn)
        self.closeBtn = ttk.Button(self, text="Close", command=self.close)
        self.exportBtn = ttk.Button(self, text="Export images, PDF", 
            command=self.export)
        self.progressLbl = ttk.Label(self, text="")
        
        # pack
        self.prevBtn.pack(side=tk.LEFT)
        self.byteCombo.pack(side=tk.LEFT)
        self.nextBtn.pack(side=tk.LEFT)
        self.bitCbx.pack(side=tk.LEFT, padx=5, pady=5)
        self.borderCbx.pack(side=tk.LEFT, padx=5, pady=5)
        self.labelCbx.pack(side=tk.LEFT, padx=5, pady=5)
        self.closeBtn.pack(side=tk.RIGHT, padx=5, pady=5)
        self.exportBtn.pack(side=tk.RIGHT, padx=5, pady=5)
        self.progressLbl.pack(side=tk.LEFT, padx=5, pady=5)

    def key_handler(self, event):
        if App.dbg_key: print "key:", event.keysym, "...",
        if (event.keysym=="Left"): #,"Down"
            self.prev_byte()
        elif (event.keysym=="Right"): #,"Up"
            self.next_byte()
        elif (event.char=="q" or event.keysym=="Escape"):
            self.close()
        elif event.char=="1":
            if App.dbg_key: print "Leading bit toggle"
            self.imgLeadBitOn.set(not(self.imgLeadBitOn.get()))
        elif event.char=="2":
            if App.dbg_key: print "PDF Border toggle"
            self.pdfBorderOn.set(not(self.pdfBorderOn.get()))
        elif event.char=="3":
            if App.dbg_key: print "PDF Label toggle"
            self.pdfLabelOn.set(not(self.pdfLabelOn.get()))
        elif event.char=="e":
            self.export()
        elif event.char=="o":
            self.pdf_open()
        else:
            if App.dbg_key: print ""

    def close(self):
        if App.dbg_ui: print "app: close()"
        self.root.quit()

    def next_byte(self, *args):
        self.set_byte(self.activeByte+1)
        if App.dbg_ui: print "Next code (%d)"%(self.activeByte)
        self.img_display()

    def prev_byte(self, *args):
        self.set_byte(self.activeByte-1)
        if App.dbg_ui: print "Previous code (%d)"%(self.activeByte)

    def set_byte(self, x):
        # set self.activeByte and the combobx value
        if App.dbg_ui: print "app: set_byte(%d)"%(x)
        self.activeByte = min(255,max(0,x))
        if self.byteCombo==None: return
        self.byteCombo.current(self.activeByte)

    def byte_change(self, *args):
        # update activeByte with the value in the combobox; update the image
        if App.dbg_ui: print "app: byte_change()"
        if self.byteCombo==None: return
        idx = self.byteCombo.current()
        self.set_byte(idx)
        self.img_display()

    def config_print(self):
        if App.dbg_ui: print "app: config_print()"
        # print configuration state
        print "Export @ %s:"%(strftime('%X %x %Z'))
        print "  %c\tBarcode: Add Leading '10'"%(yesno(self.imgLeadBitOn.get()))
        print "  %c\tPDF: borders"%(yesno(self.pdfBorderOn.get()))
        print "  %c\tPDF: labels"%(yesno(self.pdfLabelOn.get()))

    def strings_generate(self):
        if App.dbg_ui: print "app: strings_generate()"
        # generate a list of strings representing each byte
        cStr = ("NUL SOH STX ETX EOT ENQ ACK BEL BS TAB LF VT FP CR SO SI "
        "DLE DC1 DC2 DC3 DC4 NAK SYN ETB CAN EM SUB ESC FS GS RS US "
        "Space").split(' ')
        cStr += ["'%c'"%chr(x) for x in xrange(33,127)]
        cStr += ["DEL"]
        cStr += ["-?-" for x in xrange(128,256)]
        self.byteStrings=["%.3d \\x%.2x %s"%(x,x,cStr[x]) for x in xrange(256)]

    def img_generate(self):
        if App.dbg_ui: print "app: img_generate()"
        # repopulate images (in memory, not on disk)
        for i in xrange(256):
            self.progressLbl.configure(text="Image %d of 256"%i)
            self.progressLbl.update()
            self.imgArr[i] = Image.new('L', (self.imWidth,1))
            pixelVector = bin(i)[2:].zfill(8)
            pixelVector = [c=='0' and 255 or 0 for c in pixelVector]
            if self.imWidth==10: pixelVector=[0,255]+pixelVector
            if not (self.imWidth in (8,10)):
                raise ValueError("App.imWidth not in (8,10)")
            #print pixelVector
            pixels = self.imgArr[i].load()
            for j in xrange(self.imWidth): pixels[j,0] = pixelVector[j]
            #self.imgArr[i].save('img/%d.png'%(i))
        self.progressLbl.configure(text="")
        self.progressLbl.update()
        self.imgReady = True

    def img_display(self):
        """update displayed barcode image"""
        if App.dbg_ui: print "app: img_display()"
        if self.imageLbl==None: return
        imBig = self.imgArr[self.activeByte]
        imBig = imBig.resize((self.imWidth*App.W,App.H), Image.NEAREST)
        self.imageLbl.image = ImageTk.PhotoImage(imBig)
        self.imageLbl.configure(image=self.imageLbl.image)
        #imBig.save('display.png')

    def img_change(self,*args):
        if App.dbg_ui: print "app: img_change()"
        self.imWidth = 8 + 2*self.imgLeadBitOn.get()
        self.img_generate() # generate images
        self.img_display()  # display images
        self.pdf_generate() # regenerate pdf (depends on this)

    def img_out(self):
        if App.dbg_ui: print "app: img_out()"
        if self.imgReady==False: return False
        # ensure folder path exists
        # write images & print progress
        for i in xrange(256):
            self.progressLbl.configure(text="images/%d.bmp"%i)
            self.progressLbl.update()
        self.progressLbl.configure(text="")
        self.progressLbl.update()
        print "Saved: /.../images/*.bmp"
#TODO

    def pdf_generate(self):
        if App.dbg_ui: print "app: pdf_generate()"
        # generate pdf
        self.progressLbl.configure(text="Generating PDF")
        self.progressLbl.update()
        sleep(0.5)
        self.progressLbl.configure(text="")
        self.progressLbl.update()
        self.pdfReady = True
#TODO

    def pdf_change(self,*args):
        if App.dbg_ui: print "app: pdf_change()"
        self.pdf_generate() # generate pdf

    def pdf_out(self):
        if App.dbg_ui: print "app: pdf_out()"
        if self.pdfReady==False: return False
        # ensure folder path exists
        # write pdf & print result
        self.progressLbl.configure(text="barcodes.pdf")
        self.progressLbl.update()
        sleep(0.5)
        self.progressLbl.configure(text="")
        self.progressLbl.update()
        print "Saved: /.../___.pdf"
#TODO

    def pdf_open(self):
        if App.dbg_ui: print "app: pdf_open()"
        # dialog box; open PDF file (os-specific action)
        if self.pdfReady==False: return False
        print "Opening: /.../___.pdf"
#TODO

    def export(self, openPdf=True):
        self.exportBtn.config(state='disabled') # disable button
        if App.dbg_ui: print "app: export()"
        self.exportBtn.update()
        self.config_print() # list configuration
        # regenerating images,pdf not needed - done on tickbox change
        self.img_out() # export images
        self.pdf_out() # export pdf
        if openPdf: self.pdf_open() # open PDF
        self.exportBtn.config(state='normal') # enable button
        self.exportBtn.update()
        print ""

#======================================================================

def main():

    def sigint_handler(signum, frame):
        print "Keyboard or Signal interrupt"
        root.quit()

    def root_poll(): root.after(50, root_poll)

    root = tk.Tk()
    root.geometry("+%d+%d"%(0,0))
    root.wm_title("Byte-Barcode")
    root.resizable(width=False, height=False)
    root.after(50, root_poll)

    signal.signal(signal.SIGINT, sigint_handler)

    app = App(root)
    root.mainloop()  

if __name__ == '__main__':
    main()  

#======================================================================

#TODO
"""
pdf_change: add/remove image border in gui
change combobox to listbox: http://www.tkdocs.com/tutorial/morewidgets.html
add search boxes for int/hex/char for listbox
pdf_out: add dialog box for filename
split non-gui functionality out into the lib/bytebarcode.py file
cut down on global vars; callbacks if possible
"""
