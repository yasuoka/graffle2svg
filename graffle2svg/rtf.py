#!/usr/bin/env python3
#Copyright (c) 2009, Tim Wintle
#Copyright (c) 2015, Tim Wintle, Stephane Galland
#All rights reserved.
#
#Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:
#
#    * Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
#    * Neither the name of the project nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

#THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import re

from .styles import CascadingStyles

def isint(i):
    try:
        int(i)
        return True
    except:
        return False

def extractRTFString(s):
    """Extract a string and some styling info"""
    bracket_depth = 0
    instruction = False
    inst_code = ""

    ftable = FontTable()
    colortable = ColorTable()
    # The string being generated:
    std_string = ""
    style = CascadingStyles()
    # Want to set these as defaults even if not specified
    style.appendScope()
    """TODO: 
     extract styling 
     
     e.g. 
     {\rtf1\ansi\ansicpg1252\cocoartf949\cocoasubrtf460
{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
\pard\tx560\tx1120\tx1680\tx2240\tx2800\tx3360\tx3920\tx4480\tx5040\tx5600\tx6160\tx6720\ql\qnatural\pardirnatural

\f0\fs28 \cf0 Next ads are represented in a book-ended carousel on end screen}
    """

    def do_instruction(inst_code, i, std_string):
        if inst_code == "b":
            style["font-weight"] = "bold"
        if inst_code == "ql":
            style["text-align"] = "left"
        elif inst_code == "qr":
            style["text-align"] = "right"
        elif inst_code == "qj":
            style["text-align"] = "justify"
        elif inst_code == "qc":
            style["text-align"] = "center"
        elif inst_code == "fonttbl":
            i = ftable.parseTable(s,i)
        elif inst_code == "colortbl":
            i = colortable.parseTable(s, i)
        elif inst_code[0]=="f" and inst_code[1:].isdigit():
            # Font looked up in font table
            font = ftable.fonts.get(int(inst_code[1:]),{})
            for k,v in font.items():
                if k != "":
                    style[k] = v
        elif inst_code[:2]=="fs" and isint(inst_code[2:]):
            # font size - RTF specifies half pt sizes
            style["font-size"] = "%.1fpx"%(float(inst_code[2:])/2.0)
        elif inst_code[:2]=="cf" and isint(inst_code[2:]):
            # font colour is enytry int(inst_code[2:]) in the colour table
            style["fill"] = "#" + colortable[int(inst_code[2:])]
            style["stroke"] = "#" + colortable[int(inst_code[2:])]
        elif inst_code[0] == "u" and isint(inst_code[1:]):
            std_string += chr(int(inst_code[1:]))
        return i,  std_string
    i = -1
    result_lines =[]
    while i < len(s)-1:
        i += 1
        c = s[i]
        if c == "{":
            bracket_depth +=1
            style.appendScope()
        elif c == "}":
            if len(inst_code) > 0:
                i,  std_string = do_instruction(inst_code, i,  std_string)
                instruction=False
                inst_code=""
            if std_string != "":
                result_lines.append({"string":std_string, "style":style.currentStyle()})
                std_string = ""
            style.popScope()
            bracket_depth -=1
        elif c == "\\":
            if len(inst_code) > 0:
                i, std_string = do_instruction(inst_code, i,  std_string)
            instruction = True
            inst_code = ""
        
        if instruction:
            if c == " ":
                instruction = False
                i, std_string = do_instruction(inst_code, i,  std_string)
                inst_code=""
            elif c == "\n":
                instruction = False
                if inst_code == "":
                    result_lines.append({"string":std_string, "style":style.currentStyle()})
                    std_string = ""
                else:
                    i, std_string = do_instruction(inst_code, i,  std_string)
                    inst_code=""
            elif not c  in "\\;":
                inst_code += c

        else:
            if bracket_depth == 1:
                if not c in "{}\\\n\r":
                    # those characters are escaped
                    std_string += c
    style.popScope()
    return result_lines

class FontTable(object):
    def __init__(self):
        self.fonts = {}
        # For parsing
        self.varname = ""
        self.fontnum = 0

    def parseTable(self, defn, startidx):
        #{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
        i = startidx
        in_name = False
        tkn_string = ""
        fontnum = ""
        tkn_name = ""

        def process_string():
            if tkn_name == "fcharset":
                font_opns = self.fonts.get(fontnum,{})
                existing_font = font_opns.get("font-family","")
                if existing_font != "":
                    existing_font = ","+existing_font
                font_opns["font-family"] = tkn_string + existing_font
                self.fonts[fontnum] = font_opns

            if tkn_name == "fswiss":
                font_opns = self.fonts.get(fontnum,{})
                font_opns["font-family"] = "Sans-serif"
                self.fonts[fontnum] = font_opns

            if tkn_name == "froman":
                 font_opns = self.fonts.get(fontnum,{})
                 font_opns["font-family"] = "Serif"
                 self.fonts[fontnum] = font_opns
        
        while i < len(defn):
            c = defn[i]
            if c == "}":
                if in_name:
                    tkn_name = tkn_string
                    tkn_string = ""
                if len(tkn_string)>1 and tkn_string[-1]==";":
                    tkn_string = tkn_string[:-1]
                process_string()
                break
            elif c == "{":
                pass
            elif c == "\\":
                if in_name:
                    tkn_name = tkn_string
                    tkn_string = ""
                process_string()
                in_name = True
                tkn_string = ""
                tkn_name = ""
            elif c.isdigit():
                if tkn_string == "f":
                    fontnum = int(str(fontnum) + c)
                    tkn_name = tkn_string
                    tkn_string = ""
                    in_name = False
                if not in_name:
                    tkn_string = tkn_string + c
            elif c == " ":
                if in_name:
                    in_name = False
                    tkn_name = tkn_string
                    tkn_string = ""
                else:
                    tkn_string = tkn_string + c
            else:
                tkn_string = tkn_string + c
            i += 1

        return i-1

class ColorTable(object):
    """ Create a table of colors from a RTF definition in the form of {\colortbl;\red255\green255\blue255;\red75\green75\blue75;}"""
    def __init__(self):
        self.color = []
    
    def parseTable(self,defn, startidx ):
        endidx = defn.find("}", startidx)
        primitive_reg = re.compile(r"(\D+)(\d+)")
        for colordef in defn[startidx-1:endidx-1].split(";"):
            color = {'red':0, 'green':0, 'blue':0}
            for primitivedef in colordef.split('\\'):
                 primitive_match = primitive_reg.match(primitivedef)
                 if primitive_match is not None:
                    primitive, value = primitive_match.groups()
                    color[primitive] = int(value)
            self.color.append("%02x"%color['red'] + "%02x"%color['green'] + "%02x"%color['blue'])
        return endidx-1 

    def __getitem__(self, key):
        return self.color[key]
