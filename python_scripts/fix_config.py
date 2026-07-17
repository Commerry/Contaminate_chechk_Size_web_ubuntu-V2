import json

config_path = '/home/pi/Desktop/pse-vision/python_scripts/config.json'
with open(config_path) as f:
    cfg = json.load(f)

cfg['network_camera_ip'] = ''
cfg['plc_enabled'] = False
cfg['auto_focus'] = 0          # disable auto-focus (causes single-object focus lock)
cfg['lens_position'] = 130     # manual focus: 0=infinity, 255=macro; 130≈50cm working distance

with open(config_path, 'w') as f:
    json.dump(cfg, f, indent=2)

print('config.json updated:')
print('  network_camera_ip =', repr(cfg['network_camera_ip']))
print('  plc_enabled =', cfg['plc_enabled'])
print('  auto_focus =', cfg['auto_focus'])
print('  lens_position =', cfg['lens_position'])
