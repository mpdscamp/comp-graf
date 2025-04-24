from panda3d.core import Vec3, Vec4, Point3
from direct.interval.IntervalGlobal import (Sequence, Parallel, LerpFunc,
                                             LerpScaleInterval, LerpHprInterval,
                                             LerpColorScaleInterval, LerpColorInterval,
                                             LerpPosInterval, Wait)
import random
import math

def start_pulse_reaction(geometry_np, params):
    if not geometry_np or geometry_np.isEmpty(): return None
    original_scale = geometry_np.getScale()

    speed = params.get('reaction_speed', 1.0)
    strength = params.get('reaction_strength', 1.0)

    pulse_scale = original_scale * (1 + 0.5 * strength)

    pulse_seq = Sequence(
        LerpScaleInterval(
            geometry_np,
            duration=0.5 / max(0.01, speed),
            scale=pulse_scale,
            startScale=original_scale,
            blendType='easeInOut'
        ),
        LerpScaleInterval(
            geometry_np,
            duration=0.5 / max(0.01, speed),
            scale=original_scale,
            startScale=pulse_scale,
            blendType='easeInOut'
        ),
        name=f"pulse_reaction_{geometry_np.getName()}"
    )
    pulse_seq.loop()
    return pulse_seq

def start_rotate_reaction(geometry_np, params):
    if not geometry_np or geometry_np.isEmpty(): return None
    speed = params.get('reaction_speed', 1.0)
    axis = params.get('rotation_axis', 'z')

    hpr_start = geometry_np.getHpr()
    delta_hpr = Vec3(0, 0, 0)

    if axis == 'h': delta_hpr.x = 360
    elif axis == 'p': delta_hpr.y = 360
    elif axis == 'r': delta_hpr.z = 360
    else:
        if random.random() > 0.5: delta_hpr.x = random.choice([-360, 360])
        if random.random() > 0.5: delta_hpr.y = random.choice([-360, 360])
        if random.random() > 0.5: delta_hpr.z = random.choice([-360, 360])
        if delta_hpr == Vec3(0,0,0): delta_hpr.z = 360

    hpr_end = hpr_start + delta_hpr

    max_angle = max(abs(delta_hpr.x), abs(delta_hpr.y), abs(delta_hpr.z))
    if max_angle == 0: max_angle = 360
    base_duration_per_360 = 2.0
    duration = (max_angle / 360.0) * (base_duration_per_360 / max(0.01, speed))

    rotate_seq = Sequence(
        LerpHprInterval(
            geometry_np,
            duration=duration,
            hpr=hpr_end,
            startHpr=hpr_start
        ),
        name=f"rotate_reaction_{geometry_np.getName()}"
    )
    rotate_seq.loop()
    return rotate_seq

def start_color_reaction(geometry_np, params):
    if not geometry_np or geometry_np.isEmpty(): return None

    original_color_val = params.get('color', [0.6, 0.6, 0.9, 1.0])
    target_color_val = params.get('target_color', [1.0, 1.0, 1.0, 1.0])
    speed = params.get('reaction_speed', 1.0)

    original_color = Vec4(*original_color_val) if isinstance(original_color_val, list) else original_color_val
    target_color = Vec4(*target_color_val) if isinstance(target_color_val, list) else target_color_val
    if not isinstance(original_color, Vec4): original_color = Vec4(0.6, 0.6, 0.9, 1.0)
    if not isinstance(target_color, Vec4): target_color = Vec4(1.0, 1.0, 1.0, 1.0)

    geometry_np.setColorScale(Vec4(1,1,1,1))
    geometry_np.setColor(original_color)

    duration = 1.0 / max(0.01, speed)
    color_seq = Sequence(
        LerpColorInterval(
            geometry_np, duration=duration, color=target_color,
            startColor=original_color, blendType='easeInOut'
        ),
        LerpColorInterval(
            geometry_np, duration=duration, color=original_color,
            startColor=target_color, blendType='easeInOut'
        ),
        name=f"color_reaction_{geometry_np.getName()}"
    )
    color_seq.loop()
    return color_seq

def start_float_reaction(root_np, params):
    if not root_np or root_np.isEmpty(): return None
    original_pos = root_np.getPos()
    speed = params.get('reaction_speed', 1.0)
    float_height = params.get('float_height', 5.0)

    target_pos = Point3(original_pos.x, original_pos.y, original_pos.z + float_height)
    duration = 1.5 / max(0.01, speed)

    float_seq = Sequence(
        LerpPosInterval(
            root_np, duration=duration, pos=target_pos,
            startPos=original_pos, blendType='easeInOut'
        ),
        LerpPosInterval(
            root_np, duration=duration, pos=original_pos,
            startPos=target_pos, blendType='easeInOut'
        ),
        name=f"float_reaction_{root_np.getName()}"
    )
    float_seq.loop()
    return float_seq

def start_bounce_reaction(root_np, params):
    if not root_np or root_np.isEmpty(): return None
    original_pos = root_np.getPos()
    speed = params.get('reaction_speed', 1.0)
    bounce_height = params.get('bounce_height', 3.0)

    up_duration = 0.3 / max(0.01, speed)
    down_duration = 0.4 / max(0.01, speed)
    wait_duration = 0.5 / max(0.01, speed)

    bounce_target_pos = Point3(original_pos.x, original_pos.y, original_pos.z + bounce_height)

    bounce_seq = Sequence(
        LerpPosInterval(
            root_np, duration=up_duration, pos=bounce_target_pos,
            startPos=original_pos, blendType='easeOut'
        ),
        LerpPosInterval(
            root_np, duration=down_duration, pos=original_pos,
            startPos=bounce_target_pos, blendType='easeIn'
        ),
         Wait(wait_duration),
         name=f"bounce_reaction_{root_np.getName()}"
    )
    bounce_seq.loop()
    return bounce_seq


def stop_reaction(element_data):
    interval = element_data.get('interval')
    if element_data.get('active') and interval:
        print(f"Stopping reaction: {interval.getName()}")
        interval.finish()
        element_data['interval'] = None
        element_data['active'] = False

        params = element_data.get('params', {})
        reaction_type = element_data.get('type')
        geometry_np = element_data.get('geometry')
        root_np = element_data.get('root')

        if geometry_np and not geometry_np.isEmpty():
            if reaction_type == 'pulse':
                default_size = params.get('size', 1.5)
                geometry_np.setScale(default_size)
            elif reaction_type == 'color':
                default_color_val = params.get('color', [0.6, 0.6, 0.9, 1.0])
                default_color = Vec4(*default_color_val) if isinstance(default_color_val, list) else default_color_val
                if not isinstance(default_color, Vec4): default_color = Vec4(0.6, 0.6, 0.9, 1.0)
                geometry_np.setColorScale(Vec4(1,1,1,1))
                geometry_np.setColor(default_color)