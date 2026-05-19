# Weapon definitions — dict format, consistent with project style

WEAPON_BLADE = {
    "name": "剑",
    "damage": 2,
    "cooldown": 0.35,
    "startup": 0.07,
    "active": 0.12,
    "recovery": 0.12,
    "hitbox_width": 36,
    "hitbox_height": 40,
    "hitbox_offset_x": 20,
    "pierce": False,
    "color": (255, 240, 60),
    "anim_type": "arc",
    "type": "melee",
}

WEAPON_SPEAR = {
    "name": "枪",
    "damage": 2,
    "cooldown": 0.36,
    "startup": 0.06,
    "active": 0.08,
    "recovery": 0.10,
    "hitbox_width": 56,
    "hitbox_height": 28,
    "hitbox_offset_x": 28,
    "pierce": True,
    "color": (60, 240, 240),
    "anim_type": "thrust",
    "type": "melee",
}

WEAPON_GREATSWORD = {
    "name": "斧",
    "damage": 3,
    "cooldown": 0.65,
    "startup": 0.15,
    "active": 0.10,
    "recovery": 0.25,
    "hitbox_width": 40,
    "hitbox_height": 48,
    "hitbox_offset_x": 18,
    "pierce": False,
    "color": (255, 140, 40),
    "anim_type": "overhead",
    "type": "melee",
}

WEAPON_BOW = {
    "name": "弓",
    "damage": 2,
    "cooldown": 0.45,
    "startup": 0.12,
    "active": 0.01,
    "recovery": 0.15,
    "pierce": False,
    "color": (100, 240, 100),
    "anim_type": "shoot",
    "type": "ranged",
}

WEAPONS = [WEAPON_BLADE, WEAPON_SPEAR, WEAPON_GREATSWORD, WEAPON_BOW]
