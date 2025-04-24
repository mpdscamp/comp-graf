import random
import math
from panda3d.core import (
    NodePath, Point3, Vec4, Vec3, CollisionNode, CollisionSphere, BitMask32
)
from . import reactions
from ..utils import geometry_utils
import copy

class ReactiveManager:

    def __init__(self, app, root_node):
        self.app = app
        self.render = app.render
        self.loader = app.loader
        self.root_node = root_node
        self.reactive_elements = []

        self.react_consts = self.app.settings_manager.constants.get('reactive_elements', {})
        self.collision_consts = self.app.settings_manager.constants.get('collision', {})
        self.proc_geom_consts = self.app.settings_manager.constants.get('procedural_geometry', {})
        self.env_consts = self.app.settings_manager.constants.get('environment', {})


    def create_reactive_element(self, element_type, position, **kwargs):
        element_id = len(self.reactive_elements)
        element_root = self.root_node.attachNewNode(f"reactive_{element_type}_{element_id}")
        element_root.setPos(position)

        default_params_raw = self.react_consts.get('DEFAULT_PARAMS', {})
        params = copy.deepcopy(default_params_raw)
        if 'color' in params and isinstance(params['color'], list):
             params['color'] = Vec4(*params['color'])
        elif 'color' not in params or not isinstance(params['color'], Vec4):
             params['color'] = Vec4(0.6, 0.6, 0.9, 1.0)

        params.update(kwargs)
        if isinstance(params.get('color'), list):
             params['color'] = Vec4(*params['color'])
        if 'target_color' in params and isinstance(params['target_color'], list):
             params['target_color'] = Vec4(*params['target_color'])

        shape_key = params.get('shape', 'sphere')
        sphere_segments = self.proc_geom_consts.get('SPHERE_SEGMENTS', 24)
        cyl_segments = self.proc_geom_consts.get('CYLINDER_SEGMENTS', 24)
        segments = None
        if shape_key == 'sphere': segments = sphere_segments
        elif shape_key == 'cylinder': segments = cyl_segments

        geometry = geometry_utils.get_procedural_shape(
            shape_key, f"reactive_geom_{element_id}",
            segments=segments
        )
        if not geometry:
            element_root.removeNode()
            print(f"Failed to create geometry for reactive element {element_id} (shape: {shape_key})")
            return None

        geometry.reparentTo(element_root)
        geom_scale = params.get('size', 1.0)
        geom_color = params.get('color')
        if not isinstance(geom_color, Vec4):
            geom_color = Vec4(0.6, 0.6, 0.9, 1)
        geometry.setScale(geom_scale)
        geometry.setColor(geom_color)
        geometry.setCollideMask(BitMask32(0))

        trigger_prefix = self.react_consts.get('COLLISION_NODE_PREFIX', 'trigger_')
        trigger_node_name = f"{trigger_prefix}{element_type}_{element_id}"
        trigger_node = CollisionNode(trigger_node_name)
        default_trig_radius = self.react_consts.get('DEFAULT_TRIGGER_RADIUS', 8.0)
        trigger_radius = params.get('trigger_radius', default_trig_radius)
        trigger_sphere = CollisionSphere(0, 0, 0, trigger_radius)
        trigger_node.addSolid(trigger_sphere)

        mask_player = self.collision_consts.get('MASK_PLAYER', BitMask32(2))
        trigger_node.setIntoCollideMask(mask_player)
        trigger_node.setFromCollideMask(BitMask32(0))
        trigger_np = element_root.attachNewNode(trigger_node)

        tag_root = self.react_consts.get('PYTHON_TAG_ROOT', 'element_root')
        tag_geom = self.react_consts.get('PYTHON_TAG_GEOM', 'geometry')
        tag_type = self.react_consts.get('PYTHON_TAG_TYPE', 'reaction_type')
        tag_params = self.react_consts.get('PYTHON_TAG_PARAMS', 'params')
        tag_reactive_flag = self.collision_consts.get('TAG_REACTIVE', 'ReactiveElement')

        trigger_np.setPythonTag(tag_root, element_root)
        trigger_np.setPythonTag(tag_geom, geometry)
        trigger_np.setPythonTag(tag_type, element_type)
        trigger_np.setPythonTag(tag_params, params.copy())
        trigger_np.setPythonTag(tag_reactive_flag, True)

        element_data = {
            'id': element_id, 'root': element_root, 'geometry': geometry,
            'trigger': trigger_np, 'type': element_type,
            'params': params.copy(),
            'active': False, 'interval': None
        }
        self.reactive_elements.append(element_data)

        if hasattr(self.app, 'event_handler') and self.app.event_handler:
             self.app.add_collider_to_main_traverser(trigger_np, self.app.event_handler)
        else:
             print(f"ERROR: Cannot add trigger {trigger_np.getName()} - app.event_handler not found!")

        return element_data


    def populate_reactive_elements(self, static_env_manager, num_elements=30):
        print(f"Populating {num_elements} reactive elements...")
        element_types={'pulse':5,'rotate':4,'color':4,'float':3,'bounce':2}
        weighted_types=[t for t,w in element_types.items() for _ in range(w)]
        created_count=0; attempts=0; max_attempts=num_elements*5

        terrain_size = self.env_consts.get('TERRAIN_SIZE', 200.0)
        half_terrain = terrain_size * 0.5

        while created_count<num_elements and attempts<max_attempts:
            attempts+=1; element_type=random.choice(weighted_types)
            dist=random.uniform(20, half_terrain * 0.9)
            angle=random.uniform(0,2*math.pi)
            x=dist*math.cos(angle); y=dist*math.sin(angle)
            nx=x/half_terrain if half_terrain else 0
            ny=y/half_terrain if half_terrain else 0

            if hasattr(static_env_manager, 'get_terrain_height'):
                 ground_height = static_env_manager.get_terrain_height(nx,ny)
            else:
                 print("Warning: static_env_manager missing get_terrain_height method.")
                 ground_height = 0

            z=ground_height+random.uniform(1.5,10); position=Point3(x,y,z)
            min_dist_sq=10**2
            too_close=any((elem['root'].getPos()-position).lengthSquared()<min_dist_sq for elem in self.reactive_elements)
            if not too_close:
                params_override=self._get_element_params_override(element_type)
                if self.create_reactive_element(element_type,position,**params_override):
                    created_count+=1
        print(f"Reactive elements populated: {created_count}/{num_elements}")

    def _get_element_params_override(self, element_type):
        params = {}; shape_choices = ['sphere', 'cube', 'cylinder']
        if element_type == 'pulse':
            params['shape'] = random.choice(shape_choices[:2])
            params['color'] = Vec4(0.8, 0.4, 0.4, 1); params['reaction_speed'] = random.uniform(0.8, 1.5)
        elif element_type == 'rotate':
            params['shape'] = random.choice(shape_choices[1:])
            params['color'] = Vec4(0.4, 0.6, 0.8, 1); params['rotation_axis'] = random.choice(['h', 'p', 'r', 'random'])
        elif element_type == 'color':
            params['shape'] = random.choice(shape_choices)
            params['color'] = Vec4(0.6, 0.8, 0.4, 1); params['target_color'] = Vec4(random.uniform(0.7,1.0), random.uniform(0.7,1.0), random.uniform(0.7,1.0), 1)
        elif element_type == 'float':
            params['shape'] = random.choice(shape_choices[:2])
            params['color'] = Vec4(0.8, 0.7, 0.4, 1); params['float_height'] = random.uniform(3, 8)
        elif element_type == 'bounce':
            params['shape'] = 'sphere'
            params['color'] = Vec4(0.7, 0.4, 0.7, 1); params['bounce_height'] = random.uniform(2, 5)
        if 'color' in params and isinstance(params['color'], list): params['color'] = Vec4(*params['color'])
        if 'target_color' in params and isinstance(params['target_color'], list): params['target_color'] = Vec4(*params['target_color'])
        return params

    def _find_element_data_by_trigger(self, trigger_np):
        for element_data in self.reactive_elements:
            if element_data['trigger'] == trigger_np: return element_data
        return None

    def handle_collision_enter(self, entry):
        tag_reactive_flag = self.collision_consts.get('TAG_REACTIVE', 'ReactiveElement')
        trigger_np = entry.getIntoNodePath().findNetPythonTag(tag_reactive_flag)
        if not trigger_np.isEmpty():
            element_data = self._find_element_data_by_trigger(trigger_np)
            if element_data and not element_data['active']:
                print(f"Player entered trigger: {trigger_np.getName()}")
                reaction_type = element_data['type']
                reaction_func_name = f"start_{reaction_type}_reaction"
                if hasattr(reactions, reaction_func_name):
                    reaction_func = getattr(reactions, reaction_func_name)
                    target_np = element_data['geometry'] if reaction_type in ['pulse','rotate','color'] else element_data['root']
                    interval = reaction_func(target_np, element_data['params'])
                    if interval:
                        element_data['interval'] = interval; element_data['active'] = True
                    else: print(f"Warning: Reaction function {reaction_func_name} did not return an interval.")
                else: print(f"Warning: No reaction function found for type '{reaction_type}' in reactions module.")

    def handle_collision_exit(self, entry):
        tag_reactive_flag = self.collision_consts.get('TAG_REACTIVE', 'ReactiveElement')
        trigger_np = entry.getIntoNodePath().findNetPythonTag(tag_reactive_flag)
        if not trigger_np.isEmpty():
             element_data = self._find_element_data_by_trigger(trigger_np)
             if element_data and element_data['active']:
                 print(f"Player exited trigger: {trigger_np.getName()}")
                 reactions.stop_reaction(element_data)

    def cleanup(self):
        print("Cleaning up reactive manager...")
        for element_data in self.reactive_elements:
            if element_data.get('active') and element_data.get('interval'):
                element_data['interval'].finish()
                element_data['interval'] = None
                element_data['active'] = False
            if element_data.get('trigger') and not element_data['trigger'].isEmpty():
                 if self.app:
                     self.app.remove_collider_from_main_traverser(element_data['trigger'])

            if element_data.get('root') and not element_data['root'].isEmpty():
                element_data['root'].removeNode()

        self.reactive_elements.clear()
        if self.root_node and not self.root_node.isEmpty():
            self.root_node.removeNode()
        self.root_node = None
        print("Reactive manager cleanup complete.")