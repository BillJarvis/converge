# Copyright (c) 2011 King's College London, created by Laurence Tratt
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

from pypy.rlib import debug, jit
from pypy.rlib.objectmodel import UnboxedValue
from pypy.rpython.lltypesystem import lltype, rffi

NUM_BUILTINS = 41

from Core import *
import Target, VM




BUILTIN_NULL_OBJ = 0
BUILTIN_FAIL_OBJ = 1

# Core atom defs

BUILTIN_ATOM_DEF_OBJECT = 2
BUILTIN_SLOTS_ATOM_DEF_OBJECT = 3
BUILTIN_CLASS_ATOM_DEF_OBJECT = 4
BUILTIN_VM_ATOM_DEF_OBJECT = 5
BUILTIN_THREAD_ATOM_DEF_OBJECT = 6
BUILTIN_FUNC_ATOM_DEF_OBJECT = 7
BUILTIN_STRING_ATOM_DEF_OBJECT = 8
BUILTIN_CON_STACK_ATOM_DEF_OBJECT = 9
BUILTIN_LIST_ATOM_DEF_OBJECT = 10
BUILTIN_DICT_ATOM_DEF_OBJECT = 11
BUILTIN_MODULE_ATOM_DEF_OBJECT = 12
BUILTIN_INT_ATOM_DEF_OBJECT = 13
BUILTIN_UNIQUE_ATOM_DEF_OBJECT = 14
BUILTIN_CLOSURE_ATOM_DEF_OBJECT = 15
BUILTIN_PARTIAL_APPLICATION_ATOM_DEF_OBJECT = 16
BUILTIN_EXCEPTION_ATOM_DEF_OBJECT = 17
BUILTIN_SET_ATOM_DEF_OBJECT = 18

# Core classes

BUILTIN_OBJECT_CLASS = 19
BUILTIN_CLASS_CLASS = 20
BUILTIN_VM_CLASS = 21
BUILTIN_THREAD_CLASS = 22
BUILTIN_FUNC_CLASS = 23
BUILTIN_STRING_CLASS = 24
BUILTIN_CON_STACK_CLASS = 25
BUILTIN_LIST_CLASS = 26
BUILTIN_DICT_CLASS = 27
BUILTIN_MODULE_CLASS = 28
BUILTIN_INT_CLASS = 29
BUILTIN_CLOSURE_CLASS = 30
BUILTIN_PARTIAL_APPLICATION_CLASS = 31
BUILTIN_EXCEPTION_CLASS = 32
BUILTIN_SET_CLASS = 33
BUILTIN_NUMBER_CLASS = 34

BUILTIN_BUILTINS_MODULE = 35
BUILTIN_C_FILE_MODULE = 36
BUILTIN_EXCEPTIONS_MODULE = 37
BUILTIN_SYS_MODULE = 38

# Floats

BUILTIN_FLOAT_ATOM_DEF_OBJECT = 39
BUILTIN_FLOAT_CLASS = 40




################################################################################
# Con_Object
#

class Con_Object(Con_Thingy):
    __slots__ = ()



# This map class is inspired by:
#   http://morepypy.blogspot.com/2011/03/controlling-tracing-of-interpreter-with_21.html

class _Con_Map(object):
    __slots__ = ("index_map", "other_maps")
    _immutable_fields_ = ("index_map", "other_maps")


    def __init__(self):
        self.index_map = {}
        self.other_maps = {}


    @jit.elidable
    def find(self, n):
        return self.index_map.get(n, -1)


    @jit.elidable
    def extend(self, n):
        if n not in self.other_maps:
            nm = _Con_Map()
            nm.index_map.update(self.index_map)
            nm.index_map[n] = len(self.index_map)
            self.other_maps[n] = nm
        return self.other_maps[n]



_EMPTY_MAP = _Con_Map()



class Con_Boxed_Object(Con_Object):
    __slots__ = ("instance_of", "slots_map", "slots")
    _immutable_fields = ("slots",)


    def __init__(self, vm, instance_of=None):
        if instance_of is None:
            self.instance_of = vm.get_builtin(BUILTIN_OBJECT_CLASS)
        else:
            self.instance_of = instance_of
        self.slots_map = _EMPTY_MAP
        self.slots = None


    def get_slot(self, vm, n):
        o = self.get_slot_raw(vm, n)
        if isinstance(o, Con_Func):
            return Con_Partial_Application(vm, self, o)
        
        return o


    def get_slot_raw(self, vm, n):
        o = None
        if self.slots is not None:
            m = jit.promote(self.slots_map)
            i = m.find(n)
            if i != -1:
                o = self.slots[i]
    
        if o is None:
            o = self.instance_of.get_field(vm, n)
        
        if o is None and n == "instance_of":
            return self.instance_of
        
        if o is None:
            print o, n
            raise Exception("XXX")
        
        return o


    def set_slot(self, vm, n, v):
        m = jit.promote(self.slots_map)
        if self.slots is not None:
            i = m.find(n)
            if i == -1:
                self.slots_map = m.extend(n)
                self.slots.append(v)
            else:
                self.slots[i] = v
        else:
            self.slots_map = m.extend(n)
            self.slots = [v]


def _new_func_Con_Object(vm):
    (c,), vargs = vm.decode_args("O", vargs=True)
    o = Con_Boxed_Object(vm, c)
    vm.apply(o.get_slot(vm, "init"), vargs)
    vm.return_(o)


def _Con_Object_init(vm):
    (self,), vargs = vm.decode_args("O", vargs=True)
    vm.return_(vm.get_builtin(BUILTIN_NULL_OBJ))


def _Con_Object_to_str(vm):
    (o,),_ = vm.decode_args("O")
    vm.return_(new_con_string(vm, "<Object@%x>" % id(o)))


def bootstrap_con_object(vm):
    object_class = Con_Class(vm, "Object", [], None)
    vm.set_builtin(BUILTIN_OBJECT_CLASS, object_class)
    class_class = Con_Class(vm, "Class", [object_class], None)
    vm.set_builtin(BUILTIN_CLASS_CLASS, class_class)
    object_class.instance_of = class_class
    class_class.instance_of = class_class
    
    vm.set_builtin(BUILTIN_NULL_OBJ, Con_Boxed_Object(vm))
    vm.set_builtin(BUILTIN_FAIL_OBJ, Con_Boxed_Object(vm))
    
    # In order that later objects can refer to the Builtins module, we have to create it now.
    builtins_module = new_c_con_module(vm, "Builtins", "Builtins", __file__, ["Object", "Class"])
    # We effectively initialize the Builtins module through the bootstrapping process, so it doesn't
    # need a separate initialization function.
    builtins_module.initialized = True
    vm.set_builtin(BUILTIN_BUILTINS_MODULE, builtins_module)
    vm.set_mod(builtins_module)
    
    object_class.set_slot(vm, "container", builtins_module)
    class_class.set_slot(vm, "container", builtins_module)
    builtins_module.set_defn(vm, "Object", object_class)
    builtins_module.set_defn(vm, "Class", class_class)

    object_class.new_func = \
      new_c_con_func(vm, new_con_string(vm, "new_Object"), False, _new_func_Con_Object, \
        builtins_module)

    init_func = new_c_con_func(vm, new_con_string(vm, "init"), True, _Con_Object_init, object_class)
    object_class.set_field(vm, "init", init_func)

    to_str_func = new_c_con_func(vm, new_con_string(vm, "to_str"), True, _Con_Object_to_str, \
      object_class)
    object_class.set_field(vm, "to_str", to_str_func)




################################################################################
# Con_Class
#

class Con_Class(Con_Boxed_Object):
    __slots__ = ("name", "supers", "fields_map", "fields", "new_func")
    _immutable_fields = ("supers", "fields")


    def __init__(self, vm, name, supers, container, instance_of=None, new_func=None):
        if instance_of is None:
            instance_of = vm.get_builtin(BUILTIN_CLASS_CLASS)
        Con_Boxed_Object.__init__(self, vm, instance_of)
        
        if new_func is None:
            # A new object function hasn't been supplied so we need to search for one.
            # See http://tratt.net/laurie/tech_articles/articles/more_meta_matters for
            # more details about this algorithm.
            for sc in supers:
                assert isinstance(sc, Con_Class)
                if new_func is None:
                    new_func = sc.new_func
                elif new_func is not sc.new_func:
                    new_func = sc.new_func
                    object_class = vm.get_builtin(BUILTIN_OBJECT_CLASS)
                    assert isinstance(object_class, Con_Class)
                    object_class.new_func
                    if new_func is object_class.new_func:
                        new_func = sc.new_func
                    else:
                        # There's a clash between superclass's metaclasses.
                        raise Exception("XXX")
        self.new_func = new_func
        
        self.name = name
        self.supers = supers
        self.fields_map = _EMPTY_MAP
        self.fields = []

        self.set_slot(vm, "container", container)


    def get_field(self, vm, n):
        m = jit.promote(self.fields_map)
        i = m.find(n)
        if i != -1:
            return self.fields[i]
        
        for s in self.supers:
            assert isinstance(s, Con_Class)
            o = s.get_field(vm, n)
            if not None:
                return o

        return None


    def set_field(self, vm, n, o):
        m = jit.promote(self.fields_map)
        i = m.find(n)
        if i == -1:
            self.fields_map = m.extend(n)
            self.fields.append(o)
        else:
            self.fields[i] = o


def _new_func_Con_Class(vm):
    (c, name, supers, container), vargs = vm.decode_args("CSLO", vargs=True)
    assert isinstance(c, Con_Class)
    assert isinstance(name, Con_String)
    assert isinstance(supers, Con_List)
    o = Con_Class(vm, name.v, supers.l[:], container, c)
    vm.apply(o.get_slot(vm, "init"), vargs)
    vm.return_(o)


def _Con_Class_new(vm):
    _, v = vm.decode_args(vargs=True)
    c = v[0]
    vm.type_check(c, Con_Class)
    assert isinstance(c, Con_Class)
    vm.return_(vm.apply(c.new_func, v))


def _Con_Class_to_str(vm):
    (self,),_ = vm.decode_args("C")
    assert isinstance(self, Con_Class)

    vm.return_(new_con_string(vm, "<Class %s>" % self.name))


def _Con_Class_instantiated(vm):
    (self, o),_ = vm.decode_args("CO")
    assert isinstance(self, Con_Class)
    assert isinstance(o, Con_Boxed_Object)

    if o.instance_of is self:
        # We optimise the easy case.
        vm.return_(vm.get_builtin(BUILTIN_NULL_OBJ))
    else:
		# What we do now is to put 'instance_of' onto a stack; if the current class on the stack
		# does not match 'self', we push all the class's superclasses onto the stack.
		#
		# If we run off the end of the stack then there is no match.
        stack = [o.instance_of]
        while len(stack) > 0:
            cnd = stack.pop()
            assert isinstance(cnd, Con_Class)
            if cnd is self:
                vm.return_(vm.get_builtin(BUILTIN_NULL_OBJ))
            stack.extend(cnd.supers)

    vm.return_(vm.get_builtin(BUILTIN_FAIL_OBJ))


def bootstrap_con_class(vm):
    class_class = vm.get_builtin(BUILTIN_CLASS_CLASS)
    assert isinstance(class_class, Con_Class)
    class_class.new_func = \
      new_c_con_func(vm, new_con_string(vm, "new_Class"), False, _new_func_Con_Class, \
        vm.get_builtin(BUILTIN_BUILTINS_MODULE))

    new_func = new_c_con_func(vm, new_con_string(vm, "new"), True, _Con_Class_new, class_class)
    class_class.set_field(vm, "new", new_func)
    to_str_func = new_c_con_func(vm, new_con_string(vm, "to_str"), True, _Con_Class_to_str, \
      class_class)
    class_class.set_field(vm, "to_str", to_str_func)
    instantiated_func = new_c_con_func(vm, new_con_string(vm, "instantiated"), True, \
      _Con_Class_instantiated, class_class)
    class_class.set_field(vm, "instantiated", instantiated_func)


def new_con_class(vm, name, supers, container):
    return Con_Class(vm, name, supers, container)




################################################################################
# Con_Module
#

class Con_Module(Con_Boxed_Object):
    __slots__ = ("is_bc", "bc", "name", "id_", "src_path", "imps", "tlvars_map", "consts",
      "init_func", "values", "closure", "initialized")
    _immutable_fields_ = ("is_bc", "bc", "name", "id_", "src_path", "imps", "tlvars_map",
      "init_func", "consts")



    def __init__(self, vm, is_bc, bc, name, id_, src_path, imps, tlvars_map, num_consts, init_func):
        Con_Boxed_Object.__init__(self, vm, vm.get_builtin(BUILTIN_MODULE_CLASS))

        self.is_bc = is_bc # True for bytecode modules; False for RPython modules
        self.bc = bc
        self.name = name
        self.id_ = id_
        self.src_path = src_path
        self.imps = imps
        self.tlvars_map = tlvars_map
        self.consts = [None] * num_consts
        debug.make_sure_not_resized(self.consts)
        self.init_func = init_func
        
        self.values = []
        if is_bc:
            self.closure = None
        else:
            self.closure = [None] * len(tlvars_map)

        self.initialized = False


    def import_(self, vm):
        if self.initialized:
            return
        
        if self.is_bc:
            # Bytecode modules use the old "push a Con_Int onto the stack to signify how many
            # parameters are being passed" hack. To add insult injury, they simply pop this object
            # off without using it. So we pass null as a 'magic' first parameter, knowing that it
            # won't actually be used for anything.
            v, self.closure = vm.apply_closure(self.init_func, \
              [vm.get_builtin(BUILTIN_NULL_OBJ), self])
        else:
            vm.apply(self.init_func, [self])
        self.initialized = True
        return


    @jit.elidable_promote("0")
    def get_closure_i(self, vm, n):
        i = self.tlvars_map.get(n, -1)
        if i == -1:
            vm.raise_helper("Mod_Defn_Exception", \
              [Builtins.new_con_string(vm, "Definition '%s' not found in '%s'." % (n, self.name))])
        return i


    def get_defn(self, vm, n):
        return self.closure[self.get_closure_i(vm, n)]


    def set_defn(self, vm, n, o):
        self.closure[self.get_closure_i(vm, n)] = o


    def get_const_create_off(self, vm, i):
        create_off = Target.read_word(self.bc, Target.BC_MOD_CONSTANTS_CREATE_OFFSETS)
        off = Target.read_word(self.bc, create_off + i * Target.INTSIZE)
        return off



def bootstrap_con_module():
    pass



def new_c_con_module(vm, name, id_, src_path, names):
    tlvars_map = {}
    i = 0
    for j in names:
        tlvars_map[j] = i
        i += 1
    return Con_Module(vm, False, lltype.nullptr(rffi.CCHARP.TO), name, id_, src_path, [], tlvars_map, 0, None)


def new_bc_con_module(vm, bc, name, id_, src_path, imps, tlvars_map, num_consts):
    return Con_Module(vm, True, bc, name, id_, src_path, imps, tlvars_map, num_consts, None)





################################################################################
# Con_Func
#

class Con_Func(Con_Boxed_Object):
    __slots__ = ("name", "is_bound", "pc", "num_params", "num_vars", "container_closure")
    _immutable_fields_ = ("name", "is_bound", "pc", "num_params", "num_vars", "container_closure")


    def __init__(self, vm, name, is_bound, pc, num_params, num_vars, container, container_closure):
        Con_Boxed_Object.__init__(self, vm, vm.get_builtin(BUILTIN_FUNC_CLASS))
    
        self.name = name
        self.is_bound = is_bound
        self.pc = pc
        self.num_params = num_params
        self.num_vars = num_vars
        self.container_closure = container_closure
        
        self.set_slot(vm, "container", container)


    def __repr__(self):
        return "<Func %s>" % self.name.v


def bootstrap_con_func():
    pass


def new_c_con_func(vm, name, is_bound, func, container):
    cnd = container
    while not (isinstance(cnd, Con_Module)):
        cnd = cnd.get_slot(vm, "container")
    return Con_Func(vm, name, is_bound, VM.Py_PC(cnd, func), 0, 0, container, None)


def new_bc_con_func(vm, name, is_bound, pc, num_params, num_vars, container, container_closure):
    return Con_Func(vm, name, is_bound, pc, num_params, num_vars, container, container_closure)



################################################################################
# Con_Class
#

class Con_Partial_Application(Con_Boxed_Object):
    __slots__ = ("o", "f")
    _immutable_fields_ = ("o", "f")


    def __init__(self, vm, o, f):
        self.o = o
        self.f = f




################################################################################
# Con_Number
#

class Con_Number(Con_Object):
    pass




################################################################################
# Con_Int
#

class Con_Int(Con_Boxed_Object):
    __slots__ = ("v",)
    _immutable_fields_ = ("v",)


    def __init__(self, vm, v):
        Con_Boxed_Object.__init__(self, vm, vm.get_builtin(BUILTIN_INT_CLASS))
        self.v = v


    def add(self, vm, o):
        vm.type_check(o, Con_Int)
        assert isinstance(o, Con_Int)
        return Con_Int(vm, self.v + o.v)


    def subtract(self, vm, o):
        vm.type_check(o, Con_Int)
        assert isinstance(o, Con_Int)
        return Con_Int(vm, self.v - o.v)


    def eq(self, vm, o):
        vm.type_check(o, Con_Int)
        assert isinstance(o, Con_Int)
        return self.v == o.v


    def neq(self, vm, o):
        vm.type_check(o, Con_Int)
        assert isinstance(o, Con_Int)
        return self.v != o.v


    def le(self, vm, o):
        vm.type_check(o, Con_Int)
        assert isinstance(o, Con_Int)
        return self.v < o.v


    def le_eq(self, vm, o):
        vm.type_check(o, Con_Int)
        assert isinstance(o, Con_Int)
        return self.v <= o.v


    def gr_eq(self, vm, o):
        vm.type_check(o, Con_Int)
        assert isinstance(o, Con_Int)
        return self.v >= o.v


    def gt(self, vm, o):
        vm.type_check(o, Con_Int)
        assert isinstance(o, Con_Int)
        return self.v > o.v



def _Con_Int_to_str(vm):
    (self,),_ = vm.decode_args("I")
    assert isinstance(self, Con_Int)

    vm.return_(new_con_string(vm, str(self.v)))


def _Con_Int_idiv(vm):
    (self, o),_ = vm.decode_args("II")
    assert isinstance(self, Con_Int)
    assert isinstance(o, Con_Int)

    vm.return_(new_con_int(vm, self.v / o.v))


def _Con_Int_mul(vm):
    (self, o),_ = vm.decode_args("II")
    assert isinstance(self, Con_Int)
    assert isinstance(o, Con_Int)

    vm.return_(new_con_int(vm, self.v * o.v))


def bootstrap_con_int(vm):
    int_class = Con_Class(vm, "Int", [vm.get_builtin(BUILTIN_OBJECT_CLASS)], \
      vm.get_builtin(BUILTIN_BUILTINS_MODULE))
    vm.set_builtin(BUILTIN_INT_CLASS, int_class)
    to_str_func = new_c_con_func(vm, new_con_string(vm, "to_str"), True, _Con_Int_to_str, int_class)
    int_class.set_field(vm, "to_str", to_str_func)
    idiv_func = new_c_con_func(vm, new_con_string(vm, "idiv"), True, _Con_Int_idiv, int_class)
    int_class.set_field(vm, "idiv", idiv_func)
    mul_func = new_c_con_func(vm, new_con_string(vm, "*"), True, _Con_Int_mul, int_class)
    int_class.set_field(vm, "*", mul_func)



def new_con_int(vm, v):
    return Con_Int(vm, v)



################################################################################
# Con_String
#

class Con_String(Con_Boxed_Object):
    __slots__ = ("v",)
    _immutable_fields_ = ("v",)


    def __init__(self, vm, v):
        Con_Boxed_Object.__init__(self, vm, vm.get_builtin(BUILTIN_STRING_CLASS))
        self.v = v



def new_con_string(vm, v):
    return Con_String(vm, v)



################################################################################
# Con_List
#

class Con_List(Con_Boxed_Object):
    __slots__ = ("l",)
    _immutable_fields_ = ("l",)


    def __init__(self, vm, l):
        Con_Boxed_Object.__init__(self, vm, vm.get_builtin(BUILTIN_LIST_CLASS))
        self.l = l



def _Con_List_to_str(vm):
    (self,),_ = vm.decode_args("L")
    assert isinstance(self, Con_List)
    
    es = []
    for e in self.l:
        s = vm.get_slot_apply(e, "to_str")
        vm.type_check(s, Con_String)
        assert isinstance(s, Con_String)
        es.append(s.v)

    vm.return_(new_con_string(vm, "[%s]" % ", ".join(es)))


def _Con_List_append(vm):
    (self, o),_ = vm.decode_args("LO")
    assert isinstance(self, Con_List)
    
    self.l.append(o)
    vm.return_(vm.get_builtin(Builtins.BUILTIN_NULL_OBJ))


def _Con_List_get(vm):
    (self, i),_ = vm.decode_args("LI")
    assert isinstance(self, Con_List)
    assert isinstance(i, Con_Int)
    
    vm.return_(self.l[i.v])


def _Con_List_len(vm):
    (self,),_ = vm.decode_args("L")
    assert isinstance(self, Con_List)
    
    vm.return_(new_con_int(vm, len(self.l)))


def _Con_List_set(vm):
    (self, i, o),_ = vm.decode_args("LIO")
    assert isinstance(self, Con_List)
    assert isinstance(i, Con_Int)
    self.l[i.v] = o
    vm.return_(vm.get_builtin(Builtins.BUILTIN_NULL_OBJ))


def bootstrap_con_list(vm):
    list_class = Con_Class(vm, "List", [vm.get_builtin(BUILTIN_OBJECT_CLASS)], \
      vm.get_builtin(BUILTIN_BUILTINS_MODULE))
    vm.set_builtin(BUILTIN_LIST_CLASS, list_class)
    to_str_func = new_c_con_func(vm, new_con_string(vm, "to_str"), True, _Con_List_to_str, \
      list_class)
    list_class.set_field(vm, "to_str", to_str_func)
    len_func = new_c_con_func(vm, new_con_string(vm, "len"), True, _Con_List_len, \
      list_class)
    append_func = new_c_con_func(vm, new_con_string(vm, "append"), True, _Con_List_append, \
      list_class)
    list_class.set_field(vm, "append", append_func)
    list_class.set_field(vm, "len", len_func)
    get_func = new_c_con_func(vm, new_con_string(vm, "get"), True, _Con_List_get, \
      list_class)
    list_class.set_field(vm, "get", get_func)
    set_func = new_c_con_func(vm, new_con_string(vm, "set"), True, _Con_List_set, \
      list_class)
    list_class.set_field(vm, "set", set_func)


def new_con_list(vm, l):
    return Con_List(vm, l)



################################################################################
# Con_Exception
#

class Con_Exception(Con_Boxed_Object):
    __slots__ = ("call_chain",)
    _immutable_fields_ = ()


    def __init__(self, vm, instance_of):
        Con_Boxed_Object.__init__(self, vm, instance_of)
        self.call_chain = None


def _new_func_Con_Exception(vm):
    (class_, ), vargs = vm.decode_args("C", vargs=True)
    o = Con_Exception(vm, class_)
    vm.apply(o.get_slot(vm, "init"), vargs)
    vm.return_(o)


def _Con_Exception_init(vm):
    (self, msg),_ = vm.decode_args("OO")
    self.set_slot(vm, "msg", msg)
    vm.return_(vm.get_builtin(Builtins.BUILTIN_NULL_OBJ))


def bootstrap_con_exception(vm):
    exception_class = Con_Class(vm, "Exception", [vm.get_builtin(BUILTIN_OBJECT_CLASS)], \
      vm.get_builtin(BUILTIN_BUILTINS_MODULE))
    vm.set_builtin(BUILTIN_EXCEPTION_CLASS, exception_class)
    exception_class.new_func = \
      new_c_con_func(vm, new_con_string(vm, "new_Exception"), False, _new_func_Con_Exception, \
        vm.get_builtin(BUILTIN_BUILTINS_MODULE))

    init_func = new_c_con_func(vm, new_con_string(vm, "init"), True, _Con_Exception_init, \
      exception_class)
    exception_class.set_field(vm, "init", init_func)
