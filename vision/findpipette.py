'''
Methods to find the pipette in an image
'''
from vision.crop import *
from numpy import dot, array, sign

__all__ = ['pipette_cardinal', 'up_direction']

def pipette_cardinal(image):
    '''
    Determines the cardinal direction of the pipette (N, NW, S, etc) in the image.
    '''
    xmin = None
    for direction in cardinal_points.iterkeys():
        cropped = crop_cardinal(image, direction)
        # Find the darkest subimage
        x = cropped.flatten().sum()
        if (xmin is None) or (x<xmin):
            xmin=x
            result = direction
    return result

def up_direction(pipette_position, positive_move):
    '''
    Determines the direction (+1 or -1) of the pipette going up.

    Parameters
    ---------
    pipette_position : cardinal position of the pipette
    positive_move : vector of image movement for a positive displacement along the axis
    '''
    y,x = cardinal_points[pipette_position] # position of pipette in square (0..2, 0..2)
    pipette_vector = array((1,1)) - array((x,y))
    return sign(dot(pipette_vector,positive_move[:2]))
