from .mad_object import MAD

__title__ = "pymadng"
__version__ = "0.3.1"
with MAD() as mad:
    __MAD_version__ = mad.MAD.env.version

__summary__ = "Python interface to MAD-NG running as subprocess"
__uri__ = "https://github.com/MethodicalAcceleratorDesign/MADpy"

__credits__ = """
Creator: Joshua Gray <joshua.mark.gray at cern.ch>
"""

__all__ = ["MAD"]
