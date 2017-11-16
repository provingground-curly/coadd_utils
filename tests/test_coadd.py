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

"""Test lsst.coadd.utils.Coadd
"""
import os
import unittest

import numpy

import lsst.utils
import lsst.utils.tests
import lsst.afw.geom as afwGeom
import lsst.afw.image as afwImage
import lsst.afw.image.utils as imageUtils
import lsst.coadd.utils as coaddUtils
import lsst.pex.policy as pexPolicy
from lsst.log import Log

try:
    display
except NameError:
    display = False

Log.getLogger("coadd.utils").setLevel(Log.INFO)

try:
    AfwdataDir = lsst.utils.getPackageDir('afwdata')
except Exception:
    AfwdataDir = None
# path to LsstSim calexp relative to afwData package root
SimCalexpSubpath = os.path.join("ImSim", "calexp", "v85408556-fr", "R23", "S11.fits")


class CoaddTestCase(lsst.utils.tests.TestCase):
    """A test case for Coadd
    """

    @unittest.skipUnless(AfwdataDir, "afwdata not available")
    def testAddOne(self):
        """Add a single exposure; make sure coadd = input, appropriately scaled
        """
        calexpPath = os.path.join(AfwdataDir, SimCalexpSubpath)
        inExp = afwImage.ExposureF(calexpPath)
        inMaskedImage = inExp.getMaskedImage()
        for badMaskPlanes in (
            (),
            ("NO_DATA", "BAD"),
        ):
            coadd = coaddUtils.Coadd(
                bbox=inExp.getBBox(),
                wcs=inExp.getWcs(),
                badMaskPlanes=badMaskPlanes,
            )
            coadd.addExposure(inExp)
            coaddExp = coadd.getCoadd()
            coaddMaskedImage = coaddExp.getMaskedImage()

            inMaskArr = inMaskedImage.getMask().getArray()
            badMask = coadd.getBadPixelMask()
            skipMaskArr = inMaskArr & badMask != 0

            msg = "coadd != input exposure"
            self.assertMaskedImagesNearlyEqual(inMaskedImage, coaddMaskedImage, skipMask=skipMaskArr, msg=msg)

    def assertWcsSame(self, wcs1, wcs2):
        for xPixPos in (0, 1000, 2000):
            for yPixPos in (0, 1000, 2000):
                fromPixPos = afwGeom.Point2D(xPixPos, yPixPos)
                sky1 = wcs1.pixelToSky(fromPixPos)
                sky2 = wcs2.pixelToSky(fromPixPos)
                if not numpy.allclose(sky1.getPosition(), sky2.getPosition()):
                    self.fail("wcs do not match at fromPixPos=%s: sky1=%s != sky2=%s" %
                              (fromPixPos, sky1, sky2))
                toPixPos1 = wcs1.skyToPixel(sky1)
                toPixPos2 = wcs2.skyToPixel(sky1)
                if not numpy.allclose((xPixPos, yPixPos), toPixPos1):
                    self.fail("wcs do not match at sky1=%s: fromPixPos=%s != toPixPos1=%s" %
                              (sky1, fromPixPos, toPixPos1))
                if not numpy.allclose(toPixPos1, toPixPos2):
                    self.fail("wcs do not match at fromPixPos=%s, sky1=%s: toPixPos1=%s != toPixPos2=%s" %
                              (fromPixPos, sky1, toPixPos1, toPixPos2))

    @unittest.skipUnless(AfwdataDir, "afwdata not available")
    def testGetters(self):
        """Test getters for coadd
        """
        calexpPath = os.path.join(AfwdataDir, SimCalexpSubpath)
        inExp = afwImage.ExposureF(calexpPath)
        bbox = inExp.getBBox()
        wcs = inExp.getWcs()
        for badMaskPlanes, bbox in (
            (("NO_DATA",), afwGeom.Box2I(afwGeom.Point2I(1, 2), afwGeom.Extent2I(100, 102))),
            (("NO_DATA", "BAD"), afwGeom.Box2I(afwGeom.Point2I(0, 0), afwGeom.Extent2I(100, 102))),
            (("NO_DATA",), afwGeom.Box2I(afwGeom.Point2I(104, 0), afwGeom.Extent2I(5, 10))),
            (("NO_DATA",), afwGeom.Box2I(afwGeom.Point2I(0, 1020), afwGeom.Extent2I(100, 102))),
        ):
            coadd = coaddUtils.Coadd(
                bbox=bbox,
                wcs=wcs,
                badMaskPlanes=badMaskPlanes,
            )
            badPixelMask = 0
            for maskPlaneName in badMaskPlanes:
                badPixelMask += afwImage.Mask.getPlaneBitMask(maskPlaneName)
            self.assertEqual(bbox, coadd.getBBox())
            self.assertEqual(badPixelMask, coadd.getBadPixelMask())
            self.assertWcsSame(wcs, coadd.getWcs())

    @unittest.skipUnless(AfwdataDir, "afwdata not available")
    def testFilters(self):
        """Test that the coadd filter is set correctly
        """
        filterPolicyFile = pexPolicy.DefaultPolicyFile("afw", "SdssFilters.paf", "tests")
        filterPolicy = pexPolicy.Policy.createPolicy(
            filterPolicyFile, filterPolicyFile.getRepositoryPath(), True)
        imageUtils.defineFiltersFromPolicy(filterPolicy, reset=True)

        unkFilter = afwImage.Filter()
        gFilter = afwImage.Filter("g")
        rFilter = afwImage.Filter("r")

        calexpPath = os.path.join(AfwdataDir, SimCalexpSubpath)
        inExp = afwImage.ExposureF(calexpPath, afwGeom.Box2I(afwGeom.Point2I(0, 0), afwGeom.Extent2I(10, 10)),
                                   afwImage.PARENT)
        coadd = coaddUtils.Coadd(
            bbox=inExp.getBBox(),
            wcs=inExp.getWcs(),
            badMaskPlanes=("NO_DATA", "BAD"),
        )

        inExp.setFilter(gFilter)
        coadd.addExposure(inExp)
        self.assertEqualFilters(coadd.getCoadd().getFilter(), gFilter)
        self.assertEqualFilterSets(coadd.getFilters(), (gFilter,))
        coadd.addExposure(inExp)
        self.assertEqualFilters(coadd.getCoadd().getFilter(), gFilter)
        self.assertEqualFilterSets(coadd.getFilters(), (gFilter,))

        inExp.setFilter(rFilter)
        coadd.addExposure(inExp)
        self.assertEqualFilters(coadd.getCoadd().getFilter(), unkFilter)
        self.assertEqualFilterSets(coadd.getFilters(), (gFilter, rFilter))

    def assertEqualFilters(self, f1, f2):
        """Compare two filters

        Right now compares only the name, but if == ever works for Filters (ticket #1744)
        then use == instead
        """
        self.assertEqual(f1.getName(), f2.getName())

    def assertEqualFilterSets(self, fs1, fs2):
        """Assert that two collections of filters are equal, ignoring order
        """
        self.assertEqual(set(f.getName() for f in fs1), set(f.getName() for f in fs2))


class MemoryTester(lsst.utils.tests.MemoryTestCase):
    pass


def setup_module(module):
    lsst.utils.tests.init()


if __name__ == "__main__":
    lsst.utils.tests.init()
    unittest.main()
