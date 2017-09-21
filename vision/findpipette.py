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
    cropped_image = dict()
    xmax = -1
    for direction in cardinal_points.iterkeys():
        cropped = crop_cardinal(image, direction)
        # Search the tip using the number of darkest pixels in the image
        bin_edge, _ = histogram(cropped.flatten())
        x = bin_edge.min()
        if x>xmax:
            xmax=x
            result = direction
    return result
