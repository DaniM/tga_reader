#!/usr/bin/env python
import tga_reader
import argparse

def downsample_no_int(data,factor):
	assert factor > 0 , 'The factor must be an integer between (0,MAX_INT]'
	factor = int(factor)
	new_sample = []
	for i in xrange(0,len(data),factor):
		new_sample.append(data[i])
	return new_sample

def downsample_tga(tga,factor):
	assert factor > 0, 'The factor must be an integer between (0,MAX_INT]'
	ds_width = tga.width // factor
	ds_height = tga.height // factor
	ds_data = []
	# first downsample the columns, then the rows
	# is more inneficient but simpler
	for row in tga.data:
		ds_data.append( downsample_no_int( row, factor ) )
	# downsample, remove, the rows
	ds_data = downsample_no_int( ds_data, factor )
	return tga_reader.TGA( tga.datatype_code, ds_height, ds_width, tga.pixel_size, tga.descriptor_byte, ds_data )

def downsample_test_1():
	data = [0,1,2,3,4,5,6,7]
	print 'Downsampling x2 ', data
	print 'Result ', downsample_no_int(data,2)

def downsample_test_2():
	data = [[0,1,2,3],[4,5,6,7],[8,9,10,11]]
	ds_data = []
	for row in data:
		ds_data.append( downsample_no_int( row, 2 ) )
	ds_data = downsample_no_int( ds_data, 2 )
	print 'Downsampling x2 ', data
	print 'Result ', ds_data

if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('tga_in', type=str, help='tga in image')
	parser.add_argument('factor', type=int, help='Downsampling factor', choices=[2,4,8])
	parser.add_argument('-o','--output', type=str, help='out image')
	args = parser.parse_args( )
	tga = tga_reader.read_tga( args.tga_in )
	downsampled_tga = downsample_tga( tga, args.factor )
	if args.output:
		tga_reader.save_tga( downsampled_tga, args.output )		
	else:
		tga_reader.save_tga( downsampled_tga, 'out.tga' )

