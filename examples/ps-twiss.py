from pymadng import MAD
import numpy as np
import matplotlib.pyplot as plt

with MAD("/home/joshua/Documents/MAD-NGFork/MAD/src/pyMAD/src", log = True) as mad:
    mad.beam("psbeam", particle = "proton", pc = 2.794987)
    mad.MADX.BEAM = mad.psbeam
    mad.MADX.BRHO = mad.psbeam.brho
    filepath = "/home/joshua/Documents/MAD-NGFork/MAD/examples/ex-ps-twiss/"
    mad.callMethod(None, "MADX", "load", f"'{filepath}ps_unset_vars.mad'", False)
    mad.callMethod(None, "MADX", "load", f"'{filepath}ps_mu.seq'", f"'{filepath}ps_mu.mad'", False)
    mad.callMethod(None, "MADX", "load", f"'{filepath}ps_ss.seq'", f"'{filepath}ps_ss.mad'", False)
    mad.callMethod(None, "MADX", "load", f"'{filepath}ps_fb_lhc.str'", f"'{filepath}ps_fb_lhc_str.mad'", False)
    
    mad.importVariables("MADX", ["ps"])
    mad.ps.beam = mad.psbeam
    mad.survey("srv", sequence = mad.ps)

    mad.callMethod(None, "srv", "write", "'data/PS_survey_py.tfs'", ['name', 'kind', 's', 'l', 'angle', 'x', 'y', 'z', 'theta'])

    mad.twiss("tws", sequence = mad.ps, method = 6, nslice = 3, chrom = True)

    mad.importClasses("MAD.gphys", ["melmcol"])
    mad.melmcol(None, mad.tws, ['angle', 'tilt', 
                        'k0l' , 'k1l' , 'k2l' , 'k3l' , 'k4l' , 'k5l' , 'k6l',
                        'k0sl', 'k1sl', 'k2sl', 'k3sl', 'k4sl', 'k5sl', 'k6sl',
                        'ksl', 'hkick', 'vkick'])
    
    mad.callMethod(None, mad.tws, "write", "'data/PS_twiss_py.tfs'", ['name','kind','s',
                                                        'x','px','beta11','alfa11','beta22','alfa22','dx','dpx','mu1','mu2',
                                                        'l','angle','k0l','k1l','k2l','k3l','hkick','vkick'])