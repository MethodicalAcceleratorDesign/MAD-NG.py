import os

from pymadng import MAD

original_dir = os.getcwd()
os.chdir(os.path.dirname(os.path.realpath(__file__)))

with MAD(debug=False) as mad:
    mad["psbeam"] = mad.beam(particle="'proton'", pc=2.794987)
    mad.MADX.BEAM = mad.psbeam
    mad.MADX.BRHO = mad.psbeam.brho
    mad.MADX.load("'ps_unset_vars.mad'")
    mad.MADX.load("'ps_mu.seq'")
    mad.MADX.load("'ps_ss.seq'")
    mad.MADX.load("'ps_fb_lhc.str'")

    mad.load("MADX", "ps")
    mad.ps.beam = mad.psbeam
    mad["srv", "mflw"] = mad.survey(sequence=mad.ps)

    mad.srv.write("'PS_survey_py.tfs'",
        mad.quote_strings(["name", "kind", "s", "l", "angle", "x", "y", "z", "theta"]),
        )

    mad["mtbl", "mflw"] = mad.twiss(sequence=mad.ps, method=6, nslice=3)

    mad.load("MAD.gphys", "melmcol")
    #Add element properties as columns
    mad.melmcol(mad.mtbl,
        mad.quote_strings(
            ["angle", "tilt", "k0l", "k1l", "k2l", "k3l", "k4l", "k5l", "k6l", "k0sl",
            "k1sl", "k2sl", "k3sl", "k4sl", "k5sl", "k6sl", "ksl", "hkick", "vkick" ]),
        )

    mad.mtbl.write("'PS_twiss_py.tfs'",
        mad.quote_strings(
            ["name", "kind", "s", "x", "px", "beta11", "alfa11", "beta22", "alfa22","dx",
            "dpx", "mu1", "mu2", "l", "angle", "k0l", "k1l", "k2l", "k3l", "hkick", "vkick"]
            )
        )
    
    df = mad.mtbl.to_df()
    try:
        import tfs
        assert type(df) is tfs.TfsDataFrame
        print("tfs-pandas installed, so the header is stored in headers")
        print(df.headers)
    except ImportError:
        print("tfs-pandas not installed, so the header is stored in attrs instead of headers")
        print(df.attrs)

    print(df)
    print(mad.srv.to_df())

os.chdir(original_dir)