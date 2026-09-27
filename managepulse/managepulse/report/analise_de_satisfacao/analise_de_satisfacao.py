# Copyright (c) 2026, Still Pulse and contributors
# For license information, please see license.txt

"""Relatório consolidado de respostas da pesquisa de satisfação."""

from __future__ import annotations

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate

from managepulse.api.metrics import calcular_nps_score, classificar_nps


def execute(filters=None):
	filters = frappe._dict(filters or {})
	_validar_filtros(filters)

	visao = filters.get("visao") or "Respostas"
	if visao == "Por Unidade":
		columns = _columns_por_unidade()
		data = _data_por_unidade(filters)
		chart = _chart_por_unidade(data)
	elif visao == "Por Serviço":
		columns = _columns_por_servico()
		data = _data_por_servico(filters)
		chart = _chart_por_servico(data)
	else:
		columns = _columns_respostas()
		data = _data_respostas(filters)
		chart = _chart_respostas(data)

	summary = _summary_global(filters)
	return columns, data, None, chart, summary


def _validar_filtros(filters):
	if filters.get("from_date") and filters.get("to_date"):
		if getdate(filters.from_date) > getdate(filters.to_date):
			frappe.throw(_("A data inicial não pode ser maior que a data final."))


def _base_conditions(filters) -> tuple[str, dict]:
	conditions = ["1=1"]
	values: dict = {}

	if filters.get("from_date"):
		conditions.append("r.data_resposta >= %(from_date)s")
		values["from_date"] = filters.from_date
	if filters.get("to_date"):
		conditions.append("r.data_resposta <= %(to_date)s")
		values["to_date"] = filters.to_date
	if filters.get("company"):
		conditions.append("r.company = %(company)s")
		values["company"] = filters.company
	if filters.get("modelo"):
		conditions.append("r.modelo = %(modelo)s")
		values["modelo"] = filters.modelo
	if filters.get("tipo_pesquisa"):
		conditions.append("r.tipo_pesquisa = %(tipo_pesquisa)s")
		values["tipo_pesquisa"] = filters.tipo_pesquisa
	if filters.get("canal"):
		conditions.append("r.canal = %(canal)s")
		values["canal"] = filters.canal
	if filters.get("status"):
		conditions.append("r.status = %(status)s")
		values["status"] = filters.status
	if filters.get("servico"):
		conditions.append(
			"""exists (
				select 1 from `tabServico Utilizado da Resposta` s
				where s.parent = r.name and s.servico = %(servico)s
			)"""
		)
		values["servico"] = filters.servico

	return " and ".join(conditions), values


def _columns_respostas():
	return [
		{
			"label": _("Resposta"),
			"fieldname": "name",
			"fieldtype": "Link",
			"options": "Resposta da Pesquisa",
			"width": 130,
		},
		{
			"label": _("Data"),
			"fieldname": "data_resposta",
			"fieldtype": "Date",
			"width": 100,
		},
		{
			"label": _("Unidade"),
			"fieldname": "company",
			"fieldtype": "Link",
			"options": "Company",
			"width": 180,
		},
		{
			"label": _("Modelo"),
			"fieldname": "modelo",
			"fieldtype": "Link",
			"options": "Modelo de Pesquisa",
			"width": 200,
		},
		{
			"label": _("Tipo"),
			"fieldname": "tipo_pesquisa",
			"fieldtype": "Data",
			"width": 120,
		},
		{
			"label": _("Serviços"),
			"fieldname": "servicos",
			"fieldtype": "Data",
			"width": 200,
		},
		{
			"label": _("Canal"),
			"fieldname": "canal",
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"label": _("Status"),
			"fieldname": "status",
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"label": _("NPS"),
			"fieldname": "nps",
			"fieldtype": "Int",
			"width": 70,
		},
		{
			"label": _("Classe NPS"),
			"fieldname": "classe_nps",
			"fieldtype": "Data",
			"width": 100,
		},
		{
			"label": _("Média geral"),
			"fieldname": "media_geral",
			"fieldtype": "Float",
			"width": 100,
			"precision": 2,
		},
		{
			"label": _("Quer contato"),
			"fieldname": "deseja_contato",
			"fieldtype": "Check",
			"width": 100,
		},
		{
			"label": _("Comentários"),
			"fieldname": "comentarios",
			"fieldtype": "Data",
			"width": 250,
		},
	]


def _data_respostas(filters) -> list[dict]:
	where, values = _base_conditions(filters)
	rows = frappe.db.sql(
		f"""
		select
			r.name,
			r.data_resposta,
			r.company,
			r.modelo,
			r.tipo_pesquisa,
			r.canal,
			r.status,
			r.nps,
			r.media_geral,
			r.deseja_contato,
			r.comentarios
		from `tabResposta da Pesquisa` r
		where {where}
		order by r.data_resposta desc, r.creation desc
		""",
		values,
		as_dict=True,
	)

	if not rows:
		return []

	names = [r.name for r in rows]
	servicos_map: dict[str, list[str]] = defaultdict(list)
	for s in frappe.db.sql(
		"""
		select parent, servico
		from `tabServico Utilizado da Resposta`
		where parent in %(names)s
		order by ordem, idx
		""",
		{"names": names},
		as_dict=True,
	):
		if s.servico:
			servicos_map[s.parent].append(s.servico)

	for row in rows:
		row["servicos"] = ", ".join(servicos_map.get(row.name, []))
		row["classe_nps"] = classificar_nps(row.nps)
		if row.get("comentarios") and len(row["comentarios"]) > 120:
			row["comentarios"] = row["comentarios"][:117] + "..."

	return rows


def _columns_por_unidade():
	return [
		{
			"label": _("Unidade"),
			"fieldname": "company",
			"fieldtype": "Link",
			"options": "Company",
			"width": 220,
		},
		{
			"label": _("Respostas"),
			"fieldname": "total",
			"fieldtype": "Int",
			"width": 100,
		},
		{
			"label": _("NPS médio"),
			"fieldname": "nps_medio",
			"fieldtype": "Float",
			"width": 100,
			"precision": 2,
		},
		{
			"label": _("NPS Score"),
			"fieldname": "nps_score",
			"fieldtype": "Float",
			"width": 100,
			"precision": 1,
		},
		{
			"label": _("% Promotores"),
			"fieldname": "pct_promotores",
			"fieldtype": "Percent",
			"width": 110,
		},
		{
			"label": _("% Neutros"),
			"fieldname": "pct_neutros",
			"fieldtype": "Percent",
			"width": 100,
		},
		{
			"label": _("% Detratores"),
			"fieldname": "pct_detratores",
			"fieldtype": "Percent",
			"width": 110,
		},
		{
			"label": _("Média geral"),
			"fieldname": "media_geral",
			"fieldtype": "Float",
			"width": 100,
			"precision": 2,
		},
		{
			"label": _("Quer contato"),
			"fieldname": "pedidos_contato",
			"fieldtype": "Int",
			"width": 110,
		},
	]


def _data_por_unidade(filters) -> list[dict]:
	where, values = _base_conditions(filters)
	rows = frappe.db.sql(
		f"""
		select
			r.company,
			r.nps,
			r.media_geral,
			r.deseja_contato
		from `tabResposta da Pesquisa` r
		where {where}
		""",
		values,
		as_dict=True,
	)

	by_company: dict[str, list] = defaultdict(list)
	for row in rows:
		by_company[row.company or _("(sem unidade)")].append(row)

	out = []
	for company, items in sorted(by_company.items(), key=lambda x: x[0]):
		nps_vals = [cint(i.nps) for i in items if i.nps is not None and i.nps != ""]
		medias = [flt(i.media_geral) for i in items if i.media_geral is not None]
		score = calcular_nps_score(nps_vals)
		out.append(
			{
				"company": company,
				"total": len(items),
				"nps_medio": flt(sum(nps_vals) / len(nps_vals), 2) if nps_vals else None,
				"nps_score": score["score"],
				"pct_promotores": score["pct_promotores"],
				"pct_neutros": score["pct_neutros"],
				"pct_detratores": score["pct_detratores"],
				"media_geral": flt(sum(medias) / len(medias), 2) if medias else None,
				"pedidos_contato": sum(1 for i in items if cint(i.deseja_contato)),
			}
		)

	out.sort(key=lambda r: r["total"], reverse=True)
	return out


def _columns_por_servico():
	return [
		{
			"label": _("Serviço"),
			"fieldname": "servico",
			"fieldtype": "Data",
			"width": 220,
		},
		{
			"label": _("Respostas"),
			"fieldname": "total",
			"fieldtype": "Int",
			"width": 100,
		},
		{
			"label": _("NPS médio"),
			"fieldname": "nps_medio",
			"fieldtype": "Float",
			"width": 100,
			"precision": 2,
		},
		{
			"label": _("NPS Score"),
			"fieldname": "nps_score",
			"fieldtype": "Float",
			"width": 100,
			"precision": 1,
		},
		{
			"label": _("Média critérios"),
			"fieldname": "media_criterios",
			"fieldtype": "Float",
			"width": 120,
			"precision": 2,
		},
		{
			"label": _("Unidades distintas"),
			"fieldname": "unidades",
			"fieldtype": "Int",
			"width": 120,
		},
	]


def _data_por_servico(filters) -> list[dict]:
	where, values = _base_conditions(filters)
	rows = frappe.db.sql(
		f"""
		select
			s.servico,
			r.name as resposta,
			r.company,
			r.nps
		from `tabResposta da Pesquisa` r
		inner join `tabServico Utilizado da Resposta` s on s.parent = r.name
		where {where}
			and ifnull(s.servico, '') != ''
		""",
		values,
		as_dict=True,
	)

	if not rows:
		return []

	# Média dos critérios por resposta+seção (serviço)
	names = list({r.resposta for r in rows})
	media_item: dict[tuple[str, str], list[int]] = defaultdict(list)
	for item in frappe.db.sql(
		"""
		select parent, secao, valor_numerico, avaliacao
		from `tabItem da Resposta`
		where parent in %(names)s
			and ifnull(avaliacao, '') != ''
			and avaliacao != 'Não Utilizou'
			and valor_numerico is not null
		""",
		{"names": names},
		as_dict=True,
	):
		media_item[(item.parent, item.secao)].append(cint(item.valor_numerico))

	by_servico: dict[str, list] = defaultdict(list)
	for row in rows:
		by_servico[row.servico].append(row)

	out = []
	for servico, items in sorted(by_servico.items(), key=lambda x: x[0]):
		nps_vals = [cint(i.nps) for i in items if i.nps is not None and i.nps != ""]
		# dedupe por resposta no NPS (uma resposta pode ter 1 linha por serviço já)
		# já é 1:1 servico-resposta no join
		score = calcular_nps_score(nps_vals)
		vals_crit = []
		for i in items:
			vals_crit.extend(media_item.get((i.resposta, servico), []))
		unidades = {i.company for i in items if i.company}
		out.append(
			{
				"servico": servico,
				"total": len(items),
				"nps_medio": flt(sum(nps_vals) / len(nps_vals), 2) if nps_vals else None,
				"nps_score": score["score"],
				"media_criterios": flt(sum(vals_crit) / len(vals_crit), 2) if vals_crit else None,
				"unidades": len(unidades),
			}
		)

	out.sort(key=lambda r: r["total"], reverse=True)
	return out


def _summary_global(filters) -> list[dict]:
	where, values = _base_conditions(filters)
	rows = frappe.db.sql(
		f"""
		select r.nps, r.media_geral, r.deseja_contato
		from `tabResposta da Pesquisa` r
		where {where}
		""",
		values,
		as_dict=True,
	)

	total = len(rows)
	nps_vals = [cint(r.nps) for r in rows if r.nps is not None and r.nps != ""]
	medias = [flt(r.media_geral) for r in rows if r.media_geral is not None]
	score = calcular_nps_score(nps_vals)
	contatos = sum(1 for r in rows if cint(r.deseja_contato))

	nps_score = score["score"]
	indicator_nps = "Grey"
	if nps_score is not None:
		if nps_score >= 50:
			indicator_nps = "Green"
		elif nps_score >= 0:
			indicator_nps = "Orange"
		else:
			indicator_nps = "Red"

	return [
		{
			"value": total,
			"label": _("Respostas"),
			"datatype": "Int",
			"indicator": "Blue",
		},
		{
			"value": score["score"] if score["score"] is not None else 0,
			"label": _("NPS Score"),
			"datatype": "Float",
			"indicator": indicator_nps,
		},
		{
			"value": flt(sum(nps_vals) / len(nps_vals), 2) if nps_vals else 0,
			"label": _("NPS médio"),
			"datatype": "Float",
			"indicator": "Blue",
		},
		{
			"value": flt(sum(medias) / len(medias), 2) if medias else 0,
			"label": _("Média geral"),
			"datatype": "Float",
			"indicator": "Blue",
		},
		{
			"value": contatos,
			"label": _("Pedidos de contato"),
			"datatype": "Int",
			"indicator": "Orange" if contatos else "Grey",
		},
	]


def _chart_respostas(data: list[dict]) -> dict | None:
	if not data:
		return None

	by_company: dict[str, int] = defaultdict(int)
	for row in data:
		by_company[row.get("company") or _("(sem unidade)")] += 1

	items = sorted(by_company.items(), key=lambda x: x[1], reverse=True)[:12]
	return {
		"data": {
			"labels": [i[0] for i in items],
			"datasets": [{"name": _("Respostas"), "values": [i[1] for i in items]}],
		},
		"type": "bar",
		"colors": ["#5e64ff"],
		"height": 280,
	}


def _chart_por_unidade(data: list[dict]) -> dict | None:
	if not data:
		return None
	top = data[:12]
	return {
		"data": {
			"labels": [d["company"] for d in top],
			"datasets": [
				{
					"name": _("NPS Score"),
					"values": [flt(d.get("nps_score") or 0) for d in top],
				}
			],
		},
		"type": "bar",
		"colors": ["#28a745"],
		"height": 280,
	}


def _chart_por_servico(data: list[dict]) -> dict | None:
	if not data:
		return None
	top = data[:12]
	return {
		"data": {
			"labels": [d["servico"] for d in top],
			"datasets": [
				{
					"name": _("Respostas"),
					"values": [d["total"] for d in top],
				}
			],
		},
		"type": "bar",
		"colors": ["#17a2b8"],
		"height": 280,
	}
