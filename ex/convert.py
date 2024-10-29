# run by 
# python .\convert.py --inst 50 --loc 28.54503 77.19367 --animeid 6894 --diff 0
import math
from decimal import Decimal
import csv
import ctypes
import hashlib
import os
import argparse

CONSTANT_FRAMES = 200

class anim_ds(ctypes.Structure):
	_fields_ = [
		('sf',ctypes.c_char),
		('id', ctypes.c_uint16),
		('lat',ctypes.c_int32),
		('lng',ctypes.c_int32),
		('d1',ctypes.c_uint16),
		('r',ctypes.c_uint8),
		('g',ctypes.c_uint8),
		('b',ctypes.c_uint8),
		("fcount", ctypes.c_uint8),
		('ef', ctypes.c_char),
		('crc', ctypes.c_uint8)
	]

parser = argparse.ArgumentParser(description='Process some integers.')

# Add an argument
parser.add_argument('--inst', type=int, required=True)

parser.add_argument('--loc', type=float, nargs=2, required=True)

parser.add_argument('--animeid', type=int, required=True)

parser.add_argument('--diff', type=int, required=True)
                    
args = parser.parse_args()

coordinates = []
all_paths = []

x_offset=0
y_offset=0
angle=0
threshold=11 # Altitude to trigger landing

if not os.path.exists('paths'):
   os.makedirs('paths')

if not os.path.exists('bins'):
   os.makedirs('bins')


def list_duplicates_of(seq,item):
    start_at = -1
    locs = []
    while True:
        try:
            loc = seq.index(item,start_at+1)
        except ValueError:
            break
        else:
            locs.append(loc)
            start_at = loc
    return locs

def locate_eof(j,diff):
    pos=0
    check_flag=0
    clipped = False
    with open("drone-"+str(j-diff)+".csv", "r") as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        for lines in csv_reader:
            row=lines[0]
            col_index=list_duplicates_of(row, '\t')
            Z=row[col_index[2]+1:col_index[3]]
            pos += 1  # Increment the position
            if(float(Z) > threshold and check_flag == 0):
                check_flag=1
                
            if(check_flag == 1 and float(Z) < threshold):
                return (pos, True)  # We found the position, so we can return it
            #return -1 
    return (pos, False)



def calculatehash(file_path):
	hasher = hashlib.sha256()
	with open(file_path, 'rb') as f:
		while True:
			data = f.read(65536) # read 64KB chunks at a time
			if not data:
				break
			hasher.update(data)
	sha256_hash = hasher.hexdigest()

	# save hash to separate file
	with open(file_path+'sig', 'w') as f:
		f.write(sha256_hash)

def crc8(data, size):
    # Convert the struct to a byte array
    byte_array = bytearray(data)

    # Compute the CRC-8 of the byte array
    crc = 0
    for i in range(size):
        extract = byte_array[i]
        for _ in range(8):
            sum = (crc ^ extract) & 0x01
            crc >>= 1
            if sum:
                crc ^= 0x8C
            extract >>= 1

    # Update the CRC-8 field in the struct
    data.crc = crc

    return crc

def calculatecrc8(frame):
	_data = frame
	crc = crc8(_data, 19)
	return crc

def calculatelatlon(lat1,lon1,x,y):
   earthRadiusKm= 6371
   M_LON=(2*(math.pi)/360) * earthRadiusKm * (math.cos(lat1*math.pi/180))*1000  # in meter/degree
   M_LAT= 111 * 1000
   x_t=x*math.cos(angle*math.pi/180)+y*math.sin(angle*math.pi/180)
   y_t=-x*math.sin(angle*math.pi/180)+y*math.cos(angle*math.pi/180)
   return round(Decimal(lat1 + (y_t/M_LAT)),7),round(Decimal(lon1 + (x_t/M_LON)),7)

def generate_kml_3d_polyline(coords, output_file):
	# Open the output file for writing
	with open(output_file, 'w') as f:	
		# Write the KML header
		f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
		f.write('<kml xmlns="http://www.opengis.net/kml/2.2">\n')
		f.write('<Document>\n')
		# Create a Style for the linestring
		f.write('<Style id="3d_polyline">\n')
		f.write('<LineStyle>\n')
		f.write('<color>ff0000ff</color>\n')
		f.write('<width>5</width>\n')
		f.write('</LineStyle>\n')
		f.write('<PolyStyle>\n')
		f.write('<color>7f0000ff</color>\n')
		f.write('</PolyStyle>\n')
		f.write('</Style>\n')
		# Create a Placemark for the linestring
		f.write('<Placemark>\n')
		f.write('<name>3D Polyline</name>\n')
		f.write('<styleUrl>#3d_polyline</styleUrl>\n')
		f.write('<LineString>\n')
		f.write('<altitudeMode>absolute</altitudeMode>\n')
		f.write('<coordinates>\n')
		# Add coordinates to the linestring
		for coord in coords:
			lat, lon, alt = coord
			lon, lat = lon/(10**7), lat/(10**7)
			f.write(f'{lon},{lat},{alt}\n')
		# Close the LineString and Placemark
		f.write('</coordinates>\n')
		f.write('</LineString>\n')
		f.write('</Placemark>\n')
		# Write the KML footer
		f.write('</Document>\n')
		f.write('</kml>\n')

def generate_all_drones_kml_3d_polyline(paths, output_file):
	# Open the output file for writing
	with open(output_file, 'w') as f:	
		# Write the KML header
		f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
		f.write('<kml xmlns="http://www.opengis.net/kml/2.2">\n')
		f.write('<Document>\n')
		ind = 1+args.diff
		for coords in paths:
			# Create a Style for the linestring
			f.write('<Style id="3d_polyline'+str(ind)+'">\n')
			f.write('<LineStyle>\n')
			f.write('<color>ff0000ff</color>\n')
			f.write('<width>5</width>\n')
			f.write('</LineStyle>\n')
			f.write('<PolyStyle>\n')
			f.write('<color>7f0000ff</color>\n')
			f.write('</PolyStyle>\n')
			f.write('</Style>\n')
			# Create a Placemark for the linestring
			f.write('<Placemark>\n')
			f.write('<name>3D Polyline</name>\n')
			f.write('<styleUrl>#3d_polyline</styleUrl>\n')
			f.write('<LineString>\n')
			f.write('<altitudeMode>absolute</altitudeMode>\n')
			f.write('<coordinates>\n')
			# Add coordinates to the linestring
			for coord in coords:
				lat, lon, alt = coord
				lon, lat = lon/(10**7), lat/(10**7)
				f.write(f'{lon},{lat},{alt}\n')
			# Close the LineString and Placemark
			f.write('</coordinates>\n')
			f.write('</LineString>\n')
			f.write('</Placemark>\n')

		# Write the KML footer
		f.write('</Document>\n')
		f.write('</kml>\n')

def genbaf():
	
	instance,coordinate,animeid,diff=args.inst,args.loc,args.animeid,args.diff
	j=1+diff
	#fcount = 0
	#print(instance,coordinate,animeid,diff)
	while(j <= instance+diff ):
			dronepathlist = []
			# Reading blender file 
			line_no=0
			try:
				file=open("drone-"+str(j-diff)+".csv","r")
				# line_no=0
				Content = file.read() 
				CoList = Content.split("\n") 
	
				for i in CoList: 
					if i: 
					  line_no += 1
	
				file.close()
			except FileNotFoundError:
				pass
			
			# Decoding  rows in a column  
			size=7  #[T,X,Y,Z,R,G,B]
			total_size=(line_no-1)*size 
			
			try:
				# Find the frame where we need to start landing	
				find_pos, clipped_stats =locate_eof(j,diff)
				total_size = find_pos
				print("\nhere is find_pos and clipped status",find_pos, clipped_stats)
				if(clipped_stats == False):
					print("Warning! ","drone-"+str(j-diff), "end frame is above threshold alt")
					find_pos = find_pos - 3
					total_size = find_pos
				#print("last value:"+str(find_pos))
				landing_alt = 0

				with open("drone-"+str(j-diff)+".csv", "r") as csv_file:
					i=0
					csv_reader = csv.reader(csv_file, delimiter='\t')
					wavepoint_file=open(os.path.normpath("./bins/drone_"+str(animeid)+"_"+str(j)+".baf"),"wb")
					frame = anim_ds()
					frame.ef = ctypes.c_char(bytes('e', encoding='utf-8'))
					frame.sf = ctypes.c_char(bytes('s', encoding='utf-8'))
					frame.fcount = 0
					noframes = 0
	
					for lines in csv_reader:
						X, Y=float(lines[1]), float(lines[2])
						X, Y=calculatelatlon(coordinate[0],coordinate[1],X+x_offset,Y+y_offset)
						X, Y = X*(10**7), Y*(10**7)
						noframes = noframes + 1
						#frame.fcount = fcount
						if(i==0):
							frame.id =          ctypes.c_uint16(int(total_size + CONSTANT_FRAMES))
							frame.lat =         ctypes.c_int32(int(X))
							frame.lng =         ctypes.c_int32(int(Y))
							frame.d1 =          ctypes.c_uint16(int(float(lines[3])*100))
							frame.r =           ctypes.c_uint8(int(lines[4]))
							frame.g =           ctypes.c_uint8(int(lines[5]))
							frame.b =           ctypes.c_uint8(int(lines[6]))
							frame.crc =         calculatecrc8(frame)
							noframes = noframes + 1
							wavepoint_file.write(bytearray(frame))
			
						if(i==1):
							frame.id = 	 		ctypes.c_uint16(int(animeid))
							frame.lat = 		ctypes.c_int32(int(X))
							frame.lng = 		ctypes.c_int32(int(Y))
							frame.d1 = 			ctypes.c_uint16(int(float(lines[3])*100))
							frame.r = 			ctypes.c_uint8(int(lines[4]))
							frame.g = 			ctypes.c_uint8(int(lines[5]))
							frame.b = 			ctypes.c_uint8(int(lines[6]))
							frame.crc = 		calculatecrc8(frame)
							wavepoint_file.write(bytearray(frame))
							coordinates.append([frame.lat, frame.lng])
							dronepathlist.append([frame.lat, frame.lng, frame.d1])

						if(i==2):
							frame.id = 	 		ctypes.c_uint16(int(j))
							frame.lat = 		ctypes.c_int32(int(X))
							frame.lng = 		ctypes.c_int32(int(Y))
							frame.d1 = 			ctypes.c_uint16(int(float(lines[3])*100))
							frame.r = 			ctypes.c_uint8(int(lines[4]))
							frame.g = 			ctypes.c_uint8(int(lines[5]))
							frame.b = 			ctypes.c_uint8(int(lines[6]))
							frame.crc = 		calculatecrc8(frame)
							wavepoint_file.write(bytearray(frame))

						elif(i>2 and i<line_no-1):
							frame.id = 	 		ctypes.c_uint16(int(lines[0]))
							frame.lat = 		ctypes.c_int32(int(X))
							frame.lng = 		ctypes.c_int32(int(Y))
							frame.d1 = 			ctypes.c_uint16(int(float(lines[3])*100))
							frame.r = 			ctypes.c_uint8(int(lines[4]))
							frame.g = 			ctypes.c_uint8(int(lines[5]))
							frame.b = 			ctypes.c_uint8(int(lines[6]))
							frame.crc = 		calculatecrc8(frame)
							wavepoint_file.write(bytearray(frame))
							dronepathlist.append([frame.lat, frame.lng, frame.d1])
	
						# New landing sequence, append 50 same frames and EOF frame to land, break the loop after that.
						if(i == find_pos-1):
							#print("breaking loop at ", i, "fcount", frame.fcount)
							frame.fcount = frame.fcount + 1
							for rept in range(200):
								frame.id = 	 		ctypes.c_uint16(int(lines[0]))
								frame.lat = 		ctypes.c_int32(int(X))
								frame.lng = 		ctypes.c_int32(int(Y))
								frame.d1 = 			ctypes.c_uint16(int(float(lines[3])*100))
								frame.r = 			ctypes.c_uint8(int(lines[4]))
								frame.g = 			ctypes.c_uint8(int(lines[5]))
								frame.b = 			ctypes.c_uint8(int(lines[6]))
								frame.crc = 		calculatecrc8(frame)
								wavepoint_file.write(bytearray(frame))
								dronepathlist.append([frame.lat, frame.lng, frame.d1])
								frame.fcount = frame.fcount + 1
							landing_alt = float(lines[3])
							# -----------------
	
							frame.id = 	 		ctypes.c_uint16(0)
							frame.lat = 		ctypes.c_int32(0)
							frame.lng = 		ctypes.c_int32(0)
							frame.d1 = 			ctypes.c_uint16(0)
							frame.r = 			ctypes.c_uint8(0)
							frame.g = 			ctypes.c_uint8(0)
							frame.b = 			ctypes.c_uint8(0)
							frame.crc = 		calculatecrc8(frame)
							wavepoint_file.write(bytearray(frame))
							wavepoint_file.close()
							#print("frame size-", ctypes.sizeof(frame))
							#print("total frames -", noframes)
							#calculatehash("drone_"+str(animeid)+"_"+str(j)+".baf")
							generate_kml_3d_polyline(dronepathlist, os.path.normpath("./paths/drone-"+str(j-diff)+"-path.kml"))
							all_paths.append(dronepathlist)
							print("Breaking loop at frame - ", noframes, "and alt -", landing_alt)
							break
						i=i+1
						frame.fcount = frame.fcount + 1
			except FileNotFoundError:
				#print("File not found")
				pass
			print("Progress = ", 100*(j-args.diff)/(args.inst),"%", end='\r')
			j=j+1
	generate_all_drones_kml_3d_polyline(all_paths, os.path.normpath("./paths/complete_paths.kml"))
		


def gencsv():
	def calculatelatlon(lat1,lon1,x,y):
		earthRadiusKm= 6371
		M_LON=(2*(math.pi)/360) * earthRadiusKm * (math.cos(lat1*math.pi/180))*1000  # in meter/degree
		M_LAT= 111 * 1000
		x_t=x*math.cos(angle*math.pi/180)+y*math.sin(angle*math.pi/180)
		y_t=-x*math.sin(angle*math.pi/180)+y*math.cos(angle*math.pi/180)
		return round(Decimal(lat1 + (y_t/M_LAT)),7),round(Decimal(lon1 + (x_t/M_LON)),7)



	def list_duplicates_of(seq,item):
	    start_at = -1
	    locs = []
	    while True:
	        try:
	            loc = seq.index(item,start_at+1)
	        except ValueError:
	            break
	        else:
	            locs.append(loc)
	            start_at = loc
	    return locs



	instance,coordinate,animeid,diff=args.inst,args.loc,args.animeid,args.diff

	j=1+diff
	#print(instance,coordinate,animeid,diff)
	while(j <= instance+diff ):

			# Reading blender file 
			try:
				file=open("drone-"+str(j-diff)+".csv","r")
				line_no=0
				Content = file.read() 
				CoList = Content.split("\n") 

				for i in CoList: 
					if i: 
					  line_no += 1

				file.close()

				# creating new file
				f=open("drone_"+str(animeid)+"_"+str(j)+".csv","a+")
				f.truncate(0) # deleting content
				f.close()

			except FileNotFoundError:
				#msg = "Sorry, the file does not exist."
				#print(msg) # Sorry, the file John.txt does not exist.			
				pass


			# Decoding  rows in a column  
			size=7  #[T,X,Y,Z,R,G,B]
			total_size=(line_no-1)*size 

			try:
				find_pos, clipped_stats=locate_eof(j,diff)
				print("last value:"+str(find_pos))
				with open("drone-"+str(j-diff)+".csv", "r") as csv_file:
					i=0
					csv_reader = csv.reader(csv_file, delimiter=',')
					for lines in csv_reader:
						row=lines[0]
						col_index=list_duplicates_of(row, '\t')

						T=row[0:col_index[0]]                                     
						X=row[col_index[0]+1:col_index[1]]
						Y=row[col_index[1]+1:col_index[2]]
						Z=row[col_index[2]+1:col_index[3]]
						R=row[col_index[3]+1:col_index[4]]
						G=row[col_index[4]+1:col_index[5]]
						B=row[col_index[5]+1:]

						X,Y=calculatelatlon(coordinate[0],coordinate[1],float(X)+x_offset,float(Y)+y_offset)
						if(i!=0):
							T=str(int(float(T))).zfill(4)
						else:
							T=str(int(float(animeid))).zfill(4)
						X=str(int(X*(10**7))).zfill(9)
						Y=str(int(Y*(10**7))).zfill(9)
						Z=str(int(float(Z)*(10**2))).zfill(5) 
						R=str(int(float(R))).zfill(3)
						G=str(int(float(G))).zfill(3)
						B=str(int(float(B))).zfill(3)


						if(i==0):
							wavepoint_file=open("drone_"+str(animeid)+"_"+str(j)+".csv","a+")
							wavepoint_file.write(T+'/'+X+'/'+Y+'/'+Z+'/'+R+'/'+G+'/'+B+'/')
							wavepoint_file.close()
						elif(i>0 and i<line_no-2):
							wavepoint_file=open("drone_"+str(animeid)+"_"+str(j)+".csv","a+")  
							wavepoint_file.write('\n'+T+'/'+X+'/'+Y+'/'+Z+'/'+R+'/'+G+'/'+B+'/')
							wavepoint_file.close()	
						i=i+1   
    
						if(i == find_pos):
							wavepoint_file=open("drone_"+str(animeid)+"_"+str(j)+".csv","a+")
							for i in range(50):
								wavepoint_file.write('\n'+T+'/'+X+'/'+Y+'/'+Z+'/'+R+'/'+G+'/'+B+'/')
							wavepoint_file.write('\n'+str(0).zfill(4)+'/'+str(0).zfill(9)+'/'+str(0).zfill(9)+'/'+str(0).zfill(5)+'/'+str(0).zfill(3)+'/'+str(0).zfill(3)+'/'+str(0).zfill(3)+'/') 
							wavepoint_file.close()
							break
			except FileNotFoundError:
				#msg = "Sorry, the file does not exist."
				#print(msg) # Sorry, the file John.txt does not exist.			
				pass		

			j=j+1

def generate_kml_file(coordinates):
    # Create the KML document
    kml_doc = '<?xml version="1.0" encoding="UTF-8"?>\n'
    kml_doc += '<kml xmlns="http://www.opengis.net/kml/2.2">\n'
    kml_doc += '<Document>\n'
    kml_doc += '<name>Points with Indexes</name>\n'
    
    # Add placemarks for each coordinate
    for i, coordinate in enumerate(coordinates):
        kml_doc += f'<Placemark>\n<name>{args.diff+i+1}</name>\n'
        kml_doc += f'<Point><coordinates>{coordinate[1]/10**7},{coordinate[0]/10**7}</coordinates></Point>\n'
        kml_doc += '</Placemark>\n'
    
    # Close the KML document
    kml_doc += '</Document>\n</kml>'
    
    # Write the KML document to a file
    with open(os.path.normpath('./paths/takeoff_points.kml'), 'w') as kml_file:
        kml_file.write(kml_doc)

genbaf()
generate_kml_file(coordinates)
#gencsv()
