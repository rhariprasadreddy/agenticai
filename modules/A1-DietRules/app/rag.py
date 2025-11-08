# super-light placeholder: maps keywords → guidance snippets
RAG_DB = {
    "diabetes_gi": "Favor low/medium GI foods; pair carbs with protein/fat; limit free sugars.",
    "whole_grains": "Whole grains (oats, brown rice, quinoa) in controlled portions.",
    "legumes": "Lentils/beans lower postprandial glucose; good fiber & protein.",
    "fruits": "Prefer low-GI fruits (berries, apple, pear); avoid juices; watch portions.",
    "fats": "Prefer unsaturated fats (olive oil, nuts); limit sat/trans fats.",
}

def query_hints(keys):
    return [RAG_DB[k] for k in keys if k in RAG_DB]
