"""
Search a template image in an other image
Not scale nor rotation invariant

Uses OpenCV.
Alternatively, one might use skimage.feature.match_template
"""

import warnings
try:
    import cv2
except:
    warnings.warn('OpenCV not available')
from .phase_cross_correlation import phase_cross_correlation

__all__ = ['templatematching','MatchingError']

# Optional refinement of matching with phase cross correlation
refine_with_phase = False

class MatchingError(Exception):
    def __init__(self, value):
        self.value = value # best matching value

    def __str__(self):
        return 'The template was not found'

def templatematching_phase(img, template):
    """
    Search a template image in an other image
    Not scale nor rotation invariant.
    Uses phase cross-correlation.
    !! The problem is img and template need to be the same size !!.

    Parameters
    ----------
    img : image to look in
    template : image to look for
    threshold : throw an error if match value is below threshold

    Returns
    -------
    x : x coordinate of the template in the image
    y : y coordinate
    maxval : maximum value corresponding to the best matching ratio
    """

    shifts, error, _ = phase_cross_correlation(template, img, upsample_factor=100)
    maxval = abs(1-error)

    return shifts[1], shifts[0], maxval

def templatematching(img, template, threshold = 0):
    """
    Search a template image in an other image
    Not scale nor rotation invariant.

    Parameters
    ----------
    img : image to look in
    template : image to look for
    threshold : throw an error if match value is below threshold

    Returns
    -------
    x : x coordinate of the template in the image
    y : y coordinate
    maxval : maximum value corresponding to the best matching ratio
    """

    # Searching for a template match using cv2.TM_COEFF_NORMED detection
    res = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)

    # Getting maxval and maxloc
    _, maxval, _, maxloc = cv2.minMaxLoc(res)

    x, y = maxloc
    h, w = template.shape

    if refine_with_phase:
        dx, dy , maxval = templatematching_phase(img[y:y+h,x:x+w], template)
        x, y = x+dx, y+dy

    if maxval < threshold:
        raise MatchingError(maxval)

    return x, y, maxval

if __name__ == '__main__':
    img = cv2.imread('pipette.jpg', 0)
    template = cv2.imread('template.jpg', 0)

    res, val, loc = templatematching(img, template)
    x, y = loc[:2]
    if res:
        h = template.shape[1]
        w = template.shape[0]
        cv2.rectangle(img, (x, y), (x+w, y+h), (0, 0, 255))
    cv2.imshow("camera", img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
