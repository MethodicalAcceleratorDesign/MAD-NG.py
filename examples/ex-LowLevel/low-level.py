from pymadng import MAD
import numpy as np

mad = MAD()
mad.process.send("""
    local function madMatrixToPyList(m)
        return "[" .. string.gsub(m:tostring(",", ","), "i", "j") .. "]"
    end
    m1 = MAD.matrix(1000, 1000):seq()
    py:send([[
m1 = np.array(]] .. madMatrixToPyList(m1) .. [[) #Indents can be annoying...
m1 = m1.reshape(1000, 1000)
    ]])""")

mad.process.read()

print(m1)