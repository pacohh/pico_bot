LAYER_REPLACEMENTS = {
    'AlBasrah': 'Al Basrah',
    'BlackCoast': 'Black Coast',
    'FoolsRoad': 'Fool\'s Road',
    'GooseBay': 'Goose Bay',
}


def prettify_layer_name(name: str) -> str:
    # It seems that some mod layers can have spaces in the layer name
    if '_' in name:
        name = name.split('_')
    if ' ' in name:
        name = name.split(' ')

    # Make sure the layer version number is all lower case
    name[-1] = name[-1].lower()

    # Special replacements
    name = ' '.join(name)
    for match, replacement in LAYER_REPLACEMENTS.items():
        name = name.replace(match, replacement)

    return name
