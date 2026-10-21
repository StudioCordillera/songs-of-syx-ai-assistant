"""Game-independent gesture candidate; not imported or packaged by the player.

The native adapter must establish own-surface eligibility and copy primitives on
its game thread. This model never polls/injects input or claims window focus.
"""
from dataclasses import dataclass
from math import isfinite,hypot


def number(value):
    if type(value) not in (int,float):raise ValueError('Finite numeric coordinate/time required')
    try:result=float(value)
    except (ValueError,OverflowError):raise ValueError('Finite numeric coordinate/time required') from None
    if not isfinite(result):raise ValueError('Finite numeric coordinate/time required')
    return result


def viewport_size(value):
    if not isinstance(value,(tuple,list)) or len(value)!=2:raise ValueError('Two viewport dimensions required')
    result=tuple(map(number,value))
    if min(result)<=0:raise ValueError('Positive viewport required')
    return result


@dataclass(frozen=True)
class Rect:
    x:float
    y:float
    width:float
    height:float

    def __post_init__(self):
        for value in (self.x,self.y,self.width,self.height):number(value)
        if self.width<=0 or self.height<=0:raise ValueError('Positive rectangle size required')

    def fit(self,width,height):
        width=number(width);height=number(height)
        if width<=0 or height<=0:raise ValueError('Positive viewport required')
        w=min(self.width,width);h=min(self.height,height)
        return Rect(max(0,min(self.x,width-w)),max(0,min(self.y,height-h)),w,h)


class GestureCandidate:
    HOLD_MS=350
    SLOP=6
    MAX_MS=5000
    TARGETS={'launcher','header','chrome','resize'}

    def __init__(self):self.capture=None

    def begin(self,target,x,y,at,rect,viewport):
        if self.capture is not None:raise ValueError('Existing own capture must finish or cancel')
        if target not in self.TARGETS:raise ValueError('Only explicit mod-owned gesture surfaces may capture')
        if not isinstance(rect,Rect):raise ValueError('Own layout rectangle required')
        x=number(x);y=number(y);at=number(at)
        bounds=viewport_size(viewport)
        bounded=rect.fit(*bounds)
        if not bounded.x<=x<=bounded.x+bounded.width or not bounded.y<=y<=bounded.y+bounded.height:
            raise ValueError('Press must be inside own layout bounds; native adapter must classify the gesture surface')
        self.capture=dict(target=target,x=x,y=y,at=at,last=at,rect=bounded,viewport=bounds,moved=False,drag=False,early=False,engaged=False)
        return bounded

    def cancel(self):
        self.capture=None
        return 'cancelled',None

    def sample(self,x,y,at,*,held,surface_active,viewport):
        if type(held) is not bool or type(surface_active) is not bool:raise ValueError('Explicit own input flags required')
        x=number(x);y=number(y);at=number(at)
        if self.capture is None:return 'idle',None
        c=self.capture
        if at<c['last']:raise ValueError('Monotonic gesture samples required')
        bounds=viewport_size(viewport)
        c['last']=at
        # Cancel rather than applying an old layout delta to a different scene/size.
        if not surface_active or bounds!=c['viewport'] or at-c['at']>=self.MAX_MS:return self.cancel()
        if not (0<=x<=bounds[0] and 0<=y<=bounds[1]):return self.cancel()
        dx=x-c['x'];dy=y-c['y'];distance=hypot(dx,dy)
        elapsed=at-c['at']
        c['moved']|=distance>self.SLOP
        if c['target']=='launcher':
            if not c['engaged'] and elapsed<self.HOLD_MS and distance>self.SLOP:c['early']=True
            if elapsed>=self.HOLD_MS and not c['early']:c['engaged']=True
            if held and c['engaged'] and c['moved']:c['drag']=True
        elif held and distance>0:c['drag']=True
        rect=c['rect']
        if c['drag']:
            if c['target']=='resize':
                # Minimums are candidate policy only, not measured native font/layout requirements.
                w=max(min(480,bounds[0]-rect.x),min(bounds[0]-rect.x,rect.width+dx))
                h=max(min(320,bounds[1]-rect.y),min(bounds[1]-rect.y,rect.height+dy))
                rect=Rect(rect.x,rect.y,w,h).fit(*bounds)
            else:rect=Rect(rect.x+dx,rect.y+dy,rect.width,rect.height).fit(*bounds)
        if held:
            status='dragging' if c['drag'] else 'blocked' if c['early'] else 'armed' if c['engaged'] else 'holding'
            return status,rect
        self.capture=None
        if c['drag']:return 'dropped',rect
        return ('toggle' if c['target']=='launcher' and not c['moved'] and not c['engaged'] and not c['early'] else 'released'),rect
