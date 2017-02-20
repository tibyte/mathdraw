#!/usr/bin/python3

"""MathDraw - a virtual whiteboard

with batteries included.
"""
# Controls:
# lmb        =paint
# rmb        =erase
# mmb        =cycle colors
# arrow keys =move canvas
# t          =text input
# T          =cli input
# return     =finish text input
# double lmb =cycle colors

import time
import threading
import os, subprocess, sys # Using ps2pdf
import time # Filename
import socket
from threading import Thread

r = "#BB0000"
g = "#009900"
b = "#0000BB"
num = 0
color = [r, g, b]
arg0 = os.path.dirname(sys.argv[0])
filedir = arg0+"/" if len(arg0)>0 else ""

listenedText = ""
listenToText = False
textpos = [0, 0]
useLast = False
last = [0, 0]
pos = [0, 0]

sock = None
sfile = None
ms = None
serv = None
host = socket.gethostname()
try:
    host = os.environ["MATHDRAW"]
except:
    import server
    ms = server.MathServer()
    serv = Thread(target=ms.start, daemon=True)
    serv.start()

print("Using server:", host)
basetitle = "MathDraw 5 - {}".format(host)
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
for i in range(101):
    try:
        sock.connect((host, 8228+i))
        break
    except:
        continue
sfile = sock.makefile()

accmsg = sfile.readline()
if accmsg != 'accept\n':
    print("didn't receive an accept message")
    sys.exit(1)

def main():
    import tkinter
    global root
    global canv
    root = tkinter.Tk(className="mathdraw")
    root.title(basetitle)
    canv = tkinter.Canvas(root, width=1280, height=720, background="#fff")
    canv.pack()
    canv.bind("<Button-1>", paint)
    canv.bind("<B1-Motion>", paint)
    canv.bind("c", cycle)
    canv.bind("<Button-2>", cycle)
    canv.bind("<ButtonRelease-1>", release)
    canv.bind("<Leave>", release)
    canv.bind("<B3-Motion>", erase)
    root.bind("<Left>", mleft)
    root.bind("<Right>", mright)
    root.bind("<Up>", mup)
    root.bind("<Down>", mdown)
    root.bind("t", write)
    root.bind("T", cmdInput)
    root.bind("<Return>", enter)
    root.bind("<Key>", listenT)
    root.bind("<BackSpace>", removeT)
    root.bind("D", plotting)
    move()
    tkinter.mainloop()

def paint(event):
    global useLast
    x = int(canv.canvasx(event.x))
    y = int(canv.canvasy(event.y))
    if useLast:
        _paint(last[0], last[1], x, y, num % 3)
        sock.send('d:{}:{}:{}:{}:{}\n'.format(last[0], last[1], x, y, num % 3).encode('ascii'))
    else:
        pass
    last[0] = x
    last[1] = y
    useLast = True

def _paint(x1, y1, x2, y2, n):
    canv.create_line(x1, y1, x2, y2, fill=color[n], width=3)
    canv.create_oval(x1-1,y1-1,x1+1,y1+1, fill=color[num % 3], width=0)



def cycle(event):
    global num
    num = num + 1
    root.title(basetitle + " " + color[num%3])


def release(event):
    global useLast
    useLast = False


def mleft(event):
    canv.xview_scroll(-2, "pages")
    pos[0] -= 1280
    move()


def mright(event):
    canv.xview_scroll(2, "pages")
    pos[0] += 1280
    move()


def mup(event):
    canv.yview_scroll(-2, "pages")
    pos[1] -= 720
    move()


def mdown(event):
    canv.yview_scroll(2, "pages")
    pos[1] += 720
    move()

def _change(wx, wy):
    space = 4
    pos = "[{}, {}]".format(wx, wy)
    canv.create_rectangle(canv.canvasx(0), canv.canvasy(0), canv.canvasx(6 * len(pos) + 8), canv.canvasy(20), fill="#FFF", width=0)
    canv.create_text(canv.canvasx(space), canv.canvasy(space), text=pos, anchor="nw", fill="#000")

def move():
    _change(int(pos[0]/1280), int(pos[1]/720))

def erase(event):
    x = int(canv.canvasx(event.x))
    y = int(canv.canvasy(event.y))
    sock.send('e:{}:{}\n'.format(x,y).encode('ascii'))
    _erase(x, y)

def _erase(x, y):
    s = 20
    canv.create_oval(x - s, y - s, x + s, y + s, fill="white", outline="white")

def write(event):
    global listenToText
    global listenedText
    global textpos
    if listenToText:
        listenT(event)
        return
    listenToText = True
    textpos[0] = event.x
    textpos[1] = event.y
    print("Listening to Text")


def enter(event):
    global listenToText
    if listenToText:
        listenToText = False
        writeOut()


def writeOut():
    global listenedText
    x = int(canv.canvasx(textpos[0]))
    y = int(canv.canvasy(textpos[1]))
    _writeOut(x, y, listenedText)
    sock.send('t:{}:{}:{}\n'.format(x, y, listenedText).encode('ascii'))
    listenedText = ""
    print("\nText written")

def _writeOut(x, y, t):
    canv.create_text(x, y, text=t, font="\"Times New Roman\" 18 bold")


def listenT(event):
    global listenedText
    listenedText += event.char
    if listenToText:
        print("\033[1024D", end="")
        print(listenedText, end="")
        sys.stdout.flush()
    else:
        listenedText = ""


def removeT(event):
    global listenedText
    listenedText = listenedText[:-1]
    print("\033[1D \033[1D", end="")
    sys.stdout.flush()


def cmdInput(event):
    global listenToText
    global listenedText
    if listenToText:
        listenT(event)
        return
    t = str(input("Text:"))
    x = int(canv.canvasx(event.x))
    y = int(canv.canvasy(event.y))
    sock.send('t:{}:{}:{}\n'.format(x, y, t).encode('ascii'))
    _writeOut(x, y, t)

def plotting(event):
    print("plotting not implemented")

def sock_receive():
    try:
        while True:
            msg = sfile.readline()[:-1]
            mspl = msg.split(":")
            if msg[0] == 'e':
                #e:x:y
                _erase(int(mspl[1]), int(mspl[2]))
            elif msg[0] == 'd':
                #d:x1:y1:x2:y2:num
                _paint(int(mspl[1]), int(mspl[2]), int(mspl[3]), int(mspl[4]), int(mspl[5]))
            elif msg[0] == 't':
                #t:x:y:text
                _writeOut(int(mspl[1]), int(mspl[2]), mspl[3])
            else:
                print("unknown server response")
    except:
        print("return client receive")
        return

if __name__ == '__main__':
    Thread(target=sock_receive).start()
    try:
        main()
    except KeyboardInterrupt:
        pass
    except:
        pass
    sock.send(b'close\n')
    if ms != None:
        ms.close()
    sys.exit(0)
