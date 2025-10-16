# parse_ifc.py

import ifcopenshell
import ifcopenshell.util.element as Element
import json

def parse_ifc_to_json(ifc_path):
    model = ifcopenshell.open(ifc_path)

    output = {
        'schema': model.schema,
        'entities': [],
        'relations': []
        }
    
    # Entities
    entity_types = ['IfcWall', 'IfcDoor']
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