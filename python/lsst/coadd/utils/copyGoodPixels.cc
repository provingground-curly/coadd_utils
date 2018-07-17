/*
 * LSST Data Management System
 * Copyright 2008-2016  AURA/LSST.
 *
 * This product includes software developed by the
 * LSST Project (http://www.lsst.org/).
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the LSST License Statement and
 * the GNU General Public License along with this program.  If not,
 * see <https://www.lsstcorp.org/LegalNotices/>.
 */

#include "pybind11/pybind11.h"

#include "lsst/coadd/utils/copyGoodPixels.h"

namespace py = pybind11;
using namespace pybind11::literals;

namespace lsst {
namespace coadd {
namespace utils {

namespace {

template <typename ImagePixelT>
void declareCopyGoodPixels(py::module &mod) {
    namespace afwImage = lsst::afw::image;

    mod.def("copyGoodPixels",
            (int (*)(afwImage::Image<ImagePixelT> &, afwImage::Image<ImagePixelT> const &)) & copyGoodPixels,
            "destImage"_a, "srcImage"_a);
    mod.def("copyGoodPixels",
            (int (*)(afwImage::MaskedImage<ImagePixelT> &, afwImage::MaskedImage<ImagePixelT> const &,
                     afwImage::MaskPixel const)) &
                    copyGoodPixels,
            "destImage"_a, "srcImage"_a, "badPixelMask"_a);
}

}  // <anonymous>

PYBIND11_MODULE(copyGoodPixels, mod) {
    py::module::import("lsst.afw.image");

    declareCopyGoodPixels<double>(mod);
    declareCopyGoodPixels<float>(mod);
    declareCopyGoodPixels<int>(mod);
    declareCopyGoodPixels<std::uint16_t>(mod);
}

}  // utils
}  // coadd
}  // lsst
