from math import *


def px(Dx, x, x0):
    px = (1/sqrt(2*pi*Dx)) * exp(-((x-x0)**2)/2*Dx)

def pyx(De, x, y1):
    px = (1/sqrt(2*pi*De)) * exp(-((x-y1)**2)/2*De)

def bayes(De, x, y1):
    #p(x|y)
    result = (pyx(De, x, y1) * px)/p