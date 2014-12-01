#!/usr/bin/env python
# -*- coding: utf-8 -*-
import argparse
import sys
import struct
import collections

TGA = collections.namedtuple('TGA','datatype_code height width pixel_size descriptor_byte data') 

"""Data formats extracted from here: http://www.paulbourke.net/dataformats/tga/"""

def read_tga( filename ):
	f = None
	try:
		f = open( filename, 'rb' )
		assert f, 'The file doesn\'t exists'
		idlength = struct.unpack('b',f.read(1))[0]
		colormap_type = struct.unpack( 'b', f.read(1) )[0]
		print 'Color Map Type: ',colormap_type
		datatype_code = struct.unpack( 'b', f.read(1) )[0]
		print 'Data Type Code: ', datatype_code
		colormap_origin = struct.unpack('<h',f.read(2))[0]
		colormap_length = struct.unpack('<h',f.read(2))[0]
		colormap_depth = struct.unpack( 'b', f.read(1) )[0]
		print 'Color map spec: (ignore if it\'s 0)'
		print '- Origin: ', colormap_origin
		print '- Length: ', colormap_length
		print '- Depth: ', colormap_depth
		image_xorigin = struct.unpack('<h',f.read(2))[0]
		assert image_xorigin == 0, 'Wrong tga file. The left origin is not 0'
		image_yorigin = struct.unpack('<h',f.read(2))[0]
		image_width = struct.unpack('<h',f.read(2))[0]
		image_height = struct.unpack('<h',f.read(2))[0]
		image_pxsize = struct.unpack( 'b', f.read(1) )[0]
		assert image_pxsize == 16 or image_pxsize == 24 or image_pxsize == 32, 'Wrong pixel size'
		image_descbyte = struct.unpack( 'b', f.read(1) )[0]
		print 'Image specification: '
		print 'Origin X: ', image_xorigin
		print 'Origin Y: ', image_yorigin
		print 'Width: ', image_width
		print 'Height: ', image_height
		print 'Pixel size: ', image_pxsize
		print 'Image descriptor byte: ', image_descbyte
		print 'Number of attribute bits (alfa): ', (image_descbyte & 0x0F)
		print 'Reserved 0: ', (image_descbyte & 0x10)
		print 'Origin (0 lower left-hand, 1 upper left-hand): ', (image_descbyte & 0x20)/0x20
		print 'Interleaving flag: '
		print '00 non-interleaved, 01 two-way (even/odd), 10 four-way, 11 reserved'
		print (image_descbyte & 0xC0)
		assert not (image_descbyte & 0xC0), 'Interleaved compression not supported'
		
		print 'Ignoring the Image Identification Field'
		print 'Size: ', idlength
		f.read(idlength)
	
		if colormap_type != 0:
			print 'non unmapped image, tga type not supported'

		print 'Image Data field'
		data = None
		if datatype_code == 2:
			print 'Uncompressed image'
			data = extract_notcompressed_tga_data( image_height, image_width, image_pxsize, image_descbyte & 0x0F, f )
		elif datatype_code == 10:
			print 'RLE image'
			data = uncompress_tga_data( image_height, image_width, image_pxsize, image_descbyte & 0x0F, f )
		else:
			print 'TGA type not supported'
			raise Exception('TGA type format not supported')
		assert data, 'Error occured while extracting the image data'
		# always returns the pixel matrix with the top-left corner as the origin
		if (image_descbyte & 0x20) == 0:
			print 'Bottom-left origin image'
			# Y origin = 0 means the origin is bottom-left
			data.reverse()
		#print 'Img data: ', data
		return TGA(datatype_code,image_height,image_width,image_pxsize,image_descbyte,data) 
	finally:
		if f:
			f.close()

def get_tga_origin(tga_image):
	return (tga_image.descriptor_byte & 0x20) / 0x20

def get_tga_bitsalphasize(tga_image):
	return (tga_image.descriptor_byte & 0x0F)

def get_tga_color(tga,x,y):
	if tga.pixel_size == 32:
		pass	
	elif tga.pixel_size == 16:
		alpha_size = get_tga_bitsalphasize( tga )
		if alpha_size:
			# 1 bit of alpha (1,5,5,5)
			pass
		else:
			# (5,6,5) bits
			pass
	else:
		pass
	

def create_mask(bits):
	mask = 0
	for _ in xrange(0,bits):
		mask = (mask << 1) | 0x01
	return mask 

def traspose_matrix(matrix):
	"""Naïve implementation"""
	rows = len(matrix)
	cols = len(matrix[0])
	dim = min(rows,cols)
	# first traspose the "square" part
	for i in xrange(0,dim):
		for j in xrange(0,dim):
			matrix[i][j],matrix[j][i] = matrix[j][i], matrix[i][j]
	# now check which dimension is bigger
	if rows > cols:
		# more rows than columns
		for i in xrange(dim,rows):
			for j in xrange(0,cols):
				matrix[j].append( matrix[i][j] )
		# remove the remaining rows
		for i in xrange( rows, dim, -1 ):
			matrix.pop()
	elif rows < cols:
		for j in xrange(dim,cols):
			row = []
			for i in xrange(0,rows):
				row.append( matrix[i][j] )
			matrix.append(row)
		for j in xrange(cols, dim, -1):
			for i in xrange(0,rows):
				matrix[i].pop()

def extract_notcompressed_tga_data(height, width, pxsize_inbits, alphasize_inbits, stream):
	# The stored pixel data format is ARGB
	data = []
	bytes_perpx = pxsize_inbits // 8;
	pxsize_rgb = pxsize_inbits - alphasize_inbits
	r_mask_size = g_mask_size = b_mask_size = pxsize_rgb // 3
	if pxsize_rgb % 3:
		# (5,6,5) 16 bit color
		b_mask_size += 1
	r_mask = create_mask(r_mask_size) << (g_mask_size + b_mask_size)
	print 'r mask: ', format(r_mask,'02x')
	g_mask = create_mask(g_mask_size) << b_mask_size
	print 'g mask: ', format(g_mask,'02x')
	b_mask = create_mask(b_mask_size)
	print 'b mask: ', format(b_mask,'02x')
	alpha_mask = 0x00
	if alphasize_inbits:
		alpha_mask = create_mask(alphasize_inbits)
		alpha_mask = alpha_mask << pxsize_rgb
	print 'a mask: ', format(alpha_mask,'02x')
	assert (r_mask_size + g_mask_size + b_mask_size + alphasize_inbits) == pxsize_inbits, 'wrong bit masks'
	# tga data is stored (width)x(height)
	for _ in xrange(0,height):
		row = []
		for _ in xrange(0,width):
			px_value = 0
			byte_array = []
			for _ in xrange(bytes_perpx):
				byte_array.append( struct.unpack('B',stream.read(1))[0] )
			# print 'Pixel data: ',byte_array
			# the bytes goes from lsb to msb, that's why we have shift it in
			# reverse order
			for b in xrange(bytes_perpx-1,0,-1):
				px_value |= byte_array[b]
				px_value <<= 8 
			px_value |= byte_array[0]
			# print 'Pixel value: ', format(px_value,'02X')
			value = ((px_value & r_mask) >> (g_mask_size + b_mask_size), 
			(px_value & g_mask) >> b_mask_size, 
			px_value & b_mask, 
			(px_value & alpha_mask) >> (r_mask_size+g_mask_size+b_mask_size)) 
			row.append(value)
		data.append(row)
	# traspose the matrix
	# traspose_matrix(data)
	# print data
	return data

def uncompress_tga_data(height, width, pxsize_inbits, alphasize_inbits, stream):
	data = []
	bytes_perpx = pxsize_inbits // 8;
	pxsize_rgb = pxsize_inbits - alphasize_inbits
	r_mask_size = g_mask_size = b_mask_size = pxsize_rgb // 3
	if pxsize_rgb % 3:
		# (5,6,5) 16 bit color
		b_mask_size += 1
	r_mask = create_mask(r_mask_size) << (g_mask_size + b_mask_size)
	print 'r mask: ', format(r_mask,'02x')
	g_mask = create_mask(g_mask_size) << b_mask_size
	print 'g mask: ', format(g_mask,'02x')
	b_mask = create_mask(b_mask_size)
	print 'b mask: ', format(b_mask,'02x')
	alpha_mask = 0x00
	if alphasize_inbits:
		alpha_mask = create_mask(alphasize_inbits)
		alpha_mask = alpha_mask << pxsize_rgb
	print 'a mask: ', format(alpha_mask,'02x')
	assert (r_mask_size + g_mask_size + b_mask_size + alphasize_inbits) == pxsize_inbits, 'wrong bit masks'
	
	row = []
	size = width * height
	pixels_read = 0
	while pixels_read < size:
		# check if it's a rle packet or a raw one
		# the most significative bit tell us this
		packet_header = struct.unpack('B',stream.read(1))[0]
		color_count = 0x7F & packet_header
		# the color to be read, repeated color count times more in case of rle
		# in case of raw data is the color to be read and color count more 
		color_count += 1 # that's why we add the 1
		#assert color_count > 0, 'Wrong color count in the packet header'
		pixels_read += color_count			

		# a color must be read anyway
		px_value = 0
		byte_array = []
		for _ in xrange(bytes_perpx):
			byte_array.append( struct.unpack('B',stream.read(1))[0] )
		# the bytes goes from lsb to msb, that's why we have shift it in
		# reverse order
		for b in xrange(bytes_perpx-1,0,-1):
			px_value |= byte_array[b]
			px_value <<= 8 
		# dont forget the lsb!
		px_value |= byte_array[0]

		value = ((px_value & r_mask) >> (g_mask_size + b_mask_size), 
		(px_value & g_mask) >> b_mask_size, 
		px_value & b_mask, 
		(px_value & alpha_mask) >> (r_mask_size+g_mask_size+b_mask_size)) 

		# store the current color, we have to do it anyway
		row.append( value )
		color_count -= 1

		if packet_header > 127:
			# rle packet
			# add color_count pixels to the image data
			# watch out for the row end
			while color_count:
				if len(row) == width:
					data.append(row)
					row = []
				else:
					row.append( value )
					color_count -= 1
		else:
			# raw packet
			while color_count:
				if len(row) == width:
					data.append(row)
					row = []
				else:	
					# keep reading colors
					px_value = 0
					byte_array = []
					for _ in xrange(bytes_perpx):
						byte_array.append( struct.unpack('B',stream.read(1))[0] )
					for b in xrange(bytes_perpx-1,0,-1):
						px_value |= byte_array[b]
						px_value <<= 8 
					px_value |= byte_array[0]

					value = ((px_value & r_mask) >> (g_mask_size + b_mask_size), 
					(px_value & g_mask) >> b_mask_size, 
					px_value & b_mask, 
					(px_value & alpha_mask) >> (r_mask_size+g_mask_size+b_mask_size)) 
		
					row.append( value )
					color_count -= 1

		# last element checking
		if len(row) == width:
			data.append(row)
			row = []
	return data
					

def save_tga(tga,filename):
	assert filename and filename != '', 'File to save not specified'
	f = None
	try:
		f  = open(filename,'wb')
		# id length is 0
		f.write( struct.pack('b',0) )
		# Only RGB unmapped supported, so the Color Map is 0 (no color map provided)
		f.write( struct.pack('b',0) )
		# datatype code
		f.write( struct.pack('b',tga.datatype_code) )
		assert tga.datatype_code == 2 or tga.datatype_code == 10, 'Unsupported format'
		# color map spec at 0
		f.write( struct.pack('<h',0) )
		f.write( struct.pack('<h',0) )
		f.write( struct.pack('b',0) )
		# image specification
		# x origin
		f.write( struct.pack('<h',0) )
		# y origin
		if get_tga_origin(tga):
			# top left
			f.write( struct.pack('<h',tga.height) )
		else:
			f.write( struct.pack('<h',0) )
		# width
		f.write( struct.pack('<h', tga.width) )
		# height
		f.write( struct.pack('<h', tga.height) )
		# pixel size
		f.write( struct.pack('b', tga.pixel_size) )
		# byte descriptor
		f.write( struct.pack('b', tga.descriptor_byte) )
		# no image identification field, neither color map data
		# Image Data
		# compress data using rle?
		if tga.datatype_code == 10:
			write_compress_tga_data( tga, f )
		else:
			# uncompressed
			write_uncompressed_tga_data( tga, f )
	finally:
		if f:
			f.close()

def write_uncompressed_tga_data( tga, stream ):
	# check if the origin is bottom left
	_from = 0
	_to = tga.height
	_step = 1 
	if not get_tga_origin( tga ):
		_from = tga.height - 1
		_to = -1
		_step = - 1
	
	# the writing operation will differ depending on the pixel size
	# (16 alpha/no alpha,24,32)
	if tga.pixel_size == 32:	
		for i in xrange(_from,_to,_step):
			for j in xrange(0,tga.width):
				write_tga_color32(tga.data[i][j],stream)
	elif tga.pixel_size == 16:
		alpha_size = get_tga_bitsalphasize( tga )
		if alpha_size:
			# 1 bit of alpha (1,5,5,5)
			for i in xrange(_from,_to,_step):
				for j in xrange(0,tga.width):
					write_tga_color16alpha( tga.data[i][j], stream )
		else:
			# (5,6,5) bits
			for i in xrange(_from,_to,_step):
				for j in xrange(0,tga.width):
					write_tga_color16( tga.data[i][j], stream )
	else:
		for i in xrange(_from,_to,_step):
			for j in xrange(0,tga.width):
				write_tga_color24( tga.data[i][j], stream )

def write_compress_tga_data(tga,stream):
	# check if the origin is bottom left
	origin = get_tga_origin( tga )
	pixels_left = tga.height * tga.width
	pixels_read = 0
	# used for uncompressed packets
	unc_packet = []
	while pixels_left - pixels_read:
		y = pixels_read // tga.width
		i = ( 1 - origin ) * ( tga.height - 1 - y ) + origin * y
		j = pixels_read % tga.width
		start = tga.data[i][j]
		pixels_read += 1
		# how many of them are equals
		pixels_count = 0
		while pixels_left - pixels_read:
			y = pixels_read // tga.width
			i = ( 1 - origin ) * ( tga.height - 1 - y ) + origin * y
			j = pixels_read % tga.width
	
			current = tga.data[i][j]
			if current[0] == start[0] and current[1] == start[1] and current[2] == start[2] and current[3] == start[3]:
				pixels_count += 1
				pixels_read += 1
			else:
				break
		# naive checking: there are at leat one equal pixel next to the selected one
		if pixels_count > 0:
			# although if the pixels_count is 2 we won't compress anything
			# first of all write the uncompressed ones
			write_uncompressed_packet( tga, unc_packet, stream )
			unc_packet = []	
			write_compressed_packet( tga, start, pixels_count, stream )
		else:
			# no compression
			unc_packet.append(start)
			if len(unc_packet) == 127:
				# write uncompressed packet
				write_uncompressed_packet( tga, unc_packet, stream )
				unc_packet = []
	# if the uncompressed list of colors is not empty write it to the stream
	if len(unc_packet) > 0:
		write_uncompressed_packet( tga, unc_packet, stream )	
	
def write_tga_color16(color,stream):
	# green channel is the tricky part, we have to divide between the two bytes
	# RRRRRGGG GGGBBBBB
	byte_msb = color[0] #R 
	byte_msb << 3

	# the three most significative bits of G
	byte_msb |= (color[1] & 0x38) >> 3

	# less significative byte
	# the three less significative bits of green
	byte_lsb = color[1] & 0x07
	byte_lsb << 5	

	byte_lsb |= color[2] # B
	
	stream.write(struct.pack('B',byte_lsb))
	stream.write(struct.pack('B',byte_msb))
 

def write_tga_color16alpha(color,stream):
	# ARRRRRGG GGGBBBBB
	byte_msb = color[3] # alpha
	byte_msb << 5
	byte_msb |= color[0] # R

	# the two most significative bits of G
	byte_msb << 2
	byte_msb |= (color[1] & 0x18) >> 3

	# less significative byte
	# the three less significative bits of green
	byte_lsb = color[1] & 0x07
	byte_lsb << 5	

	byte_lsb |= color[2] # B
	
	stream.write(struct.pack('B',byte_lsb))
	stream.write(struct.pack('B',byte_msb))

def write_tga_color24(color,stream):
	# write it lo-hi (little endian)
	stream.write( struct.pack('B',color[2]) ) #B
	stream.write( struct.pack('B',color[1]) ) #G
	stream.write( struct.pack('B',color[0]) ) #R

def write_tga_color32(color,stream):		
	# write it lo-hi (little endian)
	stream.write( struct.pack('B',color[2]) ) #B
	stream.write( struct.pack('B',color[1]) ) #G
	stream.write( struct.pack('B',color[0]) ) #R
	stream.write( struct.pack('B',color[3]) ) #A	

def write_uncompressed_packet(tga,colors,stream):
	# keep in mind that is the first color and count more
	# that's why we put a -1
	header = len(colors) - 1
	# do not write anything if the color list is empty
	if header < 0:
		return
	stream.write( struct.pack('B',header) )
	# the writing operation will differ depending on the pixel size
	# (16 alpha/no alpha,24,32)
	if tga.pixel_size == 32:	
		for color in colors:
			write_tga_color32(color,stream)
	elif tga.pixel_size == 16:
		alpha_size = get_tga_bitsalphasize( tga )
		if alpha_size:
			# 1 bit of alpha (1,5,5,5)
			for color in colors:
				write_tga_color16alpha(color,stream)
		else:
			# (5,6,5) bits
			for color in colors:
				write_tga_color16(color,stream)
	else:
		for color in colors:
			write_tga_color24(color,stream)
	

def write_compressed_packet(tga,color,count,stream):
	# header 0x1pixels_count, that is 128 + count
	header = 128 + count 
	stream.write( struct.pack('B',header) )
	# the writing operation will differ depending on the pixel size
	# (16 alpha/no alpha,24,32)
	if tga.pixel_size == 32:	
		write_tga_color32(color,stream)
	elif tga.pixel_size == 16:
		alpha_size = get_tga_bitsalphasize( tga )
		if alpha_size:
			# 1 bit of alpha (1,5,5,5)
			write_tga_color16alpha(color,stream)
		else:
			# (5,6,5) bits
			write_tga_color16(color,stream)
	else:
		write_tga_color24(color,stream)
	
def tga_writing_test_1():
	"""32 bits, alpha 8 bits, 4x4, bottom-left origin, compressed image"""
	data = [[(102,51,0,255),(0,0,0,0),(0,0,0,0),(0,0,0,0)],
		[(0,0,0,0),(0,0,0,0),(0,0,0,0),(0,0,0,0)],
		[(0,0,0,0),(0,0,0,0),(0,0,0,0),(0,0,0,0)],
		[(0,0,0,0),(0,0,0,0),(0,0,0,0),(0,0,0,0)]]
	tga = TGA(10,4,4,32,0x08,data)
	save_tga(tga,'out1.tga')
	# test the output
	tga_copy = read_tga('out1.tga')
	assert tga[0] == tga_copy[0] and tga[1] == tga_copy[1] and tga[2] == tga_copy[2] and tga[3] == tga_copy[3] and tga[4] == tga_copy[4]
	print 'Image data:'
	print tga_copy.data

def tga_writing_test_2():
	"""32 bits, alpha 8 bits, 5x4, top-left origin, compressed image"""
	data = [[(102,51,0,255),(0,0,0,0),(0,0,0,0),(0,0,0,0),(0,0,0,0)],
		[(0,0,0,0),(0,0,0,0),(0,0,0,0),(0,0,0,0),(0,0,0,0)],
		[(0,0,0,0),(0,0,0,0),(0,0,0,0),(0,0,0,0),(0,0,0,0)],
		[(0,0,0,0),(0,0,0,0),(0,0,0,0),(0,0,0,0),(0,0,0,0)]]
	tga = TGA(10,4,5,32,0x28,data)
	save_tga(tga,'out2.tga')
	# test the output
	tga_copy = read_tga('out2.tga')
	assert tga[0] == tga_copy[0] and tga[1] == tga_copy[1] and tga[2] == tga_copy[2] and tga[3] == tga_copy[3] and tga[4] == tga_copy[4]
	print 'Image data:'
	print tga_copy.data
	

def tga_writing_test_3():
	"""24 bits, alpha 0 bits, 5x4, top-left origin, compressed image"""
	data = [[(102,51,0,255),(0,0,0,0),(0,0,0,0),(0,0,0,0),(0,0,0,0)],
		[(0,0,0,0),(0,0,0,0),(0,0,0,0),(0,0,0,0),(0,0,0,0)],
		[(0,0,0,0),(0,0,0,0),(0,0,0,0),(0,0,0,0),(0,0,0,0)],
		[(0,0,0,0),(0,0,0,0),(0,0,0,0),(0,0,0,0),(0,0,0,0)]]
	tga = TGA(10,4,5,24,0x20,data)
	save_tga(tga,'out3.tga')
	# test the output
	tga_copy = read_tga('out3.tga')
	assert tga[0] == tga_copy[0] and tga[1] == tga_copy[1] and tga[2] == tga_copy[2] and tga[3] == tga_copy[3] and tga[4] == tga_copy[4]
	print 'Image data:'
	print tga_copy.data


def tga_limit_compression_test():
	"""LIMIT VALUE TEST: 128xHeight compressed image"""
	# create the data manually
	height = 2
	data = []
	for i in xrange(0,height):
		row = []
		for j in xrange(0,127):
			row.append( (0,0,0,255) )
		# change the color of the last one
		row.append( (100,50,200,255) )
		data.append(row)
	# now create the tga
	tga = TGA(10,2,128,32,0x08,data)
	save_tga(tga,'out4.tga')
	tga_copy = read_tga('out4.tga')
	assert tga[0] == tga_copy[0] and tga[1] == tga_copy[1] and tga[2] == tga_copy[2] and tga[3] == tga_copy[3] and tga[4] == tga_copy[4]
	print 'Image data:'
	print tga_copy.data
	

if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('tga_in', type=str, help='tga in image')
	parser.add_argument('-o','--output', type=str, help='out image')
	args = parser.parse_args()
	tga = read_tga( args.tga_in )
	print 'Image data: '
	print tga.data
	if args.output:
		save_tga( tga, args.output )
