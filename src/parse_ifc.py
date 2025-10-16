# parse_ifc.py

import ifcopenshell
import ifcopenshell.util.element as Element
import json

def parse_ifc_to_json(ifc_path):
    model = ifcopenshell.open(ifc_path)

    output = {
        'schema': model.schema,
        'entities': [],
        'relationshipts': []
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



    # relationships

    # topology

    return output

result = parse_ifc_to_json("data/sample.ifc")

# Save to JSON file
with open("data/json_cr.json", "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2, ensure_ascii=False)