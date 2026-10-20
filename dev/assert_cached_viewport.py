"""Current-candidate scene invariant, not a legacy-player or renderer check."""
def validate_context(context, scene):
    camera=context['cached_viewport']
    view=context['active_view'];flags=context['known_overlays']
    expected=(view in ('settlement','settlement_battle','battle','world')
              and (view!='world' or scene['world_generation']['is_done'])
              and not flags['management_screen'] and not flags['loading'])
    assert camera['available'] is expected
    if not expected:
        assert camera['coverage']=='unavailable' and camera['data'] is None and camera['reason']
        return
    assert camera['coverage']=='partial' and camera['reason'] is None
    assert camera['coordinate_scope']==('campaign_world_tiles' if view=='world' else 'instantiated_settlement_tiles')
    assert camera['ui_hidden']==context['ui_hidden']
    assert camera['cache_age_known'] is camera['rendered_visibility_known'] is False
    assert type(camera['data']['zoomout']) is int
    for field in ('tiles','pixels','screen','map_bounds_tiles'):
        rect=camera['data'][field]
        assert len(rect)==4 and all(type(v) is int for v in rect)
    assert camera['data']['map_bounds_tiles'][:2]==[0,0]
