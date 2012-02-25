import asyncore, asynchat
import os, string
import sys
import appuifw
try: # next lines important for select_access_point()
	sys.modules['socket'] = __import__('btsocket')
except ImportError:
	pass
import socket
import e32
import struct
import StringIO, mimetools
import time, datetime, ftplib
import thread

appuifw.app.orientation = 'landscape'
import camera  # must be after "landscape"

app_lock = e32.Ao_lock()

ROOT = "C:\\"
apidFile = "C:\\data\\python\\apid.txt"

class HTTPChannel(asynchat.async_chat):

	def __init__(self, server, sock, addr):
		asynchat.async_chat.__init__(self, sock)
		self.server = server
		self.set_terminator("\r\n\r\n")
		self.header = None
		self.data = ""
		self.shutdown = 0

	def collect_incoming_data(self, data):
		#print "data: ", data
		self.data = self.data + data
		if len(self.data) > 16384:
			# limit the header size to prevent attacks
			self.shutdown = 1

	def found_terminator(self):
		if not self.header:
			# parse http header
			fp = StringIO.StringIO(self.data)
			request = string.split(fp.readline(), None, 2)
			if len(request) != 3:
				# badly formed request; just shut down
				self.shutdown = 1
			else:
				# parse message header
				self.header = mimetools.Message(fp)
				self.set_terminator("\r\n")
				self.server.handle_request(
					self, request[0], request[1], self.header
					)
				self.close_when_done()
			self.data = ""
		else:
			pass # ignore body data, for now

	def pushstatus(self, status, explanation="OK"):
		self.push("HTTP/1.0 %d %s\r\n" % (status, explanation))


class FileProducer:
	# a producer which reads data from a file object

	def __init__(self, file):
		self.file = file

	def more(self):
		if self.file:
			data = self.file.read(2048)
			if data:
				return data
			self.file.close()
			self.file = None
		return ""



class HTTPServer(asyncore.dispatcher):

	def __init__(self, ip, port=None, request=None):
		print "init http server"
		self.handle_request_in_UI_thread_executing = 0
		asyncore.dispatcher.__init__(self)
		if not port:
			port = 80
		self.port = port
		if request:
			self.handle_request = request # external request handler
		self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
		#self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)		
		print "binding socket %s:%d" % (ip, port)
		self.bind((ip, port))
		self.listen(5)   # bug? this one pretty much blocks UI

	def handle_accept(self):
		conn, addr = self.accept()
		HTTPChannel(self, conn, addr)

	def handle_request(self, channel, method, path, header):
		self.handle_request_in_UI_thread_executing = 0
		handle_request_in_UI_thread(self, channel, method, path, header)
		while self.handle_request_in_UI_thread_executing == 0:
			time.sleep(0.1)


def _handle_request_in_UI_thread(self, channel, method, path, header):
	try:
		try:
			# this is not safe!
			params = (string.join(path.split("?")[1:], "?")).split("&")
			path = path.split("?")[0]
			while path[:1] == "/":
				path = path[1:]
			if path == 'quit':
				print "Exiting ..."
				self.shutdown = 1
				self.close()
				ap.stop()	
				appuifw.app.orientation = 'portrait'				
				appuifw.app.set_exit()
				filename = ""
			elif path == 'takepicture.jpg':			
				print "[camera] => takepicture.jpg ..."					
				e32.reset_inactivity()
				if appuifw.app.orientation == 'portrait':
					print "switching to landscape"
					appuifw.app.orientation = 'landscape'
				size = max(camera.image_sizes("JPEG_Exif"))	
				filename = os.path.join("D:\\", path)
				flash = "none"
				if "&flash=forced" in "&"+"&".join(params):
					flash = "forced"
				appuifw.app.orientation = 'landscape'
				take_picture(filename, size, flash)
				file = open(filename, "rb")
			elif os.path.splitext(path)[1] == '.jpg':
				filename = os.path.join(ROOT, path)
				print path, "=>", filename
				file = open(filename, "rb")				
			else:
				filename = os.path.join(ROOT, path)
				print path, "=>", filename
				file = open(filename, "rb")		
		except IOError:
			print "404 not found"
			channel.pushstatus(404, "Not found")
			channel.push("Content-type: text/html\r\n")
			channel.push("\r\n")
			channel.push("<html><body>File not found.</body></html>\r\n")
		else:
			print "200 OK"
			channel.pushstatus(200, "OK")
			if os.path.splitext(filename)[1] == '.jpg':
				channel.push("Content-type: image/jpeg\r\n")
			elif os.path.splitext(filename)[1] == '.zip':
				channel.push("Content-type: application/x-zip-compressed\r\n")
			else:
				channel.push("Content-type: text/html\r\n")
			fileSize = os.lstat(filename).st_size
			print "sending %d bytes" % (fileSize,)
			channel.push("Content-length: %d\r\n" % (fileSize,))
			channel.push("\r\n")
			channel.push_with_producer(FileProducer(file))
	finally:
		#print "done doing stuff in UI thread"
		self.handle_request_in_UI_thread_executing = 1  # let HTTP server's handle_request() know we're done

def take_picture(aFilename, picSize, aFlash='none'):
	#Take the photo
	print "Taking photo .. ", picSize, " flash=", aFlash
	#photo = camera.take_photo('JPEG_Exif', (2048,1536), flash='none', exposure='auto', white_balance='auto')
	photo = camera.take_photo('JPEG_Exif', picSize, flash=aFlash, exposure='auto', white_balance='auto')	
	#Save it
	print "Saving photo to %s."%(aFilename)
	F=open(aFilename, "wb")
	F.write(photo)
	F.close()			
			
def sel_access_point(a_id=0):
	# Select temporary default access point 
	if a_id:
		apid = a_id
	else:
		apid = socket.select_access_point() 
	print "Selected AP: %d" % (apid)
	# zero is not a valid AP number
	return apid

def startup():
	#ap = sel_access_point()
	ap.stop()
	print "starting AP"
	ap.start()
	ip = ap.ip()
	port = 50000
	print "starting http server"
	global httpDisp
        httpDisp = HTTPServer(ip, port)
	print "Serving at ip:", ip," port:", port
	asyncore.loop()
	
def startupInThread():
	print "thread running"
	startup()
	print "thread stopped"


def stopServer():
	print "stopping server"
	httpDisp.close()
	print "server stopped"

def StoreAccessPointSelection(apid):
	file = open(apidFile,'w')
	print "write to file: %d" %(apid)
	file.write('%d'%(apid))
	file.close	
	
def RetrieveAccessPointSelection():
	if os.path.exists(apidFile):
		print "ap file exist"
		file = open(apidFile,'r')
		apid = sel_access_point(int(file.read()))
		file.close
	else:
		print "no stored iap. will prompt."
		apid = sel_access_point(0)
		StoreAccessPointSelection(apid)
		
	if apid:
		apo = socket.access_point(apid)
		socket.set_default_access_point(apo)
		return apo
	else:		
		return None

def RemoveAccessPointSelection():
	if os.path.exists(apidFile):
		os.remove(apidFile)

		
#Define the exit function
def Quit():
	stopServer
	app_lock.signal()
	appuifw.app.orientation = 'portrait'
	appuifw.app.set_exit()

#
# try it out
print camera.image_sizes("JPEG_Exif")

ap = RetrieveAccessPointSelection()

appuifw.app.exit_key_handler = quit
appuifw.app.menu=[(u"Stop server", stopServer),(u"Remove saved AP", RemoveAccessPointSelection),(u"Exit", Quit)]

#startup()
handle_request_in_UI_thread = e32.ao_callgate(_handle_request_in_UI_thread)
thread.start_new_thread(startupInThread, ())

app_lock.wait()	