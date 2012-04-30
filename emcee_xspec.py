#!/usr/bin/env python

"""
Use EMCEE to do MCMC in Xspec.
Jeremy Sanders 2012

Requires Python 2.7+, numpy, scipy and emcee
"""

import sys
import argparse

import numpy as N
import emcee

import emcee_pool

def doMCMC(xcm, nwalkers=100, nburn=100, niters=1000, systems = ['localhost'],
           outchain = 'out.dat'):
    """Do the actual MCMC process."""

    # pool controls xspecs and parameters
    # this should be a multiprocessing.Pool, but we implement
    # our own pool as it is much more reliable
    pool = emcee_pool.Pool(xcm, systems)

    # make some initial parameters for each walker, based on the xcm
    # file and adding on some randomness
    parvals = N.array(pool.parvals)
    # use 1% of parameter initially, or 0.01 if zero
    parerrs = N.where( parvals == 0., 0.01, parvals * 0.01 )
    p0 = [ N.random.normal(parvals, parerrs) for i in xrange(nwalkers) ]

    # sample the mcmc
    sampler = emcee.EnsembleSampler(nwalkers, len(parvals), None,
                                    pool=pool)

    # burn in
    pos, prob, state = sampler.run_mcmc(p0, nburn)
    sampler.reset()

    # run for real
    sampler.run_mcmc(pos, niters, rstate0=state)

    print "Writing", outchain
    writeXSpecChain(outchain, sampler.chain,
                    sampler.lnprobability, pool.params, pool.paridxs)

    return sampler

def writeXSpecChain(filename, chain, lnprob, params, paridxs):
    """Write an xspec text chain file."""
    with open(filename, 'w') as f:
        f.write('! Markov chain file generated by xspec "chain" command.\n')
        f.write('!    Do not modify, else file may not reload properly.\n')
        length = chain.shape[0] * chain.shape[1]
        width = chain.shape[2]
        f.write('!Length: %i  Width: %i\n' % (length, width+1))

        # header for contents of file
        hdr = []
        for idx in paridxs:
            hdr.append("%i %s %s" % (
                    idx, params[idx-1]['name'],
                    "0" if params[idx-1]['unit'] == ""
                    else params[idx-1]['unit']))
        hdr.append("Chi-Squared")
        f.write('!%s\n' % ' '.join(hdr))

        for w, walker in enumerate(N.dstack((chain, N.expand_dims(-lnprob, 2)))):
            #f.write('! walker %i\n' % i)
            for line in walker:
                fmt = '\t'.join(['%g']*len(line))
                f.write( fmt % tuple(line) + '\n' )

def main():
    """Main program."""

    p = argparse.ArgumentParser(
        description="Xspec MCMC with EMCEE. Jeremy Sanders 2012.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    p.add_argument("xcm", metavar="XCM",
                   help="Input XCM file")
    p.add_argument("--niters", metavar="N", type=int, default=5000,
                   help="Number of iterations")
    p.add_argument("--nburn", metavar="N", type=int, default=500,
                   help="Number of burn iterations")
    p.add_argument("--nwalkers", metavar="N", type=int, default=50,
                   help="Number of walkers")
    p.add_argument("--systems", default="localhost", metavar="LIST",
                   help="Space separated list of systems to run on")
    p.add_argument("--output-npz", default="emcee.npz", metavar="FILE",
                   help="Output NPZ file")
    p.add_argument("--output-chain", default="emcee.chain", metavar="FILE",
                   help="Output text file")

    args = p.parse_args()

    print "Starting MCMC"
    sampler = doMCMC( args.xcm,
                      systems = args.systems.split(),
                      nwalkers = args.nwalkers,
                      nburn = args.nburn,
                      niters = args.niters,
                      outchain = args.output_chain,
                      )

    print "Writing", args.output_npz
    N.savez( args.output_npz,
             chain = sampler.chain,
             lnprobability = sampler.lnprobability,
             acceptance_fraction = sampler.acceptance_fraction )

    print "Done"

if __name__ == '__main__':
    main()
