'''
Methods to crop images
'''

__all__ = ['crop_center', 'crop_cardinal', 'cardinal_points']

# coordinates of cardinal points (y,x)
cardinal_points = {'NW' : (0,0),
                   'N' : (0,1),
                   'NE' : (0,2),
                   'E' : (1,2),
                   'SE' : (2,2),
                   'S' : (2,1),
                   'SW' : (2,0),
                   'W' : (1,0)}

def crop_center(image, ratio=32):
    '''
    Returns the center of the image.

    Parameters
    ----------
    image : the image
    ratio : size ratio of cropped image to original image
    '''
    shape = image.shape
    return image[int(shape[0] / 2 - 3 * shape[0] / ratio):int(shape[0] / 2 + 3 * shape[0] / ratio),
                 int(shape[1] / 2 - 3 * shape[1] / ratio):int(shape[1] / 2 + 3 * shape[1] / ratio)]

def crop_cardinal(image, direction):
    '''
    Returns a quadrant of the image corresponding to a cardinal point

    Parameters
    ----------
    image : the image
    direction : cardinal point as a string, in 'N', 'NW', 'S' etc
    '''
    height, width = image.shape # dimensions of image
    # Dimensions of cropped image
    height = height/2
    width = width/2
    # Coordinates of the quadrant
    i,j = cardinal_points[direction]
    return image[i*height/2: (i+2)*height/2, j*width/2:(j+2)*width/2]
