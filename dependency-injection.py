import inspect
import functools


object_ctors = {} # {name -> {(ctor, args, kwargs)}}
objects = {} # {name -> object}

ALREADY_CONSTRUCTED = object()
def make_object(name):
	assert name not in objects

	try:
		ctor, args, kwargs = object_ctors.pop(name)
	except KeyError:
		raise AttributeError('cannot find ' + name)

	if ctor is ALREADY_CONSTRUCTED:
		raise AttributeError('detected race / circular injection when injecting ' + name)

	object_ctors[name] = ALREADY_CONSTRUCTED, None, None
	obj = ctor(*args, **kwargs)
	objects[name] = obj
	return obj

NOT_FOUND = object()
def get_or_make_object(name):
	obj = objects.get(name, NOT_FOUND)
	if obj is NOT_FOUND:
		return make_object(name)
	return obj

def inject(name):
	class Inject(object):
		def __get__(self, _instance, _owner):
			obj = get_or_make_object(name)
			self.__get__ = lambda _instance, _owner: obj
			return obj
	return Inject()

def inject_into_args(*names):
	def decorator(func):
		arg_spec = inspect.getargspec(func)
		func_args = set(arg_spec.args)
		func_takes_kwargs = bool(arg_spec.keywords)
		assert func_takes_kwargs or all(name in func_args for name in names)

		to_inject = {}

		@functools.wraps(func)
		def inner(*args, **kwargs):
			if not to_inject:
				to_inject.update({name: get_or_make_object(name) for name in names})

			kwargs.update(to_inject)
			return func(*args, **kwargs)

		return inner

	return decorator

def provide(name, ctor_or_value, *args, **kwargs):
	assert name not in objects

	if callable(ctor_or_value) or args or kwargs:
		ctor = ctor_or_value
	else:
		ctor = lambda: ctor_or_value

	for name in (name, name.replace('-', '_')):
		object_ctors[name] = (ctor, args, kwargs)




class A(object):
	b = inject('b')
	c = inject('c')
	d = inject('d')

	def __init__(self):
		print 'A()'
		self.c.f()
		self.c.f()
		print '/A()'

	def f(self):
		print 'A.f()'
		return self.b

class B(object):
	def __init__(self, a):
		print 'B(%s)' % a

class C(object):
	b = inject('b')
	a = inject('a')

	def __init__(self):
		print 'C()'

	def f(self):
		print 'C.f()'


@inject_into_args('a')
def hello(a):
	a.f()
	return a

def exc():
	raise RuntimeError('hello')

def main():
	provide('b', B, 2)
	provide('a', A)
	provide('c', C)
	provide('d', exc)

	a = hello()
	print
	aa = hello()
	assert a.b is aa.b
	assert a.c is aa.c
	assert a.c.a is a

	try:
		a.d
		assert False
	except RuntimeError:
		pass

if __name__ == '__main__':
	main()
