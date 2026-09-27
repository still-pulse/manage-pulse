# Copyright (c) 2026, Still Pulse and contributors
# For license information, please see license.txt

"""Instalação, seed de modelos e artefatos de dashboard (Fase 3)."""

from __future__ import annotations

import json

import frappe

from managepulse.setup.seed_modelos import ensure_modelos_upa


ROLES = (
	{
		"role_name": "ManagePulse Manager",
		"desk_access": 1,
	},
	{
		"role_name": "ManagePulse Viewer",
		"desk_access": 1,
	},
)

NUMBER_CARDS = (
	{
		"name": "MP Total Respostas",
		"label": "MP Total Respostas",
		"type": "Document Type",
		"document_type": "Resposta da Pesquisa",
		"function": "Count",
		"filters_json": "[]",
		"show_percentage_stats": 1,
		"stats_time_interval": "Monthly",
	},
	{
		"name": "MP Média NPS",
		"label": "MP Média NPS",
		"type": "Document Type",
		"document_type": "Resposta da Pesquisa",
		"function": "Average",
		"aggregate_function_based_on": "nps",
		"filters_json": "[]",
	},
	{
		"name": "MP Média Geral",
		"label": "MP Média Geral",
		"type": "Document Type",
		"document_type": "Resposta da Pesquisa",
		"function": "Average",
		"aggregate_function_based_on": "media_geral",
		"filters_json": "[]",
	},
	{
		"name": "MP Pedidos de Contato",
		"label": "MP Pedidos de Contato",
		"type": "Document Type",
		"document_type": "Resposta da Pesquisa",
		"function": "Count",
		"filters_json": '[["Resposta da Pesquisa","deseja_contato","=",1]]',
		"color": "#EC864B",
	},
	{
		"name": "MP NPS Score",
		"label": "MP NPS Score",
		"type": "Custom",
		"method": "managepulse.api.metrics.get_nps_score_card",
	},
)

DASHBOARD_CHARTS = (
	{
		"name": "MP Respostas por Unidade",
		"chart_name": "MP Respostas por Unidade",
		"chart_type": "Group By",
		"document_type": "Resposta da Pesquisa",
		"group_by_based_on": "company",
		"group_by_type": "Count",
		"number_of_groups": 12,
		"type": "Donut",
		"filters_json": "[]",
	},
	{
		"name": "MP Respostas no Tempo",
		"chart_name": "MP Respostas no Tempo",
		"chart_type": "Count",
		"document_type": "Resposta da Pesquisa",
		"based_on": "data_resposta",
		"time_interval": "Monthly",
		"timespan": "Last Year",
		"timeseries": 1,
		"type": "Line",
		"color": "#5e64ff",
		"filters_json": "[]",
	},
	{
		"name": "MP NPS Médio por Unidade",
		"chart_name": "MP NPS Médio por Unidade",
		"chart_type": "Group By",
		"document_type": "Resposta da Pesquisa",
		"group_by_based_on": "company",
		"group_by_type": "Average",
		"aggregate_function_based_on": "nps",
		"number_of_groups": 12,
		"type": "Bar",
		"color": "#28a745",
		"filters_json": "[]",
	},
	{
		"name": "MP Respostas por Canal",
		"chart_name": "MP Respostas por Canal",
		"chart_type": "Group By",
		"document_type": "Resposta da Pesquisa",
		"group_by_based_on": "canal",
		"group_by_type": "Count",
		"number_of_groups": 5,
		"type": "Pie",
		"filters_json": "[]",
	},
)

DASHBOARD_CARDS = (
	"MP Total Respostas",
	"MP NPS Score",
	"MP Média NPS",
	"MP Média Geral",
	"MP Pedidos de Contato",
)

DASHBOARD_CHART_LINKS = (
	("MP Respostas por Unidade", "Half"),
	("MP NPS Médio por Unidade", "Half"),
	("MP Respostas no Tempo", "Half"),
	("MP Respostas por Canal", "Half"),
)


def after_install():
	ensure_roles()
	_safe_seed()
	_safe_dashboard()
	_safe_gestor_workspace()


def after_migrate():
	ensure_roles()
	_safe_seed()
	_safe_dashboard()
	_safe_gestor_workspace()


def _safe_seed():
	if not frappe.db.exists("DocType", "Modelo de Pesquisa"):
		return
	try:
		ensure_modelos_upa()
	except Exception:
		frappe.log_error(title="ManagePulse seed modelos", message=frappe.get_traceback())


def _safe_dashboard():
	if not frappe.db.exists("DocType", "Resposta da Pesquisa"):
		return
	try:
		ensure_dashboard_artifacts()
	except Exception:
		frappe.log_error(
			title="ManagePulse seed dashboard",
			message=frappe.get_traceback(),
		)


def _safe_gestor_workspace():
	"""Mescla atalhos no Workspace Gestor e oculta o workspace ManagePulse."""
	try:
		ensure_gestor_workspace()
	except Exception:
		frappe.log_error(
			title="ManagePulse seed workspace Gestor",
			message=frappe.get_traceback(),
		)


# Atalhos e links da pesquisa de satisfação (integrados no Workspace Gestor)
GESTOR_SHORTCUTS = (
	{
		"label": "Modelos de Pesquisa",
		"link_to": "Modelo de Pesquisa",
		"type": "DocType",
		"doc_view": "List",
		"color": "Blue",
	},
	{
		"label": "Respostas da Pesquisa",
		"link_to": "Resposta da Pesquisa",
		"type": "DocType",
		"doc_view": "List",
		"color": "Green",
	},
	{
		"label": "Analise de Satisfacao",
		"link_to": "Analise de Satisfacao",
		"type": "Report",
		"color": "Purple",
	},
	{
		"label": "Satisfacao por Criterio",
		"link_to": "Satisfacao por Criterio",
		"type": "Report",
		"color": "Cyan",
	},
	{
		"label": "Dashboard Satisfação",
		"link_to": "ManagePulse",
		"type": "Dashboard",
		"color": "Orange",
	},
)

GESTOR_LINKS = (
	{
		"type": "Card Break",
		"label": "Satisfação",
		"link_count": 4,
	},
	{
		"type": "Link",
		"label": "Modelo de Pesquisa",
		"link_type": "DocType",
		"link_to": "Modelo de Pesquisa",
		"is_query_report": 0,
		"onboard": 1,
	},
	{
		"type": "Link",
		"label": "Resposta da Pesquisa",
		"link_type": "DocType",
		"link_to": "Resposta da Pesquisa",
		"is_query_report": 0,
		"onboard": 1,
	},
	{
		"type": "Link",
		"label": "Análise de Satisfação",
		"link_type": "Report",
		"link_to": "Analise de Satisfacao",
		"is_query_report": 1,
		"onboard": 1,
	},
	{
		"type": "Link",
		"label": "Satisfação por Critério",
		"link_type": "Report",
		"link_to": "Satisfacao por Criterio",
		"is_query_report": 1,
		"onboard": 1,
	},
)

GESTOR_CONTENT_SHORTCUTS = (
	{"id": "mp_hdr_sat", "type": "header", "data": {"text": '<span class="h4"><b>Satisfação</b></span>', "col": 12}},
	{"id": "mp_sc_modelo", "type": "shortcut", "data": {"shortcut_name": "Modelos de Pesquisa", "col": 3}},
	{"id": "mp_sc_resp", "type": "shortcut", "data": {"shortcut_name": "Respostas da Pesquisa", "col": 3}},
	{"id": "mp_sc_analise", "type": "shortcut", "data": {"shortcut_name": "Analise de Satisfacao", "col": 3}},
	{"id": "mp_sc_crit", "type": "shortcut", "data": {"shortcut_name": "Satisfacao por Criterio", "col": 3}},
	{"id": "mp_sc_dash", "type": "shortcut", "data": {"shortcut_name": "Dashboard Satisfação", "col": 3}},
)


def ensure_gestor_workspace():
	"""
	Coloca atalhos/links da pesquisa no Workspace Gestor (site) e oculta
	o workspace ManagePulse, para existir só um ponto de entrada no menu.
	"""
	# Oculta workspace próprio do app (se existir)
	if frappe.db.exists("Workspace", "ManagePulse"):
		frappe.db.set_value("Workspace", "ManagePulse", "is_hidden", 1, update_modified=False)

	if not frappe.db.exists("Workspace", "Gestor"):
		return

	doc = frappe.get_doc("Workspace", "Gestor")
	changed = False

	# --- shortcuts ---
	existing_labels = {s.label for s in (doc.shortcuts or [])}
	for sc in GESTOR_SHORTCUTS:
		if sc["label"] in existing_labels:
			continue
		row = {
			"label": sc["label"],
			"link_to": sc["link_to"],
			"type": sc["type"],
			"color": sc.get("color") or "Grey",
		}
		if sc.get("doc_view"):
			row["doc_view"] = sc["doc_view"]
		doc.append("shortcuts", row)
		changed = True

	# --- links (card Satisfação) ---
	existing_link_labels = {lk.label for lk in (doc.links or [])}
	if "Satisfação" not in existing_link_labels:
		for lk in GESTOR_LINKS:
			doc.append("links", dict(lk))
			changed = True

	# --- content blocks (atalhos visíveis na home do Gestor) ---
	try:
		content = json.loads(doc.content or "[]")
	except json.JSONDecodeError:
		content = []

	existing_ids = {b.get("id") for b in content if isinstance(b, dict)}
	if "mp_hdr_sat" not in existing_ids:
		# Insere antes do spacer / módulo, ou no final
		insert_at = None
		for i, block in enumerate(content):
			if block.get("type") == "spacer" or (
				block.get("type") == "header"
				and "Módulo" in (block.get("data") or {}).get("text", "")
			):
				insert_at = i
				break
		new_blocks = list(GESTOR_CONTENT_SHORTCUTS)
		if insert_at is None:
			content.extend(new_blocks)
		else:
			content = content[:insert_at] + new_blocks + content[insert_at:]
		doc.content = json.dumps(content, ensure_ascii=False)
		changed = True

	if changed:
		doc.flags.ignore_links = True
		doc.flags.ignore_permissions = True
		doc.save(ignore_permissions=True)
		frappe.db.commit()


def ensure_roles():
	for role in ROLES:
		if frappe.db.exists("Role", role["role_name"]):
			continue
		doc = frappe.get_doc(
			{
				"doctype": "Role",
				"role_name": role["role_name"],
				"desk_access": role["desk_access"],
			}
		)
		doc.insert(ignore_permissions=True)


def ensure_dashboard_artifacts():
	"""Cria Number Cards, Charts e Dashboard se ainda não existirem."""
	for card in NUMBER_CARDS:
		_ensure_number_card(card)
	for chart in DASHBOARD_CHARTS:
		_ensure_dashboard_chart(chart)
	_ensure_dashboard()
	frappe.db.commit()


def _ensure_number_card(spec: dict):
	name = spec["name"]
	if frappe.db.exists("Number Card", name):
		return

	doc = frappe.get_doc(
		{
			"doctype": "Number Card",
			"name": name,
			"label": spec.get("label") or name,
			"type": spec["type"],
			"is_public": 1,
			"module": "ManagePulse",
			"show_percentage_stats": spec.get("show_percentage_stats", 0),
			"stats_time_interval": spec.get("stats_time_interval") or "Daily",
		}
	)

	if spec["type"] == "Document Type":
		doc.document_type = spec["document_type"]
		doc.function = spec.get("function") or "Count"
		doc.filters_json = spec.get("filters_json") or "[]"
		if spec.get("aggregate_function_based_on"):
			doc.aggregate_function_based_on = spec["aggregate_function_based_on"]
		if spec.get("color"):
			doc.color = spec["color"]
	elif spec["type"] == "Custom":
		doc.method = spec["method"]

	doc.insert(ignore_permissions=True)


def _ensure_dashboard_chart(spec: dict):
	name = spec["name"]
	if frappe.db.exists("Dashboard Chart", name):
		return

	doc = frappe.get_doc(
		{
			"doctype": "Dashboard Chart",
			"name": name,
			"chart_name": spec.get("chart_name") or name,
			"chart_type": spec["chart_type"],
			"document_type": spec["document_type"],
			"type": spec.get("type") or "Bar",
			"is_public": 1,
			"module": "ManagePulse",
			"filters_json": spec.get("filters_json") or "[]",
			"use_report_chart": 0,
		}
	)

	if spec.get("group_by_based_on"):
		doc.group_by_based_on = spec["group_by_based_on"]
		doc.group_by_type = spec.get("group_by_type") or "Count"
		doc.number_of_groups = spec.get("number_of_groups") or 10
	if spec.get("aggregate_function_based_on"):
		doc.aggregate_function_based_on = spec["aggregate_function_based_on"]
	if spec.get("based_on"):
		doc.based_on = spec["based_on"]
		doc.timeseries = 1
		doc.time_interval = spec.get("time_interval") or "Monthly"
		doc.timespan = spec.get("timespan") or "Last Year"
	if spec.get("color"):
		doc.color = spec["color"]

	doc.insert(ignore_permissions=True)


def _ensure_dashboard():
	name = "ManagePulse"
	if frappe.db.exists("Dashboard", name):
		# Garante vínculos se o dashboard já existir vazio
		doc = frappe.get_doc("Dashboard", name)
		existing_cards = {c.card for c in doc.cards}
		existing_charts = {c.chart for c in doc.charts}
		changed = False
		for card in DASHBOARD_CARDS:
			if card not in existing_cards and frappe.db.exists("Number Card", card):
				doc.append("cards", {"card": card})
				changed = True
		for chart, width in DASHBOARD_CHART_LINKS:
			if chart not in existing_charts and frappe.db.exists("Dashboard Chart", chart):
				doc.append("charts", {"chart": chart, "width": width})
				changed = True
		if changed:
			doc.save(ignore_permissions=True)
		return

	doc = frappe.get_doc(
		{
			"doctype": "Dashboard",
			"dashboard_name": name,
			"name": name,
			"module": "ManagePulse",
			"is_standard": 0,
			"is_default": 0,
		}
	)
	for card in DASHBOARD_CARDS:
		if frappe.db.exists("Number Card", card):
			doc.append("cards", {"card": card})
	for chart, width in DASHBOARD_CHART_LINKS:
		if frappe.db.exists("Dashboard Chart", chart):
			doc.append("charts", {"chart": chart, "width": width})
	doc.insert(ignore_permissions=True)
