"""
100 A Ni film with attached data.
"""
from refl1d.names import *
    
nickel = Material('Ni')
sample = silicon(0,10) | nickel(100,10) | air

instrument = SNS.Liquids()
files = ['nifilm-tof-%d.dat'%d for d in 1,2,3,4] 
probe = ProbeSet(instrument.load(f) for f in files)

M = Experiment(probe=probe, sample=sample)

problem = FitProblem(M)

