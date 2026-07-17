import backend_server

app = backend_server.app

print("\n====== Flask Routes ======")
for rule in app.url_map.iter_rules():
    print(f"{rule.rule} -> {rule.endpoint} [{', '.join(rule.methods)}]")

# Search for PLC routes
plc_routes = [rule for rule in app.url_map.iter_rules() if 'plc' in rule.rule]
print(f"\n====== PLC Routes ({len(plc_routes)}) ======")
for route in plc_routes:
    print(f"✓ {route.rule} -> {route.endpoint}")
