"""

Provides a way to encapsulate long-running operations so
that they can be invoked asynchronously and whilst active
their progress can be tracked from the calling thread.

Hides a great amount of detail about handling threads.

"""


import threading
import time

from rjgtoys.xc import BaseXC,BugXC

class Bug(BugXC):
    """Indicates an implementation bug
    
    Args:
        description: Text describing the bug
    """
    
    oneline = "Bug: {description)"
    
class ErrorXC(BaseXC):
    """Base class for error exceptions"""

    pass

class NothingToDoError(BugXC):
    """Raised when an empty action is invoked"""
    
    oneline = "Nothing to do"

class AlreadyStartedError(ErrorXC):
    """Raised on an attempt to start an operation that is already active"""
    
    oneline = "Already started"

class ActionFailedError(ErrorXC):
    """Raised if the action fails to perform the right protocol with the wrapper code"""
    
    oneline = "Action failed"

class Thread(object):
    """
    A decorator for a callable that makes the callable
    capable of being progress-tracked::
    
        @Thread()
        def func(tracker,...)
       
    ``func`` is converted into a :class:`Threaded` object,
    which can behave just like the original function but can also
    be called asynchronously.   You can still do::
    
        result = func(...)
        
    but you can also do::
    
        func.start(...)
        
        result = func.wait()
    
    The enhanced function still permits of only one caller at a time,
    but the function execution proceeds in a separate thread.
    
    Note the additional ``tracker`` parameter in the function declaration:
    this is passed the wrapper object, and is used by the function to
    report on its progress.   It is never passed by the caller.
    
    In other words, if you declare::
    
        @Thread()
        def find_all_files(tracker,root_dir)
        
    Then the function behaves as if it were declared::
    
        def find_all_files(root_dir)
            ...
    
    Calls to it might look like this:
    
        result = find_all_files('/tmp')
        
    Or::
    
        find_all_files.start('/usr')
        
        result = find_all_files.wait()

    """

    def __init__(self,name=None):
        self.name = name
    
    def __call__(self,f):
        
        return Threaded(target=f,name=self.name)

# codes to indicate how the function returned

RETURN_NOTHING = 0      # No result at all (yet)
RETURN_VALUE = 1       # A result (value)
RETURN_EXCEPTION = 2    # An exception was raised

class Threaded(object):
    """
    Encapsulates a process so that the caller can
    monitor its progress.
    
    This is the result of the :class:`Thread` decorator.
    """
    
    def __init__(self,target=None,name=None):
        """
        Args:
            name: A descriptive name for this operation
        """

        self._target = target
        self.name = name
        self._lock = threading.RLock()
        self._stopping = threading.Event()
        self._started = threading.Event()
        self._running = False
        
        self._steps = 0
        self._done = 0

    def run(self,*args,**kwargs):
        """
        Perform the progressive operation.
        
        This object ('self') is always passed as the first parameter
        
        May be overridden in a subclass.
        """

        if self._target is None:
            raise NothingToDoBug(self)

        self._return = RETURN_NOTHING
        self._result = None
        self._exc_info = (None,None,None)
        
        try:
            r = self._target(self,*args,**kwargs)
            self._return = RETURN_VALUE
            self._result = r
        except:
            self._return = RETURN_EXCEPTION
            self._exc_info = sys.exc_info()

    def _run_stop(self,*args,**kwargs):
    
        self.run(*args,**kwargs)

        if not self._started.is_set():  # Failed to call set_goal?
            return                      # caller will notice and raise ActionFailedException

        with self._lock:
            self.update(0)              # Ensure final update
            self._started.clear()
            self._running = False

    def start(self,*args,**kwargs):
        """
        Start the action.  Needs to reset the progress info too.
        """
        
        with self._lock:
            
            if self._running:
                raise AlreadyStartedError(self)

            self._running = True
            self._started.clear()

            self.since = time.time()
            try:
                self._worker = threading.Thread(target=self._run_stop,
                                            name=self.name,
                                            args=args,kwargs=kwargs)
                self._worker.start()
            except:
                self._running = False
                raise

            while not self._started.wait(1.0):      # Wait for operation to start
                if not self._worker.is_alive():     # keeping an eye on early abort
                    self._running = False           # Not running after all
                    raise ActionFailedError(self)
    
    def started(self):
        return self._started.is_set()

    def stop(self):
        self._stopping.set()

    def stopping(self):
        return self._stopping.is_set()

    def set_goal(self,steps=None,done=0):
        """
        Called from run: sets the goal of
        this action (defined by a number of steps)
        
        Until this is done nothing will see any progress
        reports and the action is not considered
        'started'
        
        *MUST* be called by the action.
        
        The main lock is already held by the starting thread.
        """

        if steps is not None:
            self._steps = steps
        self._done = done
        self._updated = time.time()
        
        self._started.set()
    
    def update(self,done=1):
        """
        Called by the action whenever it has made
        some progress
        """

        with self._lock:
            t = time.time()
            
            self._updated = t
            
            self._done += done
            
            if self._done < 0:
                self._done = 0
            elif self._done > self._steps:
                self._done = self._steps
        
    def stop(self):
        self._stopping.set()

    def sample(self):
        with self._lock:
            
            t = time.time()
            
            self.sampled = t
            
            self.updated = self._updated
            self.steps = self._steps
            self.done = self._done
            
            if self.steps:
                self.pcdone = int(self.done*100/self.steps)
            else:
                self.pcdone = 0

            if self.pcdone:
                # time to go = time to do the rest - time since the update
                self.ttg = (((self.updated-self.since)*(100.-self.pcdone))/self.pcdone)-(self.sampled-self.updated)
            else:
                self.ttg = 60.0    # Needs to be a time
        
            self.eta = self.ttg + t
            self.elapsed = t-self.since

    def wait(self,timeout=None):

        self._worker.join(timeout)

        # Return the result and try hard not to keep a reference to it
        
        if self._return == RETURN_VALUE:
            r = self._result
            self._return = RETURN_NOTHING
            self._result = None
            return r
            
        if self._return == RETURN_EXCEPTION:
            raise self._exc_info[1]
        
        raise Bug("Unrecognised return type")
        
            
    def __call__(self,*args,**kwargs):
        """
        A simple synchronous call
        """

        self.start(*args,**kwargs)
        return self.wait()
        # No result?

    def exc_info(self):
        """Get the exception info associated with the last
        call of this :class:`Threaded`
        """
        
        return self._exc_info
