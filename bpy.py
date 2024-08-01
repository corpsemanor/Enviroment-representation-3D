import json
import numpy as np
import math
import bpy
import mathutils
from mathutils import Euler, Vector, geometry
from datetime import datetime
import bmesh
import os

with open('D:\\DocuSketch\\Enviroment representation 3D\\data\\80.json', 'r') as file:
    data = json.load(file)

# Load textures
wall_texture_path = 'D:\\DocuSketch\\Enviroment representation 3D\\data\\textures\\brick_wall.png'
floor_texture_path = 'D:\\DocuSketch\\Enviroment representation 3D\\data\\textures\\floor_brown.png'

wall_texture = bpy.data.images.load(wall_texture_path)
floor_texture = bpy.data.images.load(floor_texture_path)

walls = {}
windows = {}
doors = {}

for wall in data['walls']:
    walls[wall['id']] = {"windows":{}, 'doors':{}}

for window in data['windows']:
    windows[window['id']] = {}

for door in data['doors']:
    doors[door['id']] = {}

for corner in data['corners']:
    all_keys = corner.keys()
    if 'wallStarts' in all_keys:
        for wall in corner['wallStarts']:
            walls[wall['id']]['start'] = (corner['x'], corner['y'])
            walls[wall['id']]['thickness'] = wall['thickness']
    if 'wallEnds' in all_keys:
        for wall in corner['wallEnds']:
            walls[wall['id']]['end'] = (corner['x'], corner['y'])
            walls[wall['id']]['thickness'] = wall['thickness']

for window in data['windows']:
    attributes = windows[window['id']]
    attributes["start"] = (window['x1'], window['y1'])
    attributes["end"] = (window['x2'], window['y2'])
    attributes["height"] = window['height']
    attributes["length"] = window['length']
    attributes["height_from_floor"] = window['heightFromFloor']
    walls[window['wall']['id']]["windows"][window['id']] = windows[window['id']]

for door in data['doors']:
    door_id = door['id']
    if door_id not in doors:
        print(f"Door ID {door_id} not found in doors dictionary. Skipping this door.")
        continue
    attributes = doors[door_id]
    attributes["start"] = (door['x1'], door['y1'])
    attributes["end"] = (door['x2'], door['y2'])
    attributes["height"] = door['height']
    attributes["width"] = door['wallWidth']
    attributes["rotation"] = door['angle']
    attributes["radius"] = door['radius']
    attributes["entry_point_height"] = door['entryPointHeight']
    attributes["entry_point_width"] = door['entryPointWidth']
    walls[door['wall']['id']]["doors"][door['id']] = attributes

def cut_window_hole(wall, start, end, height, height_from_floor, length):
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    bpy.ops.mesh.primitive_cube_add(size=2, location=((start[0] + end[0]) / 2, (start[1] + end[1]) / 2, height_from_floor + height / 2))
    hole = bpy.context.object
    hole.scale = (length / 2, wall.scale.y * 1.5, height / 2)
    hole.rotation_euler[2] = angle
    bool_mod = wall.modifiers.new(name="WindowHole", type='BOOLEAN')
    bool_mod.operation = 'DIFFERENCE'
    bool_mod.object = hole
    bpy.context.view_layer.objects.active = wall
    bpy.ops.object.modifier_apply(modifier=bool_mod.name)
    bpy.data.objects.remove(hole, do_unlink=True)

def create_window(start, end, height, height_from_floor, length, wall_thickness, name):
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    bpy.ops.mesh.primitive_cube_add(size=2, location=((start[0] + end[0]) / 2, (start[1] + end[1]) / 2, height_from_floor + height / 2))
    window = bpy.context.object
    window.name = name
    window.scale.x = length / 2
    window.scale.y = wall_thickness / 4
    window.scale.z = height / 2
    window.rotation_euler[2] = angle
    
    mat = bpy.data.materials.new(name="GlassMaterial")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    if bsdf:
        bsdf.inputs['Alpha'].default_value = 0.05
        bsdf.inputs['Base Color'].default_value = (1, 1, 1, 0)
        if 'Transmission' in bsdf.inputs:
            bsdf.inputs['Transmission'].default_value = 0.9
        if 'Roughness' in bsdf.inputs:
            bsdf.inputs['Roughness'].default_value = 0
        if 'IOR' in bsdf.inputs:
            bsdf.inputs['IOR'].default_value = 1.45
    
    if window.data.materials:
        window.data.materials[0] = mat
    else:
        window.data.materials.append(mat)
    return window

def cut_door_hole(wall, start, end, height):

    length = ((end[0] - start[0])**2 + (end[1] - start[1])**2)**0.5
    
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    bpy.ops.mesh.primitive_cube_add(size=2, location=((start[0] + end[0]) / 2, (start[1] + end[1]) / 2, height / 2))
    hole = bpy.context.object
    hole.scale = (length / 2, wall.scale.y, height / 2)
    hole.rotation_euler[2] = angle
    bool_mod = wall.modifiers.new(name="DoorHole", type='BOOLEAN')
    bool_mod.operation = 'DIFFERENCE'
    bool_mod.object = hole
    bpy.context.view_layer.objects.active = wall
    bpy.ops.object.modifier_apply(modifier=bool_mod.name)
    bpy.data.objects.remove(hole, do_unlink=True)

def create_door(wall, start, end, height, rotation, radius, wall_thickness, entry_point_height, entry_point_width, direction=-1):
    # НЕ ДОРАБОТАНА!
    length = ((end[0] - start[0])**2 + (end[1] - start[1])**2)**0.5
    # door_thickness = wall_thickness
    
    # Calculate the location and dimensions of the door
    location_z = height / 2
    if start[0] == end[0]:  # если True, то стена с дверью будет вертикальной в 2D
        location_x = start[0] + wall_thickness / 2 + length / 2  # Мы расширяем стену по оси X 
        
        if start[1] > end[1]:  # Если True, то располагаем дверь снизу
            location_y = start[1] + wall_thickness / 4
            
        else:
            location_y = end[1] + wall_thickness / 4
        location = (location_x, location_y, location_z)
        dimensions = (length, wall_thickness / 2, height)
    else:
        location_y = start[1] + wall_thickness / 2 + length / 2  # Мы расширяем стену по оси Y
        
        if start[0] < end[0]:  # Если True, то располагаем дверь снизу
            
            location_x = end[0] + wall_thickness / 4
        else:
            location_x = start[0] + wall_thickness / 4
        location = (location_x, location_y, location_z)
        dimensions = (wall_thickness / 2, length, height)
    
    # Calculate the location and dimensions of the door
    # location = (location_x, location_y, location_z)
    
    # Calculate the dimensions
    # dimensions = (length, wall_thickness / 2, height)  # 0.1 is the thickness of the door
    
    # Add a cube to represent the door
    bpy.ops.mesh.primitive_cube_add(size=2, location=location)
    door = bpy.context.object
    
     # Move the origin to one side of the door (e.g., the negative X side)
    # bpy.context.view_layer.objects.active = door
    # bpy.ops.object.origin_set(type='ORIGIN_CURSOR', center='BOUNDS')
    door.scale = (dimensions[0] /2, dimensions[1] / 2, dimensions[2] / 2)
    
    
    # door.location = (start[0], start[1]*0.5, height / 2)
    
    # Rotate the door to be 90 degrees to the wall
    door.rotation_euler[2] = math.radians(90 + 90 * direction)
    
    # Add a material to the door
    mat = bpy.data.materials.new(name="DoorMaterial")
    mat.diffuse_color = (0.6, 0.3, 0.1, 1)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    if bsdf:
        bsdf.inputs['Base Color'].default_value = (0.6, 0.3, 0.1, 1)  # Brown color
        bsdf.inputs['Roughness'].default_value = 0.5  # Some roughness for the door surface
    
    if door.data.materials:
        door.data.materials[0] = mat
    else:
        door.data.materials.append(mat)
    
    
    # Добавляем ручку двери
    handle_start = ((start[0] + end[0]) / 2 + length /2, start[1], entry_point_height / 2)
    bpy.ops.mesh.primitive_cylinder_add(radius=entry_point_width / 2, depth=entry_point_height, location=handle_start)
    handle = bpy.context.object

    # Привязываем ручку к двери
    handle.parent = door
    
    return door


#def calculate_camera_height(width, fov):
#    return width / (2 * math.tan(fov / 2))

#def setup_camera(location, height):
#    camera_location = (location[0], location[1], height)
#    
#    bpy.ops.object.camera_add(location=camera_location)
#    cam = bpy.context.object
#    cam.name = 'TopDownCamera'
#    bpy.context.scene.camera = cam

#    cam.rotation_euler = Euler((math.radians(90), 0, math.radians(180)), 'XYZ')
#    
#    cam.data.clip_start = 0.1
#    cam.data.clip_end = 10000
#    
#    for area in bpy.context.screen.areas:
#        if area.type == 'VIEW_3D':
#            override = bpy.context.copy()
#            override['area'] = area
#            override['region'] = area.regions[-1]
#            with bpy.context.temp_override(**override):
#                bpy.ops.view3d.object_as_camera()
#            break
#    
#    return cam


def setup_camera(location):
    bpy.ops.object.camera_add(location=location)
    cam = bpy.context.object
    cam.name = 'TopDownCamera'
    bpy.context.scene.camera = cam

    cam.rotation_euler = Euler((math.radians(0), 0, math.radians(180)), 'XYZ')
    
    cam.data.clip_start = 0.1
    cam.data.clip_end = 10000
    
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            override = bpy.context.copy()
            override['area'] = area
            override['region'] = area.regions[-1]
            with bpy.context.temp_override(**override):
                bpy.ops.view3d.object_as_camera()
            break
    
    return cam

def add_light(location):
    bpy.ops.object.light_add(type='SUN', location=(0, 0, 1000000))
    sun_light = bpy.context.object
    sun_light.name = 'SunLight'
    sun_light.data.energy = 15
    sun_light.rotation_euler = Euler((math.radians(50), math.radians(0), 0), 'XYZ')

    return sun_light

def direction_to_quaternion(direction):
    up = mathutils.Vector((0, 0, 1))
    forward = mathutils.Vector(direction).normalized()
    right = up.cross(forward).normalized()
    up = forward.cross(right).normalized()
    mat = mathutils.Matrix((right, up, forward)).transposed()
    return mat.to_quaternion()

def render_to_png():
    current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = f'D:\\DocuSketch\\Enviroment representation 3D\\render\\render_{current_time}.png'
    bpy.context.scene.render.image_settings.file_format = 'PNG'
    bpy.context.scene.render.filepath = filepath
    bpy.ops.render.render(write_still=True)

def place_furniture(furniture_data):
    for furniture in furniture_data['embeds']:
        furniture_type = furniture['type']
        location = (furniture['x'], furniture['y'], 0)
        
        # Закомментируем импорт объектов из файла
        # furniture_path = f"D:\\DocuSketch\\Enviroment representation 3D\\data\\models\\bed.blend"

        # with bpy.data.libraries.load(furniture_path, link=False) as (data_from, data_to):
        #     data_to.objects = data_from.objects

        # imported_objects = []

        # for obj in data_to.objects:
        #     if obj is not None and obj.type not in {'CAMERA', 'LIGHT'}:
        #         bpy.context.collection.objects.link(obj)
        #         imported_objects.append(obj)

        # if not imported_objects:
        #     continue

        # bpy.ops.object.select_all(action='DESELECT')
        # for obj in imported_objects:
        #     obj.select_set(True)
        # bpy.context.view_layer.objects.active = imported_objects[0]
        # bpy.ops.object.join()

        # combined_object = bpy.context.view_layer.objects.active
        # bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS', center='BOUNDS')

        # Создаем куб вместо импортированного объекта
        bpy.ops.mesh.primitive_cube_add(size=2, location=location)
        combined_object = bpy.context.object

        rect = furniture['rect']['data']['vertices']
        scale_xyz = rect[:3]

        # local_min_z = min(vertex.co.z for vertex in combined_object.data.vertices)

        dims = combined_object.dimensions
        center_offset = (dims.x / 2, dims.y / 2, dims.z / 2)

        combined_object.scale = (abs(scale_xyz[0]), abs(scale_xyz[2]) + 17, abs(scale_xyz[1]))
        combined_object.location = (
            location[0] - center_offset[0],
            location[1] - center_offset[1],
            combined_object.scale[1] * 2
        )
        combined_object.rotation_euler = Euler((math.radians(90), 0, furniture['angle'] + math.radians(180)), 'XYZ')

        combined_object.name = furniture_type

        combined_object.data.materials.clear()

        material = bpy.data.materials.new(name="WhiteMaterial")
        material.diffuse_color = (1, 1, 1, 1)
        combined_object.data.materials.append(material)

def add_ceiling_lights(rooms, wall_height):
    for room in rooms:
        if isinstance(room, dict):
            room = room['corners']
        min_x = min(corner['x'] for corner in room)
        max_x = max(corner['x'] for corner in room)
        min_y = min(corner['y'] for corner in room)
        max_y = max(corner['y'] for corner in room)
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        light_location = (center_x, center_y, wall_height)
        bpy.ops.object.light_add(type='SUN', location=light_location)
        ceiling_light = bpy.context.object
        ceiling_light.name = f'CeilingLight_{center_x}_{center_y}'
        ceiling_light.data.energy = 0.3
        ceiling_light.rotation_euler = Euler((math.radians(0), 0, 0), 'XYZ')

# def create_floor(room_corners, name, thickness=1, scale=(1, 1)):
#     min_x = min(corner['x'] + 7.5 for corner in room_corners)
#     max_x = max(corner['x'] - 7.5 for corner in room_corners)
#     min_y = min(corner['y'] + 7.5 for corner in room_corners)
#     max_y = max(corner['y'] - 7.5 for corner in room_corners)
    
#     bpy.ops.mesh.primitive_cube_add(size=2, location=((min_x + max_x) / 2, (min_y + max_y) / 2, (thickness / 2) + 0.4 ))
#     floor = bpy.context.object
#     floor.name = name
#     floor.scale = ((max_x - min_x) / 2, (max_y - min_y) / 2, thickness / 2)
    
#     # Создание материала пола с текстурой
#     mat = bpy.data.materials.new(name="FloorMaterial")
#     mat.use_nodes = True
#     bsdf = mat.node_tree.nodes.get("Principled BSDF")
#     if bsdf:
#         tex_image = mat.node_tree.nodes.new('ShaderNodeTexImage')
#         tex_image.image = bpy.data.images.load(floor_texture_path)  # Замените на путь к вашей текстуре
#         tex_mapping = mat.node_tree.nodes.new('ShaderNodeMapping')
#         tex_coord = mat.node_tree.nodes.new('ShaderNodeTexCoord')
        
#         # Настройка масштаба для плитки текстуры
#         tex_mapping.inputs['Scale'].default_value[0] = scale[0]
#         tex_mapping.inputs['Scale'].default_value[1] = scale[1]

#         mat.node_tree.links.new(tex_coord.outputs['UV'], tex_mapping.inputs['Vector'])
#         mat.node_tree.links.new(tex_mapping.outputs['Vector'], tex_image.inputs['Vector'])
#         mat.node_tree.links.new(bsdf.inputs['Base Color'], tex_image.outputs['Color'])
    
#     if floor.data.materials:
#         floor.data.materials[0] = mat
#     else:
#         floor.data.materials.append(mat)
    
#     # Применение UV-карт для корректировки текстуры
#     bpy.context.view_layer.objects.active = floor
#     bpy.ops.object.mode_set(mode='EDIT')
#     bpy.ops.uv.cube_project(cube_size=1.0)
#     bpy.ops.object.mode_set(mode='OBJECT')
    
#     return floor

def create_floor(room_corners, name, floor_texture_path, thickness=1, scale=(4, 4)):
    # Создаем пустую mesh и объект
    mesh = bpy.data.meshes.new(name)
    floor = bpy.data.objects.new(name, mesh)
    
    # Добавляем объект в коллекцию
    bpy.context.collection.objects.link(floor)
    
    # Создаем bmesh для редактирования в режиме объекта
    bm = bmesh.new()
    
    # Добавляем вершины на основе углов комнаты
    verts = [bm.verts.new((corner['x'], corner['y'], 0)) for corner in room_corners]
    
    # Создаем лицо на основе вершин
    face = bm.faces.new(verts)
    bm.to_mesh(mesh)
    
    # Экструдируем поверхность для создания толщины пола
    geom = bmesh.ops.extrude_face_region(bm, geom=[face])
    verts_extruded = [v for v in geom['geom'] if isinstance(v, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, vec=(0, 0, thickness), verts=verts_extruded)
    
    # Обновляем mesh после экструдирования
    bm.to_mesh(mesh)
    bm.free()
    
    # Создание UV-развертки вручную
    uv_layer = mesh.uv_layers.new(name='UVMap')
    bpy.context.view_layer.objects.active = floor
    bpy.ops.object.mode_set(mode='EDIT')
    
    # Выбираем только верхнюю грань
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT')
    
    mesh.update()
    top_face = None
    for poly in mesh.polygons:
        # Находим верхнюю грань по нормали, направленной вверх
        if poly.normal.z == 1:
            top_face = poly.index
            break
    
    if top_face is not None:
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT')
        mesh.polygons[top_face].select = True
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.uv.smart_project(
            angle_limit=66.0, 
            island_margin=0.0, 
            correct_aspect=True, 
            scale_to_bounds=False,
            margin_method='SCALED'
        )
        bpy.ops.mesh.select_all(action='DESELECT')
    
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # Создание материала пола с текстурой
    mat = bpy.data.materials.new(name="FloorMaterial")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    
    if bsdf:
        tex_image = mat.node_tree.nodes.new('ShaderNodeTexImage')
        if os.path.isfile(floor_texture_path):
            tex_image.image = bpy.data.images.load(floor_texture_path)
        else:
            print(f"Error: Texture file '{floor_texture_path}' not found.")
            return
        
        tex_mapping = mat.node_tree.nodes.new('ShaderNodeMapping')
        tex_coord = mat.node_tree.nodes.new('ShaderNodeTexCoord')
        
        # Настройка масштаба для плитки текстуры
        tex_mapping.inputs['Scale'].default_value[0] = scale[0]
        tex_mapping.inputs['Scale'].default_value[1] = scale[1]

        # Связывание узлов
        mat.node_tree.links.new(tex_coord.outputs['UV'], tex_mapping.inputs['Vector'])
        mat.node_tree.links.new(tex_mapping.outputs['Vector'], tex_image.inputs['Vector'])
        mat.node_tree.links.new(tex_image.outputs['Color'], bsdf.inputs['Base Color'])
    
    # Добавление материала к объекту
    if floor.data.materials:
        floor.data.materials[0] = mat
    else:
        floor.data.materials.append(mat)
    
    return floor

def create_wall(start, end, height, thickness, windows, doors, name):
    length = ((end[0] - start[0])**2 + (end[1] - start[1])**2)**0.5
    bpy.ops.mesh.primitive_cube_add(size=2, location=((start[0] + end[0]) / 2, (start[1] + end[1]) / 2, height / 2))
    wall = bpy.context.object
    wall.name = name
    wall.scale = (length / 2, thickness / 2, height / 2)
    wall.rotation_euler[2] = math.atan2(end[1] - start[1], end[0] - start[0])

    for id, window in windows.items():
        cut_window_hole(wall, window['start'], window['end'], window['height'], window['height_from_floor'], window['length'])
        create_window(window['start'], window['end'], window['height'], window['height_from_floor'], window['length'], thickness, f'window_{id}')

    # Creating holes + doors 
    for id, door in doors.items():
        cut_door_hole(wall, door['start'], door['end'], door['height'])
        create_door(wall, door['start'], door['end'], door['height'], door['rotation'], door['radius'], thickness, door['entry_point_height'], door['entry_point_width'])
    
    return wall

def is_near_wall(corner, walls, thickness):
    distance = thickness + 1
    x0, y0 = corner
    directions = [(distance, 0), (-distance, 0), (0, distance), (0, -distance)]
    wall_count = 0

    for dx, dy in directions:
        px, py = x0 + dx, y0 + dy
        for wall in walls:
            if 'start' in wall and 'end' in wall:
                x1, y1 = wall['start']
                x2, y2 = wall['end']
                
                # Проверка, если точка находится на линии стены с учетом толщины
                if x1 == x2:  # Вертикальная стена
                    if min(y1, y2) - wall['thickness'] / 2 <= py <= max(y1, y2) + wall['thickness'] / 2 and \
                       x1 - wall['thickness'] / 2 <= px <= x1 + wall['thickness'] / 2:
                        wall_count += 1
                        break
                elif y1 == y2:  # Горизонтальная стена
                    if min(x1, x2) - wall['thickness'] / 2 <= px <= max(x1, x2) + wall['thickness'] / 2 and \
                       y1 - wall['thickness'] / 2 <= py <= y1 + wall['thickness'] / 2:
                        wall_count += 1
                        break
                else:  # Диагональная стена
                    # Проекция точки на линию стены и вычисление расстояния до линии
                    dx1 = x2 - x1
                    dy1 = y2 - y1
                    dx2 = px - x1
                    dy2 = py - y1
                    t = (dx1 * dx2 + dy1 * dy2) / (dx1 ** 2 + dy1 ** 2)
                    nearest_x = x1 + t * dx1
                    nearest_y = y1 + t * dy1
                    distance_to_wall = math.sqrt((nearest_x - px) ** 2 + (nearest_y - py) ** 2)
                    
                    if distance_to_wall <= wall['thickness'] / 2 and \
                       min(x1, x2) - wall['thickness'] / 2 <= nearest_x <= max(x1, x2) + wall['thickness'] / 2 and \
                       min(y1, y2) - wall['thickness'] / 2 <= nearest_y <= max(y1, y2) + wall['thickness'] / 2:
                        wall_count += 1
                        break

        if wall_count >= 3:
            return True

    return wall_count >= 3

def check_corner_position(corner, walls):
    return is_near_wall(corner, walls)


def create_corner_filler(location, height, thickness, walls):
    if is_near_wall(location, walls, thickness):
        return  # Corner is inside the wall, do not create

    bpy.ops.mesh.primitive_cube_add(size=2, location=(location[0], location[1], height / 2))
    filler = bpy.context.object
    filler.name = "CornerFiller"
    filler.scale = (thickness / 2, thickness / 2, height / 2)
    return filler

def get_wall_thickness_at_corner(corner, walls):
    for wall in walls.values():
        if ('start' in wall and wall['start'] == (corner['x'], corner['y'])) or ('end' in wall and wall['end'] == (corner['x'], corner['y'])):
            return wall['thickness']
    return None

def create_walls_and_corners(data):
    walls = {}
    windows = {}
    doors = {}

    # Инициализация стен, окон и дверей
    for wall in data['walls']:
        walls[wall['id']] = {"windows":{}, 'doors':{}}

    for window in data['windows']:
        windows[window['id']] = {}

    for door in data['doors']:
        doors[door['id']] = {}
    
    # Заполнение данных о началах и концах стен
    for corner in data['corners']:
        all_keys = corner.keys()
        if 'wallStarts' in all_keys:
            for wall in corner['wallStarts']:
                walls[wall['id']]['start'] = (corner['x'], corner['y'])
                walls[wall['id']]['thickness'] = wall['thickness']
        if 'wallEnds' in all_keys:
            for wall in corner['wallEnds']:
                walls[wall['id']]['end'] = (corner['x'], corner['y'])
                walls[wall['id']]['thickness'] = wall['thickness']

    # Заполнение данных об окнах
    for window in data['windows']:
        attributes = windows[window['id']]
        attributes["start"] = (window['x1'], window['y1'])
        attributes["end"] = (window['x2'], window['y2'])
        attributes["height"] = window['height']
        attributes["length"] = window['length']
        attributes["height_from_floor"] = window['heightFromFloor']
        walls[window['wall']['id']]["windows"][window['id']] = windows[window['id']]

    # Заполнение данных о дверях
    for door in data['doors']:
        door_id = door['id']
        if door_id not in doors:
            print(f"Door ID {door_id} not found in doors dictionary. Skipping this door.")
            continue
        attributes = doors[door_id]
        attributes["start"] = (door['x1'], door['y1'])
        attributes["end"] = (door['x2'], door['y2'])
        attributes["height"] = door['height']
        attributes["width"] = door['wallWidth']
        attributes["rotation"] = door['angle']
        attributes["radius"] = door['radius']
        attributes["entry_point_height"] = door['entryPointHeight']
        attributes["entry_point_width"] = door['entryPointWidth']
        walls[door['wall']['id']]["doors"][door['id']] = attributes

    # Создание стен
    for id, wall in walls.items():
        start = (wall['start'][0], wall['start'][1])
        end = (wall['end'][0], wall['end'][1])
        height = data['settings']['wallsHeight']
        thickness = wall['thickness']
        windows = wall['windows']
        doors = wall['doors']
        create_wall(start, end, height, thickness, windows, doors, f'wall_{id}')
    
    # Создание угловых объектов, если они действительно угловые
    for corner in data['corners']:
        location = (corner['x'], corner['y'])
        height = data['settings']['wallsHeight']
        thickness = get_wall_thickness_at_corner(corner, walls)
        if thickness:
            create_corner_filler(location, height, thickness, walls.values())

    # Применение Boolean Union для объединения пересекающихся объектов
    bpy.ops.object.select_all(action='DESELECT')
    objects_to_union = [obj for obj in bpy.context.scene.objects if obj.name.startswith("wall_")]

    # Применение трансформаций к объектам
    for obj in objects_to_union:
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    while len(objects_to_union) > 1:
        bpy.ops.object.select_all(action='DESELECT')
        obj1 = objects_to_union.pop(0)
        obj2 = objects_to_union.pop(0)
        
        obj1.select_set(True)
        obj2.select_set(True)
        bpy.context.view_layer.objects.active = obj1
        
        # Создание временного объекта для объединения
        bpy.ops.object.duplicate()
        temp_obj = bpy.context.selected_objects[0]
        temp_obj.name = "TempUnion"
        
        # Применение модификатора Boolean Union
        mod = temp_obj.modifiers.new(name='Boolean', type='BOOLEAN')
        mod.operation = 'UNION'
        mod.object = obj2
        bpy.context.view_layer.objects.active = temp_obj
        bpy.ops.object.modifier_apply(modifier=mod.name)
        
        # Удаление исходных объектов
        bpy.data.objects.remove(obj1, do_unlink=True)
        bpy.data.objects.remove(obj2, do_unlink=True)
        
        # Добавление временного объекта обратно в список
        objects_to_union.append(temp_obj)

    # Переименование финального объекта
    final_obj = objects_to_union[0]
    final_obj.name = "CombinedObject"
    
    # Удаление всех объектов кроме финального и углов
    for obj in bpy.context.scene.objects:
        if 'wall' in obj.name or 'Temp' in obj.name:
            bpy.data.objects.remove(obj, do_unlink=True)
            
    # Применение текстуры к объединенному объекту
    apply_texture_to_combined_object(wall_texture_path, scale=(4, 4, 4))



def is_corner_filler_needed(connected_walls, walls):
    # Список для хранения точек начала и конца стен
    points = []
    for wall in connected_walls:
        wall_id = wall['id']
        start = Vector(walls[wall_id]['start'])
        end = Vector(walls[wall_id]['end'])
        points.append((start, end))

    # Проверка пересечения стен в одной точке (угол)
    for i, (start1, end1) in enumerate(points):
        for j, (start2, end2) in enumerate(points):
            if i >= j:
                continue
            if start1 == start2 or start1 == end2 or end1 == start2 or end1 == end2:
                return True
    return False

def apply_texture_to_combined_object(texture_path, scale=(2, 2, 2)):
    # Создание материала для внутренней текстуры
    inner_material = bpy.data.materials.new(name="InnerTextureMaterial")
    inner_material.use_nodes = True
    bsdf_inner = inner_material.node_tree.nodes.get("Principled BSDF")
    
    # Создание узла текстуры изображения для внутренней текстуры
    tex_image_inner = inner_material.node_tree.nodes.new('ShaderNodeTexImage')
    tex_image_inner.image = bpy.data.images.load(texture_path)
    tex_image_inner.projection = 'BOX'
    tex_image_inner.projection_blend = 0.1  # значение для смешивания проекций

    # Создание узлов для координат и преобразования текстуры для внутренней текстуры
    tex_coord_inner = inner_material.node_tree.nodes.new('ShaderNodeTexCoord')
    tex_mapping_inner = inner_material.node_tree.nodes.new('ShaderNodeMapping')
    tex_mapping_inner.inputs['Scale'].default_value = scale

    # Соединение узлов для внутренней текстуры
    inner_material.node_tree.links.new(tex_coord_inner.outputs['Generated'], tex_mapping_inner.inputs['Vector'])
    inner_material.node_tree.links.new(tex_mapping_inner.outputs['Vector'], tex_image_inner.inputs['Vector'])
    inner_material.node_tree.links.new(tex_image_inner.outputs['Color'], bsdf_inner.inputs['Base Color'])
    
    # Создание внешнего материала без текстуры
    outer_material = bpy.data.materials.new(name="OuterMaterial")
    outer_material.use_nodes = True
    bsdf_outer = outer_material.node_tree.nodes.get("Principled BSDF")
    bsdf_outer.inputs['Base Color'].default_value = (0.8, 0.8, 0.8, 1)  # Серый цвет

    # Применение материалов к объекту
    obj = bpy.context.object
    if obj.type == 'MESH':
        if len(obj.data.materials) < 2:
            obj.data.materials.append(inner_material)
            obj.data.materials.append(outer_material)
        else:
            obj.data.materials[0] = inner_material
            obj.data.materials[1] = outer_material

    # Переключение в режим редактирования
    bpy.ops.object.mode_set(mode='EDIT')
    
    # Использование BMesh для работы с геометрией
    bm = bmesh.from_edit_mesh(obj.data)

    # Поиск объектов пола
    floors = [obj for obj in bpy.data.objects if 'floor' in obj.name.lower()]

    def faces_touch(face1_verts, face2_verts):
        # Преобразование вершин граней в треугольники и проверка пересечения
        for vert1 in face1_verts:
            for vert2 in face2_verts:
                if (vert1 - vert2).length < 7.5:  # Сравнение с небольшим допуском
                    return True
        return False

    def is_face_touching_floor(face):
        face_verts_world = [obj.matrix_world @ v.co for v in face.verts]
        for floor in floors:
            for poly in floor.data.polygons:
                floor_verts_world = [floor.matrix_world @ floor.data.vertices[i].co for i in poly.vertices]
                if faces_touch(face_verts_world, floor_verts_world):
                    return True
        return False

    for face in bm.faces:
        face.select = False  # Сброс выбора всех граней
        
        # Проверка на соприкосновение с полом
        if is_face_touching_floor(face):
            face.material_index = 0  # Применение внутренней текстуры
        else:
            face.material_index = 1  # Применение внешнего материала
    
    # Обновление BMesh и возврат в объектный режим
    bmesh.update_edit_mesh(obj.data)
    bpy.ops.object.mode_set(mode='OBJECT')


print("peenis")

min_x = min(corner['x'] for corner in data['corners'])
max_x = max(corner['x'] for corner in data['corners'])
min_y = min(corner['y'] for corner in data['corners'])
max_y = max(corner['y'] for corner in data['corners'])
center_x = (min_x + max_x) / 2
center_y = (min_y + max_y) / 2
camera_altitude = max(max_x - min_x, max_y - min_y) + 1000

camera_location = (center_x, center_y, camera_altitude)
setup_camera(camera_location)

add_light(camera_location)

place_furniture(data)

rooms = data['rooms']
wall_height = data['settings']['wallsHeight']
add_ceiling_lights(rooms, wall_height)

for i, room in enumerate(data['rooms']):
    room_corners = room['corners']
    create_floor(room_corners, f'floor_{i}', floor_texture_path, scale=(4, 4))

create_walls_and_corners(data)

render_to_png()