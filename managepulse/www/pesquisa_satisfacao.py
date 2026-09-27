# Copyright (c) 2026, Still Pulse and contributors
# For license information, please see license.txt

import frappe
from frappe import _


no_cache = 1


def get_context(context):
	"""Página pública standalone (sem chrome do website)."""
	context.no_cache = 1
	context.no_header = 1
	context.no_sidebar = 1
	context.no_breadcrumbs = 1
	context.full_width = 1
	context.show_sidebar = 0

	slug = frappe.form_dict.get("slug") or frappe.form_dict.get("modelo") or ""
	company = frappe.form_dict.get("company") or frappe.form_dict.get("unidade") or ""

	context.slug = slug
	context.company = company
	context.title = _("Pesquisa de Satisfação")
	context.boot = {
		"slug": slug,
		"company": company,
		"csrf_token": frappe.sessions.get_csrf_token(),
		"api_get": "managepulse.api.public_survey.get_modelo_publico",
		"api_send": "managepulse.api.public_survey.enviar_resposta",
	}

	# Meta
	context.metatags = {
		"description": _("Pesquisa de satisfação — Beneficência Hospitalar de Cesário Lange"),
		"robots": "noindex, nofollow",
	}
