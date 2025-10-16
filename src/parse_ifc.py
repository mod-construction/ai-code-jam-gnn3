import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.element as Element
import ifcopenshell.util.placement as Placement
from topologicpy.Topology import Topology
from topologicpy.Cell import Cell
from topologicpy.Vertex import Vertex
import numpy as np

def get_local_bounding_box(ifc_element, settings):
    """Get bounding box in local coordinates (before transformation)"""
    try:
        # Create shape without applying placement
        shape = ifcopenshell.geom.create_shape(settings, ifc_element)
        geometry = shape.geometry
        verts = geometry.verts
        
        # Get min/max in local coordinates
        xs = [verts[i] for i in range(0, len(verts), 3)]
        ys = [verts[i+1] for i in range(0, len(verts), 3)]
        zs = [verts[i+2] for i in range(0, len(verts), 3)]
        
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        min_z, max_z = min(zs), max(zs)
        
        # Calculate center and dimensions
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        center_z = (min_z + max_z) / 2
        
        width = max_x - min_x
        length = max_y - min_y
        height = max_z - min_z
        
        # Create origin vertex at center
        origin = Vertex.ByCoordinates(center_x, center_y, center_z)
        
        # Create bounding box cell centered at origin
        bbox = Cell.Box(origin=origin, width=width, length=length, height=height)
        
        return bbox
    except Exception as e:
        print(f"Error creating local bbox for {ifc_element.GlobalId}: {e}")
        return None

def get_transformation_matrix(ifc_element):
    """Get the 4x4 transformation matrix from IFC element placement"""
    try:
        # Get the placement matrix
        matrix = ifcopenshell.util.placement.get_local_placement(ifc_element.ObjectPlacement)
        return matrix
    except Exception as e:
        print(f"Error getting transformation for {ifc_element.GlobalId}: {e}")
        return np.identity(4)

def transform_topology(topology, matrix):
    """Apply transformation matrix to a topology"""
    try:
        # Extract translation from 4x4 matrix
        tx, ty, tz = matrix[0][3], matrix[1][3], matrix[2][3]
        
        # Apply translation to topology
        transformed = Topology.Translate(topology, tx, ty, tz)
        
        # Note: For full rotation support, you'd need to decompose the rotation matrix
        # and apply it using Topology.Rotate, but for many cases translation is sufficient
        # If rotation is needed, we can add that functionality
        
        return transformed
    except Exception as e:
        print(f"Error transforming topology: {e}")
        return topology

def parse_ifc_to_json(ifc_path):
    model = ifcopenshell.open(ifc_path)
    
    # Settings without applying transformations initially
    settings = ifcopenshell.geom.settings()
    settings.set(settings.DISABLE_OPENING_SUBTRACTIONS, False)

    output = {
        'schema': model.schema,
        'entities': [],
        'relations': []
    }
    
    # Store element data for topologic analysis
    element_data = []
    
    # Entities
    entity_types = ['IfcWall', 'IfcDoor', 'IfcWindow']
    for entity_type in entity_types:
        entities = model.by_type(entity_type)
        for entity in entities:
            obj = {
                'id': entity.GlobalId,
                'name': entity.Name,
                'tag': entity.Tag,
                'type': entity.is_a()
            }
            psets = Element.get_psets(entity)
            # Add all properties and quantities as flat key-value pairs
            for pset_name, properties in psets.items():
                for prop_name, prop_value in properties.items():
                    # Skip the 'id' key that IfcOpenShell adds
                    if prop_name != 'id':
                        obj[prop_name] = prop_value

            output["entities"].append(obj)

            # Get local bounding box (before transformation)
            local_bbox = get_local_bounding_box(entity, settings)
            
            if local_bbox:
                # Get transformation matrix
                transform_matrix = get_transformation_matrix(entity)
                
                # Apply transformation to bounding box
                world_bbox = transform_topology(local_bbox, transform_matrix)
                
                element_data.append({
                    'GlobalId': entity.GlobalId,
                    'bbox': world_bbox
                })

            # Get all inverse relationships
            inverse_attrs = model.get_inverse(entity)

            # Find IfcRelVoidsElement relationships
            voids = [inv for inv in inverse_attrs if inv.is_a() == "IfcRelVoidsElement"]

            # Find the filling objects
            for void in voids:
                opening = void.RelatedOpeningElement
                
                # Find what fills this opening
                filling = None
                opening_inverses = model.get_inverse(opening)
                for inv in opening_inverses:
                    if inv.is_a() == "IfcRelFillsElement":
                        filling = inv.RelatedBuildingElement
                        break
                
                if filling:
                    # Relationship: filling element voids the wall
                    output["relations"].append({
                        "type": "contained_in",
                        "from": filling.GlobalId,
                        "to": entity.GlobalId
                    })
    
    # Find topologic relationships between transformed bounding boxes
    print(f"Finding topologic relationships for {len(element_data)} elements...")
    
    for i, elem1 in enumerate(element_data):
        print(i, 'checking element ', elem1)
        for elem2 in element_data[i+1:]:
            try:
                # Check if bounding boxes intersect in world coordinates
                intersection = Topology.Intersect(elem1["bbox"], elem2["bbox"])
                
                if intersection:
                    output["relations"].append({
                        "type": "intersects",
                        "from": elem1["GlobalId"],
                        "to": elem2["GlobalId"]
                    })
                    
            except Exception as e:
                # Skip if topology operations fail
                continue
    
    print(f"Found {len(output['relations'])} total relationships")
    
    return output

# Usage
if __name__ == "__main__":
    import json
    
    result = parse_ifc_to_json("data/sample.ifc")
    
    # Save to JSON
    with open("data/json_cr.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"Saved {len(result['entities'])} entities and {len(result['relations'])} relationships")