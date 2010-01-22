# This program is public domain.
"""
Optical matrix form of the reflectivity calculation.

O.S. Heavens, Optical Properties of Thin Solid Films
"""
from numpy import asarray, isscalar, empty, ones_like
from numpy import sqrt, exp, pi

def refl(kz,depth,rho,mu,sigma=0):
    """
    Reflectometry as a function of kz

    kz ([n] inv angstrom)
        Scattering vector 2*pi*sin(theta)/wavelength. This is Qz/2.
    depth ([m] angstrom)
        thickness of each layer.  The thickness of the incident medium
        and substrate are ignored.
    rho,mu ([n x m] uNb)
        scattering length density and absorption of each layer for each kz
    sigma ([m-1] angstrom)
        interfacial roughness.  This is the roughness between a layer
        and the subsequent layer.  There is no interface associated
        with the substrate.  The sigma array should have at least m-1
        entries, though it may have m with the last entry ignored.
    """
    if isscalar(kz): kz = array([kz], 'd')
    n = len(kz)
    m = len(depth)

    # Make everything into arrays
    depth = asarray(depth,'d')
    rho = asarray(rho,'d')
    mu = mu*ones_like(rho) if isscalar(mu) else asarray(mu,'d')
    sigma = sigma*ones(m-1,'d') if isscalar(sigma) else asarray(sigma,'d')

    ## For kz < 0 we need to reverse the order of the layers
    ## Note that the interface array sigma is conceptually one
    ## shorter than rho,mu so when reversing it, start at n-1.
    ## This allows the caller to provide an array of length n
    ## corresponding to rho,mu or of length n-1.
    idx = (kz>=0)
    r = empty(len(kz),'D')
    r[idx] = calc(kz[idx], depth, rho, mu, sigma)
    r[~idx] = calc(abs(kz[~idx]),
                   depth[::-1], rho[:,::-1], mu[:,::-1], sigma[m-2::-1])
    return r


def calc(kz, depth, rho, mu, sigma):
    if len(kz) == 0: return kz

    # Complex index of refraction is relative to the incident medium.
    # We can get the same effect using kz_rel^2 = kz^2 + 4*pi*rho_o
    # in place of kz^2, and ignoring rho_o
    kz_sq = kz**2 + 4e-6*pi*rho[:,0]
    k = kz

    # According to Heavens, the initial matrix should be [ 1 F; F 1],
    # which we do by setting B=I and M0 to [1 F; F 1].  An extra matrix
    # multiply versus some coding convenience.
    B11 = 1
    B22 = 1
    B21 = 0
    B12 = 0
    for i in xrange(0,len(depth)-1):
        k_next = sqrt(kz_sq - 4e-6*pi*(rho[:,i+1] + 0.5j*mu[:,i+1]))
        F = (k - k_next) / (k + k_next)
        F *= exp(-2*k*k_next*sigma[i]**2)
        M11 = exp(1j*k*depth[i]) if i>0 else 1
        M22 = exp(-1j*k*depth[i]) if i>0 else 1
        M21 = F*M11
        M12 = F*M22
        C1 = B11*M11 + B21*M12
        C2 = B11*M21 + B21*M22
        B11 = C1
        B21 = C2
        C1 = B12*M11 + B22*M12
        C2 = B12*M21 + B22*M22
        B12 = C1
        B22 = C2
        k = k_next

    r = B12/B11
    return r