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
This module contains the Model class. It can use
GROMACS routines to read and write structure files. Moreover it
allows to modify structure files in various ways.

1) Rename atoms, residues, chains
2) Delete or add atoms, residues and chains

Basic Usage:
    >>> model = Model().read(args['-f'])
    where args is the dictionary returned from
    parse_common_args (see gmx module).
    The Model instance contains:
    - model.atoms       -> list of atoms
    - model.residues    -> list of residues
    - model.chains      -> list of chains
    - model.chdic       -> chain dictionary (chdic['A'] returns chain A)
    .
    .

    Some useful methods:
    - model.fetch_atoms (inherited from atomselection):
    >>> model.fetch_atoms(['CA','N','C']) returns all backbone atoms
    >>> model.fetch_atoms('C',how='byelem') returns all carbon atoms
    >>> model.fetch_atoms('H',how='byelem',inv=True) return all atoms
    except hydrogens

    - model.fetch_residues
    >>> model.fetch_residues(['ALA','TRP','CYS']) return all ALA,TRP and
    CYS residues

    - some selection examples:
    >>> rl = model.residues[:10] returns the first 10 residues
    >>> rl = model.chdic['A'].residues[-1] return the last residue
    from chain A
    >>> rl = map(lamda m: m.residues[0], model.chains)
    returns a list with the first residues of each chain
    >>> del model['A']
    remove chain A
    >>> model.write(args['-o']) write new structure file
    """
from .atomselection import *
import sys,copy
import pmx.library
#from chain import *
from . import chain
from .molecule import *
from .atom import *
import pmx._pmx as _p
XX       =  0             
YY       =  1             
ZZ       =  2


class Model(Atomselection):

    def __init__(self, filename = None, pdbline = None, renumber_atoms=True,
                 renumber_residues = True, **kwargs):
        
        Atomselection.__init__(self)
        self.title = 'PMX MODEL'
        self.chains = []
        self.chdic = {}
        self.residues = []
        self.name = None
        self.id = 0
#        self.top=None
        self.have_bonds=0
        self.box = [ [0,0,0], [0,0,0], [0,0,0] ]
        self.unity = 'A'
        for key, val in list(kwargs.items()):
            setattr(self,key,val)

        if filename is not None:
            self.read(filename)
        if pdbline is not None:
            self.__readPDB(pdbline = pdbline)
        if self.atoms:
            self.unity = self.atoms[0].unity
            self.make_chains()
            self.make_residues()
        if self.residues and not self.atoms:
            self.al_from_resl()
            self.make_chains()
            self.make_residues()
        if self.chains and not self.residues:
            self.resl_from_chains()
            self.al_from_resl()
            self.make_chains()
            self.make_residues()
        if self.chdic and not self.chains:
            for key, val in list(self.chdic.items()):
                self.chains.append(val)
            if not self.atoms and not self.residues:
                self.resl_from_chains()
                self.al_from_resl()
        if renumber_atoms:
            self.renumber_atoms()
        if renumber_residues:
            self.renumber_residues()

    def __add__(first_model, second_model):
        new_model = Model()
        for attribute in ('title', 'name', 'id', 'have_bonds', 'box', 'unity',):
            # Get those attributes from first_model ONLY
            setattr(
                new_model,
                attribute,
                getattr(first_model, attribute),
            )
        for attribute in ('chains', 'residues', 'atoms',):
            # Concatenate those list attributes
            setattr(
                new_model,
                attribute,
                (getattr(first_model, attribute) + getattr(second_model, attribute)),
            )
        for attribute in ('chdic',):
            # Concatenate those dict attributes
            setattr(
                new_model,
                attribute,
                dict(list(getattr(first_model, attribute).items()) + list(getattr(second_model, attribute).items())),
            )

        new_model.renumber_atoms()
        new_model.renumber_residues()

        return new_model

    def __str__(self):
        s = '< Model: nchain = %d nres = %d natom = %d >' %\
            (len(self.chains), len(self.residues), len(self.atoms))
        return s
        

##     def writePDB(self,fname,title="",nr=1):

##         fp = open(fname,'w')
##         if not title:
##             title = self.title
##         header = 'TITLE    '+title
##         print >>fp, header
##         print >>fp, 'MODEL%5d' % nr
##         if self.box[XX][XX]*self.box[YY][YY]*self.box[ZZ][ZZ] != 0:
##             box_line = _p.box_as_cryst1( self.box )
##             print >>fp, box_line
##         for atom in self.atoms:
##             print >>fp, atom
##         print >>fp, 'ENDMDL'
##         fp.close()

    def writePIR( self, filename, title=""):
        fp = open(filename,"w")
        if not title: title = '_'.join(self.title.split())
        print('>P1;%s' % title, file=fp)
        print('sequence:::::::::', file=fp)
        for i in range( len(self.chains) - 1):
            print(self.chains[i].get_sequence()+'/', file=fp)
        print(self.chains[-1].get_sequence()+'*', file=fp)
        fp.close()

    def writeFASTA( self, filename, title = ""):
        fp = open(filename,"w")
        if not title: title = '_'.join(self.title.split())
        if len(self.chains) == 1:
            print('> %s' % title, file=fp)
            print(self.chains[0].get_sequence(), file=fp)
        else:
            for chain in self.chains:
                print('> %s_chain_%s' % (title, chain.id ), file=fp)
                print(chain.get_sequence(), file=fp)
                
    

##     def writeGRO( self, filename, title = ''):
##         fp = open(filename,'w')
##         if self.unity == 'nm': fac = 1.
##         else: fac = 0.1
##         if not title:
##             title = self.title
##         print >>fp, title
##         print >>fp, "%5d" % len(self.atoms)
##         if self.atoms[0].v[0] != 0.000 : bVel = True
##         else: bVel = False
##         if bVel:
##             gro_format = "%8.3f%8.3f%8.3f%8.4f%8.4f%8.4f"
##         else:
##             gro_format = "%8.3f%8.3f%8.3f"
##         for atom in self.atoms:
##             resid = (atom.resnr)%100000
##             at_id = (atom.id)%100000
##             ff = "%5d%-5.5s%5.5s%5d" % (resid, atom.resname, atom.name, at_id)
##             if bVel:
##                 ff+=gro_format % (atom.x[XX]*fac, atom.x[YY]*fac, atom.x[ZZ]*fac,
##                                   atom.v[XX], atom.v[YY], atom.v[ZZ])
##             else:
##                 ff+=gro_format % (atom.x[XX]*fac, atom.x[YY]*fac, atom.x[ZZ]*fac )
##             print >>fp, ff
            
##         if self.box[XX][YY] or self.box[XX][ZZ] or self.box[YY][XX] or \
##                self.box[YY][ZZ] or self.box[ZZ][XX] or self.box[ZZ][YY]:
##             bTric = False
##             ff = "%10.5f%10.5f%10.5f%10.5f%10.5f%10.5f%10.5f%10.5f%10.5f"
##         else:
##             bTric = True
##             ff = "%10.5f%10.5f%10.5f"
##         if bTric:
##             print >>fp, ff % (self.box[XX][XX],self.box[YY][YY],self.box[ZZ][ZZ])
##         else:
##             print >>fp, ff % (self.box[XX][XX],self.box[YY][YY],self.box[ZZ][ZZ],
##                               self.box[XX][YY],self.box[XX][ZZ],self.box[YY][XX],
##                               self.box[YY][ZZ],self.box[ZZ][XX],self.box[ZZ][YY])
##         fp.close()


    def write(self,fn, title = '', nr = 1, write_by_residue=False):
        ext = fn.split('.')[-1]
        if ext == 'pdb':
            self.writePDB( fn, title, nr, write_by_residue=write_by_residue)
        elif ext == 'gro':
            self.writeGRO( fn, title, write_by_residue=write_by_residue)
        elif ext == 'pir':
            self.writePIR( fn, title )
        elif ext == 'fasta':
            self.writeFASTA( fn, title )
        else:
            print('pmx_Error_> Can only write pdb or gro!', file=sys.stderr)
            sys.exit(1)



    def make_chains(self):
        self.chains = []
        self.chdic = {}
        cur_chain = None
        ch = None
        for atom in self.atoms:
            if atom.chain_id == cur_chain:
                if ch:
                    atom.chain = ch
                    ch.atoms.append(atom)
                else:
                    ch = chain.Chain()
                    cur_chain = atom.chain_id
                    ch.id = atom.chain_id
                    atom.chain = ch
                    ch.atoms.append(atom)
            else:
                if ch:
                    self.chains.append(ch)
                    ch = chain.Chain()
                    cur_chain = atom.chain_id
                    ch.id = cur_chain
                    atom.chain = ch
                    ch.atoms.append(atom)
                else:
                    ch = chain.Chain()
                    cur_chain = atom.chain_id
                    ch.id = atom.chain_id
                    atom.chain = ch
                    ch.atoms.append(atom)
        
        self.chains.append(ch)
        for ch in self.chains:
            ch.model = self
            idx = ch.id
            self.chdic[idx] = ch
            
    def make_residues(self):
        self.residues = []
        for ch in self.chains:
            cur_mol = None
            mol = None
            for atom in ch.atoms:
                if atom.resnr == cur_mol:
                    if mol:
                        mol.atoms.append(atom)
                    else:
                        mol = Molecule()
                        cur_mol = atom.resnr
                        mol.resname = atom.resname
                        mol.id = cur_mol
                        mol.atoms.append(atom)
                else:
                    if mol:
                        mol.model = self
                        mol.chain = ch
                        ch.residues.append(mol)
                        self.residues.append(mol)
                        mol = Molecule()
                        cur_mol = atom.resnr
                        mol.resname = atom.resname
                        mol.id = cur_mol
                        mol.atoms.append(atom)
                    else:
                        mol = Molecule()
                        cur_mol = atom.resnr
                        mol.resname = atom.resname
                        mol.id = cur_mol
                        mol.atoms.append(atom)
            self.residues.append(mol)
            ch.residues.append(mol)
        for r in self.residues:
            for atom in r.atoms:
                atom.molecule = r
                atom.model = self
                r.model = self
        for ch in self.chains:
            for r in ch.residues:
                r.chain = ch
                r.chain_id = ch.id
                
    def __readPDB(self,fname=None, pdbline=None):
        if pdbline:
            l = pdbline.split('\n')
        else:
            with open(fname,'r') as fh:
                l = fh.readlines()
        for line in l:
            if line[:4]=='ATOM' or \
               line[:6]=='HETATM':
                a = Atom().readPDBString(line)
                self.atoms.append(a)
            if line[:6] == 'CRYST1':
                self.box = [
                    [x * 10. for x in v]
                    for v in _p.box_from_cryst1(line)
                ]
        self.make_chains()
        self.make_residues()
        self.unity = 'A'
        return self
    
    
    def __readGRO(self, filename):
        with open(filename) as fh:
            l = fh.readlines()
        # first line is name/comment
        name = l[0].rstrip()
        self.title = name
        # next line is number of atoms
        natoms = int(l[1])
        atoms_parsed = 0
        al = []
        while atoms_parsed != natoms:
            line = l[atoms_parsed+2]
            resid = int(line[:5])
            resname = line[5:9].strip()
            name = line[10:15].strip()
            idx = int(line[15:20])
            rest = line[20:].split()
            if len(rest) in [3, 6]:
                try:
                    coords, vel = self.parse_x_v(rest)
                except:
                    # fall back to fixed-width based parsing format
                    coords, vel = self.problematic_grofile_parsing(line)
            else:
                # fall back to fixed-width based parsing format
                coords, vel = self.problematic_grofile_parsing(line)

            a = Atom( id =idx, name = name, resname = resname,
                      resnr = resid, x = coords, v = vel, unity = 'nm')
            a.get_symbol()
            self.atoms.append( a )
            atoms_parsed += 1
        box_line = [float(x) for x in l[-1].split()]
        assert len(box_line) in [3,9]
        box = [ [0,0,0], [0,0,0], [0,0,0] ]
        box[XX][XX] = box_line[0]
        box[YY][YY] = box_line[1]
        box[ZZ][ZZ] = box_line[2]
        if len(box_line) == 3:
            box[XX][YY] = 0
            box[XX][ZZ] = 0
            box[YY][XX] = 0
            box[YY][ZZ] = 0
            box[ZZ][XX] = 0
            box[ZZ][YY] = 0
        else:
            box[XX][YY] = box_line[3]
            box[XX][ZZ] = box_line[4]
            box[YY][XX] = box_line[5]
            box[YY][ZZ] = box_line[6]
            box[ZZ][XX] = box_line[7]
            box[ZZ][YY] = box_line[8]
        self.box = box
        self.make_chains()
        self.make_residues()
        self.unity = 'nm'
        return self

    def parse_x_v(self, x_v):
        x = float(x_v[0])
        y = float(x_v[1])
        z = float(x_v[2])
        coords = [x, y, z]
        if len(x_v) == 6:
            vx = float(x_v[3])
            vy = float(x_v[4])
            vz = float(x_v[5])
            vel = [vx, vy, vz]
        else:
            vel = [0, 0, 0]
        return coords, vel

    def problematic_grofile_parsing(self, line):
        # First attempt to split columns on - character
        x_y_cols = line[20:].replace("-", " -").split()
        # Use .4f formatting to extract columns
        split_x_y_cols = []
        for col in x_y_cols:
            if col.count(".") < 2:
                split_x_y_cols.append(col)
            else:
                column_delimiter_indexes = [0] + [i + 4 for i, c in enumerate(col) if c == "."]
                for j in range(len(column_delimiter_indexes)-1):
                    split_x_y_cols.append(col[column_delimiter_indexes[j]:column_delimiter_indexes[j+1]])
        assert len(split_x_y_cols) in [3, 6], split_x_y_cols
        coords, vel = self.parse_x_v(split_x_y_cols)
        print(f"WARNING: unexpected column format in GRO file: {line} (coords={coords}, vel={vel})")
        return coords, vel

    def updateGRO(self, filename):
        with open(filename) as fh:
            l = fh.readlines()
        # first line is name/comment
        name = l[0].rstrip()
        self.title = name
        # next line is number of atoms
        natoms = int(l[1])
        atoms_parsed = 0
        al = []
        while atoms_parsed != natoms:
            line = l[atoms_parsed+2]
            rest = line[20:].split()
            if len(rest) in [3, 6]:
                try:
                    coords, vel = self.parse_x_v(rest)
                except:
                    # use .4f based parsing
                    coords, vel = self.problematic_grofile_parsing(line)
            else:
                # use .4f based parsing
                coords, vel = self.problematic_grofile_parsing(line)
            self.atoms[atoms_parsed].x = coords
            self.atoms[atoms_parsed].v = vel
            atoms_parsed += 1
        box_line = [float(x) for x in l[-1].split()]
        assert len(box_line) in [3,9]
        box = [ [0,0,0], [0,0,0], [0,0,0] ]
        box[XX][XX] = box_line[0]
        box[YY][YY] = box_line[1]
        box[ZZ][ZZ] = box_line[2]
        if len(box_line) == 3:
            box[XX][YY] = 0
            box[XX][ZZ] = 0
            box[YY][XX] = 0
            box[YY][ZZ] = 0
            box[ZZ][XX] = 0
            box[ZZ][YY] = 0
        else:
            box[XX][YY] = box_line[3]
            box[XX][ZZ] = box_line[4]
            box[YY][XX] = box_line[5]
            box[YY][ZZ] = box_line[6]
            box[ZZ][XX] = box_line[7]
            box[ZZ][YY] = box_line[8]
        self.box = box
        return

    def read(self, filename ):
        ext = filename.split('.')[-1]
        if ext == 'pdb':
            return self.__readPDB( filename )
        elif ext == 'gro':
            return self.__readGRO( filename )
        else:
            print('ERROR: Can only read pdb or gro!', file=sys.stderr)
            sys.exit(1)

    def renumber_residues(self):
        for i, res in enumerate(self.residues):
            res.set_orig_resid( res.id )
            res.set_resid(i+1)
            

    def remove_atom(self,atom):
        m = atom.molecule
        m.remove_atom(atom)

    def remove_residue(self,residue):
        ch = residue.chain
        ch.remove_residue(residue)

    def remove_chain(self,key):
        if key not in self.chdic:
            print('No chain %s to remove....' % key)
            print('No changes applied.')
            return
        for ch in self.chains:
            if ch.id == key:
                idx = self.chains.index(ch)
                del self.chains[idx]
                del self.chdic[key]
        self.resl_from_chains()
        self.al_from_resl()
        self.renumber_residues()
        self.renumber_atoms()
        

    def __delitem__(self,key):
        self.remove_chain(key)
    
##     def insert_sequence(self,pos,new_chain,chain_id):
##         """insert a sequence"""
##         ch = self.chdic[chain_id]
##         ch.insert_chain(pos,new_chain)
        

    def insert_residue(self,pos,res,chain_id):
        ch = self.chdic[chain_id]
        ch.insert_residue(pos,res)

    def replace_residue(self,residue,new):
        ch = residue.chain
        ch.replace_residue(residue,new)
        
    def insert_chain(self,pos,new_chain):
        if new_chain.id in self.chdic:
            print('Chain identifier %s already in use!' % new_chain.id)
            print('Changing chain identifier to 0')
            new_chain.set_chain_id('0')
        self.chains.insert(pos,new_chain)
        self.resl_from_chains()
        self.al_from_resl()
        self.make_chains()
        self.make_residues()
        self.renumber_atoms()
        self.renumber_residues()
        

    def append(self,new_chain):
        """ we assume chain is a Chain"""
        idx = len(self.chains)
        self.insert_chain(idx,new_chain)
        
    
    def fetch_residues(self,key, inv=False):
        if not hasattr(key,"append"):
            key = [key]
        result = []
        if not inv:
            for r in self.residues:
                if r.resname in key:
                    result.append(r)
        else:
            for r in self.residues:
                if r.resname not in key:
                    result.append(r)
        return result
    

    def al_from_resl(self):
        self.atoms = []
        for r in self.residues:
            for atom in r.atoms:
                self.atoms.append(atom)
                

    def resl_from_chains(self):
        self.residues = []
        for ch in self.chains:
            for r in ch.residues:
                self.residues.append(r)
                
    def copy(self):
        return copy.deepcopy(self)


        
##     def get_bonded(self):
##         for ch in self.chains:
##             ch.get_bonded()
##         cysl = self.fetch_residues('CYS')
##         for i, cys1 in enumerate(cysl[:-1]):
##             for j, cys2 in enumerate(cysl[i+1:]):
##                 sg1 = cys1.fetch('SG')[0]
##                 sg2 = cys2.fetch('SG')[0]
##                 d= sg1-sg2
##                 if self.unity=='A':
##                     d*=.1
##                 if d < 0.25:
##                     sg1.bonds.append(sg2)
##                     sg2.bonds.append(sg1)

##     def get_b13(self):
##         for atom in self.atoms:
##             for at2 in atom.bonds:
##                 for at3 in at2.bonds:
##                     if atom.id > at3.id:
##                         atom.b13.append(at3)
##                         at3.b13.append(atom)

##     def get_b14(self):
##         for atom in self.atoms:
##             for at2 in atom.b13:
##                 for at3 in at2.bonds:
##                     if atom.id > at3.id and at3 not in \
##                            atom.bonds+atom.b13:
##                         atom.b14.append(at3)
##                         at3.b14.append(atom)


                    
##     def get_connections(self,cutoff=.8):
##         if self.atoms[0].symbol == '':
##             self.get_symbol()
##         self.get_bonded()
##         self.get_b13()
##         self.get_b14()
##         self.get_nlist(cutoff)


##     def update(self,frame,trj='xtc'):
##         """ update the coordinates in a model
##         from trajectory data"""
##         if trj=='xtc':
##             nat = len(self.atoms)
##             if nat != frame['natoms']:
##                 print 'Error: Number of atoms in trajectory\n \
##                 doesn\'t match topology\n'
##                 sys.exit(1)
                
##             for i in range(nat):
##                 self.atoms[i].x=frame['x'][i]
##             self.box = frame['box']
        
    def get_mol2_types(self):
        if self.atoms[0].symbol == '':
            self.get_symbol()
        for ch in self.chains:
            ch.get_mol2_types()
            

    def get_mol2_resname(self):
        for ch in self.chains:
            ch.get_mol2_resname()
            
    def get_nterms(self):
        nter = []
        for ch in model.chains:
            first = ch.residues[0]      # first residue
            if first.resname in list(library._one_letter.keys()):
                nter.append(first)
        return nter

    def get_cterms(self):
        cter = []
        for ch in model.chains:
            last = ch.residues[-1]      # last residue
            if last.resname in list(library._one_letter.keys()):
                cter.append(last)
        return last

    def rename_atoms(self):
        for c in self.chains:
            c.rename_atoms()

    def residue(self, idx):
        return self.residues[idx-1]

    def chain(self, iden):
        return self.chdic[iden] 
    




    


