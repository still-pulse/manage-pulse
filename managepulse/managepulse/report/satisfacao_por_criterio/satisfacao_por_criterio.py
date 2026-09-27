# Copyright (c) 2026, Still Pulse and contributors
# For license information, please see license.txt

"""Breakdown de avaliações por serviço (seção) e critério."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if filters.get("from_date") and filters.get("to_date"):
		if getdate(filters.from_date) > getdate(filters.to_date):
			frappe.throw(_("A data inicial não pode ser maior que a data final."))

	columns = get_columns()
	data = get_data(filters)
	chart = get_chart(data)
	summary = get_summary(data)
	return columns, data, None, chart, summary


def get_columns():
	return [
		{
			"label": _("Serviço"),
			"fieldname": "secao",
			"fieldtype": "Data",
			"width": 180,
		},
		{
			"label": _("Critério"),
			"fieldname": "criterio",
			"fieldtype": "Data",
			"width": 220,
		},
		{
			"label": _("Avaliações"),
			"fieldname": "total",
			"fieldtype": "Int",
			"width": 100,
		},
		{
			"label": _("Ótimo"),
			"fieldname": "otimo",
			"fieldtype": "Int",
			"width": 80,
		},
		{
			"label": _("Bom"),
			"fieldname": "bom",
			"fieldtype": "Int",
			"width": 70,
		},
		{
			"label": _("Regular"),
			"fieldname": "regular",
			"fieldtype": "Int",
			"width": 80,
		},
		{
			"label": _("Ruim"),
			"fieldname": "ruim",
			"fieldtype": "Int",
			"width": 70,
		},
		{
			"label": _("% Ótimo+Bom"),
			"fieldname": "pct_positivo",
			"fieldtype": "Percent",
			"width": 110,
		},
		{
			"label": _("Média (1–5)"),
			"fieldname": "media",
			"fieldtype": "Float",
			"width": 100,
			"precision": 2,
		},
	]


def _conditions(filters) -> tuple[str, dict]:
	conditions = [
		"ifnull(i.avaliacao, '') != ''",
		"i.avaliacao != 'Não Utilizou'",
	]
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
		conditions.append("i.secao = %(servico)s")
		values["servico"] = filters.servico

	return " and ".join(conditions), values


def get_data(filters) -> list[dict]:
	where, values = _conditions(filters)
	rows = frappe.db.sql(
		f"""
		select
			i.secao,
			i.criterio,
			i.avaliacao,
			i.valor_numerico
		from `tabItem da Resposta` i
		inner join `tabResposta da Pesquisa` r on r.name = i.parent
		where {where}
		""",
		values,
		as_dict=True,
	)

	agg: dict[tuple[str, str], dict] = {}
	for row in rows:
		key = (row.secao or "", row.criterio or "")
		if key not in agg:
			agg[key] = {
				"secao": row.secao,
				"criterio": row.criterio,
				"total": 0,
				"otimo": 0,
				"bom": 0,
				"regular": 0,
				"ruim": 0,
				"soma": 0,
				"com_valor": 0,
			}
		bucket = agg[key]
		bucket["total"] += 1
		av = row.avaliacao
		if av == "Ótimo":
			bucket["otimo"] += 1
		elif av == "Bom":
			bucket["bom"] += 1
		elif av == "Regular":
			bucket["regular"] += 1
		elif av == "Ruim":
			bucket["ruim"] += 1
		if row.valor_numerico is not None:
			bucket["soma"] += cint(row.valor_numerico)
			bucket["com_valor"] += 1

	out = []
	for bucket in agg.values():
		total = bucket["total"] or 1
		positivo = bucket["otimo"] + bucket["bom"]
		out.append(
			{
				"secao": bucket["secao"],
				"criterio": bucket["criterio"],
				"total": bucket["total"],
				"otimo": bucket["otimo"],
				"bom": bucket["bom"],
				"regular": bucket["regular"],
				"ruim": bucket["ruim"],
				"pct_positivo": flt(positivo * 100.0 / total, 1),
				"media": (
					flt(bucket["soma"] / bucket["com_valor"], 2)
					if bucket["com_valor"]
					else None
				),
			}
		)

	out.sort(key=lambda r: (r.get("secao") or "", r.get("criterio") or ""))
	return out


def get_chart(data: list[dict]) -> dict | None:
	if not data:
		return None

	# Top 10 critérios com mais avaliações — média
	top = sorted(data, key=lambda r: r["total"], reverse=True)[:10]
	labels = [f"{d['secao']}: {d['criterio']}"[:40] for d in top]
	return {
		"data": {
			"labels": labels,
			"datasets": [
				{
					"name": _("Média"),
					"values": [flt(d.get("media") or 0) for d in top],
				}
			],
		},
		"type": "bar",
		"colors": ["#5e64ff"],
		"height": 300,
	}


def get_summary(data: list[dict]) -> list[dict]:
	if not data:
		return [
			{"value": 0, "label": _("Critérios"), "datatype": "Int", "indicator": "Grey"},
		]

	total_av = sum(d["total"] for d in data)
	medias = [d["media"] for d in data if d.get("media") is not None]
	media_geral = flt(sum(medias) / len(medias), 2) if medias else 0
	piores = sorted(
		[d for d in data if d.get("media") is not None],
		key=lambda d: d["media"],
	)
	pior = piores[0] if piores else None

	return [
		{
			"value": len(data),
			"label": _("Critérios"),
			"datatype": "Int",
			"indicator": "Blue",
		},
		{
			"value": total_av,
			"label": _("Avaliações"),
			"datatype": "Int",
			"indicator": "Blue",
		},
		{
			"value": media_geral,
			"label": _("Média geral"),
			"datatype": "Float",
			"indicator": "Green" if media_geral >= 4 else "Orange" if media_geral >= 3 else "Red",
		},
		{
			"value": flt(pior["media"], 2) if pior else 0,
			"label": _("Pior critério (média)"),
			"datatype": "Float",
			"indicator": "Red",
		},
	]
