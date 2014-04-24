import os, bpy
from subprocess import PIPE, Popen
from os import rename
from .vi_func import processf

def envi_sim(calc_op, node, connode):
    os.chdir(connode.newdir)
    esimcmd = "EnergyPlus in.idf in.epw" 
    esimrun = Popen(esimcmd, shell = True, stdout = PIPE)
    for line in esimrun.stdout:
        if 'FATAL' in line.decode():
            print(line) 
    for fname in os.listdir('.'):
        if fname.split(".")[0] == node.resname:
            os.remove(os.path.join(connode.newdir, fname))
    for fname in os.listdir('.'):
        if fname.split(".")[0] == "eplusout":
            rename(os.path.join(connode.newdir, fname), os.path.join(connode.newdir,fname.replace("eplusout", node.resname)))

    processf(calc_op, node)
    node.dsdoy = connode.sdoy # (locnode.startmonthnode.sdoy
    node.dedoy = connode.edoy
    if node.resname+".err" not in [im.name for im in bpy.data.texts]:
        bpy.data.texts.load(os.path.join(connode.newdir, node.resname+".err"))
    calc_op.report({'INFO'}, "Calculation is finished.")  
            
    if node.resname+".err" not in [im.name for im in bpy.data.texts]:
        bpy.data.texts.load(os.path.join(connode.newdir, node.resname+".err"))

   