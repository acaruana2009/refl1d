# This program is public domain
# Author: Paul Kienzle
"""
Interfacial roughness

Interfacial roughness is defined by a probability distribution P and the
step function H, with the convolution (P*H)(z) defining the probability
of finding a part of layer B in A.

Example::

    from mystic.param import Parameter as Par
    from refl1d import Sample, Slab, Material, Erf

    # define a silicon wafer with 1-sigma roughness between 0 and 5
    model = Sample()
    model.add(Slab(Material('Si'), interface=Erf(Par(0,5,"Si:Air"))

The above example uses an error function interface.  Other interface include::

    Sharp()             Dirac delta interface (cumulative density ~ sign(z))
    Erf(width=sigma)    Gaussian interface (cumulative density ~ erf(z))
    Tanh(width=sigma)   sech**2 interface (cumulative density ~ tanh(z))
    Linear(width=w)     boxcar interface (cumulative density ~ linear(z))

You can plot the available interfaces as follows::

    from refl1d import interface
    interface.demo()

As you can see from the above plot, the hyperbolic tangent profile will be
indistinguishable from the error function profile in all practical
circumstances.  Given the computational advantage of the error function
profile, there will be little reason to choose anything else.

Some interfaces can be defined using full width at half maximum (FWHM)
rather than 1-sigma::

    Erf.as_fwhm(width=fwhm)  Gaussian interface using FWHM
    Tanh.as_fwhm(width=fwhm) sech**2 interface using FWHM

To see what the effect of choosing FWHM, use::

    from refl1d import interface
    interface.demo_fwhm()

Defined using FWHM, tanh and erf profiles are significantly different
for the same value of width.  From the 1-sigma plots above, though, we
know that some values of width for tanh will closely match the shape
of the erf sigmoid.  What this means is that you will get different
values for the interface width from Erf.as_fwhm and Tanh.as_fwhm, but
the generated scattering length density profiles will be indistinguishable.

Extensions
==========

You can define new interface profiles by subclassing from Interface.
You will need to provide the following methods::

    pdf(z)
        returns the probability density function over z for the underlying
        distribution.
    cdf(z)
        returns the cumulative density function, which is the integral
        over the pdf from -inf to z.
    ppf(z)
        returns the percent point function, which is the inverse of
        the cdf.  You can define a profile with n equal sized steps in
        y using y=numpy.linspace(0,1,n+2)[1:-1], x=interface.ppf(y)
    parameters()
        returns the set of parameters used to define the interface

See the implementation of :class:`Erf` or :class:`Tanh` for a complete example.
"""
from __future__ import division
__all__ = ['Sharp', 'Erf', 'Tanh', 'Linear']

import math

import numpy
from numpy import tanh, cosh, exp, log, sqrt, pi, inf
from numpy import arccosh as acosh
from numpy import arctanh as atanh
from scipy.special import erf, erfinv

try:
    from mystic.parameter import Parameter as Par
except ImportError:
    print "Could not import Parameter from mystic; using trivial implementation"
    class Parameter:
        def __init__(self, value, **kw):
            self.value = value

sech = lambda x: 1/cosh(x)
asech = lambda x: acosh(1/x)

class Interface(object):
    """
    Interfacial mixing function.

    An interface defines the transition from one layer to another in terms
    of the relative proportion of materials on either side of the interface.
    """
    def parameters(self):
        """
        Fittable parameters
        """
        return []
    def cdf(self, z):
        """
        Return the cumulative density function corresponding to the interface.
        """
    def pdf(self, z):
        """
        Return the probability density function corresponding to the interface.
        """
    def ppf(self, z):
        """
        Return the percent point function, which is the inverse of the cdf.
        """

class Sharp(Interface):
    """
    Perfectly sharp interface

    The sharp interface has the form::

        CDF(z) = 1 if z>=0, 0 otherwise
        PDF(z) = inf if z==0, 0 otherwise
        PPF(z) = 0

    This interface has a trivial analytic solution in that it has no
    effect on the optical matrix calculation of the reflectivity.
    """
    def parameters(self):
        return []
    def cdf(self, z):
        return 1*(z>=0)
    def pdf(self, z):
        return inf*(z==0)
    def ppf(self, z):
        return 0*z

class Erf(Interface):
    """
    Error function profile

    *width* (Parameter: 0 Angstroms)

        1-sigma roughness.  For roughness w measured by the
        full width at half maximum (FWHM), use Erf.as_fwhm(w).

    *name* (string: "erf")

    The erf profile has the form::

        CDF(z) = (1 - erf(z/(sqrt(2)*sigma)))
        PDF(z) = 1/sqrt(2 pi sigma**2) exp( (z/sigma)**2/2 )
        PPF(z) = sigma*sqrt(2)*erfinv(2*z-1)

    To convert from a 1-sigma error function to the equivalent FWHM,
    you need to scale the error function roughness by sqrt(8*log(2))
    which is about 2.35.

    Note that this interface can be computed analytically.  When computing
    the slab product of the reflectivity, scale the Fresnel coefficient
    F = (k-k_next)/(k+k_next) by::

        S = exp(-2*k*k_next*sigma[i]**2)
    """
    @classmethod
    def as_fwhm(cls, *args, **kw):
        self = cls(*args, **kw)
        self._scale = 1/sqrt(8*log(2))
        return self
    def __init__(self, width=0, name="erf"):
        self._scale = 1
        self.width = Par.default(width, limits=(0,inf), name=name)
    def parameters(self):
        return self.width
    def cdf(self, z):
        sigma = self.width.value * self._scale
        if sigma <= 0.0:
            return 1.*(z >= 0)
        else:
            return 0.5*(1 + erf( z/(sigma*sqrt(2)) ))
    def pdf(self, z):
        sigma = self.width.value * self._scale
        if sigma <= 0.0:
            return inf*(z==0)
        else:
            return exp(z**2/(-2*sigma**2)) / sqrt(2*pi*sigma**2)
    def ppf(self, z):
        sigma = self.width.value * self._scale
        if sigma <= 0.0:
            return 0*z
        else:
            return sigma*sqrt(2)*erfinv(2*z-1)

class Linear(Interface):
    """
    Linear interface.

    *width*  full width of the interface

    *name* (string: "tanh")

    The linear profile has the form::

        CDF(z) = 2/w*z if |z|<w/2, 0 if z<-w/2, 1 otherwise
        PDF(z) = 1/w if |z|<w/2, otherwise 0
        PPF(z) = w/2*z if |z|<w/2, -w/2 if z<-w/2, w/2 otherwise
    """
    def __init__(self, width=0, name="linear"):
        self.width = Par.default(width, limits=(0,inf), name=name)
    def parameters(self):
        return self.width
    def cdf(self, z):
        w = float(self.width.value)
        if w <= 0.0:
            return 1.*(z >= 0)
        else:
            return numpy.clip(z/w + 0.5,0,1)
    def pdf(self, z):
        w = float(self.width.value)
        if w <= 0.0:
            return inf*(z==0)
        else:
            return (abs(z)<w/2)/w
    def ppf(self, z):
        w = float(self.width.value)
        if w <= 0.0:
            return 0*z
        else:
            return numpy.clip(2*z/w,-w/2,w/2)

class Tanh(Interface):
    """
    Hyperbolic tangent profile

    *width* (Parameter: 0 Angstroms)

        1-sigma equivalent roughness.  For roughness w measured by the
        full width at half maximum (FWHM), use Tanh.as_fwhm(w).

    *name* (string: "tanh")

    The tanh profile has the form::

        CDF(z) = (1 + tanh(C/w*z))/2
        PDF(z) = C/(2*w) * sech((C/w)*z)**2
        PPF(z) = (w/C) * atanh(2*z-1)

    where w is the interface roughness and C is a scaling constant.
    C is atanh(erf(1/sqrt(2))) for width w defined by 1-sigma, or
    C is 2*acosh(sqrt(2)) for widht 2 defined by FWHM.

    This profile was derived from the free energy of a nonuniform system::

        J. W. Cahn and J. E. Hilliard, J. Chem. Phys. 28, 258 (1958)

    Note that this profile has an analytic solution.  See::

        E. S. Wu, and W. W. Webb, Phys Rev A 8(4) 2065-2076 (1973)
    """

    # Derivation
    # ==========
    #
    # To find C where w is defined as 1-sigma equivalent, use the
    # identity Erf.CDF(z=sigma;w=sigma) = tanh.CDF(z=sigma;w=sigma).
    # This simplifies to::
    #
    #    erf.CDF  = (1+erf(z/(w*sqrt(2)))/2 = (1+erf(1/sqrt(2)))/2
    #    tanh.CDF = (1+tanh(C/w*z))/2       = (1+tanh(C))/2
    #
    #    erf.CDF = tanh.CDF => C = atanh(erf(1/sqrt(2)))
    #
    # To find C where w is defined as FWHM, use the equivalent probability
    # density function::
    #
    #    PDF(z) = C/2w * sech(C/w*z)**2
    #
    # Solving PDF(w/2) = PDF(0)/2 yields::
    #
    #    Pw = PDF(w/2) = C/2w * sech(C/2)**2
    #    Po = PDF(0) = C/2w * sech(0)**2/2 = C/2w
    #
    #    Pw = Po/2 => sech(C/2)**2 = 1/2
    #              => C = 2 acosh(sqrt(2))
    #
    C = atanh(erf(1/sqrt(2)))
    Cfwhm = 2*acosh(sqrt(2))
    @classmethod
    def as_fwhm(cls, *args, **kw):
        """
        Defines interface using FWHM rather than 1-sigma.
        """
        self = cls(*args, **kw)
        self._scale = Tanh.C/Tanh.Cfwhm
        return self
    def __init__(self, width=0, name="tanh"):
        self._scale = 1
        self.width = Par.default(width, limits=(0,inf), name=name)
    def parameters(self):
        return [self.width]
    def cdf(self, z):
        w = self.width.value * self._scale
        if w <= 0.0:
            return 1.*(z > 0)
        else:
            return 0.5*( 1 + tanh((Tanh.C/w)*z))
    def pdf(self, z):
        w = self.width.value * self._scale
        if w <= 0.0:
            return inf*(z==0)
        else:
            return sech( (Tanh.C/w)*z )**2 * (Tanh.C / (2*w))
    def ppf(self, z):
        w = self.width.value * self._scale
        if w <= 0.0:
            return 0*z
        else:
            return (w/Tanh.C)*atanh(2*z-1)

def demo_fwhm():
    """
    Show the available interface functions and the corresponding probability
    density functions.
    """

    # Plot the cdf and pdf
    import pylab
    w = 10
    perf = Erf.as_fwhm(w)
    ptanh = Tanh.as_fwhm(w)

    z=pylab.linspace(-w,w,800)
    pylab.subplot(211)
    pylab.plot(z,perf.cdf(z),hold=False)
    pylab.plot(z,ptanh.cdf(z),hold=True)
    pylab.legend(['erf','tanh'])
    pylab.grid(True)
    pylab.subplot(212)
    pylab.plot(z,perf.pdf(z),'b',hold=False)
    pylab.plot(z,ptanh.pdf(z),'g',hold=True)
    pylab.legend(['erf','tanh'])

    # Show fwhm
    arrowprops=dict(arrowstyle='wedge',connectionstyle='arc3',fc='0.6')
    bbox=dict(boxstyle='round', fc='0.8')
    pylab.annotate('erf FWHM',xy=(w/2,perf.pdf(0)/2),
                   xytext=(-35,10),textcoords="offset points",
                   arrowprops=arrowprops, bbox=bbox)
    pylab.annotate('tanh FWHM',xy=(w/2,ptanh.pdf(0)/2),
                   xytext=(-35,-35),textcoords="offset points",
                   arrowprops=arrowprops,bbox=bbox)

    pylab.grid(True)
    pylab.show()

def demo():
    """
    Show the available interface functions and the corresponding probability
    density functions.
    """

    # Plot the cdf and pdf
    import pylab
    w = 10
    perf = Erf(w)
    ptanh = Tanh(w)
    plinear = Linear(2.35*w)

    arrowprops=dict(arrowstyle='wedge',connectionstyle='arc3',fc='0.6')
    bbox=dict(boxstyle='round', fc='0.8')

    z=pylab.linspace(-3*w,3*w,800)
    pylab.subplot(211)
    pylab.plot(z,perf.cdf(z),hold=False)
    pylab.plot(z,ptanh.cdf(z),hold=True)
    pylab.plot(z,plinear.cdf(z),hold=True)
    pylab.axvline(w,linewidth=2)
    pylab.annotate('1-sigma',xy=(w*1.1,0.2))
    pylab.legend(['erf','tanh'])
    pylab.grid(True)
    pylab.subplot(212)
    pylab.plot(z,perf.pdf(z),hold=False)
    pylab.plot(z,ptanh.pdf(z),hold=True)
    pylab.plot(z,plinear.pdf(z),hold=True)
    pylab.axvline(w, linewidth=2)
    pylab.annotate('1-sigma',xy=(w*1.1,0.2))
    pylab.legend(['erf','tanh','linear'])
    pylab.grid(True)
    pylab.show()

def _test_one(p,w):
    import scipy.integrate as sum
    # Check that the pdf approximately matchs the numerical integral
    # Check that integral(-inf,0) of pdf sums to 0.5
    err = abs(sum.romberg(p.pdf,-20*w,0,tol=1e-15) - 0.5)
    assert err<1e-14,"cdf(0) == 0.5 yields %g"%err

    # Check that integral(-inf,x) of pdf sums to cdf when x != 0
    err = abs(sum.romberg(p.pdf,-20*w,w/6,tol=1e-15) - p.cdf(w/6))
    assert err<1e-14,"cdf(w/6) == w/6 yields %g"%err

    # Check that P = cdf(ppf(P))
    P = 0.002
    err = abs(p.cdf(p.ppf(P)) - P)
    assert err < 1e-14,"p(lo) = P yields %g"%err

def test():
    w=1.5
    _test_one(Erf(w),w=w)
    _test_one(Tanh(w),w=w)
    _test_one(Erf.as_fwhm(2.35*w),w)
    _test_one(Tanh.as_fwhm(2*w),w)

if __name__ == "__main__":
    import sys; sys.path.append('..')
    demo()
    #demo_fwhm()
    #test()