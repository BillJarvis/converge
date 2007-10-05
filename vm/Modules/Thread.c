// Copyright (c) 2003-2006 King's College London, created by Laurence Tratt
//
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to
// deal in the Software without restriction, including without limitation the
// rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
// sell copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in
// all copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
// FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
// IN THE SOFTWARE.


#include "Config.h"

#include "Bytecode.h"
#include "Core.h"
#include "Memory.h"
#include "Numbers.h"
#include "Object.h"
#include "Shortcuts.h"
#include "Slots.h"

#include "Builtins/Con_Stack/Atom.h"
#include "Builtins/Func/Atom.h"
#include "Builtins/List/Atom.h"
#include "Builtins/Module/Atom.h"
#include "Builtins/String/Atom.h"
#include "Builtins/Thread/Atom.h"
#include "Builtins/VM/Atom.h"



Con_Obj *Con_Module_Thread_init(Con_Obj *, Con_Obj *);
Con_Obj *Con_Module_Thread_import(Con_Obj *, Con_Obj *);

Con_Obj *_Con_Module_Thread_get_continuation_src_infos_func(Con_Obj *);




Con_Obj *Con_Module_Thread_init(Con_Obj *thread, Con_Obj *identifier)
{
	const char* defn_names[] = {"get_continuation_src_infos", NULL};

	return Con_Builtins_Module_Atom_new_c(thread, identifier, CON_NEW_STRING("Thread"), defn_names, CON_BUILTIN(CON_BUILTIN_NULL_OBJ));
}



Con_Obj *Con_Module_Thread_import(Con_Obj *thread, Con_Obj *thread_mod)
{
	CON_SET_MOD_DEF(thread_mod, "get_continuation_src_infos", CON_NEW_UNBOUND_C_FUNC(_Con_Module_Thread_get_continuation_src_infos_func, "get_continuation_src_infos", thread_mod));
	
	return thread_mod;
}



////////////////////////////////////////////////////////////////////////////////////////////////////
// Functions in Thread module
//


Con_Obj *_Con_Module_Thread_get_continuation_src_infos_func(Con_Obj *thread)
{
	Con_Obj *levels_back_obj;
	CON_UNPACK_ARGS("I", &levels_back_obj);
	
	Con_Int levels_back = Con_Numbers_Number_to_Con_Int(thread, levels_back_obj);
	
	Con_Obj *con_stack = Con_Builtins_Thread_Atom_get_con_stack(thread);

	CON_MUTEX_LOCK(&con_stack->mutex);
	Con_PC pc = Con_Builtins_Con_Stack_Atom_get_continuation_pc(thread, con_stack, levels_back);
	CON_MUTEX_UNLOCK(&con_stack->mutex);
	
	return Con_Builtins_Module_Atom_pc_to_src_locations(thread, pc);
}
