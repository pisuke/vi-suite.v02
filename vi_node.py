# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####


import bpy, glob, os, inspect, sys, datetime
from nodeitems_utils import NodeCategory, NodeItem
from .vi_func import nodeinit, objvol, triarea, socklink, newrow, epwlatilongi, nodeid, nodeinputs

try:
    import numpy
    np =1
except:
    np = 0

class ViNetwork(bpy.types.NodeTree):
    '''A node tree for VI-Suite analysis.'''
    bl_idname = 'ViN'
    bl_label = 'Vi Network'
    bl_icon = 'LAMP_SUN'

class ViNodes:
    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == 'ViN'

class ViGExLiNode(bpy.types.Node, ViNodes):
    '''Node describing a LiVi geometry export node'''
    bl_idname = 'ViGExLiNode'
    bl_label = 'LiVi Geometry'
    bl_icon = 'LAMP'

    (filepath, filename, filedir, newdir, filebase, objfilebase, nodetree, nproc, rm, cp, cat, fold) = (bpy.props.StringProperty() for x in range(12))
    exported = bpy.props.BoolProperty()

    def nodeupdate(self, context):
        self.exported = False
        if self.bl_label[0] != '*':
            self.bl_label = '*'+self.bl_label
        self.outputs['Generative out'].hide = True if self.animmenu != 'Static' else False       
        
    animtype = [('Static', "Static", "Simple static analysis"), ('Geometry', "Geometry", "Animated geometry analysis"), ('Material', "Material", "Animated material analysis"), ('Lights', "Lights", "Animated artificial lighting analysis")]
    animmenu = bpy.props.EnumProperty(name="", description="Animation type", items=animtype, default = 'Static', update = nodeupdate)
    cpoint = bpy.props.EnumProperty(items=[("0", "Faces", "Export faces for calculation points"),("1", "Vertices", "Export vertices for calculation points"), ],
            name="", description="Specify the calculation point geometry", default="1", update = nodeupdate)

    def init(self, context):   
        self.outputs.new('ViGen', 'Generative out')
        self.outputs.new('ViLiG', 'Geometry out')
        self.outputs['Geometry out'].hide = True
        self['nodeid'] = nodeid(self, bpy.data.node_groups)
     
        if bpy.data.filepath:
            nodeinit(self)
        bpy.context.scene.gfe = 0
                
    def draw_buttons(self, context, layout):
        newrow(layout, 'Animation:', self, 'animmenu')
        newrow(layout, 'Result point:', self, 'cpoint')
        row = layout.row()
        row.operator("node.ligexport", text = "Export").nodeid = self['nodeid']

    def update(self):
        self.outputs[0].hide = True if self.animmenu != 'Static' else False  
        if self.get('Geometry out'):
            if self.outputs['Geometry out'].is_linked and self.outputs['Geometry out'].links[0].to_node.name == 'LiVi Compliance' and self.cpoint == '1':
                self.cpoint = '0'
        if self.get('nodeid'):
            socklink(self.outputs['Generative out'], self['nodeid'].split('@')[1])
            socklink(self.outputs['Geometry out'], self['nodeid'].split('@')[1])
            
    def export(self, context):
        self['frames'] = {'Material': 0, 'Geometry': 0, 'Lights':0} 
        for mglfr in self['frames']:
            self['frames'][mglfr] = context.scene.frame_end if self.animmenu == mglfr else 0
            context.scene.gfe = max(self['frames'].values())
        if self.filepath != bpy.data.filepath:
            nodeinit(self)
        
class ViLiNode(bpy.types.Node, ViNodes):
    '''Node describing a basic LiVi analysis'''
    bl_idname = 'ViLiNode'
    bl_label = 'LiVi Basic'
    bl_icon = 'LAMP'

    analysistype = [('0', "Illuminance", "Lux Calculation"), ('1', "Irradiance", "W/m"+ u'\u00b2' + " Calculation"), ('2', "Daylight Factor", "DF (%) Calculation"), ('3', "Glare", "Glare Calculation")]
    unit = bpy.props.StringProperty()
    animtype = [('Static', "Static", "Simple static analysis"), ('Time', "Time", "Animated time analysis")]
    skylist = [    ("0", "Sunny", "CIE Sunny Sky description"),
                   ("1", "Partly Coudy", "CIE Sunny Sky description"),
                   ("2", "Coudy", "CIE Partly Cloudy Sky description"),
                   ("3", "DF Sky", "Daylight Factor Sky description"),
                   ("4", "HDR Sky", "HDR file sky"),
                   ("5", "Radiance Sky", "Radiance file sky"),
                   ("6", "None", "No Sky")]
#    skytypeparams = bpy.props.StringProperty(default = "+s")
        
    def nodeupdate(self, context):
        self.exported = False
        self.outputs['Context out'].hide = True
        self.bl_label = '*LiVi Basic'
        self.outputs['Target out'].hide = True if self.animmenu != 'Static' else False
        if self.analysismenu == '2' or self.skymenu not in ('0', '1', '2'):
            if self.inputs['Location in'].is_linked:
                bpy.data.node_groups[self['nodeid'].split('@')[1]].links.remove(self.inputs['Location in'].links[0])
            self.inputs['Location in'].hide = True
        else:
            self.inputs['Location in'].hide = False                        
        if self.edoy < self.sdoy:
            self.edoy = self.sdoy
        if self.edoy == self.sdoy:
            if self.ehour < self.shour:
                self.ehour = self.shour


    analysismenu = bpy.props.EnumProperty(name="", description="Type of lighting analysis", items = analysistype, default = '0', update = nodeupdate)
#    simalg = bpy.props.StringProperty(name="", description="Algorithm to run on the radiance results", default=" |  rcalc  -e '$1=47.4*$1+120*$2+11.6*$3' " if str(sys.platform) != 'win32' else ' |  rcalc  -e "$1=47.4*$1+120*$2+11.6*$3" ')
    animmenu = bpy.props.EnumProperty(name="", description="Animation type", items=animtype, default = 'Static', update = nodeupdate)
    skymenu = bpy.props.EnumProperty(name="", items=skylist, description="Specify the type of sky for the simulation", default="0", update = nodeupdate)
    shour = bpy.props.FloatProperty(name="", description="Hour of simulation", min=1, max=24, default=12, update = nodeupdate)
    sdoy = bpy.props.IntProperty(name="", description="Day of simulation", min=1, max=365, default=1, update = nodeupdate)
    ehour = bpy.props.FloatProperty(name="", description="Hour of simulation", min=1, max=24, default=12, update = nodeupdate)
    edoy = bpy.props.IntProperty(name="", description="Day of simulation", min=1, max=365, default=1, update = nodeupdate)
    interval = bpy.props.FloatProperty(name="", description="Site Latitude", min=0.25, max=24, default=1, update = nodeupdate)
    exported = bpy.props.BoolProperty(default=False)
    hdr = bpy.props.BoolProperty(name="", description="Export HDR panoramas", default=False, update = nodeupdate)
    hdrname = bpy.props.StringProperty(name="", description="Name of the HDR image file", default="", update = nodeupdate)
    skyname = bpy.props.StringProperty(name="", description="Name of the Radiance sky file", default="", update = nodeupdate)
#    skynum = bpy.props.IntProperty()
    resname = bpy.props.StringProperty()
    rp_display = bpy.props.BoolProperty(default = False)
    needloc = bpy.props.BoolProperty(default = True)
#    starttimet = datetime.datetime(datetime.datetime.now().year, 1, 1, 12, 0)
#    endtimet = datetime.datetime(datetime.datetime.now().year, 1, 1, 12, 0)

    def init(self, context):
        self.inputs.new('ViLiG', 'Geometry in')
        self.inputs.new('ViLoc', 'Location in')
        self.outputs.new('ViTar', 'Target out')
        self.outputs.new('ViLiC', 'Context out')        
        self.outputs['Context out'].hide = True
        self['nodeid'] = nodeid(self, bpy.data.node_groups)
        self.starttime = datetime.datetime(datetime.datetime.now().year, 1, 1, 12, 0)
        self.endtime = datetime.datetime(datetime.datetime.now().year, 1, 1, 12, 0)
        self['hours'] = 0         
        self['frames'] = {'Time':0}
        self['resname'] = 'illumout'
        self['unit'] = "Lux"

    def draw_buttons(self, context, layout):
        row = layout.row()
        row.label("Analysis type:")
        row.prop(self, 'analysismenu')
        row = layout.row()
        if self.analysismenu in ('0', '1', '3'):
            row.label("Sky type:")
            row.prop(self, 'skymenu')
            if self.skymenu in ('0', '1', '2'):                
                newrow(layout, "Animation", self, 'animmenu')
                newrow(layout, "Start hour:", self, 'shour')
                newrow(layout, "Start day:", self, 'sdoy')
                if self.animmenu == 'Time':
                    newrow(layout, "End hour:", self, 'ehour')
                    newrow(layout, "End day of year:", self, 'edoy')
                    if self.edoy < self.sdoy:
                        self.edoy = self.sdoy
                    if self.edoy == self.sdoy and self.ehour < self.shour:
                        self.ehour = self.shour
                    newrow(layout, "Interval (hours):", self, 'interval')
            
            if self.skymenu == '4':
                row = layout.row()
                row.label("HDR file:")
                row.operator('node.hdrselect', text = 'HDR select')
                row = layout.row()
                row.prop(self, 'hdrname')
            elif self.skymenu == '5':
                row = layout.row()
                row.label("Radiance file:")
                row.operator('node.skyselect', text = 'Sky select')
                row = layout.row()
                row.prop(self, 'skyname')
        row = layout.row()
        
        if self.skymenu not in ('4', '6'):
            newrow(layout, 'HDR:', self, 'hdr')
        
        if nodeinputs(self):
            row = layout.row()
            if context.scene.gfe == 0 or self['frames']['Time'] == 0:
                row.operator("node.liexport", text = "Export").nodeid = self['nodeid']
            else:
                row.label('Cannot have geometry and time animation')
            
    def export(self, context):
        self['skynum'] = int(self.skymenu) if self.analysismenu != "2" else 3
        self.starttime = datetime.datetime(datetime.datetime.now().year, 1, 1, int(self.shour), int((self.shour - int(self.shour))*60)) + datetime.timedelta(self.sdoy - 1) if self['skynum'] < 3 else datetime.datetime(2013, 1, 1, 12)
        self.endtime = datetime.datetime(datetime.datetime.now().year, 1, 1, int(self.ehour), int((self.ehour - int(self.ehour))*60)) + datetime.timedelta(self.edoy - 1) if self.animmenu == 'Time' else self.starttime
        self['hours'] = 0 if self.animmenu == 'Static' or int(self.skymenu) > 2  else (self.endtime-self.starttime).days*24 + (self.endtime-self.starttime).seconds/3600
        self['frames']['Time'] = context.scene.cfe = context.scene.fs + int(self['hours']/self.interval)
        self['resname'] = ("illumout", "irradout", "dfout", '')[int(self.analysismenu)] 
        self['unit'] = ("Lux", "W/m"+ u'\u00b2', "DF %", '')[int(self.analysismenu)]
        self['simalg'] = (" |  rcalc  -e '$1=47.4*$1+120*$2+11.6*$3' ", " |  rcalc  -e '$1=$1' ", " |  rcalc  -e '$1=(47.4*$1+120*$2+11.6*$3)/100' ", '')[int(self.analysismenu)] \
            if str(sys.platform) != 'win32' else (' |  rcalc  -e "$1=47.4*$1+120*$2+11.6*$3" ', ' |  rcalc  -e "$1=$1" ', ' |  rcalc  -e "$1=(47.4*$1+120*$2+11.6*$3)/100" ', '')[int(self.analysismenu)]       

        if int(self.skymenu) < 4:
            self['skytypeparams'] = ("+s", "+i", "-c", "-b 22.86 -c")[int(self['skynum'])]
        

class ViLiClass(bpy.types.Node):
    '''Node describing a base LiVi context node'''
    bl_idname = 'ViLiClass'
    bl_label = 'LiVi Base Class'
    bl_icon = 'LAMP'
    
class ViLiCBNode(ViLiClass, ViNodes):
    '''Node describing a VI-Suite climate based lighting node'''
    bl_idname = 'ViLiCBNode'
    bl_label = 'LiVi CBDM'
    bl_icon = 'LAMP'

    def nodeupdate(self, context):
        self.exported = False
        self.bl_label = '*LiVi CBDM'
        if int(self.analysismenu) < 2:
            self.sm = self.sourcemenu2
        else:
            self.sm = self.sourcemenu
        self.exported = False
        if self.sm != '0' and self.inputs['Location in'].is_linked:
            bpy.data.node_groups[self['nodeid'].split('@')[1]].links.remove(self.inputs['Location in'].links[0])
        self.inputs['Location in'].hide = False if self.sm == '0' else True
            
    analysistype = [('0', "Light Exposure", "LuxHours Calculation"), ('1', "Radiation Exposure", "kWh/m"+ u'\u00b2' + " Calculation"), ('2', "Daylight Autonomy", "DA (%) Calculation"), ('3', "Hourly irradiance", "Irradiance for each simulation time step"), ('4', "UDI", "Useful Daylight Illuminance")]
    analysismenu = bpy.props.EnumProperty(name="", description="Type of lighting analysis", items = analysistype, default = '0', update = nodeupdate)
    animtype = [('0', "Static", "Simple static analysis"), ('1', "Geometry", "Animated time analysis"), ('2', "Material", "Animated time analysis")]
    animmenu = bpy.props.EnumProperty(name="", description="Animation type", items=animtype, default = '0')
    sourcetype = [('0', "EPW", "EnergyPlus weather file"), ('1', "VEC", "Generated vector file")]
    sourcetype2 = [('0', "EPW", "EnergyPlus weather file"), ('2', "HDR", "HDR sky file")]
    sourcemenu = bpy.props.EnumProperty(name="", description="Source type", items=sourcetype, default = '0', update = nodeupdate)
    sourcemenu2 = bpy.props.EnumProperty(name="", description="Source type", items=sourcetype2, default = '0', update = nodeupdate)
#    simalg = bpy.props.StringProperty(name="", description="Algorithm to run on the radiance results", default=" |  rcalc  -e '$1=(47.4*$1+120*$2+11.6*$3)/1000' ")
    hdrname = bpy.props.StringProperty(
            name="", description="Name of the composite HDR sky file", default="", update = nodeupdate)
    mtxname = bpy.props.StringProperty(
            name="", description="Name of the calculated vector sky file", default="", update = nodeupdate)
    weekdays = bpy.props.BoolProperty(name = '', default = False, update = nodeupdate)
    cbdm_start_hour =  bpy.props.IntProperty(name = '', default = 8, min = 1, max = 24)
    cbdm_end_hour =  bpy.props.IntProperty(name = '', default = 20, min = 1, max = 24)
    dalux =  bpy.props.IntProperty(name = '', default = 300, min = 1, max = 2000)
    damin = bpy.props.IntProperty(name = '', default = 100, min = 1, max = 2000)
    dasupp = bpy.props.IntProperty(name = '', default = 300, min = 1, max = 2000)
    daauto = bpy.props.IntProperty(name = '', default = 3000, min = 1, max = 5000)
#    skynum = bpy.props.IntProperty(name = '', default = 0, min = 0, max = 6)
    sm = bpy.props.StringProperty(name = '', default = '0')
    exported = bpy.props.BoolProperty(name = '', default = False)
    hdr = bpy.props.BoolProperty(name = '', default = False)
    fromnode = bpy.props.BoolProperty(name = '', default = False)
    num = (("-ab", 2, 3, 5), ("-ad", 512, 2048, 4096), ("-ar", 128, 512, 1024), ("-as", 256, 1024, 2048), ("-aa", 0.0, 0.0, 0.0), ("-dj", 0, 0.7, 1), ("-ds", 0, 0.5, 0.15), ("-dr", 1, 2, 3), ("-ss", 0, 2, 5), ("-st", 1, 0.75, 0.1), ("-lw", 0.05, 0.001, 0.0002))
#    resname = bpy.props.StringProperty()
#   unit = bpy.props.StringProperty()

    def init(self, context):
        self.inputs.new('ViLoc', 'Location in')
        self.inputs.new('ViLiG', 'Geometry in')
        self.outputs.new('ViLiC', 'Context out')
        self.outputs['Context out'].hide = True
        self['nodeid'] = nodeid(self, bpy.data.node_groups)  
        self['frames'] = {'Time':0}
        self['whitesky'] = "void glow sky_glow \n0 \n0 \n4 1 1 1 0 \nsky_glow source sky \n0 \n0 \n4 0 0 1 180 \nvoid glow ground_glow \n0 \n0 \n4 1 1 1 0 \nground_glow source ground \n0 \n0 \n4 0 0 -1 180\n\n"
        
    def draw_buttons(self, context, layout):
        row = layout.row()
        row.label("Analysis Type:")
        row.prop(self, 'analysismenu')
        if self.analysismenu in ('2', '4'):
           newrow(layout, 'Weekdays only:', self, 'weekdays')
           newrow(layout, 'Start hour:', self, 'cbdm_start_hour')
           newrow(layout, 'End hour:', self, 'cbdm_end_hour')
           if self.analysismenu =='2':
               newrow(layout, 'Min Lux level:', self, 'dalux')
           if self.analysismenu =='4':
               newrow(layout, 'Fell short (Max):', self, 'damin')
               newrow(layout, 'Supplementry (Max):', self, 'dasupp')
               newrow(layout, 'Autonomous (Max):', self, 'daauto')
        
        if self.get('vecvals'):
            newrow(layout, 'From node:', self, 'fromnode')
        
        if not self.fromnode:
            row = layout.row()
            row.label('Source file:')
            if int(self.analysismenu) < 2:
                row.prop(self, 'sourcemenu2')
            else:
                row.prop(self, 'sourcemenu')
        
            row = layout.row()
            if self.sm == '1':
                row.operator('node.mtxselect', text = 'Select MTX').nodeid = self['nodeid']
                row = layout.row()
                row.prop(self, 'mtxname')
            elif self.sm == '2':
                row.operator('node.hdrselect', text = 'Select HDR').nodeid = self['nodeid']
                row = layout.row()
                row.prop(self, 'hdrname')
                if self.analysismenu not in ('0', '1'):
                    row = layout.row()
                    row.operator('node.vecselect', text = 'Select MTX').nodeid = self['nodeid']
                    row = layout.row()
                    row.prop(self, 'vecname')
        
        if int(self.analysismenu) > 1:
            row = layout.row()
            row.label('Export HDR:')
            row.prop(self, 'hdr')
            
        if nodeinputs(self):
            if self.inputs['Location in'].is_linked:
                if self.inputs['Location in'].links[0].from_node.loc == '1':
                    export = 1
                else:
                    export = 0
            elif self.sm != '0' or self.get('vecvals'):
                export = 1
            else:
                export = 0
        else:
            export = 0

        if export == 1:
            row = layout.row()
            row.operator("node.liexport", text = "Export").nodeid = self['nodeid']
    
    def export(self, context):
        self['skynum'] = 4
        self['simalg'] = (" |  rcalc  -e '$1=(47.4*$1+120*$2+11.6*$3)/1000' ", " |  rcalc  -e '$1=($1+$2+$3)/3000' ", " |  rcalc  -e '$1=(47.4*$1+120*$2+11.6*$3)' ", " |  rcalc  -e '$1=($1+$2+$3)/3' ", " |  rcalc  -e '$1=(47.4*$1+120*$2+11.6*$3)' ")[int(self.analysismenu)]
        self['wd'] = (7, 5)[self.weekdays]
        self['resname'] = ('kluxhours', 'cumwatth', 'dayauto', 'hourrad', 'udi')[int(self.analysismenu)]
        self['unit'] = ('kLuxHours', 'kWh', 'DA (%)', '', 'UDI-a (%)')[int(self.analysismenu)]

class ViLiCNode(bpy.types.Node, ViNodes):
    '''Node describing a VI-Suite lighting compliance node'''
    bl_idname = 'ViLiCNode'
    bl_label = 'LiVi Compliance'
    bl_icon = 'LAMP'

    def nodeupdate(self, context):
        self.exported = False
        self.bl_label = '*LiVi Compliance'
            
    interval = 0
    exported = bpy.props.BoolProperty(default=False)
    TZ = bpy.props.StringProperty(default = 'GMT')
#    simalg = bpy.props.StringProperty(name="", description="Calculation algorithm", default=" |  rcalc  -e '$1=(47.4*$1+120*$2+11.6*$3)/100' " if str(sys.platform) != 'win32' else ' |  rcalc  -e "$1=(47.4*$1+120*$2+11.6*$3)/100" ')
#    resname = bpy.props.StringProperty()
    unit = bpy.props.StringProperty()
    hdr = bpy.props.BoolProperty(name="HDR", description="Export HDR panoramas", default=False, update = nodeupdate)
    analysistype = [('0', "BREEAM", "BREEAM HEA1 calculation"), ('1', "CfSH", "Code for Sustainable Homes calculation")] #, ('2', "LEED", "LEED EQ8.1 calculation"), ('3', "Green Star", "Green Star Calculation")]
    bambuildtype = [('0', "School", "School lighting standard"), ('1', "Higher Education", "Higher education lighting standard"), ('2', "Healthcare", "Healthcare lighting standard"), ('3', "Residential", "Residential lighting standard"), ('4', "Retail", "Retail lighting standard"), ('5', "Office & other", "Office and other space lighting standard")]
    animtype = [('Static', "Static", "Simple static analysis")]
    animmenu = bpy.props.EnumProperty(name="", description="Animation type", items=animtype, default = 'Static', update = nodeupdate)
    analysismenu = bpy.props.EnumProperty(name="", description="Type of analysis", items = analysistype, default = '0', update = nodeupdate)
    bambuildmenu = bpy.props.EnumProperty(name="", description="Type of building", items=bambuildtype, default = '0', update = nodeupdate)
    cusacc = bpy.props.StringProperty(name="", description="Custom Radiance simulation parameters", default="", update = nodeupdate)
    buildstorey = bpy.props.EnumProperty(items=[("0", "Single", "Single storey building"),("1", "Multi", "Multi-storey building")], name="", description="Building storeys", default="0", update = nodeupdate)

    def init(self, context):
        self.inputs.new('ViLiG', 'Geometry in')
        self.outputs.new('ViLiC', 'Context out')
        self.outputs['Context out'].hide = True
        self['nodeid'] = nodeid(self, bpy.data.node_groups)
        self['frames'] = {'Time':0}
        self['unit'] = "DF %"
        self['skynum'] = 3
 
    def draw_buttons(self, context, layout):
        newrow(layout, "Compliance standard:", self, 'analysismenu')
        if self.analysismenu == '0':
            newrow(layout, "Building type:", self, 'bambuildmenu')
            newrow(layout, "Storeys:", self, 'buildstorey')
        newrow(layout, 'Animation:', self, "animmenu")
        if nodeinputs(self):
            row = layout.row()
            row.operator("node.liexport", text = "Export").nodeid = self['nodeid']
            
    def export(self, context):
        if self.analysismenu in ('0', '1'):
            self['simalg'] = " |  rcalc  -e '$1=(47.4*$1+120*$2+11.6*$3)/100' " if str(sys.platform) != 'win32' else ' |  rcalc  -e "$1=(47.4*$1+120*$2+11.6*$3)/100" '
        self['resname'] = 'breaamout' if self.analysismenu == '0' else 'cfsh'
        self['skytypeparams'] = "-b 22.86 -c"
        context.scene.cfe = 0

class ViLiSNode(bpy.types.Node, ViNodes):
    '''Node describing a LiVi simulation'''
    bl_idname = 'ViLiSNode'
    bl_label = 'LiVi Simulation'
    bl_icon = 'LAMP'
    
    def nodeupdate(self, context):
        if self.inputs['Context in'].is_linked:
            connode = self.inputs['Context in'].links[0].from_node
            if connode.bl_label == 'LiVi Basic':
                self['radparams'] = self.cusacc if self.simacc == '3' else (" {0[0]} {1[0]} {0[1]} {1[1]} {0[2]} {1[2]} {0[3]} {1[3]} {0[4]} {1[4]} {0[5]} {1[5]} {0[6]} {1[6]} {0[7]} {1[7]} {0[8]} {1[8]} {0[9]} {1[9]} {0[10]} {1[10]} ".format([n[0] for n in self.numbasic], [n[int(self.simacc)+1] for n in self.numbasic]))
            else:
                self['radparams'] = self.cusacc if self.csimacc == '0' else (" {0[0]} {1[0]} {0[1]} {1[1]} {0[2]} {1[2]} {0[3]} {1[3]} {0[4]} {1[4]} {0[5]} {1[5]} {0[6]} {1[6]} {0[7]} {1[7]} {0[8]} {1[8]} {0[9]} {1[9]} {0[10]} {1[10]} ".format([n[0] for n in self.numadvance], [n[int(self.csimacc)+1] for n in self.numadvance]))

    simacc = bpy.props.EnumProperty(items=[("0", "Low", "Low accuracy and high speed (preview)"),("1", "Medium", "Medium speed and accuracy"), ("2", "High", "High but slow accuracy"),("3", "Custom", "Edit Radiance parameters"), ],
            name="", description="Simulation accuracy", default="0", update = nodeupdate)
    csimacc = bpy.props.EnumProperty(items=[("0", "Custom", "Edit Radiance parameters"), ("1", "Initial", "Initial accuracy for this metric"), ("2", "Final", "Final accuracy for this metric")],
            name="", description="Simulation accuracy", default="1", update = nodeupdate)
    cusacc = bpy.props.StringProperty(
            name="", description="Custom Radiance simulation parameters", default="", update = nodeupdate)
    numbasic = (("-ab", 2, 3, 4), ("-ad", 256, 1024, 4096), ("-ar", 128, 512, 1024), ("-as", 128, 512, 1024), ("-aa", 0.3, 0.15, 0.08), ("-dj", 0, 0.7, 1), ("-ds", 0, 0.5, 0.15), ("-dr", 1, 3, 5), ("-ss", 0, 2, 5), ("-st", 1, 0.75, 0.1), ("-lw", 0.05, 0.01, 0.002))
    numadvance = (("-ab", 3, 5), ("-ad", 2048, 4096), ("-ar", 512, 1024), ("-as", 1024, 2048), ("-aa", 0.0, 0.0), ("-dj", 0.7, 1), ("-ds", 0.5, 0.15), ("-dr", 2, 3), ("-ss", 2, 5), ("-st", 0.75, 0.1), ("-lw", 0.001, 0.0002))
        
    def init(self, context):
        self.inputs.new('ViLiC', 'Context in')
        self.outputs.new('LiViWOut', 'Data out')
        self.outputs['Data out'].hide = True
        self['nodeid'] = nodeid(self, bpy.data.node_groups)
    
    def update(self):
        if self.inputs['Context in'].is_linked:
            connode = self.inputs['Context in'].links[0].from_node
            if connode.bl_label == 'LiVi Basic':
                self['radparams'] = self.cusacc if self.simacc == '3' else (" {0[0]} {1[0]} {0[1]} {1[1]} {0[2]} {1[2]} {0[3]} {1[3]} {0[4]} {1[4]} {0[5]} {1[5]} {0[6]} {1[6]} {0[7]} {1[7]} {0[8]} {1[8]} {0[9]} {1[9]} {0[10]} {1[10]} ".format([n[0] for n in self.numbasic], [n[int(self.simacc)+1] for n in self.numbasic]))
            else:
                self['radparams'] = self.cusacc if self.csimacc == '0' else (" {0[0]} {1[0]} {0[1]} {1[1]} {0[2]} {1[2]} {0[3]} {1[3]} {0[4]} {1[4]} {0[5]} {1[5]} {0[6]} {1[6]} {0[7]} {1[7]} {0[8]} {1[8]} {0[9]} {1[9]} {0[10]} {1[10]} ".format([n[0] for n in self.numadvance], [n[int(self.csimacc)+1] for n in self.numadvance]))

    def draw_buttons(self, context, layout):
        if nodeinputs(self):            
            row = layout.row()
            row.label("Accuracy:")
            if self.inputs['Context in'].links[0].from_node.bl_label == 'LiVi Basic':
                row.prop(self, 'simacc')
            elif self.inputs['Context in'].links[0].from_node.bl_label == 'LiVi Compliance':
                row.prop(self, 'csimacc')
            elif self.inputs['Context in'].links[0].from_node.bl_label == 'LiVi CBDM':
                row.prop(self, 'csimacc')

            if (self.simacc == '3' and self.inputs['Context in'].links[0].from_node.bl_label == 'LiVi Basic') or (self.csimacc == '0' and self.inputs['Context in'].links[0].from_node.bl_label in ('LiVi Compliance', 'LiVi CBDM')):
               newrow(layout, "Radiance parameters:", self, 'cusacc')

            row = layout.row()
            row.operator("node.radpreview", text = 'Preview').nodeid = self['nodeid']
            row.operator("node.livicalc", text = 'Calculate').nodeid = self['nodeid']

class ViSPNode(bpy.types.Node, ViNodes):
    '''Node describing a VI-Suite sun path'''
    bl_idname = 'ViSPNode'
    bl_label = 'VI Sun Path'
    bl_icon = 'LAMP'

    def init(self, context):
        self.inputs.new('ViLoc', 'Location in')
        self['nodeid'] = nodeid(self, bpy.data.node_groups)

    def draw_buttons(self, context, layout):
        if nodeinputs(self):
            row = layout.row()
            row.operator("node.sunpath", text="Create Sun Path").nodeid = self['nodeid']

class ViSSNode(bpy.types.Node, ViNodes):
    '''Node describing a VI-Suite shadow study'''
    bl_idname = 'ViSSNode'
    bl_label = 'VI Shadow Study'
    bl_icon = 'LAMP'

    exported = bpy.props.BoolProperty()

    def nodeupdate(self, context):
        self.exported = False
        if self.bl_label[0] != '*':
            self.bl_label = '*'+self.bl_label

    animtype = [('Static', "Static", "Simple static analysis"), ('Geometry', "Geometry", "Animated geometry analysis")]
    animmenu = bpy.props.EnumProperty(name="", description="Animation type", items=animtype, default = 'Static', update = nodeupdate)
    starthour = bpy.props.IntProperty(name = '', default = 1, min = 1, max = 24, description = 'Start hour')
    endhour = bpy.props.IntProperty(name = '', default = 24, min = 1, max = 24, description = 'End hour')
    interval = bpy.props.FloatProperty(name = '', default = 1, min = 0.1, max = 24, description = 'Interval')
    cpoint = bpy.props.EnumProperty(items=[("0", "Faces", "Export faces for calculation points"),("1", "Vertices", "Export vertices for calculation points"), ],
            name="", description="Specify the calculation point geometry", default="0")

    def init(self, context):
        self.inputs.new('ViLoc', 'Location in')
        self['nodeid'] = nodeid(self, bpy.data.node_groups)

    def draw_buttons(self, context, layout):
        if nodeinputs(self):
            newrow(layout, 'Animation:', self, "animmenu")
            newrow(layout, 'Start hour:', self, "starthour")
            newrow(layout, 'End hour:', self, "endhour")
            newrow(layout, 'Interval:', self, "interval")
            row = layout.row()
            row.operator("node.shad", text = 'Calculate').nodeid = self['nodeid']

class ViWRNode(bpy.types.Node, ViNodes):
    '''Node describing a VI-Suite wind rose generator'''
    bl_idname = 'ViWRNode'
    bl_label = 'VI Wind Rose'
    bl_icon = 'LAMP'

    wrtype = bpy.props.EnumProperty(items = [("0", "Hist 1", "Stacked histogram"), ("1", "Hist 2", "Stacked Histogram 2"), ("2", "Cont 1", "Filled contour"), ("3", "Cont 2", "Edged contour"), ("4", "Cont 3", "Lined contour")], name = "", default = '0')

    def init(self, context):
        self.inputs.new('ViLoc', 'Location in')
        self['nodeid'] = nodeid(self, bpy.data.node_groups)

    def draw_buttons(self, context, layout):
        if nodeinputs(self) and self.inputs[0].links[0].from_node.loc == '1':
            newrow(layout, 'Type', self, "wrtype")
            row = layout.row()
            row.operator("node.windrose", text="Create Wind Rose").nodeid = self['nodeid']
        else:
            row = layout.row()
            row.label('Location node error')

class ViLoc(bpy.types.Node, ViNodes):
    '''Node describing a geographical location manually or with an EPW file'''
    bl_idname = 'ViLoc'
    bl_label = 'VI Location'
    bl_icon = 'LAMP'
            
    def updatelatlong(self, context):
        (context.scene['latitude'], context.scene['longitude']) = epwlatilongi(context.scene, self) if self.loc == '1' and self.weather else (self.lat, self.long)

    (filepath, filename, filedir, newdir, filebase, objfilebase, nodetree, nproc, rm , cp, cat, fold) = (bpy.props.StringProperty() for x in range(12))
    epwpath = os.path.dirname(inspect.getfile(inspect.currentframe()))+'/EPFiles/Weather/'
    weatherlist = [((wfile, os.path.basename(wfile).strip('.epw').split(".")[0], 'Weather Location')) for wfile in glob.glob(epwpath+"/*.epw")]
    weather = bpy.props.EnumProperty(items = weatherlist, name="", description="Weather for this project", update = updatelatlong)
    loc = bpy.props.EnumProperty(items = [("0", "Manual", "Manual location"), ("1", "EPW ", "Get location from EPW file")], name = "", description = "Location", default = "0", update = updatelatlong)
    lat = bpy.props.FloatProperty(name="Latitude", description="Site Latitude", min=-90, max=90, default=52, update = updatelatlong)
    long = bpy.props.FloatProperty(name="Longitude", description="Site Longitude (East is positive, West is negative)", min=-180, max=180, default=0, update = updatelatlong)
    maxws = bpy.props.FloatProperty(name="", description="Max wind speed", min=0, max=90, default=0)
    minws = bpy.props.FloatProperty(name="", description="Min wind speed", min=0, max=90, default=0)
    avws = bpy.props.FloatProperty(name="", description="Average wind speed", min=0, max=90, default=0)
    startmonth = bpy.props.IntProperty(name = 'Start Month', default = 1, min = 1, max = 12, description = 'Start Month')
    endmonth = bpy.props.IntProperty(name = 'End Month', default = 12, min = 1, max = 12, description = 'End Month')
    exported = bpy.props.BoolProperty(default = 1)
    
    def init(self, context):
        self['nodeid'] = nodeid(self, bpy.data.node_groups)
        bpy.data.node_groups[self['nodeid'].split('@')[1]].use_fake_user = True
        self.outputs.new('ViLoc', 'Location out')
        bpy.context.scene['latitude'] = self.lat
        bpy.context.scene['longitude'] = self.long
        if bpy.data.filepath:
            nodeinit(self)
        
    def update(self):
        socklink(self.outputs[0], self['nodeid'].split('@')[1])

    def draw_buttons(self, context, layout):
        row = layout.row()
        row.label(text = 'Source:')
        row.prop(self, "loc")
        if self.loc == "1":
            row = layout.row()
            row.prop(self, "weather")
        else:
            row = layout.row()
            row.prop(self, "lat")
            row = layout.row()
            row.prop(self, "long")
        if not self.outputs['Location out'].is_linked or (self.outputs['Location out'].is_linked and self.outputs['Location out'].links[0].to_node.bl_label not in ('LiVi Basic', 'VI Sun Path')):
            row = layout.row()
            row.prop(self, "startmonth")
            row = layout.row()
            row.prop(self, "endmonth")
        
class ViGExEnNode(bpy.types.Node, ViNodes):
    '''Node describing an EnVi Geometry Export'''
    bl_idname = 'ViGExEnNode'
    bl_label = 'EnVi Geometry'

    exported = bpy.props.BoolProperty()

    def nodeupdate(self, context):
        self.exported = False
        self.outputs['Geometry out'].hide = True

    animtype = [('Static', "Static", "Simple static analysis"), ('Geometry', "Geometry", "Animated geometry analysis"), ('Material', "Material", "Animated material analysis"), ('Lights', "Lights", "Animated artificial lighting analysis")]
    animmenu = bpy.props.EnumProperty(name="", description="Animation type", items=animtype, default = 'Static', update = nodeupdate)
    epfiles = []

    def init(self, context):
        self.outputs.new('ViEnG', 'Geometry out')
        self.outputs['Geometry out'].hide = True
        self['nodeid'] = nodeid(self, bpy.data.node_groups)

    def draw_buttons(self, context, layout):
        row = layout.row()
        row.label('Animation:')
        row.prop(self, 'animmenu')
        row = layout.row()
        row.operator("node.engexport", text = "Export").nodeid = self['nodeid']

    def update(self):
        if self.outputs[0].is_linked:
            if self.outputs[0].links[0].to_socket.color() != self.outputs[0].color():
                link = self.outputs[0].links[0]
                bpy.data.node_groups['VI Network'].links.remove(link)

class ViExEnNode(bpy.types.Node, ViNodes):
    '''Node describing an EnergyPlus export'''
    bl_idname = 'ViExEnNode'
    bl_label = 'EnVi Export'
    bl_icon = 'LAMP'

    nproc = bpy.props.StringProperty()
    rm = bpy.props.StringProperty()
    cat = bpy.props.StringProperty()
    fold = bpy.props.StringProperty()
    cp = bpy.props.StringProperty()
    filepath = bpy.props.StringProperty()
    filename = bpy.props.StringProperty()
    filedir = bpy.props.StringProperty()
    newdir = bpy.props.StringProperty()
    filebase = bpy.props.StringProperty()
    idf_file = bpy.props.StringProperty()
    exported = bpy.props.BoolProperty()
    
    def nodeupdate(self, context):
        self.exported = False
        self.bl_label = '*EnVi Export'
        self.outputs['Context out'].hide = True

    loc = bpy.props.StringProperty(name="", description="Identifier for this project", default="", update = nodeupdate)
    terrain = bpy.props.EnumProperty(items=[("0", "City", "Towns, city outskirts, centre of large cities"),
                   ("1", "Urban", "Urban, Industrial, Forest"),("2", "Suburbs", "Rough, Wooded Country, Suburbs"),
                    ("3", "Country", "Flat, Open Country"),("4", "Ocean", "Ocean, very flat country")],
                    name="", description="Specify the surrounding terrain", default="0", update = nodeupdate)

    addonpath = os.path.dirname(inspect.getfile(inspect.currentframe()))
    matpath = addonpath+'/EPFiles/Materials/Materials.data'
    sdoy = bpy.props.IntProperty(name = "", description = "Day of simulation", min = 1, max = 365, default = 1, update = nodeupdate)
    edoy = bpy.props.IntProperty(name = "", description = "Day of simulation", min = 1, max = 365, default = 365, update = nodeupdate)
    timesteps = bpy.props.IntProperty(name = "", description = "Time steps per hour", min = 1, max = 4, default = 1, update = nodeupdate)
    
    restype= bpy.props.EnumProperty(items = [("0", "Ambient", "Ambient Conditions"), ("1", "Zone Thermal", "Thermal Results"), ("2", "Comfort", "Comfort Results"), ("3", "Zone Ventilation", "Zone Ventilation Results"), ("4", "Ventilation Link", "ZoneVentilation Results")],
                                   name="", description="Specify the EnVi results catagory", default="0", update = nodeupdate)

    resat = bpy.props.BoolProperty(name = "Temperature", description = "Ambient Temperature (K)", default = False, update = nodeupdate)
    resaws = bpy.props.BoolProperty(name = "Wind Speed", description = "Ambient Wind Speed (m/s)", default = False, update = nodeupdate)
    resawd = bpy.props.BoolProperty(name = "Wind Direction", description = "Ambient Wind Direction (degrees from North)", default = False, update = nodeupdate)
    resah = bpy.props.BoolProperty(name = "Humidity", description = "Ambient Humidity", default = False, update = nodeupdate)
    resasb = bpy.props.BoolProperty(name = "Direct Solar", description = u'Direct Solar Radiation (W/m\u00b2K)', default = False, update = nodeupdate)
    resasd = bpy.props.BoolProperty(name = "Diffuse Solar", description = u'Diffuse Solar Radiation (W/m\u00b2K)', default = False, update = nodeupdate)
    restt = bpy.props.BoolProperty(name = "Temperature", description = "Zone Temperatures", default = False, update = nodeupdate)
    restwh = bpy.props.BoolProperty(name = "Heating Watts", description = "Zone Heating Requirement (Watts)", default = False, update = nodeupdate)
    restwc = bpy.props.BoolProperty(name = "Cooling Watts", description = "Zone Cooling Requirement (Watts)", default = False, update = nodeupdate)
    reswsg = bpy.props.BoolProperty(name = "Solar Gain", description = "Window Solar Gain (Watts)", default = False, update = nodeupdate)
#    resthm = BoolProperty(name = "kWh/m2 Heating", description = "Zone Heating kilo Watt hours of heating per m2 floor area", default = False)
#    restcm = BoolProperty(name = "kWh/m2 Cooling", description = "Zone Cooling kilo Watt hours of cooling per m2 floor area", default = False)
    rescpp = bpy.props.BoolProperty(name = "PPD", description = "Percentage Proportion Dissatisfied", default = False, update = nodeupdate)
    rescpm = bpy.props.BoolProperty(name = "PMV", description = "Predicted Mean Vote", default = False, update = nodeupdate)
    resvls = bpy.props.BoolProperty(name = "Ventilation (l/s)", description = "Zone Ventilation rate (l/s)", default = False, update = nodeupdate)
    resvmh = bpy.props.BoolProperty(name = u'Ventilation (m3/h)', description = u'Zone Ventilation rate (m\u00b3/h)', default = False, update = nodeupdate)
#    resims = bpy.props.BoolProperty(name = u'Infiltration (m3/s)', description = u'Zone Infiltration rate (m\u00b3/s)', default = False, update = nodeupdate)
    resim = bpy.props.BoolProperty(name = u'Infiltration (m\u00b3)', description = u'Zone Infiltration (m\u00b3)', default = False, update = nodeupdate)
    resiach = bpy.props.BoolProperty(name = 'Infiltration (ACH)', description = 'Zone Infiltration rate (ACH)', default = False, update = nodeupdate)
    resco2 = bpy.props.BoolProperty(name = u'CO\u2082 concentration (ppm)', description = u'Zone CO\u2082 concentration (ppm)', default = False, update = nodeupdate)
    resihl = bpy.props.BoolProperty(name = "Heat loss (W)", description = "Ventilation Heat Loss (W)", default = False, update = nodeupdate)
    resl12ms = bpy.props.BoolProperty(name = u'Flow (m\u00b3/s)', description = u'Linkage flow (m\u00b3/s)', default = False, update = nodeupdate)
    reslof = bpy.props.BoolProperty(name = 'Opening factor', description = 'Linkage Opening Factor', default = False, update = nodeupdate)
    
    def init(self, context):
        self.inputs.new('ViEnG', 'Geometry in')
        self.inputs.new('ViLoc', 'Location in')
        self.outputs.new('ViEnC', 'Context out')
        self.outputs['Context out'].hide = True
        nodeinit(self)
        self['nodeid'] = nodeid(self, bpy.data.node_groups)        

    def draw_buttons(self, context, layout):
        row = layout.row()
        row.label("Project name/location")
        row.prop(self, "loc")
        row = layout.row()
        row.label(text = 'Terrain:')
        col = row.column()
        col.prop(self, "terrain")
        row = layout.row()
        row.label(text = 'Time-steps/hour)')
        row.prop(self, "timesteps")
        row = layout.row()
        row.label(text = 'Results Catagory:')
        col = row.column()
        col.prop(self, "restype")
        resdict = {'0': (0, "resat", "resaws", 0, "resawd", "resah", 0, "resasb", "resasd"), '1': (0, "restt", "restwh", 0, "restwc", "reswsg"),\
        '2': (0, "rescpp", "rescpm"), '3': (0, "resim", "resiach", 0, "resco2", "resihl"), '4': (0, "resl12ms", "reslof")}
        
        for rprop in resdict[self.restype]:        
            if not rprop:
                row = layout.row()
            else:
                row.prop(self, rprop)

        if all([s.is_linked for s in self.inputs]) and self.inputs['Location in'].links[0].from_node.loc == '1':
            row = layout.row()
            row.operator("node.enexport", text = 'Export').nodeid = self['nodeid']
                
class ViEnSimNode(bpy.types.Node, ViNodes):
    '''Node describing an EnergyPlus simulation'''
    bl_idname = 'ViEnSimNode'
    bl_label = 'EnVi Simulation'
    bl_icon = 'LAMP' 

    def init(self, context):
        self.inputs.new('ViEnC', 'Context in') 
        self.outputs.new('ViEnR', 'Results out')
        self.outputs['Results out'].hide = True
        self['nodeid'] = nodeid(self, bpy.data.node_groups) 
                
    def nodeupdate(self, context):
        self.exported = False
        self.bl_label = '*EnVi Simulation'
        self.outputs['Results out'].hide = True
        if self.inputs['Context in'].is_linked:
            self.resfilename = os.path.join(self.inputs['Context in'].links[0].from_node.newdir, self.resname+'.eso')
        
    resname = bpy.props.StringProperty(name="", description="Base name for the results files", default="results", update = nodeupdate)
    resfilename = bpy.props.StringProperty(name = "", default = 'results')
    dsdoy = bpy.props.IntProperty()
    dedoy = bpy.props.IntProperty()
    
    def update(self):
        if self.inputs['Context in'].is_linked:
            self.resfilename = os.path.join(self.inputs['Context in'].links[0].from_node.newdir, self.resname+'.eso')
    
    def draw_buttons(self, context, layout):
         if self.inputs['Context in'].is_linked:       
            row = layout.row()
            row.label(text = 'Results name:')
            row.prop(self, 'resname')
            row = layout.row()
            row.operator("node.ensim", text = 'Calculate').nodeid = self['nodeid']

class ViEnRFNode(bpy.types.Node, ViNodes):
    '''Node for EnergyPlus results file selection'''
    bl_idname = 'ViEnRFNode'
    bl_label = 'EnVi Results File'
    
    def nodeupdate(self, context):
        self.bl_label = '*EnVi Results File'
        self.outputs['Results out'].hide = True

    resfilename = bpy.props.StringProperty(name="", description="Name of the EnVi results file", default="", update = nodeupdate)
    dsdoy = bpy.props.IntProperty()
    dedoy = bpy.props.IntProperty()
    
    def init(self, context):
        self.outputs.new('ViEnR', 'Results out')
        self.outputs['Results out'].hide = True
        self['nodeid'] = nodeid(self, bpy.data.node_groups)
    
    def draw_buttons(self, context, layout):
        row = layout.row()
        row.label('ESO file:')
        row.operator('node.esoselect', text = 'Select ESO file').nodeid = self['nodeid']
        row = layout.row()
        row.prop(self, 'resfilename')
        row.operator("node.fileprocess", text = 'Process file').nodeid = self['nodeid']

class ViEnRNode(bpy.types.Node, ViNodes):
    '''Node for 2D results plotting'''
    bl_idname = 'ViChNode'
    bl_label = 'VI Chart'

    ctypes = [("0", "Line/Scatter", "Line/Scatter Plot"), ("1", "Bar", "Bar Chart")]
    dsh = bpy.props.IntProperty(name = "Start", description = "", min = 1, max = 24, default = 1)
    deh = bpy.props.IntProperty(name = "End", description = "", min = 1, max = 24, default = 24)
    charttype = bpy.props.EnumProperty(items = ctypes, name = "Chart Type", default = "0")
    timemenu = bpy.props.EnumProperty(items=[("0", "Hourly", "Hourly results"),("1", "Daily", "Daily results"), ("2", "Monthly", "Monthly results")],
                                                      name="", description="Results frequency", default="0")

    def init(self, context):
        self['nodeid'] = nodeid(self, bpy.data.node_groups)
        self.inputs.new("ViEnRXIn", "X-axis")
        self['Start'] = 1
        self['End'] = 365
        self.inputs.new("ViEnRY1In", "Y-axis 1")
        self.inputs["Y-axis 1"].hide = True
        self.inputs.new("ViEnRY2In", "Y-axis 2")
        self.inputs["Y-axis 2"].hide = True
        self.inputs.new("ViEnRY3In", "Y-axis 3")
        self.inputs["Y-axis 3"].hide = True

    def draw_buttons(self, context, layout):
        row = layout.row()
        row.label("Day:")
        row.prop(self, '["Start"]')
        row.prop(self, '["End"]')
        row = layout.row()
        row.label("Hour:")
        row.prop(self, "dsh")
        row.prop(self, "deh")
        row = layout.row()
        row.prop(self, "charttype")
        row.prop(self, "timemenu")

        if self.inputs['X-axis'].is_linked and self.inputs['Y-axis 1'].is_linked:
            layout.operator("node.chart", text = 'Create plot').nodeid = self['nodeid']

    def update(self):
        if self.inputs['X-axis'].is_linked == False:
            class ViEnRXIn(bpy.types.NodeSocket):
                '''Energy geometry out socket'''
                bl_idname = 'ViEnRXIn'
                bl_label = 'X-axis'

                def draw_color(self, context, node):
                    return (0.0, 1.0, 0.0, 0.75)
                def draw(self, context, layout, node, text):
                    layout.label('X-axis')

        else:
            xrtype, xctype, xztype, xzrtype, xltype, xlrtype = [], [], [], [], [], []
            try:
                innode = self.inputs['X-axis'].links[0].from_node
            except:
                return
            self["_RNA_UI"] = {"Start": {"min":innode.dsdoy, "max":innode.dedoy}, "End": {"min":innode.dsdoy, "max":innode.dedoy}}
            self['Start'], self['End'] = innode.dsdoy, innode.dedoy
            for restype in innode['rtypes']:
                xrtype.append((restype, restype, "Plot "+restype))
            for clim in innode['ctypes']:
                xctype.append((clim, clim, "Plot "+clim))
            for zone in innode['ztypes']:
                xztype.append((zone, zone, "Plot "+zone))
            for zoner in innode['zrtypes']:
                xzrtype.append((zoner, zoner, "Plot "+zoner))
            for link in innode['ltypes']:
                xltype.append((link, link, "Plot "+link))
            for linkr in innode['lrtypes']:
                xlrtype.append((linkr, linkr, "Plot "+linkr))
            if self.inputs.get('Y-axis 1'):
                self.inputs['Y-axis 1'].hide = False

            class ViEnRXIn(bpy.types.NodeSocket):
                '''Energy geometry out socket'''
                bl_idname = 'ViEnRXIn'
                bl_label = 'X-axis'

                if len(innode['rtypes']) > 0:
                    rtypemenu = bpy.props.EnumProperty(items=xrtype, name="", description="Data type", default = xrtype[0][0])
                    if 'Climate' in innode['rtypes']:
                        climmenu = bpy.props.EnumProperty(items=xctype, name="", description="Climate type", default = xctype[0][0])
                    if 'Zone' in innode['rtypes']:
                        zonemenu = bpy.props.EnumProperty(items=xztype, name="", description="Zone", default = xztype[0][0])
                        zonermenu = bpy.props.EnumProperty(items=xzrtype, name="", description="Zone result", default = xzrtype[0][0])
                    if 'Linkage' in innode['rtypes']:
                        linkmenu = bpy.props.EnumProperty(items=xltype, name="", description="Flow linkage result", default = xltype[0][0])
                        linkrmenu = bpy.props.EnumProperty(items=xlrtype, name="", description="Flow linkage result", default = xlrtype[0][0])
                    statmenu = bpy.props.EnumProperty(items=[('Average', 'Average', 'Average Value'), ('Maximum', 'Maximum', 'Maximum Value'), ('Minimum', 'Minimum', 'Minimum Value')], name="", description="Result statistic", default = 'Average')

                def draw(self, context, layout, node, text):
                    row = layout.row()
                    row.prop(self, "rtypemenu", text = text)
                    if self.is_linked == True:
                        typedict = {"Time": [], "Climate": ['climmenu'], "Zone": ("zonemenu", "zonermenu"), "Linkage":("linkmenu", "linkrmenu")}
                        for rtype in typedict[self.rtypemenu]:
                            row.prop(self, rtype)
                        if self.node.timemenu in ('1', '2') and self.rtypemenu !='Time':
                            row.prop(self, "statmenu")

                def draw_color(self, context, node):
                    return (0.0, 1.0, 0.0, 0.75)

                def color(self):
                    return (0.0, 1.0, 0.0, 0.75)
            bpy.utils.register_class(ViEnRXIn)

        if self.inputs.get('Y-axis 1'):
            if self.inputs['Y-axis 1'].is_linked == False:
                class ViEnRY1In(bpy.types.NodeSocket):
                    '''Energy geometry out socket'''
                    bl_idname = 'ViEnRY1In'
                    bl_label = 'Y-axis 1'
    
                    def draw_color(self, context, node):
                        return (0.0, 1.0, 0.0, 0.75)
                    def draw(self, context, layout, node, text):
                        layout.label('Y-axis 1')
               
                bpy.utils.register_class(ViEnRY1In)
                if self.inputs.get('Y-axis 2'):
                    self.inputs['Y-axis 2'].hide = True

            else:
                y1rtype, y1ctype, y1ztype, y1zrtype, y1ltype, y1lrtype = [], [], [], [], [], []
                innode = self.inputs['Y-axis 1'].links[0].from_node
                for restype in innode['rtypes']:
                    y1rtype.append((restype, restype, "Plot "+restype))
                for clim in innode['ctypes']:
                    y1ctype.append((clim, clim, "Plot "+clim))
                for zone in innode['ztypes']:
                    y1ztype.append((zone, zone, "Plot "+zone))
                for zoner in innode['zrtypes']:
                    y1zrtype.append((zoner, zoner, "Plot "+zoner))
                for link in innode['ltypes']:
                    y1ltype.append((link, link, "Plot "+link))
                for linkr in innode['lrtypes']:
                    y1lrtype.append((linkr, linkr, "Plot "+linkr))
    
                class ViEnRY1In(bpy.types.NodeSocket):
                    '''Energy geometry out socket'''
                    bl_idname = 'ViEnRY1In'
                    bl_label = 'Y-axis1'
                    if len(innode['rtypes']) > 0:
                        rtypemenu = bpy.props.EnumProperty(items=y1rtype, name="", description="Data type", default = y1rtype[0][0])
                        if 'Climate' in innode['rtypes']:
                            climmenu = bpy.props.EnumProperty(items=y1ctype, name="", description="Climate type", default = y1ctype[0][0])
                        if 'Zone' in innode['rtypes']:
                            zonemenu = bpy.props.EnumProperty(items=y1ztype, name="", description="Zone", default = y1ztype[0][0])
                            zonermenu = bpy.props.EnumProperty(items=y1zrtype, name="", description="Zone result", default = y1zrtype[0][0])
                        if 'Linkage' in innode['rtypes']:
                            linkmenu = bpy.props.EnumProperty(items=y1ltype, name="", description="Flow linkage result", default = y1ltype[0][0])
                            linkrmenu = bpy.props.EnumProperty(items=y1lrtype, name="", description="Flow linkage result", default = y1lrtype[0][0])
                        statmenu = bpy.props.EnumProperty(items=[('Average', 'Average', 'Average Value'), ('Maximum', 'Maximum', 'Maximum Value'), ('Minimum', 'Minimum', 'Minimum Value')], name="", description="Result statistic", default = 'Average')
    
    
                    def draw(self, context, layout, node, text):
                        row = layout.row()
                        row.prop(self, "rtypemenu", text = text)
                        if self.is_linked:
                            typedict = {"Time": [], "Climate": ['climmenu'], "Zone": ("zonemenu", "zonermenu"), "Linkage":("linkmenu", "linkrmenu")}
                            for rtype in typedict[self.rtypemenu]:
                                row.prop(self, rtype)
                            if self.node.timemenu in ('1', '2') and self.rtypemenu != 'Time':
                                row.prop(self, "statmenu")
    
                    def draw_color(self, context, node):
                        return (0.0, 1.0, 0.0, 0.75)
    
                    def color(self):
                        return (0.0, 1.0, 0.0, 0.75)
                bpy.utils.register_class(ViEnRY1In)
                self.inputs['Y-axis 2'].hide = False

        if self.inputs.get('Y-axis 2'):
            if self.inputs['Y-axis 2'].is_linked == False:
                class ViEnRY2In(bpy.types.NodeSocket):
                    '''Energy geometry out socket'''
                    bl_idname = 'ViEnRY2In'
                    bl_label = 'Y-axis 2'
    
                    def draw_color(self, context, node):
                        return (0.0, 1.0, 0.0, 0.75)
                    def draw(self, context, layout, node, text):
                        layout.label('Y-axis 2')
                
                bpy.utils.register_class(ViEnRY2In)
                if self.inputs.get('Y-axis 3'):
                    self.inputs['Y-axis 3'].hide = True
    
            else:
                y2rtype, y2ctype, y2ztype, y2zrtype, y2ltype, y2lrtype = [], [], [], [], [], []
                innode = self.inputs[2].links[0].from_node
                for restype in innode['rtypes']:
                    y2rtype.append((restype, restype, "Plot "+restype))
                for clim in innode['ctypes']:
                    y2ctype.append((clim, clim, "Plot "+clim))
                for zone in innode['ztypes']:
                    y2ztype.append((zone, zone, "Plot "+zone))
                for zoner in innode['zrtypes']:
                    y2zrtype.append((zoner, zoner, "Plot "+zoner))
                for link in innode['ltypes']:
                    y2ltype.append((link, link, "Plot "+link))
                for linkr in innode['lrtypes']:
                    y2lrtype.append((linkr, linkr, "Plot "+linkr))
    
                class ViEnRY2In(bpy.types.NodeSocket):
                    '''Energy geometry out socket'''
                    bl_idname = 'ViEnRY2In'
                    bl_label = 'Y-axis 2'
    
                    rtypemenu = bpy.props.EnumProperty(items=y2rtype, name="", description="Result type", default = y2rtype[0][0])
                    if 'Climate' in innode['rtypes']:
                        climmenu = bpy.props.EnumProperty(items=y2ctype, name="", description="Climate type", default = y2ctype[0][0])
                    if 'Zone' in innode['rtypes']:
                        zonemenu = bpy.props.EnumProperty(items=y2ztype, name="", description="Zone", default = y2ztype[0][0])
                        zonermenu = bpy.props.EnumProperty(items=y2zrtype, name="", description="Zone result", default = y2zrtype[0][0])
                    if 'Linkage' in innode['rtypes']:
                        linkmenu = bpy.props.EnumProperty(items=y2ltype, name="", description="Flow linkage result", default = y2ltype[0][0])
                        linkrmenu = bpy.props.EnumProperty(items=y2lrtype, name="", description="Flow linkage result", default = y2lrtype[0][0])
                    statmenu = bpy.props.EnumProperty(items=[('Average', 'Average', 'Average Value'), ('Maximum', 'Maximum', 'Maximum Value'), ('Minimum', 'Minimum', 'Minimum Value')], name="", description="Zone result", default = 'Average')
    
                    def draw(self, context, layout, node, text):
                        row = layout.row()
                        row.prop(self, "rtypemenu", text = text)
                        if self.is_linked:
                            typedict = {"Time": [], "Climate": ['climmenu'], "Zone": ("zonemenu", "zonermenu"), "Linkage":("linkmenu", "linkrmenu")}
                            for rtype in typedict[self.rtypemenu]:
                                row.prop(self, rtype)
                            if self.node.timemenu in ('1', '2') and self.rtypemenu != 'Time':
                                row.prop(self, "statmenu")
    
                    def draw_color(self, context, node):
                        return (0.0, 1.0, 0.0, 0.75)
    
                    def color(self):
                        return (0.0, 1.0, 0.0, 0.75)
    
                    self.inputs['Y-axis 3'].hide = False
                bpy.utils.register_class(ViEnRY2In)

        if self.inputs.get('Y-axis 3'):
            if self.inputs['Y-axis 3'].is_linked == False:
                class ViEnRY3In(bpy.types.NodeSocket):
                    '''Energy geometry out socket'''
                    bl_idname = 'ViEnRY3In'
                    bl_label = 'Y-axis 3'
    
                    def draw_color(self, context, node):
                        return (0.0, 1.0, 0.0, 0.75)
                    def draw(self, context, layout, node, text):
                        layout.label('Y-axis 3')
                bpy.utils.register_class(ViEnRY3In)
            else:
                y3rtype, y3ctype, y3ztype, y3zrtype, y3ltype, y3lrtype = [], [], [], [], [], []
                innode = self.inputs[3].links[0].from_node
                for restype in innode['rtypes']:
                    y3rtype.append((restype, restype, "Plot "+restype))
                for clim in innode['ctypes']:
                    y3ctype.append((clim, clim, "Plot "+clim))
                for zone in innode['ztypes']:
                    y3ztype.append((zone, zone, "Plot "+zone))
                for zoner in innode['zrtypes']:
                    y3zrtype.append((zoner, zoner, "Plot "+zoner))
                for link in innode['ltypes']:
                    y3ltype.append((link, link, "Plot "+link))
                for linkr in innode['lrtypes']:
                    y3lrtype.append((linkr, linkr, "Plot "+linkr))
    
                class ViEnRY3In(bpy.types.NodeSocket):
                    '''Energy geometry out socket'''
                    bl_idname = 'ViEnRY3In'
                    bl_label = 'Y-axis 3'
    
                    rtypemenu = bpy.props.EnumProperty(items=y3rtype, name="", description="Simulation accuracy", default = y3rtype[0][0])
                    if 'Climate' in innode['rtypes']:
                        climmenu = bpy.props.EnumProperty(items=y3ctype, name="", description="Climate type", default = y3ctype[0][0])
                    if 'Zone' in innode['rtypes']:
                        zonemenu = bpy.props.EnumProperty(items=y3ztype, name="", description="Zone", default = y3ztype[0][0])
                        zonermenu = bpy.props.EnumProperty(items=y3zrtype, name="", description="Zone result", default = y3zrtype[0][0])
                    if 'Linkage' in innode['rtypes']:
                        linkmenu = bpy.props.EnumProperty(items=y3ltype, name="", description="Flow linkage result", default = y3ltype[0][0])
                        linkrmenu = bpy.props.EnumProperty(items=y3lrtype, name="", description="Flow linkage result", default = y3lrtype[0][0])
                    statmenu = bpy.props.EnumProperty(items=[('Average', 'Average', 'Average Value'), ('Maximum', 'Maximum', 'Maximum Value'), ('Minimum', 'Minimum', 'Minimum Value')], name="", description="Zone result", default = 'Average')
    
                    def draw(self, context, layout, node, text):
                        row = layout.row()
                        row.prop(self, "rtypemenu", text = text)
                        if self.is_linked:
                            typedict = {"Time": [], "Climate": ['climmenu'], "Zone": ("zonemenu", "zonermenu"), "Linkage":("linkmenu", "linkrmenu")}
                            for rtype in typedict[self.rtypemenu]:
                                row.prop(self, rtype)
                            if self.node.timemenu in ('1', '2') and self.rtypemenu != 'Time':
                                row.prop(self, "statmenu")
    
                    def draw_color(self, context, node):
                        return (0.0, 1.0, 0.0, 0.75)
    
                    def color(self):
                        return (0.0, 1.0, 0.0, 0.75)
                
                bpy.utils.register_class(ViEnRY3In)

class ViNodeCategory(NodeCategory):
    @classmethod
    def poll(cls, context):
        return context.space_data.tree_type == 'ViN'

class ViLocOut(bpy.types.NodeSocket):
    '''Vi Location socket'''
    bl_idname = 'ViLoc'
    bl_label = 'Location socket'

    def draw(self, context, layout, node, text):
        layout.label(text)

    def draw_color(self, context, node):
        return (0.0, 1.0, 0.0, 0.75)

class ViLiWResOut(bpy.types.NodeSocket):
    '''LiVi irradiance out socket'''
    bl_idname = 'LiViWOut'
    bl_label = 'LiVi W/m2 out'

    def draw(self, context, layout, node, text):
        layout.label(text)

    def draw_color(self, context, node):
        return (1.0, 0.2, 0.2, 0.75)

class ViLiGIn(bpy.types.NodeSocket):
    '''Lighting geometry socket'''
    bl_idname = 'ViLiG'
    bl_label = 'Geometry'

    def draw(self, context, layout, node, text):
        layout.label(text)

    def draw_color(self, context, node):
        return (0.3, 0.17, 0.07, 0.75)

    def color(self):
        return (0.3, 0.17, 0.07, 0.75)

class ViLiC(bpy.types.NodeSocket):
    '''Lighting context in socket'''
    bl_idname = 'ViLiC'
    bl_label = 'Context'

    def draw(self, context, layout, node, text):
        layout.label(text)

    def draw_color(self, context, node):
        return (1.0, 1.0, 0.0, 0.75)

    def color(self):
        return (1.0, 1.0, 0.0, 0.75)
        
class ViGen(bpy.types.NodeSocket):
    '''VI Generative geometry socket'''
    bl_idname = 'ViGen'
    bl_label = 'Generative geometry'

    def draw(self, context, layout, node, text):
        layout.label(text)

    def draw_color(self, context, node):
        return (0.0, 1.0, 1.0, 0.75)

    def color(self):
        return (0.0, 1.0, 1.0, 0.75)
        
class ViTar(bpy.types.NodeSocket):
    '''VI Generative target socket'''
    bl_idname = 'ViTar'
    bl_label = 'Generative target'

    def draw(self, context, layout, node, text):
        layout.label(text)

    def draw_color(self, context, node):
        return (1.0, 0.0, 1.0, 0.75)

    def color(self):
        return (1.0, 0.0, 1.0, 0.75)

class ViEnG(bpy.types.NodeSocket):
    '''Energy geometry out socket'''
    bl_idname = 'ViEnG'
    bl_label = 'EnVi Geometry'

    def draw(self, context, layout, node, text):
        layout.label(text)

    def draw_color(self, context, node):
        return (0.0, 0.0, 1.0, 0.75)

    def color(self):
        return (0.0, 0.0, 1.0, 0.75)

class ViEnR(bpy.types.NodeSocket):
    '''Energy results out socket'''
    bl_idname = 'ViEnR'
    bl_label = 'EnVi results'

    def draw(self, context, layout, node, text):
        layout.label(text)

    def draw_color(self, context, node):
        return (0.0, 1.0, 0.0, 0.75)

    def color(self):
        return (0.0, 1.0, 0.0, 0.75)
        
class ViEnC(bpy.types.NodeSocket):
    '''EnVi context socket'''
    bl_idname = 'ViEnC'
    bl_label = 'EnVi context'

    def draw(self, context, layout, node, text):
        layout.label(text)

    def draw_color(self, context, node):
        return (0.0, 1.0, 1.0, 0.75)

    def color(self):
        return (0.0, 1.0, 1.0, 0.75)

class EnViDataIn(bpy.types.NodeSocket):
    '''EnVi data in socket'''
    bl_idname = 'EnViDIn'
    bl_label = 'EnVi data in socket'

    def draw(self, context, layout, node, text):
        layout.label(text)

    def draw_color(self, context, node):
        return (0.0, 1.0, 0.0, 0.75)

# Generative nodes
class ViGenNode(bpy.types.Node, ViNodes):
    '''Generative geometry manipulation node'''
    bl_idname = 'ViGenNode'
    bl_label = 'VI Generative'
    bl_icon = 'LAMP'

    geotype = [('Object', "Object", "Object level manipulation"), ('Mesh', "Mesh", "Mesh level manipulation")]
    geomenu = bpy.props.EnumProperty(name="", description="Geometry type", items=geotype, default = 'Mesh')
    seltype = [('All', "All", "All geometry"), ('Selected', "Selected", "Only selected geometry"), ('Not selected', "Not selected", "Only unselected geometry")]
    oselmenu = bpy.props.EnumProperty(name="", description="Object selection", items=seltype, default = 'Selected')
    mselmenu = bpy.props.EnumProperty(name="", description="Mesh selection", items=seltype, default = 'Selected')
    omantype = [('0', "Move", "Move geometry"), ('1', "Rotate", "Only unselected geometry"), ('2', "Scale", "Scale geometry")]
    omanmenu = bpy.props.EnumProperty(name="", description="Manipulation type", items=omantype, default = '0')
    mmantype = [('0', "Move", "Move geometry"), ('1', "Rotate", "Only unselected geometry"), ('2', "Scale", "Scale geometry"), ('3', "Extrude", "Extrude geometry")]
    mmanmenu = bpy.props.EnumProperty(name="", description="Manipulation type", items=mmantype, default = '0')
    x = bpy.props.FloatProperty(name = 'X', min = 0, max = 1, default = 1)
    y = bpy.props.FloatProperty(name = 'Y', min = 0, max = 1, default = 0)
    z = bpy.props.FloatProperty(name = 'Z', min = 0, max = 1, default = 0)
    normal = bpy.props.BoolProperty(name = '', default = False)
    direction = bpy.props.EnumProperty(items=[("0", "Positive", "Increase/positive direction"),("1", "Negative", "Decrease/negative direction")],  name="", description="Manipulation direction", default="0")
    extent = bpy.props.FloatProperty(name = '', min = 0, max = 360, default = 0)
    steps = bpy.props.IntProperty(name = '', min = 1, max = 100, default = 1)

    #    buildstorey = bpy.props.EnumProperty(items=[("0", "Single", "Single storey building"),("1", "Multi", "Multi-storey building")], name="", description="Building storeys", default="0", update = nodeupdate)

    def init(self, context):
        self.inputs.new('ViGen', 'Generative in')
        self['nodeid'] = nodeid(self, bpy.data.node_groups)

    def draw_buttons(self, context, layout):
        newrow(layout, 'Geometry:', self, 'geomenu')
        newrow(layout, 'Object Selection:', self, 'oselmenu')
        if self.geomenu == 'Object':
           newrow(layout, 'Manipulation:', self, 'omanmenu')
           row = layout.row()
           col = row.column()
           subrow = col.row(align=True)
           subrow.prop(self, 'x')
           subrow.prop(self, 'y')
           subrow.prop(self, 'z')
        else:
           newrow(layout, 'Mesh Selection:', self, 'mselmenu') 
           newrow(layout, 'Manipulation:', self, 'mmanmenu')
           newrow(layout, 'Normal:', self, 'normal')
           if not self.normal:
               row = layout.row()
               col = row.column()
               subrow = col.row(align=True)
               subrow.prop(self, 'x')
               subrow.prop(self, 'y')
               subrow.prop(self, 'z')
        newrow(layout, 'Direction:', self, 'direction')
        newrow(layout, 'Extent:', self, 'extent')
        newrow(layout, 'Increment:', self, 'steps')

class ViTarNode(bpy.types.Node, ViNodes):
    '''Target Node'''
    bl_idname = 'ViTarNode'
    bl_label = 'VI Target'
    bl_icon = 'LAMP'

    ab = bpy.props.EnumProperty(items=[("0", "Above", "Target is above level"),("1", "Below", "Target is below level")],  name="", description="Whether target is to go above or below a specified level", default="0")
    stat = bpy.props.EnumProperty(items=[("0", "Average", "Average of data points"),("1", "Max", "Maximum of data points"),("2", "Min", "Minimum of data points"),("3", "Tot", "Total of data points")],  name="", description="Metric statistic", default="0")
    value = bpy.props.FloatProperty(name = '', min = 0, max = 100000, default = 0, description="Desired value")

    def init(self, context):
        self.inputs.new('ViTar', 'Target in')
        self['nodeid'] = nodeid(self, bpy.data.node_groups)
        
    def draw_buttons(self, context, layout):
        newrow(layout, 'Above/Below:', self, 'ab')
        newrow(layout, 'Statistic:', self, 'stat')
        newrow(layout, 'Value:', self, 'value')

viexnodecat = [NodeItem("ViLoc", label="VI Location"), NodeItem("ViGExLiNode", label="LiVi Geometry"), NodeItem("ViLiNode", label="LiVi Basic"), NodeItem("ViLiCNode", label="LiVi Compliance"), NodeItem("ViLiCBNode", label="LiVi CBDM"), NodeItem("ViGExEnNode", label="EnVi Geometry"), NodeItem("ViExEnNode", label="EnVi Export")]

vinodecat = [NodeItem("ViLiSNode", label="LiVi Simulation"),\
             NodeItem("ViSPNode", label="VI-Suite sun path"), NodeItem("ViSSNode", label="VI-Suite shadow study"), NodeItem("ViWRNode", label="VI-Suite wind rose"), NodeItem("ViEnSimNode", label="EnVi Simulation")]

vigennodecat = [NodeItem("ViGenNode", label="VI-Suite Generative"), NodeItem("ViTarNode", label="VI-Suite Target")]

vidisnodecat = [NodeItem("ViChNode", label="VI-Suite Chart"), NodeItem("ViEnRFNode", label="EnergyPlus result file")]

vinode_categories = [ViNodeCategory("Display", "Display Nodes", items=vidisnodecat), ViNodeCategory("Generative", "Generative Nodes", items=vigennodecat), ViNodeCategory("Analysis", "Analysis Nodes", items=vinodecat), ViNodeCategory("Export", "Export Nodes", items=viexnodecat)]


####################### EnVi ventilation network ##############################

class EnViNetwork(bpy.types.NodeTree):
    '''A node tree for the creation of EnVi advanced ventilation networks.'''
    bl_idname = 'EnViN'
    bl_label = 'EnVi Network'
    bl_icon = 'FORCE_WIND'
    nodetypes = {}

class EnViNodes:
    @classmethod
    def poll(cls, ntree):
        return ntree.bl_idname == 'EnViN'

class EnViBoundSocket(bpy.types.NodeSocket):
    '''A plain zone boundary socket'''
    bl_idname = 'EnViBoundSocket'
    bl_label = 'Plain zone boundary socket'
    bl_color = (1.0, 1.0, 0.2, 0.5)
    sn = bpy.props.StringProperty()
    def draw(self, context, layout, node, text):
        layout.label(text)

    def draw_color(self, context, node):
        return (0.5, 0.2, 0.0, 0.75)

class EnViSchedSocket(bpy.types.NodeSocket):
    '''Schedule socket'''
    bl_idname = 'EnViSchedSocket'
    bl_label = 'Schedule socket'

    def draw(self, context, layout, node, text):
        layout.label(text)

    def draw_color(self, context, node):
        return (1.0, 1.0, 0.0, 0.75)

class EnViSAirSocket(bpy.types.NodeSocket):
    '''A plain zone surface airflow socket'''
    bl_idname = 'EnViSAirSocket'
    bl_label = 'Plain zone surface airflow socket'
    sn = bpy.props.StringProperty()

    def draw(self, context, layout, node, text):
        layout.label(text)

    def draw_color(self, context, node):
        return (0.1, 1.0, 0.2, 0.75)

class EnViCAirSocket(bpy.types.NodeSocket):
    '''A plain zone airflow component socket'''
    bl_idname = 'EnViCAirSocket'
    bl_label = 'Plain zone airflow component socket'
    sn = bpy.props.StringProperty()

    def draw(self, context, layout, node, text):
        layout.label(text)

    def draw_color(self, context, node):
        return (1.0, 0.2, 0.2, 0.75)

class EnViCrRefSocket(bpy.types.NodeSocket):
    '''A plain zone airflow component socket'''
    bl_idname = 'EnViCrRefSocket'
    bl_label = 'Plain zone airflow component socket'
    sn = bpy.props.StringProperty()
    
    def draw(self, context, layout, node, text):
        layout.label(text)

    def draw_color(self, context, node):
        return (1.0, 0.4, 0.0, 0.75)

class EnViOccSocket(bpy.types.NodeSocket):
    '''An EnVi zone occupancy socket'''
    bl_idname = 'EnViOccSocket'
    bl_label = 'Zone occupancy socket'
    sn = bpy.props.StringProperty()

    def draw(self, context, layout, node, text):
        layout.label(text)

    def draw_color(self, context, node):
        return (1.0, 0.2, 0.2, 0.75)

class AFNCon(bpy.types.Node, EnViNodes):
    '''Node defining the overall airflow network simulation'''
    bl_idname = 'AFNCon'
    bl_label = 'Control'
    bl_icon = 'SOUND'

    afnname = bpy.props.StringProperty()
    afntype = bpy.props.EnumProperty(items = [('MultizoneWithDistribution', 'MultizoneWithDistribution', 'Include a forced airflow system in the model'),
                                              ('MultizoneWithoutDistribution', 'MultizoneWithoutDistribution', 'Exclude a forced airflow system in the model'),
                                              ('MultizoneWithDistributionOnlyDuringFanOperation', 'MultizoneWithDistributionOnlyDuringFanOperation', 'Apply forced air system only when in operation'),
                                              ('NoMultizoneOrDistribution', 'NoMultizoneOrDistribution', 'Only zone infiltration controls are modelled')], name = "", default = 'MultizoneWithoutDistribution')

    wpctype = bpy.props.EnumProperty(items = [('SurfaceAverageCalculation', 'SurfaceAverageCalculation', 'Calculate wind pressure coefficients based on oblong building assumption'),
                                              ('Input', 'Input', 'Input wind pressure coefficients from an external source')], name = "", default = 'SurfaceAverageCalculation')
    wpcaname = bpy.props.StringProperty()
    wpchs = bpy.props.EnumProperty(items = [('OpeningHeight', 'OpeningHeight', 'Calculate wind pressure coefficients based on opening height'),
                                              ('ExternalNode', 'ExternalNode', 'Calculate wind pressure coefficients based on external node height')], name = "", default = 'OpeningHeight')
    buildtype = bpy.props.EnumProperty(items = [('LowRise', 'Low Rise', 'Height is less than 3x the longest wall'),
                                              ('HighRise', 'High Rise', 'Height is more than 3x the longest wall')], name = "", default = 'LowRise')

    maxiter = bpy.props.IntProperty(default = 500, description = 'Maximum Number of Iterations')

    initmet = bpy.props.EnumProperty(items = [('ZeroNodePressures', 'ZeroNodePressures', 'Initilisation type'),
                                              ('LinearInitializationMethod', 'LinearInitializationMethod', 'Initilisation type')], name = "", default = 'ZeroNodePressures')

    rcontol = bpy.props.FloatProperty(default = 0.0001, description = 'Relative Airflow Convergence Tolerance')

    acontol = bpy.props.FloatProperty(default = 0.000001, description = 'Absolute Airflow Convergence Tolerance')

    conal = bpy.props.FloatProperty(default = -0.1, max = 1, min = -1, description = 'Convergence Acceleration Limit')
    aalax = bpy.props.IntProperty(default = 0, max = 180, min = 0, description = 'Azimuth Angle of Long Axis of Building')
    rsala = bpy.props.FloatProperty(default = 1, max = 1, min = 0, description = 'Ratio of Building Width Along Short Axis to Width Along Long Axis')

    def draw_buttons(self, context, layout):
        layout.prop(self, 'afnname')
        row = layout.row()
        row.prop(self, 'afntype')
        row = layout.row()
        row.prop(self, 'wpctype')
        if self.wpctype == 'Input':
            row = layout.row()
            row.prop(self, 'wpcaname')
            row = layout.row()
            row.prop(self, 'wpchs')
        elif self.wpctype == 'SurfaceAverageCalculation':
            row = layout.row()
            row.prop(self, 'buildtype')
        row = layout.row()
        row.prop(self, 'maxiter')
        row = layout.row()
        row.prop(self, 'initmet')
        row = layout.row()
        row.prop(self, 'rcontol')
        row = layout.row()
        row.prop(self, 'acontol')
        row = layout.row()
        row.prop(self, 'conal')
        if self.wpctype == 'SurfaceAverageCalculation':
            row = layout.row()
            row.prop(self, 'aalax')
            row = layout.row()
            row.prop(self, 'rsala')

class EnViZone(bpy.types.Node, EnViNodes):
    '''Node describing a simulation zone'''
    bl_idname = 'EnViZone'
    bl_label = 'Zone'
    bl_icon = 'SOUND'

    def zupdate(self, context):
        obj = bpy.data.objects[self.zone]
        odm = obj.data.materials
        omw = obj.matrix_world
        self.location = (50 * (omw*obj.location)[0], ((omw*obj.location)[2] + (omw*obj.location)[1])*25)
        self.zonevolume = objvol('', obj)
        for oname in [outputs for outputs in self.outputs if outputs.name not in [mat.name for mat in odm if mat.envi_boundary == True] and outputs.bl_idname == 'EnViBoundSocket']:
            self.outputs.remove(oname)
        for oname in [outputs for outputs in self.outputs if outputs.name not in [mat.name for mat in odm if mat.afsurface == True] and outputs.bl_idname == 'EnViCAirSocket']:
            self.outputs.remove(oname)
        for iname in [inputs for inputs in self.inputs if inputs.name not in [mat.name for mat in odm if mat.envi_boundary == True] and inputs.bl_idname == 'EnViBoundSocket']:
            self.inputs.remove(iname)
        for iname in [inputs for inputs in self.inputs if inputs.name not in [mat.name for mat in odm if mat.afsurface == True] and inputs.bl_idname == 'EnViCAirSocket']:
            self.inputs.remove(iname)

        socklist = [odm[face.material_index].name for face in obj.data.polygons if odm[face.material_index].envi_boundary == 1 and odm[face.material_index].name not in [outp.name for outp in self.outputs if outp.bl_idname == 'EnViBoundSocket']]
        for sock in sorted(set(socklist)):
            self.outputs.new('EnViBoundSocket', sock+'_b')
            self.inputs.new('EnViBoundSocket', sock+'_b')
        socklist = [(odm[face.material_index].name, face.index) for face in obj.data.polygons if odm[face.material_index].afsurface == 1 and odm[face.material_index].envi_con_type not in ('Window', 'Door') and odm[face.material_index].name not in [outp.name for outp in self.outputs if outp.bl_idname == 'EnViCAirSocket']]
        for sock in sorted(set(socklist)):
            self.outputs.new('EnViCAirSocket', sock[0]+'_c').sn = str(sock[1])
            self.inputs.new('EnViCAirSocket', sock[0]+'_c').sn = str(sock[1])
        socklist = [(odm[face.material_index].name, face.index) for face in obj.data.polygons if odm[face.material_index].afsurface == 1 and odm[face.material_index].envi_con_type in ('Window', 'Door') and odm[face.material_index].name not in [outp.name for outp in self.outputs if outp.bl_idname == 'EnViSAirSocket']]
        for sock in sorted(set(socklist)):
            if not self.outputs.get(sock[0]+'_s'):
                self.outputs.new('EnViSAirSocket', sock[0]+'_s').sn = str(sock[1])
            if not self.inputs.get(sock[0]+'_s'):
                self.inputs.new('EnViSAirSocket', sock[0]+'_s').sn = str(sock[1])

    def supdate(self, context):
        self.outputs['TSPSchedule'].hide = False if self.control == 'Temperature' else True

    zone = bpy.props.StringProperty(update = zupdate)
    controltype = [("NoVent", "None", "No ventilation control"), ("Temperature", "Temperature", "Temperature control")]
    control = bpy.props.EnumProperty(name="", description="Ventilation control type", items=controltype, default='NoVent', update = supdate)
    zonevolume = bpy.props.FloatProperty(name = '')
    mvof = bpy.props.FloatProperty(default = 0, name = "", min = 0, max = 1)
    lowerlim = bpy.props.FloatProperty(default = 0, name = "", min = 0, max = 100)
    upperlim = bpy.props.FloatProperty(default = 50, name = "", min = 0, max = 100)

    def init(self, context):
        self.outputs.new('EnViSchedSocket', 'TSPSchedule')
        self.outputs['TSPSchedule'].hide = True
        self.outputs.new('EnViSchedSocket', 'VASchedule')

    def update(self):
        try:
            for inp in [inp for inp in self.inputs if inp.bl_idname in ('EnViBoundSocket', 'EnViCAirSocket')]:
                self.outputs[inp.name].hide = True if inp.is_linked and self.outputs[inp.name].bl_idname == inp.bl_idname else False
            for outp in [outp for outp in self.outputs if outp.bl_idname in ('EnViBoundSocket', 'EnViCAirSocket')]:
                self.inputs[outp.name].hide = True if outp.is_linked and self.inputs[outp.name].bl_idname == outp.bl_idname else False
        except Exception as e:
            print(e)

    def draw_buttons(self, context, layout):
        row=layout.row()
        row.prop(self, "zone")
        newrow(layout, "Volume:", self, "zonevolume")
        newrow(layout, "Control type:", self, "control")
        if self.control == 'Temperature':
            newrow(layout, "Minimum OF:", self, "mvof")
            newrow(layout, "Lower:", self, "lowerlim")
            newrow(layout, "Upper:", self, "upperlim")

class EnViSLinkNode(bpy.types.Node, EnViNodes):
    '''Node describing an surface airflow component'''
    bl_idname = 'EnViSLink'
    bl_label = 'Envi surface airflow Component'
    bl_icon = 'SOUND'

    def supdate(self, context):
        self.outputs['Reference'].hide = False if self.linkmenu in ('Crack', 'EF') else True
        self.outputs['TSPSchedule'].hide = False if self.linkmenu in ('SO', 'DO', 'HO') else True
        if self.linkmenu in ('SO', 'DO', 'HO'):
            for sock in [sock for sock in [outs for outs in self.outputs]+[ins for ins in self.inputs] if sock.bl_idname == 'EnViCAirSocket']:
                if sock.is_linked == True:
                    bpy.data.node_groups['EnVi Network'].links.remove(sock.links[0])
                sock.hide = True
            for sock in [sock for sock in [outs for outs in self.outputs]+[ins for ins in self.inputs] if sock.bl_idname == 'EnViSAirSocket']:
                sock.hide = False
        else:
            for sock in [sock for sock in [outs for outs in self.outputs]+[ins for ins in self.inputs] if sock.bl_idname == 'EnViSAirSocket']:
                if sock.is_linked == True:
                    bpy.data.node_groups['EnVi Network'].links.remove(sock.links[0])
                sock.hide = True
            for sock in [sock for sock in [outs for outs in self.outputs]+[ins for ins in self.inputs] if sock.bl_idname == 'EnViCAirSocket']:
                sock.hide = False

    linktype = [("SO", "Simple Opening", "Simple opening element"),("DO", "Detailed Opening", "Detailed opening element"),
        ("HO", "Horizontal Opening", "Horizontal opening element"),("Crack", "Crack", "Crack aperture used for leakage calculation"),
        ("ELA", "ELA", "Effective leakage area"), ("EF", "Exhaust fan", "Exhaust fan")]

    linkmenu = bpy.props.EnumProperty(name="Type", description="Linkage type", items=linktype, default='SO', update = supdate)

    wdof = bpy.props.FloatProperty(default = 1, min = 0, max = 1, name = "")
    controltype = [("ZoneLevel", "ZoneLevel", "Zone level ventilation control"), ("NoVent", "None", "No ventilation control"),
                   ("Temperature", "Temperature", "Temperature control")]
    controls = bpy.props.EnumProperty(name="", description="Ventilation control type", items=controltype, default='ZoneLevel')
    controlc = bpy.props.EnumProperty(name="", description="Ventilation control type", items=controltype[:-1], default='ZoneLevel')
    mvof = bpy.props.FloatProperty(default = 0, min = 0, max = 1, name = "", description = 'Minimium venting open factor')
    lvof = bpy.props.FloatProperty(default = 0, min = 0, max = 100, name = "", description = 'Indoor and Outdoor Temperature Difference Lower Limit For Maximum Venting Open Factor (deltaC)')
    uvof = bpy.props.FloatProperty(default = 1, min = 1, max = 100, name = "", description = 'Indoor and Outdoor Temperature Difference Upper Limit For Minimum Venting Open Factor (deltaC)')
    amfcc = bpy.props.FloatProperty(default = 0.001, min = 0, max = 1, name = "", description = 'Air Mass Flow Coefficient When Opening is Closed (kg/s-m)')
    amfec = bpy.props.FloatProperty(default = 0.65,min = 0.5, max = 1, name = '', description =  'Air Mass Flow Exponent When Opening is Closed (dimensionless)')
    lvo = bpy.props.EnumProperty(items = [('NonPivoted', 'NonPivoted', 'Non pivoting opening'), ('HorizontallyPivoted', 'HPivoted', 'Horizontally pivoting opening')], default = 'NonPivoted', description = 'Type of Rectanguler Large Vertical Opening (LVO)')
    ecl = bpy.props.FloatProperty(default = 0.0, min = 0, name = '', description = 'Extra Crack Length or Height of Pivoting Axis (m)')
    noof = bpy.props.IntProperty(default = 2, min = 2, max = 4, name = '', description = 'Number of Sets of Opening Factor Data')
    spa = bpy.props.IntProperty(default = 90, min = 0, max = 90, name = '', description = 'Sloping Plane Angle')
    dcof = bpy.props.FloatProperty(default = 0.2, min = 0, max = 1, name = '', description = 'Discharge Coefficient')
    ddtw = bpy.props.FloatProperty(default = 0.1, min = 0, max = 10, name = '', description = 'Mimum Density Difference for Two-way Flow')
    amfc = bpy.props.FloatProperty(default = 1.0, name = "")
    amfe = bpy.props.FloatProperty(default = 0.6, name = "")
    dlen = bpy.props.FloatProperty(default = 2, name = "")
    dhyd = bpy.props.FloatProperty(default = 0.1, name = "")
    dcs = bpy.props.FloatProperty(default = 0.1, name = "")
    dsr = bpy.props.FloatProperty(default = 0.0009, name = "")
    dlc = bpy.props.FloatProperty(default = 1.0, name = "")
    dhtc = bpy.props.FloatProperty(default = 0.772, name = "")
    dmtc = bpy.props.FloatProperty(default = 0.0001, name = "")
    cf = bpy.props.FloatProperty(default = 1, min = 0, max = 1, name = "")
    ela = bpy.props.FloatProperty(default = 0.1, min = 0, max = 1, name = "")
    rpd = bpy.props.FloatProperty(default = 4, min = 0.1, max = 50, name = "")
    dcof1 = bpy.props.FloatProperty(default = 0.001, min = 0, max = 1, name = '', description = 'Discharge Coefficient for Opening Factor 1 (dimensionless)')
    wfof1 = bpy.props.FloatProperty(default = 0.0, min = 0, max = 1, name = '', description = 'Width Factor for Opening Factor 1 (dimensionless)')
    hfof1 = bpy.props.FloatProperty(default = 0.0, min = 0, max = 1, name = '', description = 'Height Factor for Opening Factor 1 (dimensionless)')
    sfof1 = bpy.props.FloatProperty(default = 0.0, min = 0, max = 1, name = '', description = 'Start Height Factor for Opening Factor 1 (dimensionless)')
    of2 = bpy.props.FloatProperty(default = 0.0, min = 0, max = 1, name = '', description = 'Opening Factor 2 (dimensionless)')
    dcof2 = bpy.props.FloatProperty(default = 0.001, min = 0, max = 1, name = '', description = 'Discharge Coefficient for Opening Factor 2 (dimensionless)')
    wfof2 = bpy.props.FloatProperty(default = 0.0, min = 0, max = 1, name = '', description = 'Width Factor for Opening Factor 2 (dimensionless)')
    hfof2 = bpy.props.FloatProperty(default = 0.0, min = 0, max = 1, name = '', description = 'Height Factor for Opening Factor 2 (dimensionless)')
    sfof2 = bpy.props.FloatProperty(default = 0.0, min = 0, max = 1, name = '', description = 'Start Height Factor for Opening Factor 2 (dimensionless)')
    of3 = bpy.props.FloatProperty(default = 0.0, min = 0, max = 1, name = '', description = 'Opening Factor 3 (dimensionless)')
    dcof3 = bpy.props.FloatProperty(default = 0.001, min = 0, max = 1, name = '', description = 'Discharge Coefficient for Opening Factor 3 (dimensionless)')
    wfof3 = bpy.props.FloatProperty(default = 0.0, min = 0, max = 1, name = '', description = 'Width Factor for Opening Factor 3 (dimensionless)')
    hfof3 = bpy.props.FloatProperty(default = 0.0, min = 0, max = 1, name = '', description = 'Height Factor for Opening Factor 3 (dimensionless)')
    sfof3 = bpy.props.FloatProperty(default = 0.0, min = 0, max = 1, name = '', description = 'Start Height Factor for Opening Factor 3 (dimensionless)')
    of4 = bpy.props.FloatProperty(default = 0.0, min = 0, max = 1, name = '', description = 'Opening Factor 4 (dimensionless)')
    dcof4 = bpy.props.FloatProperty(default = 0.001, min = 0, max = 1, name = '', description = 'Discharge Coefficient for Opening Factor 4 (dimensionless)')
    wfof4 = bpy.props.FloatProperty(default = 0.0, min = 0, max = 1, name = '', description = 'Width Factor for Opening Factor 4 (dimensionless)')
    hfof4 = bpy.props.FloatProperty(default = 0.0, min = 0, max = 1, name = '', description = 'Height Factor for Opening Factor 4 (dimensionless)')
    sfof4 = bpy.props.FloatProperty(default = 0.0, min = 0, max = 1, name = '', description = 'Start Height Factor for Opening Factor 4 (dimensionless)')
    dcof = bpy.props.FloatProperty(default = 0.2, min = 0, max = 1, name = '', description = 'Discharge Coefficient')

    def init(self, context):
        self['nodeid'] = nodeid(self, bpy.data.node_groups)
        self.inputs.new('EnViSAirSocket', 'Node 1', identifier = 'Node1_s')
        self.inputs.new('EnViSAirSocket', 'Node 2', identifier = 'Node2_s')
        self.outputs.new('EnViSAirSocket', 'Node 1', identifier = 'Node1_s')
        self.outputs.new('EnViSAirSocket', 'Node 2', identifier = 'Node2_s')
        self.outputs.new('EnViSchedSocket', 'VASchedule')
        self.outputs.new('EnViSchedSocket', 'TSPSchedule')
        self.outputs.new('EnViCrRefSocket', 'Reference')
        self.outputs['Reference'].hide = True
        self.inputs.new('EnViCAirSocket', 'Node 1', identifier = 'Node1_c')
        self.inputs.new('EnViCAirSocket', 'Node 2', identifier = 'Node2_c')
        self.outputs.new('EnViCAirSocket', 'Node 1', identifier = 'Node1_c')
        self.outputs.new('EnViCAirSocket', 'Node 2', identifier = 'Node2_c')
        for sock in [sock for sock in [outs for outs in self.outputs]+[ins for ins in self.inputs] if sock.identifier[-1] == 'c']:
            sock.hide = True

    def update(self):
        for sock in [sock for sock in self.inputs]+[sock for sock in self.outputs]:
            socklink(sock, self['nodeid'].split('@')[1])
        try:
            lsockids = [('Node1_s', 'Node2_s'), ('Node1_c', 'Node2_c')][self.linkmenu not in ('SO', 'DO', 'HO')]
            for ins in [ins for ins in self.inputs if ins.identifier in lsockids]:
                if ins.is_linked == True and ins.bl_idname == ins.links[0].from_socket.bl_idname:
                    for outs in self.outputs:
                        if outs.name == ins.name and outs.identifier == ins.identifier:
                            outs.hide = True
                elif ins.hide == False:
                    for outs in self.outputs:
                        if outs.name == ins.name and outs.identifier == ins.identifier:
                            outs.hide = False

            for outs in [outs for outs in self.outputs if outs.identifier in lsockids]:
                if outs.is_linked == True:
                    for ins in self.inputs:
                        if ins.name == outs.name and ins.identifier == outs.identifier:
                            ins.hide = True
                elif outs.hide == False:
                    for outs in self.outputs:
                        if ins.name == outs.name and ins.identifier == outs.identifier:
                            ins.hide = False
        except:
            pass

        for sock in self.inputs:
            if self.linkmenu == 'ELA' and sock.is_linked:
                try:
                    self.ela = triarea(bpy.data.objects[sock.links[0].from_node.zone], bpy.data.objects[sock.links[0].from_node.zone].data.polygons[int(sock.links[0].from_socket.sn)])
                except:
                    pass

    def draw_buttons(self, context, layout):
        layout.prop(self, 'linkmenu')
        newrow(layout, 'Opening factor:', self, 'wdof')
        row = layout.row()
        row.label("Control type:")
        if self.linkmenu in ('SO', 'DO', 'HO'):
            row.prop(self, 'controls')
        else:
            row.prop(self, 'controlc')
        if self.linkmenu == "SO":
            newrow(layout, 'Closed FC:', self, 'amfcc')
            newrow(layout, 'Closed FE:', self, 'amfec')
            newrow(layout, 'Density diff:', self, 'ddtw')
            newrow(layout, 'DC:', self, 'dcof')
            
        elif self.linkmenu == "DO":
            newrow(layout, 'OF Number:', self, 'noof')
            newrow(layout, 'DC1:', self, 'dcof1')
            
            row = layout.row()
            row.prop(self, 'wfof1')
            row = layout.row()
            row.prop(self, 'hfof1')
            row = layout.row()
            row.prop(self, 'sfof1')
            row = layout.row()
            row.prop(self, 'of2')
            row = layout.row()
            row.label('DC2')
            row.prop(self, 'dcof2')
            row = layout.row()
            row.prop(self, 'wfof2')
            row = layout.row()
            row.prop(self, 'hfof2')
            row = layout.row()
            row.prop(self, 'sfof2')
            if self.noof > 2:
                row = layout.row()
                row.prop(self, 'of3')
                row = layout.row()
                row.label('DC3')
                row.prop(self, 'dcof3')
                row = layout.row()
                row.prop(self, 'wfof3')
                row = layout.row()
                row.prop(self, 'hfof3')
                row = layout.row()
                row.prop(self, 'sfof3')
                if self.noof > 3:
                    row = layout.row()
                    row.prop(self, 'of4')
                    row = layout.row()
                    row.label('DC4')
                    row.prop(self, 'dcof4')
                    row = layout.row()
                    row.prop(self, 'wfof4')
                    row = layout.row()
                    row.prop(self, 'hfof4')
                    row = layout.row()
                    row.prop(self, 'sfof4')
        elif self.linkmenu == 'HO':
            newrow(layout, "Closed FC:", self, 'amfcc')
            newrow(layout, "Closed FE:", self, 'amfec')
            newrow(layout, "Slope:", self, 'spa')
            newrow(layout, "Discharge Coeff:", self, 'dcof')

            if self.linkmenu in ('SO', 'DO') and self.controls == 'Temperature':
                newrow(layout, "Minimum OF:", self, 'mvof')
                newrow(layout, "Lower OF:", self, 'lvof')
                newrow(layout, "Lower OF:", self, 'lvof')

        elif self.linkmenu == "Crack":
            newrow(layout, "Coefficient:", self, 'amfc')
            newrow(layout, "Exponent:", self, 'amfe')
            newrow(layout, "Crack factor:", self, 'cf')

        elif self.linkmenu == "ELA":
            newrow(layout, "ELA:", self, 'ela')
            newrow(layout, "Discharge Coeff:", self, 'dcof')
            newrow(layout, "PA diff:", self, 'rpd')
            newrow(layout, "FE:", self, 'amfe')

        elif self.linkmenu == "EF":
            newrow(layout, "Off FC:", self, 'amfc')
            newrow(layout, "Off FE:", self, 'amfe')

class EnViCLinkNode(bpy.types.Node, EnViNodes):
    '''Node describing an airflow component'''
    bl_idname = 'EnViCLink'
    bl_label = 'Envi Component'
    bl_icon = 'SOUND'

    def supdate(self, context):
        self.outputs['Reference'].hide = False if self.linkmenu in ('Crack', 'EF') else True

    linktype = [("Crack", "Crack", "Crack aperture used for leakage calculation"),
        ("ELA", "ELA", "Effective leakage area"),
        ("EF", "Exhaust fan", "Exhaust fan")]

    linkmenu = bpy.props.EnumProperty(name="Type", description="Linkage type", items=linktype, default='ELA', update = supdate)

    ecl = bpy.props.FloatProperty(default = 0.0, min = 0, name = '', description = 'Extra Crack Length or Height of Pivoting Axis (m)')
    dcof = bpy.props.FloatProperty(default = 0.2, min = 0, max = 1, name = '', description = 'Discharge Coefficient')
    amfc = bpy.props.FloatProperty(default = 1.0, name = "")
    amfe = bpy.props.FloatProperty(default = 0.6, name = "")
    dlen = bpy.props.FloatProperty(default = 2, name = "")
    dhyd = bpy.props.FloatProperty(default = 0.1, name = "")
    dcs = bpy.props.FloatProperty(default = 0.1, name = "")
    dsr = bpy.props.FloatProperty(default = 0.0009, name = "")
    dlc = bpy.props.FloatProperty(default = 1.0, name = "")
    dhtc = bpy.props.FloatProperty(default = 0.772, name = "")
    dmtc = bpy.props.FloatProperty(default = 0.0001, name = "")
    cf = bpy.props.FloatProperty(default = 1, min = 0, max = 1, name = "")
    ela = bpy.props.FloatProperty(default = 0.1, min = 0, max = 1, name = "")
    rpd = bpy.props.FloatProperty(default = 4, min = 0.1, max = 50, name = "")

    def init(self, context):
        self.inputs.new('EnViCAirSocket', 'Node 1')
        self.inputs.new('EnViCAirSocket', 'Node 2')
        self.outputs.new('EnViCrRefSocket', 'Reference')
        self.outputs['Reference'].hide = True
        self.outputs.new('EnViCAirSocket', 'Node 1')
        self.outputs.new('EnViCAirSocket', 'Node 2')

    def update(self):
        try:
            lsocknames = ('Node 1', 'Node 2')
            for ins in [insock for insock in self.inputs if insock.name in lsocknames]:
                self.outputs[ins.name].hide = True if ins.is_linked else False
            for outs in [outsock for outsock in self.outputs if outsock.name in lsocknames]:
                self.inputs[outs.name].hide = True if outs.is_linked else False
        except:
            pass

        for sock in self.inputs:
            if self.linkmenu == 'ELA' and sock.is_linked:
                try:
                    self.ela = triarea(bpy.data.objects[sock.links[0].from_node.zone], bpy.data.objects[sock.links[0].from_node.zone].data.polygons[int(sock.links[0].from_socket.sn)])
                except:
                    pass

    def draw_buttons(self, context, layout):
        layout.prop(self, 'linkmenu')
        if self.linkmenu == "Crack":
            newrow(layout, "Coefficient:", self, 'amfc')
            newrow(layout, "Exponent:", self, 'amfe')
            newrow(layout, "Crack factor:", self, 'cf')

        elif self.linkmenu == "ELA":
            newrow(layout, "ELA:", self, 'ela')
            newrow(layout, "Discharge Coeff:", self, 'dcof')
            newrow(layout, "PA diff:", self, 'rpd')
            newrow(layout, "FE:", self, 'amfe')

        elif self.linkmenu == "EF":
            newrow(layout, "Off FC:", self, 'amfc')
            newrow(layout, "Off FE:", self, 'amfe')

class EnViCrRef(bpy.types.Node, EnViNodes):
    '''Node describing reference crack conditions'''
    bl_idname = 'EnViCrRef'
    bl_label = 'Envi Reference Crack Node'
    bl_icon = 'SOUND'

    reft = bpy.props.FloatProperty(name = '', min = 0, max = 30, default = 20, description = 'Reference Temperature ('+u'\u00b0C)')
    refp = bpy.props.IntProperty(name = '', min = 100000, max = 105000, default = 101325, description = 'Reference Pressure (Pa)')
    refh = bpy.props.FloatProperty(name = '', min = 0, max = 10, default = 0, description = 'Reference Humidity Ratio (kgWater/kgDryAir)')

    def init(self, context):
        self.inputs.new('EnViCrRefSocket', 'Reference', type = 'CUSTOM')

    def draw_buttons(self, context, layout):
        newrow(layout, 'Temperature:', self, 'reft')
        newrow(layout, 'Pressure:', self, 'refp')
        newrow(layout, 'Humidity', self, 'refh')

class EnViFanNode(bpy.types.Node, EnViNodes):
    '''Node describing a fan component'''
    bl_idname = 'EnViFan'
    bl_label = 'Envi Fan'
    bl_icon = 'SOUND'

    fantype = [("Volume", "Constant Volume", "Constant volume flow fan component")]
    fantypeprop = bpy.props.EnumProperty(name="Type", description="Linkage type", items=fantype, default='Volume')
    fname = bpy.props.StringProperty(default = "", name = "")
    feff = bpy.props.FloatProperty(default = 0.7, name = "")
    fpr = bpy.props.FloatProperty(default = 600.0, name = "")
    fmfr = bpy.props.FloatProperty(default = 1.9, name = "")
    fmeff = bpy.props.FloatProperty(default = 0.9, name = "")
    fmaf = bpy.props.FloatProperty(default = 1.0, name = "")

    def init(self, context):
        self.inputs.new('EnViCAirSocket', 'Extract from')
        self.inputs.new('EnViCAirSocket', 'Supply to')
        self.outputs.new('NodeSocket', 'Schedule')
        self.outputs.new('EnViCAirSocket', 'Extract from')
        self.outputs.new('EnViCAirSocket', 'Supply to')

    def update(self):
        try:
            fsocknames = ('Extract from', 'Supply to')
            for ins in [insock for insock in self.inputs if insock.name in fsocknames]:
                self.outputs[ins.name].hide = True if ins.is_linked else False
            for outs in [outsock for outsock in self.outputs if outsock.name in fsocknames]:
                self.inputs[outs.name].hide = True if outs.is_linked else False
        except:
            pass

    def draw_buttons(self, context, layout):
        layout.prop(self, 'fantypeprop')
        if self.fantypeprop == "Volume":
            newrow(layout, "Name:", self, 'fname')
            newrow(layout, "Efficiency:", self, 'feff')
            newrow(layout, "Pressure Rise (Pa):", self, 'fpr')
            newrow(layout, "Max flow rate:", self, 'fmfr')
            newrow(layout, "Motor efficiency:", self, 'fmeff')
            newrow(layout, "Airstream fraction:", self, 'fmaf')

class EnViExtNode(bpy.types.Node, EnViNodes):
    '''Node describing an EnVi external node'''
    bl_idname = 'EnViExt'
    bl_label = 'Envi External Node'
    bl_icon = 'SOUND'

    height = bpy.props.FloatProperty(default = 1.0)
    azimuth = bpy.props.FloatProperty(default = 30)

    def init(self, context):
        self.inputs.new('EnViSAirSocket', 'External')
#        self.inputs.new('WPCSocket', 'WPC values')
        self.outputs.new('EnViSAirSocket', 'External')

    def draw_buttons(self, context, layout):
        layout.prop(self, 'height')

class EnViSched(bpy.types.Node, EnViNodes):
    '''Node describing a schedule'''
    bl_idname = 'EnViSched'
    bl_label = 'Schedule'
    bl_icon = 'SOUND'

    t1 = bpy.props.IntProperty(name = "", default = 365)
    f1 = bpy.props.StringProperty(name = "Fors", description = "Valid entries (space separated): AllDays, Weekdays, Weekends, Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday, AllOtherDays")
    u1 = bpy.props.StringProperty(name = "Untils", description = "Valid entries (; separated for each 'For', comma separated for each day)")
    t2 = bpy.props.IntProperty(name = "")
    f2 = bpy.props.StringProperty(name = "Fors")
    u2 = bpy.props.StringProperty(name = "Untils")
    t3 = bpy.props.IntProperty(name = "")
    f3 = bpy.props.StringProperty(name = "Fors")
    u3 = bpy.props.StringProperty(name = "Untils")
    t4 = bpy.props.IntProperty(name = "")
    f4 = bpy.props.StringProperty(name = "Fors")
    u4 = bpy.props.StringProperty(name = "Untils")

    def init(self, context):
        self.inputs.new('EnViSchedSocket', 'Schedule')

    def draw_buttons(self, context, layout):
        newrow(layout, 'End day 1:', self, 't1')
        newrow(layout, '', self, 'f1')
        newrow(layout, '', self, 'u1')
        if self.u1 != '':
            newrow(layout, 'End day 2:', self, 't2')
            newrow(layout, '', self, 'f2')
            newrow(layout, '', self, 'u2')
            if self.u2 != '':
                newrow(layout, 'End day 3:', self, 't3')
                newrow(layout, '', self, 'f3')
                newrow(layout, '', self, 'u3')
                if self.u3 != '':
                    newrow(layout, 'End day 4:', self, 't4')
                    newrow(layout, '', self, 'f4')
                    newrow(layout, '', self, 'u4')

class EnViNodeCategory(NodeCategory):
    @classmethod
    def poll(cls, context):
        return context.space_data.tree_type == 'EnViN'

envinode_categories = [
        # identifier, label, items list
        EnViNodeCategory("Control", "Control Node", items=[NodeItem("AFNCon", label="Control Node")]),
        EnViNodeCategory("ZoneNodes", "Zone Nodes", items=[NodeItem("EnViZone", label="Zone Node"), NodeItem("EnViExt", label="External Node")]),
#        EnViNodeCategory("SLinkNodes", "Surface Link Nodes", items=[
#            NodeItem("EnViSLink", label="Surface Link Node")]),
        EnViNodeCategory("CLinkNodes", "Airflow Link Nodes", items=[
            NodeItem("EnViSLink", label="Surface Link Node"), NodeItem("EnViCLink", label="Component Link Node"), NodeItem("EnViCrRef", label="Crack Reference")]),
        EnViNodeCategory("SchedNodes", "Schedule Nodes", items=[
            NodeItem("EnViSched", label="Schedule")]),
        EnViNodeCategory("PlantNodes", "Plant Nodes", items=[
            NodeItem("EnViFan", label="EnVi fan node")])]



