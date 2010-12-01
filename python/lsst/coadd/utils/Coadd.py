# 
# LSST Data Management System
# Copyright 2008, 2009, 2010 LSST Corporation.
# 
# This product includes software developed by the
# LSST Project (http://www.lsst.org/).
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the LSST License Statement and 
# the GNU General Public License along with this program.  If not, 
# see <http://www.lsstcorp.org/LegalNotices/>.
#
import sys
import lsst.pex.logging as pexLog
import lsst.afw.image as afwImage
import lsst.afw.math as afwMath
import makeBitMask
import makeBlankCoadd
import utilsLib

__all__ = ["Coadd"]

class Coadd(object):
    """Basic coadd.
    
    Exposures are (by default) warped to the coadd WCS and then added to the coadd
    with a weight of 1 / clipped mean variance.
    
    This class may be subclassed to implement other coadd techniques.
    Typically this is done by overriding addExposure.
    """
    def __init__(self, dimensions, wcs, policy, logName="coadd.utils.Coadd"):
        """Create a coadd
        
        Inputs:
        - dimensions: dimensions of coadd; must be the type of object returned by
            exposure.getMaskedImage().getDimensions() (presently std::pair<int, int>)
        - wcs: WCS of coadd
        - policy: see policy/coadd_dict.paf
        """
        self._log = pexLog.Log(pexLog.Log.getDefaultLog(), logName)
        self._policy = policy

        allowedMaskPlanes = policy.get("allowedMaskPlanes")
        self._badPixelMask = makeBitMask.makeBitMask(allowedMaskPlanes.split(), doInvert=True)

        self._wcs = wcs # for convenience
        blankMaskedImage = afwImage.MaskedImageF(dimensions)
        self._coadd = afwImage.ExposureF(blankMaskedImage, wcs)

        self._weightMap = afwImage.ImageF(self._coadd.getMaskedImage().getDimensions(), 0)

    def addExposure(self, exposure, weightFactor=1.0):
        """Add an Exposure to the coadd
        
        Inputs:
        - exposure: Exposure to add to coadd; must be background-subtracted and warped to match the coadd.
        - weightFactor: extra weight factor for this exposure; weight = weightFactor / clipped mean variance
        
        Subclasses may override to preprocess the exposure or change the way it is added to the coadd.
        """
        self._basicAddExposure(warpedExposure, weightFactor)
        
        return warpedExposure

    def getCoadd(self):
        """Get the coadd Exposure, as computed so far
        
        Return the coadd Exposure consisting of the reference exposure and all exposures
        you have added so far. You may call addExposure and getCoadd as often as you like.
        """
        # make a deep copy so I can scale it
        coaddMaskedImage = self._coadd.getMaskedImage()
        scaledMaskedImage = coaddMaskedImage.__class__(coaddMaskedImage, True)

        # set the edge pixels
        utilsLib.setCoaddEdgeBits(scaledMaskedImage.getMask(), self._weightMap)
        
        # scale non-edge pixels by weight map
        scaledMaskedImage /= self._weightMap
        
        return afwImage.makeExposure(scaledMaskedImage, self._wcs)
        
    def getWeightMap(self):
        """Get the weight map
        
        The weight map is a float Image of the same dimensions as the coadd;
        the value of each pixel is the number of input images
        that contributed to the associated pixel of the coadd.
        """
        return self._weightMap
    
    def _basicAddExposure(self, exposure, weightFactor=1.0):
        """Add a warped exposure the coadd

        Inputs:
        - exposure: Exposure to add to coadd; must be background-subtracted and warped to match the coadd.
        - weightFactor: extra weight factor for this exposure; weight = weightFactor / clipped mean variance
        """
        # compute variance using a bit of sigma-clipping (though this is probably excessive)
        statsControl = afwMath.StatisticsControl()
        statsControl.setNumSigmaClip(3.0)
        statsControl.setNumIter(2)
        statsControl.setAndMask(self._badPixelMask)
        maskedImage = exposure.getMaskedImage()
        statObj = afwMath.makeStatistics(maskedImage.getVariance(), maskedImage.getMask(),
            afwMath.MEANCLIP, statsControl)
        meanVar, meanVarErr = statObj.getResult(afwMath.MEANCLIP);
        weight = weightFactor / float(meanVar)

        self._log.log(pexLog.Log.INFO, "add masked image to coadd; weight=%0.3g" % (weight,))

        utilsLib.addToCoadd(self._coadd.getMaskedImage(), self._weightMap,
            maskedImage, self._badPixelMask, weight)
