from collections import namedtuple
import pprint
from asm3.proxy import ProxyType, PropertyInfo
from asm3.system import System, SystemBase, SystemExtension
from asm3.utils import syslogger as logger, objName
import sympy as sp
import sympy.vector as spv
import scipy.optimize as sopt
import numpy as np

class _AlgoType(ProxyType):
    'SciPy minimize algorithm meta class'

    _typeID = '_AlgorithmType'
    _typeEnum = 'AlgorithmType'
    _propGroup = 'SolverAlgorithm'
    _proxyName = '_algo'

def _makeProp(name,doc='',tp='App::PropertyFloat',group=None):
    if not group:
        group = _AlgoType._propGroup
    info = PropertyInfo(_AlgoType,name,tp,doc,duplicate=True,group=group)
    return info.Key

_makeProp('Tolerance','','App::PropertyPrecision','Solver')

class _AlgoBase(object):
    __metaclass__ = _AlgoType
    _id = -2
    _common_options = [_makeProp('maxiter',
        'Maximum number of function evaluations','App::PropertyInteger')]
    _options = []
    NeedHessian = False
    NeedJacobian = True

    def __init__(self,obj):
        self.Object = obj

    @classmethod
    def getName(cls):
        return cls.__name__[5:].replace('_','-')

    @property
    def Options(self):
        ret = {}
        for key in self._common_options + self._options:
            name = _AlgoType.getPropertyInfo(key).Name
            v = getattr(self.Object,name,None)
            if v:
                ret[name] = v
        return ret

    @property
    def Tolerance(self):
        tol = self.Object.Tolerance
        return tol if tol else None

    @classmethod
    def getPropertyInfoList(cls):
        return ['Tolerance'] + cls._common_options + cls._options

class _AlgoNoJacobian(_AlgoBase):
    NeedJacobian = False

class _AlgoNelder_Mead(_AlgoNoJacobian):
    _id = 0
    _options = [
        _makeProp('maxfev',
           'Maximum allowed number of function evaluations. Both maxiter and\n'
           'maxfev Will default to N*200, where N is the number of variables.\n'
           'If neither maxiter or maxfev is set. If both maxiter and maxfev \n'
           'are set, minimization will stop at the first reached.',
           'App::PropertyInteger'),
        _makeProp('xatol',
            'Absolute error in xopt between iterations that is acceptable for\n'
            'convergence.'),
        _makeProp('fatol',
            'Absolute error in func(xopt) between iterations that is \n'
            'acceptable for convergence.'),
    ]

class _AlgoPowell(_AlgoNelder_Mead):
    _id = 1

class _AlgoCG(_AlgoBase):
    _id = 2
    _options = [
        _makeProp('norm','Order of norm (Inf is max, -Inf is min).'),
        _makeProp('gtol','Gradient norm must be less than gtol before '
            'successful termination'),
    ]

class _AlgoBFGS(_AlgoCG):
    _id = 3

class _AlgoNeedHessian(_AlgoBase):
    NeedHessian = True

class _AlgoNewton_CG(_AlgoNeedHessian):
    _id = 4
    _options = [
        _makeProp('xtol','Average relative error in solution xopt acceptable '
            'for convergence.'),
    ]

class _AlgoL_BFGS_B(_AlgoBase):
    _id = 5
    _options = [
        _makeProp('maxcor',
            'The maximum number of variable metric corrections used to define\n'
            'the limited memory matrix. (The limited memory BFGS method does\n'
            'not store the full hessian but uses this many terms in an \n'
            'approximation to it.)','App::PropertyInteger'),
        _makeProp('factr',
            'The iteration stops when \n'
            '   (f^k - f^{k+1})/max{|f^k|,|f^{k+1}|,1} <= factr * eps,\n'
            'where eps is the machine precision, which is automatically \n'
            'generated by the code. Typical values for factr are: 1e12 for\n'
            'low accuracy; 1e7 for moderate accuracy; 10.0 for extremely high\n'
            'accuracy.'),
        _makeProp('ftol','The iteration stops when (f^k - f^{k+1})/max{|f^k|,'
            '|f^{k+1}|,1} <= ftol.'),
        _makeProp('gtol','The iteration will stop when max{|proj g_i | i = 1, '
            '..., n} <= gtol\nwhere pg_i is the i-th component of the projected'
            'gradient.'),
        _makeProp('maxfun','Maximum number of function evaluations.',
            'App::PropertyInteger'),
        _makeProp('maxls','Maximum number of line search steps (per iteration).'
            'Default is 20.'),
    ]

class _AlgoTNC(_AlgoBase):
    _id = 6
    _options = [
        _makeProp('offset',
            'Value to subtract from each variable. If None, the offsets are \n'
            '(up+low)/2 for interval bounded variables and x for the others.'),
        _makeProp('maxCGit',
            'Maximum number of hessian*vector evaluations per main iteration.\n'
            'If maxCGit == 0, the direction chosen is -gradient if maxCGit<0,\n'
            'maxCGit is set to max(1,min(50,n/2)). Defaults to -1.'),
        _makeProp('eta','Severity of the line search. if < 0 or > 1, set to'
            '0.25. Defaults to -1.'),
        _makeProp('stepmx',
            'Maximum step for the line search. May be increased during call.\n'
            'If too small, it will be set to 10.0. Defaults to 0.'),
        _makeProp('accuracy',
           'Relative precision for finite difference calculations. If <=\n'
           'machine_precision, set to sqrt(machine_precision). Defaults to 0.'),
        _makeProp('minifev','Minimum function value estimate. Defaults to 0.',
            'App::PropertyInteger'),
        _makeProp('ftol',
            'Precision goal for the value of f in the stoping criterion.\n'
            'If ftol < 0.0, ftol is set to 0.0 defaults to -1.'),
        _makeProp('xtol',
            'Precision goal for the value of x in the stopping criterion\n'
            '(after applying x scaling factors). If xtol < 0.0, xtol is set\n'
            'to sqrt(machine_precision). Defaults to -1.'),
        _makeProp('gtol',
            'Precision goal for the value of the projected gradient in the\n'
            'stopping criterion (after applying x scaling factors). If \n'
            'gtol < 0.0, gtol is set to 1e-2 * sqrt(accuracy). Setting it to\n'
            '0.0 is not recommended. Defaults to -1.'),
        _makeProp('rescale',
            'Scaling factor (in log10) used to trigger f value rescaling. If\n'
            '0, rescale at each iteration. If a large value, never rescale.\n'
            'If < 0, rescale is set to 1.3.')
    ]


class _AlgoCOBYLA(_AlgoNoJacobian):
    _id = 7
    _options = [
        _makeProp('rhobeg','Reasonable initial changes to the variables'),
        _makeProp('tol',
            'Final accuracy in the optimization (not precisely guaranteed).\n'
            'This is a lower bound on the size of the trust region'),
    ]

class _AlgoSLSQP(_AlgoNoJacobian):
    _id = 8
    _options = [
        _makeProp('ftol',
            'Precision goal for the value of f in the stopping criterion'),
    ]


class _Algodogleg(_AlgoNeedHessian):
    _id = 9
    _options = [
        _makeProp('initial_trust_radius','Initial trust-region radius'),
        _makeProp('max_trust_radius',
            'Maximum value of the trust-region radius. No steps that are\n'
            'longer than this value will be proposed'),
        _makeProp('eta',
            'Trust region related acceptance stringency for proposed steps'),
        _makeProp('gtol','Gradient norm must be less than gtol before '
            'successful termination'),
    ]

class _Algotrust_ncg(_Algodogleg):
    _id = 10

class SystemSymPy(SystemBase):
    __metaclass__ = System
    _id = 2

    def __init__(self,obj):
        super(SystemSymPy,self).__init__(obj)
        _AlgoType.attach(obj)

    def onDetach(self,obj):
        _AlgoType.detach(obj,True)

    @classmethod
    def getName(cls):
        return 'SymPy + SciPy'

    def isConstraintSupported(self,cstrName):
        return _MetaType.isConstraintSupported(cstrName) or \
                getattr(_SystemSymPy,'add'+cstrName)

    def getSystem(self,obj):
        return _SystemSymPy(self,_AlgoType.getProxy(obj))

    def isDisabled(self,_obj):
        return False

    def onChanged(self,obj,prop):
        _AlgoType.onChanged(obj,prop)
        super(SystemSymPy,self).onChanged(obj,prop)


class _Base(object):
    def __init__(self,name,g):
        self._symobj = None
        self.group = g
        self.solvingGroup = None
        self._name = name

    def reset(self,g):
        self.solvingGroup = g
        self._symobj = None

    @property
    def Name(self):
        if self._name:
            return '"{}"'.format(self._name)
        return '<unknown>'

    @property
    def SymObj(self):
        if self._symobj is None:
            self._symobj = self.getSymObj()
        return self._symobj

    def __repr__(self):
        return '"{}"'.format(self.__class__.__name__[1:])


class _Param(_Base):
    def __init__(self,name,v,g):
        self.val = v
        self._sym = sp.Dummy(name,real=True)
        self._symobj = self._sym
        self._val = sp.Float(self.val)
        super(_Param,self).__init__(name,g)

    def reset(self,g):
        if self.group == g:
            self._symobj = self._sym
        else:
            self._symobj = self._val

    @property
    def _repr(self):
        return self.val

    def __repr__(self):
        return '{}({})'.format(self._name,self._val)

class _MetaType(type):
    _types = []
    _typeMap = {}

    def __init__(cls, name, bases, attrs):
        super(_MetaType,cls).__init__(name,bases,attrs)
        if len(cls._args):
            logger.trace('registing sympy ' + cls.__name__)
            mcs = cls.__class__
            mcs._types.append(cls)
            mcs._typeMap[cls.__name__[1:]] = cls

    @classmethod
    def isConstraintSupported(mcs,name):
        cls = mcs._typeMap.get(name,None)
        if cls:
            return issubclass(cls,_Constraint)


class _MetaBase(_Base):
    __metaclass__ = _MetaType
    _args = ()
    _opts = ()
    _vargs = ()
    def __init__(self,system,args,kargs):
        cls = self.__class__
        n = len(cls._args)+len(cls._opts)
        max_args = n
        if kargs is None:
            kargs = {}
        if 'group' in kargs:
            g = kargs['group']
            kargs.pop('group')
        elif len(args) > n:
            g = args[n]
            max_args = n+1
        else:
            g = 0
        if not g:
            g = system.GroupHandle
        super(_MetaBase,self).__init__(system.NameTag,g)

        if len(args) < len(cls._args):
            raise ValueError('not enough parameters when making ' + str(self))
        if len(args) > max_args:
            raise ValueError('too many parameters when making ' + str(self))
        for i,p in enumerate(args):
            if i < len(cls._args):
                setattr(self,cls._args[i],p)
                continue
            i -= len(cls._args)
            if isinstance(cls._opts[i],tuple):
                setattr(self,cls._opts[i][0],p)
            else:
                setattr(self,cls._opts[i],p)
        for k in self._opts:
            if isinstance(k,tuple):
                k,p = k
            else:
                p = 0
            if k in kargs:
                p = kargs[k]
                if hasattr(self,k):
                    raise KeyError('duplicate key "{}" while making '
                            '{}'.format(k,self))
                kargs.pop(k)
            setattr(self,k,p)
        if len(kargs):
            for k in kargs:
                raise KeyError('unknown key "{}" when making {}'.format(
                    k,self))
        if cls._vargs:
            nameTagSave = system.NameTag
            if nameTagSave:
                nameTag = nameTagSave + '.' + cls.__name__[1:] + '.'
            else:
                nameTag = cls.__name__[1:] + '.'
            for k in cls._vargs:
                v = getattr(self,k)
                system.NameTag = nameTag+k
                setattr(self,k,system.addParamV(v,g))
            system.NameTag = nameTagSave

    @property
    def _repr(self):
        v = {}
        cls = self.__class__
        for k in cls._args:
            attr = getattr(self,k)
            v[k] = getattr(attr,'_repr',attr)
        for k in cls._opts:
            if isinstance(k,(tuple,list)):
                attr = getattr(self,k[0])
                if attr != k[1]:
                    v[k[0]] = attr
                continue
            attr = getattr(self,k)
            if attr:
                v[k] = attr
        return v

    def __repr__(self):
        return '\n{}<{}>:{{\n {}\n'.format(self._name,
                self.__class__.__name__[1:],
                pprint.pformat(self._repr,indent=1,width=1)[1:])

    def getEqWithParams(self,_args):
        return self.getEq()

    def getEq(self):
        return []


if hasattr(spv,'CoordSys3D'):
    CoordSystem = spv.CoordSys3D
else:
    CoordSystem = spv.CoordSysCartesian
_gref = CoordSystem('global')

def _makeVector(x,y,z,ref=None):
    if not ref:
        ref = _gref
    return x.SymObj * ref.i + y.SymObj * ref.j + z.SymObj * ref.k

def _project(wrkpln,*args):
    if not wrkpln:
        return [ e.Vector for e in args ]
    r = wrkpln.CoordSys
    return [ e.Vector.dot(r.i)+e.Vector.dot(r.j) for e in args ]

def _distance(wrkpln,p1,p2):
    e1,e2 = _project(wrkpln,p1,p2)
    return (e1-e2).magnitude()

def _pointPlaneDistance(pt,pln):
    e = _project(pln,[pt])
    return (e[0]-pln.origin.Vector).magnitude()

def _pointLineDistance(wrkpln,pt,line):
    ep,ea,eb = _project(wrkpln,pt,line.p1,line.p2)
    eab = ea - eb
    return eab.cross(ea-ep).magnitude()/eab.magnitude()

def _directionConsine(wrkpln,l1,l2,supplement=False):
    l1p1,l1p2,l2p1,l2p2 = _project(wrkpln,l1.p1,l1.p2,l2.p1,l2.p2)
    v1 = l1p1-l1p2
    if supplement:
        v1 = v1 * -1.0
    v2 = l2p1-l2p2
    return v1.cross(v2)/(v1.magnitude()*v2.magnitude())

_x = 'i'
_y = 'j'
_z = 'k'
def _vectorComponent(v,*args,**kargs):
    if not args:
        args = (_x,_y,_z)
    if isinstance(v,spv.VectorZero):
        return [sp.S.Zero]*len(args)
    v = spv.express(v,_gref)
    ret = [v.components.get(getattr(_gref,a),sp.S.Zero) for a in args]
    if not kargs:
        return ret
    subs = kargs.get('subs',None)
    if not subs:
        return ret
    return [ c.evalf(subs=subs) for c in ret ]

def _vectorsParallel(args,a,b):
    a = a.Vector
    b = b.Vector
    r = a.cross(b)
    rx,ry,rz = [ c for c in _vectorComponent(r,subs=args)]
    x,y,z = [ abs(c) for c in _vectorComponent(a,subs=args)]
    if x > y and x > z:
        return [ry, rz]
    elif y > z:
        return [rz, rx]
    else:
        return [rx, ry]

def _vectorsEqual(projected,v1,v2):
    if projected:
        x1,y1 = _vectorComponent(v1,_x,_y)
        x2,y2 = _vectorComponent(v2,_x,_y)
        return (x1-x2,y1-y2)
    x1,y1,z1 = _vectorComponent(v1)
    x2,y2,z2 = _vectorComponent(v2)
    return (x1-x2,y1-y2,z1-z2)

class _Entity(_MetaBase):
    @classmethod
    def make(cls,system):
        return lambda *args,**kargs :\
                system.addEntity(cls(system,args,kargs))

    @property
    def CoordSys(self):
        return _gref

class _Vector(_Entity):
    Vector = _Entity.SymObj

    @property
    def CoordSys(self):
        return self.Vector.system

class _Point(_Vector):
    pass

class _Point2d(_Point):
    _args = ('wrkpln', 'u', 'v')

    def getSymObj(self):
        r = self.wrkpln.CoordSys
        return self.u.SymObj * r.i + self.v.SymObj * r.j

class _Point2dV(_Point2d):
    _vargs = ('u','v')

class _Point3d(_Point):
    _args = ('x','y','z')

    def getSymObj(self):
        return _makeVector(self.x,self.y,self.z)

class _Point3dV(_Point3d):
    _vargs = _Point3d._args

class _Normal(_Vector):
    @property
    def Vector(self):
        return self.SymObj.k

class _Normal3d(_Normal):
    _args = ('qw','qx','qy','qz')

    @property
    def Params(self):
        return (self.qw.SymObj,self.qx.SymObj,self.qy.SymObj,self.qz.SymObj)

    def getSymObj(self):
        name = self._name if self._name else 'R'
        return _gref.orient_new_quaternion(name,*self.Params)

    def getEq(self):
        return sp.Matrix(self.Params).norm() - 1.0

class _Normal3dV(_Normal3d):
    _vargs = _Normal3d._args

class _Normal2d(_Normal):
    _args = ('wrkpln',)

    def getSymObj(self):
        return self.wrkpln.normal.SymObj

class _Distance(_Entity):
    _args = ('d',)

    def getSymObj(self):
        return sp.Float(self.d)

class _DistanceV(_Distance):
    _vargs = _Distance._args

class _LineSegment(_Vector):
    _args = ('p1','p2')

    def getSymObj(self):
        return self.p1.Vector - self.p2.Vector

#  class _Cubic(_Entity):
#      _args = ('wrkpln', 'p1', 'p2', 'p3', 'p4')

class _ArcOfCircle(_Entity):
    _args = ('wrkpln', 'center', 'start', 'end')

    @property
    def CoordSys(self):
        return self.wrkpln.SymObj

    def getSymObj(self):
        return _project(self.wrkpln,self.center,self.start,self.end)

    @property
    def Center(self):
        return self.SymObj[0]

    @property
    def Start(self):
        return self.SymObj[1]

    @property
    def End(self):
        return self.SymObj[2]

    @property
    def Radius(self):
        return (self.Center-self.Start).magnitude()

    def getEq(self):
        return self.Radius - (self.Center-self.End).magnitude()

class _Circle(_Entity):
    _args = ('center', 'normal', 'radius')

    @property
    def Radius(self):
        return self.radius.SymObj

    @property
    def Center(self):
        return self.SymObj

    def getSymObj(self):
        return spv.express(self.center.Vector,self.normal.SymObj)

    @property
    def CoodSys(self):
        return self.normal.SymObj

class _CircleV(_Circle):
    _vargs = _Circle._args

class _Workplane(_Entity):
    _args = ('origin', 'normal')

    def getSymObj(self):
        name = self._name if self._name else 'W'
        return self.normal.SymObj.locate_new(name,self.origin.Vector)

    @property
    def CoordSys(self):
        return self.SymObj

class _Translate(_Vector):
    _args = ('src', 'dx', 'dy', 'dz')
    #  _opts = (('scale',1.0), 'timesApplied')

    @property
    def Vector(self):
        e = self.SymObj
        if isinstance(e,spv.Vector):
            return e
        else:
            return e.k

    def getSymObj(self):
        e = self.src.SymObj
        if isinstance(e,spv.Vector):
            return e+_makeVector(self.dx,self.dy,self.dz)
        elif isinstance(e,CoordSystem):
            # This means src is a normal, and we don't translate normal in order
            # to be compatibable with solvespace
            logger.warn('{} translating normal has no effect'.format(self.Name))
            return e
        else:
            raise ValueError('unsupported transformation {} of '
                '{} with type {}'.format(self.Name,self.src,e))

class _Transform(_Translate):
    _args = ('src', 'dx', 'dy', 'dz', 'qw', 'qx', 'qy', 'qz')
    _opts = (('asAxisAngle',False),
             # not support for scal and timesApplied yet
             #  ('scale',1.0),'timesApplied'
             )

    def getSymObj(self):
        e = self.src.SymObj
        if isinstance(e,spv.Vector):
            location = _makeVector(self.dx,self.dy,self.dz)
            if isinstance(e,spv.VectorZero):
                return location
            ref = e._sys
        elif isinstance(e,CoordSystem):
            # This means src is a normal, and we don't translate normal in order
            # to be compatibable with solvespace
            location = None
            ref = e
        else:
            raise ValueError('unknown supported transformation {} of '
                '{} with type {}'.format(self.Name,self.src,e))

        if self.asAxisAngle:
            r = ref.orient_new_axis(self._name, self.qw.SymObj,
                    _makeVector(self.qx, self.qy, self.qz), location)
        else:
            r = ref.orient_new_quaternion(self._name, self.qw.SymObj,
                    self.qx.SymObj, self.qy.SymObj, self.qz.SymObj, location)
        if not location:
            return r
        return spv.express(e,r) + _makeVector(self.dx,self.dy,self.dz)

class _Constraint(_MetaBase):
    @classmethod
    def make(cls,system):
        return lambda *args,**kargs :\
                system.addConstraint(cls(system,args,kargs))

class _ProjectingConstraint(_Constraint):
    _opts = ('wrkpln',)

    def project(self,*args):
        return _project(self.wrkpln,*args)

class _PointsDistance(_ProjectingConstraint):
    _args = ('d', 'p1', 'p2',)

    def getEq(self):
        return _distance(self.wrkpln,self.p1,self.p2) - self.d

class _PointsProjectDistance(_Constraint):
    _args = ('d', 'p1', 'p2', 'line')

    def getEq(self):
        dp = self.p1.Vector - self.p2.Vector
        pp = self.line.Vector.normalize()
        return dp.dot(pp) - self.d

class _PointsCoincident(_ProjectingConstraint):
    _args = ('p1', 'p2',)

    def getEq(self):
        p1,p2 = self.project(self.p1,self.p2)
        return _vectorsEqual(self.wrkpln,p1,p2)

class _PointInPlane(_ProjectingConstraint):
    _args = ('pt', 'pln')

    def getEq(self):
        return _pointPlaneDistance(self.pt,self.pln)

class _PointPlaneDistance(_ProjectingConstraint):
    _args = ('d', 'pt', 'pln')

    def getEq(self):
        return _pointPlaneDistance(self.pt,self.pln) - self.d.SymObj

class _PointOnLine(_ProjectingConstraint):
    _args = ('pt', 'line',)

    def getEq(self):
        return _pointLineDistance(self.wrkpln,self.pt,self.line)

class _PointLineDistance(_ProjectingConstraint):
    _args = ('d', 'pt', 'line')

    def getEq(self):
        d = _pointLineDistance(self.wrkpln,self.pt,self.line)
        return d**2 - self.d.SymObj**2

class _EqualLength(_ProjectingConstraint):
    _args = ('l1', 'l2',)

    @property
    def Distance1(self):
        return _distance(self.wrkpln,self.l1.p1,self.l1.p2)

    @property
    def Distance2(self):
        return _distance(self.wrkpln,self.l2.p1,self.l2.p2)

    def getEq(self):
        return self.Distance1 - self.Distance2

class _LengthRatio(_EqualLength):
    _args = ('ratio', 'l1', 'l2',)

    def getEq(self):
        return self.Distance1/self.Distance2 - self.ratio.SymObj

class _LengthDifference(_EqualLength):
    _args = ('diff', 'l1', 'l2',)

    def getEq(self):
        return self.Distance1 - self.Distance2 - self.diff.SymObj

class _EqualLengthPointLineDistance(_EqualLength):
    _args = ('pt','l1','l2')

    @property
    def Distance2(self):
        return _pointLineDistance(self.wrkpln,self.pt,self.l2)

    def getEq(self):
        return self.Distance1**2 - self.Distance2**2

class _EqualPointLineDistance(_EqualLengthPointLineDistance):
    _args = ('p1','l1','p2','l2')

    @property
    def Distance1(self):
        return _pointLineDistance(self.wrkpln,self.p1,self.l1)

    @property
    def Distance2(self):
        return _pointLineDistance(self.wrkpln,self.p1,self.l2)

class _EqualAngle(_ProjectingConstraint):
    _args = ('supplement', 'l1', 'l2', 'l3', 'l4')

    @property
    def Angle1(self):
        return _directionConsine(self.wrkpln,self.l1,self.l2,self.supplement)

    @property
    def Angle2(self):
        return _directionConsine(self.wrkpln,self.l3,self.l4)

    def getEq(self):
        return self.Angle1 - self.Angle2

class _EqualLineArcLength(_ProjectingConstraint):
    _args = ('line', 'arc')

    def getEq(self):
        raise NotImplementedError('not implemented')

class _Symmetric(_ProjectingConstraint):
    _args = ('p1', 'p2', 'pln')

    def getEq(self):
        e1,e2 = _project(self.wrkpln,self.p1,self.p2)
        m = (e1-e2)*0.5

        eq = []
        # first equation, mid point of p1 and p2 coincide with pln's origin
        eq += _vectorsEqual(0,m,self.pln.origin.Vector)

        e1,e2 = _project(self.pln,self.p1,self.p2)
        # second equation, p1 and p2 cincide when project to pln
        eq += _vectorsEqual(self.pln,e1,e2)
        return eq

class _SymmetricHorizontal(_Constraint):
    _args = ('p1', 'p2', 'wrkpln')

    def getEq(self):
        e1,e2 = _project(self.wrkpln,self.p1,self.p2)
        x1,y1 = _vectorComponent(e1,_x,_y)
        x2,y2 = _vectorComponent(e2,_x,_y)
        return [x1+x2,y1-y2]

class _SymmetricVertical(_Constraint):
    _args = ('p1', 'p2', 'wrkpln')

    def getEq(self):
        e1,e2 = _project(self.wrkpln,self.p1,self.p2)
        x1,y1 = _vectorComponent(e1,_x,_y)
        x2,y2 = _vectorComponent(e2,_x,_y)
        return [x1-x2,y1+y2]

class _SymmetricLine(_Constraint):
    _args = ('p1', 'p2', 'line', 'wrkpln')

    def getEq(self):
        e1,e2,le1,le2 = _project(self.wrkpln, self.p1, self.p2,
                self.line.p1, self.line.p2)
        return (e1-e2).dot(le1-le2)

class _MidPoint(_ProjectingConstraint):
    _args = ('pt', 'line')

    def getEq(self):
        e,le1,le2 = _project(self.wrkpln,self.pt,self.line.p1,self.line.p2)
        return _vectorsEqual(self.wrkpln,e,(le1-le2)*0.5)

class _PointsHorizontal(_ProjectingConstraint):
    _args = ('p1', 'p2')

    def getEq(self):
        e1,e2 = _project(self.wrkpln,self.p1,self.p2)
        x1, = _vectorComponent(e1,_x)
        x2, = _vectorComponent(e2,_x)
        return x1-x2

class _PointsVertical(_ProjectingConstraint):
    _args = ('p1', 'p2')

    def getEq(self):
        e1,e2 = _project(self.wrkpln,self.p1,self.p2)
        y1, = _vectorComponent(e1,_y)
        y2, = _vectorComponent(e2,_y)
        return y1-y2

class _LineHorizontal(_ProjectingConstraint):
    _args = ('line',)

    def getEq(self):
        e1,e2 = _project(self.wrkpln,self.line.p1,self.line.p2)
        x1, = _vectorComponent(e1,_x)
        x2, = _vectorComponent(e2,_x)
        return x1-x2

class _LineVertical(_ProjectingConstraint):
    _args = ('line',)

    def getEq(self):
        e1,e2 = _project(self.wrkpln,self.line.p1,self.line.p2)
        y1, = _vectorComponent(e1,_y)
        y2, = _vectorComponent(e2,_y)
        return y1-y2

class _Diameter(_Constraint):
    _args = ('d', 'c')

    def getEq(self):
        return self.c.Radius*2 - self.d.SymObj

class _PointOnCircle(_Constraint):
    _args = ('pt', 'circle')

    def getEq(self):
        # to be camptible with slvs, this actual constraint the point to the
        # cylinder
        e = _project(self.circle.normal,self.pt)
        return self.circle.Radius - (e-self.center.Vector).magnitude()

class _SameOrientation(_Constraint):
    _args = ('n1', 'n2')

    def getEqWithParams(self,args):
        if self.n1.group == self.solvingGroup:
            n1,n2 = self.n2,self.n1
        else:
            n1,n2 = self.n1,self.n2
        eqs = _vectorsParallel(args,n1,n2)
        d1 = n1.CoordSys.i.dot(n2.CoordSys.j)
        d2 = n1.CoordSys.i.dot(n2.CoordSys.i)
        if abs(d1.evalf(subs=args)) < abs(d2.evalf(subs=args)):
            eqs.append(d1)
        else:
            eqs.append(d2)
        return eqs

class _Angle(_ProjectingConstraint):
    _args = ('degree', 'supplement', 'l1', 'l2',)

    @property
    def DirectionCosine(self):
        return _directionConsine(self.wrkpln,self.l1,self.l2,self.supplement)

    def getEq(self):
        return self.Angle - sp.cos(self.degree.SymObj*sp.pi/180.0)

class _Perpendicular(_Angle):
    _args = ('l1', 'l2',)

    def getEq(self):
        return self.DirectionConsine

class _Parallel(_ProjectingConstraint):
    _args = ('l1', 'l2',)

    def getEqWithParams(self,args):
        if self.l1.group == self.solvingGroup:
            l1,l2 = self.l2,self.l1
        else:
            l1,l2 = self.l1,self.l2
        if not self.wrkpln:
            return _vectorsParallel(args,l1,l2)
        return l1.Vector.cross(l2.Vector).dot(self.wrkpln.normal.Vector)

#  class _ArcLineTangent(_Constraint):
#      _args = ('atEnd', 'arc', 'line')
#
#  class _CubicLineTangent(_Constraint):
#      _args = ('atEnd', 'cubic', 'line')
#      _opts = ('wrkpln',)
#
#  class _CurvesTangent(_Constraint):
#      _args = ('atEnd1', 'atEnd2', 'c1', 'c2', 'wrkpln')

class _EqualRadius(_Constraint):
    _args = ('c1', 'c2')

    def getEq(self):
        return self.c1.Radius - self.c2.Radius

#  class _WhereDragged(_ProjectingConstraint):
#      _args = ('pt',)

class _SystemSymPy(SystemExtension):
    def __init__(self,parent,algo):
        super(_SystemSymPy,self).__init__()
        self.GroupHandle = 1
        self.NameTag = '?'
        self.Dof = -1
        self.Failed = []
        self.Params = set()
        self.Constraints = set()
        self.Entities = set()
        self.eqs = []
        self.algo = algo
        self.log = parent.log

        for cls in _MetaType._types:
            name = 'add' + cls.__name__[1:]
            setattr(self,name,cls.make(self))

    def reset(self):
        self.__init__()

    def F(self,params,eq,jeqs,_heqs):
        params = tuple(params)
        res = eq(*params)
        if not jeqs:
            return res
        return (res,np.array([jeq(*params) for jeq in jeqs]))

    def hessF(self,params,_eqs,_jeqs,heqs):
        params = tuple(params)
        return np.array([[eq(*params) for eq in eqs] for eqs in heqs])

    EquationInfo = namedtuple('EquationInfo',('Name','Expr'))

    def solve(self, group=0, reportFailed=False):
        _ = reportFailed
        if not group:
            group = self.GroupHandle

        algo = self.algo

        # for params that can be represent by another single param
        param_subs = {}

        # restart equation generation if any equation can be solved earlier
        restart = False
        while True:
            params = {} # symobl -> value
            param_table = {} # symbol -> _Param object
            for e in self.Params:
                e.reset(group)
                if e.group == group:
                    params[e._sym] = e.val
                    param_table[e._sym] = e
            if not params:
                logger.error('no parameter')
                return
            for e in self.Constraints:
                e.reset(group)
            for e in self.Entities:
                e.reset(group)

            eqs = []
            active_params = {}
            for objs in (self.Entities,self.Constraints):
                for o in objs:
                    if o.group != group:
                        continue
                    eq = o.getEqWithParams(params)
                    if not eq:
                        continue
                    for e in eq if isinstance(eq,(list,tuple)) else [eq]:
                        symbols = e.free_symbols
                        if not symbols:
                            continue
                        if len(symbols)==1:
                            self.log('single solve {}: {}'.format(o.Name,e))
                            x = symbols[0]
                            if x not in param_table:
                                continue
                            f = sp.lambdify(x,e,modules='numpy')
                            ret = sopt.minimize_scalar(self.F,args=(f,None),
                                    tol=algo.Tolerance)
                            if not ret.success:
                                raise RuntimeError('failed to solve {}: '
                                    '{}'.format(o.Name,ret.message))
                            self.log('signal solve done: {}'.format(
                                o.Name,ret.x[0]))
                            restart = True
                            param = param_table[x]
                            param.group = -1
                            param.val = ret.x[0]
                            param._val = sp.Float(ret.x[0])
                            param_table.pop(x)
                            continue
                        if len(symbols)==2:
                            x,y = symbols
                            self.log('simple solve{}: {}'.format(o.Name,e))
                            try:
                                ret = sp.solve(eq,y)
                                if not ret:
                                    logger.warn('simple solve failed')
                                elif len(ret)!=1:
                                    self.log('simple solve returns {} '
                                        'solutions'.format(len(ret)))
                                else:
                                    param_subs[y] = param_table[x]
                                    param = param_table[y]
                                    param.group = -2
                                    param._val = ret[0]
                                    param_table.pop(y)
                                    self.log('simple solve done: {}'.format(
                                        param))
                                    continue
                            except Exception as excp:
                                logger.warn('simple solve exception: '
                                        '{}'.format(excp.message))

                        if not restart:
                            if len(active_params)!=len(params):
                                for x in symbols:
                                    if not x in active_params:
                                        active_params[x] = params[x]
                            eqs.append(self.EquationInfo(Name=o.Name, Expr=e))
            if not restart:
                break

        if not eqs:
            logger.error('no constraint')
            return

        self.log('parameters {}, {}, {}'.format(len(self.Params),
            len(params),len(active_params)))

        # all parameters to be solved
        params = active_params.keys()
        # initial values
        x0 = active_params.values()

        # For holding the sum of square of all equations, which is the one we
        # are trying to minimize
        f = None

        for i,eq in enumerate(eqs):
            self.log('\n\neq {}: {}\n'.format(i,eq.Expr))
            e = eq.Expr**2
            f = e if f is None else f+e

        eq = sp.lambdify(params,f,modules='numpy')

        self.log('generated {} equations, with {} parameters'.format(
            len(eqs),len(params)))

        jac = None
        jeqs = None
        heqs = None
        hessF = None
        if self.algo.NeedJacobian or self.algo.NeedHessian:
            # Jacobian matrix in sympy expressions
            jexprs = [f.diff(x) for x in params]

            if self.algo.NeedJacobian:
                # Lambdified Jacobian matrix
                jeqs = [sp.lambdify(params,je,modules='numpy') for je in jexprs]
                self.log('generated jacobian matrix')
                jac = True

            if self.algo.NeedHessian:
                # Lambdified Hessian matrix
                heqs = [[sp.lambdify(params,je.diff(x),modules='numpy')
                            for x in params] for je in jexprs ]
                self.log('generated hessian matrix')
                hessF = self.hessF

        ret = sopt.minimize(self.F,x0,(eq,jeqs,heqs), jac=jac,hess=hessF,
            tol=algo.Tolerance,method=algo.getName(),options=algo.Options)
        if ret.success:
            for x,v in zip(params,ret.x):
                param_table[x].val = v
                y = param_subs.get(x,None)
                if y:
                    y.val = y._val.evalf(x,v)
            self.log('solver success: {}'.format(ret.message))
        else:
            raise RuntimeError('failed to solve: {}'.format(ret.message))

    def getParam(self, h):
        if h not in self.Params:
            raise KeyError('parameter not found')
        return h

    def removeParam(self, h):
        self.Params.pop(h)

    def addParam(self, v, overwrite=False):
        _ = overwrite
        self.Params.add(v)
        return v

    def getConstraint(self, h):
        if h not in self.Constraints:
            raise KeyError('constraint not found')
        return h

    def removeConstraint(self, h):
        self.Constraints.pop(h)

    def addConstraint(self, v, overwrite=False):
        _ = overwrite
        self.Constraints.add(v)
        return v

    def getEntity(self, h):
        if h not in self.Entities:
            raise KeyError('entity not found')
        return h

    def removeEntity(self, _h):
        pass

    def addEntity(self, v, overwrite=False):
        _ = overwrite
        self.Entities.add(v)
        return v

    def addParamV(self, val, group=0):
        if not group:
            group = self.GroupHandle
        return self.addParam(_Param(self.NameTag,val,group))


