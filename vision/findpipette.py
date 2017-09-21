'''
Methods to find the pipette in an image
'''
from vision.crop import *
from numpy import histogram

__all__ = ['pipette_cardinal']

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
