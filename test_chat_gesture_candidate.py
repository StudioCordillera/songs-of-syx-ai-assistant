from math import inf,nan
import pytest
from dev.chat_gesture_candidate import GestureCandidate,Rect


BOUNDS=(1280,960)


def start(target='launcher',rect=Rect(40,40,44,44),x=50,y=50):
    g=GestureCandidate();g.begin(target,x,y,0,rect,BOUNDS);return g


def sample(g,x,y,at,held=True,active=True,bounds=BOUNDS):
    return g.sample(x,y,at,held=held,surface_active=active,viewport=bounds)


def test_launcher_click_toggles_once_on_release():
    g=start()
    assert sample(g,51,51,100)[0]=='holding'
    assert sample(g,51,51,140,False)[0]=='toggle'
    assert sample(g,51,51,150,False)==('idle',None)


def test_hold_then_drag_drops_without_toggle_and_clamps():
    g=start()
    assert sample(g,70,70,200)[0]=='holding'
    kind,rect=sample(g,1200,900,400)
    assert kind=='dragging' and rect==Rect(1190,890,44,44)
    kind,rect=sample(g,1280,960,500,False)
    assert kind=='dropped' and rect==Rect(1236,916,44,44)


def test_move_before_hold_then_release_never_opens_accidentally():
    g=start();sample(g,80,80,100)
    assert sample(g,80,80,150,False)[0]=='released'


@pytest.mark.parametrize('target',['header','chrome'])
def test_own_panel_chrome_moves_without_launcher_hold(target):
    g=start(target,Rect(40,40,600,500))
    kind,rect=sample(g,70,80,20)
    assert kind=='dragging' and rect==Rect(60,70,600,500)
    assert sample(g,70,80,30,False)[0]=='dropped'


def test_resize_limits_and_small_viewport_rect_fit():
    g=start('resize',Rect(40,40,600,500),630,530)
    kind,rect=sample(g,100,100,20)
    assert kind=='dragging' and rect.width==480 and rect.height==320
    assert rect.x+rect.width<=1280 and rect.y+rect.height<=960
    assert Rect(40,40,600,500).fit(300,200)==Rect(0,0,300,200)


@pytest.mark.parametrize('change', ['inactive','viewport','outside','timeout'])
def test_cancellation_does_not_toggle_or_leave_capture(change):
    g=start()
    options={'held':True,'active':True,'bounds':BOUNDS};x=y=50;at=400
    if change=='inactive':options['active']=False
    if change=='viewport':options['bounds']=(800,600)
    if change=='outside':x=-1
    if change=='timeout':at=5000
    assert sample(g,x,y,at,**options)==('cancelled',None)
    assert sample(g,50,50,5100,False)==('idle',None)


@pytest.mark.parametrize('target',['composer','citation','button','game','scroll'])
def test_child_controls_and_game_cannot_initiate_capture(target):
    with pytest.raises(ValueError,match='mod-owned'):start(target)


@pytest.mark.parametrize('value',[nan,inf,-inf,True,'1'])
def test_nonfinite_or_coerced_coordinates_refused(value):
    g=start()
    with pytest.raises(ValueError):sample(g,value,50,20)
    assert g.capture is not None


def test_nested_capture_and_backwards_time_refused():
    g=start();sample(g,50,50,100)
    with pytest.raises(ValueError,match='Monotonic'):sample(g,50,50,99)
    with pytest.raises(ValueError,match='Existing'):g.begin('header',50,50,100,Rect(40,40,600,500),BOUNDS)
    assert g.cancel()==('cancelled',None)


def test_resize_at_edge_keeps_origin_and_remains_reachable():
    g=start('resize',Rect(1000,700,280,260),1270,950)
    kind,rect=sample(g,1280,960,20)
    assert kind=='dragging' and rect==Rect(1000,700,280,260)


@pytest.mark.parametrize('bounds',[(0,960),(1280,),('bad',960)])
def test_malformed_viewport_leaves_last_valid_capture_unchanged(bounds):
    g=start();before=dict(g.capture)
    with pytest.raises(ValueError):sample(g,50,50,100,bounds=bounds)
    assert g.capture==before
