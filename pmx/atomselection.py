# pmx  Copyright Notice
# ============================
#
# The pmx source code is copyrighted, but you can freely use and
# copy it as long as you don't change or remove any of the copyright
# notices.
#
# ----------------------------------------------------------------------
# pmx is Copyright (C) 2006-2013 by Daniel Seeliger
#
#                        All Rights Reserved
#
# Permission to use, copy, modify, distribute, and distribute modified
# versions of this software and its documentation for any purpose and
# without fee is hereby granted, provided that the above copyright
# notice appear in all copies and that both the copyright notice and
# this permission notice appear in supporting documentation, and that
# the name of Daniel Seeliger not be used in advertising or publicity
# pertaining to distribution of the software without specific, written
# prior permission.
#
# DANIEL SEELIGER DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS
# SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND
# FITNESS.  IN NO EVENT SHALL DANIEL SEELIGER BE LIABLE FOR ANY
# SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER
# RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF
# CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN
# CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
# ----------------------------------------------------------------------
__doc__="""
This module contains the Atomselection class. It contains methods
that are inherited to the Molecule, Chain and Model classes.
Take a look there for details...


"""
import sys
from numpy import *
import random
from .atom import *
from .geometry import Rotation
from . import library
import copy as cp
import pmx._pmx
#import _gridns

XX = 0
YY = 1
ZZ = 2


class Atomselection:
    """ Basic class to handle sets of atoms. Atoms are stored
    in a list <atoms>"""
    
    def __init__(self, **kwargs):
        self.atoms = []
        self.unity = 'A'
        for key, val in list(kwargs.items()):
            setattr(self,key,val)

    def writePDB(self,fname,title="",nr=1, write_by_residue=False):

        fp = open(fname,'w')
        if not title:
            if hasattr(self,"title"):
                title = self.title
            else:
                title = str(self.__class__)+' '+str(self)

        header = 'TITLE    '+title
        print(header, file=fp)
        print('MODEL%5d' % nr, file=fp)
        if not hasattr(self,"box"):
            self.box = [ [0,0,0], [0,0,0], [0,0,0] ]
        if self.box[XX][XX]*self.box[YY][YY]*self.box[ZZ][ZZ] != 0:
            box_line = _pmx.box_as_cryst1( self.box )
            print(box_line, file=fp)
        if not write_by_residue:
            for atom in self.atoms:
                if( len(atom.name) > 4): # too long atom name
                    foo = cp.deepcopy(atom)
                    foo.name = foo.name[:4]
                    print(foo, file=fp)
                else:
                    print(atom, file=fp)
        else:
            residue_id, atom_id = 0, 0
            for residue in self.residues:
                residue_id = (residue_id + 1) % 100000
                for atom in residue.atoms:
                    atom_id = (atom_id + 1) % 100000
                    atom.resnr, atom.id = residue_id, atom_id
                    if( len(atom.name) > 4): # too long atom name
                        foo = cp.deepcopy(atom)
                        foo.name = foo.name[:4]
                        print(foo, file=fp)
                    else:
                        print(atom, file=fp)
        print('ENDMDL', file=fp)
        fp.close()


    def writeGRO( self, filename, title = '', write_by_residue=False):
        fp = open(filename,'w')
        if self.unity == 'nm': fac = 1.
        else: fac = 0.1
        if not title:
            if hasattr(self,"title"):
                title = self.title
            else:
                title = str(self.__class__)+' '+str(self)
        print(title, file=fp)
        if not write_by_residue:
          print("%5d" % len(self.atoms), file=fp)
        else:
          print("%5d" % sum([len(residue.atoms) for residue in self.residues]), file=fp)
        gro_format = "%8.3f%8.3f%8.3f%8.4f%8.4f%8.4f"
        if not write_by_residue:
            for atom in self.atoms:
                resid = (atom.resnr)%100000
                at_id = (atom.id)%100000
                ff = "%5d%-5.5s%5.5s%5d" % (resid, atom.resname, atom.name, at_id)
                ff+=gro_format % (atom.x[XX]*fac, atom.x[YY]*fac, atom.x[ZZ]*fac,
                                      atom.v[XX], atom.v[YY], atom.v[ZZ])
                print(ff, file=fp)
        else:
            residue_id, atom_id = 0, 0
            for residue in self.residues:
                residue_id = (residue_id + 1) % 100000
                for atom in residue.atoms:
                    atom_id = (atom_id + 1) % 100000
                    ff = "%5d%-5.5s%5.5s%5d" % (residue_id, atom.resname, atom.name, atom_id)
                    ff+=gro_format % (atom.x[XX]*fac, atom.x[YY]*fac, atom.x[ZZ]*fac,
                                          atom.v[XX], atom.v[YY], atom.v[ZZ])
                    print(ff, file=fp)

        if not hasattr(self,"box"):
            self.box = [ [0,0,0], [0,0,0], [0,0,0] ]
        if self.box[XX][YY] or self.box[XX][ZZ] or self.box[YY][XX] or \
               self.box[YY][ZZ] or self.box[ZZ][XX] or self.box[ZZ][YY]:
            bTric = False
            ff = "%10.5f%10.5f%10.5f%10.5f%10.5f%10.5f%10.5f%10.5f%10.5f"
        else:
            bTric = True
            ff = "%10.5f%10.5f%10.5f"
        if bTric:
            print(ff % (self.box[XX][XX]*fac, self.box[YY][YY]*fac, self.box[ZZ][ZZ]*fac), file=fp)
        else:
            print(ff % (self.box[XX][XX]*fac, self.box[YY][YY]*fac, self.box[ZZ][ZZ]*fac,
                              self.box[XX][YY]*fac, self.box[XX][ZZ]*fac, self.box[YY][XX]*fac,
                              self.box[YY][ZZ]*fac, self.box[ZZ][XX]*fac, self.box[ZZ][YY]*fac), file=fp)
        fp.close()

    def write(self,fn, title = '', nr = 1):
        ext = fn.split('.')[-1]
        if ext == 'pdb':
            self.writePDB( fn, title, nr )
        elif ext == 'gro':
            self.writeGRO( fn, title )
        else:
            print('pmx_Error_> Can only write pdb or gro!', file=sys.stderr)
            sys.exit(1)


            
    def com(self,vector_only=False):
        """move atoms to center of mass or return vector only"""
        M = sum([a.m for a in self.atoms])
        if M == 0:
            # Zero total mass, so treat all atoms as having equal mass
            x = sum([a.x[0] for a in self.atoms])
            y = sum([a.x[1] for a in self.atoms])
            z = sum([a.x[2] for a in self.atoms])
        else:
            x = sum([a.x[0]*a.m for a in self.atoms]) / M
            y = sum([a.x[1]*a.m for a in self.atoms]) / M
            z = sum([a.x[2]*a.m for a in self.atoms]) / M
        if vector_only:
            return [x,y,z]
        else:
            for atom in self.atoms:
                atom.x[0]-=x
                atom.x[1]-=y
                atom.x[2]-=z
        


    def atomlistFromTop(self,topDic):
        """ return a list of atom objects
        found in topDic"""
        self.atoms=[]
        for idx in list(topDic['atoms'].keys()):
            at=Atom().atomFromTop(topDic,idx)
            self.atoms.append(at)
        return self


    def renumber_atoms(self, start=1):
        for i, atom in enumerate(self.atoms):
            if not hasattr(atom,"orig_id") or atom.orig_id == 0: atom.orig_id = atom.id
            atom.id = i+1

    def a2nm(self):
        if self.unity == 'nm':
            return
        for atom in self.atoms:
            atom.x[0]*=.1
            atom.x[1]*=.1
            atom.x[2]*=.1
            atom.unity = 'nm'
        self.unity = 'nm'

        if hasattr(self, 'box'):
            self.box = [
                [x * 0.1 for x in v]
                for v in self.box
            ]
        
    def nm2a(self):
        if self.unity == 'A':
            return
        for atom in self.atoms:
            atom.x[0]*=10.
            atom.x[1]*=10.
            atom.x[2]*=10.
            atom.unity = 'A'
        self.unity = 'A'

        if hasattr(self, 'box'):
            self.box = [
                [x * 10. for x in v]
                for v in self.box
            ]
        
    def get_long_name(self):
        for atom in self.atoms:
            atom.make_long_name()
            
    def get_symbol(self):
        for atom in self.atoms:
            atom.get_symbol()

    def get_order(self):
        for atom in self.atoms:
            atom.get_order()


    def max_crd(self):
        x = [a.x[0] for a in self.atoms]
        y = [a.x[1] for a in self.atoms]
        z = [a.x[2] for a in self.atoms]
        return (min(x),max(x)),(min(y),max(y)),(min(z),max(z))

    def search_neighbors(self, cutoff = 8., build_bonds = True ):
        changed = False
        if self.unity == 'nm':
            changed = True
            self.nm2a()
        _pmx.search_neighbors(self.atoms, cutoff, build_bonds )
    
    

    def coords(self):
        return [a.x for a in self.atoms]


    def fetch_atoms(self,key,how='byname',wildcard=False,inv=False):
        result = []
        if not hasattr(key,"append"):
            key = [key]
        if how == 'byname':
            for atom in self.atoms:
                for k in key:
                    if wildcard:
                        if k in atom.name:
                            result.append(atom)
                    else:
                        if atom.name == k:
                            result.append(atom)
        elif how == 'byelem':
            for atom in self.atoms:
                for k in key:
                    if atom.symbol == k:
                        result.append(atom)
        elif how == 'byid':
            for atom in self.atoms:
                for k in key:
                    if atom.id == int(k):
                        result.append(atom)
        if inv:
            r = []
            for atom in self.atoms:
                if atom not in result:
                    r.append(atom)
            return r
        else:
            return result



    def get_b13(self):
        for atom in self.atoms:
            for at2 in atom.bonds:
                for at3 in at2.bonds:
                    if atom.id > at3.id:
                        atom.b13.append(at3)
                        at3.b13.append(atom)

    def get_b14(self):
        for atom in self.atoms:
            for at2 in atom.b13:
                for at3 in at2.bonds:
                    if atom.id > at3.id and at3 not in \
                           atom.bonds+atom.b13:
                        atom.b14.append(at3)
                        at3.b14.append(atom)


    def translate(self, vec):
        for atom in self.atoms:
            atom.x[0]+=vec[0]
            atom.x[1]+=vec[1]
            atom.x[2]+=vec[2]
            

    def random_rotation(self):
        vec = self.com(vector_only = True)
        self.com()
        r = Rotation([0,0,0],[1,0,0])  # x-rot
        phi = random.uniform(0.,360.)
        for atom in self.atoms:
            atom.x = r.apply(atom.x,phi)
        r = Rotation([0,0,0],[0,1,0])  # y-rot
        phi = random.uniform(0.,360.)
        for atom in self.atoms:
            atom.x = r.apply(atom.x,phi)
        r = Rotation([0,0,0],[0,0,1])  # z-rot
        phi = random.uniform(0.,360.)
        for atom in self.atoms:
            atom.x = r.apply(atom.x,phi)
        for atom in self.atoms:
            atom.x[0]+=vec[0]
            atom.x[1]+=vec[1]
            atom.x[2]+=vec[2]

    def make_mol2_bondlist(self):
        lst = []
        bt = library._mol2_bondtypes
        for atom in self.atoms:
            for at in atom.bonds:
                if atom.id > at.id:
                    lst.append([atom, at])
        newl = []
        for at1, at2 in lst:
            check = False
            for t1, t2, tp in bt:
                if (at1.atype == t1 and at2.atype == t2) or \
                   (at1.atype == t2 and at2.atype == t1):
                    newl.append((at1,at2,tp))
                    check = True
            if not check:
                print('bondtype %s-%s defaults to 1' % (at1.atype, at2.atype))
                newl.append((at1,at2,'1'))
        self.bondlist = newl
                                
    def get_by_id(self, lst):
        atlst = []
        for idx in lst:
            atlst.append(self.atoms[idx-1])
        return atlst
    
            


