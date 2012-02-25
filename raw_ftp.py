import appuifw, e32, time, datetime, ftplib
from time import sleep
from ftplib import FTP
 
#Switch to landscape mode
appuifw.app.orientation = 'landscape'
 
import camera
app_lock = e32.Ao_lock()

#Define the exit function 
def quit():
	#Close the viewfinder
	#camera.stop_finder()
	#Release the camera so that other programs can use it
	camera.release()
	app_lock.signal()
	appuifw.app.orientation = 'portrait'	
appuifw.app.exit_key_handler = quit
 
#Function for looping it all
def loop():
	numImages = appuifw.query(u"Enter number of photos you wish to take:", "number", "1")
	delay = appuifw.query(u"Enter time between each photo:", "number")
	x = 0
	photo_savepath = "D:\\phototmp.jpg"
	while x != numImages:
		print "Taking photo num: %s."%(x)
		take_picture(photo_savepath)
		sleep(delay)
		x +=1
	print "Done!" 

#Function for taking the picture
def take_picture(aFilename):
	#Take the photo
	print "Taking photo .."
	photo = camera.take_photo('JPEG_Exif', (2592, 1944), flash='forced', exposure='auto', white_balance='auto')
	#Save it
	print "Saving photo to %s."%(aFilename)
	F=open(aFilename, "wb")
	F.write(photo)
	F.close()	
	#Upload it
	F=open(aFilename,'rb')
	ftp = FTP('192.168.123.1')
	ftp.set_pasv('false')
	ftp.login('o','o')	
	ftp.cwd('/shares/USB_Storage')
	now = datetime.datetime.now()
	uploadFilename = "%i%i%i_%i%i%i.jpg" % (now.year, now.month, now.day, now.hour, now.minute, now.second)
	ftp.storbinary('STOR '+uploadFilename,F,8192)
	ftp.quit()
	F.close()

print camera.image_sizes("JPEG_Exif")
appuifw.app.menu=[(u"Take photo", loop)]
 
#Wait for the user to request the exit
app_lock.wait()