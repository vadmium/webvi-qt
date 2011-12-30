from __future__ import print_function

from PyQt4.QtGui import (QFormLayout, QLayout)
from PyQt4.QtCore import (QTimer, QSocketNotifier)
import event

class FormLayout(QFormLayout):
    def __init__(self, *args, **kw):
        QFormLayout.__init__(self, *args,
            sizeConstraint=QLayout.SetMinAndMaxSize,
        **kw)
    
    def maximumSize(self):
        max = QFormLayout.maximumSize(self)
        max.setHeight(self.sizeHint().height())
        return max

class Event(event.Event):
    def __init__(self, signal):
        self.signal = signal
    def arm(self, callback):
        self.callback = callback
        self.signal.connect(self.slot)
    def close(self):
        self.signal.disconnect(self.slot)
    def slot(self, *args):
        self.callback(args)
    def __repr__(self):
        return "{0}({1})".format(type(self).__name__, self.signal)

class FdEvent(Event):
    def __init__(self, *args, **kw):
        self.note = QSocketNotifier(*args, **kw)
        self.note.setEnabled(False)
        Event.__init__(self, self.note.activated)
    def arm(self, *args):
        Event.arm(self, *args)
        self.note.setEnabled(True)
    def close(self, *args):
        self.note.setEnabled(False)
        Event.close(self, *args)

class ActionEvent(Event):
    def __init__(self, action):
        self.action = action
        Event.__init__(self, action.triggered)
    def arm(self, *args, **kw):
        self.action.pyqtConfigure(enabled=True)
        Event.arm(self, *args, **kw)
    def close(self, *args, **kw):
        Event.close(self, *args, **kw)
        self.action.pyqtConfigure(enabled=False)

def select(read=(), write=(), exc=(), timeout=None):
    op_names = dict((note, name) for (name, note) in dict(
        read=QSocketNotifier.Read,
        write=QSocketNotifier.Write,
        exc=QSocketNotifier.Exception,
    ).items())
    
    events = event.EventSet()
    
    if timeout is not None:
        timer = QTimer(singleShot=True, active=True, interval=timeout * 1000)
        timer.start()
        events.add(Event(timer.timeout))
    
    for (op, name) in op_names.items():
        for fd in locals()[name]:
            events.add(FdEvent(fd, op))
    
    (trigger, args) = (yield events)
    
    if isinstance(trigger, FdEvent):
        (fd,) = args
        raise StopIteration((fd, op_names[trigger.note.type()]))
    else:
        raise StopIteration((None, None))
