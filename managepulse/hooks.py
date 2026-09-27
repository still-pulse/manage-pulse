app_name = "managepulse"
app_title = "ManagePulse"
app_publisher = "Still Pulse"
app_description = "Pesquisas de satisfação multi-unidade (paciente, acompanhante e visitante)"
app_email = "dev@stillpulse.com.br"
app_license = "mit"
app_version = "0.4.0"

required_apps = ["erpnext"]

# after_install / after_migrate: seed de modelos, papéis e dashboard
after_install = "managepulse.setup.install.after_install"
after_migrate = "managepulse.setup.install.after_migrate"

# Desktop / Awesomebar
add_to_apps_screen = [
	{
		"name": "managepulse",
		"title": "Gestor",
		"route": "/app/gestor",
	}
]

# Fixtures exportáveis
fixtures = [
	{
		"dt": "Role",
		"filters": [["name", "in", ["ManagePulse Manager", "ManagePulse Viewer"]]],
	},
	{
		"dt": "Number Card",
		"filters": [["module", "=", "ManagePulse"]],
	},
	{
		"dt": "Dashboard Chart",
		"filters": [["module", "=", "ManagePulse"]],
	},
	{
		"dt": "Dashboard",
		"filters": [["name", "=", "ManagePulse"]],
	},
]

# Página pública (guest) — pesquisa de satisfação
website_route_rules = [
	{"from_route": "/pesquisa-satisfacao/<slug>", "to_route": "pesquisa_satisfacao"},
	{"from_route": "/pesquisa-satisfacao", "to_route": "pesquisa_satisfacao"},
]

# Assets públicos
# (css/js em public/ servidos em /assets/managepulse/...)
