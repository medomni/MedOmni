"""Decoders for image families: radiographs, fundus, echo, OCT, OCTA, FLIO, heightmaps."""
import math

from ..aliases import _aliases_for
from ._util import _confined_companion, _read_json_manifest
from ..errors import Degraded


def _read_image(path, root):
    """An image file -> one plane of 8-bit pixels, as cxr-radiograph-2d declares.

    The protocol is {format: image, planes: 1, dtype: u8, ndim: 2}. Conformance
    is verified here and never inferred. A file that does not conform degrades,
    it is not reshaped into something plausible.
    """
    try:
        import numpy as np
        from PIL import Image
    except ImportError as exc:          # a build error, not a caller error
        raise RuntimeError(f"this image has no imaging library: {exc}")

    try:
        img = Image.open(path)
        img.load()
    except Exception as exc:
        raise Degraded(f"the file is not a readable image: {exc}")

    notes = []
    if img.mode == "L":
        pixels = np.asarray(img)
    elif img.mode in ("RGB", "RGBA"):
        planes = np.asarray(img.convert("RGB"))
        first = planes[..., 0]
        if not (np.array_equal(first, planes[..., 1])
                and np.array_equal(first, planes[..., 2])):
            raise Degraded(
                f"the image carries color, the family declares one plane (mode {img.mode})")
        pixels = first
        notes.append(f"one plane read from a {img.mode} file; the three planes are equal")
    else:
        raise Degraded(
            f"image mode '{img.mode}' does not conform; the family declares 8-bit, one plane")

    if pixels.ndim != 2:
        raise Degraded(f"the image has {pixels.ndim} dimensions, the family declares 2")
    if pixels.dtype != np.uint8:
        raise Degraded(f"the image is {pixels.dtype}, the family declares u8")
    return {"kind": "image", "pixels": pixels,
            "height": int(pixels.shape[0]), "width": int(pixels.shape[1]),
            "notes": notes}


def _read_fundus_dicom(path, root):
    import numpy as np
    import pydicom
    from pydicom.errors import InvalidDicomError
    try:
        dataset = pydicom.dcmread(path)
        if int(getattr(dataset, 'NumberOfFrames', 1)) != 1:
            raise Degraded('fundus input must contain one frame')
        if (dataset.BitsAllocated != 8 or dataset.BitsStored != 8
                or dataset.PixelRepresentation != 0):
            raise Degraded('the fundus family requires unsigned eight-bit pixels')
        photometric = dataset.PhotometricInterpretation
        colour_spaces = {'RGB'} | set(_aliases_for('fundus-photography-2d')['colors'])
        if photometric in colour_spaces and dataset.SamplesPerPixel == 3:
            role = 'colour-3plane'
        elif photometric in ('MONOCHROME1', 'MONOCHROME2') and dataset.SamplesPerPixel == 1:
            role = 'infrared-1plane'
        else:
            raise Degraded(f'unsupported fundus photometric interpretation: {photometric}')
        pixels = dataset.pixel_array
    except (InvalidDicomError, AttributeError, ValueError, OSError, RuntimeError, NotImplementedError) as exc:
        raise Degraded(f'cannot read fundus DICOM: {exc}') from exc
    expected = (dataset.Rows, dataset.Columns, 3) if role == 'colour-3plane' else (dataset.Rows, dataset.Columns)
    if pixels.shape != expected or pixels.dtype != np.uint8:
        raise Degraded('fundus pixel shape does not match its DICOM header')
    notes = ([f'DICOM {photometric} pixels were converted to RGB']
             if photometric.startswith('YBR') else [])
    return {'kind': 'image', 'pixels': pixels, 'role': role,
            'height': int(dataset.Rows), 'width': int(dataset.Columns), 'notes': notes}


def _read_echo_study(path, root):
    import numpy as np
    import pydicom
    manifest = _read_json_manifest(path, root)
    names = manifest.get('files')
    if not isinstance(names, list) or not names:
        raise Degraded('echo study manifest needs a non-empty files list')
    videos = []
    for name in names:
        target = _confined_companion(path, root, name)
        try:
            dataset = pydicom.dcmread(target)
            pixels = np.asarray(dataset.pixel_array)
        except Exception as exc:
            raise Degraded(f'cannot read echo DICOM {name}: {exc}') from exc
        if pixels.ndim not in (3, 4) or not len(pixels):
            raise Degraded(f'echo DICOM {name} does not contain a video')
        videos.append(dict(path=str(target), pixels=pixels,
                           photometric=str(getattr(dataset, 'PhotometricInterpretation', ''))))
    return dict(kind='echo-study', videos=videos, notes=[])


def _read_echo_frame(path, root):
    import numpy as np
    try:
        if path.suffix.lower() == '.dcm':
            import pydicom
            dataset = pydicom.dcmread(path)
            pixels = np.asarray(dataset.pixel_array)
            if pixels.ndim == 4:
                pixels = pixels[len(pixels) // 2]
            elif pixels.ndim == 3 and pixels.shape[-1] not in (3, 4):
                pixels = pixels[len(pixels) // 2]
        else:
            from PIL import Image
            pixels = np.asarray(Image.open(path).convert('RGB'))
    except Exception as exc:
        raise Degraded(f'cannot read echo frame: {exc}') from exc
    if pixels.ndim == 2:
        pixels = np.repeat(pixels[..., None], 3, axis=2)
    if pixels.ndim != 3 or pixels.shape[-1] not in (3, 4):
        raise Degraded('echo frame must decode to two-dimensional RGB pixels')
    pixels = pixels[..., :3]
    if pixels.dtype != np.uint8:
        low, high = float(np.min(pixels)), float(np.max(pixels))
        if not math.isfinite(low + high) or high <= low:
            raise Degraded('echo frame has no finite intensity range')
        pixels = np.rint((pixels - low) * (255.0 / (high - low))).astype(np.uint8)
    return dict(kind='image', pixels=pixels, height=int(pixels.shape[0]),
                width=int(pixels.shape[1]), notes=[])


def _retinal_acquisition(dataset):
    """What the file says about its own acquisition, for encoders that need geometry or device.

    Reported, never required: every key is None when the file does not carry it,
    and no note is added, so an encoder with no use for it sees what it saw before.
    """
    def text(value):
        return str(value).strip() or None if value is not None else None
    spacing = dataset.get('PixelSpacing')
    if spacing is None:
        try:
            spacing = dataset.SharedFunctionalGroupsSequence[0].PixelMeasuresSequence[0].PixelSpacing
        except (AttributeError, IndexError, KeyError, TypeError):
            spacing = None
    try:
        spacing = tuple(float(v) for v in spacing) if spacing is not None and len(spacing) == 2 else None
    except (TypeError, ValueError):
        spacing = None
    try:
        structure = text(dataset.PrimaryAnatomicStructureSequence[0].CodeMeaning)
    except (AttributeError, IndexError, KeyError, TypeError):
        structure = None
    return dict(manufacturer=text(dataset.get('Manufacturer')), model=text(dataset.get('ManufacturerModelName')),
                pixel_spacing_mm=spacing, image_comments=text(dataset.get('ImageComments')),
                anatomic_structure=structure, protocol=text(dataset.get('ProtocolName')))


def _read_retinal_u8(path, family, ndim, frames=None):
    """Decode mono8 retinal frames, preserving native frame order and stored values."""
    import numpy as np
    import pydicom
    from pydicom.errors import InvalidDicomError
    notes = []
    try:
        dataset = pydicom.dcmread(path)
        count = int(dataset.get('NumberOfFrames', 1))
        rows, columns = int(dataset.Rows), int(dataset.Columns)
        if min(count, rows, columns) < 1 or count * rows * columns > 300_000_000:
            raise ValueError('empty or oversized retinal image')
        if int(dataset.BitsAllocated) != 8 or int(dataset.BitsStored) != 8 or int(dataset.PixelRepresentation) != 0:
            raise ValueError('requires unsigned mono8 stored pixels')
        if (ndim == 2 and count != 1) or (ndim == 3 and count < 2):
            raise ValueError('frame count does not match family dimensionality')
        if frames is not None and count != frames:
            raise ValueError(f'requires {frames} frames in acquisition order')
        color = str(dataset.PhotometricInterpretation)
        planes = int(dataset.SamplesPerPixel)
        allowed_color = color in _aliases_for(family)['colors']
        if not ((color in ('MONOCHROME1', 'MONOCHROME2') and planes == 1)
                or (allowed_color and planes == 3 and ndim == 2)):
            raise ValueError('photometric interpretation is not declared for this family')
        pixels = dataset.pixel_array
        if allowed_color and planes == 3:
            if pixels.shape != (rows, columns, 3):
                raise ValueError('unexpected color pixel shape')
            # pydicom returns RGB after decoding YBR.
            pixels = np.rint(pixels.astype(np.float64) @ np.array([0.299, 0.587, 0.114])).astype(np.uint8)
            notes.append(f'{color} decoded to RGB and converted to mono8 using 0.299R+0.587G+0.114B.')
        expected = (rows, columns) if ndim == 2 else (count, rows, columns)
        if pixels.shape != expected or pixels.dtype != np.uint8:
            raise ValueError('pixel shape or dtype does not match the protocol')
        if color == 'MONOCHROME1':
            pixels = 255 - pixels
            notes.append('MONOCHROME1 inverted to MONOCHROME2 intensity convention.')
    except (InvalidDicomError, OSError, ValueError, AttributeError, TypeError, RuntimeError, NotImplementedError) as exc:
        raise Degraded(f'cannot read retinal DICOM: {exc}') from exc
    notes.append('Stored pixel intensities; no spatial resampling, modality LUT or physical calibration.')
    return dict(kind='image', pixels=pixels, notes=notes, acquisition=_retinal_acquisition(dataset))


def _read_oct_raster(path, root):
    return _read_retinal_u8(path, 'oct-volume-raster-mono8-3d', 3)


def _read_octa_enface(path, root):
    return _read_retinal_u8(path, 'octa-enface-slab-mono8-2d', 2)


def _read_octa_flowcube(path, root):
    return _read_retinal_u8(path, 'octa-flowcube-mono8-3d', 3)


# The optic-nerve-head set the family declares: 24 radial lines through the
# disc and 3 concentric circles around it. They are not a stack and they are
# not interchangeable — a circle scan cuts the peripapillary nerve fibre layer
# and a radial line crosses the cup — so which frame is which is something any
# encoder of this family needs, and it is a property of the data rather than of
# a model. Geometry comes from each frame's own reference coordinates: a line
# carries two endpoints, a circle carries the polyline that traces it. Nothing
# reads geometry off a frame's position in the file.
_BSCANSET_RADIAL = 24
_BSCANSET_CIRCLE = 3


def _read_oct_radial(path, root):
    """The 24 + 3 set, with each frame's geometry when the file records it.

    Geometry is reported, never required: a file that does not carry per-frame
    reference coordinates still conforms to the family, and an encoder that
    reads intensity alone has no use for them. An encoder that does need to
    tell a radial line from a circle refuses the file itself — which is the
    difference between what the data is and what a model needs of it.
    """
    import pydicom
    sample = _read_retinal_u8(path, 'oct-bscanset-radial24-circle3-mono8', 3, frames=27)
    try:
        groups = pydicom.dcmread(path, stop_before_pixels=True).PerFrameFunctionalGroupsSequence
        kinds = ['radial' if len(group.OphthalmicFrameLocationSequence[0].ReferenceCoordinates) == 4
                 else 'circle' for group in groups]
    except (AttributeError, IndexError, KeyError, TypeError, ValueError):
        # No geometry keys, and no note: a reader with no use for geometry
        # should see exactly the response it saw before, and the encoder that
        # needs geometry says so itself when it refuses the file.
        return sample
    if len(kinds) != int(sample['pixels'].shape[0]):
        raise Degraded(f"{len(kinds)} frame geometries for {sample['pixels'].shape[0]} frame(s)")
    radial = [i for i, kind in enumerate(kinds) if kind == 'radial']
    circle = [i for i, kind in enumerate(kinds) if kind == 'circle']
    if len(radial) != _BSCANSET_RADIAL or len(circle) != _BSCANSET_CIRCLE:
        raise Degraded(
            f'the family declares {_BSCANSET_RADIAL} radial and {_BSCANSET_CIRCLE} circle '
            f'scans; this file holds {len(radial)} and {len(circle)}')
    sample['frame_kinds'] = kinds
    sample['radial_frames'] = radial
    sample['circle_frames'] = circle
    return sample


def _read_fundus_faf(path, root):
    return _read_retinal_u8(path, 'fundus-faf-mono8-2d', 2)


def _read_flio(path, root):
    import pydicom
    from pydicom.errors import InvalidDicomError
    try:
        dataset = pydicom.dcmread(path)
        if (int(dataset.Rows), int(dataset.Columns), int(dataset.get('NumberOfFrames', 1))) != (256, 256, 1024):
            raise ValueError('requires 256x256 spatial pixels and 1024 time frames')
        if (int(dataset.BitsAllocated), int(dataset.BitsStored), int(dataset.PixelRepresentation), int(dataset.SamplesPerPixel)) != (16, 16, 0, 1):
            raise ValueError('requires one unsigned 16-bit photon-count plane')
        if dataset.PhotometricInterpretation != 'MONOCHROME2':
            raise ValueError('photon counts require MONOCHROME2, without inversion')
        pixels = dataset.pixel_array
        if pixels.shape != (1024, 256, 256) or pixels.dtype.kind != 'u' or pixels.dtype.itemsize != 2:
            raise ValueError('FLIO pixel layout does not match protocol')
    except (InvalidDicomError, OSError, ValueError, AttributeError, TypeError, RuntimeError, NotImplementedError) as exc:
        raise Degraded(f'cannot read FLIO DICOM: {exc}') from exc
    return dict(kind='flio', pixels=pixels,
                notes=['One wavelength-band acquisition; frame axis retained as temporal bins.'])


def _read_retinal_heightmap(path, root):
    import pydicom
    from pydicom.errors import InvalidDicomError
    try:
        dataset = pydicom.dcmread(path)
        count = int(dataset.get('NumberOfFrames', 1))
        rows, columns = int(dataset.Rows), int(dataset.Columns)
        if count not in (2, 9, 10, 11) or min(rows, columns) < 1 or count*rows*columns > 100_000_000:
            raise ValueError('requires 2, 9, 10 or 11 nonempty surface frames within size limit')
        if 'FloatPixelData' not in dataset or int(dataset.BitsAllocated) != 32 or int(dataset.SamplesPerPixel) != 1:
            raise ValueError('requires single-plane float32 DICOM Float Pixel Data')
        if dataset.PhotometricInterpretation != 'MONOCHROME2':
            raise ValueError('height coordinates require MONOCHROME2 without inversion')
        pixels = dataset.pixel_array
        if pixels.shape != (count, rows, columns) or pixels.dtype.kind != 'f' or pixels.dtype.itemsize != 4:
            raise ValueError('heightmap layout does not match protocol')
    except (InvalidDicomError, OSError, ValueError, AttributeError, TypeError, RuntimeError, NotImplementedError) as exc:
        raise Degraded(f'cannot read heightmap DICOM: {exc}') from exc
    # Which surface each frame holds, from the frame's own segment reference; None when absent.
    try:
        names = {int(item.SegmentNumber): (str(item.get('SegmentLabel') or '').strip() or None)
                 for item in dataset.SegmentSequence}
        surfaces = [names.get(int(group.SegmentIdentificationSequence[0].ReferencedSegmentNumber))
                    for group in dataset.PerFrameFunctionalGroupsSequence]
        if len(surfaces) != count:
            surfaces = [None] * count
    except (AttributeError, IndexError, KeyError, TypeError, ValueError):
        surfaces = [None] * count
    return dict(kind='heightmap', pixels=pixels, notes=['Float surface order and stored coordinates preserved.'],
                surfaces=surfaces, acquisition=_retinal_acquisition(dataset))
