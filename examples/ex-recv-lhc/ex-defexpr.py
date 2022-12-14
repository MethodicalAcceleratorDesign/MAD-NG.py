from pymadng import MAD
import time, os
current_dir = os.path.dirname(os.path.realpath(__file__)) + "/"

mad = MAD()

mad.send(f"""
function LHC_load () --Not local!
  local beam in MAD
  local assertf in MAD.utility

  MADX:load('{current_dir}lhc_as-built.seq', '{current_dir}lhc_as-built.mad') -- convert and save on need
  MADX:load('{current_dir}opt_400_10000_400_3000.madx', '{current_dir}opt_400_10000_400_3000.mad') -- ditto
  MADX:load('{current_dir}lhc_unset_vars.mad') -- handmade, cleaner than disabling warnings...

  local lhcb1, lhcb2 in MADX

  -- sanity checks
  local n1, n2 = #lhcb1, #lhcb2
  assertf(n1 == 6677, "invalid number of elements %d in LHCB1 (6677 expected)", n1)
  assertf(n2 == 6676, "invalid number of elements %d in LHCB2 (6676 expected)", n2)
  py:send("done")
end
""")

mad.send("""
local is_number, is_string, is_function, is_table in MAD.typeid

expr = {} -- list of deferred expressions

function reg_expr(k,v) -- collect deferred expressions
  if is_number(v) or is_string(v) then
    ;
  elseif is_function(v) then -- deferred expressions are functions
    expr[#expr+1] = v
  elseif is_table(v) then
    for kk, vv in pairs(v) do reg_expr(kk,vv) end -- recursive call
  else
    print(k, v, type(v)) -- unexpected for MAD-X, just for debug
  end
end
""")

t0 = time.time()
mad.LHC_load ()
mad.recv() #done
t1 = time.time()
print("Load time:", t1-t0, " sec\n")

t0 = time.time()
mad.reg_expr("MADX", mad.MADX)
mad.send("py:send('done')").recv() # reg_expr is recursive
t1 = time.time()
print("reg_expr time:", t1-t0, " sec\n")

mad.send("for i=1,#expr do expr[i]() end") #So that warnings are performed here and do no affect timing


#Methods of evaluation:
t0 = time.time()
mad.send("py:send(#expr)")
for i in range(mad.recv()):
    mad.send(f"py:send(expr[{i+1}]())").recv()
t1 = time.time()
print("eval time method 1:", t1-t0, " sec")

t0 = time.time()
mad.send("len = #expr py:send(len) for i=1,len do py:send(expr[i]()) end")
for i in range(mad.recv()):
    mad.recv()
t1 = time.time()
print("eval time method 2:", t1-t0, " sec")

t0 = time.time()
mad.send("py:send(#expr)")
exprList1 = [mad.send(f"py:send(expr[{i+1}]())").recv() for i in range(mad.recv())]
t1 = time.time()
print("eval time method 3:", t1-t0, " sec")

t0 = time.time()
mad.send("len = #expr py:send(len) for i=1,len do py:send(expr[i]()) end")
exprList2 = [mad.recv() for i in range(mad.recv())]
t1 = time.time()
print("eval time method 4:", t1-t0, " sec\n")


print("sanity check", exprList1 == exprList2, len(exprList1))

t0 = time.time()
mad["lhcb1"] = mad.MADX.lhcb1

mad.send("""
py:send(#lhcb1)
for i, elm, spos, len in lhcb1:iter() do 
    py:send(elm.name)
end
""")
nameList = [mad.recv() for _ in range(mad.recv())]
t1 = time.time()
print("time to retrieve every element name in lhcb1 sequence", t1-t0, "sec")
print(len(nameList))


t0 = time.time()
mad["lhcb2"] = mad.MADX.lhcb2
mad.send("""
lhcb2_tbl = {}
for i, elm, spos, len in lhcb2:iter() do 
    lhcb2_tbl[i] = elm.name
end
py:send(lhcb2_tbl)
""")
nameList = mad.recv()
t1 = time.time()
print("time to retrieve every element name in lhcb2 sequence", t1-t0, "sec")
print(len(nameList))