# Copyright (c) 2026, Still Pulse and contributors
# For license information, please see license.txt

"""Métricas de satisfação (NPS, listagens para filtros e cards)."""

from __future__ import annotations

import frappe
from frappe.utils import cint, flt


def classificar_nps(nps) -> str:
	"""Promotor (9–10), Neutro (7–8), Detrator (0–6)."""
	if nps is None or nps == "":
		return ""
	n = cint(nps)
	if n >= 9:
		return "Promotor"
	if n >= 7:
		return "Neutro"
	return "Detrator"


def calcular_nps_score(nps_values: list[int] | list) -> dict:
	"""
	NPS Score clássico: % promotores − % detratores (escala -100 a 100).
	Retorna score e percentuais.
	"""
	vals = [cint(v) for v in nps_values if v is not None and v != ""]
	total = len(vals)
	if not total:
		return {
			"score": None,
			"total": 0,
			"promotores": 0,
			"neutros": 0,
			"detratores": 0,
			"pct_promotores": 0,
			"pct_neutros": 0,
			"pct_detratores": 0,
		}

	promotores = sum(1 for v in vals if v >= 9)
	neutros = sum(1 for v in vals if 7 <= v <= 8)
	detratores = sum(1 for v in vals if v <= 6)

	pct_p = flt(promotores * 100.0 / total, 1)
	pct_n = flt(neutros * 100.0 / total, 1)
	pct_d = flt(detratores * 100.0 / total, 1)

	return {
		"score": flt(pct_p - pct_d, 1),
		"total": total,
		"promotores": promotores,
		"neutros": neutros,
		"detratores": detratores,
		"pct_promotores": pct_p,
		"pct_neutros": pct_n,
		"pct_detratores": pct_d,
	}


@frappe.whitelist()
def listar_servicos() -> list[str]:
	"""Serviços já usados nas respostas + seções dos modelos ativos."""
	frappe.has_permission("Resposta da Pesquisa", "read", throw=True)

	from_respostas = frappe.db.sql(
		"""
		select distinct servico
		from `tabServico Utilizado da Resposta`
		where ifnull(servico, '') != ''
		order by servico
		"""
	)
	servicos = {r[0] for r in from_respostas}

	# Seções dos modelos (mesmo sem respostas ainda)
	if frappe.db.exists("DocType", "Pergunta do Modelo"):
		from_modelos = frappe.db.sql(
			"""
			select distinct p.secao
			from `tabPergunta do Modelo` p
			inner join `tabModelo de Pesquisa` m on m.name = p.parent
			where ifnull(p.secao, '') != ''
				and ifnull(p.tipo, '') = 'Escala'
				and ifnull(m.ativo, 0) = 1
			order by p.secao
			"""
		)
		servicos.update(r[0] for r in from_modelos)

	return sorted(servicos)


@frappe.whitelist()
def get_nps_score_card(filters=None) -> dict:
	"""Number Card custom: NPS Score consolidado."""
	frappe.has_permission("Resposta da Pesquisa", "read", throw=True)

	rows = frappe.get_all(
		"Resposta da Pesquisa",
		fields=["nps"],
		filters={"nps": ["is", "set"]},
		limit_page_length=0,
	)
	vals = [cint(r.nps) for r in rows if r.nps is not None]
	score = calcular_nps_score(vals)
	return {
		"value": score["score"] if score["score"] is not None else 0,
		"fieldtype": "Float",
		"route": ["query-report", "Analise de Satisfacao"],
	}
