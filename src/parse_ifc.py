# parse_ifc.py

import ifcopenshell
import ifcopenshell.util.element as Element
import json


import ifcopenshell
import ifcopenshell.geom
from topologicpy.Topology import Topology
from topologicpy.Cell import Cell

def find_topologic_relationships(ifc_file_path, element_types=None):
    """
    Find spatial relationships between IFC elements using TopologicPy
    
    Args:
        ifc_file_path: Path to IFC file
        element_types: List of IFC types to analyze (e.g., ["IfcWall", "IfcDoor", "IfcWindow"])
                      If None, uses common building elements
    
    Returns:
        List of relationship dictionaries with format:
        {"type": "intersects", "from": "GlobalId1", "to": "GlobalId2"}
    """
    settings = ifcopenshell.geom.settings()
    ifc_file = ifcopenshell.open(ifc_file_path)
    
    # Default element types if not specified
    if element_types is None:
        element_types = ["IfcWall", "IfcSlab", "IfcColumn", "IfcBeam", 
                        "IfcDoor", "IfcWindow", "IfcSpace"]
    
    def get_bounding_box_topology(ifc_element):
        """Get bounding box as Topologic cell"""
        try:
            shape = ifcopenshell.geom.create_shape(settings, ifc_element)
            geometry = shape.geometry
            
            # Get bounding box coordinates
            verts = geometry.verts
            xs = [verts[i] for i in range(0, len(verts), 3)]
            ys = [verts[i+1] for i in range(0, len(verts), 3)]
            zs = [verts[i+2] for i in range(0, len(verts), 3)]
            
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            min_z, max_z = min(zs), max(zs)
            
            # Create bounding box cell
            bbox = Cell.ByMinMaxCoordinates(min_x, min_y, min_z, max_x, max_y, max_z)
            return bbox
        except Exception as e:
            print(f"Error creating bbox for {ifc_element.GlobalId}: {e}")
            return None
    
    # Collect all elements with their bounding boxes
    all_elements = []
    
    for element_type in element_types:
        elements = ifc_file.by_type(element_type)
        for element in elements:
            bbox = get_bounding_box_topology(element)
            if bbox:
                all_elements.append({
                    "element": element,
                    "bbox": bbox,
                    "GlobalId": element.GlobalId,
                    "Type": element.is_a()
                })
    
    print(f"Processing {len(all_elements)} elements...")
    
    # Find relationships
    relationships = []
    
    for i, elem1 in enumerate(all_elements):
        for elem2 in all_elements[i+1:]:
            try:
                # Check if bounding boxes intersect
                intersection = Topology.Intersect(elem1["bbox"], elem2["bbox"])
                
                if intersection:
                    volume = Topology.Volume(intersection)
                    
                    # If intersection has significant volume, they intersect
                    if volume > 0.001:  # Threshold to avoid numerical errors
                        relationships.append({
                            "type": "intersects",
                            "from": elem1["GlobalId"],
                            "to": elem2["GlobalId"]
                        })
                    
                    # Check for adjacency (touching but not intersecting)
                    # This would be when they share a face but have minimal volume intersection
                    elif volume < 0.001:
                        # Check if they share topology (adjacent)
                        shared = Topology.SharedTopologies(elem1["bbox"], elem2["bbox"])
                        if shared and len(shared) > 0:
                            relationships.append({
                                "type": "adjacent",
                                "from": elem1["GlobalId"],
                                "to": elem2["GlobalId"]
                            })
            
            except Exception as e:
                # Skip if topology operations fail
                continue
    
    print(f"Found {len(relationships)} relationships")
    return relationships



def parse_ifc_to_json(ifc_path):
    model = ifcopenshell.open(ifc_path)

    output = {
        'schema': model.schema,
        'entities': [],
        'relations': []
        }
    
    # Entities
    entity_types = ['IfcWall', 'IfcDoor', 'IfcWindow']
    for entity_type in entity_types:
        entities = model.by_type(entity_type)
        for entity in entities:
            obj = {
                'id': entity.GlobalId,
                'name': entity.Name,
                'tag': entity.Tag,
            }
            psets = Element.get_psets(entity)
            # Add all properties and quantities as flat key-value pairs
            for pset_name, properties in psets.items():
                for prop_name, prop_value in properties.items():
                # Skip the 'id' key that IfcOpenShell adds
                    if prop_name != 'id':
                        obj[prop_name] = prop_value

            output["entities"].append(obj)

            # Get all inverse relationships
            inverse_attrs = model.get_inverse(entity)

            # Find IfcRelVoidsElement relationships
            voids = [inv for inv in inverse_attrs if inv.is_a() == "IfcRelVoidsElement"]

            # Find the filling objects
            print(voids)
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
    # topology

    return output

result = parse_ifc_to_json("data/sample_2.ifc")

# Save to JSON file
with open("data/json_cr.json", "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2, ensure_ascii=False)